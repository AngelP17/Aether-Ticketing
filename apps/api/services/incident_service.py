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
        snapshots = [
            build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"]))
            for ticket in tickets
        ]
        return synthesize_incidents(snapshots)
