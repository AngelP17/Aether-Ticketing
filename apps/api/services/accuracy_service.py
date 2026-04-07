from __future__ import annotations

import math

from sqlalchemy import text
from sqlalchemy.orm import Session


class AccuracyService:
    def __init__(self, db: Session):
        self.db = db

    def compute_classification_accuracy(self, days: int = 7) -> dict:
        row = (
            self.db.execute(
                text(
                    """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE feedback_type = 'accepted') AS accepted,
                    COUNT(*) FILTER (WHERE feedback_type = 'rejected') AS rejected,
                    COUNT(*) FILTER (WHERE feedback_type = 'overridden') AS overridden
                FROM operator_feedback
                WHERE feedback_ts >= NOW() - (:days || ' days')::INTERVAL
                """
                ),
                {"days": days},
            )
            .mappings()
            .first()
        )
        if row is None or (row["total"] or 0) == 0:
            return {
                "rate": None,
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "overridden": 0,
                "period_days": days,
            }
        total = row["total"]
        accepted = row["accepted"] or 0
        rejected = row["rejected"] or 0
        overridden = row["overridden"] or 0
        correct = accepted + overridden
        rate = round(correct / total * 100, 1) if total > 0 else None
        return {
            "rate": rate,
            "total": total,
            "accepted": accepted,
            "rejected": rejected,
            "overridden": overridden,
            "period_days": days,
        }

    def compute_priority_correlation(self, days: int = 30) -> float | None:
        rows = list(
            self.db.execute(
                text(
                    """
                    SELECT
                        dr.priority_score AS automated_priority,
                        dr.root_cause_hypothesis AS automated_root_cause,
                        of.feedback_type,
                        of.feedback_note
                    FROM operator_feedback of
                    JOIN recommendations r ON r.id = of.recommendation_id
                    JOIN decision_records dr ON dr.id = r.decision_record_id
                    WHERE of.feedback_ts >= NOW() - (:days || ' days')::INTERVAL
                      AND of.feedback_type IN ('accepted', 'overridden')
                    """
                ),
                {"days": days},
            ).mappings()
        )
        if len(rows) < 3:
            return None
        automated = []
        actual = []
        for row in rows:
            automated.append(float(row["automated_priority"]))
            if row["feedback_type"] == "overridden" and row["feedback_note"]:
                try:
                    override_val = float(row["feedback_note"])
                    actual.append(override_val)
                except (ValueError, TypeError):
                    actual.append(float(row["automated_priority"]))
            else:
                actual.append(float(row["automated_priority"]))
        return _pearson_correlation(automated, actual)

    def compute_incident_accuracy(self, days: int = 7) -> dict:
        row = (
            self.db.execute(
                text(
                    """
                WITH incident_tickets AS (
                    SELECT DISTINCT i.id AS incident_id, i.opened_at, i.closed_at
                    FROM incidents i
                    WHERE i.opened_at >= NOW() - (:days || ' days')::INTERVAL
                )
                SELECT
                    COUNT(*) AS total_incidents,
                    COUNT(*) FILTER (WHERE closed_at IS NOT NULL) AS resolved,
                    COUNT(*) FILTER (WHERE closed_at IS NULL) AS still_open
                FROM incident_tickets
                """
                ),
                {"days": days},
            )
            .mappings()
            .first()
        )
        if row is None or (row["total_incidents"] or 0) == 0:
            return {
                "validity_rate": None,
                "total_created": 0,
                "resolved": 0,
                "still_open": 0,
                "period_days": days,
            }
        total = row["total_incidents"]
        resolved = row["resolved"] or 0
        still_open = row["still_open"] or 0
        validity = round((total - still_open) / total * 100, 1) if total > 0 else None
        return {
            "validity_rate": validity,
            "total_created": total,
            "resolved": resolved,
            "still_open": still_open,
            "period_days": days,
        }

    def compute_recommendation_acceptance_rate(self, days: int = 7) -> float | None:
        row = (
            self.db.execute(
                text(
                    """
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE status IN ('accepted')) AS accepted,
                    COUNT(*) FILTER (WHERE status = 'rejected') AS rejected,
                    COUNT(*) FILTER (WHERE status = 'proposed') AS pending
                FROM recommendations r
                WHERE r.created_at IS NOT NULL
                  AND EXISTS (
                      SELECT 1 FROM ticket_events te
                      WHERE te.ticket_id = (
                          SELECT dr.ticket_id FROM decision_records dr WHERE dr.id = r.decision_record_id
                      )
                      AND te.event_ts >= NOW() - (:days || ' days')::INTERVAL
                  )
                """
                ),
                {"days": days},
            )
            .mappings()
            .first()
        )
        if row is None or (row["total"] or 0) == 0:
            return None
        total = row["total"]
        accepted = row["accepted"] or 0
        return round(accepted / total * 100, 1) if total > 0 else None

    def compute_sla_compliance_rate(self, days: int = 30) -> float | None:
        row = (
            self.db.execute(
                text(
                    """
                SELECT
                    COUNT(*) AS total_closed,
                    COUNT(*) FILTER (
                        WHERE EXTRACT(EPOCH FROM (resolved_at - date_opened)) / 3600
                            <= COALESCE(
                                CASE priority
                                    WHEN 'Critical' THEN 4.0
                                    WHEN 'High' THEN 8.0
                                    WHEN 'Medium' THEN 24.0
                                    ELSE 72.0
                                END, 24.0
                            )
                    ) AS within_sla
                FROM tickets
                WHERE status IN ('Resolved', 'Closed')
                  AND resolved_at IS NOT NULL
                  AND date_opened IS NOT NULL
                  AND resolved_at >= NOW() - (:days || ' days')::INTERVAL
                """
                ),
                {"days": days},
            )
            .mappings()
            .first()
        )
        if row is None or (row["total_closed"] or 0) == 0:
            return None
        total = row["total_closed"]
        within_sla = row["within_sla"] or 0
        return round(within_sla / total * 100, 1) if total > 0 else None

    def get_all_accuracy_metrics(self, days: int = 7) -> dict:
        return {
            "classification_accuracy": self.compute_classification_accuracy(days),
            "priority_correlation": self.compute_priority_correlation(days * 4),
            "incident_accuracy": self.compute_incident_accuracy(days),
            "recommendation_acceptance_rate": self.compute_recommendation_acceptance_rate(days),
            "sla_compliance_rate": self.compute_sla_compliance_rate(days * 4),
        }


def _pearson_correlation(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3 or len(y) != n:
        return None
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    numerator = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    denom_x = math.sqrt(sum((xi - mean_x) ** 2 for xi in x))
    denom_y = math.sqrt(sum((yi - mean_y) ** 2 for yi in y))
    if denom_x == 0 or denom_y == 0:
        return None
    return round(numerator / (denom_x * denom_y), 4)
