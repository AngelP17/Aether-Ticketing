"""
Priority Scoring: Computes the 8-factor priority score.
Full formula implemented per spec.
"""

import math
from dataclasses import dataclass
from typing import Any

from domain.policies import SCORING_WEIGHTS, PriorityRawToSeverity


@dataclass
class PriorityScore:
    severity_score: float
    urgency_score: float
    business_impact_score: float
    sla_risk_score: float
    recurrence_score: float
    dependency_criticality_score: float
    graph_centrality_score: float
    actionability_score: float
    uncertainty_penalty: float
    priority_score: float


def compute_priority_score(
    severity: float,
    urgency: float,
    business_impact: float,
    sla_risk: float,
    recurrence: float,
    dependency_criticality: float,
    actionability: float,
    uncertainty: float,
    graph_centrality: float = 0.0,
) -> PriorityScore:
    """
    Calculate the weighted priority score using the 8-factor formula.

    priority_score =
        (0.20 × severity) +
        (0.16 × urgency) +
        (0.18 × business_impact) +
        (0.12 × sla_risk) +
        (0.10 × recurrence) +
        (0.08 × dependency_criticality) +
        (0.06 × actionability) +
        (0.10 × graph_centrality) −
        (0.10 × uncertainty)
    """
    w = SCORING_WEIGHTS

    priority = (
        w.SEVERITY * severity
        + w.URGENCY * urgency
        + w.BUSINESS_IMPACT * business_impact
        + w.SLA_RISK * sla_risk
        + w.RECURRENCE * recurrence
        + w.DEPENDENCY_CRITICALITY * dependency_criticality
        + w.ACTIONABILITY * actionability
        + w.GRAPH_CENTRALITY * graph_centrality
        - w.UNCERTAINTY_PENALTY * uncertainty
    )

    priority = max(0.0, min(100.0, priority))

    return PriorityScore(
        severity_score=severity,
        urgency_score=urgency,
        business_impact_score=business_impact,
        sla_risk_score=sla_risk,
        recurrence_score=recurrence,
        dependency_criticality_score=dependency_criticality,
        graph_centrality_score=graph_centrality,
        actionability_score=actionability,
        uncertainty_penalty=uncertainty,
        priority_score=round(priority, 2),
    )


def severity_from_priority(priority_raw: str) -> float:
    """Map raw priority string to severity score 0-100."""
    return PriorityRawToSeverity.get(priority_raw, 20.0)


def compute_urgency(days_open: float, is_business_hours: bool = True) -> float:
    """Compute urgency from ticket age using sigmoid curve."""
    base = 100.0 * (1.0 - math.exp(-0.4 * days_open))
    if not is_business_hours:
        base *= 1.15
    return min(base, 100.0)


def compute_sla_risk(
    elapsed_hours: float, sla_target_hours: float, backlog_modifier: float = 1.0
) -> float:
    """Compute SLA risk: how close to breaching the SLA target."""
    if sla_target_hours <= 0:
        return 0.0
    ratio = (elapsed_hours / sla_target_hours) * backlog_modifier
    return min(100.0, ratio * 100.0)


def compute_recurrence(
    same_asset_count: int,
    same_category_count: int,
    *,
    avg_recency_days: float = 0.0,
    half_life_days: float = 21.0,
) -> float:
    """
    Compute time-decayed recurrence score from pattern frequency.

    Uses exponential half-life decay (default ~21 days) so recent similar cases
    contribute full weight while old ones decay. This replaces pure linear count
    with real temporal intelligence: recurrence signal fades for stale patterns.

    Capped at 100. Base 5+ occurrences -> 100 before decay.
    """
    total = same_asset_count + same_category_count
    base = min(total * 20.0, 100.0)
    if avg_recency_days > 0 and half_life_days > 0:
        # exponential decay: e^(-ln(2) * t / T_half)
        decay = math.exp(-math.log(2) * avg_recency_days / half_life_days)
        base *= max(0.20, decay)  # floor at 20% so ancient patterns retain weak signal
    return min(base, 100.0)


def compute_actionability(
    has_description: bool, has_category: bool, similar_cases_count: int
) -> float:
    """
    Actionability: can an operator do something useful immediately?
    """
    score = 30.0
    if has_description:
        score += 25.0
    if has_category:
        score += 20.0
    score += min(similar_cases_count * 5.0, 25.0)
    return min(score, 100.0)


def compute_uncertainty(
    ticket: dict[str, Any], similar_cases_count: int, root_cause_scores: dict[str, float] | None = None
) -> float:
    """
    Entropy-based uncertainty penalty: higher when root cause distribution
    is spread across many classes or when we lack signal.
    Max 50: completely ambiguous ticket.
    """
    entropy_penalty = 0.0
    if root_cause_scores and len(root_cause_scores) > 1:
        total = sum(root_cause_scores.values())
        if total > 0:
            probs = [s / total for s in root_cause_scores.values() if s > 0]
            entropy = -sum(p * math.log2(p) for p in probs)
            max_entropy = math.log2(len(probs))
            entropy_penalty = (entropy / max_entropy) * 30.0

    missing_penalty = 0.0
    if not ticket.get("description"):
        missing_penalty += 10.0
    if not ticket.get("site_id") and not ticket.get("site"):
        missing_penalty += 15.0
    if similar_cases_count < 1:
        missing_penalty += 10.0
    elif similar_cases_count < 3:
        missing_penalty += 5.0

    return min(entropy_penalty + missing_penalty, 50.0)
