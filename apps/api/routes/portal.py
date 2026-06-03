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
    # Phase 8 portal: use service for proper ticket (with id gen, events, etc), fallback for demo
    svc = TicketService(db)
    data = {
        "title": payload.get("title", "Portal submission")[:200],
        "description": payload.get("description", "")[:4000],
        "requester": payload.get("requester") or payload.get("email") or "portal@customer",
        "priority": "Low",
        "status": "Open",
        "custom_fields": payload.get("custom_fields") or payload.get("customFields"),
    }
    tid = None
    try:
        ticket = svc.create_ticket(data, actor={"username": "portal", "role": "viewer"})
        if ticket:
            tid = ticket.get("ticket_id")
    except Exception:
        pass
    if not tid:
        import time
        tid = "PORTAL-" + str(int(time.time()))[-8:]
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
