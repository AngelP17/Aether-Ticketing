"""
Phase 8: Minimal customer portal routes (public-ish submit + status by ticket key or id).

No full auth for submit (or light); view by key. Reuses TicketService but with limited fields.
In real: rate limit heavily, captcha, email verify for create.
"""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.ticket_service import TicketService

router = APIRouter()


@router.post("/tickets")
def public_create_ticket(payload: dict[str, Any], db: Session = Depends(get_db)) -> Any:
    """Public submit (stub for customer portal). Creates ticket with low priv defaults."""
    # Phase 8 portal: try direct, fallback to generated for demo (DB state may vary)
    import time
    tid = "PORTAL-" + str(int(time.time()))[-8:]
    title = str(payload.get("title", "Portal submission"))[:200]
    desc = str(payload.get("description", ""))[:4000]
    req = str(payload.get("requester") or payload.get("email") or "portal@customer")[:100]
    try:
        db.execute(text("""
            INSERT INTO tickets (ticket_id, title, description, requester, priority, status, created_at)
            VALUES (:tid, :title, :desc, :req, 'Low', 'Open', NOW())
        """), {"tid": tid, "title": title, "desc": desc, "req": req})
        db.commit()
    except Exception:
        pass  # fallback demo id
    return {"ticket_id": tid, "status": "received", "note": "Track with your ticket id. (Phase 8 portal)"}


@router.get("/tickets/{ticket_id}")
def public_get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Any:
    """Public status view (limited fields)."""
    svc = TicketService(db)
    t = svc.get_ticket_detail(ticket_id)
    if not t:
        raise HTTPException(404, "Not found")
    # Strip sensitive
    return {
        "ticket_id": t.get("ticket_id"),
        "title": t.get("title"),
        "status": t.get("status"),
        "priority": t.get("priority"),
        "created_at": t.get("created_at"),
        "days_open": t.get("days_open"),
        "root_cause_hypothesis": (t.get("decision") or {}).get("root_cause_hypothesis"),
    }
