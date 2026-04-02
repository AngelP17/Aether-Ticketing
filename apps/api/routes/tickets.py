from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from apps.api.deps import get_db
from apps.api.schemas.ticket import TicketResponse, TicketDetailResponse
from apps.api.services.ticket_service import TicketService

router = APIRouter()


@router.get("/", response_model=list[TicketResponse], include_in_schema=False)
@router.get("", response_model=list[TicketResponse])
def list_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    assignee: Optional[str] = Query(None),
    ranking: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    service = TicketService(db)
    return service.list_tickets(
        status=status,
        priority=priority,
        category=category,
        assignee=assignee,
        ranking=ranking,
        limit=limit,
        offset=offset,
    )


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    ticket = service.get_ticket_detail(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.get("/{ticket_id}/events")
def get_ticket_events(ticket_id: str, db: Session = Depends(get_db)):
    service = TicketService(db)
    return service.get_ticket_events(ticket_id)
