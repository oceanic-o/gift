from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

from app.core.taxonomy import (
    HOBBIES, AGE_GROUPS, RELATIONSHIPS, OCCASIONS,
    GENDERS, BUDGET_RANGES, AGE_RULE_CONSTRAINTS,
)

router = APIRouter(prefix="/taxonomy", tags=["Taxonomy"])

MAX_HOBBY_OPTIONS = 16
MAX_RELATIONSHIP_OPTIONS = 8
RELATIONSHIP_PRIORITY: list[str] = [
    "Parent",
    "Spouse/Partner",
    "Child",
    "Sibling",
    "Friend",
    "Colleague",
    "Teacher",
    "Grandparent",
    "Mentor",
]

_HOBBY_TOKEN_TO_LABEL: dict[str, str] = {
    "art": "Art",
    "fitness": "Fitness",
    "fashion": "Fashion",
    "travel": "Travel",
    "cooking": "Cooking",
    "music": "Music",
    "photography": "Photography",
    "technology": "Technology",
    "electronics": "Electronics",
    "reading": "Reading",
    "gaming": "Gaming",
    "gardening": "Gardening",
    "hiking": "Hiking",
    "camping": "Camping",
    "cycling": "Cycling",
    "yoga": "Yoga",
    "coffee": "Coffee",
    "wine": "Wine",
    "home decor": "Home Decor",
    "diy": "DIY",
    "beauty": "Beauty",
    "wellness": "Wellness",
    "food & drink": "Food & Drink",
    "flowers & garden": "Flowers & Garden",
    "tech & gadgets": "Tech & Gadgets",
    "sports & outdoors": "Sports & Outdoors",
    "music & audio": "Music & Audio",
    "home & kitchen": "Home & Kitchen",
    "toys & games": "Toys & Games",
}

_RELATION_TOKEN_TO_LABEL: dict[str, str] = {
    "parent": "Parent",
    "child": "Child",
    "sibling": "Sibling",
    "friend": "Friend",
    "colleague": "Colleague",
    "teacher": "Teacher",
    "grandparent": "Grandparent",
    "spouse/partner": "Spouse/Partner",
    "spouse": "Spouse/Partner",
    "partner": "Spouse/Partner",
    "mentor": "Mentor",
}


async def _data_backed_hobbies(db: AsyncSession) -> list[str]:
    """
    Return hobbies that actually occur in gifts.tags, filtered to our curated
    shortlist to avoid noisy brand/vendor tokens.
    """
    rows = await db.execute(
        text(
            """
            WITH tok AS (
              SELECT lower(trim(x)) AS token
              FROM gifts, regexp_split_to_table(coalesce(tags, ''), ',') AS x
            )
            SELECT token, COUNT(*) AS c
            FROM tok
            WHERE token <> ''
            GROUP BY token
            ORDER BY c DESC
            """
        )
    )
    label_counts: dict[str, int] = {}
    for token, _count in rows.fetchall():
        label = _HOBBY_TOKEN_TO_LABEL.get(token)
        if not label:
            continue
        label_counts[label] = label_counts.get(label, 0) + int(_count)

    if not label_counts:
        return HOBBIES[:MAX_HOBBY_OPTIONS]

    labels = sorted(label_counts.keys(), key=lambda x: label_counts[x], reverse=True)
    return labels[:MAX_HOBBY_OPTIONS]


async def _data_backed_relationships(db: AsyncSession) -> list[str]:
    """
    Return a compact relationship list backed by actual values in gifts.relationship.
    """
    rows = await db.execute(
        text(
            """
            SELECT trim(relationship) AS relationship, COUNT(*) AS c
            FROM gifts
            WHERE relationship IS NOT NULL AND trim(relationship) <> ''
            GROUP BY trim(relationship)
            ORDER BY c DESC
            """
        )
    )
    counts: dict[str, int] = {}
    for raw_rel, c in rows.fetchall():
        token = str(raw_rel).strip().lower()
        label = _RELATION_TOKEN_TO_LABEL.get(token)
        if not label:
            continue
        counts[label] = counts.get(label, 0) + int(c)
    if not counts:
        return RELATIONSHIPS[:MAX_RELATIONSHIP_OPTIONS]

    ordered = [r for r in RELATIONSHIP_PRIORITY if r in counts]
    if len(ordered) < MAX_RELATIONSHIP_OPTIONS:
        by_freq = sorted(counts.keys(), key=lambda x: counts[x], reverse=True)
        for rel in by_freq:
            if rel not in ordered:
                ordered.append(rel)
            if len(ordered) >= MAX_RELATIONSHIP_OPTIONS:
                break

    return ordered[:MAX_RELATIONSHIP_OPTIONS]


@router.get("/hobbies", response_model=list[str])
async def list_hobbies(db: AsyncSession = Depends(get_db)) -> list[str]:
    """Return data-backed hobbies/interests for dropdowns."""
    return await _data_backed_hobbies(db)


@router.get("/age-groups", response_model=list[str])
async def list_age_groups() -> list[str]:
    """Return age groups with explicit ranges for dropdowns."""
    return AGE_GROUPS


@router.get("/relationships", response_model=list[str])
async def list_relationships(db: AsyncSession = Depends(get_db)) -> list[str]:
    """Return compact, data-backed recipient relationship options."""
    return await _data_backed_relationships(db)


@router.get("/occasions", response_model=list[str])
async def list_occasions() -> list[str]:
    """Return all gift occasions."""
    return OCCASIONS


@router.get("/genders", response_model=list[str])
async def list_genders() -> list[str]:
    """Return gender options for the recipient."""
    return GENDERS


@router.get("/budgets", response_model=list[str])
async def list_budgets() -> list[str]:
    """Return budget range labels for the dropdown."""
    return BUDGET_RANGES


@router.get("/age-rules", response_model=dict[str, list[str]])
async def list_age_rules(db: AsyncSession = Depends(get_db)) -> dict[str, list[str]]:
    """
    Return age-based relationship constraints.
    Maps each age group label to a list of relationships that are logically
    disabled when the RECIPIENT belongs to that age group.
    Frontend uses this to dynamically disable relationship options.
    """
    available = set(await _data_backed_relationships(db))
    return {
        age_group: [rel for rel in disabled if rel in available]
        for age_group, disabled in AGE_RULE_CONSTRAINTS.items()
    }
