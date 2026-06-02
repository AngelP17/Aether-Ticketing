"""
Decision Drift: detect weekly drift in the decision engine's outputs.

Drift is a leading indicator that the world changed (more network
incidents, more uncertainty) and the rules engine should be reviewed.
We deliberately do not use a trained model: the drift checks are
deterministic threshold comparisons over the last two weekly windows
of `decision_records`.

Drift signals reported:

- ``priority_shift`` — mean priority in the recent 7 days vs the prior
  7 days, expressed as an absolute delta and a percentage change.
- ``uncertainty_shift`` — same idea, on `uncertainty_penalty`.
- ``review_needed_rate_shift`` — share of decisions in the
  `review_needed` band, current vs prior.
- ``root_cause_spikes`` — top root causes whose count grew by ≥ 50%
  week-over-week.
- ``status`` — ``ok`` (no signal moved > 20%), ``watch`` (one moved
  > 20%), or ``drift`` (two or more moved > 20%).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.policies import (
    BAND_REVIEW_NEEDED,
    SCORING_WEIGHTS,
)


DRIFT_THRESHOLD_PCT = 20.0
ROOT_CAUSE_SPIKE_PCT = 50.0


def _avg(rows: list[dict[str, Any]], key: str) -> float:
    if not rows:
        return 0.0
    return round(sum(float(r.get(key) or 0) for r in rows) / len(rows), 4)


def _band_share(rows: list[dict[str, Any]], band: str) -> float:
    if not rows:
        return 0.0
    matches = sum(1 for r in rows if r.get("decision_band") == band)
    return round(100.0 * matches / len(rows), 2)


def detect_priority_shift(current: list[dict[str, Any]], prior: list[dict[str, Any]]) -> dict[str, Any]:
    current_mean = _avg(current, "priority_score")
    prior_mean = _avg(prior, "priority_score")
    delta = round(current_mean - prior_mean, 4)
    pct = round(100.0 * delta / max(prior_mean, 0.01), 2)
    return {
        "current_mean": current_mean,
        "prior_mean": prior_mean,
        "delta": delta,
        "pct_change": pct,
        "drift_flag": abs(pct) >= DRIFT_THRESHOLD_PCT,
    }


def detect_uncertainty_shift(
    current: list[dict[str, Any]], prior: list[dict[str, Any]]
) -> dict[str, Any]:
    current_mean = _avg(current, "uncertainty_penalty")
    prior_mean = _avg(prior, "uncertainty_penalty")
    delta = round(current_mean - prior_mean, 4)
    pct = round(100.0 * delta / max(prior_mean, 0.01), 2)
    return {
        "current_mean": current_mean,
        "prior_mean": prior_mean,
        "delta": delta,
        "pct_change": pct,
        "drift_flag": abs(pct) >= DRIFT_THRESHOLD_PCT,
    }


def detect_review_needed_rate_shift(
    current: list[dict[str, Any]], prior: list[dict[str, Any]]
) -> dict[str, Any]:
    current_rate = _band_share(current, BAND_REVIEW_NEEDED)
    prior_rate = _band_share(prior, BAND_REVIEW_NEEDED)
    delta = round(current_rate - prior_rate, 2)
    pct = round(100.0 * delta / max(prior_rate, 0.01), 2)
    return {
        "current_rate": current_rate,
        "prior_rate": prior_rate,
        "delta": delta,
        "pct_change": pct,
        "drift_flag": abs(delta) >= DRIFT_THRESHOLD_PCT,
    }


def detect_root_cause_spikes(
    current: list[dict[str, Any]], prior: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    current_counts: dict[str, int] = {}
    for row in current:
        cause = (row.get("root_cause_hypothesis") or "unknown").strip() or "unknown"
        current_counts[cause] = current_counts.get(cause, 0) + 1
    prior_counts: dict[str, int] = {}
    for row in prior:
        cause = (row.get("root_cause_hypothesis") or "unknown").strip() or "unknown"
        prior_counts[cause] = prior_counts.get(cause, 0) + 1
    spikes: list[dict[str, Any]] = []
    for cause, current_count in current_counts.items():
        prior_count = prior_counts.get(cause, 0)
        if prior_count == 0 and current_count < 3:
            continue
        baseline = max(prior_count, 1)
        pct = round(100.0 * (current_count - prior_count) / baseline, 2)
        if pct >= ROOT_CAUSE_SPIKE_PCT:
            spikes.append(
                {
                    "root_cause": cause,
                    "current_count": current_count,
                    "prior_count": prior_count,
                    "pct_change": pct,
                }
            )
    spikes.sort(key=lambda item: item["pct_change"], reverse=True)
    return spikes


def compute_drift_status(signals: dict[str, bool]) -> str:
    flagged = sum(1 for value in signals.values() if value)
    if flagged >= 2:
        return "drift"
    if flagged == 1:
        return "watch"
    return "ok"


def fetch_window(
    db: Session,
    *,
    start: datetime,
    end: datetime,
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                priority_score,
                uncertainty_penalty,
                confidence_score,
                root_cause_hypothesis,
                decision_band
            FROM decision_records
            WHERE decision_ts >= :start AND decision_ts < :end
            ORDER BY decision_ts ASC
            """
        ),
        {"start": start, "end": end},
    ).mappings()
    return [dict(row) for row in rows]


def run_drift_detection(
    db: Session,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Run the full weekly drift check and return a JSON-shaped payload."""
    now = now or datetime.now(timezone.utc)
    current_start = now - timedelta(days=7)
    prior_start = now - timedelta(days=14)
    prior_end = current_start

    current = fetch_window(db, start=current_start, end=now)
    prior = fetch_window(db, start=prior_start, end=prior_end)

    priority_shift = detect_priority_shift(current, prior)
    uncertainty_shift = detect_uncertainty_shift(current, prior)
    review_rate_shift = detect_review_needed_rate_shift(current, prior)
    root_cause_spikes = detect_root_cause_spikes(current, prior)

    status = compute_drift_status(
        {
            "priority_shift": priority_shift["drift_flag"],
            "uncertainty_shift": uncertainty_shift["drift_flag"],
            "review_needed_rate": review_rate_shift["drift_flag"],
            "root_cause_spikes": bool(root_cause_spikes),
        }
    )

    return {
        "status": status,
        "thresholds": {
            "drift_threshold_pct": DRIFT_THRESHOLD_PCT,
            "root_cause_spike_pct": ROOT_CAUSE_SPIKE_PCT,
        },
        "window": {
            "current": {"start": current_start.isoformat(), "end": now.isoformat()},
            "prior": {"start": prior_start.isoformat(), "end": prior_end.isoformat()},
        },
        "current_decision_count": len(current),
        "prior_decision_count": len(prior),
        "priority_shift": priority_shift,
        "uncertainty_shift": uncertainty_shift,
        "review_needed_rate_shift": review_rate_shift,
        "root_cause_spikes": root_cause_spikes,
        "rule_version": SCORING_WEIGHTS.version_tag,
        "engine": "deterministic graph + rules (no trained model)",
    }
