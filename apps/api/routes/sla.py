"""SLA routes (admin + dashboard + per ticket). In-house implementation."""
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_admin
from apps.api.services.sla_service import SlaService

from typing import Dict

router = APIRouter(prefix="/sla", tags=["sla"])

@router.get("/policies")
def list_policies(db: Session = Depends(get_db), _user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    return SlaService(db).list_policies()

@router.post("/policies", dependencies=[Depends(require_admin)])
def create_policy(body: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    return SlaService(db).create_policy(body)

@router.put("/policies/{policy_id}", dependencies=[Depends(require_admin)])
def update_policy(policy_id: int, body: Dict[str, Any], db: Session = Depends(get_db)) -> Any:
    ok = SlaService(db).update_policy(policy_id, body)
    if not ok:
        raise HTTPException(404, "Not found")
    return {"ok": True}

@router.get("/dashboard")
def sla_dashboard(db: Session = Depends(get_db), _user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    return SlaService(db).get_dashboard()

@router.get("/ticket/{ticket_id}")
def sla_for_ticket(ticket_id: str, db: Session = Depends(get_db), _user: Dict[str, Any] = Depends(get_current_user)) -> Any:
    return SlaService(db).get_sla_status(ticket_id)
