"""Endpoint tests for /api/reports/excel and /api/reports/csv."""
from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest

import apps.api.routes.reports as reports_routes


def test_excel_report_returns_xlsx_streaming_response(admin_client: Any) -> None:
    from openpyxl import Workbook

    def _fake_workbook(*args: Any, **kwargs: Any) -> Workbook:
        return Workbook()

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            reports_routes.ReportService, "generate_workbook", _fake_workbook
        )
        response = admin_client.get("/api/reports/excel?report_type=operational")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "attachment" in response.headers["content-disposition"]
    assert "aether_report_" in response.headers["content-disposition"]
    assert ".xlsx" in response.headers["content-disposition"]
    # The body is a real xlsx file (PK zip header).
    assert response.content[:2] == b"PK"


def test_csv_report_returns_text_csv(agent_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            reports_routes.ReportService,
            "generate_csv",
            lambda *args, **kwargs: "# Section: foo\ncol1,col2\n1,2\n",
        )
        response = agent_client.get("/api/reports/csv?report_type=operational")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert ".csv" in response.headers["content-disposition"]
    assert response.text.startswith("# Section: foo")


def test_excel_report_404_on_lookup_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> Workbook:
        raise LookupError("no data")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(reports_routes.ReportService, "generate_workbook", _raise)
        response = admin_client.get("/api/reports/excel")
    assert response.status_code == 404


def test_excel_report_500_on_unexpected_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> Workbook:
        raise RuntimeError("boom")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(reports_routes.ReportService, "generate_workbook", _raise)
        response = admin_client.get("/api/reports/excel")
    assert response.status_code == 500
    assert "boom" in response.json()["detail"]


def test_csv_report_500_on_unexpected_error(admin_client: Any) -> None:
    def _raise(self: Any, *args: Any, **kwargs: Any) -> str:
        raise RuntimeError("kaboom")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(reports_routes.ReportService, "generate_csv", _raise)
        response = admin_client.get("/api/reports/csv")
    assert response.status_code == 500


def test_reports_pass_query_params_through(agent_client: Any) -> None:
    captured: dict[str, Any] = {}

    def _capture(self: Any, *args: Any, **kwargs: Any) -> str:
        captured["args"] = args
        captured["kwargs"] = kwargs
        return ""

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(reports_routes.ReportService, "generate_csv", _capture)
        agent_client.get(
            "/api/reports/csv?report_type=incident&date_from=2026-01-01"
            "&date_to=2026-01-31&incident_id=INC-1"
        )
    assert captured["args"][0] == "incident"
    assert captured["args"][1] == "2026-01-01"
    assert captured["args"][2] == "2026-01-31"
    assert captured["args"][3] == "INC-1"
