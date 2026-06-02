from __future__ import annotations

from pipelines.governance.decision_card import build_decision_card


def test_decision_card_includes_required_sections() -> None:
    card = build_decision_card()
    assert card["title"] == "Aether Decision Engine Card"
    assert card["engine"]["kind"] == "deterministic graph + rules"
    assert card["engine"]["trained_ml_model"] is False
    assert card["engine"]["external_llm"] is False
    assert card["engine"]["decision_schema_version"] == "v2"
    assert isinstance(card["what_this_engine_is"], list) and len(card["what_this_engine_is"]) >= 1
    assert isinstance(card["what_this_engine_is_not"], list) and len(card["what_this_engine_is_not"]) >= 1
    assert "scoring_weights" in card
    assert "graph_weights" in card
    assert "uncertainty_bands" in card
    assert "guardrails" in card
    assert "ownership" in card
    assert card["ownership"]["team"] == "Aether OpsCenter"


def test_decision_card_uses_live_policy_versions() -> None:
    card = build_decision_card()
    assert card["engine"]["version"]
    assert card["uncertainty_bands"]["labels"] == [
        "high_confidence_action",
        "review_needed",
        "standard_queue",
    ]
    assert "shared_requester" in card["graph_weights"]
    assert "severity" in card["scoring_weights"]
