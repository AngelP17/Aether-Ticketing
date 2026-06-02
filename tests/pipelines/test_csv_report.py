"""
Tests for the CSV report generator (`pipelines.reports.csv_report`).

The CSV report mirrors the styled Excel workbook with five sections:
Executive Summary, Operational Queue, Incident Clusters, Decision
Intelligence, and Audit Extract. Each section is preceded by a header
marker line and uses standard CSV quoting so it opens cleanly in Excel,
Numbers, Google Sheets, and pandas.
"""
from __future__ import annotations

import csv
import io

from pipelines.reports.csv_report import (
    AUDIT_HEADERS,
    DECISION_HEADERS,
    EXECUTIVE_KPI_HEADERS,
    INCIDENT_HEADERS,
    OPERATIONAL_QUEUE_HEADERS,
    generate_csv,
)


def _parse_sections(csv_text: str) -> dict[str, list[list[str]]]:
    """Return a mapping of section name -> rows (excluding the section marker
    and the leading title/date rows in the Executive Summary)."""
    reader = csv.reader(io.StringIO(csv_text))
    sections: dict[str, list[list[str]]] = {}
    current: str | None = None
    for row in reader:
        if len(row) == 1 and row[0].startswith("# Section:"):
            current = row[0].split(":", 1)[1].strip()
            sections[current] = []
            continue
        if not row:
            continue
        if current is not None:
            # Skip the leading decorative rows in Executive Summary
            # (title, generated timestamp) so the test data starts at
            # the KPI header.
            if current == "Executive Summary" and (
                row[0].startswith("Aether") or row[0].startswith("Generated ")
            ):
                continue
            sections[current].append(row)
    return sections


def test_generate_csv_with_no_data() -> None:
    csv_text = generate_csv(tickets=[], incidents=[])
    sections = _parse_sections(csv_text)
    assert set(sections.keys()) == {
        "Executive Summary",
        "Operational Queue",
        "Incident Clusters",
        "Decision Intelligence",
        "Audit Extract",
    }
    # Executive Summary: 1 header + 4 KPI rows = 5 rows
    assert len(sections["Executive Summary"]) == 5
    # The other sections should each be a single header row with no data.
    for name in [
        "Operational Queue",
        "Incident Clusters",
        "Decision Intelligence",
        "Audit Extract",
    ]:
        assert len(sections[name]) == 1


def test_executive_summary_section_uses_kpi_headers() -> None:
    csv_text = generate_csv(tickets=[], incidents=[])
    sections = _parse_sections(csv_text)
    assert sections["Executive Summary"][0] == EXECUTIVE_KPI_HEADERS


def test_operational_queue_headers_match_export_contract() -> None:
    headers = OPERATIONAL_QUEUE_HEADERS
    assert headers[0] == "Ticket ID"
    assert "Top Recommendation" in headers
    assert "Recommendation Risk" in headers
    assert "Requester" in headers
    assert "Created At" in headers


def test_incident_headers_match_export_contract() -> None:
    assert INCIDENT_HEADERS[0] == "Incident ID"
    assert "Root Cause" in INCIDENT_HEADERS
    assert "Ticket Count" in INCIDENT_HEADERS


def test_decision_headers_match_export_contract() -> None:
    assert DECISION_HEADERS[0] == "Ticket ID"
    assert "Priority Score" in DECISION_HEADERS
    assert "Top Recommendation" in DECISION_HEADERS


def test_audit_headers_match_export_contract() -> None:
    assert AUDIT_HEADERS[0] == "Ticket ID"
    assert "Event Type" in AUDIT_HEADERS
    assert "Feedback Status" in AUDIT_HEADERS


