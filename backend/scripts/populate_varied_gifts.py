"""
Generate varied gift data by creating variations of existing gifts.
Changes: name prefixes/suffixes, categories, slight price changes.
Adds ~5000 new gifts spread across all occasions, relationships, categories.
"""
import asyncio
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import AsyncSessionLocal
from app.models.models import Gift, Category

PREFIXES = [
    "Premium", "Deluxe", "Classic", "Modern", "Artisan", "Handcrafted",
    "Signature", "Essential", "Luxury", "Custom", "Vintage", "Designer",
    "Limited Edition", "Exclusive", "Elegant", "Charming", "Cozy",
]
SUFFIXES = [
    "Collection", "Set", "Bundle", "Edition", "Gift Box", "Selection",
    "Assortment", "Pack", "Kit", "Combo", "Special", "Surprise",
]
OCCASIONS = ["Birthday", "Anniversary", "Wedding", "Graduation"]
RELATIONSHIPS = ["Partner", "Friend", "Child"]

async def populate():
    async with AsyncSessionLocal() as db:
        # Get existing categories
        cats = (await db.execute(select(Category))).scalars().all()
        cat_ids = [c.id for c in cats]

        # Sample some existing gifts as templates
        result = await db.execute(
            select(Gift).order_by(text("RANDOM()")).limit(1000)
        )
        templates = result.scalars().all()

        if not templates:
            print("No existing gifts to use as templates!")
            return

        new_gifts = []
        for i in range(5000):
            tmpl = random.choice(templates)
            prefix = random.choice(PREFIXES)
            suffix = random.choice(SUFFIXES) if random.random() > 0.5 else ""

            # Vary the name
            base_name = tmpl.title
            if len(base_name) > 60:
                base_name = base_name[:60]
            new_name = f"{prefix} {base_name}"
            if suffix:
                new_name = f"{new_name} {suffix}"

            # Vary price by ±20%
            price_factor = random.uniform(0.8, 1.2)
            new_price = round(tmpl.price * price_factor, 2)
            new_price = max(5.0, min(new_price, 999.99))

            # Random occasion and relationship
            occ = random.choice(OCCASIONS)
            rel = random.choice(RELATIONSHIPS)

            # Random category
            cat_id = random.choice(cat_ids)

            gift = Gift(
                title=new_name[:200],
                description=tmpl.description,
                price=new_price,
                occasion=occ,
                relationship=rel,
                category_id=cat_id,
                image_url=tmpl.image_url,
                product_url=tmpl.product_url,
            )
            new_gifts.append(gift)

        db.add_all(new_gifts)
        await db.commit()
        print(f"Added {len(new_gifts)} new varied gifts!")

        # Count total
        count = await db.execute(text("SELECT count(*) FROM gifts"))
        total = count.scalar()
        print(f"Total gifts now: {total}")

if __name__ == "__main__":
    asyncio.run(populate())
