"""Endpoint tests for /api/tickets/.../comments routes."""
from __future__ import annotations

from typing import Any, cast

import pytest
from fastapi.routing import APIRoute

import apps.api.routes.comments as comments_routes
from apps.api.routes.comments import router as comments_router


@pytest.fixture
def client(admin_client: Any) -> Any:
    return admin_client


def _patch_comment_service(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(comments_routes.CommentService, name, _impl)

    for method_name in ["list_comments", "create_comment", "update_comment", "delete_comment"]:
        _wrap(method_name)
    return calls


def test_list_comments_returns_service_payload(client: Any) -> None:
    payload = [{"id": 1, "body": "first", "author": "admin"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_comment_service(monkeypatch, list_comments=payload)
        response = client.get("/api/tickets/IT-1/comments")
    assert response.status_code == 200
    assert response.json() == payload


def test_create_comment_returns_created_record(client: Any) -> None:
    created = {"id": 7, "body": "investigating", "author": "admin"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_comment_service(monkeypatch, create_comment=created)
        response = client.post(
            "/api/tickets/IT-1/comments", json={"body": "investigating"}
        )
    assert response.status_code == 201
    assert response.json() == created
    assert calls["create_comment"]["args"] == ("IT-1", "investigating", {"username": "admin", "role": "admin", "display_name": "Admin"})


def test_create_comment_rejects_blank_body(client: Any) -> None:
    response = client.post("/api/tickets/IT-1/comments", json={"body": "   "})
    assert response.status_code == 400
    assert "required" in response.json()["detail"].lower()


def test_create_comment_404_when_ticket_missing(client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_comment_service(monkeypatch, create_comment=None)
        response = client.post("/api/tickets/IT-MISSING/comments", json={"body": "hi"})
    assert response.status_code == 404


def test_update_comment_returns_record(client: Any) -> None:
    updated = {"id": 7, "body": "updated", "author": "admin"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_comment_service(monkeypatch, update_comment=updated)
        response = client.put(
            "/api/tickets/IT-1/comments/7", json={"body": "updated"}
        )
    assert response.status_code == 200
    assert response.json() == updated
    assert calls["update_comment"]["args"] == (
        "IT-1",
        7,
        "updated",
        {"username": "admin", "role": "admin", "display_name": "Admin"},
    )


def test_update_comment_403_on_permission_error(client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise PermissionError("not your comment")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_comment_service(monkeypatch, update_comment=None)
        monkeypatch.setattr(
            comments_routes.CommentService, "update_comment", _raise
        )
        response = client.put(
            "/api/tickets/IT-1/comments/7", json={"body": "no"}
        )
    assert response.status_code == 403


def test_delete_comment_returns_success(client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch_comment_service(monkeypatch, delete_comment=True)
        response = client.delete("/api/tickets/IT-1/comments/7")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    assert calls["delete_comment"]["args"] == (
        "IT-1",
        7,
        {"username": "admin", "role": "admin", "display_name": "Admin"},
    )


def test_delete_comment_404_when_missing(client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch_comment_service(monkeypatch, delete_comment=False)
        response = client.delete("/api/tickets/IT-1/comments/999")
    assert response.status_code == 404


def test_comment_writes_require_write_role(viewer_client: Any) -> None:
    assert viewer_client.post("/api/tickets/IT-1/comments", json={"body": "x"}).status_code == 403
    assert viewer_client.put("/api/tickets/IT-1/comments/1", json={"body": "x"}).status_code == 403
    assert viewer_client.delete("/api/tickets/IT-1/comments/1").status_code == 403


def test_comment_router_path_prefix() -> None:
    # Sanity: the router does not accidentally expose a leading slash that
    # would break mounting under /api.
    assert all(
        not cast(APIRoute, r).path.startswith("/api")
        for r in comments_router.routes
    )
