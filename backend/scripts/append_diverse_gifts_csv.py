import csv
import random
from pathlib import Path

CSV_PATH = Path("/home/samundra/Documents/gift/backend/data/gifts.csv")
TARGET_NEW_ROWS = 10_000

random.seed(42)

# Keep schema aligned with existing CSV
HEADER = [
    "Item",
    "Brand",
    "Category 0",
    "Category 1",
    "Category 2",
    "Product Name",
    "Description",
    "MSRP",
    "Rating",
    "Num of Reviews",
    "Features",
    "Link To Product",
    "Image URL",
]

books_data = {
    "Fiction": [
        ("Midnight Library", "A heartwarming contemporary novel about second chances and alternate lives."),
        ("The Silent Passenger", "A gripping psychological thriller with layered twists and suspense."),
        ("River of Echoes", "Literary fiction exploring family, memory, and identity across generations."),
        ("City of Emberlight", "A fast-paced urban fantasy adventure with rich world-building."),
        ("The Last Orchard", "An emotional coming-of-age story set in a quiet mountain town."),
    ],
    "Non-Fiction": [
        ("Atomic Habits", "A practical guide to building better habits through small daily improvements."),
        ("Deep Work", "Strategies to improve focus and create meaningful high-quality output."),
        ("Sapiens", "A broad history of humankind from early evolution to modern societies."),
        ("Think Again", "A thoughtful framework for rethinking beliefs and decision-making."),
        ("The Psychology of Money", "Timeless lessons about wealth, behavior, and financial choices."),
    ],
    "Self-Help": [
        ("Mindful Mornings", "Simple routines and reflection prompts for a calmer, productive day."),
        ("The Confidence Blueprint", "Practical exercises to improve confidence and self-expression."),
        ("Calm in Chaos", "Stress-management techniques for busy professionals and students."),
        ("The Joy Journal", "Daily gratitude prompts designed to improve emotional well-being."),
        ("Reset", "A practical roadmap to overcome burnout and regain motivation."),
    ],
    "Business": [
        ("Build to Last", "Insights on creating enduring companies and values-driven cultures."),
        ("Zero to One", "A startup-focused guide to innovation and competitive differentiation."),
        ("The Lean Startup", "Experiment-driven methods for launching products effectively."),
        ("Good Strategy Bad Strategy", "A clear framework for diagnosing and solving strategic challenges."),
        ("Competing in the Age of AI", "How organizations can leverage AI for long-term advantage."),
    ],
    "Cookbooks": [
        ("30-Minute Weeknight Dinners", "Fast, flavorful recipes for everyday home cooking."),
        ("Plant-Based Comfort", "Healthy vegetarian and vegan recipes with bold flavors."),
        ("Baking Basics", "Foundational techniques for cakes, cookies, breads, and pastries."),
        ("Global Street Food", "Inspired recipes from famous food markets around the world."),
        ("The Home Barista", "Café-style coffee, tea, and espresso drinks made at home."),
    ],
    "Children's Books": [
        ("The Little Moon Explorer", "An illustrated story that encourages curiosity and imagination."),
        ("Piper and the Forest Friends", "A gentle bedtime story about kindness and friendship."),
        ("STEM Adventures for Kids", "Fun educational activities introducing science and engineering concepts."),
        ("The Brave Little Otter", "A colorful children’s story about courage and resilience."),
        ("My First Big Book of Animals", "A picture-rich introduction to animals from around the world."),
    ],
    "Manga & Graphic Novels": [
        ("Skyblade Chronicles Vol. 1", "Action-packed fantasy manga featuring powerful rivals and alliances."),
        ("Neon District", "Cyberpunk graphic novel with stylized art and compelling antiheroes."),
        ("Star Academy", "Character-driven school adventure with humor and high-stakes battles."),
        ("The Silent Ronin", "Historical action manga with cinematic fight choreography."),
        ("Moonlit Detective", "Mystery graphic novel solving supernatural cases in a modern city."),
    ],
}

flowers_data = [
    ("Rose Elegance Bouquet", "A classic rose bouquet arranged for birthdays, anniversaries, and celebrations."),
    ("Spring Mixed Blooms", "A colorful hand-tied bouquet featuring seasonal flowers and greenery."),
    ("Sunflower Joy Bundle", "Bright sunflower arrangement designed to lift mood and add warmth."),
    ("Orchid Grace Pot", "Elegant potted orchid ideal for home décor and thoughtful gifting."),
    ("Preserved Rose Dome", "Long-lasting preserved roses presented in a premium display dome."),
]

watches_data = [
    ("Classic Leather Analog Watch", "Minimalist analog watch with timeless dial and comfortable leather strap."),
    ("Sport Chronograph Watch", "Durable chronograph watch designed for active daily wear."),
    ("Mesh Strap Dress Watch", "Sophisticated watch with stainless mesh strap for formal occasions."),
    ("Digital Fitness Watch", "Lightweight digital watch with step counter and workout timer features."),
    ("Couple Gift Watch Set", "Matching watch set designed as a stylish gift for special moments."),
]

