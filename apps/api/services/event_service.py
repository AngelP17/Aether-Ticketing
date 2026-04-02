from sqlalchemy.orm import Session
from sqlalchemy import text

from apps.api.services.operational_intelligence import fetch_ticket_row

class EventService:
    def __init__(self, db: Session):
        self.db = db

    def get_ticket_event_stream(self, ticket_id: str):
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return []

        rows = self.db.execute(
            text(
                """
                SELECT
                    event_type,
                    event_ts,
                    actor_type,
                    actor_id,
                    payload_json
                FROM ticket_events
                WHERE ticket_id = :ticket_pk
                ORDER BY event_ts ASC, id ASC
                """
            ),
            {"ticket_pk": ticket["id"]},
        ).mappings()
        events = [
            {
                "event_type": row["event_type"],
                "event_ts": row["event_ts"].isoformat() if row["event_ts"] else None,
                "actor_type": row["actor_type"],
                "actor_id": row["actor_id"],
                "payload": row["payload_json"],
            }
            for row in rows
        ]
        if events:
            return events
        created_at = ticket.get("created_at") or ticket.get("date_opened")
        return [
            {
                "event_type": "ticket_created",
                "event_ts": created_at.isoformat() if hasattr(created_at, "isoformat") else str(created_at),
                "actor_type": "legacy",
                "actor_id": "flask-app",
                "payload": {
                    "status": ticket.get("status"),
                    "priority": ticket.get("priority"),
                },
            }
        ]
