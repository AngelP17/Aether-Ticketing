"""Endpoint tests for /api/governance routes."""
from __future__ import annotations

from typing import Any

import pytest

import apps.api.routes.governance as governance_routes


def _patch(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str, target: Any) -> None:
        def _impl(*args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(target, name, _impl)

    for method_name in ["run_drift_detection", "summarize_graph", "build_decision_card"]:
        # Each is a top-level function in a different module — patch by attribute.
        if method_name == "run_drift_detection":
            target = governance_routes  # imported as a name in routes module
        elif method_name == "summarize_graph":
            target = governance_routes
        else:
            target = governance_routes
        _wrap(method_name, target)
    return calls


def test_governance_summary_combines_drift_graph_card(agent_client: Any) -> None:
    drift = {"status": "ok", "drift_count": 0}
    graph = {"node_count": 100, "edge_count": 250}
    card = {"engine": "graph-v2", "version": "rules-2026-graph"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(governance_routes, "run_drift_detection", lambda db: drift)
        monkeypatch.setattr(governance_routes, "summarize_graph", lambda db: graph)
        monkeypatch.setattr(governance_routes, "build_decision_card", lambda: card)
        response = agent_client.get("/api/governance/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["drift"] == drift
    assert body["graph"] == graph
    assert body["card"] == card


def test_governance_summary_handles_drift_failure(agent_client: Any) -> None:
    card = {"engine": "graph-v2"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            governance_routes, "run_drift_detection", lambda db: (_ for _ in ()).throw(RuntimeError("db down"))
        )
        monkeypatch.setattr(governance_routes, "summarize_graph", lambda db: {"status": "ok"})
        monkeypatch.setattr(governance_routes, "build_decision_card", lambda: card)
        response = agent_client.get("/api/governance/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["drift"]["status"] == "unavailable"
    assert "db down" in body["drift"]["error"]
    assert body["graph"] == {"status": "ok"}
    assert body["card"] == card


def test_governance_summary_handles_graph_failure(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(governance_routes, "run_drift_detection", lambda db: {"status": "ok"})
        monkeypatch.setattr(
            governance_routes,
            "summarize_graph",
            lambda db: (_ for _ in ()).throw(RuntimeError("graph empty")),
        )
        monkeypatch.setattr(governance_routes, "build_decision_card", lambda: {})
        response = agent_client.get("/api/governance/summary")
    assert response.status_code == 200
    assert response.json()["graph"]["status"] == "unavailable"


def test_governance_card_returns_card_only(agent_client: Any) -> None:
    card = {"engine": "graph-v2", "version": "rules-2026-graph"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(governance_routes, "build_decision_card", lambda: card)
        response = agent_client.get("/api/governance/card")
    assert response.status_code == 200
    assert response.json() == card


def test_governance_requires_authentication(anon_client: Any) -> None:
    assert anon_client.get("/api/governance/summary").status_code == 401
    assert anon_client.get("/api/governance/card").status_code == 401
