"""Endpoint tests for /api/auth routes."""
from __future__ import annotations

from typing import Any

import pytest

import apps.api.routes.auth as auth_routes


def _patch(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(auth_routes.AuthService, name, _impl)

    for method_name in [
        "login",
        "current_user",
        "list_users",
        "create_user",
        "update_user",
        "delete_user",
        "change_password",
    ]:
        _wrap(method_name)
    return calls


def test_login_returns_token_and_user(anon_client: Any) -> None:
    payload = {
        "access_token": "tkn-1",
        "token_type": "bearer",
        "user": {"username": "admin", "role": "admin"},
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, login=payload)
        response = anon_client.post(
            "/api/auth/login", json={"username": "admin", "password": "admin123"}
        )
    assert response.status_code == 200
    assert response.json() == payload


def test_login_401_on_invalid_credentials(anon_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, login=None)
        response = anon_client.post(
            "/api/auth/login", json={"username": "x", "password": "y"}
        )
    assert response.status_code == 401


def test_login_429_when_rate_limited(anon_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(auth_routes.login_rate_limiter, "is_limited", lambda *a, **k: True)
        response = anon_client.post(
            "/api/auth/login", json={"username": "x", "password": "y"}
        )
    assert response.status_code == 429


def test_logout_returns_status(anon_client: Any) -> None:
    response = anon_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_me_returns_current_user(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(
            monkeypatch,
            current_user={"username": "agent-jane", "role": "agent"},
        )
        response = agent_client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer fake"},
        )
    assert response.status_code == 200
    assert response.json() == {"username": "agent-jane", "role": "agent"}


def test_me_401_when_token_invalid(anon_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, current_user=None)
        response = anon_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer bogus"}
        )
    assert response.status_code == 401


def test_me_401_when_header_missing(anon_client: Any) -> None:
    response = anon_client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_503_when_user_store_unavailable(anon_client: Any) -> None:
    def _raise(self: Any, token: str) -> None:  # noqa: ARG001
        raise OSError("users file unavailable")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, current_user=None)
        monkeypatch.setattr(auth_routes.AuthService, "current_user", _raise)
        response = anon_client.get(
            "/api/auth/me", headers={"Authorization": "Bearer valid-shape"}
        )
    assert response.status_code == 503
    assert response.json()["detail"] == "Auth user store unavailable"


def test_list_users_requires_admin(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, list_users=[{"username": "admin", "role": "admin"}])
        response = agent_client.get("/api/auth/users")
    assert response.status_code == 403


def test_list_users_returns_users(admin_client: Any) -> None:
    users = [{"username": "admin", "role": "admin"}, {"username": "a1", "role": "agent"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, list_users=users)
        response = admin_client.get("/api/auth/users")
    assert response.status_code == 200
    assert response.json() == users


def test_create_user_returns_record(admin_client: Any) -> None:
    record = {"username": "new", "role": "agent", "display_name": "New User"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, create_user=record)
        response = admin_client.post(
            "/api/auth/users",
            json={"username": "new", "password": "pw", "role": "agent", "display_name": "New User"},
        )
    assert response.status_code == 201
    assert response.json() == record
    kwargs = calls["create_user"]["kwargs"]
    assert kwargs["username"] == "new"
    assert kwargs["password"] == "pw"
    assert kwargs["role"] == "agent"
    assert kwargs["display_name"] == "New User"


def test_create_user_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("username taken")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, create_user=None)
        monkeypatch.setattr(auth_routes.AuthService, "create_user", _raise)
        response = admin_client.post(
            "/api/auth/users",
            json={"username": "x", "password": "pw", "role": "agent", "display_name": "X"},
        )
    assert response.status_code == 400


def test_update_user_returns_record(admin_client: Any) -> None:
    record = {"username": "admin", "role": "admin", "display_name": "Admin"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, update_user=record)
        response = admin_client.put(
            "/api/auth/users/admin",
            json={"password": "new"},
        )
    assert response.status_code == 200
    assert calls["update_user"]["kwargs"]["username"] == "admin"
    assert calls["update_user"]["kwargs"]["password"] == "new"


def test_update_user_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, update_user=None)
        response = admin_client.put(
            "/api/auth/users/ghost", json={"password": "x"}
        )
    assert response.status_code == 404


def test_delete_user_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, delete_user=True)
        response = admin_client.delete("/api/auth/users/old")
    assert response.status_code == 200
    assert calls["delete_user"]["args"] == ("old",)


def test_delete_user_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> bool:
        raise ValueError("cannot delete self")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_user=False)
        monkeypatch.setattr(auth_routes.AuthService, "delete_user", _raise)
        response = admin_client.delete("/api/auth/users/admin")
    assert response.status_code == 400


def test_delete_user_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_user=False)
        response = admin_client.delete("/api/auth/users/ghost")
    assert response.status_code == 404


def test_change_password_returns_success(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, change_password=None)
        response = agent_client.post(
            "/api/auth/change-password",
            json={"current_password": "old", "new_password": "new"},
        )
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    kwargs = calls["change_password"]["kwargs"]
    assert kwargs["username"] == "agent-jane"
    assert kwargs["current_password"] == "old"
    assert kwargs["new_password"] == "new"


def test_change_password_401_on_permission_error(agent_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise PermissionError("wrong current password")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, change_password=None)
        monkeypatch.setattr(auth_routes.AuthService, "change_password", _raise)
        response = agent_client.post(
            "/api/auth/change-password",
            json={"current_password": "wrong", "new_password": "new"},
        )
    assert response.status_code == 401


def test_change_password_400_on_value_error(agent_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("weak password")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, change_password=None)
        monkeypatch.setattr(auth_routes.AuthService, "change_password", _raise)
        response = agent_client.post(
            "/api/auth/change-password",
            json={"current_password": "old", "new_password": "123"},
        )
    assert response.status_code == 400


def test_change_password_requires_authentication(anon_client: Any) -> None:
    response = anon_client.post(
        "/api/auth/change-password",
        json={"current_password": "old", "new_password": "new"},
    )
    assert response.status_code == 401


def test_user_admin_endpoints_reject_agents(agent_client: Any) -> None:
    payload = {"username": "x", "password": "pw", "role": "agent", "display_name": "X"}
    assert agent_client.post("/api/auth/users", json=payload).status_code == 403
    assert agent_client.put("/api/auth/users/x", json={"password": "y"}).status_code == 403
    assert agent_client.delete("/api/auth/users/x").status_code == 403
