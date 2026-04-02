"""
Delta Detector: Compares source rows against DB state to find changes.
Only returns rows that are new or have changed since last ingest.
"""

from dataclasses import dataclass
from typing import Iterator

from infrastructure.db.session import get_db_context
from pipelines.ingest.excel_loader import NormalizedTicket


@dataclass
class DeltaResult:
    ticket: NormalizedTicket
    change_type: str  # "new" | "changed" | "unchanged"


def detect_delta(tickets: Iterator[NormalizedTicket]) -> Iterator[DeltaResult]:
    """
    Compare source tickets against stored hashes.
    Yields only new or changed tickets.
    """
    with get_db_context() as db:
        from infrastructure.db.models.ticket import Ticket

        for ticket in tickets:
            existing = (
                db.query(Ticket)
                .filter(Ticket.ticket_id == ticket.external_ticket_id)
                .first()
            )

            if existing is None:
                yield DeltaResult(ticket=ticket, change_type="new")
            elif getattr(existing, "source_hash", None) != ticket.source_hash:
                yield DeltaResult(ticket=ticket, change_type="changed")
            else:
                yield DeltaResult(ticket=ticket, change_type="unchanged")
