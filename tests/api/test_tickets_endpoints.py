"""
Endpoint tests for /api/tickets, /api/tickets/{id}, /api/tickets/{id}/events,
/api/tickets/{id}/labels and /api/tickets/{id}/move.

The TicketService is patched per test so we never need a real Postgres
database. Routes are verified to delegate to the right service method
and to translate success / not-found / validation cases into the
documented HTTP responses.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import tickets as tickets_routes
from tests.api.factories import ticket_detail_payload, ticket_payload


def _patch_ticket_service(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(tickets_routes.TicketService, name, _impl)

    for method_name in [
        "list_tickets",
        "get_ticket_detail",
        "get_ticket_events",
        "create_ticket",
        "update_ticket",
        "delete_ticket",
        "set_ticket_labels",
        "move_ticket",
    ]:
        _wrap(method_name)
    return calls


def test_list_tickets_returns_service_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_ticket_service(
            monkeypatch, list_tickets=[ticket_payload("IT-1")]
        )
        response = admin_client.get("/api/tickets?status=Open&ranking=true&limit=5")
    assert response.status_code == 200
    body = response.json()
    assert body[0]["ticket_id"] == "IT-1"
    assert body[0]["title"] == "Cannot access shared drive"
    kwargs = calls["list_tickets"]["kwargs"]
    assert kwargs["status"] == "Open"
    assert kwargs["ranking"] is True
    assert kwargs["limit"] == 5


def test_list_tickets_validates_limit(admin_client: Any) -> None:
    response = admin_client.get("/api/tickets?limit=10000")
    assert response.status_code == 422


def test_list_tickets_validates_negative_offset(admin_client: Any) -> None:
    response = admin_client.get("/api/tickets?offset=-1")
    assert response.status_code == 422


def test_get_ticket_returns_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, get_ticket_detail=None)
        response = admin_client.get("/api/tickets/IT-MISSING")
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_get_ticket_returns_detail(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(
            monkeypatch,
            get_ticket_detail=ticket_detail_payload("IT-2"),
        )
        response = admin_client.get("/api/tickets/IT-2")
    assert response.status_code == 200
    body = response.json()
    assert body["ticket"]["ticket_id"] == "IT-2"
    assert body["comments"] == []
    assert body["recommendations"] == []


def test_ticket_events_returns_stream(admin_client: Any) -> None:
    stream = [{"event_type": "ticket_created", "event_ts": "2026-06-01T12:00:00Z"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, get_ticket_events=stream)
        response = admin_client.get("/api/tickets/IT-3/events")
    assert response.status_code == 200
    assert response.json() == stream


def test_create_ticket_201_on_success(admin_client: Any) -> None:
    payload = ticket_detail_payload("IT-NEW")
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, create_ticket=payload)
        response = admin_client.post(
            "/api/tickets",
            json={"title": "VPN down", "priority": "High"},
        )
    assert response.status_code == 201
    assert response.json()["ticket"]["ticket_id"] == "IT-NEW"


def test_create_ticket_400_on_validation_error(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:

        def _raise(*_args: Any, **_kwargs: Any) -> Any:
            raise ValueError("Title is required")

        monkeypatch.setattr(tickets_routes.TicketService, "create_ticket", _raise)
        response = admin_client.post("/api/tickets", json={"title": ""})
    assert response.status_code == 400
    assert "Title" in response.json()["detail"]


def test_update_ticket_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, update_ticket=None)
        response = admin_client.put("/api/tickets/IT-X", json={"priority": "Low"})
    assert response.status_code == 404


def test_update_ticket_returns_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(
            monkeypatch,
            update_ticket=ticket_detail_payload("IT-4"),
        )
        response = admin_client.put("/api/tickets/IT-4", json={"priority": "High"})
    assert response.status_code == 200
    assert response.json()["ticket"]["ticket_id"] == "IT-4"


def test_delete_ticket_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, delete_ticket=False)
        response = admin_client.delete("/api/tickets/IT-D")
    assert response.status_code == 404


def test_delete_ticket_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, delete_ticket=True)
        response = admin_client.delete("/api/tickets/IT-D2")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_set_labels_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, set_ticket_labels=False)
        response = admin_client.put("/api/tickets/IT-L/labels", json={"label_ids": [1, 2]})
    assert response.status_code == 404


def test_set_labels_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, set_ticket_labels=True)
        response = admin_client.put("/api/tickets/IT-L/labels", json={"label_ids": [1]})
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_move_ticket_400_on_validation_error(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:

        def _raise(*_args: Any, **_kwargs: Any) -> Any:
            raise ValueError("A valid target status or column is required")

        monkeypatch.setattr(tickets_routes.TicketService, "move_ticket", _raise)
        response = admin_client.put("/api/tickets/IT-M/move", json={"column": "NONSENSE"})
    assert response.status_code == 400


def test_move_ticket_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, move_ticket=None)
        response = admin_client.put("/api/tickets/IT-M2/move", json={"column": "DONE"})
    assert response.status_code == 404


def test_move_ticket_returns_updated_ticket(admin_client: Any) -> None:
    payload = ticket_detail_payload("IT-M3")
    payload["ticket"]["status"] = "Resolved"
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_ticket_service(monkeypatch, move_ticket=payload)
        response = admin_client.put("/api/tickets/IT-M3/move", json={"column": "DONE"})
    assert response.status_code == 200
    assert response.json()["ticket"]["status"] == "Resolved"


def test_ticket_writes_require_write_role(viewer_client: Any) -> None:
    response = viewer_client.post("/api/tickets", json={"title": "x"})
    assert response.status_code == 403, response.text
    response = viewer_client.put("/api/tickets/IT-1/labels", json={"label_ids": [1]})
    assert response.status_code == 403, response.text
    response = viewer_client.delete("/api/tickets/IT-1")
    assert response.status_code == 403, response.text
