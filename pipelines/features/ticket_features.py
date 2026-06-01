"""
Ticket Features: Derives structured features from raw ticket data.
"""

from dataclasses import dataclass
from typing import Any

from apps.api.services.operational_intelligence import compute_live_decision

@dataclass
class TicketFeatures:
    severity_score: float
    urgency_score: float
    business_impact_score: float
    sla_risk_score: float
    recurrence_score: float
    actionability_score: float
    uncertainty_penalty: float
    clean_summary: str
    root_cause: str


def derive_ticket_features(ticket: dict[str, Any]) -> TicketFeatures:
    """
    Derive all feature signals from a ticket dict.
    """
    decision = compute_live_decision(ticket, ticket.get("similar_cases_count", 0))
    return TicketFeatures(
        severity_score=decision["severity_score"],
        urgency_score=decision["urgency_score"],
        business_impact_score=decision["business_impact_score"],
        sla_risk_score=decision["sla_risk_score"],
        recurrence_score=decision["recurrence_score"],
        actionability_score=decision["actionability_score"],
        uncertainty_penalty=decision["uncertainty_penalty"],
        clean_summary=decision["clean_summary"],
        root_cause=decision["root_cause_hypothesis"],
    )
