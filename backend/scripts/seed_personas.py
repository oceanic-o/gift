#!/usr/bin/env python3
"""
seed_personas.py — Seed 8 user persona groups with realistic interaction data.

Each persona group maps to ~25 users and seeds weighted interactions
(clicks, ratings, purchases) that match the persona's profile.

Usage:
  python scripts/seed_personas.py --all
  python scripts/seed_personas.py --profiles-only
  python scripts/seed_personas.py --interactions-only
"""

import asyncio
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://giftuser:giftpassword@localhost:5432/giftdb",
)
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ─── Persona definitions ─────────────────────────────────────────────────────
PERSONAS = [
    {
        "name": "Young Gamer",
        "age": "Young Adult (18-25)",
        "gender": "Male",
        "hobbies": "Video Games, Gadgets, Esports",
        "interests": ["Video Games", "Gadgets", "Esports"],
        "relationship": "Partner",
        "occasion": "Birthday",
        "budget_min": 50.0,
        "budget_max": 100.0,
        "keyword_matches": ["gaming", "game", "controller", "headset", "tech", "electronic", "gadget"],
        "category_matches": ["Electronics", "Gaming", "Tech"],
    },
    {
        "name": "Fitness Mum",
        "age": "Adult (26-40)",
        "gender": "Female",
        "hobbies": "Gym, Yoga, Running",
        "interests": ["Gym", "Yoga", "Running"],
        "relationship": "Mother",
        "occasion": "Mother's Day",
        "budget_min": 25.0,
        "budget_max": 80.0,
        "keyword_matches": ["fitness", "yoga", "gym", "workout", "sport", "health", "wellness", "activewear"],
        "category_matches": ["Sports", "Fitness", "Health", "Wellness"],
    },
    {
        "name": "Retired Grandparent",
        "age": "Senior (60+)",
        "gender": "Female",
        "hobbies": "Gardening, Reading, Cooking",
        "interests": ["Gardening", "Reading", "Cooking"],
        "relationship": "Grandmother",
        "occasion": "Birthday",
        "budget_min": 30.0,
        "budget_max": 100.0,
        "keyword_matches": ["garden", "plant", "book", "reading", "cook", "kitchen", "home", "comfort"],
        "category_matches": ["Books", "Home", "Garden", "Kitchen"],
    },
    {
        "name": "Teen Creator",
        "age": "Teen (13-17)",
        "gender": "Female",
        "hobbies": "Photography, Vlogging, DIY Crafts",
        "interests": ["Photography", "Vlogging", "DIY Crafts"],
        "relationship": "Daughter",
        "occasion": "Birthday",
        "budget_min": 10.0,
        "budget_max": 50.0,
        "keyword_matches": ["camera", "photo", "creative", "art", "craft", "diy", "stationery", "journal"],
        "category_matches": ["Photography", "Arts", "Crafts", "Stationery"],
    },
    {
        "name": "Professional Chef",
        "age": "Young Adult (18-25)",
        "gender": "Male",
        "hobbies": "Cooking, Baking, Coffee",
        "interests": ["Cooking", "Baking", "Coffee"],
        "relationship": "Friend",
        "occasion": "Birthday",
        "budget_min": 30.0,
        "budget_max": 120.0,
        "keyword_matches": ["cook", "bake", "kitchen", "coffee", "chef", "culinary", "spice", "recipe", "utensil"],
        "category_matches": ["Kitchen", "Cooking", "Food", "Coffee"],
    },
    {
        "name": "Creative Kid",
        "age": "Child (0-12)",
        "gender": "Male",
        "hobbies": "Painting, Board Games, DIY Crafts",
        "interests": ["Painting", "Board Games", "DIY Crafts"],
        "relationship": "Son",
        "occasion": "Birthday",
        "budget_min": 10.0,
        "budget_max": 40.0,
        "keyword_matches": ["kids", "toy", "game", "play", "educational", "art", "craft", "fun", "child"],
        "category_matches": ["Toys", "Games", "Educational", "Kids"],
    },
    {
        "name": "Music Lover",
        "age": "Adult (26-40)",
        "gender": "Male",
        "hobbies": "Guitar, Vinyl Records, Music Production",
        "interests": ["Guitar", "Vinyl Records", "Music Production"],
        "relationship": "Partner",
        "occasion": "Anniversary",
        "budget_min": 80.0,
        "budget_max": 200.0,
        "keyword_matches": ["music", "guitar", "vinyl", "audio", "speaker", "headphone", "instrument", "record"],
        "category_matches": ["Music", "Audio", "Entertainment"],
    },
    {
        "name": "Tech Entrepreneur",
        "age": "Adult (26-40)",
        "gender": "Male",
        "hobbies": "Gadgets, Programming, Robotics",
        "interests": ["Gadgets", "Programming", "Robotics"],
        "relationship": "Colleague",
        "occasion": "Birthday",
        "budget_min": 80.0,
        "budget_max": 250.0,
        "keyword_matches": ["tech", "gadget", "smart", "wireless", "bluetooth", "electronic", "device", "innovation"],
        "category_matches": ["Electronics", "Tech", "Gadgets"],
    },
]


