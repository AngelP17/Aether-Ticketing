from sqlalchemy.orm import Session

from apps.api.services.operational_intelligence import (
    build_ticket_snapshot,
    build_live_decision_map,
    fetch_similar_cases,
    fetch_ticket_row,
    synthesize_incidents,
)
from apps.api.services.decision_service import DecisionService
from apps.api.services.event_service import EventService
from sqlalchemy import text


class TicketService:
    def __init__(self, db: Session):
        self.db = db

    def list_tickets(self, **kwargs):
        filters = []
        params: dict[str, object] = {}
        ranking = kwargs.get("ranking", False)
        offset = kwargs.get("offset", 0)
        limit = kwargs.get("limit", 50)

        if kwargs.get("status"):
            filters.append("t.status = :status")
            params["status"] = kwargs["status"]
        if kwargs.get("priority"):
            filters.append("t.priority = :priority")
            params["priority"] = kwargs["priority"]
        if kwargs.get("category"):
            filters.append("COALESCE(c.name, t.request_type) = :category")
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
                f"""
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
                    t.clean_summary,
                    t.site_id,
                    t.asset_id,
                    c.name AS category_name
                FROM tickets t
                LEFT JOIN categories c ON c.id = t.category_id
                {where_clause}
                ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                LIMIT :sql_limit
                OFFSET :sql_offset
                """
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

    def get_ticket_detail(self, ticket_id: str):
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        decisions = DecisionService(self.db)
        decision = decisions.get_latest_decision(ticket_id)
        similar_cases = fetch_similar_cases(self.db, ticket)
        events = EventService(self.db).get_ticket_event_stream(ticket_id)

        all_rows = list(
            self.db.execute(
                text(
                    """
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
                        t.clean_summary,
                        t.site_id,
                        t.asset_id,
                        c.name AS category_name
                    FROM tickets t
                    LEFT JOIN categories c ON c.id = t.category_id
                    ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                    """
                )
            ).mappings()
        )
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
            },
            "decision": decision,
            "recommendations": decision.get("recommendations", []) if decision else [],
            "similar_cases": similar_cases,
            "events": events,
            "linked_incident": incident,
        }

    def get_ticket_events(self, ticket_id: str):
        return EventService(self.db).get_ticket_event_stream(ticket_id)
