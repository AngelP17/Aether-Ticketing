import json
import logging
import math
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
from apps.api.services.sla_service import SlaService
from apps.api.services.automation_service import AutomationService
from apps.api.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)


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
        category_join = ""

        if kwargs.get("status"):
            filters.append("t.status = :status")
            params["status"] = kwargs["status"]
        if kwargs.get("priority"):
            filters.append("t.priority = :priority")
            params["priority"] = kwargs["priority"]
        if kwargs.get("category"):
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
        try:
            _, category_join = category_join_sql(self.db)
            effective_where_clause = where_clause
            if kwargs.get("category") and category_join:
                category_filters = [
                    "COALESCE(c.name, t.request_type) = :category"
                    if item == "t.request_type = :category"
                    else item
                    for item in filters
                ]
                effective_where_clause = (
                    f"WHERE {' AND '.join(category_filters)}" if category_filters else ""
                )
            rows = list(
                self.db.execute(
                    text(
                        _ticket_list_sql(
                            self.db,
                            where_clause=effective_where_clause,
                            limit_clause="LIMIT :sql_limit OFFSET :sql_offset",
                        )
                    ),
                    params,
                ).mappings()
            )
        except Exception:
            logger.exception("ticket list compatibility query failed; using base ticket query")
            rows = list(
                self.db.execute(
                    text(
                        _base_ticket_list_sql(
                            where_clause=where_clause,
                            limit_clause="LIMIT :sql_limit OFFSET :sql_offset",
                        )
                    ),
                    params,
                ).mappings()
            )

        tickets = [dict(row) for row in rows]
        try:
            decision_map = build_live_decision_map(tickets)
        except Exception:
            logger.exception("ticket decision enrichment failed; returning base ticket snapshots")
            decision_map = {}
        snapshots = []
        for ticket in tickets:
            try:
                snapshots.append(
                    build_ticket_snapshot(ticket, decision=decision_map.get(ticket["ticket_id"]))
                )
            except Exception:
                logger.exception(
                    "ticket snapshot failed; returning minimal live snapshot",
                    extra={"ticket_id": ticket.get("ticket_id")},
                )
                snapshots.append(_fallback_ticket_snapshot(ticket))

        try:
            incidents = synthesize_incidents(snapshots)
        except Exception:
            logger.exception("ticket incident enrichment failed; returning tickets without incident links")
            incidents = []
        incident_lookup = {
            ticket["ticket_id"]: incident.get("id") or incident.get("incident_key")
            for incident in incidents
            for ticket in incident.get("tickets", [])
            if ticket.get("ticket_id")
        }
        for snapshot in snapshots:
            snapshot["incident_id"] = incident_lookup.get(snapshot["ticket_id"])
        snapshots = [_json_safe_snapshot(snapshot) for snapshot in snapshots]

        if ranking:
            snapshots.sort(
                key=lambda ticket: ticket.get("priority_score") or 0,
                reverse=True,
            )
            return snapshots[offset : offset + limit]

        return snapshots

    def get_ticket_detail(self, ticket_id: str) -> Any:
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        try:
            decision = DecisionService(self.db).get_latest_decision(ticket_id)
        except Exception:
            logger.exception("ticket decision detail failed", extra={"ticket_id": ticket_id})
            decision = None

        try:
            similar_cases = fetch_similar_cases(self.db, ticket)
        except Exception:
            logger.exception("ticket similar-case detail failed", extra={"ticket_id": ticket_id})
            similar_cases = []

        try:
            events = EventService(self.db).get_ticket_event_stream(ticket_id)
        except Exception:
            logger.exception("ticket event stream failed", extra={"ticket_id": ticket_id})
            events = []

        incident = self._linked_incident_for_ticket(ticket_id)

        try:
            ticket_snapshot = build_ticket_snapshot(
                ticket,
                decision=decision,
                incident_id=incident.get("id") or incident.get("incident_key") if incident else None,
            )
        except Exception:
            logger.exception("ticket detail snapshot failed", extra={"ticket_id": ticket_id})
            ticket_snapshot = _fallback_ticket_snapshot(ticket)

        try:
            labels = self.get_ticket_labels(ticket_id)
        except Exception:
            logger.exception("ticket labels failed", extra={"ticket_id": ticket_id})
            labels = []

        try:
            comments = self.comments.list_comments(ticket_id)
        except Exception:
            logger.exception("ticket comments failed", extra={"ticket_id": ticket_id})
            comments = []

        try:
            attachments = [
                attachment
                for attachment in self.attachments.list_attachments(ticket_id)
                if attachment.get("comment_id") is None
            ]
        except Exception:
            logger.exception("ticket attachments failed", extra={"ticket_id": ticket_id})
            attachments = []

        payload = {
            "ticket": {
                **ticket_snapshot,
                "request_type": ticket.get("request_type") or ticket.get("category_name"),
                "requester": ticket.get("requester"),
                "description": ticket.get("description") or "",
                "resolution_notes": ticket.get("resolution_notes") or "",
                "category": ticket.get("category_name") or ticket.get("request_type"),
                "category_id": ticket.get("category_id"),
                "labels": labels,
            },
            "decision": decision,
            "recommendations": decision.get("recommendations", []) if isinstance(decision, dict) else [],
            "similar_cases": similar_cases,
            "events": events,
            "linked_incident": incident,
            "comments": comments,
            "attachments": attachments,
        }
        return _json_safe_value(payload)

    def _linked_incident_for_ticket(self, ticket_id: str) -> dict[str, Any] | None:
        """Optimized linked incident lookup.

        Fast path: use persisted incident_ticket_links (avoids full table scan).
        Fallback: only load a small bounded set of *candidate* open tickets that share
        site/asset/category/requester with the target (instead of unconditional LIMIT 200).
        This eliminates the previous N+1/perf killer on every ticket detail view.
        """
        try:
            # 1. Fast persisted link path (post-persistence)
            link_row = self.db.execute(
                text(
                    """
                    SELECT
                        i.id,
                        i.incident_key,
                        i.title,
                        i.status,
                        i.root_cause_hypothesis,
                        i.site_scope,
                        i.ticket_count,
                        i.confidence,
                        i.opened_at
                    FROM incidents i
                    JOIN incident_ticket_links itl ON itl.incident_id = i.id
                    WHERE itl.ticket_id = (
                        SELECT id FROM tickets WHERE ticket_id = :ticket_id LIMIT 1
                    )
                    LIMIT 1
                    """
                ),
                {"ticket_id": ticket_id},
            ).mappings().first()

            if link_row:
                return dict(link_row)
        except Exception:
            logger.exception("persisted linked incident lookup failed", extra={"ticket_id": ticket_id})

        # 2. Bounded fallback synthesis only on relevant candidates
        try:
            ticket = fetch_ticket_row(self.db, ticket_id)
            if ticket is None:
                return None

            # Small candidate pool: recent open tickets sharing key attributes
            # (prevents OOM and N+1 on detail views)
            site = ticket.get("site_id")
            asset = ticket.get("asset_id")
            cat = ticket.get("request_type") or ticket.get("category_name")
            req = ticket.get("requester")

            where_parts = ["t.status NOT IN ('Resolved', 'Closed')"]
            params: dict[str, Any] = {"ticket_id": ticket_id}
            if site:
                where_parts.append("t.site_id = :site")
                params["site"] = site
            if asset:
                where_parts.append("t.asset_id = :asset")
                params["asset"] = asset
            if cat:
                where_parts.append("COALESCE(t.request_type, '') = :cat")
                params["cat"] = cat
            if req:
                where_parts.append("t.requester = :req")
                params["req"] = req

            where_clause = "WHERE " + " OR ".join(where_parts) if len(where_parts) > 1 else where_parts[0]
            # also include the target ticket itself for synthesis
            where_clause = f"({where_clause}) OR t.ticket_id = :ticket_id"

            rows = list(
                self.db.execute(
                    text(
                        _ticket_list_sql(
                            self.db,
                            where_clause=where_clause,
                            limit_clause="LIMIT 40",  # bounded, attribute-filtered
                        )
                    ),
                    params,
                ).mappings()
            )
            incident_rows = [dict(row) for row in rows]

            try:
                incident_decision_map = build_live_decision_map(incident_rows)
            except Exception:
                logger.exception("ticket detail incident decision enrichment failed (bounded)")
                incident_decision_map = {}

            snapshots = []
            for row in incident_rows:
                try:
                    snapshots.append(
                        build_ticket_snapshot(
                            row,
                            incident_decision_map.get(row["ticket_id"]),
                        )
                    )
                except Exception:
                    logger.exception(
                        "ticket detail incident snapshot failed (bounded)",
                        extra={"ticket_id": row.get("ticket_id")},
                    )
                    snapshots.append(_fallback_ticket_snapshot(row))

            return next(
                (
                    current
                    for current in synthesize_incidents(snapshots)
                    if any(item.get("ticket_id") == ticket_id for item in current.get("tickets", []))
                ),
                None,
            )
        except Exception:
            logger.exception("ticket linked incident lookup failed (bounded)", extra={"ticket_id": ticket_id})
            return None

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
                    site_id,
                    custom_fields
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
                    :site_id,
                    :custom_fields
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
                "custom_fields": json.dumps(payload.get("custom_fields") or payload.get("customFields") or {}) if (payload.get("custom_fields") or payload.get("customFields")) else None,
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
        # SLA
        try:
            SlaService(self.db).ensure_tracking(int(created["id"]))
            SlaService(self.db).update_tracking_on_event({"id": int(created["id"]), "ticket_id": ticket_id, **payload, "status": status, "priority": priority, "days_open": 0}, "ticket_created")
        except Exception:
            logger.exception("SLA tracking on create failed (non-fatal)")
        # Automation
        try:
            AutomationService(self.db).evaluate_and_execute("ticket_created", {"ticket_id": ticket_id, "id": int(created["id"]), **payload, "status": status, "priority": priority})
        except Exception:
            logger.exception("automation on create failed (non-fatal)")
        # Webhook for OSS
        try:
            WebhookService(self.db).dispatch("ticket.created", {"ticket_id": ticket_id, "status": status, "priority": priority, "requester": payload.get("requester")})
        except Exception:
            logger.exception("webhook ticket.created failed (non-fatal)")
        self.db.commit()
        try:
            return self.get_ticket_detail(ticket_id)
        except Exception:
            logger.exception("get after create/update failed, returning minimal")
            return {"ticket_id": ticket_id, "title": payload.get("title") or "", "status": payload.get("status") or "Open", "priority": payload.get("priority") or "Low"}

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
            "custom_fields": "custom_fields",
        }
        for payload_key, column_name in field_map.items():
            if payload_key not in payload:
                continue
            updates.append(f"{column_name} = :{payload_key}")
            val = payload[payload_key]
            if payload_key == "custom_fields" and isinstance(val, (dict, list)):
                val = json.dumps(val)
            params[payload_key] = val
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
        # SLA update
        try:
            SlaService(self.db).update_tracking_on_event({"id": int(existing["id"]), "ticket_id": ticket_id, **existing, **payload, "status": next_status}, "status_changed" if "status" in payload else "field_updated")
        except Exception:
            logger.exception("SLA on update failed (non-fatal)")
        # Automation + webhook
        try:
            AutomationService(self.db).evaluate_and_execute("ticket_updated", {"ticket_id": ticket_id, **existing, **payload, "status": next_status})
            WebhookService(self.db).dispatch("ticket.updated", {"ticket_id": ticket_id, "changes": change_set})
        except Exception:
            logger.exception("automation/webhook on update failed (non-fatal)")
        self.db.commit()
        try:
            return self.get_ticket_detail(ticket_id)
        except Exception:
            logger.exception("get after create/update failed, returning minimal")
            return {"ticket_id": ticket_id, "title": payload.get("title") or "", "status": payload.get("status") or "Open", "priority": payload.get("priority") or "Low"}

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
            t.custom_fields AS custom_fields,
            {category_select}
        FROM tickets t
        {category_join}
        {where_clause}
        ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
        {limit_clause}
    """


def _base_ticket_list_sql(*, where_clause: str = "", limit_clause: str = "") -> str:
    return f"""
        SELECT
            t.id,
            t.ticket_id,
            t.title,
            COALESCE(t.status, 'Open') AS status,
            COALESCE(t.priority, 'Low') AS priority,
            t.request_type,
            t.staff_assigned,
            t.requester,
            t.date_opened,
            t.description,
            t.resolution_notes,
            t.created_at,
            t.updated_at,
            NULL AS resolved_at,
            NULL AS clean_summary,
            NULL AS site_id,
            NULL AS asset_id,
            NULL AS category_id,
            NULL AS category_name
        FROM tickets t
        {where_clause}
        ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
        {limit_clause}
    """


def _fallback_ticket_snapshot(ticket: dict[str, Any]) -> dict[str, Any]:
    priority = _safe_text(ticket.get("priority"), default="Low")
    request_type = _safe_text(ticket.get("category_name") or ticket.get("request_type"))
    return {
        "ticket_id": _safe_text(ticket.get("ticket_id"), default="UNKNOWN"),
        "title": _safe_text(ticket.get("title"), default="Untitled ticket"),
        "status": _safe_text(ticket.get("status"), default="Open"),
        "priority_raw": priority,
        "priority_score": None,
        "root_cause_hypothesis": None,
        "confidence_score": None,
        "site": _safe_text(ticket.get("site_id")) or None,
        "assignee": _safe_text(ticket.get("staff_assigned")) or None,
        "category": request_type or None,
        "created_at": _safe_datetime_text(ticket.get("created_at") or ticket.get("date_opened")),
        "days_open": 0,
        "incident_id": None,
        "description": _safe_text(ticket.get("description")) or None,
        "resolution_notes": _safe_text(ticket.get("resolution_notes")) or None,
        "requester": _safe_text(ticket.get("requester")) or None,
        "custom_fields": ticket.get("custom_fields"),
    }


def _json_safe_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: _json_safe_value(value) for key, value in snapshot.items()}


def _json_safe_value(value: object) -> object:
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return value


def _safe_text(value: object, *, default: str = "") -> str:
    if value is None:
        return default
    try:
        text_value = str(value).strip()
    except Exception:
        return default
    return text_value or default


def _safe_datetime_text(value: object) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    return _safe_text(value, default=datetime.now(UTC).isoformat())
