#!/usr/bin/env python3
"""
Seed demo user profiles and interactions to improve collaborative filtering.

Usage examples:
  python scripts/seed_demo.py --profiles --interactions 50
  python scripts/seed_demo.py --profiles
  python scripts/seed_demo.py --interactions 100

Requirements:
  - Postgres running (docker compose up -d in backend/)
  - DATABASE_URL set (defaults provided)
"""
import asyncio
import os
import random
from pathlib import Path
import sys

# Add project root to path
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


async def seed_profiles(session: AsyncSession) -> int:
    from app.core.taxonomy import HOBBIES, AGE_GROUPS, RELATIONSHIPS, OCCASIONS
    from app.repositories.user_repository import UserRepository
    from app.repositories.user_profile_repository import UserProfileRepository

    user_repo = UserRepository(session)
    profile_repo = UserProfileRepository(session)

    users = await user_repo.get_all()
    updated = 0

    # Sample categories distribution
    from app.repositories.gift_repository import CategoryRepository
    cat_repo = CategoryRepository(session)
    cats = await cat_repo.get_all()
    cat_names = [c.name for c in cats] or ["General"]

    genders = ["Male", "Female", "Non-binary", "Prefer not to say"]

    for u in users:
        # Pick 2-3 hobbies/interests
        interests = random.sample(HOBBIES, k=min(3, max(1, len(HOBBIES)//20)))
        # Favorites
        fav_cats = random.sample(cat_names, k=min(2, len(cat_names)))

        profile = await profile_repo.get_by_user_id(u.id)
        payload = dict(
            age=random.choice(AGE_GROUPS),
            gender=random.choice(genders),
            hobbies=", ".join(interests),
            relationship=random.choice(RELATIONSHIPS),
            occasion=random.choice(OCCASIONS),
            budget_min=float(random.choice([20, 30, 40, 50])),
            budget_max=float(random.choice([80, 120, 150, 200, 250, 300])),
            favorite_categories=fav_cats,
            occasions=[random.choice(OCCASIONS)],
            gifting_for_ages=[random.choice(AGE_GROUPS)],
            interests=interests,
        )
        if profile is None:
            await profile_repo.create(profile_repo.model(user_id=u.id, **payload))
        else:
            for k, v in payload.items():
                setattr(profile, k, v)
        updated += 1
    await session.commit()
    return updated


async def seed_interactions(session: AsyncSession, per_user: int = 60) -> int:
    from app.models.models import Interaction, InteractionType
    from app.repositories.user_repository import UserRepository
    from app.repositories.gift_repository import GiftRepository
    from app.repositories.user_profile_repository import UserProfileRepository

    user_repo = UserRepository(session)
    profile_repo = UserProfileRepository(session)
    gift_repo = GiftRepository(session)

    users = await user_repo.get_all()
    gifts = await gift_repo.get_all_gifts()
    if not gifts or not users:
        return 0

    total = 0
    for u in users:
        profile = await profile_repo.get_by_user_id(u.id)
        interests = set((profile.interests or [])) if profile else set()
        occ = (profile.occasion or "").lower() if profile else None
        rel = (profile.relationship or "").lower() if profile else None

        # Weighted gift sampling by tag/category/occasion/relationship match
        def score_gift(g):
            s = 1.0
            text = " ".join(
                [
                    g.title or "",
                    g.description or "",
                    g.tags or "",
                    g.category.name if g.category else "",
                    g.occasion or "",
                    g.relationship or "",
                ]
            ).lower()
            if interests:
                for it in interests:
                    if it.lower() in text:
                        s += 3.0
                        break
            if occ and g.occasion and occ in g.occasion.lower():
                s += 1.2
            if rel and g.relationship and rel in g.relationship.lower():
                s += 0.8
            return s

        weighted = [(score_gift(g), g) for g in gifts]
        weighted.sort(key=lambda x: x[0], reverse=True)
        top_pool = [g for _, g in weighted[: max(200, per_user * 3)]]

        picks = random.sample(top_pool, k=min(per_user, len(top_pool)))
        for g in picks:
            # Mostly clicks
            session.add(
                Interaction(
                    user_id=u.id,
                    gift_id=g.id,
                    interaction_type=InteractionType.click,
                    rating=None,
                )
            )
            # Some ratings
            if random.random() < 0.5:
                rating = 4.0 if random.random() < 0.7 else random.choice([2.0, 3.0, 5.0])
                session.add(
                    Interaction(
                        user_id=u.id,
                        gift_id=g.id,
                        interaction_type=InteractionType.rating,
                        rating=rating,
                    )
                )
            # Few purchases
            if random.random() < 0.12:
                session.add(
                    Interaction(
                        user_id=u.id,
                        gift_id=g.id,
                        interaction_type=InteractionType.purchase,
                        rating=None,
                    )
                )
            total += 1
    await session.commit()
    return total


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed demo profiles and interactions")
    parser.add_argument("--profiles", action="store_true", help="Seed or update user profiles")
    parser.add_argument("--interactions", type=int, default=0, help="Generate N interactions per user")
    args = parser.parse_args()

    async with SessionLocal() as session:
        if args.profiles:
            n = await seed_profiles(session)
            print(f"[OK] Profiles upserted for {n} users")
        if args.interactions > 0:
            n = await seed_interactions(session, per_user=args.interactions)
            print(f"[OK] Interactions created: ~{n}")


if __name__ == "__main__":
    asyncio.run(main())
