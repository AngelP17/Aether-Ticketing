from apps.api.services.accuracy_service import _pearson_correlation


def test_pearson_perfect_correlation() -> None:
    result = _pearson_correlation([1.0, 2.0, 3.0], [1.0, 2.0, 3.0])
    assert result is not None
    assert abs(result - 1.0) < 0.001


def test_pearson_negative_correlation() -> None:
    result = _pearson_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert result is not None
    assert abs(result - (-1.0)) < 0.001


def test_pearson_no_correlation() -> None:
    result = _pearson_correlation([1.0, 2.0, 3.0], [10.0, 20.0, 10.0])
    assert result is not None
    assert abs(result) < 1.0


def test_pearson_too_few_points() -> None:
    assert _pearson_correlation([1.0, 2.0], [1.0, 2.0]) is None
    assert _pearson_correlation([1.0], [1.0]) is None


def test_pearson_zero_variance() -> None:
    assert _pearson_correlation([5.0, 5.0, 5.0], [1.0, 2.0, 3.0]) is None


def test_pearson_mismatched_lengths() -> None:
    assert _pearson_correlation([1.0, 2.0, 3.0], [1.0, 2.0]) is None
