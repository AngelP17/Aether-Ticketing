from sqlalchemy.orm import Session

from apps.api.services.operational_intelligence import (
    build_live_decision_map,
    build_ticket_snapshot,
    synthesize_incidents,
)
from sqlalchemy import text


class IncidentService:
    def __init__(self, db: Session):
        self.db = db

    def list_incidents(self):
        rows = list(
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
                    WHERE t.status NOT IN ('Resolved', 'Closed')
                    ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                    LIMIT 120
                    """
                )
            ).mappings()
        )
        tickets = [dict(row) for row in rows]
        decision_map = build_live_decision_map(tickets)
        ticket_snapshots = [
            build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"]))
            for ticket in tickets
        ]
        incidents = synthesize_incidents(ticket_snapshots)
        return [
            {
                "id": incident["id"],
                "title": incident["title"],
                "status": incident["status"],
                "root_cause_hypothesis": incident["root_cause_hypothesis"],
                "ticket_count": incident["ticket_count"],
                "confidence": incident["confidence"],
                "business_impact_score": incident["business_impact_score"],
                "opened_at": incident["opened_at"],
            }
            for incident in incidents
        ]

    def get_incident_detail(self, incident_id: str):
        rows = list(
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
                    WHERE t.status NOT IN ('Resolved', 'Closed')
                    ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                    LIMIT 120
                    """
                )
            ).mappings()
        )
        tickets = [dict(row) for row in rows]
        decision_map = build_live_decision_map(tickets)
        incidents = synthesize_incidents(
            [
                build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"]))
                for ticket in tickets
            ]
        )
        incident = next((item for item in incidents if item["id"] == incident_id), None)
        if incident is None:
            return None
        return {
            "incident": {
                "id": incident["id"],
                "title": incident["title"],
                "status": incident["status"],
                "ticket_count": incident["ticket_count"],
                "confidence": incident["confidence"],
                "business_impact_score": incident["business_impact_score"],
                "opened_at": incident["opened_at"],
            },
            "tickets": incident["tickets"],
            "common_cause": incident["common_cause"],
            "recommended_action": incident["recommended_action"],
        }
