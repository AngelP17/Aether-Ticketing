"""
Ticket Graph: deterministic, in-memory relationship graph over the recent
ticket corpus.

Edges are constructed from observable ticket facts that already exist in
Postgres: requester, assignee, site, asset, category, root cause, and
co-occurrence within a time window. No external service or trained model
is involved.

This module is pure-Python: it takes already-fetched ticket rows and
returns a graph representation. The expensive SQL lives in
`apps.api.services.graph_intelligence_service`, which is the only place
that touches the database.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from domain.policies import GRAPH_TIME_WINDOW_HOURS, GRAPH_FEATURE_WEIGHTS

EDGE_REQUESTER = "shared_requester"
EDGE_ASSIGNEE = "shared_assignee"
EDGE_SITE = "shared_site"
EDGE_ASSET = "shared_asset"
EDGE_CATEGORY = "shared_category"
EDGE_ROOT_CAUSE = "shared_root_cause"
EDGE_TIME_WINDOW = "within_time_window"

ALL_EDGE_TYPES: tuple[str, ...] = (
    EDGE_REQUESTER,
    EDGE_ASSIGNEE,
    EDGE_SITE,
    EDGE_ASSET,
    EDGE_CATEGORY,
    EDGE_ROOT_CAUSE,
    EDGE_TIME_WINDOW,
)


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    edge_type: str
    weight: float

    def fingerprint(self) -> str:
        raw = f"{self.edge_type}|{min(self.source, self.target)}|{max(self.source, self.target)}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


@dataclass
class TicketGraph:
    """An undirected, weighted ticket relationship graph."""

    nodes: dict[str, dict[str, Any]] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)
    adjacency: dict[str, list[tuple[str, GraphEdge]]] = field(default_factory=lambda: defaultdict(list))
    edge_counts: dict[str, dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))

    def add_node(self, ticket_id: str, attrs: dict[str, Any]) -> None:
        self.nodes[ticket_id] = attrs

    def add_edge(self, source: str, target: str, edge_type: str, weight: float) -> None:
        if source == target:
            return
        if source not in self.nodes or target not in self.nodes:
            return
        edge = GraphEdge(source=source, target=target, edge_type=edge_type, weight=weight)
        self.edges.append(edge)
        self.adjacency[source].append((target, edge))
        self.adjacency[target].append((source, edge))
        self.edge_counts[source][edge_type] += 1
        self.edge_counts[target][edge_type] += 1

    def degree(self, ticket_id: str) -> int:
        return len(self.adjacency.get(ticket_id, ()))

    def weighted_degree(self, ticket_id: str) -> float:
        return sum(edge.weight for _, edge in self.adjacency.get(ticket_id, ()))

    def edges_by_type(self, ticket_id: str) -> dict[str, int]:
        return dict(self.edge_counts.get(ticket_id, {}))

    def neighbors_by_type(self, ticket_id: str, edge_type: str) -> list[str]:
        return [
            neighbor
            for neighbor, edge in self.adjacency.get(ticket_id, ())
            if edge.edge_type == edge_type
        ]

    def compute_pagerank(self, alpha: float = 0.85, iterations: int = 20) -> dict[str, float]:
        """Compute PageRank centrality over the ticket graph.

        Returns scores normalised to 0-100 where the top-ranked node is 100.
        """
        if not self.nodes:
            return {}
        N = len(self.nodes)
        ranks: dict[str, float] = {tid: 1.0 / N for tid in self.nodes}
        for _ in range(iterations):
            new_ranks: dict[str, float] = {}
            for tid in self.nodes:
                incoming = sum(
                    edge.weight * ranks[neighbor] / max(1, len(self.adjacency.get(neighbor, [])))
                    for neighbor, edge in self.adjacency.get(tid, [])
                )
                new_ranks[tid] = (1 - alpha) / N + alpha * incoming
            ranks = new_ranks
        max_rank = max(ranks.values()) or 1.0
        return {tid: round(100.0 * r / max_rank, 2) for tid, r in ranks.items()}


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_ticket_graph(
    tickets: Iterable[dict[str, Any]],
    *,
    time_window_hours: int = GRAPH_TIME_WINDOW_HOURS,
) -> TicketGraph:
    """Build a deterministic graph from a collection of ticket rows.

    Each row must contain at least `ticket_id` and optionally any of
    `requester`, `assignee`, `site_id`, `asset_id`, `category`,
    `root_cause_hypothesis`, `created_at`. Missing values are simply
    skipped — no ticket is excluded for missing optional fields.
    """
    graph = TicketGraph()
    materialized = list(tickets)
    for ticket in materialized:
        ticket_pk = _coerce_str(ticket.get("ticket_id"))
        if ticket_pk is None:
            continue
        graph.add_node(
            ticket_pk,
            {
                "requester": _coerce_str(ticket.get("requester")),
                "assignee": _coerce_str(ticket.get("assignee") or ticket.get("staff_assigned")),
                "site_id": _coerce_str(ticket.get("site_id")),
                "asset_id": ticket.get("asset_id"),
                "category": _coerce_str(ticket.get("category")),
                "root_cause_hypothesis": _coerce_str(ticket.get("root_cause_hypothesis")),
                "created_at": ticket.get("created_at"),
            },
        )

    nodes = list(graph.nodes.items())

    weights = GRAPH_FEATURE_WEIGHTS
    attr_to_edge = (
        ("requester", EDGE_REQUESTER, weights.REQUESTER),
        ("assignee", EDGE_ASSIGNEE, weights.ASSIGNEE),
        ("site_id", EDGE_SITE, weights.SITE),
        ("asset_id", EDGE_ASSET, weights.ASSET),
        ("category", EDGE_CATEGORY, weights.CATEGORY),
        ("root_cause_hypothesis", EDGE_ROOT_CAUSE, weights.ROOT_CAUSE),
    )

    for attr, edge_type, weight in attr_to_edge:
        buckets: dict[Any, list[str]] = defaultdict(list)
        for ticket_id, node in nodes:
            value = node.get(attr)
            if value is None:
                continue
            buckets[value].append(ticket_id)
        for members in buckets.values():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    graph.add_edge(members[i], members[j], edge_type, weight)

    graph = _add_time_window_edges(graph, nodes, time_window_hours=time_window_hours)
    return graph


def _add_time_window_edges(
    graph: TicketGraph,
    nodes: list[tuple[str, dict[str, Any]]],
    *,
    time_window_hours: int,
) -> TicketGraph:
    """Connect tickets that were opened close together in time.

    Time proximity is a weak co-occurrence signal (a site-wide outage
    produces many tickets in a short window) so the weight is small.
    """
    parsed: list[tuple[str, Any]] = []
    for ticket_id, node in nodes:
        opened = node.get("created_at")
        if opened is None:
            continue
        if hasattr(opened, "timestamp"):
            parsed.append((ticket_id, opened.timestamp()))
        else:
            try:
                from datetime import datetime

                parsed.append((ticket_id, datetime.fromisoformat(str(opened).replace("Z", "")).timestamp()))
            except (TypeError, ValueError):
                continue

    parsed.sort(key=lambda item: item[1])
    for i in range(len(parsed)):
        for j in range(i + 1, len(parsed)):
            delta_hours = (parsed[j][1] - parsed[i][1]) / 3600.0
            if delta_hours > time_window_hours:
                break
            weight = GRAPH_FEATURE_WEIGHTS.TIME_WINDOW * max(0.0, 1.0 - delta_hours / max(time_window_hours, 1))
            graph.add_edge(parsed[i][0], parsed[j][0], EDGE_TIME_WINDOW, weight)
    return graph


def compute_graph_features(graph: TicketGraph, ticket_id: str) -> dict[str, Any]:
    """Return deterministic graph-derived features for a single ticket."""
    if ticket_id not in graph.nodes:
        return {
            "ticket_id": ticket_id,
            "graph_degree": 0,
            "graph_weighted_degree": 0.0,
            "edge_counts": {},
            "neighbor_count": 0,
            "is_isolated": True,
            "signal_density": 0.0,
        }
    edges_by_type = graph.edges_by_type(ticket_id)
    weighted = graph.weighted_degree(ticket_id)
    degree = graph.degree(ticket_id)
    signal_density = round(weighted / max(1, len(ALL_EDGE_TYPES)), 4)
    return {
        "ticket_id": ticket_id,
        "graph_degree": degree,
        "graph_weighted_degree": round(weighted, 4),
        "edge_counts": edges_by_type,
        "neighbor_count": degree,
        "is_isolated": degree == 0,
        "signal_density": signal_density,
    }


def build_reasoning(graph: TicketGraph, ticket_id: str) -> dict[str, Any]:
    """Return a human-readable reasoning payload describing the ticket's
    position in the graph (which edges connect it, which neighbors share
    the same site/asset/root cause, etc.)."""
    if ticket_id not in graph.nodes:
        return {"ticket_id": ticket_id, "graph_reasoning": "Ticket is isolated — no graph neighbors."}
    edges_by_type = graph.edges_by_type(ticket_id)
    notes: list[str] = []
    if edges_by_type.get(EDGE_SITE):
        notes.append(f"shares site with {edges_by_type[EDGE_SITE]} other ticket(s)")
    if edges_by_type.get(EDGE_ASSET):
        notes.append(f"shares asset with {edges_by_type[EDGE_ASSET]} other ticket(s)")
    if edges_by_type.get(EDGE_REQUESTER):
        notes.append(f"shares requester with {edges_by_type[EDGE_REQUESTER]} other ticket(s)")
    if edges_by_type.get(EDGE_ASSIGNEE):
        notes.append(f"shares assignee with {edges_by_type[EDGE_ASSIGNEE]} other ticket(s)")
    if edges_by_type.get(EDGE_CATEGORY):
        notes.append(f"shares category with {edges_by_type[EDGE_CATEGORY]} other ticket(s)")
    if edges_by_type.get(EDGE_ROOT_CAUSE):
        notes.append(f"shares root cause with {edges_by_type[EDGE_ROOT_CAUSE]} other ticket(s)")
    if edges_by_type.get(EDGE_TIME_WINDOW):
        notes.append(f"opened within {GRAPH_TIME_WINDOW_HOURS}h of {edges_by_type[EDGE_TIME_WINDOW]} other ticket(s)")
    if not notes:
        notes.append("no graph neighbors")
    return {
        "ticket_id": ticket_id,
        "graph_reasoning": "; ".join(notes),
        "edge_counts": edges_by_type,
        "weighted_degree": graph.weighted_degree(ticket_id),
    }
