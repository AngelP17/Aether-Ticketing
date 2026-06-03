from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.services.graph_intelligence_service import features_for_ticket
from apps.api.services.operational_intelligence import (
    compute_live_decision,
    count_similar_cases,
    fetch_ticket_row,
)
from pipelines.decisions.decision_hash import compute_decision_hash
from pipelines.decisions.uncertainty_bands import band_payload


def _compute_anomaly_zscore(priority_score: float, category_scores: list[float]) -> float:
    if len(category_scores) < 5:
        return 0.0
    mean = sum(category_scores) / len(category_scores)
    variance = sum((s - mean) ** 2 for s in category_scores) / len(category_scores)
    std = math.sqrt(variance) or 1.0
    return round((priority_score - mean) / std, 2)


class DecisionService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_latest_decision(self, ticket_id: str, persist_if_missing: bool = True) -> Any:
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
                    dr.decision_ts,
                    dr.decision_version,
                    dr.rule_version,
                    dr.model_version,
                    dr.decision_band,
                    dr.priority_interval_low,
                    dr.priority_interval_high,
                    dr.decision_hash,
                    dr.graph_degree,
                    dr.graph_weighted_degree,
                    dr.anomaly_zscore,
                    dr.feature_snapshot_json,
                    dr.explanation_json
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
            payload = _serialize_decision(dict(existing))
            payload["recommendations"] = self._load_recommendations(payload["id"])
            return payload
        if not persist_if_missing:
            ticket = fetch_ticket_row(self.db, ticket_id)
            if ticket is None:
                return None
            # Use graph even in fallback path so centrality affects score
            try:
                gfeat = features_for_ticket(self.db, ticket_id)
                gcent = float(gfeat.get("graph_centrality", 0.0) or 0.0)
            except Exception:
                gcent = 0.0
            return compute_live_decision(ticket, count_similar_cases(self.db, ticket), graph_centrality=gcent)
        return self.recompute_decision(ticket_id)

    def recompute_decision(self, ticket_id: str) -> Any:
        ticket = fetch_ticket_row(self.db, ticket_id)
        if ticket is None:
            return None

        graph_features = features_for_ticket(self.db, ticket_id)
        graph_degree = int(graph_features.get("graph_degree", 0) or 0)
        graph_centrality = float(graph_features.get("graph_centrality", 0.0) or 0.0)
        similar_cases_count = max(count_similar_cases(self.db, ticket), graph_degree)
        decision = compute_live_decision(
            ticket, similar_cases_count, db=self.db, graph_centrality=graph_centrality,
        )

        feature_snapshot_json = dict(decision["feature_snapshot_json"])
        feature_snapshot_json["graph_features"] = graph_features
        feature_snapshot_json["similar_cases_source"] = {
            "legacy_similar_count": count_similar_cases(self.db, ticket),
            "graph_degree": graph_degree,
            "used_similar_cases_count": similar_cases_count,
        }

        explanation_json = dict(decision["explanation_json"])
        explanation_json["graph_reasoning"] = graph_features.get("graph_reasoning", "")

        band_info = band_payload(
            priority_score=decision["priority_score"],
            confidence_score=decision["confidence_score"],
            uncertainty_penalty=decision["uncertainty_penalty"],
            graph_signal_density=graph_features.get("signal_density", 0.0),
        )
        rule_version = "rules-2026-graph-v2"
        decision_version = "v2"
        model_version = "rules-2026-graph-v2"

        category_scores = self._fetch_category_scores(ticket)
        anomaly_zscore = _compute_anomaly_zscore(decision["priority_score"], category_scores)

        decision_hash = compute_decision_hash(
            ticket_id=ticket_id,
            priority_score=decision["priority_score"],
            decision_band=band_info["decision_band"],
            root_cause_hypothesis=decision["root_cause_hypothesis"],
            confidence_score=decision["confidence_score"],
            feature_snapshot_json=feature_snapshot_json,
            explanation_json=explanation_json,
            rule_version=rule_version,
        )

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
                    decision_band,
                    priority_interval_low,
                    priority_interval_high,
                    decision_hash,
                    graph_degree,
                    graph_weighted_degree,
                    anomaly_zscore,
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
                    :decision_version,
                    :rule_version,
                    :model_version,
                    :decision_band,
                    :priority_interval_low,
                    :priority_interval_high,
                    :decision_hash,
                    :graph_degree,
                    :graph_weighted_degree,
                    :anomaly_zscore,
                    CAST(:explanation_json AS JSONB)
                )
                RETURNING id, decision_ts
                """
            ),
            {
                **decision,
                "ticket_pk": ticket["id"],
                "feature_snapshot_json": json.dumps(feature_snapshot_json),
                "explanation_json": json.dumps(explanation_json),
                "decision_version": decision_version,
                "rule_version": rule_version,
                "model_version": model_version,
                "decision_band": band_info["decision_band"],
                "priority_interval_low": band_info["priority_interval_low"],
                "priority_interval_high": band_info["priority_interval_high"],
                "decision_hash": decision_hash,
                "graph_degree": graph_features.get("graph_degree", 0),
                "graph_weighted_degree": graph_features.get("graph_weighted_degree", 0.0),
                "anomaly_zscore": anomaly_zscore,
            },
        ).mappings().first()

        if inserted is None:
            raise RuntimeError("decision_records insert returned no row")
        decision_id = int(inserted["id"])
        decision_ts = inserted["decision_ts"].isoformat()
        self.db.execute(
            text("DELETE FROM recommendations WHERE decision_record_id = :decision_id"),
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
                        status,
                        created_at
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
                        'proposed',
                        NOW()
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
                "payload_json": json.dumps(
                    {
                        "priority_score": decision["priority_score"],
                        "root_cause_hypothesis": decision["root_cause_hypothesis"],
                        "decision_version": decision_version,
                        "rule_version": rule_version,
                        "model_version": model_version,
                        "decision_band": band_info["decision_band"],
                        "decision_hash": decision_hash,
                        "graph_degree": graph_degree,
                        "anomaly_zscore": anomaly_zscore,
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
                    confidence_score_cache = :confidence_score_cache,
                    source_hash = COALESCE(source_hash, :source_hash),
                    updated_at = NOW()
                WHERE id = :ticket_pk
                """
            ),
            {
                "ticket_pk": ticket["id"],
                "clean_summary": decision["clean_summary"],
                "confidence_score_cache": int(round(decision["confidence_score"])),
                "source_hash": ticket.get("source_hash"),
            },
        )

        self.db.commit()

        recommendations = self._load_recommendations(decision_id)

        # Phase 8 email (config gated)
        try:
            from apps.api.services.email_service import EmailService
            es = EmailService()
            if es.is_configured:
                es.send_decision_notification(
                    ticket_id=ticket_id,
                    to="admin@example.local",
                    priority=decision["priority_score"],
                    band=band_info.get("decision_band", ""),
                    root_cause=decision.get("root_cause_hypothesis", ""),
                )
        except Exception:
            pass

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
            "graph_centrality_score": decision.get("graph_centrality_score", 0.0),
            "actionability_score": decision["actionability_score"],
            "uncertainty_penalty": decision["uncertainty_penalty"],
            "root_cause_hypothesis": decision["root_cause_hypothesis"],
            "confidence_score": decision["confidence_score"],
            "decision_ts": decision_ts,
            "decision_version": decision_version,
            "rule_version": rule_version,
            "model_version": model_version,
            "decision_band": band_info["decision_band"],
            "priority_interval_low": band_info["priority_interval_low"],
            "priority_interval_high": band_info["priority_interval_high"],
            "decision_hash": decision_hash,
            "graph_degree": graph_features.get("graph_degree", 0),
            "graph_weighted_degree": graph_features.get("graph_weighted_degree", 0.0),
            "graph_centrality": graph_centrality,
            "anomaly_zscore": anomaly_zscore,
            "graph_signal_density": graph_features.get("signal_density", 0.0),
            "graph_reasoning": graph_features.get("graph_reasoning", ""),
            "band_rationale": band_info["band_rationale"],
            "operator_action": band_info["operator_action"],
            "feature_snapshot_json": feature_snapshot_json,
            "explanation_json": explanation_json,
            "recommendations": recommendations,
        }

        # Phase 8 email (config gated)
        try:
            from apps.api.services.email_service import EmailService
            es = EmailService()
            if es.is_configured:
                es.send_decision_notification(
                    ticket_id=ticket_id,
                    to="admin@example.local",
                    priority=decision["priority_score"],
                    band=band_info.get("decision_band", ""),
                    root_cause=decision.get("root_cause_hypothesis", ""),
                )
        except Exception:
            pass

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
            "graph_centrality_score": decision.get("graph_centrality_score", 0.0),
            "actionability_score": decision["actionability_score"],
            "uncertainty_penalty": decision["uncertainty_penalty"],
            "root_cause_hypothesis": decision["root_cause_hypothesis"],
            "confidence_score": decision["confidence_score"],
            "decision_ts": decision_ts,
            "decision_version": decision_version,
            "rule_version": rule_version,
            "model_version": model_version,
            "decision_band": band_info["decision_band"],
            "priority_interval_low": band_info["priority_interval_low"],
            "priority_interval_high": band_info["priority_interval_high"],
            "decision_hash": decision_hash,
            "graph_degree": graph_features.get("graph_degree", 0),
            "graph_weighted_degree": graph_features.get("graph_weighted_degree", 0.0),
            "graph_centrality": graph_centrality,
            "anomaly_zscore": anomaly_zscore,
            "graph_signal_density": graph_features.get("signal_density", 0.0),
            "graph_reasoning": graph_features.get("graph_reasoning", ""),
            "band_rationale": band_info["band_rationale"],
            "operator_action": band_info["operator_action"],
            "feature_snapshot_json": feature_snapshot_json,
            "explanation_json": explanation_json,
            "recommendations": recommendations,
        }

    def _load_recommendations(self, decision_id: int) -> list[dict[str, Any]]:
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
                    requires_approval,
                    recommended_runbook_id,
                    status,
                    created_at
                FROM recommendations
                WHERE decision_record_id = :decision_id
                ORDER BY rank ASC, id ASC
                """
            ),
            {"decision_id": decision_id},
        ).mappings()
        recommendations = [dict(row) for row in rows]
        for rec in recommendations:
            rec["last_feedback"] = self._load_last_feedback(rec["id"])
            rec["latest_action_run"] = self._load_latest_action_run(rec["id"])
            if rec.get("created_at") is not None:
                rec["created_at"] = _iso(rec["created_at"])
        return recommendations

    def _fetch_category_scores(self, ticket: dict[str, Any]) -> list[float]:
        request_type = ticket.get("request_type") or ticket.get("category_name")
        try:
            if request_type:
                rows = self.db.execute(
                    text(
                        """
                        SELECT dr.priority_score
                        FROM decision_records dr
                        JOIN tickets t ON t.id = dr.ticket_id
                        WHERE COALESCE(t.request_type, '') = :rt
                        ORDER BY dr.decision_ts DESC
                        LIMIT 20
                        """
                    ),
                    {"rt": request_type},
                ).scalars().all()
            else:
                rows = []
            scores = [float(s) for s in rows if s is not None]
            if len(scores) < 5:
                rows = self.db.execute(
                    text(
                        """
                        SELECT priority_score
                        FROM decision_records
                        WHERE priority_score IS NOT NULL
                        ORDER BY decision_ts DESC
                        LIMIT 50
                        """
                    )
                ).scalars().all()
                scores = [float(s) for s in rows if s is not None]
            return scores
        except Exception:
            return []

    def _load_last_feedback(self, recommendation_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT id, feedback_type, feedback_note, feedback_ts, operator_id
                FROM operator_feedback
                WHERE recommendation_id = :rid
                ORDER BY feedback_ts DESC, id DESC
                LIMIT 1
                """
            ),
            {"rid": recommendation_id},
        ).mappings().first()
        if row is None:
            return None
        result = dict(row)
        result["feedback_ts"] = _iso(result.get("feedback_ts"))
        return result

    def _load_latest_action_run(self, recommendation_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT
                    id,
                    recommendation_id,
                    action_type,
                    risk_level,
                    requested_by,
                    approved_by,
                    started_at,
                    finished_at,
                    status,
                    result_json,
                    rollback_available,
                    rollback_metadata_json,
                    operator_note,
                    rollback_payload_json,
                    ticket_event_id
                FROM action_runs
                WHERE recommendation_id = :rid
                ORDER BY started_at DESC, id DESC
                LIMIT 1
                """
            ),
            {"rid": recommendation_id},
        ).mappings().first()
        if row is None:
            return None
        result = dict(row)
        result["started_at"] = _iso(result.get("started_at"))
        result["finished_at"] = _iso(result.get("finished_at"))
        result["rollback_available"] = bool(result.get("rollback_available"))
        return result


def _serialize_decision(row: dict[str, Any]) -> dict[str, Any]:
    payload = dict(row)
    for ts_field in ("decision_ts",):
        if hasattr(payload.get(ts_field), "isoformat"):
            payload[ts_field] = payload[ts_field].isoformat()
    return payload


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return str(value.isoformat())
    return str(value)
