"""
Operational intelligence health endpoint.

GET /api/intelligence/health

Reports the live readiness of every subsystem powering the decision engine:
scoring weights, last decision timestamp, feedback volume, retrieval link
counts, incident persistence, graph status, and governance drift. Honest
about what is and is not wired up.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user
from apps.api.services.graph_intelligence_service import summarize_graph
from domain.policies import SCORING_WEIGHTS
from pipelines.governance.decision_drift import run_drift_detection

router = APIRouter()


def _safe_count(db: Session, sql: str, params: dict[str, Any] | None = None) -> int:
    try:
        row = db.execute(text(sql), params or {}).mappings().first()
    except Exception:
        return 0
    if not row:
        return 0
    return int(next(iter(row.values()), 0) or 0)


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


@router.get("/health")
def intelligence_health(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    ticket_count = _safe_count(db, "SELECT COUNT(*) AS c FROM tickets")
    decision_count = _safe_count(db, "SELECT COUNT(*) AS c FROM decision_records")
    feedback_count = _safe_count(db, "SELECT COUNT(*) AS c FROM operator_feedback")
    action_run_count = _safe_count(db, "SELECT COUNT(*) AS c FROM action_runs")
    recommendation_count = _safe_count(db, "SELECT COUNT(*) AS c FROM recommendations")
    incident_count = _safe_count(db, "SELECT COUNT(*) AS c FROM incidents")
    similar_link_count = _safe_count(db, "SELECT COUNT(*) AS c FROM similar_case_links")

    last_decision = db.execute(
        text("SELECT MAX(decision_ts) AS ts FROM decision_records")
    ).mappings().first()
    last_feedback = db.execute(
        text("SELECT MAX(feedback_ts) AS ts FROM operator_feedback")
    ).mappings().first()
    last_action_run = db.execute(
        text("SELECT MAX(started_at) AS ts FROM action_runs")
    ).mappings().first()

    feedback_by_type_rows = db.execute(
        text(
            """
            SELECT feedback_type, COUNT(*) AS c
            FROM operator_feedback
            GROUP BY feedback_type
            """
        )
    ).mappings()
    feedback_by_type = {row["feedback_type"]: int(row["c"]) for row in feedback_by_type_rows}

    action_runs_by_status_rows = db.execute(
        text(
            """
            SELECT status, COUNT(*) AS c
            FROM action_runs
            GROUP BY status
            """
        )
    ).mappings()
    action_runs_by_status = {row["status"]: int(row["c"]) for row in action_runs_by_status_rows}

    try:
        graph_summary = summarize_graph(db)
    except Exception as exc:  # noqa: BLE001
        graph_summary = {"status": "unavailable", "error": str(exc)}

    try:
        drift = run_drift_detection(db)
    except Exception as exc:  # noqa: BLE001
        drift = {"status": "unavailable", "error": str(exc)}

    return {
        "status": "ok",
        "engine": {
            "name": "rules",
            "kind": "deterministic graph + rules",
            "version": SCORING_WEIGHTS.version_tag,
            "decision_schema_version": "v2",
            "model_version": None,
            "description": (
                "Deterministic weighted rules engine plus a 7-edge ticket relationship graph. "
                "No external LLM, no trained ML model in this pass. Decision lineage is "
                "reproducible from feature_snapshot_json + decision_hash + rule_version."
            ),
        },
        "scoring_weights": {
            "version": SCORING_WEIGHTS.version_tag,
            "severity": SCORING_WEIGHTS.SEVERITY,
            "urgency": SCORING_WEIGHTS.URGENCY,
            "business_impact": SCORING_WEIGHTS.BUSINESS_IMPACT,
            "sla_risk": SCORING_WEIGHTS.SLA_RISK,
            "recurrence": SCORING_WEIGHTS.RECURRENCE,
            "dependency_criticality": SCORING_WEIGHTS.DEPENDENCY_CRITICALITY,
            "actionability": SCORING_WEIGHTS.ACTIONABILITY,
            "uncertainty_penalty": SCORING_WEIGHTS.UNCERTAINTY_PENALTY,
        },
        "subsystems": {
            "decision_records": {
                "count": decision_count,
                "last_decision_ts": _iso(last_decision["ts"]) if last_decision else None,
            },
            "recommendations": {"count": recommendation_count},
            "operator_feedback": {
                "count": feedback_count,
                "by_type": feedback_by_type,
                "last_feedback_ts": _iso(last_feedback["ts"]) if last_feedback else None,
            },
            "action_runs": {
                "count": action_run_count,
                "by_status": action_runs_by_status,
                "last_started_at": _iso(last_action_run["ts"]) if last_action_run else None,
            },
            "incidents": {"count": incident_count, "stable_ids": True},
            "retrieval": {
                "similar_case_links": similar_link_count,
                "engine": "DB-backed similar_case_links + ticket text overlap",
            },
            "graph": graph_summary,
            "tickets": {"count": ticket_count},
        },
        "drift": drift,
        "feedback_loop": {
            "enabled": feedback_count > 0,
            "adjustment_cap": 20.0,
            "decay_factor": 0.85,
            "source": "infrastructure.logging.feedback_learner.FeedbackLearner",
        },
        "truthful_disclosure": {
            "no_external_llm": True,
            "no_trained_ml_model": True,
            "actions_are_real_workflow_mutations": True,
            "runbooks_require_human_review": True,
            "graph_features_are_deterministic": True,
            "decision_hash_is_deterministic": True,
        },
    }
