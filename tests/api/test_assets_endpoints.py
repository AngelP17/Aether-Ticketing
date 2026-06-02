"""
Endpoint tests for /api/assets.
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.routes import assets as assets_routes


def test_list_assets_returns_inventory(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            assets_routes.AssetService,
            "list_assets",
            lambda self: [
                {"id": 1, "asset_name": "FileServ-Prod", "criticality": "high"},
                {"id": 2, "asset_name": "EdgeRouter", "criticality": "medium"},
            ],
        )
        response = admin_client.get("/api/assets")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["asset_name"] == "FileServ-Prod"


def test_get_asset_returns_row(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            assets_routes.AssetService,
            "get_asset",
            lambda self, asset_id: {
                "id": 1,
                "asset_name": "FileServ-Prod",
                "criticality": "high",
            },
        )
        response = admin_client.get("/api/assets/1")
    assert response.status_code == 200
    assert response.json()["asset_name"] == "FileServ-Prod"


def test_get_asset_404_when_missing(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            assets_routes.AssetService,
            "get_asset",
            lambda self, asset_id: None,
        )
        response = admin_client.get("/api/assets/999")
    assert response.status_code == 404


def test_assets_list_does_not_require_authentication(anon_client: Any) -> None:
    # /api/assets is a read-only inventory route used by the command center
    # before login. The UI gate handles auth, so the API is open.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            assets_routes.AssetService, "list_assets", lambda self: []
        )
        assert anon_client.get("/api/assets").status_code == 200
        monkeypatch.setattr(
            assets_routes.AssetService, "get_asset", lambda self, asset_id: None
        )
        assert anon_client.get("/api/assets/1").status_code == 404
