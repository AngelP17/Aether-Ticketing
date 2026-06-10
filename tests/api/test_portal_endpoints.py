from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import portal as portal_routes

portal_module: Any = portal_routes


def test_portal_submit_requires_authentication(anon_client: Any) -> None:
    response = anon_client.post("/api/portal/tickets", json={"title": "demo"})

    assert response.status_code == 401


def test_portal_submit_disabled_without_demo_mode(viewer_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(portal_module.settings, "DEMO_MODE", False)
        monkeypatch.setattr(portal_module.settings, "DEMO_PORTAL_SUBMIT_ENABLED", False)
        response = viewer_client.post("/api/portal/tickets", json={"title": "demo"})

    assert response.status_code == 403


def test_portal_submit_tags_demo_ticket(viewer_client: Any, viewer_user: dict[str, str]) -> None:
    calls: dict[str, Any] = {}

    def _create_ticket(self: Any, payload: dict[str, Any], actor: dict[str, Any]) -> dict[str, Any]:
        calls["payload"] = payload
        calls["actor"] = actor
        return {"ticket_id": "IT-20260099"}

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(portal_module.settings, "DEMO_MODE", True)
        monkeypatch.setattr(portal_module.settings, "DEMO_PORTAL_SUBMIT_ENABLED", True)
        monkeypatch.setattr(portal_module.TicketService, "create_ticket", _create_ticket)
        response = viewer_client.post(
            "/api/portal/tickets",
            json={
                "title": "Demo portal request",
                "description": "Need access",
                "custom_fields": {"site": "Demo HQ"},
            },
        )

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "IT-20260099"
    assert calls["actor"]["username"] == viewer_user["username"]
    assert calls["payload"]["source_system"] == "demo_portal"
    assert calls["payload"]["custom_fields"]["demo"] is True
    assert calls["payload"]["custom_fields"]["submitted_by"] == viewer_user["username"]
