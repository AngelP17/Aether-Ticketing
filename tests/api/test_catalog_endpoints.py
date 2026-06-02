"""Endpoint tests for /api/categories, /api/labels, /api/assignees, /api/options."""
from __future__ import annotations

from typing import Any

import pytest

import apps.api.routes.catalog as catalog_routes


def _patch(monkeypatch: pytest.MonkeyPatch, **overrides: Any) -> dict[str, Any]:
    calls: dict[str, Any] = {}

    def _wrap(name: str) -> None:
        def _impl(self: Any, *args: Any, **kwargs: Any) -> Any:
            calls[name] = {"args": args, "kwargs": kwargs}
            return overrides.get(name)

        monkeypatch.setattr(catalog_routes.CatalogService, name, _impl)

    for method_name in [
        "list_categories",
        "create_category",
        "update_category",
        "delete_category",
        "list_labels",
        "create_label",
        "delete_label",
        "create_assignee",
        "delete_assignee",
        "get_options",
    ]:
        _wrap(method_name)
    return calls


def test_list_categories_returns_active(agent_client: Any) -> None:
    rows = [{"id": 1, "name": "Access", "color": "#6366f1"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, list_categories=rows)
        response = agent_client.get("/api/categories")
    assert response.status_code == 200
    assert response.json() == rows


def test_create_category_returns_record(admin_client: Any) -> None:
    record = {"id": 5, "name": "Networking", "color": "#10b981", "icon": "fa-network-wired"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, create_category=record)
        response = admin_client.post(
            "/api/categories",
            json={"name": "Networking", "color": "#10b981", "icon": "fa-network-wired"},
        )
    assert response.status_code == 201
    assert response.json() == record
    assert calls["create_category"]["args"] == ("Networking", "#10b981", "fa-network-wired")


def test_create_category_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("duplicate name")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, create_category=None)
        monkeypatch.setattr(catalog_routes.CatalogService, "create_category", _raise)
        response = admin_client.post(
            "/api/categories", json={"name": "Dup", "color": "#000", "icon": "fa-x"}
        )
    assert response.status_code == 400


def test_update_category_returns_record(admin_client: Any) -> None:
    record = {"id": 1, "name": "Access (renamed)", "color": "#10b981"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, update_category=record)
        response = admin_client.put(
            "/api/categories/1",
            json={"name": "Access (renamed)", "color": "#10b981"},
        )
    assert response.status_code == 200
    assert response.json() == record
    args = calls["update_category"]["args"]
    assert args[0] == 1
    assert args[1]["name"] == "Access (renamed)"
    assert args[1]["color"] == "#10b981"


def test_update_category_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, update_category=None)
        response = admin_client.put(
            "/api/categories/999", json={"name": "X"}
        )
    assert response.status_code == 404


def test_delete_category_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, delete_category=True)
        response = admin_client.delete("/api/categories/1")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    assert calls["delete_category"]["args"] == (1,)


def test_delete_category_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_category=False)
        response = admin_client.delete("/api/categories/999")
    assert response.status_code == 404


def test_list_labels_returns_all(agent_client: Any) -> None:
    rows = [{"id": 1, "name": "p1", "color": "#000"}]
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, list_labels=rows)
        response = agent_client.get("/api/labels")
    assert response.status_code == 200
    assert response.json() == rows


def test_create_label_returns_record(admin_client: Any) -> None:
    record = {"id": 2, "name": "p2", "color": "#0f0"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, create_label=record)
        response = admin_client.post(
            "/api/labels", json={"name": "p2", "color": "#0f0"}
        )
    assert response.status_code == 201
    assert response.json() == record
    assert calls["create_label"]["args"] == ("p2", "#0f0")


def test_delete_label_returns_success(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_label=None)
        response = admin_client.delete("/api/labels/1")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_list_assignees_returns_options(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            catalog_routes.CatalogService,
            "get_options",
            lambda self: {"assignees": [{"id": 1, "display_name": "alpha"}]},
        )
        response = agent_client.get("/api/assignees")
    assert response.status_code == 200
    assert response.json() == [{"id": 1, "display_name": "alpha"}]


def test_create_assignee_returns_record(admin_client: Any) -> None:
    record = {"id": 7, "display_name": "new_assignee"}
    with pytest.MonkeyPatch.context() as monkeypatch:
        calls = _patch(monkeypatch, create_assignee=record)
        response = admin_client.post(
            "/api/assignees", json={"display_name": "new_assignee"}
        )
    assert response.status_code == 201
    assert response.json() == record
    assert calls["create_assignee"]["args"] == ("new_assignee",)


def test_create_assignee_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("dup")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, create_assignee=None)
        monkeypatch.setattr(catalog_routes.CatalogService, "create_assignee", _raise)
        response = admin_client.post(
            "/api/assignees", json={"display_name": "dup"}
        )
    assert response.status_code == 400


def test_delete_assignee_uses_query_param(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_assignee=None)
        response = admin_client.delete("/api/assignees?display_name=alpha")
    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_delete_assignee_400_on_value_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> None:
        raise ValueError("missing")

    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, delete_assignee=None)
        monkeypatch.setattr(catalog_routes.CatalogService, "delete_assignee", _raise)
        response = admin_client.delete("/api/assignees?display_name=ghost")
    assert response.status_code == 400


def test_options_endpoint_returns_full_options(agent_client: Any) -> None:
    payload = {
        "categories": [],
        "labels": [],
        "assignees": [],
        "priorities": [],
        "statuses": [],
        "sites": [],
    }
    with pytest.MonkeyPatch.context() as monkeypatch:
        _patch(monkeypatch, get_options=payload)
        response = agent_client.get("/api/options")
    assert response.status_code == 200
    assert response.json() == payload


def test_catalog_writes_require_admin(viewer_client: Any, agent_client: Any) -> None:
    payload = {"name": "X", "color": "#000", "icon": "fa-x"}
    # Viewer is rejected on every write.
    assert viewer_client.post("/api/categories", json=payload).status_code == 403
    assert viewer_client.post("/api/labels", json={"name": "p", "color": "#0"}).status_code == 403
    assert viewer_client.post("/api/assignees", json={"display_name": "x"}).status_code == 403
    # Agent is rejected on writes (admin only).
    assert agent_client.post("/api/categories", json=payload).status_code == 403
    assert agent_client.put("/api/categories/1", json={"name": "y"}).status_code == 403
    assert agent_client.delete("/api/categories/1").status_code == 403


def test_catalog_reads_require_authentication(anon_client: Any) -> None:
    assert anon_client.get("/api/categories").status_code == 401
    assert anon_client.get("/api/labels").status_code == 401
    assert anon_client.get("/api/assignees").status_code == 401
    assert anon_client.get("/api/options").status_code == 401
