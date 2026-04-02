"""
Row Normalizer: Cleans ticket data into canonical form.
Handles enum mapping, null fills, text cleanup.
"""

from dataclasses import dataclass

from domain.enums import TicketStatus
from pipelines.ingest.excel_loader import NormalizedTicket


STATUS_MAP = {
    "open": TicketStatus.OPEN,
    "in progress": TicketStatus.IN_PROGRESS,
    "waiting for info": TicketStatus.WAITING_FOR_INFO,
    "waiting": TicketStatus.WAITING_FOR_INFO,
    "resolved": TicketStatus.RESOLVED,
    "closed": TicketStatus.CLOSED,
}


@dataclass
class CleanTicket:
    external_ticket_id: str
    title: str
    status: TicketStatus
    priority_raw: str
    request_type: str
    staff_assigned: str
    requester: str
    date_opened: str
    description: str
    resolution_notes: str
    source_hash: str


def normalize(ticket: NormalizedTicket) -> CleanTicket:
    """Map raw Excel row to canonical internal representation."""
    status_str = ticket.status.lower().strip()
    normalized_status = STATUS_MAP.get(status_str, TicketStatus.OPEN)

    return CleanTicket(
        external_ticket_id=ticket.external_ticket_id,
        title=ticket.title.strip(),
        status=normalized_status,
        priority_raw=_normalize_priority(ticket.priority_raw),
        request_type=ticket.request_type.strip(),
        staff_assigned=ticket.staff_assigned.strip(),
        requester=ticket.requester.strip(),
        date_opened=ticket.date_opened.strftime("%Y-%m-%d"),
        description=_clean_description(ticket.description),
        resolution_notes=ticket.resolution_notes.strip(),
        source_hash=ticket.source_hash,
    )


def _normalize_priority(priority: str) -> str:
    p = priority.lower().strip()
    if p in ("critical", "crit"):
        return "Critical"
    if p in ("high", "hi"):
        return "High"
    if p in ("medium", "med"):
        return "Medium"
    if p in ("low", "lo"):
        return "Low"
    return "Low"


def _clean_description(text: str) -> str:
    if not text:
        return ""
    lines = text.strip().split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(">"):
            cleaned_lines.append(stripped)
    return " ".join(cleaned_lines)
