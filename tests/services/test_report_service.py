"""
Tests for `apps.api.services.report_service.ReportService`.

The report service produces workbook and CSV exports that mirror the
live Aether state. These tests verify that the snapshot builder
populates the recommendation fields from the live decision engine
when given a stub DB session, and that the CSV/Excel generators share
the same data path.
"""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from apps.api.services.report_service import ReportService


class _StubMappingResult:
    """Result stub that supports both `.mappings().all()` and `.mappings().first()`."""

    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None

    def __iter__(self) -> Any:
        return iter(self._rows)


class _StubSession:
    """Stub session that returns scripted rows for the SELECT and a
    zero count for similar-case queries."""

    def __init__(self, ticket_rows: list[dict[str, Any]]) -> None:
        self.ticket_rows = ticket_rows
        self.executes: list[tuple[str, dict[str, Any]]] = []

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql_text = getattr(statement, "text", str(statement))
        self.executes.append((sql_text, params or {}))

        if "FROM tickets" in sql_text and "LEFT JOIN categories" in sql_text:
            return SimpleNamespace(mappings=lambda: _StubMappingResult(self.ticket_rows))
        if "COUNT(*) AS total" in sql_text and "tickets" in sql_text:
            return SimpleNamespace(
                mappings=lambda: _StubMappingResult([{"total": 2}])
            )
        if "FROM incidents" in sql_text or "incidents" in sql_text:
            return SimpleNamespace(mappings=lambda: _StubMappingResult([]))
        return SimpleNamespace(mappings=lambda: _StubMappingResult([]))


@pytest.fixture
def stub_db() -> _StubSession:
    return _StubSession(
        [
            {
                "id": 1,
                "ticket_id": "T-1",
                "title": "ERP outage",
                "status": "Open",
                "priority": "High",
                "request_type": "Server Issues",
                "staff_assigned": "@Test",
                "requester": "Req A",
                "date_opened": None,
                "description": "ERP is down",
                "resolution_notes": None,
                "created_at": None,
                "updated_at": None,
                "resolved_at": None,
                "clean_summary": None,
                "site_id": None,
                "asset_id": None,
                "category_name": "Server Issues",
            }
        ]
    )


def test_snapshot_builder_populates_recommendation(stub_db: _StubSession) -> None:
    service = ReportService(stub_db)  # type: ignore[arg-type]
    snapshots, _incidents = service._load_report_payload("operational", None, None, None)
    assert len(snapshots) == 1
    snapshot = snapshots[0]
    # The recommendation and risk must be strings (never None) so the
    # CSV/Excel writers stay simple.
    assert isinstance(snapshot["recommendation"], str)
    assert isinstance(snapshot["recommendation_risk"], str)
    # Top recommendation is non-empty for an Open High ticket — the live
    # decision engine always emits at least one recommendation.
    assert snapshot["recommendation"]
    assert snapshot["recommendation_risk"] in {"low", "medium", "high"}


def test_snapshot_builder_maps_live_ticket_fields(stub_db: _StubSession) -> None:
    service = ReportService(stub_db)  # type: ignore[arg-type]
    snapshots, _incidents = service._load_report_payload("operational", None, None, None)
    snapshot = snapshots[0]
    assert snapshot["ticket_id"] == "T-1"
    assert snapshot["title"] == "ERP outage"
    assert snapshot["status"] == "Open"
    assert snapshot["priority_raw"] == "High"
    assert snapshot["category"] == "Server Issues"
    assert snapshot["requester"] == "Req A"
    assert snapshot["assignee"] == "@Test"
    # The decision engine must have computed scores and root cause.
    assert snapshot["priority_score"] is not None
    assert snapshot["root_cause_hypothesis"] is not None


def test_csv_and_excel_share_payload(stub_db: _StubSession) -> None:
    """The CSV and Excel exports must use the same ticket/incident payload."""
    from openpyxl import Workbook

    service = ReportService(stub_db)  # type: ignore[arg-type]
    csv_text = service.generate_csv("operational", None, None)
    workbook: Workbook = service.generate_workbook("operational", None, None)
    assert "T-1" in csv_text
    assert "ERP outage" in csv_text
    assert workbook.sheetnames == [
        "Executive Summary",
        "Operational Queue",
        "Incident Clusters",
        "Decision Intelligence",
        "Audit Extract",
    ]


def test_load_report_payload_raises_lookup_error_for_missing_incident(
    stub_db: _StubSession,
) -> None:
    service = ReportService(stub_db)  # type: ignore[arg-type]
    with pytest.raises(LookupError):
        service._load_report_payload("operational", None, None, "INC-DOES-NOT-EXIST")
