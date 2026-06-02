from __future__ import annotations

from typing import Any

from pipelines.decisions.decision_hash import (
    compute_decision_hash,
    short_decision_hash,
)


def _kwargs(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "ticket_id": "T-1",
        "priority_score": 72.5,
        "decision_band": "high_confidence_action",
        "root_cause_hypothesis": "switch uplink down",
        "confidence_score": 84.0,
        "feature_snapshot_json": {"severity": 60.0, "urgency": 55.0},
        "explanation_json": {"rationale": "site-wide outage"},
        "rule_version": "rules-2026-graph",
    }
    base.update(overrides)
    return base


def test_decision_hash_is_deterministic_for_same_inputs() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(**_kwargs())
    assert first == second
    assert len(first) == 64


def test_decision_hash_changes_when_priority_changes() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(**_kwargs(priority_score=80.0))
    assert first != second


def test_decision_hash_changes_when_band_changes() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(**_kwargs(decision_band="review_needed"))
    assert first != second


def test_decision_hash_changes_when_rule_version_changes() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(**_kwargs(rule_version="rules-2024-Q1"))
    assert first != second


def test_decision_hash_changes_when_feature_snapshot_changes() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(
        **_kwargs(feature_snapshot_json={"severity": 90.0, "urgency": 55.0}),
    )
    assert first != second


def test_decision_hash_accepts_missing_snapshots() -> None:
    first = compute_decision_hash(**_kwargs())
    second = compute_decision_hash(
        **_kwargs(feature_snapshot_json=None, explanation_json=None),
    )
    assert first != second


def test_short_decision_hash_returns_first_twelve_chars() -> None:
    full = compute_decision_hash(**_kwargs())
    assert short_decision_hash(full) == full[:12]
