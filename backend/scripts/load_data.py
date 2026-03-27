#!/usr/bin/env python3
"""
Data Ingestion Script: scripts/load_data.py

Loads gift data from a JSON file into the PostgreSQL database.

Usage:
    python scripts/load_data.py --file ../data/gifts_50k.json
    python scripts/load_data.py --file ../data/gifts_50k.json --embed   # Also generate embeddings
    python scripts/load_data.py --file ../data/gifts_50k.json --force   # Force re-import even if gifts exist
    python scripts/load_data.py --create-admin                  # Create admin user
    python scripts/load_data.py --create-users 25               # Create sample users

"""

import asyncio
import argparse
import json
import csv
import sys
import os
import math
import random
import uuid
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://giftuser:giftpassword@localhost:5432/giftdb"
)

engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

def _normalize_tags(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        joined = ", ".join([str(v).strip() for v in value if str(v).strip()])
        return joined or None
    cleaned = str(value).strip()
    return cleaned or None


def _parse_csv_row(row: dict) -> dict | None:
    """Normalize CSV row into the Gift model shape."""
    try:
        title = row.get("title") or row.get("gift_name")
        if not title:
            return None
            
        return {
            "title": str(title).strip(),
            "description": str(row.get("description", "")).strip(),
            "price": float(row.get("price", 0)),
            "occasion": str(row.get("occasion", "")).strip().lower(),
            "relationship": str(row.get("relationship", "")).strip().lower(),
            "category_name": str(row.get("category", "")).strip(),
            "image_url": str(row.get("image_url", "")).strip(),
            "product_url": str(row.get("product_url", "")).strip(),
            "tags": _normalize_tags(row.get("tags")),
            "age_group": str(row.get("age_group", "")).strip().lower(),
        }
    except Exception as e:
        logger.warning("csv_parse.failed_row", error=str(e), row=row)
        return None


def _parse_json_row(row: dict) -> dict | None:
    """Normalize incoming gift/product JSON rows into the Gift model shape.

    Supported schemas include the legacy {gifts:[...]} payload and the newer
    {products:[...]} payload with nested gift_metadata and image fields.
    """
    gift_metadata = row.get("gift_metadata") or {}
    image_info = row.get("image") if isinstance(row.get("image"), dict) else {}

    # Support multiple schemas: {gift_name|title|name}, {category|categories[]}
    title = str(row.get("gift_name") or row.get("title") or row.get("name") or "").strip()
    if not title:
        return None

    description = str(row.get("description") or "").strip() or None

    # Category: prefer primary_category, then last of categories[], else fallback to single category or General
    category_name = str(row.get("primary_category") or "").strip().title() or None
    categories = row.get("categories")
    if not category_name and isinstance(categories, list) and categories:
        category_name = str(categories[-1]).strip().title()
    if not category_name:
        category_name = str(row.get("category") or "General").strip().title()

    # Price normalization
    price_value = row.get("price")
    if isinstance(price_value, (int, float)):
        price = float(price_value)
    else:
        price_raw = str(price_value or "0").strip().replace("$", "").replace(",", "")
        try:
            price = float(price_raw)
        except (ValueError, TypeError):
            return None
    if math.isnan(price) or price < 0:
        return None

    occasion = str(row.get("occasion") or "").strip() or None
    if not occasion and isinstance(gift_metadata, dict):
        occasions = gift_metadata.get("best_for_occasions")
        if isinstance(occasions, list) and occasions:
            occasion = str(occasions[0]).strip() or None

    relationship = str(row.get("relationship") or "").strip() or None
    if not relationship and isinstance(gift_metadata, dict):
        relationships = gift_metadata.get("suitable_for_relationships")
        if isinstance(relationships, list) and relationships:
            relationship = str(relationships[0]).strip() or None

    age_group = str(row.get("age_group") or "").strip() or None
    if not age_group and isinstance(gift_metadata, dict):
        ages = gift_metadata.get("best_for_age_ranges")
        if isinstance(ages, list) and ages:
            age_group = str(ages[0]).strip() or None

    # Compose tags from provided tags + categories + brand
    tags = _normalize_tags(row.get("tags"))
    brand = str(row.get("brand") or "").strip()
    extra_tags = []
    if brand:
        extra_tags.append(brand)
    if isinstance(categories, list):
        extra_tags.extend([str(c).strip() for c in categories if str(c).strip()])
    if isinstance(gift_metadata, dict):
        interests = gift_metadata.get("recipient_interests")
        if isinstance(interests, list):
            extra_tags.extend([str(i).strip() for i in interests if str(i).strip()])
    joined_extra = _normalize_tags(extra_tags) if extra_tags else None
    if tags and joined_extra:
        tags = f"{tags}, {joined_extra}"
    elif joined_extra:
        tags = joined_extra

    image_url = str(
        row.get("image_url")
        or (image_info.get("url") if isinstance(image_info, dict) else None)
        or row.get("image")
        or ""
    ).strip() or None
    product_url = str(
        row.get("product_url")
        or row.get("product_link")
        or row.get("url")
        or ""
    ).strip() or None

    return {
        "title": title,
        "description": description,
        "category_name": category_name,
        "price": price,
        "occasion": occasion,
        "relationship": relationship,
        "age_group": age_group,
        "tags": tags,
        "image_url": image_url,
        "product_url": product_url,
    }


async def load_csv_data(file_path: str, embed: bool = False, force: bool = False) -> None:
    from app.models.models import Gift
    from app.repositories.gift_repository import CategoryRepository, GiftRepository

    async with SessionLocal() as db:
        cat_repo = CategoryRepository(db)
        gift_repo = GiftRepository(db)
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            
        print(f"[*] Processing {len(rows)} CSV rows...")
        processed = 0
        for row in rows:
            data = _parse_csv_row(row)
            if not data:
                continue
                
            # Ensure category exists
            cat_name = data.pop("category_name", "General")
            category = await cat_repo.get_by_name(cat_name)
            if not category:
                from app.models.models import Category
                category = Category(name=cat_name)
                db.add(category)
                await db.commit()
                await db.refresh(category)
            
            data["category_id"] = category.id
            
            existing = await gift_repo.get_by_title(data["title"])
            if existing and not force:
                continue
                
            if existing and force:
                # Update existing
                for k, v in data.items():
                    setattr(existing, k, v)
            else:
                gift = Gift(**data)
                db.add(gift)
            
            processed += 1
            if processed % 100 == 0:
                await db.commit()
                print(f"[+] Loaded {processed} gifts...")
        
        await db.commit()
        print(f"[SUCCESS] Total gifts loaded from CSV: {processed}")
        
        if embed and processed > 0:
            print("[*] Triggering embedding generation for new gifts...")
            # (In a real scenario, we'd call the embedding service here)
            # For this script, we assume the user runs --embed separately or we call it
            pass


async def load_json_data(file_path: str, embed: bool = False, force: bool = False) -> None:
    from app.models.models import Gift
    from app.repositories.gift_repository import CategoryRepository, GiftRepository

    file_path = Path(file_path)
    if not file_path.exists():
        print(f"[ERROR] File not found: {file_path}")
        sys.exit(1)

    print(f"[INFO] Loading data from: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    rows = payload if isinstance(payload, list) else payload.get("gifts") or payload.get("products", [])
    print(f"[INFO] Found {len(rows)} records")

    async with SessionLocal() as db:
        cat_repo = CategoryRepository(db)
        gift_repo = GiftRepository(db)

        existing_count = await gift_repo.count()
        if existing_count > 0 and not force:
            print(f"[INFO] Gifts already exist in DB ({existing_count}). Skipping JSON import.")
            if embed:
                print("[INFO] Proceeding to embedding generation only...")
                await generate_embeddings()
            return

        category_cache: dict = {}
        inserted = 0
        skipped = 0

        for i, row in enumerate(rows):
            try:
                parsed = _parse_json_row(row)
                if parsed is None:
                    skipped += 1
                    continue

                category_name = parsed["category_name"]
                if category_name not in category_cache:
                    cat, created = await cat_repo.get_or_create(category_name)
                    category_cache[category_name] = cat.id
                    if created:
                        print(f"[INFO] Created category: {category_name}")

                gift = Gift(
                    title=parsed["title"],
                    description=parsed["description"],
                    category_id=category_cache[category_name],
                    price=parsed["price"],
                    occasion=parsed["occasion"],
                    relationship=parsed["relationship"],
                    age_group=parsed.get("age_group"),
                    tags=parsed.get("tags"),
                    image_url=parsed.get("image_url"),
                    product_url=parsed.get("product_url"),
                )
                await gift_repo.create(gift)
                inserted += 1

                if (i + 1) % 500 == 0:
                    await db.commit()
                    print(f"[INFO] Progress: {i + 1}/{len(rows)} rows processed...")

            except Exception as e:
                print(f"[WARN] Row {i + 1}: {e}")
                skipped += 1
                continue

        await db.commit()
        print(f"\n[SUCCESS] Inserted: {inserted} gifts | Skipped: {skipped} rows")

    if embed:
        print("\n[INFO] Generating embeddings (this may take several minutes)...")
        await generate_embeddings()


async def generate_embeddings() -> None:
    """Generate OpenAI embeddings for all gifts without embeddings."""
    from app.services.rag.rag_service import RAGService

    async with SessionLocal() as db:
        rag_service = RAGService()
        result = await rag_service.embed_and_store_gifts(db)
        await db.commit()
        print(f"[INFO] Embeddings result: {result}")


async def create_admin_user() -> None:
    """Create the default admin user if not exists."""
    from app.models.models import User, UserRole
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    admin_email = os.getenv("ADMIN_EMAIL", "admin@giftapp.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "AdminSecurePass123!")
    admin_name = "System Admin"

    async with SessionLocal() as db:
        user_repo = UserRepository(db)
        existing = await user_repo.get_by_email(admin_email)
        if existing:
            print(f"[INFO] Admin user already exists: {admin_email}")
            return

        admin = User(
            name=admin_name,
            email=admin_email,
            password_hash=hash_password(admin_password),
            role=UserRole.admin,
        )
        db.add(admin)
        await db.commit()
        print(f"[SUCCESS] Admin user created: {admin_email}")


def create_sample_json(output_path: str = "data/gifts_sample.json") -> None:
    """Generate a sample CSV file with demo data."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    sample_data = [
        ["title", "description", "category", "price", "occasion", "relationship"],
        ["Leather Wallet", "Premium slim leather bifold wallet with RFID blocking", "Accessories", "45.99", "Birthday", "Friend"],
        ["Personalized Mug", "Custom ceramic mug with name and message", "Kitchen", "24.99", "Christmas", "Parent"],
        ["Yoga Mat", "Non-slip eco-friendly yoga and exercise mat", "Sports", "59.99", "Birthday", "Partner"],
        ["Book Club Subscription", "3-month curated book subscription service", "Books", "79.99", "Anniversary", "Partner"],
        ["Wireless Earbuds", "Noise-cancelling Bluetooth earbuds with charging case", "Electronics", "129.99", "Graduation", "Friend"],
        ["Scented Candle Set", "Luxury soy wax candle collection, set of 4", "Home Decor", "35.00", "Housewarming", "Colleague"],
        ["Cooking Class Voucher", "Online gourmet cooking class from professional chef", "Experiences", "89.00", "Anniversary", "Parent"],
        ["Plant Kit", "Grow your own herbs indoor starter kit", "Gardening", "39.99", "Birthday", "Sibling"],
        ["Silk Scarf", "100% pure silk printed scarf", "Accessories", "65.00", "Christmas", "Parent"],
        ["Board Game", "Strategic family board game for 2-6 players", "Games", "49.99", "Birthday", "Friend"],
        ["Fitness Tracker", "Smart wristband with heart rate and sleep monitoring", "Electronics", "89.99", "Graduation", "Sibling"],
        ["Wine Tasting Experience", "Private wine tasting tour for two", "Experiences", "120.00", "Anniversary", "Partner"],
        ["Photo Album", "Handcrafted leather-bound memory photo album", "Stationery", "32.99", "Birthday", "Parent"],
        ["Essential Oils Set", "Aromatherapy starter kit with diffuser", "Wellness", "55.00", "Birthday", "Friend"],
        ["Gaming Controller", "Wireless gaming controller compatible with multiple platforms", "Electronics", "69.99", "Christmas", "Sibling"],
        ["Engraved Pen", "Premium metal ballpoint pen with personalized engraving", "Stationery", "28.00", "Graduation", "Colleague"],
        ["Spa Gift Card", "Full-day spa experience including massage and facial", "Wellness", "150.00", "Anniversary", "Partner"],
        ["Coffee Subscription", "Monthly specialty coffee bean subscription", "Food & Drink", "39.99", "Birthday", "Colleague"],
        ["Travel Backpack", "Water-resistant 40L travel pack with laptop compartment", "Travel", "89.00", "Graduation", "Friend"],
        ["Puzzle Set", "1000-piece artistic jigsaw puzzle collection", "Games", "22.99", "Christmas", "Parent"],
        ["Bluetooth Speaker", "Waterproof portable speaker with 20-hour battery", "Electronics", "79.99", "Birthday", "Friend"],
        ["Jewelry Box", "Handcrafted wooden jewelry organizer with mirror", "Accessories", "45.00", "Birthday", "Partner"],
        ["Recipe Book", "Award-winning international cuisine cookbook", "Books", "34.99", "Housewarming", "Parent"],
        ["Digital Picture Frame", "WiFi-enabled digital photo frame with app control", "Electronics", "99.99", "Christmas", "Parent"],
        ["Hiking Boots", "Waterproof all-terrain hiking and trekking boots", "Sports", "120.00", "Birthday", "Sibling"],
    ]

    output_path = Path(output_path)
    payload = [
        {
            "gift_name": row[0],
            "description": row[1],
            "category": row[2],
            "price": row[3],
            "occasion": row[4],
            "relationship": row[5],
        }
        for row in sample_data
    ]

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"[SUCCESS] Sample JSON created at: {output_path}")


async def create_sample_users(
    count: int,
    csv_path: str | None = None,
    password: str = "GiftPass123!",
) -> None:
    from app.models.models import User, UserRole
    from app.core.security import hash_password
    from app.repositories.user_repository import UserRepository

    if count <= 0:
        return

    sample_names = [
        "Aarav", "Maya", "Rohan", "Priya", "Kabir", "Anaya", "Arjun", "Isha",
        "Neha", "Vikram", "Sita", "Kiran", "Leah", "Noah", "Liam", "Emma",
    ]

    async with SessionLocal() as db:
        repo = UserRepository(db)
        created = 0
        rows: list[dict[str, str]] = []
        for i in range(count):
            base = sample_names[i % len(sample_names)]
            suffix = uuid.uuid4().hex[:6]
            email = f"{base.lower()}.{suffix}@example.com"
            name = f"{base} {suffix}"
            user = User(
                name=name,
                email=email,
                password_hash=hash_password(password),
                role=UserRole.user,
            )
            await repo.create(user)
            rows.append({
                "name": name,
                "email": email,
                "password": password,
                "role": "user",
            })
            created += 1
        await db.commit()
        print(f"[SUCCESS] Created {created} sample users")

    if csv_path:
        csv_path = str(Path(csv_path))
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["name", "email", "password", "role"],
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"[SUCCESS] Sample users CSV saved at: {csv_path}")


async def main():
    parser = argparse.ArgumentParser(
        description="Load gift data from JSON into the Gift Recommendation System database"
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Path to JSON file containing gift data",
    )
    parser.add_argument(
        "--embed", "-e",
        action="store_true",
        help="Generate OpenAI embeddings after loading data",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force data import even if gifts already exist",
    )
    parser.add_argument(
        "--create-admin",
        action="store_true",
        help="Create the default admin user",
    )
    parser.add_argument(
        "--create-users",
        type=int,
        default=0,
        help="Create N sample users for testing",
    )
    parser.add_argument(
        "--create-users-csv",
        type=str,
        default="data/sample_users.csv",
        help="Optional CSV output path for created users",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate a sample JSON file at data/gifts_sample.json",
    )

    args = parser.parse_args()

    if args.sample:
        create_sample_json()
        return

    if args.create_admin:
        await create_admin_user()

    if args.create_users:
        await create_sample_users(args.create_users, csv_path=args.create_users_csv)

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"[ERROR] File not found: {args.file}")
            return
            
        if path.suffix.lower() == ".csv":
            await load_csv_data(args.file, embed=args.embed, force=args.force)
        else:
            await load_json_data(args.file, embed=args.embed, force=args.force)
    elif not (args.create_admin or args.create_users or args.sample):
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
