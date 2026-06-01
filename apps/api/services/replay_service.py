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

        decisions = self.db.execute(
            text(
                """
                SELECT
                    dr.id,
                    dr.decision_ts,
                    dr.priority_score,
                    dr.root_cause_hypothesis,
                    dr.confidence_score,
                    dr.explanation_json
                FROM decision_records dr
                JOIN tickets t ON t.id = dr.ticket_id
                WHERE t.ticket_id = :ticket_id
                ORDER BY dr.decision_ts ASC, dr.id ASC
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings()

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
        return {
            "ticket_id": ticket_id,
            "latest_decision": latest_decision,
            "decision_history": [
                {
                    "id": row["id"],
                    "decision_ts": row["decision_ts"].isoformat() if row["decision_ts"] else None,
                    "priority_score": row["priority_score"],
                    "root_cause_hypothesis": row["root_cause_hypothesis"],
                    "confidence_score": row["confidence_score"],
                    "explanation_json": row["explanation_json"],
                }
                for row in decisions
            ],
            "events": EventService(self.db).get_ticket_event_stream(ticket_id),
            "operator_feedback": [
                {
                    "feedback_type": row["feedback_type"],
                    "feedback_note": row["feedback_note"],
                    "feedback_ts": row["feedback_ts"].isoformat() if row["feedback_ts"] else None,
                    "operator_id": row["operator_id"],
                }
                for row in feedback
            ],
            "similar_cases": fetch_similar_cases(self.db, ticket),
        }
