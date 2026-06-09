from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user
from apps.api.services.accuracy_service import AccuracyService as AccuracyService
from apps.api.services.metrics_service import MetricsService as MetricsService
from infrastructure.logging.feedback_learner import FeedbackLearner

router = APIRouter()


@router.get("/", include_in_schema=False)
@router.get("")
def get_metrics(db: Session = Depends(get_db), _user: dict[str, Any] = Depends(get_current_user)) -> Any:
    service = MetricsService(db)
    return service.get_queue_metrics()


@router.get("/accuracy")
def get_accuracy_metrics(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
    _user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    service = AccuracyService(db)
    return service.get_all_accuracy_metrics(days)


@router.get("/feedback/summary")
def get_feedback_summary(
    db: Session = Depends(get_db),
    _user: dict[str, Any] = Depends(get_current_user),
) -> Any:
    learner = FeedbackLearner(db)
    return learner.get_pattern_summary()