def _gift_relevance_score(gift, persona: dict) -> float:
    """Score how well a gift matches a persona for weighted sampling."""
    score = 1.0
    text = " ".join([
        (gift.title or "").lower(),
        (gift.description or "").lower(),
        (gift.tags or "").lower(),
        (gift.category.name if gift.category else "").lower(),
        (gift.occasion or "").lower(),
        (gift.relationship or "").lower(),
    ])

    # Keyword match bonus
    for kw in persona["keyword_matches"]:
        if kw in text:
            score += 4.0
            break

    # Category match bonus
    cat = (gift.category.name if gift.category else "").lower()
    for c in persona["category_matches"]:
        if c.lower() in cat:
            score += 3.0
            break

    # Occasion match
    if persona["occasion"] and gift.occasion and persona["occasion"].lower() in (gift.occasion or "").lower():
        score += 2.0

    # Relationship match
    if persona["relationship"] and gift.relationship and persona["relationship"].lower() in (gift.relationship or "").lower():
        score += 1.5

    # Budget fit
    price = float(gift.price or 0)
    if persona["budget_min"] <= price <= persona["budget_max"]:
        score += 2.0
    elif price > persona["budget_max"] * 1.5:
        score -= 1.0

    return max(score, 0.1)


async def seed_all_profiles_and_interactions(
    session: AsyncSession,
    interactions_per_user: int = 60,
) -> dict:
    from app.repositories.user_repository import UserRepository
    from app.repositories.user_profile_repository import UserProfileRepository
    from app.repositories.gift_repository import GiftRepository
    from app.models.models import Interaction, InteractionType

    user_repo = UserRepository(session)
    profile_repo = UserProfileRepository(session)
    gift_repo = GiftRepository(session)

    users = await user_repo.get_all()
    gifts = await gift_repo.get_all_gifts()
    if not users or not gifts:
        print("[!] No users or gifts found. Load data first.")
        return {"profiles": 0, "interactions": 0}

    print(f"[·] Found {len(users)} users and {len(gifts)} gifts")

    # Pre-score gifts for each persona
    persona_gift_scores: list[list[tuple[float, any]]] = []
    for p in PERSONAS:
        scored = [(max(_gift_relevance_score(g, p), 0.01), g) for g in gifts]
        scored.sort(key=lambda x: x[0], reverse=True)
        persona_gift_scores.append(scored)

    profiles_updated = 0
    total_interactions = 0

    for i, user in enumerate(users):
        persona_idx = i % len(PERSONAS)
        persona = PERSONAS[persona_idx]
        scored_gifts = persona_gift_scores[persona_idx]

        # Assign profile
        profile = await profile_repo.get_by_user_id(user.id)
        payload = dict(
            age=persona["age"],
            gender=persona["gender"],
            hobbies=persona["hobbies"],
            interests=persona["interests"],
            relationship=persona["relationship"],
            occasion=persona["occasion"],
            budget_min=persona["budget_min"],
            budget_max=persona["budget_max"],
            favorite_categories=persona["category_matches"],
            occasions=[persona["occasion"]],
            gifting_for_ages=[persona["age"]],
        )
        if profile is None:
            await profile_repo.create(profile_repo.model(user_id=user.id, **payload))
        else:
            for k, v in payload.items():
                setattr(profile, k, v)
        profiles_updated += 1

        # Weighted gift pool: top 60% by persona relevance + some random noise
        pool_size = min(max(interactions_per_user * 3, 150), len(scored_gifts))
        top_pool = scored_gifts[:pool_size]
        weights = [s for s, _ in top_pool]
        pool_gifts = [g for _, g in top_pool]

        # Normalize weights for random.choices
        total_w = sum(weights)
        probs = [w / total_w for w in weights]

        # Sample unique gifts for interaction
        n_interactions = min(interactions_per_user, len(pool_gifts))
        picks = random.choices(pool_gifts, weights=probs, k=n_interactions * 3)
        seen_ids: set[int] = set()
        unique_picks = []
        for g in picks:
            if g.id not in seen_ids:
                seen_ids.add(g.id)
                unique_picks.append(g)
            if len(unique_picks) >= n_interactions:
                break

        for rank, gift in enumerate(unique_picks):
            relevance = weights[pool_gifts.index(gift)] / (weights[0] + 1e-9) if gift in pool_gifts else 0.5

            # Click (almost always)
            session.add(Interaction(
                user_id=user.id,
                gift_id=gift.id,
                interaction_type=InteractionType.click,
                rating=None,
            ))
            total_interactions += 1

            # Rating: more likely for higher-relevance gifts
            if random.random() < (0.4 + 0.4 * relevance):
                # Relevant gifts get higher ratings
                if relevance > 0.5:
                    rating = random.choices([3.0, 4.0, 5.0], weights=[1, 3, 6])[0]
                else:
                    rating = random.choices([2.0, 3.0, 4.0], weights=[2, 3, 2])[0]
                session.add(Interaction(
                    user_id=user.id,
                    gift_id=gift.id,
                    interaction_type=InteractionType.rating,
                    rating=rating,
                ))
                total_interactions += 1

            # Purchase: only for top-ranked, highly relevant gifts
            if rank < 10 and relevance > 0.6 and random.random() < 0.25:
                session.add(Interaction(
                    user_id=user.id,
                    gift_id=gift.id,
                    interaction_type=InteractionType.purchase,
                    rating=None,
                ))
                total_interactions += 1

        if (i + 1) % 25 == 0:
            await session.flush()
            print(f"[·] Processed {i + 1}/{len(users)} users...")

    await session.commit()
    return {"profiles": profiles_updated, "interactions": total_interactions}


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Seed persona-based user profiles and interactions")
    parser.add_argument("--all", action="store_true", help="Seed profiles AND interactions (default)")
    parser.add_argument("--profiles-only", action="store_true", help="Only update user profiles")
    parser.add_argument("--interactions-only", action="store_true", help="Only seed interactions")
    parser.add_argument("--n", type=int, default=60, help="Interactions per user (default: 60)")
    args = parser.parse_args()

    do_all = args.all or not (args.profiles_only or args.interactions_only)

    async with SessionLocal() as session:
        if do_all or (args.profiles_only and args.interactions_only):
            result = await seed_all_profiles_and_interactions(session, interactions_per_user=args.n)
            print(f"[OK] Profiles updated: {result['profiles']}")
            print(f"[OK] Interactions created: {result['interactions']}")
        elif args.profiles_only:
            result = await seed_all_profiles_and_interactions(session, interactions_per_user=0)
            print(f"[OK] Profiles updated: {result['profiles']}")
        elif args.interactions_only:
            result = await seed_all_profiles_and_interactions(session, interactions_per_user=args.n)
            print(f"[OK] Interactions created: {result['interactions']}")


if __name__ == "__main__":
    asyncio.run(main())
