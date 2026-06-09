from __future__ import annotations

from typing import Any


def test_automation_trigger_requires_write_role(viewer_client: Any) -> None:
    response = viewer_client.post(
        "/api/automation/trigger/ticket_created",
        json={"ticket_id": "IT-1"},
    )

    assert response.status_code == 403


def test_automation_trigger_requires_authentication(anon_client: Any) -> None:
    response = anon_client.post(
        "/api/automation/trigger/ticket_created",
        json={"ticket_id": "IT-1"},
    )

    assert response.status_code == 401
