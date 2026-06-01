from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.accuracy_service import AccuracyService
from apps.api.services.metrics_service import MetricsService
from infrastructure.logging.feedback_learner import FeedbackLearner

router = APIRouter()


@router.get("/", include_in_schema=False)
@router.get("")
def get_metrics(db: Session = Depends(get_db)) -> Any:
    service = MetricsService(db)
    return service.get_queue_metrics()


@router.get("/accuracy")
def get_accuracy_metrics(
    db: Session = Depends(get_db),
    days: int = Query(default=7, ge=1, le=90),
) -> Any:
    service = AccuracyService(db)
    return service.get_all_accuracy_metrics(days)


@router.get("/feedback/summary")
def get_feedback_summary(db: Session = Depends(get_db)) -> Any:
    learner = FeedbackLearner(db)
    return learner.get_pattern_summary()