def test_operational_queue_row_populates_recommendation_and_risk() -> None:
    tickets = [
        {
            "ticket_id": "T-1",
            "title": "Test ticket",
            "status": "Open",
            "priority_raw": "High",
            "category": "Network",
            "assignee": "@Test User",
            "site": "Site-A",
            "days_open": 2,
            "priority_score": 80.0,
            "root_cause_hypothesis": "network_connectivity",
            "sla_risk": 50.0,
            "confidence_score": 70.0,
            "recommendation": "Restart VPN client and verify network connectivity",
            "recommendation_risk": "low",
            "requester": "Test Requester",
            "created_at": "2026-06-01T00:00:00",
            "resolved_at": None,
        }
    ]
    csv_text = generate_csv(tickets=tickets, incidents=[])
    sections = _parse_sections(csv_text)
    rows = sections["Operational Queue"]
    assert len(rows) == 2  # header + 1 data row
    data = rows[1]
    assert data[0] == "T-1"
    assert data[1] == "Test ticket"
    assert data[2] == "Open"
    assert data[3] == "High"
    assert "Restart VPN" in data[12]
    assert data[13] == "low"
    assert data[14] == "Test Requester"


def test_incident_clusters_section_uses_incident_fields() -> None:
    incidents = [
        {
            "id": "INC-1",
            "title": "ERP cluster",
            "status": "open",
            "root_cause_hypothesis": "erp_application",
            "ticket_count": 5,
            "confidence": 75.0,
            "business_impact_score": 80.0,
            "opened_at": "2026-06-01T00:00:00",
        }
    ]
    csv_text = generate_csv(tickets=[], incidents=incidents)
    sections = _parse_sections(csv_text)
    rows = sections["Incident Clusters"]
    assert len(rows) == 2
    assert rows[1][0] == "INC-1"
    assert rows[1][3] == "erp_application"
    assert rows[1][4] == "5"


def test_audit_extract_section_includes_decision_generated_events() -> None:
    tickets = [
        {
            "ticket_id": "T-9",
            "root_cause_hypothesis": "erp_application",
        }
    ]
    csv_text = generate_csv(tickets=tickets, incidents=[])
    sections = _parse_sections(csv_text)
    rows = sections["Audit Extract"]
    assert len(rows) == 2
    assert rows[1][0] == "T-9"
    assert rows[1][1] == "decision_generated"
    assert rows[1][2] == "aether-api"
    assert rows[1][4] == "erp_application"
    assert rows[1][5] == "proposed"


def test_generate_csv_handles_missing_recommendation() -> None:
    tickets = [
        {
            "ticket_id": "T-2",
            "title": "Edge",
            "status": "Open",
            "priority_raw": "Low",
            "category": None,
            "assignee": None,
            "site": None,
            "days_open": 0,
            "priority_score": None,
            "root_cause_hypothesis": None,
            "sla_risk": 0,
            "confidence_score": 0,
            "recommendation": "",
            "recommendation_risk": "",
            "requester": None,
            "created_at": None,
            "resolved_at": None,
        }
    ]
    csv_text = generate_csv(tickets=tickets, incidents=[])
    sections = _parse_sections(csv_text)
    data_row = sections["Operational Queue"][1]
    # Missing fields become empty strings, never None.
    for value in data_row:
        assert value is not None
    assert data_row[12] == ""
    assert data_row[13] == ""


def test_executive_summary_kpi_counts() -> None:
    tickets = [
        {"status": "Open", "priority_raw": "Critical", "sla_risk": 90},
        {"status": "Open", "priority_raw": "Low", "sla_risk": 10},
        {"status": "Resolved", "priority_raw": "Low", "sla_risk": 0},
        {"status": "Closed", "priority_raw": "Low", "sla_risk": 0},
    ]
    csv_text = generate_csv(tickets=tickets, incidents=[{"id": "X"}])
    sections = _parse_sections(csv_text)
    rows = sections["Executive Summary"]
    kpis = {row[0]: row[1] for row in rows[1:]}
    assert kpis["Total Open Tickets"] == "2"
    assert kpis["Critical Queue"] == "1"
    assert kpis["SLA Breach Risk"] == "1"
    assert kpis["Incident Clusters"] == "1"
