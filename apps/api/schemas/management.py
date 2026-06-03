from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "viewer"
    display_name: str | None = None


class UserUpdateRequest(BaseModel):
    password: str | None = None
    role: str | None = None
    display_name: str | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class CategoryCreateRequest(BaseModel):
    name: str
    color: str = "#6366f1"
    icon: str = "fa-tag"


class CategoryUpdateRequest(BaseModel):
    name: str | None = None
    color: str | None = None
    icon: str | None = None
    is_active: bool | None = None


class LabelCreateRequest(BaseModel):
    name: str
    color: str = "#3b82f6"


class AssigneeCreateRequest(BaseModel):
    display_name: str


class TicketCreateRequest(BaseModel):
    title: str
    status: str = "Open"
    priority: str = "Low"
    request_type: str | None = None
    category_id: int | None = None
    staff_assigned: str | None = None
    requester: str | None = None
    description: str | None = None
    resolution_notes: str | None = None
    site_id: str | None = None
    label_ids: list[int] = Field(default_factory=list)
    custom_fields: dict[str, Any] | None = None  # for OSS hybrid forms/integrations (Jira parity, device attrs, etc.)


class TicketUpdateRequest(BaseModel):
    title: str | None = None
    status: str | None = None
    priority: str | None = None
    request_type: str | None = None
    category_id: int | None = None
    staff_assigned: str | None = None
    requester: str | None = None
    description: str | None = None
    resolution_notes: str | None = None
    site_id: str | None = None
    label_ids: list[int] | None = None
    custom_fields: dict[str, Any] | None = None  # for OSS hybrid forms/integrations (Jira parity, device attrs, etc.)


class TicketLabelsRequest(BaseModel):
    label_ids: list[int] = Field(default_factory=list)


class TicketMoveRequest(BaseModel):
    column: str | None = None
    status: str | None = None


class CommentCreateRequest(BaseModel):
    body: str


class CommentUpdateRequest(BaseModel):
    body: str


class AttachmentResponse(BaseModel):
    id: int
    original_name: str
    mime_type: str
    file_size: int
    created_at: datetime | None = None
    uploaded_by: str | None = None
    comment_id: int | None = None
    url: str


class CommentResponse(BaseModel):
    id: int
    ticket_id: str
    author_username: str
    author_display_name: str
    body: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    attachments: list[AttachmentResponse] = Field(default_factory=list)
