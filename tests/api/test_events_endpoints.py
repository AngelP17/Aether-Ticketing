"""
Endpoint tests for /api/events/{ticket_id}.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import events as events_routes


def test_get_events_returns_stream(admin_client: Any) -> None:
    stream = [
        {
            "event_type": "ticket_created",
            "event_ts": "2026-06-01T10:00:00Z",
            "actor_type": "import",
            "actor_id": "ingest",
        },
        {
            "event_type": "decision_generated",
            "event_ts": "2026-06-01T10:00:01Z",
            "actor_type": "system",
            "actor_id": "aether-api",
        },
    ]
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            events_routes.EventService,
            "get_ticket_event_stream",
            lambda self, ticket_id: stream,
        )
        response = admin_client.get("/api/events/IT-1")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["event_type"] == "ticket_created"


def test_get_events_returns_empty_list_when_no_ticket(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            events_routes.EventService,
            "get_ticket_event_stream",
            lambda self, ticket_id: [],
        )
        response = admin_client.get("/api/events/IT-MISSING")
    assert response.status_code == 200
    assert response.json() == []


def test_events_does_not_require_authentication(anon_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            events_routes.EventService,
            "get_ticket_event_stream",
            lambda self, ticket_id: [],
        )
        assert anon_client.get("/api/events/IT-1").status_code == 200
