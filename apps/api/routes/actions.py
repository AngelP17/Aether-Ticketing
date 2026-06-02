"""
Action execution endpoints: /api/actions

POST /api/actions/recommendations/{id}/apply   - apply a recommendation
GET  /api/actions/{id}                         - inspect a single action run

Every apply creates a real action_runs row, writes operator_feedback and a
ticket_events row, and applies the safe workflow mutation matching the
recommendation's action_type. Mutations are dispatched by ActionService —
see apps/api/services/action_service.py.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_ticket_write
from apps.api.services.action_service import ActionService as ActionService

router = APIRouter()


class ApplyRequest(BaseModel):
    action_type: str | None = Field(
        default=None,
        description="Override the recommendation's action_type (e.g. assign_team vs escalate).",
    )
    override_priority: float | None = Field(
        default=None,
        description="Optional new priority score to record with this action.",
    )
    confirm: bool = Field(
        default=False,
        description="Required true for any action that resolves the ticket (auto_resolve).",
    )
    note: str | None = Field(default=None, max_length=500)


def _serialize_result(result: Any) -> dict[str, Any]:
    return {
        "recommendation_id": result.recommendation_id,
        "action_run": result.action_run,
        "event_id": result.event_id,
        "ticket_state": result.ticket_state,
        "rollback_available": result.rollback_available,
        "rollback_payload": result.rollback_payload,
        "feedback": result.feedback,
    }


@router.post("/recommendations/{recommendation_id}/apply")
def apply_recommendation(
    recommendation_id: int,
    body: ApplyRequest,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(require_ticket_write),
) -> Any:
    service = ActionService(db)
    try:
        result = service.apply_recommendation(
            recommendation_id=recommendation_id,
            action_type_override=body.action_type,
            override_priority=body.override_priority,
            confirm_auto_resolve=body.confirm,
            note=body.note,
            operator_id=current_user.get("username", "api-user"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return _serialize_result(result)


@router.get("/{action_run_id}")
def get_action_run(
    action_run_id: int,
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    service = ActionService(db)
    action_run = service.get_action_run(action_run_id)
    if action_run is None:
        raise HTTPException(status_code=404, detail="Action run not found")
    return action_run
