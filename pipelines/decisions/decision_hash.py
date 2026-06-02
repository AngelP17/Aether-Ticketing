"""
Decision hash: deterministic SHA-256 fingerprint for a decision.

The hash lets a UI or governance report prove that two decision
records came from the same input + rules, or that a recompute
genuinely changed something meaningful. It is computed from:

- the ticket's external id
- the priority score
- the decision band
- the root cause hypothesis
- the confidence score
- the feature snapshot (as a stable dict)
- the explanation (as a stable dict)
- the rule version

Any meaningful change to those inputs produces a different hash.
The hash is a 64-character lowercase hex string.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def _stable(value: Any) -> str:
    """Serialize a value to a stable, sorted JSON string."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def compute_decision_hash(
    *,
    ticket_id: str,
    priority_score: float,
    decision_band: str,
    root_cause_hypothesis: str,
    confidence_score: float,
    feature_snapshot_json: dict[str, Any] | None,
    explanation_json: dict[str, Any] | None,
    rule_version: str,
) -> str:
    """Return a SHA-256 hex digest that fingerprints a decision."""
    payload = {
        "ticket_id": str(ticket_id),
        "priority_score": round(float(priority_score), 4),
        "decision_band": str(decision_band),
        "root_cause_hypothesis": str(root_cause_hypothesis or ""),
        "confidence_score": round(float(confidence_score), 4),
        "feature_snapshot_json": feature_snapshot_json or {},
        "explanation_json": explanation_json or {},
        "rule_version": str(rule_version),
    }
    encoded = _stable(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def short_decision_hash(full_hash: str) -> str:
    """Return the first 12 characters of a decision hash for compact display."""
    return full_hash[:12]
