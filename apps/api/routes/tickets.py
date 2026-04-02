from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.management import (
    TicketCreateRequest,
    TicketLabelsRequest,
    TicketMoveRequest,
    TicketUpdateRequest,
)
from apps.api.schemas.ticket import TicketResponse, TicketDetailResponse
from apps.api.security import require_ticket_write
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


@router.post("/", status_code=201, include_in_schema=False)
@router.post("", status_code=201)
def create_ticket(
    body: TicketCreateRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    try:
        return TicketService(db).create_ticket(body.model_dump(), actor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.put("/{ticket_id}")
def update_ticket(
    ticket_id: str,
    body: TicketUpdateRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    ticket = TicketService(db).update_ticket(ticket_id, body.model_dump(exclude_unset=True), actor)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket


@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    deleted = TicketService(db).delete_ticket(ticket_id, actor)
    if not deleted:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "success"}


@router.put("/{ticket_id}/labels")
def set_ticket_labels(
    ticket_id: str,
    body: TicketLabelsRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    updated = TicketService(db).set_ticket_labels(ticket_id, body.label_ids, actor)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "success"}


@router.put("/{ticket_id}/move")
def move_ticket(
    ticket_id: str,
    body: TicketMoveRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    try:
        ticket = TicketService(db).move_ticket(ticket_id, body.column, body.status, actor)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket
