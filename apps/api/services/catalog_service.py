from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.auth_service import AuthService


class CatalogService:
    def __init__(self, db: Session):
        self.db = db

    def list_categories(self, active_only: bool = True):
        where_clause = "WHERE is_active = TRUE" if active_only else ""
        rows = self.db.execute(
            text(
                f"""
                SELECT id, name, color, icon, is_custom, is_active
                FROM categories
                {where_clause}
                ORDER BY sort_order NULLS LAST, name ASC
                """
            )
        ).mappings()
        return [dict(row) for row in rows]

    def create_category(self, name: str, color: str, icon: str):
        row = self.db.execute(
            text(
                """
                INSERT INTO categories (name, color, icon, is_custom, is_active)
                VALUES (:name, :color, :icon, TRUE, TRUE)
                RETURNING id, name, color, icon, is_custom, is_active
                """
            ),
            {"name": name.strip(), "color": color, "icon": icon},
        ).mappings().one()
        self.db.commit()
        return dict(row)

    def update_category(self, category_id: int, payload: dict[str, object]):
        updates: list[str] = []
        params: dict[str, object] = {"category_id": category_id}
        for field in ["name", "color", "icon", "is_active"]:
            if field not in payload:
                continue
            updates.append(f"{field} = :{field}")
            params[field] = payload[field]

        if not updates:
            return self.get_category(category_id)

        row = self.db.execute(
            text(
                f"""
                UPDATE categories
                SET {", ".join(updates)}
                WHERE id = :category_id
                RETURNING id, name, color, icon, is_custom, is_active
                """
            ),
            params,
        ).mappings().first()
        self.db.commit()
        return dict(row) if row else None

    def delete_category(self, category_id: int):
        self.db.execute(
            text("UPDATE categories SET is_active = FALSE WHERE id = :category_id"),
            {"category_id": category_id},
        )
        self.db.commit()

    def get_category(self, category_id: int):
        row = self.db.execute(
            text(
                """
                SELECT id, name, color, icon, is_custom, is_active
                FROM categories
                WHERE id = :category_id
                """
            ),
            {"category_id": category_id},
        ).mappings().first()
        return dict(row) if row else None

    def list_labels(self):
        rows = self.db.execute(
            text("SELECT id, name, color FROM labels ORDER BY name ASC")
        ).mappings()
        return [dict(row) for row in rows]

    def create_label(self, name: str, color: str):
        row = self.db.execute(
            text(
                """
                INSERT INTO labels (name, color)
                VALUES (:name, :color)
                RETURNING id, name, color
                """
            ),
            {"name": name.strip().upper(), "color": color},
        ).mappings().one()
        self.db.commit()
        return dict(row)

    def delete_label(self, label_id: int):
        self.db.execute(text("DELETE FROM labels WHERE id = :label_id"), {"label_id": label_id})
        self.db.commit()

    def get_options(self):
        staff_rows = self.db.execute(
            text(
                """
                SELECT DISTINCT staff_assigned
                FROM tickets
                WHERE staff_assigned IS NOT NULL AND staff_assigned <> ''
                ORDER BY staff_assigned
                """
            )
        )
        requester_rows = self.db.execute(
            text(
                """
                SELECT DISTINCT requester
                FROM tickets
                WHERE requester IS NOT NULL AND requester <> ''
                ORDER BY requester
                """
            )
        )

        return {
            "categories": self.list_categories(active_only=True),
            "labels": self.list_labels(),
            "staff": [row[0] for row in staff_rows],
            "requesters": [row[0] for row in requester_rows],
            "users": AuthService().list_users(),
        }
