from sqlalchemy.orm import Session
from sqlalchemy import text


class RecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def accept_recommendation(self, recommendation_id: int, note: str | None):
        return self._update_recommendation(
            recommendation_id=recommendation_id,
            status="accepted",
            feedback_type="accepted",
            feedback_note=note,
        )

    def reject_recommendation(self, recommendation_id: int, reason: str | None):
        return self._update_recommendation(
            recommendation_id=recommendation_id,
            status="rejected",
            feedback_type="rejected",
            feedback_note=reason,
        )

    def override_recommendation(
        self, recommendation_id: int, note: str, override_priority: float | None
    ):
        result = self._update_recommendation(
            recommendation_id=recommendation_id,
            status="accepted",
            feedback_type="overridden",
            feedback_note=note,
        )
        if result and override_priority is not None:
            self.db.execute(
                text(
                    """
                    UPDATE decision_records
                    SET priority_score = :priority_score
                    WHERE id = (
                        SELECT decision_record_id
                        FROM recommendations
                        WHERE id = :recommendation_id
                    )
                    """
                ),
                {
                    "priority_score": override_priority,
                    "recommendation_id": recommendation_id,
                },
            )
            self.db.commit()
            result["override_priority"] = override_priority
        return result

    def _update_recommendation(
        self,
        recommendation_id: int,
        status: str,
        feedback_type: str,
        feedback_note: str | None,
    ):
        row = self.db.execute(
            text(
                """
                SELECT
                    r.id,
                    r.decision_record_id,
                    dr.ticket_id,
                    t.ticket_id AS external_ticket_id
                FROM recommendations r
                JOIN decision_records dr ON dr.id = r.decision_record_id
                JOIN tickets t ON t.id = dr.ticket_id
                WHERE r.id = :recommendation_id
                """
            ),
            {"recommendation_id": recommendation_id},
        ).mappings().first()
        if row is None:
            return None

        self.db.execute(
            text("UPDATE recommendations SET status = :status WHERE id = :recommendation_id"),
            {"status": status, "recommendation_id": recommendation_id},
        )
        self.db.execute(
            text(
                """
                INSERT INTO operator_feedback (
                    recommendation_id,
                    ticket_id,
                    feedback_type,
                    feedback_note,
                    feedback_ts,
                    operator_id
                )
                VALUES (
                    :recommendation_id,
                    :ticket_pk,
                    :feedback_type,
                    :feedback_note,
                    NOW(),
                    'api-user'
                )
                """
            ),
            {
                "recommendation_id": recommendation_id,
                "ticket_pk": row["ticket_id"],
                "feedback_type": feedback_type,
                "feedback_note": feedback_note,
            },
        )
        self.db.execute(
            text(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    event_type,
                    event_ts,
                    actor_type,
                    actor_id,
                    payload_json,
                    source_hash
                )
                VALUES (
                    :ticket_pk,
                    :event_type,
                    NOW(),
                    'operator',
                    'api-user',
                    CAST(:payload_json AS JSONB),
                    NULL
                )
                """
            ),
            {
                "ticket_pk": row["ticket_id"],
                "event_type": f"recommendation_{feedback_type}",
                "payload_json": __import__("json").dumps(
                    {
                        "recommendation_id": recommendation_id,
                        "status": status,
                        "note": feedback_note,
                    }
                ),
            },
        )
        self.db.commit()
        return {
            "id": recommendation_id,
            "ticket_id": row["external_ticket_id"],
            "status": status,
            "feedback_type": feedback_type,
            "feedback_note": feedback_note,
        }
