from __future__ import annotations

from datetime import datetime, timedelta

from pipelines.retrieval.ticket_graph import (
    EDGE_REQUESTER,
    EDGE_SITE,
    EDGE_TIME_WINDOW,
    GraphEdge,
    TicketGraph,
    build_reasoning,
    build_ticket_graph,
    compute_graph_features,
)


def _ticket(ticket_id: str, **kwargs: object) -> dict[str, object]:
    base: dict[str, object] = {"ticket_id": ticket_id}
    base.update(kwargs)
    return base


def test_graph_edge_fingerprint_is_canonical() -> None:
    edge = GraphEdge(source="T-1", target="T-2", edge_type=EDGE_SITE, weight=0.8)
    assert edge.fingerprint() == GraphEdge(source="T-2", target="T-1", edge_type=EDGE_SITE, weight=0.8).fingerprint()


def test_add_edge_skips_self_loop() -> None:
    graph = TicketGraph()
    graph.add_node("T-1", {"site_id": "S-1"})
    graph.add_edge("T-1", "T-1", EDGE_SITE, 0.8)
    assert graph.degree("T-1") == 0


def test_add_edge_skips_unknown_node() -> None:
    graph = TicketGraph()
    graph.add_node("T-1", {"site_id": "S-1"})
    graph.add_edge("T-1", "T-9", EDGE_SITE, 0.8)
    assert graph.degree("T-1") == 0


def test_build_ticket_graph_connects_shared_site() -> None:
    base = datetime(2026, 6, 2, 10, 0, 0)
    rows = [
        _ticket("T-1", site_id="S-1", created_at=base),
        _ticket("T-2", site_id="S-1", created_at=base + timedelta(hours=1)),
        _ticket("T-3", site_id="S-2", created_at=base + timedelta(hours=2)),
    ]
    graph = build_ticket_graph(rows)
    # T-1 ↔ T-2 share a site; T-1 ↔ T-2 and T-1 ↔ T-3 also co-occur in time.
    assert graph.degree("T-1") == 3
    assert graph.edges_by_type("T-1").get(EDGE_SITE) == 1
    assert graph.edges_by_type("T-1").get(EDGE_TIME_WINDOW) == 2
    # T-3 has no shared site, only time-window edges.
    assert graph.edges_by_type("T-3").get(EDGE_SITE) is None


def test_build_ticket_graph_separates_isolated_ticket() -> None:
    rows = [
        _ticket("T-1", site_id="S-1"),
        _ticket("T-2", site_id="S-2", asset_id="A-9"),
    ]
    graph = build_ticket_graph(rows)
    assert graph.degree("T-1") == 0
    assert graph.degree("T-2") == 0


def test_compute_graph_features_isolated_returns_zeros() -> None:
    graph = build_ticket_graph([_ticket("T-1", site_id="S-1")])
    features = compute_graph_features(graph, "T-1")
    assert features["is_isolated"] is True
    assert features["graph_degree"] == 0
    assert features["signal_density"] == 0.0


def test_compute_graph_features_weighted_degree_matches_edges() -> None:
    rows = [
        _ticket("T-1", site_id="S-1", requester="R-1"),
        _ticket("T-2", site_id="S-1", requester="R-1"),
    ]
    graph = build_ticket_graph(rows)
    features = compute_graph_features(graph, "T-1")
    assert features["is_isolated"] is False
    # T-1 ↔ T-2 emit two edges: shared_site + shared_requester
    assert features["graph_degree"] == 2
    assert features["edge_counts"][EDGE_SITE] == 1
    assert features["edge_counts"][EDGE_REQUESTER] == 1
    assert features["graph_weighted_degree"] > 0


def test_build_reasoning_isolated_message() -> None:
    graph = build_ticket_graph([_ticket("T-1", site_id="S-1")])
    payload = build_reasoning(graph, "T-1")
    # No edges exist for a single-node graph; reasoning falls through to "no graph neighbors".
    assert "no graph neighbors" in payload["graph_reasoning"]


def test_build_reasoning_summarises_known_edges() -> None:
    rows = [
        _ticket("T-1", site_id="S-1", asset_id="A-9", requester="R-1"),
        _ticket("T-2", site_id="S-1", asset_id="A-9", requester="R-1"),
    ]
    graph = build_ticket_graph(rows)
    payload = build_reasoning(graph, "T-1")
    assert "site" in payload["graph_reasoning"]
    assert "asset" in payload["graph_reasoning"]
    assert "requester" in payload["graph_reasoning"]
