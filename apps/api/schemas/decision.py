from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ActionRunResponse(BaseModel):
    id: int
    recommendation_id: int
    action_type: str
    status: str
    risk_level: str | None = None
    requested_by: str | None = None
    approved_by: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    rollback_available: bool = False
    result_json: Any | None = None
    rollback_payload_json: Any | None = None
    operator_note: str | None = None
    ticket_event_id: int | None = None

    model_config = {"from_attributes": True}


class FeedbackResponse(BaseModel):
    id: int
    feedback_type: str
    feedback_note: str | None = None
    operator_id: str | None = None
    feedback_ts: str | None = None

    model_config = {"from_attributes": True}


class RecommendationResponse(BaseModel):
    id: int
    rank: int
    action_type: str
    action_label: str
    rationale: str
    risk_level: str
    expected_benefit: str | None = None
    confidence: float
    recommended_runbook_id: str | None = None
    requires_approval: bool = False
    status: str | None = None
    created_at: str | None = None
    last_feedback: FeedbackResponse | None = None
    latest_action_run: ActionRunResponse | None = None

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
    decision_ts: datetime | str
    decision_version: str = "v1"
    rule_version: str = "rules-2026-graph"
    model_version: str | None = None
    decision_band: str | None = None
    priority_interval_low: float | None = None
    priority_interval_high: float | None = None
    decision_hash: str | None = None
    graph_degree: int | None = None
    graph_weighted_degree: float | None = None
    graph_signal_density: float | None = None
    graph_reasoning: str | None = None
    band_rationale: str | None = None
    operator_action: str | None = None
    feature_snapshot_json: dict[str, Any] | None = None
    explanation_json: dict[str, Any] | None = None
    recommendations: list[RecommendationResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
