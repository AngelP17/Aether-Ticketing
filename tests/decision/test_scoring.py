from pipelines.decisions.root_cause_rules import classify_root_cause
from pipelines.decisions.scoring import compute_priority_score


def test_priority_score_stays_within_bounds() -> None:
    result = compute_priority_score(95, 90, 85, 80, 60, 70, 75, 5, graph_centrality=50)
    assert 0 <= result.priority_score <= 100
    assert result.priority_score > 70


def test_root_cause_classification_finds_email_pattern() -> None:
    root_cause, confidence, scores = classify_root_cause(
        "Shared mailbox forwarding broken",
        "Outlook shared mailbox delegate access is not working",
        "Email Issues",
    )
    assert root_cause.value in {"shared_mailbox_forwarding", "email_messaging"}
    assert confidence > 0
    assert isinstance(scores, dict)
