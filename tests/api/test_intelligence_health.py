"""
Tests for /api/intelligence/health.

The endpoint depends on a real Postgres connection. We mount the test app
with an override `get_db` that returns a stub session so we can assert
the shape of the response without standing up Postgres for unit tests.
"""
from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from apps.api.deps import get_db
from apps.api.main import app


class _StubScalarResult:
    def __init__(self, row: dict[str, Any] | None) -> None:
        self._row = row

    def mappings(self) -> "_StubScalarResult":
        return self

    def first(self) -> dict[str, Any] | None:
        return self._row

    def __iter__(self) -> Any:
        return iter(self._row.get("rows", []) if self._row else [])


class _StubExecuteResult:
    def __init__(self, rows: list[dict[str, Any]] | None = None, single: dict[str, Any] | None = None) -> None:
        if single is not None:
            self._first: dict[str, Any] | None = single
            self._rows: list[dict[str, Any]] = []
        else:
            self._first = None
            self._rows = rows or []

    def mappings(self) -> "_StubScalarResult":
        if self._first is not None:
            return _StubScalarResult(self._first)
        return _StubScalarResult({"rows": self._rows})

    def first(self) -> dict[str, Any] | None:
        return self._first


class _StubSession:
    """Tiny in-memory session that responds to the limited surface the health endpoint uses."""

    def __init__(self) -> None:
        self.tickets = 7
        self.decision_records: list[dict[str, Any]] = [
            {"decision_ts": datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc)},
        ]
        self.feedback: list[dict[str, Any]] = [
            {"feedback_ts": datetime(2026, 6, 1, 13, 0, tzinfo=timezone.utc), "type": "accepted"},
            {"feedback_ts": datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc), "type": "rejected"},
        ]
        self.action_runs: list[dict[str, Any]] = [
            {"started_at": datetime(2026, 6, 1, 13, 30, tzinfo=timezone.utc), "status": "completed_manual"},
            {"started_at": datetime(2026, 6, 1, 14, 0, tzinfo=timezone.utc), "status": "pending_review"},
        ]
        self.recommendations = 3
        self.incidents = 2
        self.similar_case_links = 12

    def execute(self, statement: Any, params: dict[str, Any] | None = None) -> _StubExecuteResult:  # noqa: ARG002
        text_stmt = str(statement).strip().lower()
        if "from tickets" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": self.tickets})
        if "from decision_records" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": len(self.decision_records)})
        if "from operator_feedback" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": len(self.feedback)})
        if "from action_runs" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": len(self.action_runs)})
        if "from recommendations" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": self.recommendations})
        if "from incidents" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": self.incidents})
        if "from similar_case_links" in text_stmt and "count(*)" in text_stmt:
            return _StubExecuteResult(single={"c": self.similar_case_links})
        if "max(decision_ts)" in text_stmt:
            return _StubExecuteResult(single={"ts": self.decision_records[0]["decision_ts"]})
        if "max(feedback_ts)" in text_stmt:
            return _StubExecuteResult(single={"ts": max(f["feedback_ts"] for f in self.feedback)})
        if "max(started_at)" in text_stmt:
            return _StubExecuteResult(single={"ts": max(a["started_at"] for a in self.action_runs)})
        if "from operator_feedback" in text_stmt and "group by" in text_stmt:
            fb_counts: dict[str, int] = {}
            for row in self.feedback:
                fb_type = row["type"]
                fb_counts[fb_type] = fb_counts.get(fb_type, 0) + 1
            return _StubExecuteResult(rows=[{"feedback_type": k, "c": v} for k, v in fb_counts.items()])
        if "from action_runs" in text_stmt and "group by" in text_stmt:
            run_counts: dict[str, int] = {}
            for row in self.action_runs:
                run_status = row["status"]
                run_counts[run_status] = run_counts.get(run_status, 0) + 1
            return _StubExecuteResult(rows=[{"status": k, "c": v} for k, v in run_counts.items()])
        return _StubExecuteResult(single=None)


def _override_get_db() -> Any:
    return _StubSession()


def _override_current_user() -> dict[str, str]:
    return {"username": "admin", "role": "admin", "display_name": "Admin"}


def test_intelligence_health_returns_truthful_disclosure() -> None:
    app.dependency_overrides[get_db] = _override_get_db
    from apps.api.security import get_current_user

    app.dependency_overrides[get_current_user] = _override_current_user
    try:
        client = TestClient(app)
        response = client.get("/api/intelligence/health", headers={"Authorization": "Bearer fake"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["engine"]["name"] == "rules"
    assert body["engine"]["kind"] == "deterministic graph + rules"
    assert body["engine"]["model_version"] is None
    assert body["engine"]["version"] == "rules-2026-graph-v2"
    assert body["engine"]["decision_schema_version"] == "v2"
    assert body["truthful_disclosure"] == {
        "no_external_llm": True,
        "no_trained_ml_model": True,
        "actions_are_real_workflow_mutations": True,
        "runbooks_require_human_review": True,
        "graph_features_are_deterministic": True,
        "decision_hash_is_deterministic": True,
    }
    assert body["subsystems"]["tickets"]["count"] == 7
    assert body["subsystems"]["incidents"]["stable_ids"] is True
    assert body["feedback_loop"]["enabled"] is True
    assert body["feedback_loop"]["adjustment_cap"] == 20.0
