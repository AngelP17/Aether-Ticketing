from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.incident import IncidentDetailResponse
from apps.api.security import get_current_user
from apps.api.services.incident_service import IncidentService as IncidentService

router = APIRouter()


@router.get("/", include_in_schema=False)
@router.get("")
def list_incidents(db: Session = Depends(get_db), _user: dict[str, Any] = Depends(get_current_user)) -> Any:
    service = IncidentService(db)
    return service.list_incidents()


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: int, db: Session = Depends(get_db), _user: dict[str, Any] = Depends(get_current_user)) -> Any:
    service = IncidentService(db)
    incident = service.get_incident_detail(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
