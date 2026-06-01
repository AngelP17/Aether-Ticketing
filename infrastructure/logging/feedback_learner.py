from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

_ADJUSTMENT_CAP = 20.0
_DECAY_FACTOR = 0.85


class FeedbackLearner:
    def __init__(self, db: Session) -> None:
        self.db = db
        self._pattern_cache: dict[str, Any] | None = None

    def get_adjusted_confidence(self, root_cause: str, confidence: float) -> float:
        if self._pattern_cache is None:
            self._pattern_cache = self._load_adjustments()
        key = root_cause.lower()
        adjustment = float(self._pattern_cache.get(key, 0.0) or 0.0)
        adjusted = confidence + adjustment
        return max(0.0, min(99.0, adjusted))

    def recompute_pattern_adjustments(self) -> dict[str, Any]:
        rows = list(
            self.db.execute(
                text(
                    """
                    SELECT
                        dr.root_cause_hypothesis,
                        of.feedback_type,
                        COUNT(*) AS cnt
                    FROM operator_feedback of
                    JOIN recommendations r ON r.id = of.recommendation_id
                    JOIN decision_records dr ON dr.id = r.decision_record_id
                    GROUP BY dr.root_cause_hypothesis, of.feedback_type
                    """
                )
            ).mappings()
        )
        pattern_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in rows:
            root_cause = (row["root_cause_hypothesis"] or "unknown").lower()
            fb_type = row["feedback_type"]
            pattern_totals[root_cause][fb_type] += row["cnt"]

        adjustments: dict[str, Any] = {}
        for pattern, counts in pattern_totals.items():
            total = sum(counts.values())
            accepted = counts.get("accepted", 0)
            overridden = counts.get("overridden", 0)
            if total == 0:
                continue
            accept_rate = (accepted + overridden) / total
            if accept_rate >= 0.8:
                delta = min((accept_rate - 0.5) * 10, _ADJUSTMENT_CAP)
            elif accept_rate <= 0.4:
                delta = -min((0.5 - accept_rate) * 10, _ADJUSTMENT_CAP)
            else:
                delta = 0.0
            adjustments[pattern] = round(delta, 2)

        self._pattern_cache = adjustments
        return adjustments

    def get_pattern_summary(self) -> list[dict[str, Any]]:
        adjustments = self._pattern_cache or self._load_adjustments()
        if not adjustments:
            adjustments = self.recompute_pattern_adjustments()
        return [
            {"pattern": pattern, "confidence_adjustment": adj}
            for pattern, adj in sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        ]

    def _load_adjustments(self) -> dict[str, Any]:
        rows = list(
            self.db.execute(
                text(
                    """
                    SELECT
                        dr.root_cause_hypothesis AS pattern,
                        of.feedback_type,
                        COUNT(*) AS cnt
                    FROM operator_feedback of
                    JOIN recommendations r ON r.id = of.recommendation_id
                    JOIN decision_records dr ON dr.id = r.decision_record_id
                    GROUP BY dr.root_cause_hypothesis, of.feedback_type
                    """
                )
            ).mappings()
        )
        pattern_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for row in rows:
            pattern = (row["pattern"] or "unknown").lower()
            fb_type = row["feedback_type"]
            pattern_totals[pattern][fb_type] += row["cnt"]

        adjustments: dict[str, Any] = {}
        for pattern, counts in pattern_totals.items():
            total = sum(counts.values())
            accepted = counts.get("accepted", 0)
            overridden = counts.get("overridden", 0)
            if total == 0:
                continue
            accept_rate = (accepted + overridden) / total
            if accept_rate >= 0.8:
                delta = min((accept_rate - 0.5) * 10, _ADJUSTMENT_CAP)
            elif accept_rate <= 0.4:
                delta = -min((0.5 - accept_rate) * 10, _ADJUSTMENT_CAP)
            else:
                delta = 0.0
            adjustments[pattern] = round(delta, 2)
        return adjustments
