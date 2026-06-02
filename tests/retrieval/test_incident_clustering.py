from apps.api.services.operational_intelligence import (
    _graph_row,
    _strong_graph_adjacency,
    synthesize_incidents,
)
from pipelines.retrieval.ticket_graph import (
    EDGE_ASSET,
    EDGE_CATEGORY,
    EDGE_ROOT_CAUSE,
    EDGE_SITE,
    EDGE_TIME_WINDOW,
    GraphEdge,
    build_ticket_graph,
)


def _make_snapshot(
    ticket_id: str,
    root_cause: str = "network_connectivity",
    category: str = "network_connectivity",
    confidence: float = 80.0,
    priority: float = 65.0,
    status: str = "Open",
    site: str | None = None,
    requester: str | None = None,
    assignee: str | None = None,
    asset: str | None = None,
) -> dict[str, object]:
    return {
        "ticket_id": ticket_id,
        "title": f"Ticket {ticket_id}",
        "status": status,
        "priority_raw": "High",
        "priority_score": priority,
        "root_cause_hypothesis": root_cause,
        "confidence_score": confidence,
        "created_at": "2026-04-01T00:00:00",
        "days_open": 1,
        "category": category,
        "site": site,
        "requester": requester,
        "assignee": assignee,
        "asset_id": asset,
    }


def test_min_two_tickets_to_form_cluster() -> None:
    result = synthesize_incidents([_make_snapshot("T-1")])
    assert result == []


def test_two_tickets_same_pattern_forms_cluster() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1"),
            _make_snapshot("T-2"),
        ]
    )
    assert len(result) == 1
    assert result[0]["ticket_count"] == 2


def test_different_patterns_no_cluster() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1", root_cause="network_connectivity"),
            _make_snapshot("T-2", root_cause="email_messaging"),
        ]
    )
    assert result == []


def test_confidence_threshold_filters_low_confidence() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1", confidence=30.0),
            _make_snapshot("T-2", confidence=30.0),
        ]
    )
    assert result == []


def test_cluster_confidence_uses_average() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1", confidence=80.0),
            _make_snapshot("T-2", confidence=90.0),
        ]
    )
    assert len(result) == 1
    assert result[0]["confidence"] == 85.0


def test_resolved_tickets_excluded() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1", status="Resolved"),
            _make_snapshot("T-2", status="Resolved"),
        ]
    )
    assert result == []


def test_mixed_confidence_filters_below_link_threshold() -> None:
    result = synthesize_incidents(
        [
            _make_snapshot("T-1", confidence=90.0),
            _make_snapshot("T-2", confidence=50.0),
        ]
    )
    assert result == []


def test_graph_synthesis_uses_strong_edges_only() -> None:
    """Tickets that only share a category / time window should not cluster
    on the graph path — strong adjacency requires asset, root cause, or
    site edges."""
    rows = [
        _make_snapshot(
            "T-1",
            root_cause="rc_a",
            category="email_messaging",
            site="S-1",
        ),
        _make_snapshot(
            "T-2",
            root_cause="rc_b",
            category="email_messaging",
            site="S-2",
        ),
    ]
    graph = build_ticket_graph([_graph_row(row) for row in rows])
    adjacency = _strong_graph_adjacency(graph.edges)
    # category and time-window edges are NOT strong — adjacency is empty.
    assert adjacency == {}


def test_strong_graph_adjacency_keeps_only_asset_root_cause_site() -> None:
    """Edge types like shared_category and within_time_window must not
    bootstrap a graph-based incident on their own."""
    edges = [
        GraphEdge("T-1", "T-2", EDGE_SITE, 0.8),
        GraphEdge("T-1", "T-2", EDGE_CATEGORY, 0.7),
        GraphEdge("T-1", "T-2", EDGE_TIME_WINDOW, 0.3),
    ]
    adjacency = _strong_graph_adjacency(edges)
    # Only the SITE edge should be reflected in strong adjacency.
    assert "T-2" in adjacency["T-1"]
    assert "T-1" in adjacency["T-2"]
    # category and time-window edges are dropped.
    assert EDGE_CATEGORY not in adjacency
    assert EDGE_TIME_WINDOW not in adjacency


def test_strong_graph_adjacency_drops_only_category_pair() -> None:
    """Two tickets connected only by category should yield an empty
    strong adjacency — there is no incident bootstrappable from a
    shared category alone."""
    edges = [GraphEdge("T-1", "T-2", EDGE_CATEGORY, 0.7)]
    assert _strong_graph_adjacency(edges) == {}


def test_graph_synthesis_creates_incident_on_shared_asset() -> None:
    """Two tickets that share an asset and a root cause must form a
    graph-based incident with graph_evidence attached."""
    rows = [
        _make_snapshot(
            "T-1",
            root_cause="switch uplink down",
            site="S-1",
            requester="R-1",
            asset="A-1",
        ),
        _make_snapshot(
            "T-2",
            root_cause="switch uplink down",
            site="S-1",
            requester="R-1",
            asset="A-1",
        ),
    ]
    incidents = synthesize_incidents(rows)
    assert len(incidents) == 1
    incident = incidents[0]
    assert "graph_evidence" in incident
    evidence = incident["graph_evidence"]
    assert evidence["shared_site"] == "S-1"
    assert evidence["evidence_basis"] == "ticket relationship graph"
    assert "edge_counts" in evidence
    # All three strong signals should appear in the edge counts.
    assert EDGE_ASSET in evidence["edge_counts"]
    assert EDGE_ROOT_CAUSE in evidence["edge_counts"]
    assert EDGE_SITE in evidence["edge_counts"]


def test_graph_synthesis_uses_root_cause_evidence() -> None:
    """Even without a shared site, shared root cause + asset should
    bootstrap a graph component and form an incident."""
    rows = [
        _make_snapshot("T-1", root_cause="dns_failure", asset="A-9", site="S-1"),
        _make_snapshot("T-2", root_cause="dns_failure", asset="A-9", site="S-2"),
    ]
    incidents = synthesize_incidents(rows)
    assert len(incidents) == 1
    evidence = incidents[0]["graph_evidence"]
    assert evidence["evidence_basis"] == "ticket relationship graph"
    assert EDGE_ASSET in evidence["edge_counts"]
    assert EDGE_ROOT_CAUSE in evidence["edge_counts"]


def test_graph_synthesis_keeps_isolated_tickets_out() -> None:
    """Two tickets in different sites/assets/root causes should not form
    a graph-based incident even if they share a category."""
    rows = [
        _make_snapshot("T-1", category="network_connectivity", site="S-1", root_cause="rc_a"),
        _make_snapshot("T-2", category="network_connectivity", site="S-2", root_cause="rc_b"),
    ]
    graph = build_ticket_graph([_graph_row(row) for row in rows])
    adjacency = _strong_graph_adjacency(graph.edges)
    # Only category + time-window edges exist; both are weak.
    assert adjacency == {}


def test_graph_synthesis_prefers_strong_signal_in_recommended_action() -> None:
    """A shared asset should drive a more specific recommended action
    than a generic shared root cause."""
    rows = [
        _make_snapshot("T-1", root_cause="dns_failure", asset="A-9", site="S-1"),
        _make_snapshot("T-2", root_cause="dns_failure", asset="A-9", site="S-2"),
    ]
    incidents = synthesize_incidents(rows)
    assert len(incidents) == 1
    assert "asset" in incidents[0]["recommended_action"].lower()
