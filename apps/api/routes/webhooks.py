"""Webhook admin routes (CRUD for OSS integrations config)."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_admin

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.get("", dependencies=[Depends(require_admin)])
def list_webhooks(db: Session = Depends(get_db)) -> Any:
    rows = db.execute(text("SELECT id, url, events, active, created_at FROM webhooks ORDER BY created_at DESC")).mappings()
    return [dict(r) for r in rows]

@router.post("", dependencies=[Depends(require_admin)])
def create_webhook(body: dict[str, Any], db: Session = Depends(get_db)) -> Any:
    res = db.execute(text("INSERT INTO webhooks (url, secret, events, active) VALUES (:u, :s, :e, :a) RETURNING id"), {
        "u": body.get("url"),
        "s": body.get("secret"),
        "e": body.get("events") or ["*"],
        "a": body.get("active", True),
    }).mappings().first()
    db.commit()
    return {"id": res["id"]}

@router.delete("/{wid}", dependencies=[Depends(require_admin)])
def delete_webhook(wid: int, db: Session = Depends(get_db)) -> Any:
    db.execute(text("DELETE FROM webhooks WHERE id = :id"), {"id": wid})
    db.commit()
    return {"ok": True}
