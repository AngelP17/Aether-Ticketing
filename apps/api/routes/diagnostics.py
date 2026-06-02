from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import require_admin
from apps.api.services.ticket_service import TicketService

router = APIRouter()


@router.get("/live")
def live_diagnostics(
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_admin),
) -> dict[str, Any]:
    """Expose non-secret live DB compatibility checks for production triage."""
    return {
        "status": "ok",
        "tables": {
            "tickets": _table_snapshot(db, "tickets"),
            "categories": _table_snapshot(db, "categories"),
            "incidents": _table_snapshot(db, "incidents"),
            "decision_records": _table_snapshot(db, "decision_records"),
        },
        "queries": {
            "ticket_count": _scalar_check(db, "SELECT COUNT(*) AS value FROM tickets"),
            "ticket_probe": _ticket_probe(db),
            "ticket_feed_limits": _ticket_feed_limits(db),
        },
    }


def _table_snapshot(db: Session, table_name: str) -> dict[str, Any]:
    try:
        rows = list(
            db.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table_name
                    ORDER BY ordinal_position
                    """
                ),
                {"table_name": table_name},
            )
        )
    except Exception as exc:  # noqa: BLE001
        return {"exists": False, "columns": [], "error": _public_error(exc)}

    columns = [str(row[0]) for row in rows]
    return {"exists": bool(columns), "columns": columns}


def _scalar_check(db: Session, sql: str) -> dict[str, Any]:
    try:
        value = db.execute(text(sql)).scalar()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _public_error(exc)}
    return {"ok": True, "value": int(value or 0)}


def _ticket_probe(db: Session) -> dict[str, Any]:
    try:
        row = (
            db.execute(
                text(
                    """
                    SELECT
                        ticket_id,
                        title,
                        status,
                        priority,
                        request_type,
                        staff_assigned,
                        requester,
                        date_opened,
                        created_at
                    FROM tickets
                    ORDER BY date_opened DESC NULLS LAST, id DESC
                    LIMIT 1
                    """
                )
            )
            .mappings()
            .first()
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": _public_error(exc)}

    if not row:
        return {"ok": True, "row_present": False}
    return {
        "ok": True,
        "row_present": True,
        "fields_present": sorted([key for key, value in dict(row).items() if value is not None]),
    }


def _ticket_feed_limits(db: Session) -> list[dict[str, Any]]:
    service = TicketService(db)
    results: list[dict[str, Any]] = []
    for limit in [1, 3, 5, 10, 20, 40, 80, 160, 200]:
        try:
            tickets = service.list_tickets(limit=limit)
        except Exception as exc:  # noqa: BLE001
            results.append({"limit": limit, "ok": False, "error": _public_error(exc)})
            continue
        results.append(
            {
                "limit": limit,
                "ok": True,
                "count": len(tickets),
                "first_ticket_id": tickets[0]["ticket_id"] if tickets else None,
            }
        )
    return results


def _public_error(exc: Exception) -> dict[str, str]:
    return {
        "type": exc.__class__.__name__,
        "message": str(exc)[:500],
    }
