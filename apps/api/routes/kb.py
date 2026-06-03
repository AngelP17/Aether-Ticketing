"""Phase 8 KB (articles) admin + search (linked to root causes)."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_admin

router = APIRouter()

@router.get("")
def list_articles(db: Session = Depends(get_db), q: str = Query(""), _user: dict = Depends(get_current_user)) -> Any:
    rows = db.execute(text("SELECT id, title, root_cause_class FROM articles WHERE title ILIKE :q ORDER BY created_at DESC LIMIT 50"), {"q": f"%{q}%"}).mappings()
    return [dict(r) for r in rows]

@router.post("", dependencies=[Depends(require_admin)])
def create_article(body: dict[str, Any], db: Session = Depends(get_db)) -> Any:
    res = db.execute(text("INSERT INTO articles (title, body, root_cause_class, author_id) VALUES (:t, :b, :r, :a) RETURNING id"), {
        "t": body.get("title"), "b": body.get("body"), "r": body.get("root_cause_class"), "a": body.get("author_id")
    }).mappings().first()
    db.commit()
    return {"id": res["id"] if res else None}
