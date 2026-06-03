from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.replay_service import ReplayService as ReplayService

router = APIRouter()


@router.get("/{ticket_id}")
def get_replay(ticket_id: str, db: Session = Depends(get_db)) -> Any:
    try:
        replay = ReplayService(db).get_replay(ticket_id)
    except SQLAlchemyError as exc:
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=503,
            detail="Replay data is temporarily unavailable",
        ) from exc
    if replay is None:
        raise HTTPException(status_code=404, detail="Replay not found")
    return replay
