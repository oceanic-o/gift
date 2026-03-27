"""
Unit tests for app/utils/helpers.py (currently 0% coverage).
"""
import pytest
from app.utils.helpers import normalize_text, clamp, paginate, safe_divide


# ---------------------------------------------------------------------------
# normalize_text
# ---------------------------------------------------------------------------

def test_normalize_text_lowercase():
    assert normalize_text("Hello World") == "hello world"


def test_normalize_text_strips_whitespace():
    assert normalize_text("  hello  ") == "hello"


def test_normalize_text_collapses_spaces():
    assert normalize_text("too   many   spaces") == "too many spaces"


def test_normalize_text_combined():
    assert normalize_text("  GIFT   Idea  ") == "gift idea"


def test_normalize_text_already_clean():
    assert normalize_text("clean text") == "clean text"


def test_normalize_text_empty():
    assert normalize_text("") == ""


# ---------------------------------------------------------------------------
# clamp
# ---------------------------------------------------------------------------

def test_clamp_within_range():
    assert clamp(0.5) == 0.5


def test_clamp_at_min():
    assert clamp(0.0) == 0.0


def test_clamp_at_max():
    assert clamp(1.0) == 1.0


def test_clamp_below_min():
    assert clamp(-0.5) == 0.0


def test_clamp_above_max():
    assert clamp(1.5) == 1.0


def test_clamp_custom_range():
    assert clamp(5, min_val=1, max_val=10) == 5


def test_clamp_custom_range_below():
    assert clamp(0, min_val=1, max_val=10) == 1


def test_clamp_custom_range_above():
    assert clamp(11, min_val=1, max_val=10) == 10


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------

def test_paginate_basic():
    items = list(range(10))
    assert paginate(items, skip=0, limit=3) == [0, 1, 2]


def test_paginate_with_skip():
    items = list(range(10))
    assert paginate(items, skip=5, limit=3) == [5, 6, 7]


def test_paginate_skip_beyond_end():
    items = list(range(5))
    assert paginate(items, skip=10, limit=3) == []


def test_paginate_limit_exceeds_remaining():
    items = list(range(5))
    assert paginate(items, skip=3, limit=10) == [3, 4]


def test_paginate_empty_list():
    assert paginate([], skip=0, limit=5) == []


def test_paginate_zero_limit():
    items = list(range(10))
    assert paginate(items, skip=0, limit=0) == []


# ---------------------------------------------------------------------------
# safe_divide
# ---------------------------------------------------------------------------

def test_safe_divide_normal():
    assert safe_divide(10.0, 2.0) == 5.0


def test_safe_divide_by_zero_returns_default():
    assert safe_divide(10.0, 0.0) == 0.0


def test_safe_divide_by_zero_custom_default():
    assert safe_divide(10.0, 0.0, default=-1.0) == -1.0


def test_safe_divide_fractional():
    assert safe_divide(1.0, 3.0) == pytest.approx(1 / 3, rel=1e-6)


def test_safe_divide_near_zero_denominator():
    # math.isclose uses relative tolerance; only exact 0.0 triggers the guard
    # so test with denominator = 0.0 explicitly (already covered above)
    # Tiny but non-zero denominator should divide normally
    result = safe_divide(1.0, 1e-10)
    assert result > 0


def test_safe_divide_zero_numerator():
    assert safe_divide(0.0, 5.0) == 0.0
