from __future__ import annotations

from pipelines.governance.decision_drift import (
    compute_drift_status,
    detect_priority_shift,
    detect_review_needed_rate_shift,
    detect_root_cause_spikes,
    detect_uncertainty_shift,
)


def test_priority_shift_flags_movement_above_threshold() -> None:
    current = [{"priority_score": 80.0}, {"priority_score": 76.0}]
    prior = [{"priority_score": 50.0}, {"priority_score": 52.0}]
    payload = detect_priority_shift(current, prior)
    assert payload["drift_flag"] is True
    assert payload["delta"] > 0
    assert payload["pct_change"] >= 20.0


def test_priority_shift_below_threshold_returns_false() -> None:
    current = [{"priority_score": 52.0}, {"priority_score": 51.0}]
    prior = [{"priority_score": 50.0}, {"priority_score": 50.0}]
    payload = detect_priority_shift(current, prior)
    assert payload["drift_flag"] is False


def test_uncertainty_shift_detects_negative_movement() -> None:
    current = [{"uncertainty_penalty": 5.0}, {"uncertainty_penalty": 6.0}]
    prior = [{"uncertainty_penalty": 30.0}, {"uncertainty_penalty": 28.0}]
    payload = detect_uncertainty_shift(current, prior)
    assert payload["drift_flag"] is True


def test_review_needed_rate_shift_flags_change() -> None:
    current = [
        {"decision_band": "review_needed"},
        {"decision_band": "review_needed"},
    ]
    prior = [{"decision_band": "standard_queue"}]
    payload = detect_review_needed_rate_shift(current, prior)
    assert payload["current_rate"] == 100.0
    assert payload["drift_flag"] is True


def test_root_cause_spikes_only_when_pct_above_fifty() -> None:
    current = [
        {"root_cause_hypothesis": "switch down"},
        {"root_cause_hypothesis": "switch down"},
        {"root_cause_hypothesis": "switch down"},
    ]
    prior = [{"root_cause_hypothesis": "switch down"}]
    spikes = detect_root_cause_spikes(current, prior)
    assert any(spike["root_cause"] == "switch down" for spike in spikes)


def test_root_cause_spikes_ignores_brand_new_minor_cause() -> None:
    current: list[dict[str, object]] = [{"root_cause_hypothesis": "new cause"}]
    prior: list[dict[str, object]] = []
    assert detect_root_cause_spikes(current, prior) == []


def test_compute_drift_status_uses_signal_count() -> None:
    assert compute_drift_status({}) == "ok"
    assert (
        compute_drift_status({"a": True, "b": False, "c": False})
        == "watch"
    )
    assert (
        compute_drift_status({"a": True, "b": True, "c": False})
        == "drift"
    )
