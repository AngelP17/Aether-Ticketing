"""
Endpoint tests for /api/actions.

Two surfaces:
- POST /api/actions/recommendations/{id}/apply — apply a recommendation
- GET  /api/actions/{action_run_id}            — inspect a single action run
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from apps.api.routes import actions as actions_routes


@dataclass
class _StubActionResult:
    recommendation_id: int
    action_run: dict[str, Any]
    event_id: int
    ticket_state: dict[str, Any]
    rollback_available: bool
    rollback_payload: dict[str, Any]
    feedback: dict[str, Any]


def _patch_action_service(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            # Drop `self` so the captured args/kwargs match the public signature.
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(actions_routes.ActionService, name, _impl)

    for method_name in ["apply_recommendation", "get_action_run"]:
        _wrap(method_name)
    return calls


def test_apply_recommendation_returns_serialized_result(admin_client: Any) -> None:
    result = _StubActionResult(
        recommendation_id=42,
        action_run={"id": 7, "action_type": "assign_team", "status": "completed_manual"},
        event_id=100,
        ticket_state={"status": "In Progress", "assignee": "access_identity_queue"},
        rollback_available=True,
        rollback_payload={"kind": "assignment_changed"},
        feedback={"id": 5, "feedback_type": "accepted"},
    )
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_action_service(monkeypatch, apply_recommendation=result)
        response = admin_client.post(
            "/api/actions/recommendations/42/apply",
            json={"action_type": "assign_team", "note": "go"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["recommendation_id"] == 42
    assert body["action_run"]["status"] == "completed_manual"
    assert body["rollback_available"] is True
    assert body["ticket_state"]["status"] == "In Progress"
    kwargs = calls["apply_recommendation"]["kwargs"]
    assert calls["apply_recommendation"]["args"] == ()
    assert kwargs["recommendation_id"] == 42
    assert kwargs["action_type_override"] == "assign_team"
    assert kwargs["note"] == "go"
    assert kwargs["operator_id"] == "admin"


def test_apply_recommendation_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_action_service(monkeypatch, apply_recommendation=None)
        response = admin_client.post(
            "/api/actions/recommendations/999/apply", json={"note": None}
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Recommendation not found"


def test_apply_recommendation_400_on_value_error(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:

        def _raise(*_args: Any, **_kwargs: Any) -> Any:
            raise ValueError("auto_resolve requires confirm=true")

        monkeypatch.setattr(actions_routes.ActionService, "apply_recommendation", _raise)
        response = admin_client.post(
            "/api/actions/recommendations/1/apply",
            json={"action_type": "auto_resolve"},
        )
    assert response.status_code == 400
    assert "auto_resolve" in response.json()["detail"]


def test_get_action_run_returns_row(admin_client: Any) -> None:
    row = {
        "id": 7,
        "recommendation_id": 42,
        "action_type": "apply_runbook",
        "status": "pending_review",
        "rollback_available": True,
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_action_service(monkeypatch, get_action_run=row)
        response = admin_client.get("/api/actions/7")
    assert response.status_code == 200
    assert response.json()["id"] == 7
    assert response.json()["rollback_available"] is True


def test_get_action_run_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_action_service(monkeypatch, get_action_run=None)
        response = admin_client.get("/api/actions/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Action run not found"


def test_get_action_run_requires_authentication(anon_client: Any) -> None:
    assert anon_client.get("/api/actions/1").status_code == 401


def test_actions_apply_requires_write_role(viewer_client: Any) -> None:
    response = viewer_client.post(
        "/api/actions/recommendations/1/apply", json={"note": None}
    )
    assert response.status_code == 403
