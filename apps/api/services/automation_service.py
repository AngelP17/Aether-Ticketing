"""
Basic in-house Automation Rules engine (if/then for SLA, assign, etc.).
JSON conditions/actions.
Hooks for Activepieces for complex.
"""
import json
import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.action_service import ActionService
from apps.api.services.sla_service import SlaService

logger = logging.getLogger(__name__)

class AutomationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.actions = ActionService(db)
        self.sla = SlaService(db)

    def list_rules(self) -> list[dict[str, Any]]:
        rows = self.db.execute(text("SELECT * FROM automation_rules ORDER BY created_at DESC")).mappings()
        return [dict(r) for r in rows]

    def create_rule(self, data: dict[str, Any]) -> dict[str, Any]:
        res = self.db.execute(
            text("INSERT INTO automation_rules (name, description, enabled, trigger_type, conditions, actions) VALUES (:n, :d, :e, :t, :c, :a) RETURNING id"),
            {
                "n": data.get("name"),
                "d": data.get("description"),
                "e": data.get("enabled", True),
                "t": data.get("trigger_type", "ticket_created"),
                "c": json.dumps(data.get("conditions", [])),
                "a": json.dumps(data.get("actions", [])),
            }
        ).mappings().first()
        self.db.commit()
        return {"id": res["id"]}

    def evaluate_and_execute(self, trigger: str, ticket: dict[str, Any], context: dict[str, Any] | None = None) -> int:
        """Simple engine: load enabled rules for trigger, match conditions, exec actions."""
        rules = self.db.execute(text("SELECT * FROM automation_rules WHERE enabled=true AND trigger_type = :t"), {"t": trigger}).mappings()
        executed = 0
        for rule in rules:
            conditions = json.loads(rule["conditions"] or "[]")
            actions = json.loads(rule["actions"] or "[]")
            if self._matches(ticket, conditions):
                for act in actions:
                    self._execute_action(ticket, act, context)
                executed += 1
                self.db.execute(text("UPDATE automation_rules SET execution_count = execution_count + 1, last_executed_at = NOW() WHERE id = :id"), {"id": rule["id"]})
        self.db.commit()
        return executed

    def _matches(self, ticket: dict, conditions: list) -> bool:
        if not conditions:
            return True
        for cond in conditions:
            field = cond.get("field")
            op = cond.get("op", "equals")
            val = cond.get("value")
            tval = ticket.get(field) or (ticket.get("decision") or {}).get(field)
            if op == "equals" and str(tval) != str(val):
                return False
            if op == "greater_than" and (tval or 0) <= (val or 0):
                return False
            # add more ops as needed
        return True

    def _execute_action(self, ticket: dict, action: dict, context: dict | None) -> None:
        atype = action.get("type")
        if atype == "assign":
            self.actions.assign(ticket["ticket_id"], action.get("value"), actor={"username": "automation"})
        elif atype == "set_priority":
            # direct update
            self.db.execute(text("UPDATE tickets SET priority = :p WHERE ticket_id = :tid"), {"p": action.get("value"), "tid": ticket["ticket_id"]})
            self.db.commit()
        elif atype == "notify":
            # rely on event or email
            pass
        elif atype == "escalate":
            self.sla.update_tracking_on_event(ticket, "sla_breach")
        logger.info("automation executed %s on %s", atype, ticket.get("ticket_id"))
