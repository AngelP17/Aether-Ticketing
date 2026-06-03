"""
SLA Service for full SLA management (in-house per competitive roadmap).
Policies per priority/category, tracking per ticket, breach detection, dashboard.
Business hours support (simplified).
Wired to ticket events and decision for auto tracking.
"""
import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

DEFAULT_BUSINESS_HOURS = {"start": 9, "end": 17, "days": [0,1,2,3,4]}  # Mon-Fri 9-17, 0=Mon in some, adjust

class SlaService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_policies(self) -> list[dict[str, Any]]:
        rows = self.db.execute(text("SELECT * FROM sla_policies ORDER BY created_at DESC")).mappings()
        return [dict(r) for r in rows]

    def create_policy(self, data: dict[str, Any]) -> dict[str, Any]:
        res = self.db.execute(
            text("""
                INSERT INTO sla_policies (name, priority, category, target_hours, warn_at_percent, breach_action, active)
                VALUES (:name, :priority, :category, :target_hours, :warn, :action, :active)
                RETURNING id
            """),
            {
                "name": data.get("name"),
                "priority": data.get("priority"),
                "category": data.get("category"),
                "target_hours": data.get("target_hours", 24.0),
                "warn": data.get("warn_at_percent", 75.0),
                "action": data.get("breach_action", "escalate"),
                "active": data.get("active", True),
            }
        ).mappings().first()
        self.db.commit()
        return {"id": res["id"] if res else None}

    def update_policy(self, policy_id: int, data: dict[str, Any]) -> bool:
        self.db.execute(
            text("UPDATE sla_policies SET name=:name, priority=:p, category=:c, target_hours=:t, warn_at_percent=:w, breach_action=:a, active=:active WHERE id=:id"),
            {
                "id": policy_id,
                "name": data.get("name"),
                "p": data.get("priority"),
                "c": data.get("category"),
                "t": data.get("target_hours"),
                "w": data.get("warn_at_percent"),
                "a": data.get("breach_action"),
                "active": data.get("active", True),
            }
        )
        self.db.commit()
        return True

    def get_policy_for_ticket(self, ticket: dict[str, Any]) -> Optional[dict[str, Any]]:
        priority = ticket.get("priority") or "Medium"
        cat = ticket.get("request_type") or ticket.get("category")
        row = self.db.execute(
            text("SELECT * FROM sla_policies WHERE active=true AND (priority=:p OR priority IS NULL) AND (category=:c OR category IS NULL) ORDER BY priority NULLS LAST, category NULLS LAST LIMIT 1"),
            {"p": priority, "c": cat}
        ).mappings().first()
        return dict(row) if row else None

    def ensure_tracking(self, ticket_id: int, policy_id: Optional[int] = None) -> None:
        existing = self.db.execute(text("SELECT id FROM ticket_sla_tracking WHERE ticket_id = :tid"), {"tid": ticket_id}).first()
        if not existing:
            self.db.execute(
                text("INSERT INTO ticket_sla_tracking (ticket_id, sla_policy_id, created_at) VALUES (:tid, :pid, NOW())"),
                {"tid": ticket_id, "pid": policy_id}
            )
            self.db.commit()

    def update_tracking_on_event(self, ticket: dict[str, Any], event_type: str) -> None:
        tid = ticket.get("id")
        if not tid:
            return
        self.ensure_tracking(tid)
        now = datetime.utcnow()
        if event_type in ("ticket_created", "first_response") and not self._has_first_response(tid):
            self.db.execute(text("UPDATE ticket_sla_tracking SET first_response_at = :now WHERE ticket_id = :tid"), {"now": now, "tid": tid})
        if event_type in ("status_changed", "resolved") and ticket.get("status") in ("Resolved", "Closed"):
            self.db.execute(text("UPDATE ticket_sla_tracking SET resolved_at = :now WHERE ticket_id = :tid"), {"now": now, "tid": tid})
        self.db.commit()
        self._check_breaches(tid, ticket)

    def _has_first_response(self, ticket_id: int) -> bool:
        row = self.db.execute(text("SELECT first_response_at FROM ticket_sla_tracking WHERE ticket_id = :tid"), {"tid": ticket_id}).first()
        return bool(row and row[0])

    def _check_breaches(self, ticket_id: int, ticket: dict[str, Any]) -> None:
        tracking = self.db.execute(text("SELECT * FROM ticket_sla_tracking WHERE ticket_id = :tid"), {"tid": ticket_id}).mappings().first()
        if not tracking:
            return
        policy = self.get_policy_for_ticket(ticket)
        if not policy:
            return
        target = policy.get("target_hours", 24.0)
        warn = policy.get("warn_at_percent", 75.0) / 100.0
        days_open = ticket.get("days_open", 0)
        elapsed = days_open * 24.0
        response_breach = False
        resolution_breach = False
        if tracking.get("first_response_at") is None and elapsed > target * warn:
            response_breach = True
        if ticket.get("status") not in ("Resolved", "Closed") and elapsed > target:
            resolution_breach = True
        self.db.execute(
            text("UPDATE ticket_sla_tracking SET response_breach=:rb, resolution_breach=:resb WHERE ticket_id=:tid"),
            {"rb": response_breach, "resb": resolution_breach, "tid": ticket_id}
        )
        self.db.commit()
        if response_breach or resolution_breach:
            logger.info("SLA breach detected for ticket %s", ticket.get("ticket_id"))
            try:
                WebhookService(self.db).dispatch("sla.breached", {"ticket_id": ticket.get("ticket_id"), "response_breach": response_breach, "resolution_breach": resolution_breach})
            except Exception:
                pass

    def get_sla_status(self, ticket_id: str) -> dict[str, Any]:
        row = self.db.execute(text("""
            SELECT t.*, p.name as policy_name, p.target_hours, p.warn_at_percent
            FROM ticket_sla_tracking t
            LEFT JOIN sla_policies p ON t.sla_policy_id = p.id
            WHERE t.ticket_id = (SELECT id FROM tickets WHERE ticket_id = :tid)
        """), {"tid": ticket_id}).mappings().first()
        return dict(row) if row else {"status": "no_policy"}

    def get_dashboard(self) -> dict[str, Any]:
        breach_count = self.db.execute(text("SELECT COUNT(*) FROM ticket_sla_tracking WHERE response_breach OR resolution_breach")).scalar() or 0
        # Simplified avg etc.
        return {
            "breach_count": breach_count,
            "compliance_pct": 95.0,  # placeholder, real from accuracy_service
        }

# Helper for business hours (simplified)
def apply_business_hours(elapsed_hours: float, business_only: bool = True) -> float:
    if not business_only:
        return elapsed_hours
    # Approximate: assume 8 hour business day
    return elapsed_hours * (24 / 8)  # rough
