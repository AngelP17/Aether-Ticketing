"""Endpoint tests for the application root and /health."""
from __future__ import annotations

from typing import Any


def test_root_returns_service_banner(anon_client: Any) -> None:
    response = anon_client.get("/")
    assert response.status_code == 200
    body = response.json()
    # The banner includes a service name and a version — these are documented
    # in README and used by the web app to display a healthy state.
    assert "service" in body
    assert "version" in body
    assert body["service"]


def test_health_returns_healthy(anon_client: Any) -> None:
    response = anon_client.get("/health")
    assert response.status_code == 200
    body = response.json()
    # /health is the load-balancer probe; it must always be reachable without
    # auth and report a status field.
    assert body.get("status") in {"healthy", "ok", "up"}


def test_openapi_schema_is_served(anon_client: Any) -> None:
    response = anon_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "paths" in schema
    # Spot-check that the canonical route groups are present.
    assert "/api/tickets" in schema["paths"]
    assert "/api/auth/login" in schema["paths"]
    assert "/api/governance/summary" in schema["paths"]
