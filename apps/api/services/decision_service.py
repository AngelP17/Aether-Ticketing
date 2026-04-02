from sqlalchemy.orm import Session
from sqlalchemy import text

from apps.api.services.operational_intelligence import (
    compute_live_decision,
    count_similar_cases,
    fetch_ticket_row,
)


class DecisionService:
    def __init__(self, db: Session):
        self.db = db

    def get_latest_decision(self, ticket_id: str, persist_if_missing: bool = True):
        existing = self.db.execute(
            text(
                """
                SELECT
                    dr.id,
                    t.ticket_id,
                    dr.priority_score,
                    dr.severity_score,
                    dr.urgency_score,
                    dr.business_impact_score,
                    dr.sla_risk_score,
                    dr.recurrence_score,
                    dr.dependency_criticality_score,
                    dr.actionability_score,
                    dr.uncertainty_penalty,
                    dr.root_cause_hypothesis,
                    dr.confidence_score,
                    dr.decision_ts
                FROM decision_records dr
                JOIN tickets t ON t.id = dr.ticket_id
                WHERE t.ticket_id = :ticket_id
                ORDER BY dr.decision_ts DESC, dr.id DESC
                LIMIT 1
                """
            ),
            {"ticket_id": ticket_id},
        ).mappings().first()
        if existing:
            payload = dict(existing)
            payload["recommendations"] = self._load_recommendations(payload["id"])
            return payload
        if not persist_if_missing:
            ticket = fetch_ticket_row(self.db, ticket_id)
            if ticket is None:
                return None
            return compute_live_decision(ticket, count_similar_cases(self.db, ticket))
        return self.recompute_decision(ticket_id)

    def recompute_decision(self, ticket_id: str):
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        similar_cases_count = count_similar_cases(self.db, ticket)
        decision = compute_live_decision(ticket, similar_cases_count)

        inserted = self.db.execute(
            text(
                """
                INSERT INTO decision_records (
                    ticket_id,
                    decision_ts,
                    feature_snapshot_json,
                    severity_score,
                    urgency_score,
                    business_impact_score,
                    sla_risk_score,
                    recurrence_score,
                    dependency_criticality_score,
                    actionability_score,
                    uncertainty_penalty,
                    priority_score,
                    root_cause_hypothesis,
                    confidence_score,
                    decision_version,
                    rule_version,
                    model_version,
                    explanation_json
                )
                VALUES (
                    :ticket_pk,
                    NOW(),
                    CAST(:feature_snapshot_json AS JSONB),
                    :severity_score,
                    :urgency_score,
                    :business_impact_score,
                    :sla_risk_score,
                    :recurrence_score,
                    :dependency_criticality_score,
                    :actionability_score,
                    :uncertainty_penalty,
                    :priority_score,
                    :root_cause_hypothesis,
                    :confidence_score,
                    'v1',
                    'rules-2026-04',
                    NULL,
                    CAST(:explanation_json AS JSONB)
                )
                RETURNING id, decision_ts
                """
            ),
            {
                **decision,
                "ticket_pk": ticket["id"],
                "feature_snapshot_json": __import__("json").dumps(decision["feature_snapshot_json"]),
                "explanation_json": __import__("json").dumps(decision["explanation_json"]),
            },
        ).mappings().first()

        decision_id = int(inserted["id"])
        decision_ts = inserted["decision_ts"].isoformat()
        self.db.execute(
            text(
                """
                DELETE FROM recommendations
                WHERE decision_record_id = :decision_id
                """
            ),
            {"decision_id": decision_id},
        )
        for recommendation in decision["recommendations"]:
            self.db.execute(
                text(
                    """
                    INSERT INTO recommendations (
                        decision_record_id,
                        rank,
                        action_type,
                        action_label,
                        rationale,
                        risk_level,
                        expected_benefit,
                        confidence,
                        requires_approval,
                        recommended_runbook_id,
                        status
                    )
                    VALUES (
                        :decision_record_id,
                        :rank,
                        :action_type,
                        :action_label,
                        :rationale,
                        :risk_level,
                        :expected_benefit,
                        :confidence,
                        FALSE,
                        :recommended_runbook_id,
                        'proposed'
                    )
                    """
                ),
                {
                    **recommendation,
                    "decision_record_id": decision_id,
                },
            )

        self.db.execute(
            text(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    event_type,
                    event_ts,
                    actor_type,
                    actor_id,
                    payload_json,
                    source_hash
                )
                VALUES (
                    :ticket_pk,
                    'decision_generated',
                    NOW(),
                    'system',
                    'aether-api',
                    CAST(:payload_json AS JSONB),
                    :source_hash
                )
                """
            ),
            {
                "ticket_pk": ticket["id"],
                "payload_json": __import__("json").dumps(
                    {
                        "priority_score": decision["priority_score"],
                        "root_cause_hypothesis": decision["root_cause_hypothesis"],
                    }
                ),
                "source_hash": ticket.get("source_hash"),
            },
        )

        self.db.execute(
            text(
                """
                UPDATE tickets
                SET clean_summary = :clean_summary,
                    source_hash = COALESCE(source_hash, :source_hash),
                    updated_at = NOW()
                WHERE id = :ticket_pk
                """
            ),
            {
                "ticket_pk": ticket["id"],
                "clean_summary": decision["clean_summary"],
                "source_hash": ticket.get("source_hash"),
            },
        )
        self.db.commit()

        return {
            "id": decision_id,
            "ticket_id": ticket["ticket_id"],
            "priority_score": decision["priority_score"],
            "severity_score": decision["severity_score"],
            "urgency_score": decision["urgency_score"],
            "business_impact_score": decision["business_impact_score"],
            "sla_risk_score": decision["sla_risk_score"],
            "recurrence_score": decision["recurrence_score"],
            "dependency_criticality_score": decision["dependency_criticality_score"],
            "actionability_score": decision["actionability_score"],
            "uncertainty_penalty": decision["uncertainty_penalty"],
            "root_cause_hypothesis": decision["root_cause_hypothesis"],
            "confidence_score": decision["confidence_score"],
            "decision_ts": decision_ts,
            "recommendations": self._load_recommendations(decision_id),
        }

    def _load_recommendations(self, decision_id: int) -> list[dict]:
        rows = self.db.execute(
            text(
                """
                SELECT
                    id,
                    rank,
                    action_type,
                    action_label,
                    rationale,
                    risk_level,
                    expected_benefit,
                    confidence,
                    recommended_runbook_id,
                    status
                FROM recommendations
                WHERE decision_record_id = :decision_id
                ORDER BY rank ASC, id ASC
                """
            ),
            {"decision_id": decision_id},
        ).mappings()
        return [dict(row) for row in rows]
