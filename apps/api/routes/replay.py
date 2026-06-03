from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user
from apps.api.services.replay_service import ReplayService as ReplayService

router = APIRouter()


@router.get("/{ticket_id}")
def get_replay(ticket_id: str, db: Session = Depends(get_db), _user: dict[str, Any] = Depends(get_current_user)) -> Any:
    try:
        replay = ReplayService(db).get_replay(ticket_id)
    except Exception:  # defensive: never 500 on replay surface, return precise partial state
        # rollback best effort
        try:
            db.rollback()
        except Exception:
            pass
        # Return usable payload so UI can render "partial / no history" instead of hard fail
        return {
            "ticket_id": ticket_id,
            "latest_decision": None,
            "decision_history": [],
            "events": [],
            "operator_feedback": [],
            "similar_cases": [],
            "error": "replay_subsystem_unavailable",
            "detail": "Some replay sections are temporarily unavailable; core ticket context may still render.",
        }
    if replay is None:
        raise HTTPException(status_code=404, detail="Replay not found")
    return replay
