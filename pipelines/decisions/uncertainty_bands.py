"""
Uncertainty bands: classify a decision into one of three review bands.

The band is a deterministic, auditable label that tells the operator
how much attention a recommendation needs. It is computed from the
priority score, confidence, uncertainty penalty, and the graph
density — no external service, no trained model.

Bands:

- ``high_confidence_action`` — high priority + high confidence + low
  uncertainty. Operator can act directly.
- ``review_needed`` — low confidence, low priority, or high
  uncertainty. Operator should review before acting.
- ``standard_queue`` — everything in between.
"""
from __future__ import annotations

from typing import Any

from domain.policies import (
    BAND_HIGH_CONFIDENCE_ACTION,
    BAND_REVIEW_NEEDED,
    BAND_STANDARD_QUEUE,
    UNCERTAINTY_BAND_THRESHOLDS,
)


def classify_band(
    *,
    priority_score: float,
    confidence_score: float,
    uncertainty_penalty: float,
    graph_signal_density: float = 0.0,
) -> str:
    """Return the decision band label for a ticket decision."""
    thresholds = UNCERTAINTY_BAND_THRESHOLDS

    if (
        priority_score >= thresholds.HIGH_CONFIDENCE_MIN_PRIORITY
        and confidence_score >= thresholds.HIGH_CONFIDENCE_MIN_CONFIDENCE
        and uncertainty_penalty < thresholds.UNCERTAINTY_PENALTY_REVIEW
    ):
        return BAND_HIGH_CONFIDENCE_ACTION

    has_review_signal = (
        confidence_score <= thresholds.REVIEW_NEEDED_MAX_CONFIDENCE
        or priority_score <= thresholds.REVIEW_NEEDED_MAX_PRIORITY
        or uncertainty_penalty >= thresholds.UNCERTAINTY_PENALTY_REVIEW
    )
    if has_review_signal:
        return BAND_REVIEW_NEEDED

    if graph_signal_density <= 0.0:
        return BAND_REVIEW_NEEDED

    return BAND_STANDARD_QUEUE


def priority_interval(
    *,
    priority_score: float,
    uncertainty_penalty: float,
) -> tuple[float, float]:
    """Return a [low, high] interval that expresses the score's uncertainty.

    The interval widens with the uncertainty penalty, capped at
    ±20 points so it remains informative without spilling out of the
    0-100 priority scale.
    """
    half_width = min(20.0, uncertainty_penalty * 0.4)
    low = max(0.0, round(priority_score - half_width, 2))
    high = min(100.0, round(priority_score + half_width, 2))
    return low, high


def band_to_operator_action(band: str) -> str:
    """Map a band to a recommended operator action."""
    if band == BAND_HIGH_CONFIDENCE_ACTION:
        return "Apply highest-ranked recommendation directly."
    if band == BAND_REVIEW_NEEDED:
        return "Review and gather more context before acting."
    return "Triage via the standard queue."


def band_payload(
    *,
    priority_score: float,
    confidence_score: float,
    uncertainty_penalty: float,
    graph_signal_density: float = 0.0,
) -> dict[str, Any]:
    """Return a structured payload combining band, interval, and rationale."""
    band = classify_band(
        priority_score=priority_score,
        confidence_score=confidence_score,
        uncertainty_penalty=uncertainty_penalty,
        graph_signal_density=graph_signal_density,
    )
    low, high = priority_interval(
        priority_score=priority_score,
        uncertainty_penalty=uncertainty_penalty,
    )
    rationale_bits: list[str] = []
    if band == BAND_HIGH_CONFIDENCE_ACTION:
        rationale_bits.append("priority ≥ 70 with confidence ≥ 80 and low uncertainty")
    elif band == BAND_REVIEW_NEEDED:
        if confidence_score <= UNCERTAINTY_BAND_THRESHOLDS.REVIEW_NEEDED_MAX_CONFIDENCE:
            rationale_bits.append("confidence is low")
        if priority_score <= UNCERTAINTY_BAND_THRESHOLDS.REVIEW_NEEDED_MAX_PRIORITY:
            rationale_bits.append("priority is low")
        if uncertainty_penalty >= UNCERTAINTY_BAND_THRESHOLDS.UNCERTAINTY_PENALTY_REVIEW:
            rationale_bits.append("uncertainty penalty is high")
        if graph_signal_density <= 0.0:
            rationale_bits.append("graph has no neighbors")
    else:
        rationale_bits.append("standard queue (mid-band)")

    return {
        "decision_band": band,
        "priority_interval_low": low,
        "priority_interval_high": high,
        "band_rationale": "; ".join(rationale_bits),
        "operator_action": band_to_operator_action(band),
    }
