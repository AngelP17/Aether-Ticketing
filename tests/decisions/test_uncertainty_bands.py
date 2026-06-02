from __future__ import annotations

from domain.policies import (
    BAND_HIGH_CONFIDENCE_ACTION,
    BAND_REVIEW_NEEDED,
    BAND_STANDARD_QUEUE,
)
from pipelines.decisions.uncertainty_bands import (
    band_payload,
    band_to_operator_action,
    classify_band,
    priority_interval,
)


def test_high_confidence_band_requires_all_three_signals() -> None:
    assert (
        classify_band(
            priority_score=80.0,
            confidence_score=85.0,
            uncertainty_penalty=10.0,
        )
        == BAND_HIGH_CONFIDENCE_ACTION
    )


def test_review_needed_for_low_confidence() -> None:
    assert (
        classify_band(
            priority_score=80.0,
            confidence_score=50.0,
            uncertainty_penalty=10.0,
        )
        == BAND_REVIEW_NEEDED
    )


def test_review_needed_for_high_uncertainty() -> None:
    assert (
        classify_band(
            priority_score=80.0,
            confidence_score=85.0,
            uncertainty_penalty=30.0,
        )
        == BAND_REVIEW_NEEDED
    )


def test_review_needed_for_low_priority() -> None:
    assert (
        classify_band(
            priority_score=40.0,
            confidence_score=85.0,
            uncertainty_penalty=10.0,
        )
        == BAND_REVIEW_NEEDED
    )


def test_standard_queue_when_graph_density_positive() -> None:
    band = classify_band(
        priority_score=60.0,
        confidence_score=75.0,
        uncertainty_penalty=15.0,
        graph_signal_density=0.5,
    )
    assert band == BAND_STANDARD_QUEUE


def test_review_needed_when_no_graph_neighbors() -> None:
    band = classify_band(
        priority_score=60.0,
        confidence_score=75.0,
        uncertainty_penalty=15.0,
        graph_signal_density=0.0,
    )
    assert band == BAND_REVIEW_NEEDED


def test_priority_interval_widens_with_uncertainty_and_caps_at_twenty() -> None:
    low, high = priority_interval(priority_score=50.0, uncertainty_penalty=10.0)
    assert low == 46.0
    assert high == 54.0
    low_capped, high_capped = priority_interval(priority_score=50.0, uncertainty_penalty=200.0)
    assert high_capped - low_capped == 40.0


def test_priority_interval_clamps_to_zero_and_hundred() -> None:
    low, high = priority_interval(priority_score=2.0, uncertainty_penalty=50.0)
    assert low == 0.0
    assert high == 22.0
    high_only = priority_interval(priority_score=98.0, uncertainty_penalty=50.0)
    assert high_only[1] == 100.0


def test_band_to_operator_action() -> None:
    assert "Apply" in band_to_operator_action(BAND_HIGH_CONFIDENCE_ACTION)
    assert "Review" in band_to_operator_action(BAND_REVIEW_NEEDED)
    assert "Triage" in band_to_operator_action(BAND_STANDARD_QUEUE)


def test_band_payload_includes_interval_and_rationale() -> None:
    payload = band_payload(
        priority_score=80.0,
        confidence_score=85.0,
        uncertainty_penalty=10.0,
    )
    assert payload["decision_band"] == BAND_HIGH_CONFIDENCE_ACTION
    assert payload["priority_interval_low"] <= payload["priority_interval_high"]
    assert "priority" in payload["band_rationale"]


def test_band_payload_marks_graph_isolation_in_rationale() -> None:
    payload = band_payload(
        priority_score=60.0,
        confidence_score=75.0,
        uncertainty_penalty=15.0,
        graph_signal_density=0.0,
    )
    assert payload["decision_band"] == BAND_REVIEW_NEEDED
    assert "graph" in payload["band_rationale"]
