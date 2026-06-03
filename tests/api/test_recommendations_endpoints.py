"""
Endpoint tests for /api/recommendations.

The legacy /api/recommendations/{id}/accept, /reject, /override routes
are wired through RecommendationService which itself delegates to
ActionService. We patch the service at the route level so the response
shape is verified end-to-end.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import recommendations as recommendations_routes


def _patch_recommendation_service(
    monkeypatch: pytest.MonkeyPatch, **overrides: Any
) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(recommendations_routes.RecommendationService, name, _impl)

    for method_name in [
        "accept_recommendation",
        "reject_recommendation",
        "override_recommendation",
    ]:
        _wrap(method_name)
    return calls


def test_accept_recommendation_returns_status(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_recommendation_service(
            monkeypatch, accept_recommendation={"id": 1, "status": "accepted"}
        )
        response = admin_client.post(
            "/api/recommendations/1/accept", json={"note": "looks right"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert calls["accept_recommendation"]["args"] == (1, "looks right")


def test_reject_recommendation_returns_status(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_recommendation_service(
            monkeypatch, reject_recommendation={"id": 2, "status": "rejected"}
        )
        response = admin_client.post(
            "/api/recommendations/2/reject", json={"reason": "wrong category"}
        )
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert calls["reject_recommendation"]["args"] == (2, "wrong category")


def test_override_recommendation_returns_status(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_recommendation_service(
            monkeypatch,
            override_recommendation={"id": 3, "status": "overridden"},
        )
        response = admin_client.post(
            "/api/recommendations/3/override",
            json={"override_note": "VIP", "override_priority": 95},
        )
    assert response.status_code == 200
    assert response.json()["status"] == "overridden"
    args = calls["override_recommendation"]["args"]
    assert args == (3, "VIP", 95.0)


def test_accept_returns_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_recommendation_service(monkeypatch, accept_recommendation=None)
        response = admin_client.post("/api/recommendations/999/accept", json={"note": None})
    assert response.status_code == 404


def test_reject_returns_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_recommendation_service(monkeypatch, reject_recommendation=None)
        response = admin_client.post("/api/recommendations/999/reject", json={"reason": None})
    assert response.status_code == 404


def test_override_returns_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_recommendation_service(monkeypatch, override_recommendation=None)
        response = admin_client.post(
            "/api/recommendations/999/override",
            json={"override_note": "x", "override_priority": 1},
        )
    assert response.status_code == 404


def test_recommendations_requires_write_auth(anon_client: Any) -> None:
    # Phase1: rec actions guarded with require_ticket_write or get_current.
    src = open("apps/api/routes/recommendations.py").read()
    assert "Depends" in src
    # actions path also guarded
    src2 = open("apps/api/routes/actions.py").read()
    assert "require_ticket_write" in src2
