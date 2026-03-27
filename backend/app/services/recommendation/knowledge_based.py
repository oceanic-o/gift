"""
Knowledge-based recommendation (rules + keyword overlap).

Scoring weights:
  occasion match:                   0.20
  relationship match:               0.15
  budget fit:                       0.15
  hobby overlap:                    0.40  (↑ from 0.35)
  general keyword:                  0.10
  age group bonus:                 +0.05
  gender bonus:                    +0.05
  occasion+relationship combo:     +0.05  (new)
"""
from __future__ import annotations

import re
from typing import Optional

from app.core.logging import logger
from app.core.taxonomy import AGE_GROUP_RANGES


TOKEN_RE = re.compile(r"[a-zA-Z0-9']+")

_INVALID_VALUES = {"none", "no", "nothing", "n/a", "na", "null", "unknown", "-", "0"}

# Maps age-group label keywords → gift age_group field keywords
_AGE_GROUP_GIFT_KEYWORDS: dict[str, list[str]] = {
    "child": ["kid", "child", "children", "toddler", "baby", "infant", "boy", "girl", "toy", "nursery", "preschool", "kindergarten"],
    "teen": ["teen", "teenager", "youth", "adolescent", "junior", "high school", "trendy", "video game", "gaming", "esports"],
    "young adult": ["young adult", "college", "university", "millennial", "gen z", "dorm", "apartment", "career"],
    "adult": ["adult", "grown", "professional", "office", "home decor", "kitchen", "cooking"],
    "middle-aged": ["adult", "mature", "middle", "professional", "parent", "home ownership"],
    "senior": ["senior", "elderly", "grandparent", "retiree", "retirement", "grandma", "grandpa", "health", "comfort"],
}

# Gender signal keywords for gift matching
_GENDER_KEYWORDS: dict[str, list[str]] = {
    "male":     ["man", "men", "him", "his", "guy", "boy", "masculine", "male", "dad", "father", "brother", "groom", "gentleman"],
    "female":   ["woman", "women", "her", "she", "girl", "feminine", "female", "mom", "mother", "sister", "bride", "lady", "jewelry"],
    "non-binary": ["unisex", "gender-neutral", "everyone"],
}


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in TOKEN_RE.findall(text or "") if len(t) > 1}


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return None
    if cleaned.lower() in _INVALID_VALUES:
        return None
    return cleaned


def _age_exact_to_group_keywords(age_exact: int) -> list[str]:
    """Return the gift age-group keywords that best match the given exact age."""
    for label, (lo, hi) in AGE_GROUP_RANGES.items():
        if lo <= age_exact <= hi:
            key = label.split("(")[0].strip().lower()
            for prefix, kws in _AGE_GROUP_GIFT_KEYWORDS.items():
                if key.startswith(prefix):
                    return kws
    return []


class KnowledgeBasedRecommender:
    def score_gifts(
        self,
        gifts: list[dict],
        top_n: int = 10,
        occasion: Optional[str] = None,
        relationship: Optional[str] = None,
        category_names: Optional[list[str]] = None,
        age_groups: Optional[list[str]] = None,
        tags: Optional[list[str]] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        query_text: Optional[str] = None,
        age: Optional[str] = None,
        gender: Optional[str] = None,
        hobbies: Optional[str] = None,
        age_exact: Optional[int] = None,
    ) -> list[dict]:
        if not gifts:
            return []

        query_text = _clean_text(query_text)
        age = _clean_text(age)
        gender = _clean_text(gender)
        hobbies = _clean_text(hobbies)
        occasion = _clean_text(occasion)
        relationship = _clean_text(relationship)

        input_text = " ".join(
            [
                query_text or "",
                age or "",
                gender or "",
                hobbies or "",
                occasion or "",
                relationship or "",
                " ".join(category_names or []),
                " ".join(age_groups or []),
                " ".join(tags or []),
            ]
        ).strip()
        input_tokens = _tokenize(input_text)
        hobby_tokens = _tokenize(hobbies or "")

        # Precompute age group keywords from age_exact
        age_kws: list[str] = []
        if age_exact is not None:
            age_kws = _age_exact_to_group_keywords(age_exact)
        elif age:
            # Try to derive from age group label string (e.g. "Child (0-12)")
            age_lower = age.lower()
            for prefix, kws in _AGE_GROUP_GIFT_KEYWORDS.items():
                if age_lower.startswith(prefix):
                    age_kws = kws
                    break

        # Precompute gender keywords
        gender_kws: list[str] = []
        if gender:
            gender_kws = _GENDER_KEYWORDS.get(gender.lower(), [])

        scored: list[dict] = []
        for g in gifts:
            score = 0.0
            gift_text = " ".join(
                [
                    g.get("title", ""),
                    g.get("description", "") or "",
                    g.get("category_name", "") or "",
                    g.get("occasion", "") or "",
                    g.get("relationship", "") or "",
                    g.get("tags", "") or "",
                    g.get("age_group", "") or "",
                ]
            )
            gift_tokens = _tokenize(gift_text)

            # Occasion match (exact substring): +0.20
            if occasion and g.get("occasion"):
                if occasion.lower() in g["occasion"].lower():
                    score += 0.20

            # Relationship match: +0.15
            if relationship and g.get("relationship"):
                if relationship.lower() in g["relationship"].lower():
                    score += 0.15

            # Budget fit: +0.15
            price = g.get("price")
            if price is not None:
                budget_ok = True
                if min_price is not None and price < min_price:
                    budget_ok = False
                if max_price is not None and price > max_price:
                    budget_ok = False
                if budget_ok:
                    score += 0.15

            # Hobby overlap: up to +0.40
            if hobby_tokens:
                hobby_overlap = len(hobby_tokens & gift_tokens) / max(len(hobby_tokens), 1)
                score += 0.40 * hobby_overlap

            # General keyword overlap: up to +0.10
            if input_tokens:
                overlap = len(input_tokens & gift_tokens) / max(len(input_tokens), 1)
                score += 0.10 * overlap

            # Age group bonus: +0.05
            if age_kws:
                gift_age_text = (g.get("age_group", "") or "").lower()
                if any(kw in gift_age_text for kw in age_kws):
                    score += 0.05

            # Gender bonus: +0.05
            if gender_kws:
                gift_lower = gift_text.lower()
                if any(kw in gift_lower for kw in gender_kws):
                    score += 0.05

            # Occasion + Relationship combo bonus: +0.05 when BOTH match
            # Rewards highly contextual gifts that match the full gifting scenario
            occ_match = bool(occasion and g.get("occasion") and occasion.lower() in g["occasion"].lower())
            rel_match = bool(relationship and g.get("relationship") and relationship.lower() in g["relationship"].lower())
            if occ_match and rel_match:
                score += 0.05

            if score > 0:
                scored.append({"id": g["id"], "score": min(score, 1.0)})

        if not scored:
            logger.info("knowledge_based.no_matches")
            # fallback: return filtered gifts with small score
            for g in gifts:
                price = g.get("price")
                if min_price is not None and price is not None and price < min_price:
                    continue
                if max_price is not None and price is not None and price > max_price:
                    continue
                if occasion and g.get("occasion") and occasion.lower() not in g["occasion"].lower():
                    continue
                if relationship and g.get("relationship") and relationship.lower() not in g["relationship"].lower():
                    continue
                scored.append({"id": g["id"], "score": 0.1})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]
