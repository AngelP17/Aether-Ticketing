from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi import Header, HTTPException
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from openpyxl import Workbook

from apps.api.deps import get_db
from apps.api.main import app
from apps.api.security import get_current_user, require_admin, require_ticket_write


SAMPLE_TICKET_ID = "IT-20260001"
SAMPLE_INCIDENT_ID = "INC-20260001"
SAMPLE_RECOMMENDATION_ID = "REC-20260001"
SAMPLE_ACTION_RUN_ID = "RUN-20260001"


class _FakeRow(dict[str, Any]):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


class _FakeResult:
    def mappings(self) -> "_FakeResult":
        return self

    def first(self) -> _FakeRow:
        return _FakeRow({"id": 1, "c": 1, "cnt": 1, "value": 1, "ts": None, "feedback_type": "accepted", "status": "ok"})

    def fetchone(self) -> _FakeRow:
        return self.first()

    def scalar(self) -> int:
        return 1

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(
            [
                _FakeRow(
                    {
                        "id": 1,
                        "url": "https://example.invalid/hook",
                        "events": "[]",
                        "active": True,
                        "created_at": None,
                        "column_name": "id",
                        "feedback_type": "accepted",
                        "status": "ok",
                        "c": 1,
                    }
                )
            ]
        )


class _FakeDb:
    def execute(self, *_args: Any, **_kwargs: Any) -> _FakeResult:
        return _FakeResult()

    def commit(self) -> None:
        return None


class _FakeTicketService:
    def __init__(self, _db: Any) -> None:
        pass

    def list_tickets(self, **_kwargs: Any) -> list[dict[str, Any]]:
        return [{"ticket_id": SAMPLE_TICKET_ID, "title": "Synthetic sweep ticket", "status": "Open"}]

    def get_ticket_detail(self, ticket_id: str) -> dict[str, Any]:
        return {
            "ticket_id": ticket_id,
            "title": "Synthetic sweep ticket",
            "status": "Open",
            "priority": "Low",
            "created_at": "2026-01-01T00:00:00Z",
            "days_open": 0,
            "custom_fields": {"demo": True},
        }

    def get_ticket_events(self, _ticket_id: str) -> list[dict[str, Any]]:
        return []

    def create_ticket(self, _payload: dict[str, Any], _actor: dict[str, Any]) -> dict[str, Any]:
        return {"ticket_id": SAMPLE_TICKET_ID, "status": "Open"}

    def update_ticket(self, ticket_id: str, _payload: dict[str, Any], _actor: dict[str, Any]) -> dict[str, Any]:
        return {"ticket_id": ticket_id, "status": "Open"}

    def delete_ticket(self, _ticket_id: str, _actor: dict[str, Any]) -> bool:
        return True

    def set_ticket_labels(self, _ticket_id: str, _label_ids: list[int], _actor: dict[str, Any]) -> bool:
        return True

    def move_ticket(self, ticket_id: str, _column: str | None, status: str | None, _actor: dict[str, Any]) -> dict[str, Any]:
        return {"ticket_id": ticket_id, "status": status or "Open"}


