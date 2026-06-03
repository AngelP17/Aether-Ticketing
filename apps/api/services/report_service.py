from typing import Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from openpyxl import Workbook

from apps.api.services.incident_service import IncidentService
from apps.api.services.operational_intelligence import (
    build_ticket_snapshot,
    compute_live_decision,
    count_similar_cases,
    synthesize_incidents,
)
from apps.api.services.schema_compat import category_join_sql, column_expr


class ReportService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _load_report_payload(
        self,
        report_type: str,
        date_from: str | None,
        date_to: str | None,
        incident_id: str | None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        category_select, category_join = category_join_sql(self.db)
        clean_summary_expr = column_expr(self.db, "tickets", "clean_summary")
        site_id_expr = column_expr(self.db, "tickets", "site_id")
        asset_id_expr = column_expr(self.db, "tickets", "asset_id")
        resolved_at_expr = column_expr(self.db, "tickets", "resolved_at")
        rows = self.db.execute(
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
                    {resolved_at_expr} AS resolved_at,
                    {clean_summary_expr} AS clean_summary,
                    {site_id_expr} AS site_id,
                    {asset_id_expr} AS asset_id,
                    {category_select}
                FROM tickets t
                {category_join}
                ORDER BY COALESCE(t.updated_at, t.created_at) DESC NULLS LAST, t.id DESC
                """
            )
        ).mappings()

        tickets = [dict(row) for row in rows]
        snapshots = [_build_export_snapshot(ticket, self.db) for ticket in tickets]

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

        return snapshots, incidents

    def generate_workbook(
        self,
        report_type: str,
        date_from: str | None,
        date_to: str | None,
        incident_id: str | None = None,
    ) -> Workbook:
        from pipelines.reports.excel_report import generate_workbook

        snapshots, incidents = self._load_report_payload(
            report_type, date_from, date_to, incident_id
        )
        return generate_workbook(report_type, tickets=snapshots, incidents=incidents)

    def generate_csv(
        self,
        report_type: str,
        date_from: str | None,
        date_to: str | None,
        incident_id: str | None = None,
    ) -> str:
        from pipelines.reports.csv_report import generate_csv

        snapshots, incidents = self._load_report_payload(
            report_type, date_from, date_to, incident_id
        )
        return generate_csv(report_type, tickets=snapshots, incidents=incidents)


def _build_export_snapshot(ticket: dict[str, Any], db: Session) -> dict[str, Any]:
    try:
        from apps.api.services.graph_intelligence_service import features_for_ticket

        gfeat = features_for_ticket(db, ticket.get("ticket_id", ""))
        gcent = float(gfeat.get("graph_centrality", 0.0) or 0.0)
    except Exception:
        gcent = 0.0
    decision = compute_live_decision(
        ticket,
        similar_cases_count=count_similar_cases(db, ticket),
        include_recommendations=True,
        include_artifacts=False,
        graph_centrality=gcent,
    )
    snapshot = build_ticket_snapshot(ticket, decision)
    snapshot["category"] = ticket.get("category_name") or ticket.get("request_type")
    recommendations = decision.get("recommendations") or []
    snapshot["recommendation"] = (
        recommendations[0]["action_label"] if recommendations else ""
    )
    snapshot["recommendation_risk"] = (
        recommendations[0]["risk_level"] if recommendations else ""
    )
    snapshot["sla_risk"] = decision.get("sla_risk_score", 0) or 0
    return snapshot
