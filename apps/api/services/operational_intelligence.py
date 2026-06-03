from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from domain.policies import CLUSTERING_THRESHOLDS, SLATargetHours
from pipelines.retrieval.ticket_graph import (
    EDGE_ASSET,
    EDGE_ROOT_CAUSE,
    EDGE_SITE,
    GraphEdge,
    build_ticket_graph,
)
from pipelines.decisions.recommendation_engine import generate_recommendations
from pipelines.decisions.root_cause_rules import (
    classify_root_cause,
    classify_severity_from_keywords,
)
from pipelines.decisions.scoring import (
    compute_actionability,
    compute_priority_score,
    compute_recurrence,
    compute_sla_risk,
    compute_uncertainty,
    compute_urgency,
    severity_from_priority,
)
from pipelines.ingest.thread_cleaner import (
    clean_text,
    clean_assignee,
    clean_site_id,
    extract_clean_summary,
    normalize_category,
    normalize_priority,
    normalize_status,
)
from apps.api.services.schema_compat import category_join_sql, column_expr


def fetch_ticket_row(db: Session, ticket_id: str) -> dict[str, Any] | None:
    category_select, category_join = category_join_sql(db)
    clean_summary_expr = column_expr(db, "tickets", "clean_summary")
    site_id_expr = column_expr(db, "tickets", "site_id")
    asset_id_expr = column_expr(db, "tickets", "asset_id")
    category_id_expr = column_expr(db, "tickets", "category_id")
    custom_fields_expr = "t.custom_fields"  # force after ensure; column_expr may cache old schema in long-lived
    row = (
        db.execute(
            text(
                f"""
            SELECT
                t.id,
                t.ticket_id,
                t.title,
                t.status,
                t.priority,
                t.request_type,
                t.staff_assigned,
                t.requester,
                t.date_opened,
                t.description,
                t.resolution_notes,
                t.created_at,
                t.updated_at,
                {clean_summary_expr} AS clean_summary,
                {site_id_expr} AS site_id,
                {asset_id_expr} AS asset_id,
                {category_id_expr} AS category_id,
                {custom_fields_expr} AS custom_fields,
                {category_select}
            FROM tickets t
            {category_join}
            WHERE t.ticket_id = :ticket_id
            """
            ),
            {"ticket_id": ticket_id},
        )
        .mappings()
        .first()
    )
    return dict(row) if row else None


