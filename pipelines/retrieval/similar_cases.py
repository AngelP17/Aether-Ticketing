"""
Similar Cases: Find prior tickets with similar text for operational memory.
"""

from collections import Counter
from typing import Any


def find_similar_cases(ticket_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """
    Placeholder retrieval hook for external callers.
    The live API uses DB-backed retrieval in apps/api/services/operational_intelligence.py.
    """
    return []


def compute_text_similarity(text_a: str, text_b: str) -> float:
    """Compute text similarity 0.0–1.0 between two text strings."""
    words_a = [word for word in text_a.lower().split() if word]
    words_b = [word for word in text_b.lower().split() if word]
    if not words_a or not words_b:
        return 0.0

    counter_a = Counter(words_a)
    counter_b = Counter(words_b)
    shared = set(counter_a).intersection(counter_b)
    numerator = sum(min(counter_a[word], counter_b[word]) for word in shared)
    denominator = max(sum(counter_a.values()), sum(counter_b.values()))
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