class _FakeCatalogService:
    def __init__(self, _db: Any) -> None:
        pass

    def list_categories(self, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": 1, "name": "Access", "color": "#f59e0b", "icon": "key"}]

    def create_category(self, name: str, color: str, icon: str | None) -> dict[str, Any]:
        return {"id": 1, "name": name, "color": color, "icon": icon}

    def update_category(self, category_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        return {"id": category_id, **payload}

    def delete_category(self, _category_id: int) -> bool:
        return True

    def list_labels(self) -> list[dict[str, Any]]:
        return [{"id": 1, "name": "Demo", "color": "#f59e0b"}]

    def create_label(self, name: str, color: str) -> dict[str, Any]:
        return {"id": 1, "name": name, "color": color}

    def delete_label(self, _label_id: int) -> None:
        return None

    def create_assignee(self, display_name: str) -> dict[str, Any]:
        return {"id": 1, "display_name": display_name}

    def delete_assignee(self, _display_name: str) -> None:
        return None

    def get_options(self) -> dict[str, Any]:
        return {"assignees": ["Demo Agent"], "categories": ["Access"], "labels": ["Demo"]}


class _FakeAuthService:
    def login(self, username: str, password: str) -> dict[str, Any] | None:
        if username == "viewer" and password == "viewer123":
            return {"access_token": "token", "token_type": "bearer", "user": {"username": username, "role": "viewer"}}
        return None

    def list_users(self) -> list[dict[str, Any]]:
        return [{"username": "viewer", "role": "viewer", "display_name": "Demo Viewer"}]

    def create_user(self, **kwargs: Any) -> dict[str, Any]:
        return {"username": kwargs["username"], "role": kwargs["role"], "display_name": kwargs.get("display_name")}

    def update_user(self, username: str, **kwargs: Any) -> dict[str, Any]:
        return {"username": username, "role": kwargs.get("role") or "viewer", "display_name": kwargs.get("display_name")}

    def delete_user(self, _username: str) -> bool:
        return True

    def change_password(self, **_kwargs: Any) -> None:
        return None


class _FakeReportService:
    def __init__(self, _db: Any) -> None:
        pass

    def generate_workbook(self, *_args: Any, **_kwargs: Any) -> Workbook:
        workbook = Workbook()
        workbook.worksheets[0]["A1"] = "demo"
        return workbook

    def generate_csv(self, *_args: Any, **_kwargs: Any) -> str:
        return "ticket_id,title\nIT-20260001,Synthetic sweep ticket\n"


class _FakeScalarService:
    def __init__(self, _db: Any) -> None:
        pass

    def __getattr__(self, _name: str) -> Any:
        return lambda *_args, **_kwargs: {"status": "ok"}


class _FakeDecisionService:
    def __init__(self, _db: Any) -> None:
        pass

    def get_latest_decision(self, _ticket_id: str) -> None:
        return None

    def recompute_decision(self, _ticket_id: str) -> None:
        return None


class _FakeEventService:
    def __init__(self, _db: Any) -> None:
        pass

    def get_ticket_event_stream(self, _ticket_id: str) -> list[dict[str, Any]]:
        return []


class _FakeCommentService:
    def __init__(self, _db: Any) -> None:
        pass

    def list_comments(self, _ticket_id: str) -> list[dict[str, Any]]:
        return []

    def create_comment(self, ticket_id: str, body: str, actor: dict[str, Any]) -> dict[str, Any]:
        return {"id": 1, "ticket_id": ticket_id, "body": body, "author": actor["username"]}

    def update_comment(self, ticket_id: str, comment_id: int, body: str, actor: dict[str, Any]) -> dict[str, Any]:
        return {"id": comment_id, "ticket_id": ticket_id, "body": body, "author": actor["username"]}

    def delete_comment(self, _ticket_id: str, _comment_id: int, _actor: dict[str, Any]) -> bool:
        return True


class _FakeAttachmentService:
    def __init__(self, _db: Any) -> None:
        pass

    async def upload_attachment(self, **_kwargs: Any) -> dict[str, Any]:
        return {"id": 1, "filename": "demo.txt"}

    def list_attachments(self, _ticket_id: str) -> list[dict[str, Any]]:
        return []

    def get_attachment(self, _attachment_id: int) -> dict[str, Any]:
        return {
            "file_data": b"demo",
            "mime_type": "text/plain",
            "content_disposition": 'attachment; filename="demo.txt"',
        }

    def delete_attachment(self, _attachment_id: int, _actor: dict[str, Any]) -> bool:
        return True


def _forbid(authorization: str | None = Header(default=None)) -> None:
    raise HTTPException(status_code=403, detail="Insufficient privileges")


def _unauthenticated(authorization: str | None = Header(default=None)) -> None:
    raise HTTPException(status_code=401, detail="Missing bearer token")


def _path_for(route: APIRoute) -> str:
    replacements = {
        "ticket_id": SAMPLE_TICKET_ID,
        "incident_id": SAMPLE_INCIDENT_ID,
        "recommendation_id": SAMPLE_RECOMMENDATION_ID,
        "action_run_id": SAMPLE_ACTION_RUN_ID,
        "username": "viewer",
        "category_id": "1",
        "label_id": "1",
        "asset_id": "1",
        "attachment_id": "1",
        "notification_id": "1",
        "policy_id": "1",
        "trigger": "ticket_created",
        "wid": "1",
    }
    path = route.path
    for key, value in replacements.items():
        path = path.replace("{" + key + "}", value)
    return path


def _json_for(route: APIRoute, method: str) -> dict[str, Any] | None:
    if method == "GET" or method == "DELETE":
        return None
    path = route.path
    if path.endswith("/auth/login"):
        return {"username": "viewer", "password": "viewer123"}
    if path.endswith("/auth/change-password"):
        return {"current_password": "viewer123", "new_password": "viewer1234"}
    if path.endswith("/auth/users"):
        return {"username": "demo-agent", "password": "demo-pass-123", "role": "agent", "display_name": "Demo Agent"}
    if "/auth/users/" in path:
        return {"role": "viewer", "display_name": "Demo Viewer"}
    if path.endswith("/tickets") or path.endswith("/tickets/"):
        return {"title": "Synthetic sweep ticket", "description": "Demo only", "requester": "demo@example.invalid"}
    if path.endswith("/bulk"):
        return {"ticket_ids": [SAMPLE_TICKET_ID], "action": "close"}
    if path.endswith("/labels"):
        return {"label_ids": [1]}
    if path.endswith("/move"):
        return {"status": "In Progress", "column": "in_progress"}
    if "/comments" in path:
        return {"body": "Demo comment"}
    if path.endswith("/categories"):
        return {"name": "Access", "color": "#f59e0b", "icon": "key"}
    if "/categories/" in path:
        return {"name": "Access", "color": "#f59e0b", "icon": "key"}
    if path.endswith("/labels"):
        return {"name": "Demo", "color": "#f59e0b"}
    if path.endswith("/assignees"):
        return {"display_name": "Demo Agent"}
    if "/recommendations/" in path:
        return {"reason": "demo", "override_action": "Escalate to agent"}
    if path.endswith("/portal/tickets"):
        return {"title": "Portal demo", "description": "Demo only", "requester": "demo@example.invalid"}
    if path.endswith("/kb"):
        return {"title": "Demo article", "body": "Demo only"}
    if path.endswith("/sla/policies") or "/sla/policies/" in path:
        return {"name": "Low priority", "priority": "Low", "target_hours": 72}
    if path.endswith("/automation/rules"):
        return {"name": "Demo rule", "trigger_type": "ticket_created", "conditions": [], "actions": []}
    if "/automation/trigger/" in path:
        return {"ticket_id": SAMPLE_TICKET_ID, "priority": "Low"}
    if path.endswith("/webhooks"):
        return {"url": "https://example.invalid/webhook", "events": ["ticket.created"], "secret": "demo-secret"}
    return {}


@pytest.fixture(autouse=True)
def patch_route_services(monkeypatch: pytest.MonkeyPatch) -> None:
    from apps.api.routes import attachments, auth, catalog, comments, decisions, diagnostics, events, metrics, portal, reports, sla, tickets
    from apps.api.services import accuracy_service, metrics_service
    from infrastructure.logging import feedback_learner

    monkeypatch.setattr(tickets, "TicketService", _FakeTicketService)
    monkeypatch.setattr(portal, "TicketService", _FakeTicketService)
    monkeypatch.setattr(diagnostics, "TicketService", _FakeTicketService)
    monkeypatch.setattr(catalog, "CatalogService", _FakeCatalogService)
    monkeypatch.setattr(auth, "AuthService", _FakeAuthService)
    monkeypatch.setattr(reports, "ReportService", _FakeReportService)
    monkeypatch.setattr(decisions, "DecisionService", _FakeDecisionService)
    monkeypatch.setattr(events, "EventService", _FakeEventService)
    monkeypatch.setattr(comments, "CommentService", _FakeCommentService)
    monkeypatch.setattr(attachments, "AttachmentService", _FakeAttachmentService)
    monkeypatch.setattr(metrics, "MetricsService", _FakeScalarService)
    monkeypatch.setattr(metrics, "AccuracyService", _FakeScalarService)
    monkeypatch.setattr(metrics, "FeedbackLearner", _FakeScalarService)
    monkeypatch.setattr(sla, "SlaService", _FakeScalarService)
    monkeypatch.setattr(metrics_service, "MetricsService", _FakeScalarService, raising=False)
    monkeypatch.setattr(accuracy_service, "AccuracyService", _FakeScalarService, raising=False)
    monkeypatch.setattr(feedback_learner, "FeedbackLearner", _FakeScalarService, raising=False)


@pytest.fixture
def sweep_client(admin_user: dict[str, str]) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: admin_user
    app.dependency_overrides[require_admin] = lambda: admin_user
    app.dependency_overrides[require_ticket_write] = lambda: admin_user
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sweep_viewer_client(viewer_user: dict[str, str]) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    app.dependency_overrides[get_current_user] = lambda: viewer_user
    app.dependency_overrides[require_admin] = _forbid
    app.dependency_overrides[require_ticket_write] = _forbid
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def sweep_anon_client() -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: _FakeDb()
    app.dependency_overrides[get_current_user] = _unauthenticated
    app.dependency_overrides[require_admin] = _unauthenticated
    app.dependency_overrides[require_ticket_write] = _unauthenticated
    try:
        yield TestClient(app, raise_server_exceptions=False)
    finally:
        app.dependency_overrides.clear()


def _api_routes() -> list[APIRoute]:
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/")
        and route.methods is not None
        and "HEAD" not in route.methods
    ]


def _route_http_methods(route: APIRoute) -> set[str]:
    methods = route.methods
    assert methods is not None
    return methods - {"HEAD", "OPTIONS"}


@pytest.mark.parametrize("route", _api_routes(), ids=lambda route: f"{','.join(sorted(route.methods))} {route.path}")
def test_admin_route_sweep_has_no_unexpected_500(route: APIRoute, sweep_client: TestClient) -> None:
    for method in sorted(_route_http_methods(route)):
        response = sweep_client.request(method, _path_for(route), json=_json_for(route, method))
        assert response.status_code < 500, f"{method} {route.path} returned {response.status_code}: {response.text[:500]}"


@pytest.mark.parametrize("route", _api_routes(), ids=lambda route: f"{','.join(sorted(route.methods))} {route.path}")
def test_viewer_route_sweep_has_no_unexpected_500(route: APIRoute, sweep_viewer_client: TestClient) -> None:
    for method in sorted(_route_http_methods(route)):
        response = sweep_viewer_client.request(method, _path_for(route), json=_json_for(route, method))
        assert response.status_code < 500, f"{method} {route.path} returned {response.status_code}: {response.text[:500]}"


@pytest.mark.parametrize("route", _api_routes(), ids=lambda route: f"{','.join(sorted(route.methods))} {route.path}")
def test_anonymous_route_sweep_has_no_unexpected_500(route: APIRoute, sweep_anon_client: TestClient) -> None:
    for method in sorted(_route_http_methods(route)):
        response = sweep_anon_client.request(method, _path_for(route), json=_json_for(route, method))
        assert response.status_code < 500, f"{method} {route.path} returned {response.status_code}: {response.text[:500]}"
