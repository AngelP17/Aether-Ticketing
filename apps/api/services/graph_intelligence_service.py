"""
Graph Intelligence Service: fetches recent ticket context from Postgres
and produces deterministic graph features for each ticket.

This is the only module in the graph layer that touches the database.
Everything else in `pipelines.retrieval.ticket_graph` is pure-Python and
unit-testable without a DB.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from pipelines.retrieval.ticket_graph import (
    build_reasoning,
    build_ticket_graph,
    compute_graph_features,
)


DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_MAX_TICKETS = 500


def fetch_recent_ticket_rows(
    db: Session,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_tickets: int = DEFAULT_MAX_TICKETS,
) -> list[dict[str, Any]]:
    """Return a list of recent ticket rows suitable for graph construction."""
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
                date_opened,
                created_at,
                site_id,
                asset_id,
                category_id,
                root_cause_hypothesis,
                is_active
            FROM tickets
            WHERE is_active = TRUE
              AND created_at >= NOW() - (:lookback_days || ' days')::INTERVAL
            ORDER BY created_at DESC
            LIMIT :max_tickets
            """
        ),
        {"lookback_days": lookback_days, "max_tickets": max_tickets},
    ).mappings()
    materialized: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        if item.get("staff_assigned") is not None:
            item["assignee"] = item["staff_assigned"]
        materialized.append(item)
    return materialized


def build_graph_for_recent_tickets(
    db: Session,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_tickets: int = DEFAULT_MAX_TICKETS,
) -> tuple[Any, dict[str, dict[str, Any]]]:
    """Fetch recent tickets, build the graph, and return both plus per-ticket
    features keyed by ticket_id."""
    rows = fetch_recent_ticket_rows(db, lookback_days=lookback_days, max_tickets=max_tickets)
    graph = build_ticket_graph(rows)
    features: dict[str, dict[str, Any]] = {}
    for ticket_id in graph.nodes:
        features[ticket_id] = compute_graph_features(graph, ticket_id)
    return graph, features


def features_for_ticket(
    db: Session,
    ticket_id: str,
    *,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    max_tickets: int = DEFAULT_MAX_TICKETS,
) -> dict[str, Any]:
    """Return graph features + reasoning for a single ticket id.

    Returns an empty-features dict if the ticket is not in the recent
    graph corpus (e.g. very old, inactive, or never seen).
    """
    graph, features = build_graph_for_recent_tickets(
        db, lookback_days=lookback_days, max_tickets=max_tickets
    )
    feature = features.get(ticket_id)
    if feature is None:
        return {
            "ticket_id": ticket_id,
            "graph_degree": 0,
            "graph_weighted_degree": 0.0,
            "edge_counts": {},
            "neighbor_count": 0,
            "is_isolated": True,
            "signal_density": 0.0,
            "graph_reasoning": "Ticket not in recent graph corpus.",
        }
    feature["graph_reasoning"] = build_reasoning(graph, ticket_id)["graph_reasoning"]
    return feature


def summarize_graph(db: Session) -> dict[str, Any]:
    """Return a high-level summary of the current ticket graph."""
    graph, features = build_graph_for_recent_tickets(db)
    if not graph.nodes:
        return {
            "node_count": 0,
            "edge_count": 0,
            "isolated_count": 0,
            "average_degree": 0.0,
            "average_weighted_degree": 0.0,
            "edges_by_type": {},
        }
    total_weighted = sum(feature["graph_weighted_degree"] for feature in features.values())
    isolated = sum(1 for feature in features.values() if feature["is_isolated"])
    edge_counts: dict[str, int] = {}
    for edge in graph.edges:
        edge_counts[edge.edge_type] = edge_counts.get(edge.edge_type, 0) + 1
    return {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "isolated_count": isolated,
        "average_degree": round(sum(feature["graph_degree"] for feature in features.values()) / max(1, len(features)), 4),
        "average_weighted_degree": round(total_weighted / max(1, len(features)), 4),
        "edges_by_type": edge_counts,
    }
