from __future__ import annotations

import argparse
from datetime import UTC, datetime

from sqlalchemy import text

from apps.api.services.decision_service import DecisionService
from infrastructure.db.session import get_db_context, init_db


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Populate Aether intelligence tables from the existing ticketing data."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=25,
        help="How many of the most recent tickets to recompute decisions for.",
    )
    args = parser.parse_args()

    init_db()
    with get_db_context() as db:
        service = DecisionService(db)
        rows = db.execute(
            text(
                """
                SELECT ticket_id
                FROM tickets
                ORDER BY date_opened DESC NULLS LAST, id DESC
                LIMIT :limit
                """
            ),
            {"limit": args.limit},
        ).mappings()

        processed = 0
        for row in rows:
            service.recompute_decision(row["ticket_id"])
            processed += 1

        recommendations = db.execute(
            text("SELECT COUNT(*) AS total FROM recommendations")
        ).mappings().first()
        decisions = db.execute(
            text("SELECT COUNT(*) AS total FROM decision_records")
        ).mappings().first()

        print(f"Aether seed completed at {datetime.now(UTC).isoformat()}")
        print(f"Tickets processed: {processed}")
        print(f"Decision records available: {decisions['total'] if decisions else 0}")
        print(f"Recommendations available: {recommendations['total'] if recommendations else 0}")


if __name__ == "__main__":
    main()
