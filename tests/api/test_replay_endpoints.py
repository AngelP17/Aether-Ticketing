"""
Endpoint tests for /api/replay/{ticket_id}.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import replay as replay_routes


def test_get_replay_returns_timeline(admin_client: Any) -> None:
    payload = {
        "ticket_id": "IT-1",
        "latest_decision": {"id": 1, "priority_score": 81.4},
        "decision_history": [],
        "events": [{"event_type": "ticket_created"}],
        "operator_feedback": [],
        "similar_cases": [],
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            replay_routes.ReplayService, "get_replay", lambda self, ticket_id: payload
        )
        response = admin_client.get("/api/replay/IT-1")
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == "IT-1"
    assert body["events"][0]["event_type"] == "ticket_created"


def test_get_replay_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            replay_routes.ReplayService, "get_replay", lambda self, ticket_id: None
        )
        response = admin_client.get("/api/replay/IT-MISSING")
    assert response.status_code == 404
    assert response.json()["detail"] == "Replay not found"


def test_replay_does_not_require_authentication(anon_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            replay_routes.ReplayService, "get_replay", lambda self, ticket_id: None
        )
        assert anon_client.get("/api/replay/IT-1").status_code == 404
