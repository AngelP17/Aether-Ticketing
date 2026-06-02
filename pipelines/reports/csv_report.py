"""
CSV Report Generator: Produces a 5-section comma-separated export that
mirrors the styled Excel workbook (Executive Summary, Operational Queue,
Incident Clusters, Decision Intelligence, Audit Extract).

Sections are separated by a header line and a blank line so the file
opens cleanly in Excel, Google Sheets, Numbers, and pandas.
"""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any


OPERATIONAL_QUEUE_HEADERS = [
    "Ticket ID",
    "Title",
    "Status",
    "Priority",
    "Category",
    "Assignee",
    "Site",
    "Days Open",
    "Priority Score",
    "Root Cause",
    "SLA Risk",
    "Confidence",
    "Top Recommendation",
    "Recommendation Risk",
    "Requester",
    "Created At",
    "Resolved At",
]

INCIDENT_HEADERS = [
    "Incident ID",
    "Title",
    "Status",
    "Root Cause",
    "Ticket Count",
    "Confidence",
    "Impact Score",
    "Opened At",
]

DECISION_HEADERS = [
    "Ticket ID",
    "Priority Score",
    "Severity",
    "Urgency",
    "Business Impact",
    "SLA Risk",
    "Recurrence",
    "Actionability",
    "Uncertainty",
    "Root Cause",
    "Confidence",
    "Top Recommendation",
]

AUDIT_HEADERS = [
    "Ticket ID",
    "Event Type",
    "Actor",
    "Timestamp",
    "Details",
    "Feedback Status",
]

EXECUTIVE_KPI_HEADERS = ["KPI", "Value"]


def generate_csv(
    report_type: str = "operational",
    *,
    tickets: list[dict[str, Any]] | None = None,
    incidents: list[dict[str, Any]] | None = None,
) -> str:
    tickets = tickets or []
    incidents = incidents or []

    buf = io.StringIO()
    writer: Any = csv.writer(buf, quoting=csv.QUOTE_MINIMAL)

    _write_executive_summary(writer, tickets=tickets, incidents=incidents)
    _write_section_break(writer)
    _write_operational_queue(writer, tickets=tickets)
    _write_section_break(writer)
    _write_incident_clusters(writer, incidents=incidents)
    _write_section_break(writer)
    _write_decision_intelligence(writer, tickets=tickets)
    _write_section_break(writer)
    _write_audit_extract(writer, tickets=tickets)

    return buf.getvalue()


def _write_section_break(writer: Any) -> None:
    writer.writerow([])


def _write_executive_summary(
    writer: Any, *, tickets: list[dict[str, Any]], incidents: list[dict[str, Any]]
) -> None:
    writer.writerow(["# Section: Executive Summary"])
    writer.writerow(["Aether — Executive Summary"])
    writer.writerow([f"Generated {datetime.now(UTC).isoformat()}"])
    writer.writerow([])
    writer.writerow(EXECUTIVE_KPI_HEADERS)

    open_tickets = [t for t in tickets if t.get("status") not in {"Resolved", "Closed"}]
    critical = [t for t in open_tickets if t.get("priority_raw") == "Critical"]
    sla_risk = [t for t in open_tickets if (t.get("sla_risk") or 0) >= 75]
    writer.writerow(["Total Open Tickets", len(open_tickets)])
    writer.writerow(["Critical Queue", len(critical)])
    writer.writerow(["SLA Breach Risk", len(sla_risk)])
    writer.writerow(["Incident Clusters", len(incidents)])


def _write_operational_queue(writer: Any, *, tickets: list[dict[str, Any]]) -> None:
    writer.writerow(["# Section: Operational Queue"])
    writer.writerow(OPERATIONAL_QUEUE_HEADERS)
    for ticket in tickets:
        writer.writerow(
            [
                ticket.get("ticket_id"),
                ticket.get("title") or "",
                ticket.get("status") or "",
                ticket.get("priority_raw") or "",
                ticket.get("category") or "",
                ticket.get("assignee") or "",
                ticket.get("site") or "",
                ticket.get("days_open") if ticket.get("days_open") is not None else 0,
                ticket.get("priority_score") or 0,
                ticket.get("root_cause_hypothesis") or "",
                ticket.get("sla_risk") or 0,
                ticket.get("confidence_score") or 0,
                ticket.get("recommendation") or "",
                ticket.get("recommendation_risk") or "",
                ticket.get("requester") or "",
                ticket.get("created_at") or "",
                ticket.get("resolved_at") or "",
            ]
        )


def _write_incident_clusters(writer: Any, *, incidents: list[dict[str, Any]]) -> None:
    writer.writerow(["# Section: Incident Clusters"])
    writer.writerow(INCIDENT_HEADERS)
    for incident in incidents:
        writer.writerow(
            [
                incident.get("id"),
                incident.get("title") or "",
                incident.get("status") or "",
                incident.get("root_cause_hypothesis") or "",
                incident.get("ticket_count") or 0,
                incident.get("confidence") or 0,
                incident.get("business_impact_score") or 0,
                incident.get("opened_at") or "",
            ]
        )


def _write_decision_intelligence(writer: Any, *, tickets: list[dict[str, Any]]) -> None:
    writer.writerow(["# Section: Decision Intelligence"])
    writer.writerow(DECISION_HEADERS)
    for ticket in tickets:
        writer.writerow(
            [
                ticket.get("ticket_id"),
                ticket.get("priority_score") or 0,
                ticket.get("severity_score") or 0,
                ticket.get("urgency_score") or 0,
                ticket.get("business_impact_score") or 0,
                ticket.get("sla_risk") or 0,
                ticket.get("recurrence_score") or 0,
                ticket.get("actionability_score") or 0,
                ticket.get("uncertainty_penalty") or 0,
                ticket.get("root_cause_hypothesis") or "",
                ticket.get("confidence_score") or 0,
                ticket.get("recommendation") or "",
            ]
        )


def _write_audit_extract(writer: Any, *, tickets: list[dict[str, Any]]) -> None:
    writer.writerow(["# Section: Audit Extract"])
    writer.writerow(AUDIT_HEADERS)
    now = datetime.now(UTC).isoformat()
    for ticket in tickets:
        writer.writerow(
            [
                ticket.get("ticket_id"),
                "decision_generated",
                "aether-api",
                now,
                ticket.get("root_cause_hypothesis") or "",
                "proposed",
            ]
        )
