"""
Action Service: applies accepted recommendations to real ticket state and persists
audit-quality action_runs, operator_feedback, and ticket_events rows.

Mutations are intentionally limited to safe, reversible workflow state changes.
External IT automation is never called — apply_runbook creates a pending_review
action that an operator must complete manually in the connected ITSM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.enums import ActionType, EventType, FeedbackType, TicketStatus

_AUTO_RESOLVE_TICKET_STATES = {TicketStatus.RESOLVED.value, TicketStatus.CLOSED.value}


@dataclass
class ActionResult:
    recommendation_id: int
    action_run: dict[str, Any]
    event_id: int
    ticket_state: dict[str, Any]
    rollback_available: bool
    rollback_payload: dict[str, Any]
    feedback: dict[str, Any]


class ActionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def apply_recommendation(
        self,
        recommendation_id: int,
        *,
        action_type_override: str | None = None,
        override_priority: float | None = None,
        confirm_auto_resolve: bool = False,
        note: str | None = None,
        operator_id: str = "api-user",
    ) -> ActionResult | None:
        row = self._load_recommendation(recommendation_id)
        if row is None:
            return None

        action_type = _normalize_action_type(action_type_override or row["action_type"])
        ticket = self._load_ticket(row["ticket_pk"])
        if ticket is None:
            return None

        runner = _ActionRunner(
            db=self.db,
            recommendation=row,
            ticket=ticket,
            action_type=action_type,
            note=note,
            operator_id=operator_id,
            confirm_auto_resolve=confirm_auto_resolve,
        )
        return runner.run(override_priority=override_priority)

    def record_rejection(
        self,
        recommendation_id: int,
        note: str | None,
        operator_id: str = "api-user",
    ) -> ActionResult | None:
        row = self._load_recommendation(recommendation_id)
        if row is None:
            return None

        ticket = self._load_ticket(row["ticket_pk"])
        if ticket is None:
            return None

        runner = _ActionRunner(
            db=self.db,
            recommendation=row,
            ticket=ticket,
            action_type="reject",
            note=note,
            operator_id=operator_id,
            confirm_auto_resolve=False,
        )
        return runner.run_reject()

    def record_override(
        self,
        recommendation_id: int,
        note: str,
        override_priority: float | None,
        operator_id: str = "api-user",
    ) -> ActionResult | None:
        row = self._load_recommendation(recommendation_id)
        if row is None:
            return None

        ticket = self._load_ticket(row["ticket_pk"])
        if ticket is None:
            return None

        runner = _ActionRunner(
            db=self.db,
            recommendation=row,
            ticket=ticket,
            action_type="override",
            note=note,
            operator_id=operator_id,
            confirm_auto_resolve=False,
        )
        return runner.run_override(override_priority=override_priority)

    def get_action_run(self, action_run_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    ar.id,
                    ar.recommendation_id,
                    ar.action_type,
                    ar.risk_level,
                    ar.requested_by,
                    ar.approved_by,
                    ar.started_at,
                    ar.finished_at,
                    ar.status,
                    ar.result_json,
                    ar.rollback_available,
                    ar.rollback_metadata_json,
                    ar.operator_note,
                    ar.rollback_payload_json,
                    ar.ticket_event_id,
                    r.decision_record_id,
                    dr.ticket_id AS ticket_pk,
                    t.ticket_id AS external_ticket_id
                FROM action_runs ar
                JOIN recommendations r ON r.id = ar.recommendation_id
                JOIN decision_records dr ON dr.id = r.decision_record_id
                JOIN tickets t ON t.id = dr.ticket_id
                WHERE ar.id = :action_run_id
                """
            ),
            {"action_run_id": action_run_id},
        ).mappings().first()
        if row is None:
            return None
        return _serialize_action_run(dict(row))

    def _load_recommendation(self, recommendation_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    r.id,
                    r.decision_record_id,
                    r.rank,
                    r.action_type,
                    r.action_label,
                    r.rationale,
                    r.risk_level,
                    r.expected_benefit,
                    r.confidence,
                    r.requires_approval,
                    r.recommended_runbook_id,
                    r.status,
                    dr.ticket_id AS ticket_pk,
                    t.ticket_id AS external_ticket_id
                FROM recommendations r
                JOIN decision_records dr ON dr.id = r.decision_record_id
                JOIN tickets t ON t.id = dr.ticket_id
                WHERE r.id = :recommendation_id
                """
            ),
            {"recommendation_id": recommendation_id},
        ).mappings().first()
        return dict(row) if row else None

    def _load_ticket(self, ticket_pk: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    id,
                    ticket_id,
                    title,
                    status,
                    priority,
                    staff_assigned,
                    request_type,
                    priority_score_cache
                FROM tickets
                WHERE id = :ticket_pk
                """
            ),
            {"ticket_pk": ticket_pk},
        ).mappings().first()
        return dict(row) if row else None


