"""
Tests for the graph-degree → similar_cases_count wiring in DecisionService.

The new code in `recompute_decision` computes
`similar_cases_count = max(legacy_similar_count, graph_degree)` and then
runs `compute_live_decision` with that count. We stub out the DB session
and the `features_for_ticket` call to verify the wiring without standing
up Postgres.
"""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any

from apps.api.services import decision_service
from apps.api.services.decision_service import DecisionService


class _StubSession:
    """Records every execute() call and returns scripted responses.

    The default script returns ``respond_with`` for the INSERT INTO
    decision_records call and generic empty results for everything else
    (category score queries, recommendation lookups, etc.).
    """

    def __init__(self) -> None:
        self.executes: list[tuple[str, dict[str, Any]]] = []
        self.respond_with: Any = None
        self.committed = False

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        text = getattr(statement, "text", str(statement))
        self.executes.append((text, params or {}))

        if "INSERT INTO decision_records" in text and self.respond_with is not None:
            return self.respond_with

        return SimpleNamespace(
            mappings=lambda: [],
            scalars=lambda: SimpleNamespace(all=lambda: []),
        )

    def commit(self) -> None:
        self.committed = True


def _stub_features(graph_degree: int) -> dict[str, Any]:
    return {
        "ticket_id": "T-1",
        "graph_degree": graph_degree,
        "graph_weighted_degree": float(graph_degree) * 0.5,
        "edge_counts": {"shared_root_cause": graph_degree} if graph_degree else {},
        "neighbor_count": graph_degree,
        "is_isolated": graph_degree == 0,
        "signal_density": float(graph_degree) * 0.05,
        "graph_reasoning": "stub reasoning",
    }


def _stub_decision() -> dict[str, Any]:
    return {
        "priority_score": 60.0,
        "severity_score": 50.0,
        "urgency_score": 40.0,
        "business_impact_score": 30.0,
        "sla_risk_score": 20.0,
        "recurrence_score": 10.0,
        "dependency_criticality_score": 10.0,
        "actionability_score": 20.0,
        "uncertainty_penalty": 10.0,
        "root_cause_hypothesis": "stub",
        "confidence_score": 75.0,
        "clean_summary": "",
        "feature_snapshot_json": {"days_open": 1},
        "explanation_json": {"rationale": "stub"},
        "recommendations": [],
    }


def test_recompute_uses_max_of_legacy_similar_count_and_graph_degree(
    monkeypatch: Any,
) -> None:
    captured: dict[str, int] = {}

    def fake_compute_live_decision(
        ticket: dict[str, Any], similar_cases_count: int, **kwargs: Any
    ) -> dict[str, Any]:
        captured["similar_cases_count"] = similar_cases_count
        return _stub_decision()

    monkeypatch.setattr(decision_service, "compute_live_decision", fake_compute_live_decision)
    monkeypatch.setattr(decision_service, "count_similar_cases", lambda *_args, **_kwargs: 2)
    monkeypatch.setattr(
        decision_service,
        "fetch_ticket_row",
        lambda *_args, **_kwargs: {"id": 7, "ticket_id": "T-1", "title": "stub"},
    )
    monkeypatch.setattr(decision_service, "features_for_ticket", lambda *_args, **_kwargs: _stub_features(graph_degree=5))

    inserted = {"id": 42, "decision_ts": datetime.fromisoformat("2026-06-02T10:00:00")}
    session = _StubSession()
    session.respond_with = SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: inserted))

    service = DecisionService(session)  # type: ignore[arg-type]
    payload = service.recompute_decision("T-1")

    # max(2, 5) = 5
    assert captured["similar_cases_count"] == 5
    assert payload["graph_degree"] == 5
    assert payload["graph_weighted_degree"] == 2.5
    assert payload["decision_band"] in {"high_confidence_action", "review_needed", "standard_queue"}
    assert payload["decision_version"] == "v2"
    assert payload["rule_version"] == "rules-2026-graph-v2"
    assert payload["decision_hash"]
    assert len(payload["decision_hash"]) == 64
    assert payload["feature_snapshot_json"]["graph_features"]["graph_degree"] == 5
    assert payload["feature_snapshot_json"]["similar_cases_source"]["used_similar_cases_count"] == 5


def test_recompute_uses_legacy_count_when_graph_degree_is_zero(
    monkeypatch: Any,
) -> None:
    captured: dict[str, int] = {}

    def fake_compute_live_decision(
        ticket: dict[str, Any], similar_cases_count: int, **kwargs: Any
    ) -> dict[str, Any]:
        captured["similar_cases_count"] = similar_cases_count
        decision = _stub_decision()
        decision["confidence_score"] = 60.0
        decision["uncertainty_penalty"] = 15.0
        return decision

    monkeypatch.setattr(decision_service, "compute_live_decision", fake_compute_live_decision)
    monkeypatch.setattr(decision_service, "count_similar_cases", lambda *_args, **_kwargs: 3)
    monkeypatch.setattr(
        decision_service,
        "fetch_ticket_row",
        lambda *_args, **_kwargs: {"id": 7, "ticket_id": "T-1", "title": "stub"},
    )
    monkeypatch.setattr(decision_service, "features_for_ticket", lambda *_args, **_kwargs: _stub_features(graph_degree=0))

    inserted = {"id": 43, "decision_ts": datetime.fromisoformat("2026-06-02T10:00:00")}
    session = _StubSession()
    session.respond_with = SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: inserted))

    service = DecisionService(session)  # type: ignore[arg-type]
    service.recompute_decision("T-1")

    # max(3, 0) = 3
    assert captured["similar_cases_count"] == 3


def test_recompute_hashes_are_deterministic_for_same_inputs(monkeypatch: Any) -> None:
    """Recompute must produce the same decision hash when the underlying
    inputs are unchanged (modulo timestamps)."""

    def fake_compute_live_decision(
        ticket: dict[str, Any], similar_cases_count: int, **kwargs: Any
    ) -> dict[str, Any]:
        decision = _stub_decision()
        decision["priority_score"] = 70.0
        decision["confidence_score"] = 85.0
        decision["uncertainty_penalty"] = 5.0
        return decision

    monkeypatch.setattr(decision_service, "compute_live_decision", fake_compute_live_decision)
    monkeypatch.setattr(decision_service, "count_similar_cases", lambda *_args, **_kwargs: 2)
    monkeypatch.setattr(
        decision_service,
        "fetch_ticket_row",
        lambda *_args, **_kwargs: {"id": 7, "ticket_id": "T-9", "title": "stub"},
    )
    monkeypatch.setattr(decision_service, "features_for_ticket", lambda *_args, **_kwargs: _stub_features(graph_degree=2))

    inserted = {"id": 99, "decision_ts": datetime.fromisoformat("2026-06-02T10:00:00")}
    session_one = _StubSession()
    session_one.respond_with = SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: inserted))
    service_one = DecisionService(session_one)  # type: ignore[arg-type]
    payload_one = service_one.recompute_decision("T-9")

    session_two = _StubSession()
    session_two.respond_with = SimpleNamespace(mappings=lambda: SimpleNamespace(first=lambda: inserted))
    service_two = DecisionService(session_two)  # type: ignore[arg-type]
    payload_two = service_two.recompute_decision("T-9")

    assert payload_one["decision_hash"] == payload_two["decision_hash"]
