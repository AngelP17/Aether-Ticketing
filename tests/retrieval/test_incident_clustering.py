from apps.api.services.operational_intelligence import synthesize_incidents


def _make_snapshot(
    ticket_id: str,
    root_cause: str = "network_connectivity",
    category: str = "network_connectivity",
    confidence: float = 80.0,
    priority: float = 65.0,
    status: str = "Open",
) -> dict:
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
