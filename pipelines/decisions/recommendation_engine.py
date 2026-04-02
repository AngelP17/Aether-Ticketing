"""
Recommendation Engine: Generates ranked action recommendations per ticket.
Returns 3-5 recommendations with confidence and rationale.
"""

from dataclasses import dataclass
from typing import Optional

from domain.enums import RootCauseClass, RiskLevel, ActionType
from pipelines.decisions.root_cause_rules import suggest_runbook


@dataclass
class Recommendation:
    rank: int
    action_type: str
    action_label: str
    rationale: str
    risk_level: str
    confidence: float
    expected_benefit: str
    recommended_runbook_id: Optional[str] = None


def generate_recommendations(
    ticket_id: str,
    root_cause: RootCauseClass,
    priority_score: float,
    similar_cases_count: int,
    has_asset: bool,
) -> list[Recommendation]:
    """
    Generate 3–5 ranked recommendations for a ticket.
    """
    recommendations = []

    runbook_id = suggest_runbook(root_cause)

    if runbook_id:
        recommendations.append(
            Recommendation(
                rank=1,
                action_type=ActionType.APPLY_RUNBOOK,
                action_label=_runbook_label(root_cause),
                rationale=f"Root cause matches known pattern with {similar_cases_count} prior resolved cases",
                risk_level=RiskLevel.LOW,
                confidence=0.80 if similar_cases_count > 5 else 0.65,
                expected_benefit=f"Resolve within {(4 if priority_score > 70 else 8)} hours",
                recommended_runbook_id=runbook_id,
            )
        )

    recommendations.append(
        Recommendation(
            rank=2,
            action_type=ActionType.ASSIGN_TEAM,
            action_label=f"Route to {root_cause.value.replace('_', ' ').title()} specialist queue",
            rationale="Category-based routing for targeted ownership",
            risk_level=RiskLevel.LOW,
            confidence=0.75,
            expected_benefit="Reduce reassignment and queue delay",
        )
    )

    if similar_cases_count == 0:
        recommendations.append(
            Recommendation(
                rank=3,
                action_type=ActionType.REQUEST_INFO,
                action_label="Request diagnostic details: error messages, screenshots, timeline",
                rationale="Low actionability — more information needed to resolve",
                risk_level=RiskLevel.NONE,
                confidence=0.70,
                expected_benefit="Increase actionability to enable resolution",
            )
        )

    if priority_score > 75 and not has_asset:
        recommendations.append(
            Recommendation(
                rank=4 if len(recommendations) == 3 else len(recommendations) + 1,
                action_type=ActionType.REQUEST_INFO,
                action_label="Request affected asset/system identifier",
                rationale="High-priority ticket without asset linkage — need to identify scope",
                risk_level=RiskLevel.NONE,
                confidence=0.80,
                expected_benefit="Enable incident clustering and business impact analysis",
            )
        )

    if len(recommendations) < 3:
        recommendations.append(
            Recommendation(
                rank=len(recommendations) + 1,
                action_type=ActionType.AUTO_RESOLVE,
                action_label="Mark as resolved with known solution pattern",
                rationale=f"Strong prior resolution signal ({similar_cases_count} similar cases)",
                risk_level=RiskLevel.MEDIUM,
                confidence=0.60,
                expected_benefit="Close ticket without manual intervention",
            )
        )

    recommendations.sort(key=lambda r: r.confidence, reverse=True)
    for i, rec in enumerate(recommendations, 1):
        rec.rank = i

    return recommendations[:5]


def _runbook_label(root_cause: RootCauseClass) -> str:
    labels = {
        RootCauseClass.SHARED_MAILBOX_FORWARDING: "Apply shared mailbox forwarding migration runbook",
        RootCauseClass.EMAIL_MESSAGING: "Apply Outlook/mailbox troubleshooting runbook",
        RootCauseClass.FILE_SHARE_PERMISSIONS: "Reset NTFS permissions and remap drive",
        RootCauseClass.ACCESS_IDENTITY: "Execute identity unlock and credential reset procedure",
        RootCauseClass.PRINTER_SCANNER: "Reinstall printer driver and clear print queue",
        RootCauseClass.NETWORK_CONNECTIVITY: "Restart VPN client and verify network connectivity",
        RootCauseClass.ERP_APPLICATION: "Restart ERP application and verify services",
        RootCauseClass.INFRASTRUCTURE_SERVICE: "Run server health check and restart affected services",
        RootCauseClass.SECURITY_SPAM_BLOCK: "Review and release spam-quarantined items",
    }
    return labels.get(root_cause, "Apply category-specific runbook")