class _ActionRunner:
    def __init__(
        self,
        db: Session,
        recommendation: dict[str, Any],
        ticket: dict[str, Any],
        action_type: str,
        note: str | None,
        operator_id: str,
        confirm_auto_resolve: bool,
    ) -> None:
        self.db = db
        self.recommendation = recommendation
        self.ticket = ticket
        self.action_type = action_type
        self.note = note
        self.operator_id = operator_id
        self.confirm_auto_resolve = confirm_auto_resolve

    def run(self, override_priority: float | None = None) -> ActionResult:
        mutation = self._apply_mutation(override_priority=override_priority)
        self.db.execute(
            text("UPDATE recommendations SET status = :status WHERE id = :rid"),
            {"status": "accepted", "rid": self.recommendation["id"]},
        )
        action_run_id = self._insert_action_run(
            status=mutation["action_status"],
            ticket_state=mutation["ticket_state"],
            result_json=mutation["result_json"],
            rollback_available=mutation["rollback_available"],
            rollback_payload=mutation["rollback_payload"],
        )
        event_id = self._insert_ticket_event(
            event_type=EventType.RECOMMENDATION_ACCEPTED.value,
            payload=mutation["event_payload"],
        )
        self.db.execute(
            text(
                "UPDATE action_runs SET ticket_event_id = :eid WHERE id = :aid"
            ),
            {"eid": event_id, "aid": action_run_id},
        )
        feedback = self._insert_feedback(
            feedback_type=FeedbackType.ACCEPTED.value,
            note=self.note,
        )
        self.db.commit()

        action_run = self.db.execute(
            text(
                "SELECT id, recommendation_id, action_type, status, started_at, finished_at, "
                "rollback_available, result_json, rollback_metadata_json, ticket_event_id, operator_note "
                "FROM action_runs WHERE id = :aid"
            ),
            {"aid": action_run_id},
        ).mappings().first()
        if action_run is None:
            raise RuntimeError(f"action_run {action_run_id} disappeared after insert")
        return ActionResult(
            recommendation_id=self.recommendation["id"],
            action_run=_serialize_action_run_from_row(dict(action_run)),
            event_id=event_id,
            ticket_state=mutation["ticket_state"],
            rollback_available=mutation["rollback_available"],
            rollback_payload=mutation["rollback_payload"],
            feedback=feedback,
        )

    def run_reject(self) -> ActionResult:
        self.db.execute(
            text("UPDATE recommendations SET status = :status WHERE id = :rid"),
            {"status": "rejected", "rid": self.recommendation["id"]},
        )
        action_run_id = self._insert_action_run(
            status="rejected",
            ticket_state=_ticket_state_snapshot(self.ticket),
            result_json={"decision": "rejected", "note": self.note},
            rollback_available=0,
            rollback_payload={},
        )
        event_id = self._insert_ticket_event(
            event_type=EventType.RECOMMENDATION_REJECTED.value,
            payload={
                "recommendation_id": self.recommendation["id"],
                "action_type": self.recommendation["action_type"],
                "note": self.note,
            },
        )
        self.db.execute(
            text("UPDATE action_runs SET ticket_event_id = :eid WHERE id = :aid"),
            {"eid": event_id, "aid": action_run_id},
        )
        feedback = self._insert_feedback(
            feedback_type=FeedbackType.REJECTED.value,
            note=self.note,
        )
        self.db.commit()

        action_run = self.db.execute(
            text(
                "SELECT id, recommendation_id, action_type, status, started_at, finished_at, "
                "rollback_available, result_json, rollback_metadata_json, ticket_event_id, operator_note "
                "FROM action_runs WHERE id = :aid"
            ),
            {"aid": action_run_id},
        ).mappings().first()
        if action_run is None:
            raise RuntimeError(f"action_run {action_run_id} disappeared after insert")
        return ActionResult(
            recommendation_id=self.recommendation["id"],
            action_run=_serialize_action_run_from_row(dict(action_run)),
            event_id=event_id,
            ticket_state=_ticket_state_snapshot(self.ticket),
            rollback_available=False,
            rollback_payload={},
            feedback=feedback,
        )

    def run_override(self, override_priority: float | None) -> ActionResult:
        mutation = self._apply_override(override_priority=override_priority)
        self.db.execute(
            text("UPDATE recommendations SET status = :status WHERE id = :rid"),
            {"status": "overridden", "rid": self.recommendation["id"]},
        )
        action_run_id = self._insert_action_run(
            status=mutation["action_status"],
            ticket_state=mutation["ticket_state"],
            result_json=mutation["result_json"],
            rollback_available=0,
            rollback_payload={},
        )
        event_id = self._insert_ticket_event(
            event_type=EventType.RECOMMENDATION_OVERRIDDEN.value,
            payload=mutation["event_payload"],
        )
        self.db.execute(
            text("UPDATE action_runs SET ticket_event_id = :eid WHERE id = :aid"),
            {"eid": event_id, "aid": action_run_id},
        )
        feedback = self._insert_feedback(
            feedback_type=FeedbackType.OVERRIDDEN.value,
            note=self.note,
        )
        self.db.commit()

        action_run = self.db.execute(
            text(
                "SELECT id, recommendation_id, action_type, status, started_at, finished_at, "
                "rollback_available, result_json, rollback_metadata_json, ticket_event_id, operator_note "
                "FROM action_runs WHERE id = :aid"
            ),
            {"aid": action_run_id},
        ).mappings().first()
        if action_run is None:
            raise RuntimeError(f"action_run {action_run_id} disappeared after insert")
        return ActionResult(
            recommendation_id=self.recommendation["id"],
            action_run=_serialize_action_run_from_row(dict(action_run)),
            event_id=event_id,
            ticket_state=mutation["ticket_state"],
            rollback_available=False,
            rollback_payload={},
            feedback=feedback,
        )

    def _apply_mutation(self, override_priority: float | None) -> dict[str, Any]:
        at = self.action_type
        if at == ActionType.APPLY_RUNBOOK.value:
            return self._mutate_runbook()
        if at == ActionType.ASSIGN_TEAM.value:
            return self._mutate_assign()
        if at == ActionType.REQUEST_INFO.value:
            return self._mutate_request_info()
        if at == ActionType.AUTO_RESOLVE.value:
            return self._mutate_auto_resolve()
        if at == ActionType.ESCALATE.value:
            return self._mutate_escalate()
        if at == ActionType.LINK_INCIDENT.value:
            return self._mutate_link_incident()
        if at == "override":
            return self._apply_override(override_priority)
        return self._mutate_noop(action_type=at)

    def _mutate_runbook(self) -> dict[str, Any]:
        runbook_id = self.recommendation.get("recommended_runbook_id")
        result = {
            "decision": "runbook_queued",
            "runbook_id": runbook_id,
            "applied": False,
            "note": "Runbook dispatch is operator-driven; review queued in action_runs.",
        }
        state = _ticket_state_snapshot(self.ticket)
        return {
            "action_status": "pending_review",
            "ticket_state": state,
            "result_json": result,
            "rollback_available": True,
            "rollback_payload": {
                "kind": "runbook_queued",
                "runbook_id": runbook_id,
                "previous_state": state,
            },
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.APPLY_RUNBOOK.value,
                "runbook_id": runbook_id,
                "status": "pending_review",
                "note": self.note,
            },
        }

    def _mutate_assign(self) -> dict[str, Any]:
        target_team = self._target_assignee()
        previous = dict(self.ticket)
        self.db.execute(
            text(
                "UPDATE tickets SET staff_assigned = :assignee, status = :status, "
                "updated_at = NOW() WHERE id = :ticket_pk"
            ),
            {
                "assignee": target_team,
                "status": TicketStatus.IN_PROGRESS.value,
                "ticket_pk": self.ticket["id"],
            },
        )
        self.ticket["staff_assigned"] = target_team
        self.ticket["status"] = TicketStatus.IN_PROGRESS.value
        new_state = _ticket_state_snapshot(self.ticket)
        rollback = {
            "kind": "assignment_changed",
            "previous_assignee": previous.get("staff_assigned"),
            "previous_status": previous.get("status"),
        }
        return {
            "action_status": "completed_manual",
            "ticket_state": new_state,
            "result_json": {
                "decision": "assigned",
                "assignee": target_team,
                "applied": True,
            },
            "rollback_available": True,
            "rollback_payload": rollback,
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.ASSIGN_TEAM.value,
                "assignee": target_team,
                "previous_assignee": previous.get("staff_assigned"),
                "note": self.note,
            },
        }

    def _mutate_request_info(self) -> dict[str, Any]:
        previous = dict(self.ticket)
        self.db.execute(
            text(
                "UPDATE tickets SET status = :status, updated_at = NOW() "
                "WHERE id = :ticket_pk"
            ),
            {
                "status": TicketStatus.WAITING_FOR_INFO.value,
                "ticket_pk": self.ticket["id"],
            },
        )
        self.ticket["status"] = TicketStatus.WAITING_FOR_INFO.value
        new_state = _ticket_state_snapshot(self.ticket)
        return {
            "action_status": "completed_manual",
            "ticket_state": new_state,
            "result_json": {
                "decision": "info_requested",
                "status": TicketStatus.WAITING_FOR_INFO.value,
                "applied": True,
            },
            "rollback_available": True,
            "rollback_payload": {
                "kind": "status_changed",
                "previous_status": previous.get("status"),
            },
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.REQUEST_INFO.value,
                "previous_status": previous.get("status"),
                "note": self.note,
            },
        }

    def _mutate_auto_resolve(self) -> dict[str, Any]:
        if not self.confirm_auto_resolve:
            raise ValueError(
                "auto_resolve requires confirm=true — refusing to close ticket without explicit confirmation"
            )
        previous = dict(self.ticket)
        if previous.get("status") in _AUTO_RESOLVE_TICKET_STATES:
            return {
                "action_status": "completed_manual",
                "ticket_state": _ticket_state_snapshot(self.ticket),
                "result_json": {
                    "decision": "auto_resolve_noop",
                    "applied": False,
                    "reason": "Ticket already in resolved/closed state",
                },
                "rollback_available": False,
                "rollback_payload": {},
                "event_payload": {
                    "recommendation_id": self.recommendation["id"],
                    "action_type": ActionType.AUTO_RESOLVE.value,
                    "note": self.note,
                    "no_op": True,
                },
            }
        self.db.execute(
            text(
                "UPDATE tickets SET status = :status, resolved_at = NOW(), updated_at = NOW() "
                "WHERE id = :ticket_pk"
            ),
            {"status": TicketStatus.RESOLVED.value, "ticket_pk": self.ticket["id"]},
        )
        self.ticket["status"] = TicketStatus.RESOLVED.value
        new_state = _ticket_state_snapshot(self.ticket)
        return {
            "action_status": "completed_manual",
            "ticket_state": new_state,
            "result_json": {
                "decision": "auto_resolved",
                "applied": True,
                "status": TicketStatus.RESOLVED.value,
            },
            "rollback_available": True,
            "rollback_payload": {
                "kind": "auto_resolved",
                "previous_status": previous.get("status"),
            },
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.AUTO_RESOLVE.value,
                "previous_status": previous.get("status"),
                "note": self.note,
            },
        }

    def _mutate_escalate(self) -> dict[str, Any]:
        previous = dict(self.ticket)
        self.db.execute(
            text(
                "UPDATE tickets SET priority = :priority, updated_at = NOW() "
                "WHERE id = :ticket_pk"
            ),
            {"priority": "Critical", "ticket_pk": self.ticket["id"]},
        )
        self.ticket["priority"] = "Critical"
        new_state = _ticket_state_snapshot(self.ticket)
        return {
            "action_status": "completed_manual",
            "ticket_state": new_state,
            "result_json": {
                "decision": "escalated",
                "applied": True,
                "previous_priority": previous.get("priority"),
            },
            "rollback_available": True,
            "rollback_payload": {
                "kind": "priority_changed",
                "previous_priority": previous.get("priority"),
            },
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.ESCALATE.value,
                "previous_priority": previous.get("priority"),
                "note": self.note,
            },
        }

    def _mutate_link_incident(self) -> dict[str, Any]:
        state = _ticket_state_snapshot(self.ticket)
        return {
            "action_status": "completed_manual",
            "ticket_state": state,
            "result_json": {
                "decision": "link_recorded",
                "applied": True,
                "note": self.note,
            },
            "rollback_available": False,
            "rollback_payload": {},
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": ActionType.LINK_INCIDENT.value,
                "note": self.note,
            },
        }

    def _mutate_noop(self, action_type: str) -> dict[str, Any]:
        return {
            "action_status": "completed_manual",
            "ticket_state": _ticket_state_snapshot(self.ticket),
            "result_json": {
                "decision": "noop",
                "applied": False,
                "reason": f"No mutation registered for action_type={action_type}",
            },
            "rollback_available": False,
            "rollback_payload": {},
            "event_payload": {
                "recommendation_id": self.recommendation["id"],
                "action_type": action_type,
                "note": self.note,
                "no_op": True,
            },
        }

    def _apply_override(self, override_priority: float | None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "recommendation_id": self.recommendation["id"],
            "action_type": "override",
            "note": self.note,
        }
        previous_priority = self.recommendation.get("priority_score_cache")
        if override_priority is not None:
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
                    "recommendation_id": self.recommendation["id"],
                },
            )
            self.db.execute(
                text(
                    "UPDATE tickets SET priority_score_cache = :score, updated_at = NOW() "
                    "WHERE id = :ticket_pk"
                ),
                {"score": int(override_priority), "ticket_pk": self.ticket["id"]},
            )
            payload["override_priority"] = override_priority
            payload["previous_priority"] = previous_priority
        return {
            "action_status": "completed_manual",
            "ticket_state": _ticket_state_snapshot(self.ticket),
            "result_json": {"decision": "overridden", "applied": bool(override_priority is not None)},
            "rollback_available": False,
            "rollback_payload": {},
            "event_payload": payload,
        }

    def _target_assignee(self) -> str:
        root_cause = (self.recommendation.get("rationale") or "").strip()
        label = self.recommendation.get("action_label") or "specialist queue"
        lowered = label.lower()
        for token in ("access identity", "email", "mailbox", "printer", "file share", "erp", "network", "security", "infrastructure"):
            if token in lowered:
                return f"{token.replace(' ', '_')}_queue"
        if root_cause and root_cause != "unknown":
            return f"{root_cause}_queue"
        return "triage_queue"

    def _insert_action_run(
        self,
        *,
        status: str,
        ticket_state: dict[str, Any],
        result_json: dict[str, Any],
        rollback_available: int,
        rollback_payload: dict[str, Any],
    ) -> int:
        risk_level = _normalize_enum_value(self.recommendation.get("risk_level") or "low")
        requires_approval = bool(self.recommendation.get("requires_approval"))
        approved_by = self.operator_id if (not requires_approval or status == "pending_review") else None
        return int(
            self.db.execute(
                text(
                    """
                    INSERT INTO action_runs (
                        recommendation_id,
                        action_type,
                        risk_level,
                        requested_by,
                        approved_by,
                        started_at,
                        finished_at,
                        status,
                        result_json,
                        rollback_available,
                        rollback_metadata_json,
                        operator_note,
                        rollback_payload_json
                    )
                    VALUES (
                        :recommendation_id,
                        :action_type,
                        :risk_level,
                        :requested_by,
                        :approved_by,
                        NOW(),
                        NOW(),
                        :status,
                        CAST(:result_json AS JSONB),
                        :rollback_available,
                        CAST(:rollback_metadata AS JSONB),
                        :operator_note,
                        CAST(:rollback_payload AS JSONB)
                    )
                    RETURNING id
                    """
                ),
                {
                    "recommendation_id": self.recommendation["id"],
                    "action_type": self.action_type,
                    "risk_level": risk_level,
                    "requested_by": self.operator_id,
                    "approved_by": approved_by,
                    "status": status,
                    "result_json": json.dumps({**result_json, "ticket_state_after": ticket_state}),
                    "rollback_available": 1 if rollback_available else 0,
                    "rollback_metadata": json.dumps(
                        {
                            "previous_state": ticket_state,
                            "kind": rollback_payload.get("kind"),
                        }
                    ),
                    "operator_note": self.note,
                    "rollback_payload": json.dumps(rollback_payload),
                },
            ).scalar_one()
        )

    def _insert_ticket_event(self, *, event_type: str, payload: dict[str, Any]) -> int:
        return int(
            self.db.execute(
                text(
                    """
                    INSERT INTO ticket_events (
                        ticket_id,
                        event_type,
                        event_ts,
                        actor_type,
                        actor_id,
                        payload_json
                    )
                    VALUES (
                        :ticket_pk,
                        :event_type,
                        NOW(),
                        :actor_type,
                        :actor_id,
                        CAST(:payload_json AS JSONB)
                    )
                    RETURNING id
                    """
                ),
                {
                    "ticket_pk": self.ticket["id"],
                    "event_type": event_type,
                    "actor_type": "operator",
                    "actor_id": self.operator_id,
                    "payload_json": json.dumps(payload),
                },
            ).scalar_one()
        )

    def _insert_feedback(self, *, feedback_type: str, note: str | None) -> dict[str, Any]:
        row = self.db.execute(
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
                    :operator_id
                )
                RETURNING id, feedback_type, feedback_note, feedback_ts, operator_id
                """
            ),
            {
                "recommendation_id": self.recommendation["id"],
                "ticket_pk": self.ticket["id"],
                "feedback_type": feedback_type,
                "feedback_note": note,
                "operator_id": self.operator_id,
            },
        ).mappings().first()
        if row is None:
            raise RuntimeError("feedback insert returned no row")
        return _serialize_feedback(dict(row))


def _ticket_state_snapshot(ticket: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket_id": ticket.get("ticket_id"),
        "status": ticket.get("status"),
        "priority": ticket.get("priority"),
        "assignee": ticket.get("staff_assigned"),
        "request_type": ticket.get("request_type"),
        "priority_score_cache": ticket.get("priority_score_cache"),
        "snapshot_ts": datetime.now(timezone.utc).isoformat(),
    }


def _normalize_action_type(value: object) -> str:
    if isinstance(value, ActionType):
        return value.value
    return _normalize_enum_value(value)


def _normalize_enum_value(value: object) -> str:
    raw = str(value or "").strip()
    if "." in raw:
        raw = raw.rsplit(".", 1)[-1]
    return raw.lower()


def _serialize_feedback(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "feedback_type": row.get("feedback_type"),
        "feedback_note": row.get("feedback_note"),
        "operator_id": row.get("operator_id"),
        "feedback_ts": _iso(row.get("feedback_ts")),
    }


def _serialize_action_run_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "recommendation_id": row.get("recommendation_id"),
        "action_type": row.get("action_type"),
        "status": row.get("status"),
        "started_at": _iso(row.get("started_at")),
        "finished_at": _iso(row.get("finished_at")),
        "rollback_available": bool(row.get("rollback_available")),
        "result_json": row.get("result_json"),
        "rollback_metadata_json": row.get("rollback_metadata_json"),
        "operator_note": row.get("operator_note"),
        "ticket_event_id": row.get("ticket_event_id"),
    }


def _serialize_action_run(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row.get("id"),
        "recommendation_id": row.get("recommendation_id"),
        "action_type": row.get("action_type"),
        "risk_level": row.get("risk_level"),
        "requested_by": row.get("requested_by"),
        "approved_by": row.get("approved_by"),
        "started_at": _iso(row.get("started_at")),
        "finished_at": _iso(row.get("finished_at")),
        "status": row.get("status"),
        "result_json": row.get("result_json"),
        "rollback_available": bool(row.get("rollback_available")),
        "rollback_metadata_json": row.get("rollback_metadata_json"),
        "operator_note": row.get("operator_note"),
        "rollback_payload_json": row.get("rollback_payload_json"),
        "ticket_event_id": row.get("ticket_event_id"),
        "ticket_id": row.get("external_ticket_id"),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