def build_live_decision_map(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    """Build live decisions for a list of tickets, now with real graph PageRank centrality
    wired into every score (previously defaulted to 0.0 for list views).
    """
    request_counts = Counter(
        (ticket.get("request_type") or ticket.get("category_name") or "").strip()
        for ticket in tickets
    )
    priority_counts = Counter((ticket.get("priority") or "").strip() for ticket in tickets)

    # Build deterministic graph + PageRank once for the batch so graph_centrality
    # actually affects list scores (command center, board metrics, incidents, etc).
    graph_centralities: dict[str, float] = {}
    if tickets:
        try:
            graph = build_ticket_graph(tickets)
            pageranks = graph.compute_pagerank()
            graph_centralities = {tid: float(pageranks.get(tid, 0.0)) for tid in pageranks}
        except Exception:
            # Fallback to zero centrality on any graph failure (keeps list live)
            graph_centralities = {}

    decision_map: dict[str, Any] = {}
    for ticket in tickets:
        request_type = (ticket.get("request_type") or ticket.get("category_name") or "").strip()
        priority = (ticket.get("priority") or "").strip()
        similar_cases_count = 0
        if request_type:
            similar_cases_count = max(similar_cases_count, request_counts[request_type] - 1)
        if priority:
            similar_cases_count = max(similar_cases_count, priority_counts[priority] - 1)
        centrality = graph_centralities.get(ticket.get("ticket_id", ""), 0.0)
        decision_map[ticket["ticket_id"]] = compute_live_decision(
            ticket,
            max(similar_cases_count, 0),
            include_recommendations=False,
            include_artifacts=False,
            graph_centrality=centrality,
        )
    return decision_map


def count_similar_cases(db: Session, ticket: dict[str, Any]) -> int:
    result = (
        db.execute(
            text(
                """
            SELECT COUNT(*) AS total
            FROM tickets
            WHERE ticket_id != :ticket_id
              AND (
                COALESCE(request_type, '') = COALESCE(:request_type, '')
                OR COALESCE(priority, '') = COALESCE(:priority, '')
              )
            """
            ),
            {
                "ticket_id": ticket["ticket_id"],
                "request_type": ticket.get("request_type"),
                "priority": ticket.get("priority"),
            },
        )
        .mappings()
        .first()
    )
    return int(result["total"]) if result else 0


def fetch_similar_cases(
    db: Session, ticket: dict[str, Any], limit: int = 5
) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                ticket_id,
                title,
                status,
                priority,
                request_type,
                staff_assigned,
                requester,
                date_opened
            FROM tickets
            WHERE ticket_id != :ticket_id
              AND (
                COALESCE(request_type, '') = COALESCE(:request_type, '')
                OR COALESCE(priority, '') = COALESCE(:priority, '')
              )
            ORDER BY date_opened DESC NULLS LAST, id DESC
            LIMIT :limit
            """
        ),
        {
            "ticket_id": ticket["ticket_id"],
            "request_type": ticket.get("request_type"),
            "priority": ticket.get("priority"),
            "limit": limit,
        },
    ).mappings()

    return [
        {
            "ticket_id": row["ticket_id"],
            "title": row["title"],
            "status": row["status"],
            "priority_raw": row["priority"],
            "assignee": row["staff_assigned"],
            "requester": row["requester"],
            "date_opened": _iso_datetime(row["date_opened"]),
        }
        for row in rows
    ]


def build_ticket_snapshot(
    ticket: dict[str, Any],
    decision: dict[str, Any] | None = None,
    incident_id: str | None = None,
) -> dict[str, Any]:
    ticket["title"] = clean_text(ticket.get("title") or "")
    ticket["status"] = normalize_status(ticket.get("status") or "Open")
    ticket["priority"] = normalize_priority(ticket.get("priority") or "Low")
    ticket["staff_assigned"] = clean_assignee(ticket.get("staff_assigned"))
    ticket["site_id"] = clean_site_id(ticket.get("site_id"))
    category = normalize_category(ticket.get("category_name") or ticket.get("request_type"))

    days_open = _days_open(ticket.get("date_opened"), ticket.get("status"))
    return {
        "ticket_id": ticket["ticket_id"],
        "title": ticket.get("title"),
        "status": ticket.get("status"),
        "priority_raw": ticket.get("priority"),
        "priority_score": decision["priority_score"] if decision else None,
        "root_cause_hypothesis": decision["root_cause_hypothesis"] if decision else None,
        "confidence_score": decision["confidence_score"] if decision else None,
        "site": ticket.get("site_id"),
        "assignee": ticket.get("staff_assigned"),
        "category": category,
        "created_at": _iso_datetime(ticket.get("created_at") or ticket.get("date_opened")),
        "days_open": days_open,
        "incident_id": incident_id,
        "description": ticket.get("description"),
        "resolution_notes": ticket.get("resolution_notes"),
        "requester": ticket.get("requester"),
        "custom_fields": ticket.get("custom_fields"),
    }


def compute_live_decision(
    ticket: dict[str, Any],
    similar_cases_count: int,
    *,
    include_recommendations: bool = True,
    include_artifacts: bool = True,
    db: Session | None = None,
    graph_centrality: float = 0.0,
) -> dict[str, Any]:
    title = ticket.get("title") or ""
    description = ticket.get("description") or ""
    request_type = ticket.get("request_type") or ticket.get("category_name") or ""
    priority_raw = ticket.get("priority") or "Low"
    days_open = _days_open(ticket.get("date_opened"), ticket.get("status"))

    base_severity = severity_from_priority(priority_raw)
    severity = min(100.0, base_severity + classify_severity_from_keywords(title, description))
    urgency = compute_urgency(days_open)
    business_impact = _compute_business_impact(ticket, similar_cases_count)
    sla_target = SLATargetHours.get(priority_raw, 24.0)
    sla_risk = compute_sla_risk(days_open * 24.0, sla_target)
    recurrence = compute_recurrence(
        same_asset_count=1 if ticket.get("asset_id") else 0,
        same_category_count=similar_cases_count,
        avg_recency_days=max(0.5, days_open / 1.8),  # proxy: similar cases weighted toward more recent
    )
    dependency_criticality = _dependency_criticality(ticket)
    actionability = compute_actionability(
        has_description=bool(description.strip()),
        has_category=bool(request_type.strip()),
        similar_cases_count=similar_cases_count,
    )
    root_cause, root_confidence, root_cause_scores = classify_root_cause(title, description, request_type)
    uncertainty = compute_uncertainty(
        ticket=ticket,
        similar_cases_count=similar_cases_count,
        root_cause_scores=root_cause_scores,
    )
    score = compute_priority_score(
        severity=severity,
        urgency=urgency,
        business_impact=business_impact,
        sla_risk=sla_risk,
        recurrence=recurrence,
        dependency_criticality=dependency_criticality,
        actionability=actionability,
        uncertainty=uncertainty,
        graph_centrality=graph_centrality,
    )

    confidence = _confidence_score(root_confidence, similar_cases_count, bool(description.strip()), db=db)
    clean_summary = ""
    if include_artifacts:
        clean_summary = ticket.get("clean_summary") or extract_clean_summary(description)

    recommendations: list[dict[str, Any]] = []
    if include_recommendations:
        recommendations = [
            {
                "rank": rec.rank,
                "action_type": getattr(rec.action_type, "value", str(rec.action_type)),
                "action_label": rec.action_label,
                "rationale": rec.rationale,
                "risk_level": getattr(rec.risk_level, "value", str(rec.risk_level)),
                "confidence": round(rec.confidence, 2),
                "expected_benefit": rec.expected_benefit,
                "recommended_runbook_id": rec.recommended_runbook_id,
            }
            for rec in generate_recommendations(
                ticket_id=ticket["ticket_id"],
                root_cause=root_cause,
                priority_score=score.priority_score,
                similar_cases_count=similar_cases_count,
                has_asset=bool(ticket.get("asset_id")),
            )
        ]

    feature_snapshot_json: dict[str, Any] = {}
    explanation_json: dict[str, Any] = {}
    if include_artifacts:
        feature_snapshot_json = {
            "days_open": days_open,
            "similar_cases_count": similar_cases_count,
            "request_type": request_type,
            "site_id": ticket.get("site_id"),
            "clean_summary": clean_summary,
        }
        explanation_json = {
            "severity_base": base_severity,
            "severity_bonus": round(severity - base_severity, 2),
            "request_type": request_type,
            "category_name": ticket.get("category_name"),
        }

    return {
        "ticket_id": ticket["ticket_id"],
        "decision_ts": datetime.now(UTC).isoformat(),
        "severity_score": round(score.severity_score, 2),
        "urgency_score": round(score.urgency_score, 2),
        "business_impact_score": round(score.business_impact_score, 2),
        "sla_risk_score": round(score.sla_risk_score, 2),
        "recurrence_score": round(score.recurrence_score, 2),
        "dependency_criticality_score": round(score.dependency_criticality_score, 2),
        "graph_centrality_score": round(score.graph_centrality_score, 2),
        "actionability_score": round(score.actionability_score, 2),
        "uncertainty_penalty": round(score.uncertainty_penalty, 2),
        "priority_score": round(score.priority_score, 2),
        "root_cause_hypothesis": root_cause.value,
        "confidence_score": round(confidence, 2),
        "feature_snapshot_json": feature_snapshot_json,
        "explanation_json": explanation_json,
        "recommendations": recommendations,
        "clean_summary": clean_summary,
    }


def synthesize_incidents(ticket_snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    graph_incidents = _synthesize_graph_incidents(ticket_snapshots)
    if graph_incidents:
        return graph_incidents

    return _synthesize_grouped_incidents(ticket_snapshots)


def _synthesize_grouped_incidents(ticket_snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    min_link = CLUSTERING_THRESHOLDS.MIN_CONFIDENCE_TO_LINK * 100
    min_create = CLUSTERING_THRESHOLDS.MIN_CONFIDENCE_TO_CREATE * 100

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for snapshot in ticket_snapshots:
        if snapshot["status"] in {"Resolved", "Closed"}:
            continue
        if (snapshot.get("confidence_score") or 0) < min_link:
            continue
        root_cause = snapshot.get("root_cause_hypothesis") or "unknown"
        category = snapshot.get("category") or root_cause
        key = (root_cause, category)
        grouped.setdefault(key, []).append(snapshot)

    incidents: list[dict[str, Any]] = []
    for ((root_cause, category), tickets) in grouped.items():
        if len(tickets) < 2:
            continue
        avg_priority = round(
            sum(ticket.get("priority_score") or 0 for ticket in tickets) / len(tickets), 2
        )
        confidence = round(
            sum(ticket.get("confidence_score") or 0 for ticket in tickets) / len(tickets), 2
        )
        if confidence < min_create:
            continue
        opened_at_values = _text_values(tickets, "created_at")
        opened_at = min(opened_at_values) if opened_at_values else None
        site_scope = _text_values(tickets, "site") or ["global"]
        requesters = _text_values(tickets, "requester")
        assignees = _text_values(tickets, "assignee")
        incidents.append(
            {
                "title": f"{category} cluster",
                "status": "open",
                "root_cause_hypothesis": root_cause,
                "site_scope": ", ".join(site_scope),
                "ticket_count": len(tickets),
                "confidence": confidence,
                "business_impact_score": avg_priority,
                "opened_at": opened_at,
                "tickets": tickets,
                "common_cause": root_cause,
                "recommended_action": f"Coordinate handling for {category.lower()} cases.",
                "graph_evidence": {
                    "shared_site": site_scope[0] if site_scope else "global",
                    "distinct_sites": site_scope,
                    "shared_requester_count": len(requesters),
                    "shared_assignee_count": len(assignees),
                    "primary_requesters": requesters[:3],
                    "primary_assignees": assignees[:3],
                    "evidence_basis": "site + requester + assignee + root_cause cluster",
                },
            }
        )
    return incidents


def _synthesize_graph_incidents(ticket_snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    eligible = [
        snapshot
        for snapshot in ticket_snapshots
        if snapshot["status"] not in {"Resolved", "Closed"}
        and (snapshot.get("confidence_score") or 0) >= CLUSTERING_THRESHOLDS.MIN_CONFIDENCE_TO_LINK * 100
    ]
    if len(eligible) < 2:
        return []

    graph_rows = [_graph_row(snapshot) for snapshot in eligible]
    graph = build_ticket_graph(graph_rows)
    by_ticket_id = {snapshot["ticket_id"]: snapshot for snapshot in eligible}
    adjacency = _strong_graph_adjacency(graph.edges)
    visited: set[str] = set()
    incidents: list[dict[str, Any]] = []

    for ticket_id in sorted(by_ticket_id):
        if ticket_id in visited:
            continue
        component = _component(ticket_id, adjacency, visited)
        if len(component) < 2:
            continue

        tickets = [by_ticket_id[item] for item in sorted(component) if item in by_ticket_id]
        confidence = round(
            sum(ticket.get("confidence_score") or 0 for ticket in tickets) / len(tickets), 2
        )
        if confidence < CLUSTERING_THRESHOLDS.MIN_CONFIDENCE_TO_CREATE * 100:
            continue

        evidence_counts = _component_evidence_counts(graph.edges, component)
        site_scope = _text_values(tickets, "site") or ["global"]
        requesters = _text_values(tickets, "requester")
        assignees = _text_values(tickets, "assignee")
        root_cause = _dominant_value(tickets, "root_cause_hypothesis") or "unknown"
        category = _dominant_value(tickets, "category") or root_cause
        avg_priority = round(
            sum(ticket.get("priority_score") or 0 for ticket in tickets) / len(tickets), 2
        )
        opened_at_values = _text_values(tickets, "created_at")
        opened_at = min(opened_at_values) if opened_at_values else None
        incidents.append(
            {
                "title": _graph_incident_title(category, evidence_counts),
                "status": "open",
                "root_cause_hypothesis": root_cause,
                "site_scope": ", ".join(site_scope),
                "ticket_count": len(tickets),
                "confidence": confidence,
                "business_impact_score": avg_priority,
                "opened_at": opened_at,
                "tickets": tickets,
                "common_cause": root_cause,
                "recommended_action": _graph_recommended_action(evidence_counts),
                "graph_evidence": {
                    "shared_site": site_scope[0] if site_scope else "global",
                    "distinct_sites": site_scope,
                    "shared_requester_count": len(requesters),
                    "shared_assignee_count": len(assignees),
                    "primary_requesters": requesters[:3],
                    "primary_assignees": assignees[:3],
                    "edge_counts": evidence_counts,
                    "evidence_basis": "ticket relationship graph",
                },
            }
        )
    return incidents


def _graph_row(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "ticket_id": snapshot["ticket_id"],
        "requester": snapshot.get("requester"),
        "assignee": snapshot.get("assignee"),
        "site_id": snapshot.get("site"),
        "asset_id": snapshot.get("asset_id"),
        "category": snapshot.get("category"),
        "root_cause_hypothesis": snapshot.get("root_cause_hypothesis"),
        "created_at": snapshot.get("created_at"),
    }


def _strong_graph_adjacency(edges: list[GraphEdge]) -> dict[str, set[str]]:
    strong_edge_types = {
        EDGE_ASSET,
        EDGE_ROOT_CAUSE,
        EDGE_SITE,
    }
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        if edge.edge_type not in strong_edge_types:
            continue
        adjacency.setdefault(edge.source, set()).add(edge.target)
        adjacency.setdefault(edge.target, set()).add(edge.source)
    return adjacency


def _component(
    start: str,
    adjacency: dict[str, set[str]],
    visited: set[str],
) -> set[str]:
    stack = [start]
    component: set[str] = set()
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        component.add(current)
        stack.extend(sorted(adjacency.get(current, set()) - visited))
    return component


def _component_evidence_counts(edges: list[GraphEdge], component: set[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    seen: set[str] = set()
    for edge in edges:
        if edge.source not in component or edge.target not in component:
            continue
        fingerprint = edge.fingerprint()
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        counts[edge.edge_type] = counts.get(edge.edge_type, 0) + 1
    return counts


def _dominant_value(tickets: list[dict[str, Any]], key: str) -> str | None:
    values = [str(ticket.get(key)) for ticket in tickets if ticket.get(key)]
    if not values:
        return None
    return Counter(values).most_common(1)[0][0]


def _text_values(tickets: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(ticket[key]) for ticket in tickets if ticket.get(key)})


def _graph_incident_title(category: str, evidence_counts: dict[str, int]) -> str:
    strongest = sorted(evidence_counts, key=lambda edge_type: evidence_counts[edge_type], reverse=True)
    if strongest:
        return f"{category} cluster by {strongest[0].replace('_', ' ')}"
    return f"{category} cluster"


def _graph_recommended_action(evidence_counts: dict[str, int]) -> str:
    if evidence_counts.get(EDGE_ASSET):
        return "Check the shared asset first before treating tickets independently."
    if evidence_counts.get(EDGE_SITE):
        return "Validate whether this is a site-level issue before dispatching separate work."
    if evidence_counts.get(EDGE_ROOT_CAUSE):
        return "Use the same runbook path for linked tickets unless new evidence appears."
    return "Review linked tickets as one operational incident cluster."


def _days_open(value: Any, status: str | None) -> int:
    if status in {"Resolved", "Closed"}:
        return 0
    if value is None:
        return 0
    if isinstance(value, datetime):
        opened = value.date()
    elif isinstance(value, date):
        opened = value
    else:
        try:
            opened = datetime.fromisoformat(str(value)).date()
        except ValueError:
            return 0
    return max((datetime.utcnow().date() - opened).days, 0)


def _compute_business_impact(ticket: dict[str, Any], similar_cases_count: int) -> float:
    text = " ".join(
        [
            ticket.get("title") or "",
            ticket.get("description") or "",
            ticket.get("request_type") or "",
        ]
    ).lower()
    impact = 30.0 + min(similar_cases_count * 7.0, 25.0)
    if any(keyword in text for keyword in ("erp", "epicor", "server", "network", "vpn")):
        impact += 25.0
    if ticket.get("priority") in {"Critical", "High"}:
        impact += 20.0
    if ticket.get("site_id"):
        impact += 10.0
    return min(impact, 100.0)


def _dependency_criticality(ticket: dict[str, Any]) -> float:
    text = " ".join(
        [
            ticket.get("title") or "",
            ticket.get("description") or "",
            ticket.get("request_type") or "",
        ]
    ).lower()
    if any(keyword in text for keyword in ("erp", "server", "production", "network", "vpn")):
        return 80.0
    if any(keyword in text for keyword in ("email", "printer", "account", "access")):
        return 45.0
    return 25.0


def _confidence_score(
    root_match: float, similar_cases_count: int, has_description: bool,
    db: Session | None = None,
) -> float:
    prior_rate = _feedback_prior_rate(db)
    alpha_prior = 2.0 + prior_rate * 10.0
    beta_prior = 2.0 + (1.0 - prior_rate) * 10.0
    hits = similar_cases_count * max(root_match, 0.1)
    misses = similar_cases_count * (1.0 - max(root_match, 0.1))
    alpha_post = alpha_prior + hits
    beta_post = beta_prior + misses
    expected = alpha_post / (alpha_post + beta_post)
    description_bonus = 0.05 if has_description else 0.0
    return min((expected + description_bonus) * 100.0, 99.0)


def _feedback_prior_rate(db: Session | None) -> float:
    if db is None:
        return 0.5
    try:
        from infrastructure.logging.feedback_learner import FeedbackLearner
        learner = FeedbackLearner(db)
        adjusted = learner.get_adjusted_confidence("unknown", 50.0)
        if adjusted > 0:
            return max(0.1, min(0.95, adjusted / 100.0))
    except Exception:
        pass
    return 0.5


def _iso_datetime(value: Any) -> str:
    if value is None:
        return datetime.now(UTC).isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time()).isoformat()
    return str(value)
