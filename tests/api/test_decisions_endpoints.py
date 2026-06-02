"""
Endpoint tests for /api/decisions.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import decisions as decisions_routes
from tests.api.factories import decision_payload


def _patch_decision_service(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(decisions_routes.DecisionService, name, _impl)

    for method_name in ["get_latest_decision", "recompute_decision"]:
        _wrap(method_name)
    return calls


def test_get_decision_returns_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_decision_service(
            monkeypatch,
            get_latest_decision=decision_payload("IT-1", id=11, decision_band="high_confidence_action"),
        )
        response = admin_client.get("/api/decisions/IT-1")
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "IT-1"
    assert body["decision_band"] == "high_confidence_action"
    assert body["decision_hash"] == "a" * 64


def test_get_decision_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_decision_service(monkeypatch, get_latest_decision=None)
        response = admin_client.get("/api/decisions/IT-MISSING")
    assert response.status_code == 404
    assert response.json()["detail"] == "Decision not found"


def test_recompute_decision_returns_fresh_payload(admin_client: Any) -> None:
    payload = decision_payload(
        "IT-2",
        id=12,
        priority_score=73.0,
        root_cause_hypothesis="network_connectivity",
        decision_band="review_needed",
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_decision_service(monkeypatch, recompute_decision=payload)
        response = admin_client.post("/api/decisions/recompute/IT-2")
    assert response.status_code == 200
    body = response.json()
    assert body["decision_hash"] == "a" * 64
    assert body["root_cause_hypothesis"] == "network_connectivity"
    assert calls["recompute_decision"]["args"] == ("IT-2",)


def test_recompute_decision_returns_404_when_ticket_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_decision_service(monkeypatch, recompute_decision=None)
        response = admin_client.post("/api/decisions/recompute/IT-MISSING")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_decisions_does_not_require_authentication(anon_client: Any) -> None:
    # Decisions are read-only and used by the command center pre-auth.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            decisions_routes.DecisionService, "get_latest_decision", lambda *a, **k: None
        )
        assert anon_client.get("/api/decisions/IT-1").status_code == 404
