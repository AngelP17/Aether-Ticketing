from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from apps.api.services import ticket_service as ticket_service_module
from apps.api.services.ticket_service import TicketService


class _MappingResult:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def __iter__(self) -> Any:
        return iter(self._rows)


class _LegacySchemaSession:
    """Session stub that fails schema introspection but supports base tickets."""

    def __init__(self) -> None:
        self.executed_sql: list[str] = []

    def get_bind(self) -> Any:
        raise RuntimeError("information_schema unavailable")

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> Any:
        sql_text = getattr(statement, "text", str(statement))
        self.executed_sql.append(sql_text)
        assert "LEFT JOIN categories" not in sql_text
        assert "NULL AS category_name" in sql_text
        return SimpleNamespace(
            mappings=lambda: _MappingResult(
                [
                    {
                        "id": 1,
                        "ticket_id": "IT-LEGACY",
                        "title": "Printer queue blocked",
                        "status": "Open",
                        "priority": "High",
                        "request_type": "Printer",
                        "staff_assigned": "Aether Ops",
                        "requester": "Front Desk",
                        "date_opened": None,
                        "description": "No print jobs leave the queue.",
                        "resolution_notes": None,
                        "created_at": None,
                        "updated_at": None,
                        "resolved_at": None,
                        "clean_summary": None,
                        "site_id": None,
                        "asset_id": None,
                        "category_id": None,
                        "category_name": None,
                    }
                ]
            )
        )


def test_list_tickets_uses_base_query_when_schema_introspection_fails() -> None:
    session = _LegacySchemaSession()
    tickets = TicketService(session).list_tickets(limit=10)  # type: ignore[arg-type]

    assert tickets[0]["ticket_id"] == "IT-LEGACY"
    assert tickets[0]["priority_raw"] == "High"
    assert tickets[0]["category"] == "Printer"
    assert session.executed_sql


def test_list_tickets_keeps_feed_alive_when_one_snapshot_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _LegacySchemaSession()

    def _raise_snapshot(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("bad production row")

    monkeypatch.setattr(ticket_service_module, "build_ticket_snapshot", _raise_snapshot)

    tickets = TicketService(session).list_tickets(limit=10)  # type: ignore[arg-type]

    assert tickets[0]["ticket_id"] == "IT-LEGACY"
    assert tickets[0]["title"] == "Printer queue blocked"
    assert tickets[0]["priority_score"] is None
