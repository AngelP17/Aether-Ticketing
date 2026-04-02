from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.incident import IncidentResponse, IncidentDetailResponse
from apps.api.services.incident_service import IncidentService

router = APIRouter()


@router.get("/", response_model=list[IncidentResponse], include_in_schema=False)
@router.get("", response_model=list[IncidentResponse])
def list_incidents(db: Session = Depends(get_db)):
    service = IncidentService(db)
    return service.list_incidents()


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    service = IncidentService(db)
    incident = service.get_incident_detail(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
