from __future__ import annotations

import argparse

from sqlalchemy import text

from apps.api.services.report_service import ReportService
from infrastructure.db.session import get_db_context, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an Aether Excel report")
    parser.add_argument("--output", default="aether_report.xlsx")
    args = parser.parse_args()

    init_db()
    with get_db_context() as db:
        workbook = ReportService(db).generate_workbook("operational", None, None)
        workbook.save(args.output)
        total = db.execute(text("SELECT COUNT(*) AS total FROM tickets")).mappings().first()
        print(f"Saved {args.output} with {total['total'] if total else 0} tickets available.")


if __name__ == "__main__":
    main()
