from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from apps.api.services.action_service import ActionService


class RecommendationService:
    """
    Thin facade over ActionService that preserves the legacy response shape
    while always going through the action_run + feedback + ticket_event
    pipeline. Use ActionService directly for new code that needs the
    full action_run payload.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._actions = ActionService(db)

    def accept_recommendation(
        self, recommendation_id: int, note: str | None
    ) -> dict[str, Any] | None:
        result = self._actions.apply_recommendation(
            recommendation_id=recommendation_id, note=note
        )
        if result is None:
            return None
        return _legacy_accept_payload(result)

    def reject_recommendation(
        self, recommendation_id: int, reason: str | None
    ) -> dict[str, Any] | None:
        result = self._actions.record_rejection(
            recommendation_id=recommendation_id, note=reason
        )
        if result is None:
            return None
        return _legacy_reject_payload(result, reason=reason)

    def override_recommendation(
        self,
        recommendation_id: int,
        note: str,
        override_priority: float | None,
    ) -> dict[str, Any] | None:
        result = self._actions.record_override(
            recommendation_id=recommendation_id,
            note=note,
            override_priority=override_priority,
        )
        if result is None:
            return None
        payload = _legacy_override_payload(result, override_priority=override_priority)
        return payload


def _legacy_accept_payload(result: Any) -> dict[str, Any]:
    return {
        "id": result.recommendation_id,
        "status": "accepted",
        "feedback_type": "accepted",
        "action_run_id": result.action_run["id"],
        "action_run_status": result.action_run["status"],
        "ticket_state": result.ticket_state,
        "rollback_available": result.rollback_available,
        "event_id": result.event_id,
        "feedback": result.feedback,
    }


def _legacy_reject_payload(result: Any, reason: str | None) -> dict[str, Any]:
    return {
        "id": result.recommendation_id,
        "status": "rejected",
        "feedback_type": "rejected",
        "feedback_note": reason,
        "action_run_id": result.action_run["id"],
        "action_run_status": result.action_run["status"],
        "event_id": result.event_id,
        "feedback": result.feedback,
    }


def _legacy_override_payload(result: Any, override_priority: float | None) -> dict[str, Any]:
    return {
        "id": result.recommendation_id,
        "status": "overridden",
        "feedback_type": "overridden",
        "override_priority": override_priority,
        "action_run_id": result.action_run["id"],
        "action_run_status": result.action_run["status"],
        "ticket_state": result.ticket_state,
        "event_id": result.event_id,
        "feedback": result.feedback,
    }
