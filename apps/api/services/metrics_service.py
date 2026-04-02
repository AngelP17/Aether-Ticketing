from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.operational_intelligence import (
    build_live_decision_map,
    build_ticket_snapshot,
    synthesize_incidents,
)
from domain.policies import SLATargetHours


class MetricsService:
    def __init__(self, db: Session):
        self.db = db

    def get_queue_metrics(self) -> dict:
        rows = list(
            self.db.execute(
                text(
                    """
                    SELECT
                        t.ticket_id,
                        t.title,
                        t.status,
                        t.priority,
                        t.request_type,
                        t.staff_assigned,
                        t.date_opened,
                        t.description,
                        t.created_at,
                        t.site_id,
                        t.asset_id,
                        c.name AS category_name
                    FROM tickets t
                    LEFT JOIN categories c ON c.id = t.category_id
                    WHERE status NOT IN ('Resolved', 'Closed')
                    """
                )
            ).mappings()
        )
        tickets = [dict(row) for row in rows]
        critical = [ticket for ticket in tickets if ticket["priority"] == "Critical"]
        sla_risk = sum(1 for ticket in tickets if _is_sla_risk(ticket))
        decision_map = build_live_decision_map(tickets)
        incident_clusters = synthesize_incidents(
            [
                build_ticket_snapshot(ticket, decision_map.get(ticket["ticket_id"]))
                for ticket in tickets
            ]
        )
        return {
            "total_open": len(tickets),
            "critical": len(critical),
            "sla_breach_risk": sla_risk,
            "incident_clusters": len(incident_clusters),
        }


def _is_sla_risk(ticket: dict) -> bool:
    opened_at = ticket.get("date_opened")
    if opened_at is None:
        return False

    if isinstance(opened_at, datetime):
        opened_date = opened_at.date()
    elif isinstance(opened_at, date):
        opened_date = opened_at
    else:
        try:
            opened_date = datetime.fromisoformat(str(opened_at)).date()
        except ValueError:
            return False

    elapsed_hours = max((datetime.utcnow().date() - opened_date).days, 0) * 24
    sla_target = SLATargetHours.get(ticket.get("priority") or "Medium", 24.0)
    return elapsed_hours >= sla_target * 0.75
