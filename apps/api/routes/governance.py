"""
Governance endpoints: weekly drift summary and decision engine card.

- ``GET /api/governance/summary`` — drift status, current vs prior week,
  root cause spikes, and the engine card.
- ``GET /api/governance/card`` — only the engine card (handy for
  embedding in admin/reports).
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.security import get_current_user
from apps.api.services.graph_intelligence_service import summarize_graph
from pipelines.governance.decision_card import build_decision_card
from pipelines.governance.decision_drift import run_drift_detection


router = APIRouter()


def _rollback_after_handled_error(db: Session) -> None:
    try:
        db.rollback()
    except Exception:
        pass


@router.get("/summary")
def governance_summary(
    db: Session = Depends(get_db),
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    try:
        drift = run_drift_detection(db)
    except Exception as exc:  # noqa: BLE001
        _rollback_after_handled_error(db)
        drift = {"status": "unavailable", "error": str(exc)}

    try:
        graph_summary = summarize_graph(db)
    except Exception as exc:  # noqa: BLE001
        _rollback_after_handled_error(db)
        graph_summary = {"status": "unavailable", "error": str(exc)}

    return {
        "drift": drift,
        "graph": graph_summary,
        "card": build_decision_card(),
    }


@router.get("/card")
def governance_card(
    current_user: dict[str, str] = Depends(get_current_user),
) -> Any:
    return build_decision_card()
