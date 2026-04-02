from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TicketResponse(BaseModel):
    ticket_id: str
    title: str
    status: str
    priority_raw: str
    priority_score: Optional[float] = None
    root_cause_hypothesis: Optional[str] = None
    confidence_score: Optional[float] = None
    site: Optional[str] = None
    assignee: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    resolution_notes: Optional[str] = None
    requester: Optional[str] = None
    created_at: datetime
    days_open: int
    incident_id: Optional[str] = None

    model_config = {"from_attributes": True}


class TicketDetailResponse(BaseModel):
    ticket: dict
    decision: Optional[dict] = None
    recommendations: list[dict] = Field(default_factory=list)
    similar_cases: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    linked_incident: Optional[dict] = None

    model_config = {"from_attributes": True}
