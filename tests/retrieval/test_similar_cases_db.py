from pipelines.retrieval.similar_cases import compute_text_similarity


def test_compute_text_similarity_identical_strings() -> None:
    score = compute_text_similarity("VPN drops every morning", "VPN drops every morning")
    assert score == 1.0


def test_compute_text_similarity_no_overlap() -> None:
    score = compute_text_similarity("alpha beta gamma", "delta epsilon zeta")
    assert score == 0.0


def test_compute_text_similarity_partial_overlap() -> None:
    a = "VPN connection drops every morning on the east office"
    b = "VPN connection drops every evening on the west office"
    score = compute_text_similarity(a, b)
    assert 0.0 < score < 1.0


def test_compute_text_similarity_handles_empty_input() -> None:
    assert compute_text_similarity("", "vpn drops") == 0.0
    assert compute_text_similarity("vpn drops", "") == 0.0
    assert compute_text_similarity("", "") == 0.0


def test_compute_text_similarity_handles_missing_words() -> None:
    # The pure helper coerces None to "" via the `or ""` guard
    assert compute_text_similarity("", "vpn drops") == 0.0
    assert compute_text_similarity("vpn drops", "") == 0.0
