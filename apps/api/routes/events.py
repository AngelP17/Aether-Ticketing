from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.services.event_service import EventService

router = APIRouter()


@router.get("/{ticket_id}")
def get_ticket_events(ticket_id: str, db: Session = Depends(get_db)):
    service = EventService(db)
    return service.get_ticket_event_stream(ticket_id)
