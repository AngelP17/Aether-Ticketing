from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user

router = APIRouter()


@router.get("")
def list_audit(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    ticket_id: str | None = Query(None),
) -> Any:
    """Audit log (events + decisions + feedback). Wired for Phase 2/5."""
    params: dict[str, Any] = {"limit": limit}
    where = ""
    if ticket_id:
        where = "WHERE t.ticket_id = :tid"
        params["tid"] = ticket_id
    rows = db.execute(
        text(
            f"""
            SELECT
                e.event_ts as ts,
                e.event_type as type,
                e.actor_id as actor,
                e.payload_json as payload,
                t.ticket_id
            FROM ticket_events e
            JOIN tickets t ON t.id = e.ticket_id
            {where}
            ORDER BY e.event_ts DESC
            LIMIT :limit
            """
        ),
        params,
    ).mappings()
    return [dict(r) for r in rows]
