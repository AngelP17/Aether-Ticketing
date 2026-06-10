import json
from pathlib import Path
from typing import Any

from pytest import MonkeyPatch

from apps.api.services import auth_service as auth_module
from apps.api.services.auth_service import AuthService, pwd_context
from apps.api.services.demo_data_service import DEMO_TICKETS


SENSITIVE_DEMO_DENYLIST = {
    "@expac.com",
    "angel pinzon",
    "paula jenkins",
    "monica lopez",
    "windstream",
    "epicor",
    "kennesaw",
    "truelogic",
    "wallner expac",
}

EXPECTED_DEMO_TITLES = {
    "VPN access fails after password reset",
    "Shared mailbox forwarding rule missing",
    "Printer queue stuck on third floor",
    "ERP approval page timing out",
    "Laptop disk encryption recovery prompt",
    "New hire account missing groups",
    "Phishing report needs review",
    "Warehouse scanner cannot sync inventory",
}


def test_env_backed_admin_rejects_weak_public_passwords(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    path = tmp_path / "users.json"
    path.write_text(
        json.dumps(
            {
                "users": [
                    {
                        "username": "admin",
                        "password_hash": pwd_context.hash("admin123"),
                        "role": "admin",
                        "display_name": "Unsafe Admin",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(auth_module, "USERS_FILE_LOCATIONS", [path])
    monkeypatch.setattr(auth_module.settings, "ENV", "production")
    monkeypatch.setattr(auth_module.settings, "ADMIN_BOOTSTRAP_PASSWORD", "private-admin-pass")

    for weak_password in ["admin123", "password", "password123", "viewer123"]:
        assert AuthService().login("admin", weak_password) is None

    assert AuthService().login("admin", "private-admin-pass") is not None


def test_demo_ticket_seed_is_synthetic_and_allowlisted() -> None:
    titles = {str(ticket["title"]) for ticket in DEMO_TICKETS}

    assert titles == EXPECTED_DEMO_TITLES
    assert len(DEMO_TICKETS) == len(EXPECTED_DEMO_TITLES)

    payload = json.dumps(DEMO_TICKETS, default=str).lower()
    for sensitive_value in SENSITIVE_DEMO_DENYLIST:
        assert sensitive_value not in payload

    for ticket in DEMO_TICKETS:
        assert str(ticket["ticket_id"]).startswith("IT-2026")
        assert ticket["requester"] not in {"Angel Pinzon", "Paula Jenkins", "Monica Lopez"}
        assert ticket["staff_assigned"] not in {"Angel Pinzon", "Paula Jenkins", "Monica Lopez"}


def test_viewer_demo_client_cannot_use_representative_admin_routes(
    viewer_client: Any,
) -> None:
    client = viewer_client

    responses = [
        client.get("/api/auth/users"),
        client.post("/api/categories", json={"name": "Unsafe"}),
        client.post("/api/automation/trigger/ticket_created", json={"ticket_id": "IT-20260001"}),
    ]

    assert [response.status_code for response in responses] == [403, 403, 403]
