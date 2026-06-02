from __future__ import annotations

import logging
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

logger = logging.getLogger(__name__)


class IncidentService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_incidents(self) -> list[dict[str, Any]]:
        try:
            clusters = self._build_clusters()
        except Exception:
            logger.exception("incident cluster synthesis failed")
            clusters = []
        if clusters:
            try:
                persist_synthesized_incidents(self.db, clusters)
            except Exception:
                logger.exception("incident persistence failed; returning synthesized clusters")
                return _incident_list_from_clusters(clusters)
        try:
            return list_persisted_incidents(self.db)
        except Exception:
            logger.exception("persisted incident list failed; returning synthesized clusters")
            return _incident_list_from_clusters(clusters)

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
        try:
            decision_map = build_live_decision_map(tickets)
        except Exception:
            logger.exception("incident decision enrichment failed")
            decision_map = {}
        snapshots = []
        for ticket in tickets:
            try:
                snapshots.append(build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"])))
            except Exception:
                logger.exception(
                    "incident ticket snapshot failed",
                    extra={"ticket_id": ticket.get("ticket_id")},
                )
        return synthesize_incidents(snapshots)


def _incident_list_from_clusters(clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    incidents: list[dict[str, Any]] = []
    for index, cluster in enumerate(clusters, start=1):
        incidents.append(
            {
                "id": int(cluster.get("id") or index),
                "incident_key": cluster.get("incident_key") or f"INC-LIVE-{index:04d}",
                "title": cluster.get("title") or "Live incident cluster",
                "status": cluster.get("status") or "open",
                "root_cause_hypothesis": cluster.get("root_cause_hypothesis"),
                "site_scope": cluster.get("site_scope"),
                "ticket_count": int(cluster.get("ticket_count") or len(cluster.get("tickets", []))),
                "confidence": float(cluster.get("confidence") or 0.0),
                "business_impact_score": float(cluster.get("business_impact_score") or 0.0),
                "opened_at": cluster.get("opened_at"),
                "last_updated_at": cluster.get("last_updated_at") or cluster.get("opened_at"),
                "graph_evidence": cluster.get("graph_evidence"),
            }
        )
    return incidents
