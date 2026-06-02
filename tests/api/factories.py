"""
Reusable factory functions that produce dict stubs satisfying the API
Pydantic response models. Each helper returns plain dicts (not model
instances) so they can be mutated freely inside tests.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def ticket_payload(ticket_id: str = "IT-1", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ticket_id": ticket_id,
        "title": "Cannot access shared drive",
        "status": "Open",
        "priority_raw": "High",
        "priority_score": 81.4,
        "root_cause_hypothesis": "file_share_permissions",
        "confidence_score": 0.82,
        "site": "Production-HQ",
        "assignee": "jsmith",
        "category": "Access",
        "description": "User cannot access shared drive",
        "resolution_notes": "",
        "requester": "jsmith@company.com",
        "created_at": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "days_open": 3,
        "incident_id": "INC-2026-0001",
    }
    base.update(overrides)
    return base


def ticket_detail_payload(ticket_id: str = "IT-1", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ticket": ticket_payload(ticket_id),
        "decision": None,
        "recommendations": [],
        "similar_cases": [],
        "events": [],
        "linked_incident": None,
        "comments": [],
        "attachments": [],
    }
    base.update(overrides)
    return base


def incident_payload(incident_id: int = 1, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": incident_id,
        "title": "Mailbox outage",
        "status": "open",
        "root_cause_hypothesis": "email_messaging",
        "ticket_count": 4,
        "confidence": 0.81,
        "business_impact_score": 76,
        "opened_at": datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def incident_detail_payload(incident_id: int = 1, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "incident": incident_payload(incident_id),
        "tickets": [ticket_payload("IT-1")],
        "common_cause": "Edge SMTP queue stuck",
        "recommended_action": "Run mail flow restart runbook",
    }
    base.update(overrides)
    return base


def decision_payload(ticket_id: str = "IT-1", **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": 1,
        "ticket_id": ticket_id,
        "priority_score": 81.4,
        "severity_score": 72.0,
        "urgency_score": 68.0,
        "business_impact_score": 85.0,
        "sla_risk_score": 54.0,
        "recurrence_score": 40.0,
        "dependency_criticality_score": 50.0,
        "actionability_score": 78.0,
        "uncertainty_penalty": 12.0,
        "root_cause_hypothesis": "file_share_permissions",
        "confidence_score": 0.82,
        "decision_ts": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "decision_version": "v2",
        "rule_version": "rules-2026-graph",
        "model_version": None,
        "decision_band": "high_confidence_action",
        "priority_interval_low": 70.0,
        "priority_interval_high": 90.0,
        "decision_hash": "a" * 64,
        "graph_degree": 3,
        "graph_weighted_degree": 1.5,
        "graph_signal_density": 0.6,
        "graph_reasoning": "site cluster (3 tickets)",
        "band_rationale": "high priority, low uncertainty, strong graph signal",
        "operator_action": "auto_resolve",
        "feature_snapshot_json": {},
        "explanation_json": {},
        "recommendations": [],
    }
    base.update(overrides)
    return base


def recommendation_payload(recommendation_id: int = 1, **overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": recommendation_id,
        "rank": 1,
        "action_type": "assign_team",
        "action_label": "Assign to access_identity_queue",
        "rationale": "Pattern matches 11 resolved prior cases",
        "risk_level": "low",
        "expected_benefit": "Resolve within 1h",
        "confidence": 0.88,
        "requires_approval": False,
        "status": "proposed",
        "created_at": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "last_feedback": None,
        "latest_action_run": None,
        "recommended_runbook_id": "rb_access_identity_001",
    }
    base.update(overrides)
    return base
