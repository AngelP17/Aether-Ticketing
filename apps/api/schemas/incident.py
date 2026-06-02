from typing import Any

from pydantic import BaseModel, Field


class IncidentResponse(BaseModel):
    id: int
    incident_key: str | None = None
    title: str
    status: str
    root_cause_hypothesis: str | None = None
    site_scope: str | None = None
    ticket_count: int
    confidence: float = 0.0
    business_impact_score: float = 0.0
    opened_at: str | None = None
    last_updated_at: str | None = None
    graph_evidence: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class IncidentDetailResponse(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)
    tickets: list[dict[str, Any]] = Field(default_factory=list)
    common_cause: str | None = None
    recommended_action: str | None = None
    graph_evidence: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
