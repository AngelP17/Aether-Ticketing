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
        category = self.get_category(category_id)
        if category is None:
            return False

        self.db.execute(
            text(
                """
                UPDATE tickets
                SET
                    request_type = COALESCE(NULLIF(request_type, ''), :category_name),
                    category_id = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE category_id = :category_id
                """
            ),
            {"category_id": category_id, "category_name": category["name"]},
        )
        self.db.execute(
            text("DELETE FROM categories WHERE id = :category_id"),
            {"category_id": category_id},
        )
        self.db.commit()
        return True

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

    def create_assignee(self, display_name: str):
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("Display name is required")

        existing = self.db.execute(
            text(
                """
                SELECT id
                FROM assignees
                WHERE LOWER(display_name) = LOWER(:display_name)
                """
            ),
            {"display_name": normalized_name},
        ).mappings().first()

        if existing:
            row = self.db.execute(
                text(
                    """
                    UPDATE assignees
                    SET display_name = :display_name, is_active = TRUE
                    WHERE id = :assignee_id
                    RETURNING id, display_name, is_active
                    """
                ),
                {"display_name": normalized_name, "assignee_id": existing["id"]},
            ).mappings().one()
        else:
            row = self.db.execute(
                text(
                    """
                    INSERT INTO assignees (display_name, is_active)
                    VALUES (:display_name, TRUE)
                    RETURNING id, display_name, is_active
                    """
                ),
                {"display_name": normalized_name},
            ).mappings().one()

        self.db.commit()
        return dict(row)

    def delete_assignee(self, display_name: str):
        normalized_name = display_name.strip()
        if not normalized_name:
            raise ValueError("Display name is required")

        existing = self.db.execute(
            text(
                """
                SELECT id
                FROM assignees
                WHERE LOWER(display_name) = LOWER(:display_name)
                """
            ),
            {"display_name": normalized_name},
        ).mappings().first()

        if existing:
            self.db.execute(
                text("UPDATE assignees SET is_active = FALSE WHERE id = :assignee_id"),
                {"assignee_id": existing["id"]},
            )
        else:
            self.db.execute(
                text(
                    """
                    INSERT INTO assignees (display_name, is_active)
                    VALUES (:display_name, FALSE)
                    """
                ),
                {"display_name": normalized_name},
            )

        self.db.commit()
        return True

    def _active_assignee_names(self):
        rows = self.db.execute(
            text(
                """
                SELECT display_name
                FROM assignees
                WHERE is_active = TRUE
                ORDER BY display_name ASC
                """
            )
        )
        return [row[0] for row in rows]

    def _inactive_assignee_names(self):
        rows = self.db.execute(
            text(
                """
                SELECT display_name
                FROM assignees
                WHERE is_active = FALSE
                """
            )
        )
        return {row[0].casefold() for row in rows if row[0]}

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
        staff_values = [row[0] for row in staff_rows]
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
        users = AuthService().list_users()
        active_assignees = self._active_assignee_names()
        inactive_assignees = self._inactive_assignee_names()
        assignee_names: list[str] = []

        for name in active_assignees:
            if name and name not in assignee_names:
                assignee_names.append(name)

        for user in users:
            display_name = user["display_name"].strip()
            if user["role"] == "viewer":
                continue
            if display_name.casefold() in inactive_assignees:
                continue
            if display_name not in assignee_names:
                assignee_names.append(display_name)

        for staff_name in staff_values:
            if not staff_name:
                continue
            if staff_name.casefold() in inactive_assignees:
                continue
            if staff_name not in assignee_names:
                assignee_names.append(staff_name)

        return {
            "categories": self.list_categories(active_only=True),
            "labels": self.list_labels(),
            "staff": staff_values,
            "requesters": [row[0] for row in requester_rows],
            "users": users,
            "assignees": assignee_names,
        }
