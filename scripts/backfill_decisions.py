from __future__ import annotations

from sqlalchemy import text

from infrastructure.db.session import get_db_context, init_db
from apps.api.services.decision_service import DecisionService


def main() -> None:
    init_db()
    with get_db_context() as db:
        service = DecisionService(db)
        ticket_ids = [
            row["ticket_id"]
            for row in db.execute(text("SELECT ticket_id FROM tickets ORDER BY id ASC")).mappings()
        ]
        for ticket_id in ticket_ids:
            service.recompute_decision(ticket_id)
            print(f"Backfilled decision for {ticket_id}")


if __name__ == "__main__":
    main()
