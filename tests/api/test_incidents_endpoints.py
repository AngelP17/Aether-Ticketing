"""
Endpoint tests for /api/incidents.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import incidents as incidents_routes
from tests.api.factories import incident_detail_payload, incident_payload


def _patch_incident_service(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(incidents_routes.IncidentService, name, _impl)

    for method_name in ["list_incidents", "get_incident_detail"]:
        _wrap(method_name)
    return calls


def test_list_incidents_returns_persisted_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_incident_service(
            monkeypatch,
            list_incidents=[incident_payload(1), incident_payload(2, title="VPN outage")],
        )
        response = admin_client.get("/api/incidents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["title"] == "Mailbox outage"
    assert body[1]["title"] == "VPN outage"


def test_list_incidents_empty(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_incident_service(monkeypatch, list_incidents=[])
        response = admin_client.get("/api/incidents")
    assert response.status_code == 200
    assert response.json() == []


def test_get_incident_returns_detail(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_incident_service(
            monkeypatch,
            get_incident_detail=incident_detail_payload(7),
        )
        response = admin_client.get("/api/incidents/7")
    assert response.status_code == 200
    body = response.json()
    assert body["incident"]["id"] == 7
    assert body["common_cause"] == "Edge SMTP queue stuck"
    assert body["recommended_action"] == "Run mail flow restart runbook"


def test_get_incident_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_incident_service(monkeypatch, get_incident_detail=None)
        response = admin_client.get("/api/incidents/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Incident not found"


def test_incidents_requires_auth(anon_client: Any) -> None:
    response = anon_client.get("/api/incidents")
    assert response.status_code == 401
