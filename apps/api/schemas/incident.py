from typing import Any

from pydantic import BaseModel, Field


class IncidentDetailResponse(BaseModel):
    incident: dict[str, Any] = Field(default_factory=dict)
    tickets: list[dict[str, Any]] = Field(default_factory=list)
    common_cause: str | None = None
    recommended_action: str | None = None
    graph_evidence: dict[str, Any] | None = None

    model_config = {"from_attributes": True}
