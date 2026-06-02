from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user, require_ticket_write
from apps.api.services.attachment_service import AttachmentService as AttachmentService

router = APIRouter()


@router.post("/tickets/{ticket_id}/attachments", status_code=201)
async def upload_attachment(
    ticket_id: str,
    file: UploadFile,
    comment_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(require_ticket_write),
) -> Any:
    try:
        attachment = await AttachmentService(db).upload_attachment(
            ticket_id=ticket_id,
            file=file,
            actor=actor,
            comment_id=comment_id,
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    if attachment is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return attachment


@router.get("/tickets/{ticket_id}/attachments")
def list_ticket_attachments(
    ticket_id: str,
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
) -> Any:
    return AttachmentService(db).list_attachments(ticket_id)


@router.get("/attachments/{attachment_id}")
def serve_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
) -> Any:
    attachment = AttachmentService(db).get_attachment(attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return Response(
        content=attachment["file_data"],
        media_type=attachment["mime_type"],
        headers={"Content-Disposition": attachment["content_disposition"]},
    )


@router.delete("/attachments/{attachment_id}")
def delete_attachment(
    attachment_id: int,
    db: Session = Depends(get_db),
    actor: dict[str, Any] = Depends(require_ticket_write),
) -> Any:
    try:
        deleted = AttachmentService(db).delete_attachment(attachment_id, actor)
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    if not deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")
    return {"status": "success"}
