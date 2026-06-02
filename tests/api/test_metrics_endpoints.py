"""
Endpoint tests for /api/metrics.

Three routes:
- GET /api/metrics              — queue metrics
- GET /api/metrics/accuracy     — accuracy + drift metrics
- GET /api/metrics/feedback/summary — feedback pattern summary
"""
from __future__ import annotations

from typing import Any

import pytest

from apps.api.services import accuracy_service, metrics_service
from infrastructure.logging import feedback_learner


def test_get_metrics_returns_queue_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            metrics_service.MetricsService,
            "get_queue_metrics",
            lambda self: {
                "total_open": 12,
                "critical": 3,
                "sla_breach_risk": 5,
                "incident_clusters": 2,
            },
        )
        response = admin_client.get("/api/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "total_open": 12,
        "critical": 3,
        "sla_breach_risk": 5,
        "incident_clusters": 2,
    }


def test_get_accuracy_metrics_returns_payload(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            accuracy_service.AccuracyService,
            "get_all_accuracy_metrics",
            lambda self, days: {
                "window_days": days,
                "acceptance_rate": 0.6,
                "rejection_rate": 0.4,
            },
        )
        response = admin_client.get("/api/metrics/accuracy?days=14")
    assert response.status_code == 200
    body = response.json()
    assert body["window_days"] == 14
    assert body["acceptance_rate"] == 0.6


def test_get_accuracy_metrics_rejects_out_of_range(admin_client: Any) -> None:
    response = admin_client.get("/api/metrics/accuracy?days=999")
    assert response.status_code == 422
    response = admin_client.get("/api/metrics/accuracy?days=0")
    assert response.status_code == 422


def test_get_feedback_summary_returns_patterns(admin_client: Any) -> None:
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            feedback_learner.FeedbackLearner,
            "get_pattern_summary",
            lambda self: {
                "by_root_cause": {"file_share_permissions": {"accepted": 6, "rejected": 1}},
                "adjustments_pending": 0,
            },
        )
        response = admin_client.get("/api/metrics/feedback/summary")
    assert response.status_code == 200
    body = response.json()
    assert "file_share_permissions" in body["by_root_cause"]
    assert body["by_root_cause"]["file_share_permissions"]["accepted"] == 6


def test_metrics_does_not_require_authentication(anon_client: Any) -> None:
    # /api/metrics is consumed by the command center which is gated by the UI.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(
            metrics_service.MetricsService,
            "get_queue_metrics",
            lambda self: {"total_open": 0, "critical": 0, "sla_breach_risk": 0, "incident_clusters": 0},
        )
        monkeypatch.setattr(
            accuracy_service.AccuracyService,
            "get_all_accuracy_metrics",
            lambda self, days: {"window_days": days},
        )
        monkeypatch.setattr(
            feedback_learner.FeedbackLearner,
            "get_pattern_summary",
            lambda self: {},
        )
        assert anon_client.get("/api/metrics").status_code == 200
        assert anon_client.get("/api/metrics/accuracy").status_code == 200
        assert anon_client.get("/api/metrics/feedback/summary").status_code == 200
