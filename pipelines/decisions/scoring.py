"""
Priority Scoring: Computes the 7-factor priority score.
Full formula implemented per spec.
"""

from dataclasses import dataclass

from domain.policies import SCORING_WEIGHTS, PriorityRawToSeverity


@dataclass
class PriorityScore:
    severity_score: float
    urgency_score: float
    business_impact_score: float
    sla_risk_score: float
    recurrence_score: float
    dependency_criticality_score: float
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
) -> PriorityScore:
    """
    Calculate the weighted priority score using the 7-factor formula.

    priority_score =
        (0.22 × severity) +
        (0.18 × urgency) +
        (0.20 × business_impact) +
        (0.14 × sla_risk) +
        (0.10 × recurrence) +
        (0.08 × dependency_criticality) +
        (0.08 × actionability) −
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
        actionability_score=actionability,
        uncertainty_penalty=uncertainty,
        priority_score=round(priority, 2),
    )


def severity_from_priority(priority_raw: str) -> float:
    """Map raw priority string to severity score 0-100."""
    return PriorityRawToSeverity.get(priority_raw, 20.0)


def compute_urgency(days_open: int, is_business_hours: bool = True) -> float:
    """Compute urgency from ticket age. Max 100 at ~5+ days."""
    base = min(days_open * 20, 100.0)
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


def compute_recurrence(same_asset_count: int, same_category_count: int) -> float:
    """
    Compute recurrence score from pattern frequency.
    Capped at 100: 5+ occurrences in 90 days = 100.
    """
    total = same_asset_count + same_category_count
    return min(total * 20.0, 100.0)


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
    description_empty: bool, site_missing: bool, similar_cases_count: int
) -> float:
    """
    Uncertainty penalty: higher when we lack signal.
    Max 50: completely ambiguous ticket.
    """
    penalty = 0.0
    if description_empty:
        penalty += 10.0
    if site_missing:
        penalty += 15.0
    if similar_cases_count == 0:
        penalty += 10.0
    elif similar_cases_count < 3:
        penalty += 5.0
    return min(penalty, 50.0)
