"""
Controlled vocabularies (taxonomies) used across the application.

Expose curated lists for the frontend to render dropdowns and multi-selects.
"""
from __future__ import annotations

# Data-aligned shortlist (frontend gets dynamically filtered to existing tags in DB).
HOBBIES: list[str] = [
    "Art",
    "Fitness",
    "Fashion",
    "Travel",
    "Cooking",
    "Music",
    "Photography",
    "Technology",
    "Electronics",
    "Reading",
    "Gaming",
    "Gardening",
    "Hiking",
    "Camping",
    "Cycling",
    "Yoga",
    "Coffee",
    "Wine",
    "Home Decor",
    "DIY",
    "Beauty",
    "Wellness",
    "Food & Drink",
    "Flowers & Garden",
    "Tech & Gadgets",
    "Sports & Outdoors",
    "Music & Audio",
    "Home & Kitchen",
    "Toys & Games",
]

# Age groups with explicit ranges for dropdown display
AGE_GROUPS: list[str] = [
    "Child (0-12)",
    "Teen (13-17)",
    "Young Adult (18-25)",
    "Adult (26-40)",
    "Middle-aged (41-60)",
    "Senior (60+)",
]

# Maps an age group label to the midpoint age (used for backend scoring logic)
AGE_GROUP_MIDPOINTS: dict[str, int] = {
    "Child (0-12)": 6,
    "Teen (13-17)": 15,
    "Young Adult (18-25)": 22,
    "Adult (26-40)": 33,
    "Middle-aged (41-60)": 50,
    "Senior (60+)": 68,
}

# Maps an age group label to the approximate age range tuple (min, max)
AGE_GROUP_RANGES: dict[str, tuple[int, int]] = {
    "Child (0-12)": (0, 12),
    "Teen (13-17)": (13, 17),
    "Young Adult (18-25)": (18, 25),
    "Adult (26-40)": (26, 40),
    "Middle-aged (41-60)": (41, 60),
    "Senior (60+)": (60, 120),
}

GENDERS: list[str] = [
    "Male",
    "Female",
    "Non-binary",
    "Prefer not to say",
]

RELATIONSHIPS: list[str] = [
    "Parent",
    "Child",
    "Sibling",
    "Friend",
    "Colleague",
    "Teacher",
    "Grandparent",
    "Spouse/Partner",
    "Mentor",
]

OCCASIONS: list[str] = [
    "Birthday",
    "Anniversary",
    "Wedding",
    "Graduation",
    "Christmas",
    "Valentine's Day",
    "Mother's Day",
    "Father's Day",
    "Housewarming",
    "New Baby",
    "Retirement",
    "Get Well Soon",
    "Thank You",
    "Just Because",
]

# Budget range labels for the dropdown
BUDGET_RANGES: list[str] = [
    "Under $25",
    "$25–$50",
    "$50–$100",
    "$100–$200",
    "$200–$500",
    "$500+",
]

# Maps budget string label to (min_price, max_price). None means no bound.
BUDGET_TO_PRICE: dict[str, tuple[float | None, float | None]] = {
    "Under $25":  (0.0, 25.0),
    "$25–$50":    (25.0, 50.0),
    "$50–$100":   (50.0, 100.0),
    "$100–$200":  (100.0, 200.0),
    "$200–$500":  (200.0, 500.0),
    "$500+":      (500.0, None),
}

# Age-based relationship constraints.
# Keys are age group labels; values are relationships that are logically
# disabled when the RECIPIENT belongs to that age group.
AGE_RULE_CONSTRAINTS: dict[str, list[str]] = {
    "Child (0-12)": [
        "Spouse/Partner",
        "Colleague",
        "Parent",
        "Grandparent",
        "Teacher",
        "Mentor",
    ],
    "Teen (13-17)": [
        "Spouse/Partner",
        "Parent",
        "Grandparent",
        "Teacher",
    ],
    "Young Adult (18-25)": [
        "Grandparent",
    ],
    "Adult (26-40)": [],
    "Middle-aged (41-60)": [],
    "Senior (60+)": [
        "Child",
    ],
}
def match_age_group(age_val: str | None) -> str | None:
    """
    Map a raw age string (e.g. '35-49', '18-24', '65+') to the corresponding
    canonical taxonomy label from AGE_GROUPS.
    Returns None if no match or invalid format.
    """
    if not age_val:
        return None
    
    val = age_val.lower().strip()
    
    # 1. Direct label match (e.g. 'child')
    for label in AGE_GROUPS:
        clean_label = label.split("(")[0].strip().lower()
        if val == clean_label or val == label.lower():
            return label
            
    # 2. Range match (e.g. '35-49')
    import re
    nums = [int(n) for n in re.findall(r"\d+", val)]
    if not nums:
        return None
    
    mid = sum(nums) / len(nums)
    
    for label, (lo, hi) in AGE_GROUP_RANGES.items():
        if lo <= mid <= hi:
            return label
            
    return None
