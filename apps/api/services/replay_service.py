from __future__ import annotations
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.decision_service import DecisionService
from apps.api.services.event_service import EventService
from apps.api.services.operational_intelligence import fetch_similar_cases, fetch_ticket_row


class ReplayService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_replay(self, ticket_id: str) -> dict[str, Any] | None:
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        latest_decision = DecisionService(self.db).get_latest_decision(ticket_id)

        decision_history: list[dict[str, Any]] = []
        try:
            decisions = self.db.execute(
                text(
                    """
                    SELECT
                        dr.id,
                        dr.decision_ts,
                        dr.priority_score,
                        dr.root_cause_hypothesis,
                        dr.confidence_score,
                        dr.explanation_json,
                        dr.decision_band,
                        dr.decision_hash,
                        dr.priority_interval_low,
                        dr.priority_interval_high,
                        dr.graph_degree,
                        dr.graph_weighted_degree,
                        dr.anomaly_zscore
                    FROM decision_records dr
                    JOIN tickets t ON t.id = dr.ticket_id
                    WHERE t.ticket_id = :ticket_id
                    ORDER BY dr.decision_ts ASC, dr.id ASC
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings()
            decision_history = [
                {
                    "id": row["id"],
                    "decision_ts": row["decision_ts"].isoformat() if row["decision_ts"] else None,
                    "priority_score": row["priority_score"],
                    "root_cause_hypothesis": row["root_cause_hypothesis"],
                    "confidence_score": row["confidence_score"],
                    "explanation_json": row["explanation_json"],
                    "decision_band": row["decision_band"],
                    "decision_hash": row["decision_hash"],
                    "priority_interval_low": row["priority_interval_low"],
                    "priority_interval_high": row["priority_interval_high"],
                    "graph_degree": row["graph_degree"],
                    "graph_weighted_degree": row["graph_weighted_degree"],
                    "anomaly_zscore": row["anomaly_zscore"],
                }
                for row in decisions
            ]
        except Exception:
            decision_history = []

        operator_feedback: list[dict[str, Any]] = []
        try:
            feedback = self.db.execute(
                text(
                    """
                    SELECT
                        ofe.feedback_type,
                        ofe.feedback_note,
                        ofe.feedback_ts,
                        ofe.operator_id
                    FROM operator_feedback ofe
                    JOIN recommendations r ON r.id = ofe.recommendation_id
                    JOIN decision_records dr ON dr.id = r.decision_record_id
                    JOIN tickets t ON t.id = dr.ticket_id
                    WHERE t.ticket_id = :ticket_id
                    ORDER BY ofe.feedback_ts ASC, ofe.id ASC
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings()
            operator_feedback = [
                {
                    "feedback_type": row["feedback_type"],
                    "feedback_note": row["feedback_note"],
                    "feedback_ts": row["feedback_ts"].isoformat() if row["feedback_ts"] else None,
                    "operator_id": row["operator_id"],
                }
                for row in feedback
            ]
        except Exception:
            operator_feedback = []

        events: list[dict[str, Any]] = []
        try:
            events = EventService(self.db).get_ticket_event_stream(ticket_id) or []
        except Exception:
            events = []

        similar_cases: list[dict[str, Any]] = []
        try:
            similar_cases = fetch_similar_cases(self.db, ticket) or []
        except Exception:
            similar_cases = []

        action_runs: list[dict[str, Any]] = []
        try:
            ars = self.db.execute(
                text(
                    """
                    SELECT
                        ar.id,
                        ar.status,
                        ar.action_type,
                        ar.started_at,
                        ar.finished_at,
                        ar.operator_note,
                        r.rank as recommendation_rank
                    FROM action_runs ar
                    JOIN recommendations r ON r.id = ar.recommendation_id
                    JOIN decision_records dr ON dr.id = r.decision_record_id
                    JOIN tickets t ON t.id = dr.ticket_id
                    WHERE t.ticket_id = :ticket_id
                    ORDER BY ar.started_at DESC NULLS LAST
                    LIMIT 20
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings()
            action_runs = [
                {
                    "id": row["id"],
                    "status": row["status"],
                    "action_type": row["action_type"],
                    "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                    "finished_at": row["finished_at"].isoformat() if row["finished_at"] else None,
                    "operator_note": row["operator_note"],
                    "recommendation_rank": row["recommendation_rank"],
                }
                for row in ars
            ]
        except Exception:
            action_runs = []

        return {
            "ticket_id": ticket_id,
            "latest_decision": latest_decision,
            "decision_history": decision_history,
            "events": events,
            "operator_feedback": operator_feedback,
            "similar_cases": similar_cases,
            "action_runs": action_runs,
            "note": "Partial data returned if some subsystems were unavailable (defensive).",
        }
