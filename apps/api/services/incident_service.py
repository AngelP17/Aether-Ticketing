from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.incident_persistence import (
    get_persisted_incident_detail,
    list_persisted_incidents,
    persist_synthesized_incidents,
)
from apps.api.services.operational_intelligence import (
    build_live_decision_map,
    build_ticket_snapshot,
    synthesize_incidents,
)
from apps.api.services.schema_compat import category_join_sql, column_expr


class IncidentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_incidents(self) -> list[dict[str, Any]]:
        clusters = self._build_clusters()
        if clusters:
            persist_synthesized_incidents(self.db, clusters)
        return list_persisted_incidents(self.db)

    def get_incident_detail(self, incident_id: int) -> dict[str, Any] | None:
        clusters = self._build_clusters()
        if clusters:
            persist_synthesized_incidents(self.db, clusters)
        return get_persisted_incident_detail(self.db, incident_id)

    def _build_clusters(self) -> list[dict[str, Any]]:
        category_select, category_join = category_join_sql(self.db)
        clean_summary_expr = column_expr(self.db, "tickets", "clean_summary")
        site_id_expr = column_expr(self.db, "tickets", "site_id")
        asset_id_expr = column_expr(self.db, "tickets", "asset_id")
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
                        {clean_summary_expr} AS clean_summary,
                        {site_id_expr} AS site_id,
                        {asset_id_expr} AS asset_id,
                        {category_select}
                    FROM tickets t
                    {category_join}
                    WHERE t.status NOT IN ('Resolved', 'Closed')
                    ORDER BY t.date_opened DESC NULLS LAST, t.id DESC
                    LIMIT 120
                    """
                )
            ).mappings()
        )
        tickets = [dict(row) for row in rows]
        decision_map = build_live_decision_map(tickets)
        snapshots = [
            build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"]))
            for ticket in tickets
        ]
        return synthesize_incidents(snapshots)
