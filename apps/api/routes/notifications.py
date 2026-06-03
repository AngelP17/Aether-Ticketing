from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user

router = APIRouter()


@router.get("")
def list_notifications(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
) -> Any:
    """List notifications for current user (Phase 8 wired; creation via events/email)."""
    user = current_user.get("username", "unknown")
    where = "user_id = :user"
    params: dict[str, Any] = {"user": user, "limit": limit}
    if unread_only:
        where += " AND is_read = FALSE"
    rows = db.execute(
        text(
            f"""
            SELECT id, user_id, ticket_id, type, title, body, payload_json, is_read, created_at
            FROM notifications
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings()
    return [dict(r) for r in rows]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    """Mark a notification read."""
    user = current_user.get("username", "unknown")
    db.execute(
        text(
            """
            UPDATE notifications SET is_read = TRUE
            WHERE id = :nid AND user_id = :user
            """
        ),
        {"nid": notification_id, "user": user},
    )
    db.commit()
    return {"status": "ok"}


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    """Quick unread count for bell/polling. Lightweight alternative to full list."""
    user = current_user.get("username", "unknown")
    row = db.execute(
        text(
            "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id = :user AND is_read = FALSE"
        ),
        {"user": user},
    ).mappings().fetchone()
    return {"unread": row["cnt"] if row else 0}
