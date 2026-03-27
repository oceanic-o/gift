"""
Utility helpers for the Gift Recommendation System.
"""
import re
import math
from typing import Any


def normalize_text(text: str) -> str:
    """Lowercase, strip, and remove extra whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp a float value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def paginate(items: list[Any], skip: int, limit: int) -> list[Any]:
    """In-memory pagination helper."""
    return items[skip : skip + limit]


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Divide safely, returning default if denominator is zero."""
    if math.isclose(denominator, 0.0):
        return default
    return numerator / denominator
