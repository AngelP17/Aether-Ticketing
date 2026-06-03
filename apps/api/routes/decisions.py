from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.decision import DecisionResponse
from apps.api.security import get_current_user, require_ticket_write
from apps.api.services.decision_service import DecisionService as DecisionService

router = APIRouter()


@router.get("/{ticket_id}", response_model=DecisionResponse)
def get_decision(ticket_id: str, db: Session = Depends(get_db), _user: dict[str, Any] = Depends(get_current_user)) -> Any:
    service = DecisionService(db)
    decision = service.get_latest_decision(ticket_id)
    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")
    return decision


@router.post("/recompute/{ticket_id}", response_model=DecisionResponse)
def recompute_decision(
    ticket_id: str,
    db: Session = Depends(get_db),
    _user: dict[str, str] = Depends(require_ticket_write),
) -> Any:
    service = DecisionService(db)
    decision = service.recompute_decision(ticket_id)
    if decision is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return decision
