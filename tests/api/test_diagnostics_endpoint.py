from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from apps.api.routes.diagnostics import live_diagnostics


class _Rows:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def __iter__(self) -> Any:
        return iter(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class _DiagnosticSession:
    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql = getattr(statement, "text", str(statement))
        if "information_schema.columns" in sql:
            return [("id",), ("ticket_id",), ("title",)]
        if "COUNT(*)" in sql:
            return SimpleNamespace(scalar=lambda: 49)
        return SimpleNamespace(
            mappings=lambda: _Rows(
                [
                    {
                        "ticket_id": "IT-1",
                        "title": "Printer queue blocked",
                        "status": "Open",
                        "priority": "High",
                        "request_type": "Printer",
                        "staff_assigned": None,
                        "requester": "Front Desk",
                        "date_opened": None,
                        "created_at": None,
                    }
                ]
            )
        )


def test_live_diagnostics_reports_non_secret_schema_and_query_status() -> None:
    body = live_diagnostics(_DiagnosticSession())  # type: ignore[arg-type]

    assert body["status"] == "ok"
    assert body["tables"]["tickets"]["columns"] == ["id", "ticket_id", "title"]
    assert body["queries"]["ticket_count"] == {"ok": True, "value": 49}
    assert body["queries"]["ticket_probe"]["ok"] is True
    assert body["queries"]["ticket_probe"]["row_present"] is True
    assert "title" in body["queries"]["ticket_probe"]["fields_present"]
