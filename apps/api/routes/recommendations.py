from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from apps.api.deps import get_db
from apps.api.services.recommendation_service import RecommendationService

router = APIRouter()


class AcceptRequest(BaseModel):
    note: str | None = None


class RejectRequest(BaseModel):
    reason: str | None = None


class OverrideRequest(BaseModel):
    override_note: str
    override_priority: float | None = None


@router.post("/{recommendation_id}/accept")
def accept_recommendation(
    recommendation_id: int,
    body: AcceptRequest,
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    result = service.accept_recommendation(recommendation_id, body.note)
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result


@router.post("/{recommendation_id}/reject")
def reject_recommendation(
    recommendation_id: int,
    body: RejectRequest,
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    result = service.reject_recommendation(recommendation_id, body.reason)
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result


@router.post("/{recommendation_id}/override")
def override_recommendation(
    recommendation_id: int,
    body: OverrideRequest,
    db: Session = Depends(get_db),
):
    service = RecommendationService(db)
    result = service.override_recommendation(
        recommendation_id, body.override_note, body.override_priority
    )
    if not result:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return result
