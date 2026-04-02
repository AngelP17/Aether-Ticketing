from email.utils import quote

from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.event_service import EventService


ALLOWED_ATTACHMENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "application/pdf",
    "text/plain",
}
MAX_ATTACHMENT_BYTES = 5 * 1024 * 1024


class AttachmentService:
    def __init__(self, db: Session):
        self.db = db
        self.events = EventService(db)

    def list_attachments(self, ticket_id: str):
        rows = self.db.execute(
            text(
                """
                SELECT
                    id,
                    original_name,
                    mime_type,
                    file_size,
                    created_at,
                    uploaded_by,
                    comment_id
                FROM ticket_attachments
                WHERE ticket_id = :ticket_id
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings()
        return [
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
            for row in rows
        ]

    async def upload_attachment(
        self,
        ticket_id: str,
        file: UploadFile,
        actor: dict[str, str],
        comment_id: int | None = None,
    ):
        if file.content_type not in ALLOWED_ATTACHMENT_TYPES:
            raise ValueError("File type not allowed. Accepted: images, PDF, text")

        file_data = await file.read()
        if len(file_data) > MAX_ATTACHMENT_BYTES:
            raise ValueError("File too large (max 5MB)")

        ticket_row = self.db.execute(
            text("SELECT id FROM tickets WHERE ticket_id = :ticket_id"),
            {"ticket_id": ticket_id},
        ).mappings().first()
        if ticket_row is None:
            return None

        if comment_id is not None:
            comment = self.db.execute(
                text(
                    """
                    SELECT id
                    FROM ticket_comments
                    WHERE id = :comment_id AND ticket_id = :ticket_id
                    """
                ),
                {"comment_id": comment_id, "ticket_id": ticket_id},
            ).mappings().first()
            if comment is None:
                raise LookupError("Comment not found for attachment upload")

        inserted = self.db.execute(
            text(
                """
                INSERT INTO ticket_attachments (
                    ticket_id,
                    comment_id,
                    filename,
                    original_name,
                    mime_type,
                    file_data,
                    file_size,
                    uploaded_by
                )
                VALUES (
                    :ticket_id,
                    :comment_id,
                    :filename,
                    :original_name,
                    :mime_type,
                    :file_data,
                    :file_size,
                    :uploaded_by
                )
                RETURNING
                    id,
                    original_name,
                    mime_type,
                    file_size,
                    created_at,
                    uploaded_by,
                    comment_id
                """
            ),
            {
                "ticket_id": ticket_id,
                "comment_id": comment_id,
                "filename": file.filename,
                "original_name": file.filename,
                "mime_type": file.content_type,
                "file_data": file_data,
                "file_size": len(file_data),
                "uploaded_by": actor["username"],
            },
        ).mappings().one()

        self.events.record_ticket_event(
            ticket_pk=int(ticket_row["id"]),
            event_type="attachment_uploaded",
            actor_id=actor["username"],
            payload={
                "attachment_id": int(inserted["id"]),
                "original_name": file.filename,
                "comment_id": comment_id,
            },
        )
        self.db.commit()

        return {
            "id": inserted["id"],
            "original_name": inserted["original_name"],
            "mime_type": inserted["mime_type"],
            "file_size": inserted["file_size"],
            "created_at": inserted["created_at"],
            "uploaded_by": inserted["uploaded_by"],
            "comment_id": inserted["comment_id"],
            "url": f"/api/attachments/{inserted['id']}",
        }

    def get_attachment(self, attachment_id: int):
        row = self.db.execute(
            text(
                """
                SELECT id, original_name, mime_type, file_data
                FROM ticket_attachments
                WHERE id = :attachment_id
                """
            ),
            {"attachment_id": attachment_id},
        ).mappings().first()
        if row is None:
            return None
        return {
            "id": row["id"],
            "original_name": row["original_name"],
            "mime_type": row["mime_type"],
            "file_data": bytes(row["file_data"]),
            "content_disposition": f'inline; filename="{quote(row["original_name"])}"',
        }

    def delete_attachment(self, attachment_id: int, actor: dict[str, str]):
        row = self.db.execute(
            text(
                """
                SELECT id, ticket_id, uploaded_by
                FROM ticket_attachments
                WHERE id = :attachment_id
                """
            ),
            {"attachment_id": attachment_id},
        ).mappings().first()
        if row is None:
            return False
        if actor["role"] not in {"admin", "agent"}:
            raise PermissionError("Insufficient privileges")

        ticket_row = self.db.execute(
            text("SELECT id FROM tickets WHERE ticket_id = :ticket_id"),
            {"ticket_id": row["ticket_id"]},
        ).mappings().first()

        self.db.execute(
            text("DELETE FROM ticket_attachments WHERE id = :attachment_id"),
            {"attachment_id": attachment_id},
        )
        if ticket_row is not None:
            self.events.record_ticket_event(
                ticket_pk=int(ticket_row["id"]),
                event_type="attachment_deleted",
                actor_id=actor["username"],
                payload={"attachment_id": attachment_id},
            )
        self.db.commit()
        return True
