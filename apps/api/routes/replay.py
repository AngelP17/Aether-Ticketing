from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.replay_service import ReplayService

router = APIRouter()


@router.get("/{ticket_id}")
def get_replay(ticket_id: str, db: Session = Depends(get_db)) -> Any:
    replay = ReplayService(db).get_replay(ticket_id)
    if replay is None:
        raise HTTPException(status_code=404, detail="Replay not found")
    return replay
