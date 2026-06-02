"""
Aether Decision Engine Card.

A "decision engine card" is what an AI/ML team would normally call a
"model card", adapted for the deterministic graph + rules engine that
powers Aether. It is a static, auditable description of:

- what the engine is and is not (deterministic, no external LLM,
  no trained model in this pass);
- which inputs it consumes;
- which outputs it produces (with versioning);
- which guardrails apply;
- who is responsible.

The card is generated on demand from `domain.policies` and the
governance drift module so that the version numbers are always in
sync with the running rules.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from domain.policies import (
    BAND_HIGH_CONFIDENCE_ACTION,
    BAND_REVIEW_NEEDED,
    BAND_STANDARD_QUEUE,
    SCORING_WEIGHTS,
    GRAPH_FEATURE_WEIGHTS,
    UNCERTAINTY_BAND_THRESHOLDS,
)


def build_decision_card() -> dict[str, Any]:
    """Return a dict describing the Aether decision engine."""
    return {
        "title": "Aether Decision Engine Card",
        "kind": "decision-engine-card",
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "engine": {
            "name": "Aether Decision Engine",
            "kind": "deterministic graph + rules",
            "version": SCORING_WEIGHTS.version_tag,
            "decision_schema_version": "v2",
            "model_version": None,
            "external_llm": False,
            "trained_ml_model": False,
        },
        "what_this_engine_is": [
            "Deterministic weighted score over 7 factors plus a 7-edge ticket relationship graph.",
            "Uncertainty band classification into high_confidence_action, review_needed, or standard_queue.",
            "A SHA-256 decision hash that fingerprints the inputs and the rule version.",
        ],
        "what_this_engine_is_not": [
            "It is not an LLM and does not call any external language model.",
            "It is not a trained ML model — there are no learned weights or inference graph in this pass.",
            "It does not auto-execute runbooks; apply_runbook actions are queued for human review.",
        ],
        "inputs": [
            "tickets.ticket_id, title, description, status, priority, request_type, requester, site_id, asset_id, category_id, created_at",
            "decision_records (history) and operator_feedback (acceptance / rejection / override)",
            "similar_case_links (precomputed) and live ticket text overlap",
        ],
        "outputs": {
            "decision_record": [
                "priority_score (0–100)",
                "decision_band (high_confidence_action | review_needed | standard_queue)",
                "priority_interval_low / priority_interval_high",
                "decision_hash (SHA-256)",
                "graph_degree / graph_weighted_degree",
                "feature_snapshot_json / explanation_json",
            ],
            "recommendations": [
                "rank, action_type, action_label, rationale, risk_level, confidence, recommended_runbook_id",
            ],
            "incidents": [
                "stable incident_key, ticket_count, graph_evidence, recommended_action",
            ],
        },
        "scoring_weights": {
            "severity": SCORING_WEIGHTS.SEVERITY,
            "urgency": SCORING_WEIGHTS.URGENCY,
            "business_impact": SCORING_WEIGHTS.BUSINESS_IMPACT,
            "sla_risk": SCORING_WEIGHTS.SLA_RISK,
            "recurrence": SCORING_WEIGHTS.RECURRENCE,
            "dependency_criticality": SCORING_WEIGHTS.DEPENDENCY_CRITICALITY,
            "actionability": SCORING_WEIGHTS.ACTIONABILITY,
            "uncertainty_penalty": SCORING_WEIGHTS.UNCERTAINTY_PENALTY,
        },
        "graph_weights": {
            "shared_requester": GRAPH_FEATURE_WEIGHTS.REQUESTER,
            "shared_assignee": GRAPH_FEATURE_WEIGHTS.ASSIGNEE,
            "shared_site": GRAPH_FEATURE_WEIGHTS.SITE,
            "shared_asset": GRAPH_FEATURE_WEIGHTS.ASSET,
            "shared_category": GRAPH_FEATURE_WEIGHTS.CATEGORY,
            "shared_root_cause": GRAPH_FEATURE_WEIGHTS.ROOT_CAUSE,
            "within_time_window": GRAPH_FEATURE_WEIGHTS.TIME_WINDOW,
        },
        "uncertainty_bands": {
            "labels": [BAND_HIGH_CONFIDENCE_ACTION, BAND_REVIEW_NEEDED, BAND_STANDARD_QUEUE],
            "thresholds": {
                "high_confidence_min_priority": UNCERTAINTY_BAND_THRESHOLDS.HIGH_CONFIDENCE_MIN_PRIORITY,
                "high_confidence_min_confidence": UNCERTAINTY_BAND_THRESHOLDS.HIGH_CONFIDENCE_MIN_CONFIDENCE,
                "review_needed_max_confidence": UNCERTAINTY_BAND_THRESHOLDS.REVIEW_NEEDED_MAX_CONFIDENCE,
                "review_needed_max_priority": UNCERTAINTY_BAND_THRESHOLDS.REVIEW_NEEDED_MAX_PRIORITY,
                "uncertainty_penalty_review": UNCERTAINTY_BAND_THRESHOLDS.UNCERTAINTY_PENALTY_REVIEW,
            },
        },
        "guardrails": [
            "auto_resolve requires explicit confirm=true in the request body.",
            "apply_runbook writes an action_run with status='pending_review' and does not invoke external automation.",
            "operator feedback is required to mark a recommendation as accepted, rejected, or overridden.",
            "all action_runs and operator_feedback rows are linked to a ticket_event for audit.",
        ],
        "ownership": {
            "team": "Aether OpsCenter",
            "review_cadence": "weekly drift review",
            "override_path": "ActionService.record_override (operator_id + override_priority + note)",
        },
    }
