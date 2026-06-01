from typing import Any
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.event_service import EventService


class CommentService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = EventService(db)

    def list_comments(self, ticket_id: str) -> Any:
        comment_rows = self.db.execute(
            text(
                """
                SELECT
                    id,
                    ticket_id,
                    author_username,
                    author_display_name,
                    body,
                    created_at,
                    updated_at
                FROM ticket_comments
                WHERE ticket_id = :ticket_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings()
        comments = [dict(row) for row in comment_rows]
        if not comments:
            return []

        attachments = self.db.execute(
            text(
                """
                SELECT
                    id,
                    comment_id,
                    original_name,
                    mime_type,
                    file_size,
                    created_at,
                    uploaded_by
                FROM ticket_attachments
                WHERE ticket_id = :ticket_id AND comment_id IS NOT NULL
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings()

        attachments_by_comment: dict[int, list[dict[str, Any]]] = {}
        for row in attachments:
            comment_id = int(row["comment_id"])
            attachments_by_comment.setdefault(comment_id, []).append(
                {
                    "id": row["id"],
                    "original_name": row["original_name"],
                    "mime_type": row["mime_type"],
                    "file_size": row["file_size"],
                    "created_at": row["created_at"],
                    "uploaded_by": row["uploaded_by"],
                    "comment_id": row["comment_id"],
                    "url": f"/api/attachments/{row['id']}",
                }
            )

        return [
            {
                **comment,
                "attachments": attachments_by_comment.get(int(comment["id"]), []),
            }
            for comment in comments
        ]

    def create_comment(self, ticket_id: str, body: str, actor: dict[str, Any]) -> Any:
        ticket_row = self.db.execute(
            text("SELECT id FROM tickets WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id},
        ).mappings().first()
        if ticket_row is None:
            return None

        comment = self.db.execute(
            text(
                """
                INSERT INTO ticket_comments (
                    ticket_id,
                    author_username,
                    author_display_name,
                    body
                )
                VALUES (:ticket_id, :author_username, :author_display_name, :body)
                RETURNING
                    id,
                    ticket_id,
                    author_username,
                    author_display_name,
                    body,
                    created_at,
                    updated_at
                """
            ),
            {
                "ticket_id": ticket_id,
                "author_username": actor["username"],
                "author_display_name": actor["display_name"],
                "body": body.strip(),
            },
        ).mappings().one()

        self.events.record_ticket_event(
            ticket_pk=int(ticket_row["id"]),
            event_type="comment_added",
            actor_id=actor["username"],
            payload={"comment_id": int(comment["id"]), "body": body.strip()},
        )
        self.db.commit()

        return {
            **dict(comment),
            "attachments": [],
        }

    def update_comment(self, ticket_id: str, comment_id: int, body: str, actor: dict[str, Any]) -> Any:
        existing = self.db.execute(
            text(
                """
                SELECT id, author_username
                FROM ticket_comments
                WHERE id = :comment_id AND ticket_id = :ticket_id
                """
            ),
            {"comment_id": comment_id, "ticket_id": ticket_id},
        ).mappings().first()
        if existing is None:
            return None
        if actor["role"] != "admin" and existing["author_username"] != actor["username"]:
            raise PermissionError("Only the author or an admin can edit this comment")

        updated = self.db.execute(
            text(
                """
                UPDATE ticket_comments
                SET body = :body, updated_at = CURRENT_TIMESTAMP
                WHERE id = :comment_id AND ticket_id = :ticket_id
                RETURNING
                    id,
                    ticket_id,
                    author_username,
                    author_display_name,
                    body,
                    created_at,
                    updated_at
                """
            ),
            {"comment_id": comment_id, "ticket_id": ticket_id, "body": body.strip()},
        ).mappings().first()
        self.db.commit()
        return dict(updated) if updated else None

    def delete_comment(self, ticket_id: str, comment_id: int, actor: dict[str, Any]) -> Any:
        existing = self.db.execute(
            text(
                """
                SELECT id, author_username
                FROM ticket_comments
                WHERE id = :comment_id AND ticket_id = :ticket_id
                """
            ),
            {"comment_id": comment_id, "ticket_id": ticket_id},
        ).mappings().first()
        if existing is None:
            return False
        if actor["role"] != "admin" and existing["author_username"] != actor["username"]:
            raise PermissionError("Only the author or an admin can delete this comment")

        self.db.execute(
            text("DELETE FROM ticket_comments WHERE id = :comment_id"),
            {"comment_id": comment_id},
        )
        self.db.commit()
        return True