toys_data = [
    ("STEM Robotics Kit", "Hands-on educational kit that teaches kids coding, mechanics, and logic."),
    ("Wooden Building Blocks", "Creative building block set for imagination and motor-skill development."),
    ("Strategy Board Game", "Family-friendly board game focused on teamwork and strategic thinking."),
    ("Jigsaw Puzzle 1000 pcs", "Premium puzzle set ideal for mindfulness and collaborative play."),
    ("Creative Art Craft Box", "All-in-one craft kit with markers, papers, and DIY project ideas."),
    ("Remote Control Car", "Rechargeable RC car with responsive controls and durable build."),
    ("Plush Animal Gift Set", "Soft plush collection perfect for comfort gifts and children."),
]

kitchen_data = [
    ("Cast Iron Skillet Set", "Pre-seasoned skillet set ideal for searing, baking, and everyday cooking."),
    ("Chef Knife Starter Set", "High-carbon stainless steel knives for precision slicing and prep."),
    ("Ceramic Bakeware Collection", "Oven-safe bakeware set designed for casseroles and desserts."),
    ("Espresso Maker Bundle", "Home espresso machine set for café-style drinks and milk frothing."),
    ("Premium Tea Infuser Kit", "Elegant tea brewing set with infuser, cups, and storage tin."),
    ("Smart Kitchen Scale", "Digital scale for accurate cooking and baking measurements."),
    ("Air Fryer Essentials Pack", "Accessory kit for air fryer meals with trays and liners."),
]

extra_categories = {
    "Clothing": [
        ("Cozy Knit Sweater", "Soft knit sweater designed for warmth, comfort, and casual styling."),
        ("Premium Hoodie", "Everyday unisex hoodie made from breathable cotton blend fabric."),
        ("Classic Denim Jacket", "Versatile denim jacket suitable for year-round layering."),
    ],
    "Stationery": [
        ("Luxury Journal Set", "Premium notebook and pen set ideal for planning and journaling."),
        ("Artist Sketchbook Pack", "Acid-free sketchbook set for drawing, design, and creative work."),
        ("Desk Organizer Bundle", "Workspace organizer kit to improve desk productivity and aesthetics."),
    ],
    "Wellness": [
        ("Aromatherapy Diffuser", "Ultrasonic diffuser with calming essential oil blend."),
        ("Yoga Starter Kit", "Yoga mat, strap, and block set for home workouts and flexibility."),
        ("Self-Care Gift Box", "Curated relaxation set with candles, bath salts, and mask."),
    ],
    "Tech": [
        ("Wireless Earbuds", "Compact Bluetooth earbuds with clear audio and long battery life."),
        ("Portable Bluetooth Speaker", "Travel-ready speaker delivering rich sound indoors and outdoors."),
        ("Smart Desk Lamp", "Adjustable LED lamp with dimming modes for study and work."),
    ],
    "Home Decor": [
        ("Minimalist Table Lamp", "Elegant table lamp designed to complement modern interiors."),
        ("Framed Wall Art Set", "Curated art print set for living room, bedroom, or office décor."),
        ("Indoor Plant Gift Pot", "Decorative planter with easy-care indoor plant gift option."),
    ],
}

image_pool = {
    "books": [
        "https://images.unsplash.com/photo-1512820790803-83ca734da794",
        "https://images.unsplash.com/photo-1495446815901-a7297e633e8d",
        "https://images.unsplash.com/photo-1521587760476-6c12a4b040da",
        "https://images.unsplash.com/photo-1519682337058-a94d519337bc",
    ],
    "flowers": [
        "https://images.unsplash.com/photo-1490750967868-88aa4486c946",
        "https://images.unsplash.com/photo-1468327768560-75b778cbb551",
        "https://images.unsplash.com/photo-1455656678494-4d1b5f3e7ad8",
    ],
    "watches": [
        "https://images.unsplash.com/photo-1523170335258-f5ed11844a49",
        "https://images.unsplash.com/photo-1547996160-81dfa63595aa",
        "https://images.unsplash.com/photo-1522312346375-d1a52e2b99b3",
    ],
    "toys": [
        "https://images.unsplash.com/photo-1515488764276-beab7607c1e6",
        "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088",
        "https://images.unsplash.com/photo-1587654780291-39c9404d746b",
    ],
    "kitchen": [
        "https://images.unsplash.com/photo-1556911220-bff31c812dba",
        "https://images.unsplash.com/photo-1506368083636-6defb67639a7",
        "https://images.unsplash.com/photo-1473093295043-cdd812d0e601",
    ],
    "extra": [
        "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab",
        "https://images.unsplash.com/photo-1517705008128-361805f42e86",
        "https://images.unsplash.com/photo-1519710164239-da123dc03ef4",
        "https://images.unsplash.com/photo-1515377905703-c4788e51af15",
        "https://images.unsplash.com/photo-1485955900006-10f4d324d411",
    ],
}

def money(v: float) -> str:
    return f"${v:.2f}"


