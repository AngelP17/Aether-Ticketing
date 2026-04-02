from datetime import datetime
from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    id: int | None = None
    rank: int
    action_type: str
    action_label: str
    rationale: str
    risk_level: str
    expected_benefit: str | None = None
    confidence: float
    recommended_runbook_id: str | None = None
    status: str | None = None

    model_config = {"from_attributes": True}


class DecisionResponse(BaseModel):
    id: int
    ticket_id: str
    priority_score: float
    severity_score: float
    urgency_score: float
    business_impact_score: float
    sla_risk_score: float
    recurrence_score: float
    dependency_criticality_score: float
    actionability_score: float
    uncertainty_penalty: float
    root_cause_hypothesis: str
    confidence_score: float
    decision_ts: datetime
    recommendations: list[RecommendationResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
