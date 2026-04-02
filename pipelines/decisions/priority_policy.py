"""
Priority Policy: Constants and normalization helpers for scoring.
"""

from domain.policies import PriorityRawToSeverity, SLATargetHours


def normalize_score(value: float, min_val: float = 0.0, max_val: float = 100.0) -> float:
    """Clamp and normalize a score to 0–100."""
    if max_val <= min_val:
        return 0.0
    normalized = (value - min_val) / (max_val - min_val)
    return max(0.0, min(100.0, normalized * 100.0))


def get_sla_target_hours(priority: str) -> float:
    """Return SLA target in hours for a given priority level."""
    return SLATargetHours.get(priority, 24.0)


def get_base_severity(priority_raw: str) -> float:
    """Return base severity from raw priority field."""
    return PriorityRawToSeverity.get(priority_raw, 20.0)
