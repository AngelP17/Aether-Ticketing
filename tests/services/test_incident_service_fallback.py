from __future__ import annotations

from typing import Any

import pytest

from apps.api.services import incident_service as incident_service_module
from apps.api.services.incident_service import IncidentService


class _UnusedSession:
    pass


def test_list_incidents_returns_synthesized_clusters_when_persistence_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cluster = {
        "title": "Printer cluster",
        "status": "open",
        "root_cause_hypothesis": "printer_queue",
        "site_scope": "CA",
        "ticket_count": 3,
        "confidence": 88.0,
        "business_impact_score": 72.0,
        "opened_at": "2026-06-02T00:00:00",
        "tickets": [{"ticket_id": "IT-1"}, {"ticket_id": "IT-2"}, {"ticket_id": "IT-3"}],
        "graph_evidence": {"evidence_basis": "ticket relationship graph"},
    }

    monkeypatch.setattr(IncidentService, "_build_clusters", lambda _self: [cluster])

    def _raise(*_args: Any, **_kwargs: Any) -> Any:
        raise RuntimeError("legacy incidents table")

    monkeypatch.setattr(incident_service_module, "persist_synthesized_incidents", _raise)

    incidents = IncidentService(_UnusedSession()).list_incidents()  # type: ignore[arg-type]

    assert incidents == [
        {
            "id": 1,
            "incident_key": "INC-LIVE-0001",
            "title": "Printer cluster",
            "status": "open",
            "root_cause_hypothesis": "printer_queue",
            "site_scope": "CA",
            "ticket_count": 3,
            "confidence": 88.0,
            "business_impact_score": 72.0,
            "opened_at": "2026-06-02T00:00:00",
            "last_updated_at": "2026-06-02T00:00:00",
            "graph_evidence": {"evidence_basis": "ticket relationship graph"},
        }
    ]


def test_list_incidents_returns_empty_when_synthesis_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_build(_self: IncidentService) -> Any:
        raise RuntimeError("bad ticket row")

    monkeypatch.setattr(IncidentService, "_build_clusters", _raise_build)
    monkeypatch.setattr(incident_service_module, "list_persisted_incidents", lambda _db: [])

    assert IncidentService(_UnusedSession()).list_incidents() == []  # type: ignore[arg-type]
