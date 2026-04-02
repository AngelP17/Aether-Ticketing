from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.metrics_service import MetricsService

router = APIRouter()


@router.get("/", include_in_schema=False)
@router.get("")
def get_metrics(db: Session = Depends(get_db)):
    service = MetricsService(db)
    return service.get_queue_metrics()
