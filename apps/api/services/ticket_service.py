from typing import Any
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.attachment_service import AttachmentService
from apps.api.services.comment_service import CommentService
from apps.api.services.operational_intelligence import (
    build_ticket_snapshot,
    build_live_decision_map,
    fetch_similar_cases,
    fetch_ticket_row,
    synthesize_incidents,
)
from apps.api.services.schema_compat import category_join_sql, column_expr
from apps.api.services.decision_service import DecisionService
from apps.api.services.event_service import EventService


class TicketService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.events = EventService(db)
        self.comments = CommentService(db)
        self.attachments = AttachmentService(db)

    def list_tickets(self, **kwargs: object) -> Any:
        filters = []
        params: dict[str, Any] = {}
        ranking = bool(kwargs.get("ranking", False))
        offset_raw = kwargs.get("offset", 0)
        offset = offset_raw if isinstance(offset_raw, int) else 0
        limit_raw = kwargs.get("limit", 50)
        limit = limit_raw if isinstance(limit_raw, int) else 50
        _, category_join = category_join_sql(self.db)

        if kwargs.get("status"):
            filters.append("t.status = :status")
            params["status"] = kwargs["status"]
        if kwargs.get("priority"):
            filters.append("t.priority = :priority")
            params["priority"] = kwargs["priority"]
        if kwargs.get("category"):
            if category_join:
                filters.append("COALESCE(c.name, t.request_type) = :category")
            else:
                filters.append("t.request_type = :category")
            params["category"] = kwargs["category"]
        if kwargs.get("assignee"):
            filters.append("t.staff_assigned = :assignee")
            params["assignee"] = kwargs["assignee"]
        if ranking:
            filters.append("t.status NOT IN ('Resolved', 'Closed')")

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        params["sql_limit"] = max(limit * 6, 80) if ranking else limit
        params["sql_offset"] = 0 if ranking else offset
        rows = list(
            self.db.execute(
                text(
                    _ticket_list_sql(
                        self.db,
                        where_clause=where_clause,
                        limit_clause="LIMIT :sql_limit OFFSET :sql_offset",
                    )
                ),
                params,
            ).mappings()
        )

        tickets = [dict(row) for row in rows]
        decision_map = build_live_decision_map(tickets)
        snapshots = []
        for ticket in tickets:
            snapshots.append(
                build_ticket_snapshot(ticket, decision=decision_map.get(ticket["ticket_id"]))
            )

        incidents = synthesize_incidents(snapshots)
        incident_lookup = {
            ticket["ticket_id"]: incident["id"]
            for incident in incidents
            for ticket in incident["tickets"]
        }
        for snapshot in snapshots:
            snapshot["incident_id"] = incident_lookup.get(snapshot["ticket_id"])

        if ranking:
            snapshots.sort(
                key=lambda ticket: ticket.get("priority_score") or 0,
                reverse=True,
            )

        return snapshots[offset : offset + limit]

    def get_ticket_detail(self, ticket_id: str) -> Any:
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        decisions = DecisionService(self.db)
        decision = decisions.get_latest_decision(ticket_id)
        similar_cases = fetch_similar_cases(self.db, ticket)
        events = EventService(self.db).get_ticket_event_stream(ticket_id)

        all_rows = list(self.db.execute(text(_ticket_list_sql(self.db))).mappings())
        incident_rows = [dict(row) for row in all_rows]
        incident_decision_map = build_live_decision_map(incident_rows)
        incident = next(
            (
                current
                for current in synthesize_incidents(
                    [
                        build_ticket_snapshot(
                            row,
                            incident_decision_map.get(row["ticket_id"]),
                        )
                        for row in incident_rows
                    ]
                )
                if any(item["ticket_id"] == ticket_id for item in current["tickets"])
            ),
            None,
        )
        return {
            "ticket": {
                **build_ticket_snapshot(
                    ticket,
                    decision=decision,
                    incident_id=incident["id"] if incident else None,
                ),
                "request_type": ticket.get("request_type") or ticket.get("category_name"),
                "requester": ticket.get("requester"),
                "description": ticket.get("description") or "",
                "resolution_notes": ticket.get("resolution_notes") or "",
                "category": ticket.get("category_name") or ticket.get("request_type"),
                "category_id": ticket.get("category_id"),
                "labels": self.get_ticket_labels(ticket_id),
            },
            "decision": decision,
            "recommendations": decision.get("recommendations", []) if decision else [],
            "similar_cases": similar_cases,
            "events": events,
            "linked_incident": incident,
            "comments": self.comments.list_comments(ticket_id),
            "attachments": [
                attachment
                for attachment in self.attachments.list_attachments(ticket_id)
                if attachment.get("comment_id") is None
            ],
        }

    def get_ticket_events(self, ticket_id: str) -> Any:
        return EventService(self.db).get_ticket_event_stream(ticket_id)

    def create_ticket(self, payload: dict[str, Any], actor: dict[str, Any]) -> Any:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Title is required")

        category_id = payload.get("category_id")
        request_type = self._resolve_request_type(category_id, payload.get("request_type"))
        ticket_id = self._get_next_ticket_id()
        status = str(payload.get("status") or "Open")
        priority = str(payload.get("priority") or "Low")
        resolved_at = self._resolved_at_for_status(status)

        created = self.db.execute(
            text(
                """
                INSERT INTO tickets (
                    ticket_id,
                    title,
                    status,
                    priority,
                    request_type,
                    category_id,
                    staff_assigned,
                    requester,
                    date_opened,
                    description,
                    resolution_notes,
                    created_at,
                    updated_at,
                    resolved_at,
                    site_id
                )
                VALUES (
                    :ticket_id,
                    :title,
                    :status,
                    :priority,
                    :request_type,
                    :category_id,
                    :staff_assigned,
                    :requester,
                    CURRENT_DATE,
                    :description,
                    :resolution_notes,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    :resolved_at,
                    :site_id
                )
                RETURNING id, ticket_id
                """
            ),
            {
                "ticket_id": ticket_id,
                "title": title,
                "status": status,
                "priority": priority,
                "request_type": request_type,
                "category_id": category_id,
                "staff_assigned": payload.get("staff_assigned") or None,
                "requester": payload.get("requester") or None,
                "description": payload.get("description") or None,
                "resolution_notes": payload.get("resolution_notes") or None,
                "resolved_at": resolved_at,
                "site_id": payload.get("site_id") or None,
            },
        ).mappings().one()

        label_ids = payload.get("label_ids") or []
        self._replace_ticket_labels(ticket_id, label_ids)
        self.events.record_ticket_event(
            ticket_pk=int(created["id"]),
            event_type="ticket_created",
            actor_id=actor["username"],
            payload={"ticket_id": ticket_id, "status": status, "priority": priority},
        )
        self.db.commit()
        return self.get_ticket_detail(ticket_id)

    def update_ticket(self, ticket_id: str, payload: dict[str, Any], actor: dict[str, Any]) -> Any:
        existing = fetch_ticket_row(self.db, ticket_id)
        if existing is None:
            return None

        updates: list[str] = []
        params: dict[str, Any] = {"ticket_id": ticket_id}
        change_set: dict[str, Any] = {}

        field_map = {
            "title": "title",
            "status": "status",
            "priority": "priority",
            "staff_assigned": "staff_assigned",
            "requester": "requester",
            "description": "description",
            "resolution_notes": "resolution_notes",
            "site_id": "site_id",
            "category_id": "category_id",
        }
        for payload_key, column_name in field_map.items():
            if payload_key not in payload:
                continue
            updates.append(f"{column_name} = :{payload_key}")
            params[payload_key] = payload[payload_key]
            change_set[payload_key] = payload[payload_key]

        if "request_type" in payload or "category_id" in payload:
            request_type = self._resolve_request_type(
                payload.get("category_id", existing.get("category_id")),
                payload.get("request_type", existing.get("request_type")),
            )
            updates.append("request_type = :request_type")
            params["request_type"] = request_type
            change_set["request_type"] = request_type

        next_status = payload.get("status", existing.get("status"))
        updates.append("resolved_at = :resolved_at")
        params["resolved_at"] = self._resolved_at_for_status(str(next_status))

        if not updates and "label_ids" not in payload:
            return self.get_ticket_detail(ticket_id)

        updates.append("updated_at = CURRENT_TIMESTAMP")

        if updates:
            self.db.execute(
                text(
                    f"""
                    UPDATE tickets
                    SET {", ".join(updates)}
                    WHERE ticket_id = :ticket_id
                    """
                ),
                params,
            )

        if "label_ids" in payload:
            self._replace_ticket_labels(ticket_id, payload.get("label_ids") or [])
            change_set["label_ids"] = payload.get("label_ids") or []

        self.events.record_ticket_event(
            ticket_pk=int(existing["id"]),
            event_type="ticket_updated",
            actor_id=actor["username"],
            payload=change_set,
        )
        self.db.commit()
        return self.get_ticket_detail(ticket_id)

    def delete_ticket(self, ticket_id: str, actor: dict[str, Any]) -> Any:
        existing = fetch_ticket_row(self.db, ticket_id)
        if existing is None:
            return False

        self.db.execute(text("DELETE FROM tickets WHERE ticket_id = :ticket_id"), {"ticket_id": ticket_id})
        self.db.commit()
        return True

    def move_ticket(self, ticket_id: str, column: str | None, status: str | None, actor: dict[str, Any]) -> Any:
        next_status = status or self._column_to_status(column)
        if not next_status:
            raise ValueError("A valid target status or column is required")
        return self.update_ticket(ticket_id, {"status": next_status}, actor)

    def set_ticket_labels(self, ticket_id: str, label_ids: list[int], actor: dict[str, Any]) -> Any:
        existing = fetch_ticket_row(self.db, ticket_id)
        if existing is None:
            return False
        self._replace_ticket_labels(ticket_id, label_ids)
        self.events.record_ticket_event(
            ticket_pk=int(existing["id"]),
            event_type="labels_updated",
            actor_id=actor["username"],
            payload={"label_ids": label_ids},
        )
        self.db.commit()
        return True

    def get_ticket_labels(self, ticket_id: str) -> Any:
        rows = self.db.execute(
            text(
                """
                SELECT l.id, l.name, l.color
                FROM ticket_labels tl
                JOIN labels l ON l.id = tl.label_id
                WHERE tl.ticket_id = :ticket_id
                ORDER BY l.name ASC
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings()
        return [dict(row) for row in rows]

    def _replace_ticket_labels(self, ticket_id: str, label_ids: list[int] | object) -> Any:
        normalized_ids = [int(label_id) for label_id in label_ids if str(label_id).strip()]  # type: ignore[union-attr]
        self.db.execute(text("DELETE FROM ticket_labels WHERE ticket_id = :ticket_id"), {"ticket_id": ticket_id})
        for label_id in normalized_ids:
            self.db.execute(
                text(
                    """
                    INSERT INTO ticket_labels (ticket_id, label_id)
                    VALUES (:ticket_id, :label_id)
                    ON CONFLICT DO NOTHING
                    """
                ),
                {"ticket_id": ticket_id, "label_id": label_id},
            )

    def _resolve_request_type(self, category_id: object | None, request_type: object | None) -> Any:
        if category_id:
            row = self.db.execute(
                text("SELECT name FROM categories WHERE id = :category_id"),
                {"category_id": category_id},
            ).mappings().first()
            if row:
                return row["name"]
        return str(request_type or "").strip() or None

    def _get_next_ticket_id(self) -> Any:
        row = self.db.execute(
            text(
                """
                SELECT MAX(CAST(SUBSTRING(ticket_id FROM 4) AS BIGINT)) AS max_ticket_number
                FROM tickets
                WHERE ticket_id LIKE 'IT-%'
                """
            )
        ).mappings().first()
        current_year_seed = int(f"{datetime.now(UTC).year}0000")
        next_number = max(int(row["max_ticket_number"] or 0) + 1, current_year_seed + 1)  # type: ignore[index]
        return f"IT-{next_number}"

    def _resolved_at_for_status(self, status: str) -> Any:
        if status in {"Resolved", "Closed"}:
            return datetime.now(UTC)
        return None

    def _column_to_status(self, column: str | None) -> Any:
        mapping = {
            "TO DO": "Open",
            "IN PROGRESS": "In Progress",
            "IN REVIEW": "Waiting for Info",
            "DONE": "Resolved",
        }
        return mapping.get((column or "").upper())


def _ticket_list_sql(db: Session, *, where_clause: str = "", limit_clause: str = "") -> str:
    category_select, category_join = category_join_sql(db)
    clean_summary_expr = column_expr(db, "tickets", "clean_summary")
    site_id_expr = column_expr(db, "tickets", "site_id")
    asset_id_expr = column_expr(db, "tickets", "asset_id")
    resolved_at_expr = column_expr(db, "tickets", "resolved_at")
    category_id_expr = column_expr(db, "tickets", "category_id")
    return f"""
        SELECT
            t.id,
            t.ticket_id,
            t.title,
            t.status,
            t.priority,
            t.request_type,
            t.staff_assigned,
            t.requester,
            t.date_opened,
            t.description,
            t.resolution_notes,
            t.created_at,
            t.updated_at,
            {resolved_at_expr} AS resolved_at,
            {clean_summary_expr} AS clean_summary,
            {site_id_expr} AS site_id,
            {asset_id_expr} AS asset_id,
            {category_id_expr} AS category_id,
            {category_select}
        FROM tickets t
        {category_join}
        {where_clause}
        ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
        {limit_clause}
    """
