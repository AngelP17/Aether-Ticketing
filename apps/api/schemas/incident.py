from typing import Any

from pydantic import BaseModel


class IncidentResponse(BaseModel):
    id: str
    title: str
    status: str
    root_cause_hypothesis: str
    ticket_count: int
    confidence: float
    business_impact_score: float
    opened_at: str

    model_config = {"from_attributes": True}


class IncidentDetailResponse(BaseModel):
    incident: dict[str, Any]
    tickets: list[dict[str, Any]]
    common_cause: str
    recommended_action: str

    model_config = {"from_attributes": True}