def mk_features(kind: str, age_group: str = "All Ages") -> str:
    parts = [
        f"Great for: {kind} gift ideas",
        f"Age suitability: {age_group}",
        "Occasions: Birthday, Anniversary, Holiday, Celebration",
        "Gift-ready packaging included",
        "Imported",
    ]
    return "[\"" + "\",\"".join(parts) + "\"]"


def random_rating() -> str:
    return str(round(random.uniform(3.8, 5.0), 1))


def random_reviews() -> str:
    return str(random.randint(3, 3200))


def choose_price(low: float, high: float) -> str:
    return money(round(random.uniform(low, high), 2))


def build_row(item_id: int, brand: str, c1: str, c2: str, c3: str, name: str, desc: str, msrp: str, image_url: str) -> list[str]:
    return [
        str(item_id),
        brand,
        "For Her",
        c1,
        c2 if c2 else c3,
        name,
        desc,
        msrp,
        random_rating(),
        random_reviews(),
        mk_features(c3),
        "",
        image_url,
    ]


def main() -> None:
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

    with CSV_PATH.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        existing_rows = list(reader)

    if not existing_rows:
        raise RuntimeError("CSV is empty")

    header = existing_rows[0]
    if header != HEADER:
        raise RuntimeError(f"Header mismatch. Found: {header}")

    existing_ids = set()
    max_id = 0
    for row in existing_rows[1:]:
        if not row:
            continue
        try:
            val = int(str(row[0]).strip())
            existing_ids.add(val)
            max_id = max(max_id, val)
        except Exception:
            continue

    next_id = max_id + 1
    new_rows: list[list[str]] = []

    brands_books = ["Penguin", "HarperCollins", "Simon & Schuster", "Hachette", "Macmillan", "Vintage", "Orbit"]
    brands_flowers = ["BloomNest", "PetalCraft", "FloraJoy", "RoseAura"]
    brands_watches = ["Timex", "Casio", "Fossil", "Seiko", "Citizen", "Skagen"]
    brands_toys = ["LEGO", "Hasbro", "Mattel", "Melissa & Doug", "PlayShifu", "ThinkFun"]
    brands_kitchen = ["Cuisinart", "KitchenAid", "OXO", "Lodge", "Breville", "Ninja"]

    generators = []

    # Books
    for subtype, items in books_data.items():
        for n, d in items:
            generators.append((
                lambda n=n, d=d, subtype=subtype: (
                    random.choice(brands_books),
                    "Books",
                    subtype,
                    f"{n} ({subtype})",
                    d,
                    choose_price(9, 59),
                    random.choice(image_pool["books"]),
                )
            ))

    # Flowers
    for n, d in flowers_data:
        generators.append((
            lambda n=n, d=d: (
                random.choice(brands_flowers),
                "Flowers",
                "Bouquets & Floral Gifts",
                n,
                d,
                choose_price(24, 149),
                random.choice(image_pool["flowers"]),
            )
        ))

    # Watches
    for n, d in watches_data:
        generators.append((
            lambda n=n, d=d: (
                random.choice(brands_watches),
                "Jewelry & Watches",
                "Watches",
                n,
                d,
                choose_price(49, 499),
                random.choice(image_pool["watches"]),
            )
        ))

    # Toys
    for n, d in toys_data:
        generators.append((
            lambda n=n, d=d: (
                random.choice(brands_toys),
                "All Toys",
                "Toys & Games",
                n,
                d,
                choose_price(12, 249),
                random.choice(image_pool["toys"]),
            )
        ))

    # Kitchen
    for n, d in kitchen_data:
        generators.append((
            lambda n=n, d=d: (
                random.choice(brands_kitchen),
                "Home",
                "Kitchen & Dining",
                n,
                d,
                choose_price(18, 399),
                random.choice(image_pool["kitchen"]),
            )
        ))

    # Extra categories
    for cat, items in extra_categories.items():
        for n, d in items:
            generators.append((
                lambda n=n, d=d, cat=cat: (
                    cat + " Co.",
                    cat if cat in ["Tech", "Wellness", "Home Decor"] else "Lifestyle & Interests",
                    cat,
                    n,
                    d,
                    choose_price(15, 299),
                    random.choice(image_pool["extra"]),
                )
            ))

    while len(new_rows) < TARGET_NEW_ROWS:
        g = random.choice(generators)
        brand, c1, c2, name, desc, msrp, image = g()

        item_id = next_id
        next_id += 1
        while item_id in existing_ids:
            item_id += 1
            next_id = item_id + 1

        existing_ids.add(item_id)

        row = build_row(
            item_id=item_id,
            brand=brand,
            c1=c1,
            c2=c2,
            c3=c2,
            name=name,
            desc=desc,
            msrp=msrp,
            image_url=image,
        )
        new_rows.append(row)

    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(new_rows)

    # summary
    print(f"Appended rows: {len(new_rows)}")
    print(f"New id range: {new_rows[0][0]}..{new_rows[-1][0]}")


if __name__ == "__main__":
    main()
