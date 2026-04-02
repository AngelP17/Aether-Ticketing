from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.management import CommentCreateRequest, CommentUpdateRequest
from apps.api.security import get_current_user, require_ticket_write
from apps.api.services.comment_service import CommentService

router = APIRouter()


@router.get("/tickets/{ticket_id}/comments")
def list_comments(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return CommentService(db).list_comments(ticket_id)


@router.post("/tickets/{ticket_id}/comments", status_code=201)
def create_comment(
    ticket_id: str,
    body: CommentCreateRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    if not body.body.strip():
        raise HTTPException(status_code=400, detail="Comment body is required")
    comment = CommentService(db).create_comment(ticket_id, body.body, actor)
    if comment is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return comment


@router.put("/tickets/{ticket_id}/comments/{comment_id}")
def update_comment(
    ticket_id: str,
    comment_id: int,
    body: CommentUpdateRequest,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    try:
        comment = CommentService(db).update_comment(ticket_id, comment_id, body.body, actor)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if comment is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    return comment


@router.delete("/tickets/{ticket_id}/comments/{comment_id}")
def delete_comment(
    ticket_id: str,
    comment_id: int,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_ticket_write),
):
    try:
        deleted = CommentService(db).delete_comment(ticket_id, comment_id, actor)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Comment not found")
    return {"status": "success"}
