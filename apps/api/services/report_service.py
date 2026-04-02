from sqlalchemy.orm import Session
from sqlalchemy import text
from openpyxl import Workbook

from apps.api.services.incident_service import IncidentService
from apps.api.services.operational_intelligence import (
    build_ticket_snapshot,
    build_live_decision_map,
    synthesize_incidents,
)


class ReportService:
    def __init__(self, db: Session):
        self.db = db

    def generate_workbook(
        self,
        report_type: str,
        date_from: str | None,
        date_to: str | None,
        incident_id: str | None = None,
    ) -> Workbook:
        from pipelines.reports.excel_report import generate_workbook

        rows = self.db.execute(
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
                    c.name AS category_name
                FROM tickets t
                LEFT JOIN categories c ON c.id = t.category_id
                ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                LIMIT 250
                """
            )
        ).mappings()

        tickets = [dict(row) for row in rows]
        decision_map = build_live_decision_map(tickets)
        snapshots = []
        for ticket in tickets:
            decision = decision_map.get(ticket["ticket_id"])
            snapshot = build_ticket_snapshot(ticket, decision)
            snapshot["category"] = ticket.get("category_name") or ticket.get("request_type")
            snapshot["recommendation"] = (
                decision["recommendations"][0]["action_label"]
                if decision and decision.get("recommendations")
                else ""
            )
            snapshot["sla_risk"] = decision.get("sla_risk_score", 0) if decision else 0
            snapshots.append(snapshot)

        incidents = IncidentService(self.db).list_incidents()
        if incident_id is not None:
            synthesized_incidents = synthesize_incidents(snapshots)
            matched_incident = next(
                (incident for incident in synthesized_incidents if incident["id"] == incident_id),
                None,
            )
            if matched_incident is None:
                raise LookupError(f"Incident {incident_id} not found")

            incident_ticket_ids = {
                ticket["ticket_id"] for ticket in matched_incident["tickets"]
            }
            snapshots = [
                snapshot
                for snapshot in snapshots
                if snapshot["ticket_id"] in incident_ticket_ids
            ]
            incidents = [
                {
                    "id": matched_incident["id"],
                    "title": matched_incident["title"],
                    "status": matched_incident["status"],
                    "root_cause_hypothesis": matched_incident["root_cause_hypothesis"],
                    "ticket_count": matched_incident["ticket_count"],
                    "confidence": matched_incident["confidence"],
                    "business_impact_score": matched_incident["business_impact_score"],
                    "opened_at": matched_incident["opened_at"],
                }
            ]

        return generate_workbook(report_type, tickets=snapshots, incidents=incidents)
