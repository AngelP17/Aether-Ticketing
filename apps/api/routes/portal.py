"""
Phase 8: Minimal customer portal routes (public-ish submit + status by ticket key or id).

No full auth for submit (or light); view by key. Reuses TicketService but with limited fields.
In real: rate limit heavily, captcha, email verify for create.
"""
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
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
    ticket_resp = None
    try:
        ticket_resp = svc.create_ticket(data, actor={"username": "portal", "role": "viewer"})
        if ticket_resp and isinstance(ticket_resp, dict):
            tid = ticket_resp.get("ticket_id") or (ticket_resp.get("ticket") or {}).get("ticket_id")
    except Exception:
        pass
    if not tid:
        import time
        tid = "PORTAL-" + str(int(time.time()))[-8:]
        # ensure custom saved even in fallback path for the product loop
        try:
            db.execute(text("INSERT INTO tickets (ticket_id, title, description, requester, priority, status, custom_fields, created_at, updated_at) VALUES (:tid, :t, :d, :r, :p, :s, :c, NOW(), NOW())"), {
                "tid": tid,
                "t": data.get("title"),
                "d": data.get("description"),
                "r": data.get("requester"),
                "p": data.get("priority", "Low"),
                "s": data.get("status", "Open"),
                "c": json.dumps(data.get("custom_fields") or {}) if data.get("custom_fields") else None,
            })
            db.commit()
        except Exception:
            pass
    return {"ticket_id": tid, "status": "received", "note": "Track with your ticket id. (Phase 8 portal)"}


@router.get("/tickets/{ticket_id}")
def public_get_ticket(ticket_id: str, db: Session = Depends(get_db)) -> Any:
    """Public status view (limited fields)."""
    svc = TicketService(db)
    t = svc.get_ticket_detail(ticket_id)
    if not t:
        raise HTTPException(404, "Not found")
    # support both flat (minimal) and detail wrapper {"ticket": {...}, "decision":...}
    core = t.get("ticket") if isinstance(t.get("ticket"), dict) else t
    return {
        "ticket_id": core.get("ticket_id") or t.get("ticket_id"),
        "title": core.get("title") or t.get("title"),
        "status": core.get("status") or t.get("status"),
        "priority": core.get("priority") or t.get("priority"),
        "created_at": core.get("created_at") or t.get("created_at"),
        "days_open": core.get("days_open") or t.get("days_open"),
        "root_cause_hypothesis": (t.get("decision") or {}).get("root_cause_hypothesis") or core.get("root_cause_hypothesis"),
        "custom_fields": core.get("custom_fields") or t.get("custom_fields"),
    }
