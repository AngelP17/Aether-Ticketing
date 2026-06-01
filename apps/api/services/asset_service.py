from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import text


class AssetService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_assets(self) -> Any:
        rows = self.db.execute(
            text(
                """
                SELECT id, asset_name, asset_type, site_id, criticality, owner_team, dependency_json
                FROM assets
                ORDER BY asset_name ASC
                """
            )
        ).mappings()
        return [dict(row) for row in rows]

    def get_asset(self, asset_id: int) -> Any:
        row = self.db.execute(
            text(
                """
                SELECT id, asset_name, asset_type, site_id, criticality, owner_team, dependency_json
                FROM assets
                WHERE id = :asset_id
                """
            ),
            {"asset_id": asset_id},
        ).mappings().first()
        return dict(row) if row else None
