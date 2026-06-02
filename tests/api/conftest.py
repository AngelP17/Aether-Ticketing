"""
Shared fixtures for API endpoint tests.

Most endpoint tests in this directory stub the database session via
``app.dependency_overrides[get_db]`` and patch the service classes to
return deterministic data, so we never need a real Postgres connection.
"""
from __future__ import annotations

from typing import Iterator

import pytest
from fastapi import Header, HTTPException
from fastapi.testclient import TestClient

from apps.api.deps import get_db
from apps.api.main import app
from apps.api.security import get_current_user, require_admin, require_ticket_write


ADMIN_USER: dict[str, str] = {
    "username": "admin",
    "role": "admin",
    "display_name": "Admin",
}

AGENT_USER: dict[str, str] = {
    "username": "agent-jane",
    "role": "agent",
    "display_name": "Jane Agent",
}

VIEWER_USER: dict[str, str] = {
    "username": "viewer-bob",
    "role": "viewer",
    "display_name": "Bob Viewer",
}


class _NullSession:
    """Sentinel session; service methods are patched in each test, so it is never called."""


def _forbid(authorization: str | None = Header(default=None)) -> None:
    raise HTTPException(status_code=403, detail="Insufficient privileges")


def _unauthenticated(authorization: str | None = Header(default=None)) -> None:
    raise HTTPException(status_code=401, detail="Missing bearer token")


@pytest.fixture
def admin_user() -> dict[str, str]:
    return dict(ADMIN_USER)


@pytest.fixture
def agent_user() -> dict[str, str]:
    return dict(AGENT_USER)


@pytest.fixture
def viewer_user() -> dict[str, str]:
    return dict(VIEWER_USER)


@pytest.fixture
def admin_client(admin_user: dict[str, str]) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _NullSession()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    app.dependency_overrides[require_ticket_write] = lambda: admin_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def agent_client(agent_user: dict[str, str]) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _NullSession()
    app.dependency_overrides[get_current_user] = lambda: agent_user
    app.dependency_overrides[require_admin] = _forbid
    app.dependency_overrides[require_ticket_write] = lambda: agent_user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def viewer_client(viewer_user: dict[str, str]) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _NullSession()
    app.dependency_overrides[get_current_user] = lambda: viewer_user
    app.dependency_overrides[require_admin] = _forbid
    app.dependency_overrides[require_ticket_write] = _forbid
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def anon_client() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _NullSession()
    app.dependency_overrides[get_current_user] = _unauthenticated
    app.dependency_overrides[require_admin] = _unauthenticated
    app.dependency_overrides[require_ticket_write] = _unauthenticated
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
