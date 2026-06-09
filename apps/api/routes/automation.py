"""Automation rules routes (admin + trigger)."""
from typing import Any, Dict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_admin, require_ticket_write
from apps.api.services.automation_service import AutomationService

router = APIRouter(prefix="/automation", tags=["automation"])

@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    return AutomationService(db).list_rules()

@router.post("/rules", dependencies=[Depends(require_admin)])
def create_rule(body: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    return AutomationService(db).create_rule(body)

@router.post("/trigger/{trigger}")
def trigger_rules(trigger: str, ticket: Dict[str, Any], db: Session = Depends(get_db), _user: Dict[str, Any] = Depends(require_ticket_write)) -> Any:
    count = AutomationService(db).evaluate_and_execute(trigger, ticket)
    return {"executed": count}
