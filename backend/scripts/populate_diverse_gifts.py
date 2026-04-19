"""
Populate the database with diverse gift categories:
Books, Gaming, Tech Gadgets, Music, Art & Crafts, Outdoor, Sports,
Kitchen & Cooking, Wellness, Stationery, Plant Lover, Pet Lover
Each gift has a real Unsplash image URL.
"""
import asyncio
import sys
import os
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://giftuser:giftpassword@localhost:5432/giftdb")

from sqlalchemy import select, text, func
from app.core.database import AsyncSessionLocal
from app.models.models import Gift, Category


# ── Unsplash image helpers (deterministic, free, no API key) ──────────────
def unsplash(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?w=800&q=80"


# ── Gift data by category ────────────────────────────────────────────────
GIFT_DATA: dict[str, list[dict]] = {
    "Books": [
        {"title": "The Midnight Library", "desc": "A novel about all the lives you could have lived by Matt Haig", "price": 14.99, "img": unsplash("1512820790803-83ca734da794")},
        {"title": "Atomic Habits by James Clear", "desc": "Proven framework for building good habits and breaking bad ones", "price": 16.99, "img": unsplash("1544947950-fa07a98d237f")},
        {"title": "Sapiens: A Brief History", "desc": "Yuval Noah Harari explores the history of humankind", "price": 18.99, "img": unsplash("1589998059171-988d887df646")},
        {"title": "The Art of War", "desc": "Sun Tzu's ancient text on military strategy and leadership", "price": 9.99, "img": unsplash("1524578271613-d550eacf6090")},
        {"title": "Educated by Tara Westover", "desc": "A memoir about growing up in a survivalist family and finding education", "price": 15.99, "img": unsplash("1495446815901-a7297e633e8d")},
        {"title": "Think and Grow Rich", "desc": "Napoleon Hill's classic guide to success and wealth", "price": 12.99, "img": unsplash("1543002588-bfa74002ed7e")},
        {"title": "The Great Gatsby", "desc": "F. Scott Fitzgerald's masterpiece about the American Dream", "price": 11.99, "img": unsplash("1544716278-ca5e3f4abd8c")},
        {"title": "Dune by Frank Herbert", "desc": "Epic science fiction saga set on the desert planet Arrakis", "price": 17.99, "img": unsplash("1531346878377-a5be20888e57")},
        {"title": "1984 by George Orwell", "desc": "Dystopian novel about totalitarian surveillance and truth", "price": 10.99, "img": unsplash("1476275466078-f5ba7c65d2a1")},
        {"title": "To Kill a Mockingbird", "desc": "Harper Lee's profound novel about justice and racial inequality", "price": 13.99, "img": unsplash("1497633762265-9d179a990aa6")},
        {"title": "Harry Potter Box Set", "desc": "Complete collection of J.K. Rowling's magical series", "price": 69.99, "img": unsplash("1618666012174-83b441d55bc8")},
        {"title": "The Alchemist by Paulo Coelho", "desc": "A fable about following your dreams and personal legend", "price": 14.49, "img": unsplash("1516979187457-637abb4f9353")},
        {"title": "Rich Dad Poor Dad", "desc": "Robert Kiyosaki's guide to financial literacy and investing", "price": 15.49, "img": unsplash("1553729459-afe8f2e2ed65")},
        {"title": "The Hobbit by J.R.R. Tolkien", "desc": "Classic fantasy adventure of Bilbo Baggins", "price": 13.49, "img": unsplash("1535905557558-afc4877a26fc")},
        {"title": "Becoming by Michelle Obama", "desc": "Intimate memoir from the former First Lady of the United States", "price": 19.99, "img": unsplash("1512820790803-83ca734da794")},
        {"title": "The Power of Now", "desc": "Eckhart Tolle's guide to spiritual enlightenment and presence", "price": 14.99, "img": unsplash("1544947950-fa07a98d237f")},
        {"title": "Ikigai: The Japanese Secret", "desc": "Discover the Japanese concept of finding purpose in life", "price": 12.49, "img": unsplash("1589998059171-988d887df646")},
        {"title": "Where the Crawdads Sing", "desc": "Delia Owens' mystery novel set in the marshes of North Carolina", "price": 16.49, "img": unsplash("1524578271613-d550eacf6090")},
        {"title": "The Subtle Art of Not Caring", "desc": "Mark Manson's counterintuitive approach to living a good life", "price": 15.99, "img": unsplash("1495446815901-a7297e633e8d")},
        {"title": "Project Hail Mary", "desc": "Andy Weir's thrilling sci-fi novel about saving Earth", "price": 18.49, "img": unsplash("1543002588-bfa74002ed7e")},
        {"title": "Meditations by Marcus Aurelius", "desc": "Stoic philosophy from the Roman Emperor — timeless wisdom", "price": 8.99, "img": unsplash("1544716278-ca5e3f4abd8c")},
        {"title": "Lord of the Rings Trilogy", "desc": "Tolkien's epic fantasy masterpiece in a beautiful box set", "price": 45.99, "img": unsplash("1531346878377-a5be20888e57")},
        {"title": "The Little Prince", "desc": "Antoine de Saint-Exupéry's beloved tale about love and loss", "price": 9.49, "img": unsplash("1476275466078-f5ba7c65d2a1")},
        {"title": "Norwegian Wood by Murakami", "desc": "Haruki Murakami's nostalgic novel about love and growing up", "price": 14.99, "img": unsplash("1497633762265-9d179a990aa6")},
        {"title": "The Book Thief", "desc": "Markus Zusak's WWII novel narrated by Death", "price": 13.99, "img": unsplash("1618666012174-83b441d55bc8")},
    ],
    "Gaming": [
        {"title": "Nintendo Switch Pro Controller", "desc": "Premium wireless controller for Nintendo Switch gaming", "price": 59.99, "img": unsplash("1612287230202-1ff1d85d1bdf")},
        {"title": "PlayStation Gift Card $50", "desc": "Digital gift card for the PlayStation Store", "price": 50.00, "img": unsplash("1606144042614-b2417e99c4e3")},
        {"title": "Gaming Headset RGB", "desc": "7.1 surround sound gaming headset with noise cancellation", "price": 49.99, "img": unsplash("1618366712010-f4ae9c647dcb")},
        {"title": "Retro Arcade Mini Console", "desc": "Classic arcade machine with 200+ built-in retro games", "price": 39.99, "img": unsplash("1578303512597-81e6cc155b3e")},
        {"title": "LED Gaming Mouse Pad XL", "desc": "RGB illuminated extended mouse pad for gamers", "price": 24.99, "img": unsplash("1527814050087-3793815479db")},
        {"title": "Steam Gift Card $25", "desc": "Gift card for Steam digital game store", "price": 25.00, "img": unsplash("1542751371-adc38448a05e")},
        {"title": "Gaming Chair Ergonomic", "desc": "High-back racing style gaming chair with lumbar support", "price": 189.99, "img": unsplash("1616588589676-62b3d4ff6a10")},
        {"title": "Xbox Game Pass 3 Months", "desc": "Access hundreds of games on Xbox and PC", "price": 29.99, "img": unsplash("1621259182978-fbf93132d53d")},
        {"title": "Mechanical Gaming Keyboard", "desc": "RGB mechanical keyboard with cherry MX switches", "price": 79.99, "img": unsplash("1587829741301-dc798b83add3")},
        {"title": "Gaming Desk Organizer", "desc": "Multi-functional desk organizer with USB charging hub", "price": 34.99, "img": unsplash("1593062096033-9a26b09da705")},
        {"title": "VR Headset Stand", "desc": "Premium display stand for VR headset and controllers", "price": 29.99, "img": unsplash("1622979135225-d2ba269cf1ac")},
        {"title": "Zelda Collector's Edition", "desc": "Limited edition Zelda artbook and collectible set", "price": 44.99, "img": unsplash("1551103782-8ab11b1d49c1")},
        {"title": "Gaming Finger Sleeves", "desc": "Anti-sweat touch screen finger covers for mobile gaming", "price": 8.99, "img": unsplash("1560419015-7c427e8ae5ba")},
        {"title": "Portable Gaming Monitor", "desc": "15.6-inch portable IPS display for gaming on the go", "price": 159.99, "img": unsplash("1593305841991-05c297ba4575")},
        {"title": "D&D Starter Set", "desc": "Dungeons & Dragons starter set with dice, rulebook, and adventure", "price": 19.99, "img": unsplash("1611996575749-79a3a250f948")},
    ],
    "Tech Gadgets": [
        {"title": "Wireless Earbuds Pro", "desc": "Active noise cancelling Bluetooth earbuds with premium sound", "price": 79.99, "img": unsplash("1590658268037-6bf12f032f32")},
        {"title": "Smart Watch Fitness Tracker", "desc": "Track heart rate, steps, sleep, and notifications on your wrist", "price": 49.99, "img": unsplash("1579586337278-3befd40fd17a")},
        {"title": "Portable Bluetooth Speaker", "desc": "Waterproof portable speaker with 24-hour battery life", "price": 39.99, "img": unsplash("1608043152269-423dbba4e7e1")},
        {"title": "USB-C Hub 7-in-1", "desc": "Multi-port adapter with HDMI, USB-A, SD card, and charging", "price": 34.99, "img": unsplash("1625842268584-8f3296236761")},
        {"title": "Wireless Charging Pad", "desc": "Fast wireless charger compatible with all Qi devices", "price": 19.99, "img": unsplash("1586953208270-767fc8361b9d")},
        {"title": "Smart LED Light Strip 5m", "desc": "WiFi-enabled RGB LED strip with app and voice control", "price": 24.99, "img": unsplash("1558618666-fcd25c85f82e")},
        {"title": "Digital Drawing Tablet", "desc": "Graphics tablet with stylus pen for digital art creation", "price": 59.99, "img": unsplash("1626785774573-4b799315345d")},
        {"title": "Mini Projector Portable", "desc": "Pocket-sized LED projector for movies and presentations", "price": 89.99, "img": unsplash("1478720568477-152d9b164e26")},
        {"title": "Smart Plug WiFi 4-Pack", "desc": "Voice-controlled smart plugs compatible with Alexa and Google", "price": 29.99, "img": unsplash("1558089687-f282d8b1b0d2")},
        {"title": "E-Reader Kindle Paperwhite", "desc": "Glare-free e-reader with adjustable warm light", "price": 139.99, "img": unsplash("1544716278-ca5e3f4abd8c")},
        {"title": "Action Camera 4K", "desc": "Waterproof 4K action camera with image stabilization", "price": 69.99, "img": unsplash("1502920917128-1aa500764cbd")},
        {"title": "Drone Mini Foldable", "desc": "Compact foldable drone with HD camera for aerial photography", "price": 99.99, "img": unsplash("1507582020474-9a35b7d455d9")},
        {"title": "Power Bank 20000mAh", "desc": "High capacity portable charger with fast charging", "price": 29.99, "img": unsplash("1609091839311-d5365f9ff1c5")},
        {"title": "Noise Cancelling Headphones", "desc": "Over-ear wireless headphones with premium noise cancellation", "price": 149.99, "img": unsplash("1505740420928-5e560c06d30e")},
        {"title": "Smart Thermostat", "desc": "WiFi thermostat that learns your schedule and saves energy", "price": 129.99, "img": unsplash("1558089687-f282d8b1b0d2")},
    ],
    "Music & Instruments": [
        {"title": "Beginner Ukulele Set", "desc": "Concert ukulele with carrying case, tuner, and picks", "price": 39.99, "img": unsplash("1510915361894-db8b60106cb1")},
        {"title": "Bluetooth Record Player", "desc": "Vintage-style turntable with Bluetooth and built-in speakers", "price": 69.99, "img": unsplash("1539375665275-f9de415ef9ac")},
        {"title": "Electronic Drum Pad", "desc": "Portable electronic drum pad for practice and performance", "price": 49.99, "img": unsplash("1519892300165-cb5542fb47c7")},
        {"title": "Guitar Capo & Picks Set", "desc": "Premium guitar capo with assorted picks and holder", "price": 14.99, "img": unsplash("1510915361894-db8b60106cb1")},
        {"title": "Music Theory Book", "desc": "Complete guide to music theory for beginners", "price": 19.99, "img": unsplash("1507838153414-b4b713384a76")},
        {"title": "Piano Keyboard 61 Keys", "desc": "Portable electronic keyboard with touch sensitive keys", "price": 89.99, "img": unsplash("1520523839897-bd3ef29e2e6c")},
        {"title": "Vinyl Record Gift Set", "desc": "Curated collection of classic vinyl records in a gift box", "price": 59.99, "img": unsplash("1539375665275-f9de415ef9ac")},
        {"title": "Spotify Gift Card $30", "desc": "Premium music streaming subscription gift card", "price": 30.00, "img": unsplash("1614680376593-902f74cf0d41")},
        {"title": "Harmonica Blues Set", "desc": "Professional blues harmonica in key of C with case", "price": 24.99, "img": unsplash("1511379938547-c1f69419868d")},
        {"title": "Music LED Visualizer", "desc": "LED panel that syncs with music for ambient light shows", "price": 34.99, "img": unsplash("1470225620780-dba8ba36b745")},
        {"title": "Acoustic Guitar Strings Set", "desc": "Premium phosphor bronze guitar strings — pack of 3 sets", "price": 16.99, "img": unsplash("1510915361894-db8b60106cb1")},
        {"title": "DJ Controller Beginner", "desc": "Compact DJ controller with jog wheels and mixer", "price": 99.99, "img": unsplash("1571330735066-03aaa9429d89")},
    ],
    "Art & Crafts": [
        {"title": "Watercolor Paint Set 48 Colors", "desc": "Professional watercolor palette with brushes and paper", "price": 34.99, "img": unsplash("1513364776144-60967b0f800f")},
        {"title": "Sketching Pencil Set", "desc": "Professional graphite and charcoal drawing pencils kit", "price": 19.99, "img": unsplash("1452860606245-08dfc9eee6d7")},
        {"title": "Adult Coloring Book Set", "desc": "Intricate mandala coloring book with premium colored pencils", "price": 24.99, "img": unsplash("1513364776144-60967b0f800f")},
        {"title": "Calligraphy Pen Kit", "desc": "Modern calligraphy starter kit with nibs, ink, and guidebook", "price": 29.99, "img": unsplash("1455390582262-044cdead277a")},
        {"title": "Pottery Clay Kit", "desc": "Air-dry clay with sculpting tools and paint — no kiln needed", "price": 27.99, "img": unsplash("1565193566173-7a0ee3dbe261")},
        {"title": "Canvas Painting Set", "desc": "Acrylic paint set with canvases, brushes, and palette", "price": 39.99, "img": unsplash("1460661419201-fd4cecdf8a8b")},
        {"title": "Macramé Kit Beginner", "desc": "DIY macramé wall hanging kit with cord and instructions", "price": 22.99, "img": unsplash("1596484552834-6a570a0ef614")},
        {"title": "Resin Art Starter Kit", "desc": "Epoxy resin kit with molds, pigments, and glitter", "price": 44.99, "img": unsplash("1513364776144-60967b0f800f")},
        {"title": "Origami Paper Set 500 Sheets", "desc": "Premium origami paper in vibrant colors with instruction book", "price": 15.99, "img": unsplash("1565193566173-7a0ee3dbe261")},
        {"title": "Embroidery Starter Kit", "desc": "Cross-stitch embroidery kit with hoop, fabric, and threads", "price": 18.99, "img": unsplash("1596484552834-6a570a0ef614")},
        {"title": "Oil Pastel Set 72 Colors", "desc": "Professional oil pastels for vibrant artwork", "price": 32.99, "img": unsplash("1460661419201-fd4cecdf8a8b")},
        {"title": "Diamond Painting Kit", "desc": "Relaxing diamond art mosaic painting with all supplies", "price": 21.99, "img": unsplash("1513364776144-60967b0f800f")},
    ],
    "Outdoor & Adventure": [
        {"title": "Camping Hammock", "desc": "Portable double hammock with tree straps for camping", "price": 29.99, "img": unsplash("1504280390367-361c6d9f38f4")},
        {"title": "Hiking Backpack 40L", "desc": "Lightweight waterproof hiking backpack with rain cover", "price": 49.99, "img": unsplash("1501555088652-021faa106b9b")},
        {"title": "LED Camping Lantern", "desc": "Rechargeable LED lantern with power bank function", "price": 24.99, "img": unsplash("1510312305653-8ed496efae75")},
        {"title": "Multitool Pocket Knife", "desc": "Stainless steel multi-function tool with 15 tools", "price": 29.99, "img": unsplash("1571115764595-644a1f56a55c")},
        {"title": "Insulated Water Bottle 32oz", "desc": "Double-wall vacuum insulated stainless steel bottle", "price": 24.99, "img": unsplash("1602143407151-7111542de6e8")},
        {"title": "Binoculars Compact 10x25", "desc": "Compact binoculars for bird watching and hiking", "price": 34.99, "img": unsplash("1516557070061-c3d1653fa646")},
        {"title": "Outdoor Solar Charger", "desc": "Portable solar panel charger for phones and devices", "price": 39.99, "img": unsplash("1509391366360-2e959784a276")},
        {"title": "Adventure Journal", "desc": "Guided adventure journal for documenting outdoor travels", "price": 18.99, "img": unsplash("1501555088652-021faa106b9b")},
        {"title": "Trekking Poles Pair", "desc": "Adjustable carbon fiber trekking poles for hikers", "price": 44.99, "img": unsplash("1551632811-561732d1e306")},
        {"title": "Fire Starter Kit", "desc": "Magnesium fire starter with waterproof tinder and whistle", "price": 12.99, "img": unsplash("1510312305653-8ed496efae75")},
        {"title": "Compact Sleeping Bag", "desc": "Lightweight 3-season sleeping bag with compression sack", "price": 39.99, "img": unsplash("1504280390367-361c6d9f38f4")},
        {"title": "Trail Mix Gift Box", "desc": "Premium assorted trail mix and dried fruit gift pack", "price": 22.99, "img": unsplash("1473093295043-cdd812d0e601")},
    ],
    "Sports & Fitness": [
        {"title": "Yoga Mat Premium", "desc": "Non-slip TPE eco-friendly yoga mat with carrying strap", "price": 29.99, "img": unsplash("1544367567-0f2fcb009e0b")},
        {"title": "Resistance Band Set", "desc": "5 levels of resistance bands with handles and door anchor", "price": 19.99, "img": unsplash("1598971457999-ca4ef48a9a71")},
        {"title": "Foam Roller Massage", "desc": "High-density foam roller for muscle recovery and stretching", "price": 24.99, "img": unsplash("1571019613454-1cb2f99b2d8b")},
        {"title": "Jump Rope Speed", "desc": "Adjustable speed jump rope with ball bearing handles", "price": 14.99, "img": unsplash("1434596922112-19cb4b4e813a")},
        {"title": "Dumbbell Set Adjustable", "desc": "Adjustable dumbbells from 5-25 lbs each with stand", "price": 79.99, "img": unsplash("1534438327276-14e5300c3a48")},
        {"title": "Running Armband Phone Holder", "desc": "Sweatproof armband for phone while running or exercising", "price": 12.99, "img": unsplash("1461896836934-bd45ea8b1cdb")},
        {"title": "Gym Bag Duffel", "desc": "Water-resistant gym duffel bag with shoe compartment", "price": 34.99, "img": unsplash("1553062407-98eeb64c6a62")},
        {"title": "Basketball Indoor/Outdoor", "desc": "Official size composite leather basketball", "price": 29.99, "img": unsplash("1519861531473-9200262188bf")},
        {"title": "Massage Gun Percussion", "desc": "Deep tissue massage gun with multiple speed settings", "price": 69.99, "img": unsplash("1571019613454-1cb2f99b2d8b")},
        {"title": "Swimming Goggles Anti-Fog", "desc": "UV protection anti-fog swimming goggles with case", "price": 16.99, "img": unsplash("1530549387789-4c1017266635")},
        {"title": "Fitness Tracker Band", "desc": "Slim fitness tracker with step counter and sleep monitor", "price": 24.99, "img": unsplash("1576243345927-3a891b6a2c54")},
        {"title": "Soccer Ball Official Size", "desc": "FIFA-quality match soccer ball with premium stitching", "price": 34.99, "img": unsplash("1551958219-acbc608c6377")},
    ],
    "Kitchen & Cooking": [
        {"title": "Cast Iron Skillet 12-inch", "desc": "Pre-seasoned cast iron skillet for versatile cooking", "price": 34.99, "img": unsplash("1556909114-f6e7ad7d3136")},
        {"title": "Electric Spice Grinder", "desc": "Stainless steel electric spice and coffee grinder", "price": 24.99, "img": unsplash("1556909114-f6e7ad7d3136")},
        {"title": "Japanese Chef Knife 8-inch", "desc": "High-carbon stainless steel chef knife with ergonomic handle", "price": 49.99, "img": unsplash("1593618998160-e34014e67546")},
        {"title": "Bamboo Cutting Board Set", "desc": "Set of 3 organic bamboo cutting boards", "price": 22.99, "img": unsplash("1556909212-d5b604d0c90d")},
        {"title": "Silicone Baking Mat Set", "desc": "Non-stick silicone baking mats — set of 3 sizes", "price": 16.99, "img": unsplash("1556909114-f6e7ad7d3136")},
        {"title": "Pour Over Coffee Set", "desc": "Glass pour-over coffee maker with filters and scale", "price": 34.99, "img": unsplash("1495474472287-4d71bcdd2085")},
        {"title": "Herb Garden Indoor Kit", "desc": "Indoor hydroponic herb garden with grow light", "price": 44.99, "img": unsplash("1466692476868-aef1dfb1e735")},
        {"title": "Pasta Making Machine", "desc": "Stainless steel hand-crank pasta maker with attachments", "price": 39.99, "img": unsplash("1556909114-f6e7ad7d3136")},
        {"title": "Cookbook — World Flavors", "desc": "Culinary journey through 50 countries with 200+ recipes", "price": 28.99, "img": unsplash("1466637574441-749b8f19452f")},
        {"title": "Spice Rack Gift Set", "desc": "20 premium spices in glass jars with wooden display rack", "price": 42.99, "img": unsplash("1596040033229-a9821ebd058d")},
        {"title": "Electric Milk Frother", "desc": "Handheld rechargeable milk frother for lattes and cappuccinos", "price": 14.99, "img": unsplash("1495474472287-4d71bcdd2085")},
        {"title": "Cocktail Shaker Set", "desc": "Professional bartender kit with shaker, strainer, and jigger", "price": 29.99, "img": unsplash("1551024709-8f23befc6f87")},
    ],
    "Wellness & Self-Care": [
        {"title": "Essential Oil Diffuser", "desc": "Ultrasonic aroma diffuser with LED mood lighting", "price": 29.99, "img": unsplash("1544161515-4ab6ce6db874")},
        {"title": "Aromatherapy Candle Set", "desc": "Luxury soy candles in lavender, vanilla, and eucalyptus", "price": 34.99, "img": unsplash("1602607688066-52e8e7eb47ce")},
        {"title": "Bath Bomb Gift Box", "desc": "12 organic bath bombs with essential oils and dried flowers", "price": 24.99, "img": unsplash("1570194065650-d99fb4d5e6ff")},
        {"title": "Jade Face Roller Set", "desc": "Natural jade roller and gua sha set for facial massage", "price": 19.99, "img": unsplash("1596755389378-c31d6a60be96")},
        {"title": "Meditation Cushion", "desc": "Buckwheat hull meditation zafu cushion with cover", "price": 39.99, "img": unsplash("1544161515-4ab6ce6db874")},
        {"title": "Sleep Mask Silk", "desc": "100% mulberry silk sleep mask with adjustable strap", "price": 14.99, "img": unsplash("1531353826977-0941b4779a1c")},
        {"title": "Gratitude Journal", "desc": "5-minute daily gratitude journal with prompts and inspiration", "price": 16.99, "img": unsplash("1544161515-4ab6ce6db874")},
        {"title": "Herbal Tea Collection", "desc": "Organic herbal tea sampler with 12 varieties", "price": 22.99, "img": unsplash("1556679343-c7306c1976bc")},
        {"title": "Acupressure Mat Set", "desc": "Spike mat and pillow for stress relief and back pain", "price": 29.99, "img": unsplash("1544161515-4ab6ce6db874")},
        {"title": "Spa Gift Basket", "desc": "Luxurious spa set with lotion, scrub, and plush robe", "price": 54.99, "img": unsplash("1570194065650-d99fb4d5e6ff")},
        {"title": "Weighted Blanket 15lbs", "desc": "Premium weighted blanket for deep pressure relaxation", "price": 59.99, "img": unsplash("1531353826977-0941b4779a1c")},
        {"title": "Essential Oil Set 12-Pack", "desc": "Pure essential oils: lavender, tea tree, peppermint, and more", "price": 26.99, "img": unsplash("1602607688066-52e8e7eb47ce")},
    ],
    "Stationery & Office": [
        {"title": "Fountain Pen Gift Set", "desc": "Elegant fountain pen with ink converter and gift box", "price": 34.99, "img": unsplash("1585336261022-8f5adc08e89d")},
        {"title": "Leather Journal Handmade", "desc": "Genuine leather-bound journal with handmade paper", "price": 29.99, "img": unsplash("1531346878377-a5be20888e57")},
        {"title": "Desk Organizer Bamboo", "desc": "Multi-compartment bamboo desk organizer with phone stand", "price": 24.99, "img": unsplash("1593062096033-9a26b09da705")},
        {"title": "Washi Tape Collection", "desc": "30 rolls of decorative washi tape in various patterns", "price": 16.99, "img": unsplash("1513364776144-60967b0f800f")},
        {"title": "Bullet Journal Starter Kit", "desc": "Dotted notebook with stencils, stickers, and fine liners", "price": 27.99, "img": unsplash("1531346878377-a5be20888e57")},
        {"title": "Desk Lamp LED Wireless", "desc": "Foldable LED desk lamp with wireless charging base", "price": 39.99, "img": unsplash("1507003211169-0a1dd7228f2d")},
        {"title": "Mechanical Pencil Set", "desc": "Premium Japanese mechanical pencils with lead refills", "price": 22.99, "img": unsplash("1585336261022-8f5adc08e89d")},
        {"title": "Personalized Notebook Set", "desc": "Set of 3 notebooks with custom monogram engraving", "price": 34.99, "img": unsplash("1531346878377-a5be20888e57")},
        {"title": "Desk Calendar Minimalist", "desc": "Sleek wooden perpetual desk calendar", "price": 18.99, "img": unsplash("1593062096033-9a26b09da705")},
        {"title": "Highlighter Set Pastel", "desc": "12 pastel color aesthetic highlighters in gift tin", "price": 14.99, "img": unsplash("1513364776144-60967b0f800f")},
    ],
    "Plant Lover": [
        {"title": "Succulent Garden Kit", "desc": "DIY succulent planting kit with 5 varieties and pots", "price": 34.99, "img": unsplash("1459411552884-841db9b3cc2a")},
        {"title": "Self-Watering Planter", "desc": "Modern ceramic self-watering planter for indoor plants", "price": 24.99, "img": unsplash("1463320726281-696a485928c7")},
        {"title": "Bonsai Tree Starter Kit", "desc": "Grow your own bonsai tree with seeds, soil, and tools", "price": 29.99, "img": unsplash("1567331711402-509c12c41959")},
        {"title": "Plant Mister Brass", "desc": "Vintage-style brass plant mister for indoor plants", "price": 18.99, "img": unsplash("1459411552884-841db9b3cc2a")},
        {"title": "Macramé Plant Hanger Set", "desc": "Set of 3 handmade macramé plant hangers", "price": 22.99, "img": unsplash("1485955900006-10f4d324d411")},
        {"title": "Terrarium Kit Complete", "desc": "Glass terrarium with plants, moss, and decorative stones", "price": 44.99, "img": unsplash("1416879595882-3373a0480b5b")},
        {"title": "Indoor Herb Garden", "desc": "Smart indoor garden with LED grow light for herbs", "price": 49.99, "img": unsplash("1466692476868-aef1dfb1e735")},
        {"title": "Plant Care Tool Set", "desc": "Mini gardening tool set with pruner, fork, and trowel", "price": 16.99, "img": unsplash("1416879595882-3373a0480b5b")},
        {"title": "Monstera Deliciosa Plant", "desc": "Live Monstera plant in decorative ceramic pot", "price": 39.99, "img": unsplash("1459411552884-841db9b3cc2a")},
        {"title": "Plant Dad/Mom Mug", "desc": "Ceramic mug with cute plant parent design", "price": 14.99, "img": unsplash("1463320726281-696a485928c7")},
    ],
    "Pet Lover": [
        {"title": "Interactive Dog Toy Ball", "desc": "Smart self-rolling ball toy for dogs with LED lights", "price": 24.99, "img": unsplash("1587300003388-59208cc962cb")},
        {"title": "Cat Tree Tower", "desc": "Multi-level cat tree with scratching posts and hammock", "price": 59.99, "img": unsplash("1545249390-6bdfa286032f")},
        {"title": "Pet Camera Treat Dispenser", "desc": "WiFi pet camera with two-way audio and treat tossing", "price": 49.99, "img": unsplash("1587300003388-59208cc962cb")},
        {"title": "Dog Bandana Set 4-Pack", "desc": "Reversible seasonal dog bandanas in assorted patterns", "price": 14.99, "img": unsplash("1535930749574-1399327ce78f")},
        {"title": "Pet Portrait Custom", "desc": "Custom digital pet portrait from photo — printable art", "price": 29.99, "img": unsplash("1587300003388-59208cc962cb")},
        {"title": "Cat Puzzle Feeder", "desc": "Interactive puzzle toy that makes mealtime fun for cats", "price": 19.99, "img": unsplash("1545249390-6bdfa286032f")},
        {"title": "Dog DNA Test Kit", "desc": "At-home dog DNA breed identification and health test", "price": 69.99, "img": unsplash("1587300003388-59208cc962cb")},
        {"title": "Pet Memory Book", "desc": "Beautiful keepsake journal to document your pet's life", "price": 22.99, "img": unsplash("1535930749574-1399327ce78f")},
        {"title": "Automatic Pet Water Fountain", "desc": "Filtered water fountain to keep pets hydrated", "price": 29.99, "img": unsplash("1545249390-6bdfa286032f")},
        {"title": "Dog Treat Baking Kit", "desc": "DIY dog treat making kit with molds and recipes", "price": 24.99, "img": unsplash("1587300003388-59208cc962cb")},
    ],
}

OCCASIONS = ["Birthday", "Anniversary", "Graduation", "Wedding"]
RELATIONSHIPS = ["Partner", "Friend", "Child"]


async def main():
    async with AsyncSessionLocal() as session:
        # Build category map
        cat_result = await session.execute(select(Category))
        cat_map: dict[str, int] = {c.name: c.id for c in cat_result.scalars().all()}

        # Create any missing categories
        for cat_name in GIFT_DATA.keys():
            if cat_name not in cat_map:
                new_cat = Category(name=cat_name)
                session.add(new_cat)
                await session.flush()
                cat_map[cat_name] = new_cat.id
                print(f"  Created category: {cat_name} (id={new_cat.id})")

        total = 0
        for cat_name, gifts in GIFT_DATA.items():
            cat_id = cat_map[cat_name]
            for g in gifts:
                gift = Gift(
                    title=g["title"],
                    description=g["desc"],
                    category_id=cat_id,
                    price=g["price"],
                    occasion=random.choice(OCCASIONS),
                    relationship=random.choice(RELATIONSHIPS),
                    image_url=g["img"],
                    product_url=None,
                    embedding=None,
                )
                session.add(gift)
                total += 1

        await session.commit()
        print(f"\n✅ Inserted {total} diverse gifts across {len(GIFT_DATA)} categories")
        
        # Show final counts
        for cat_name in GIFT_DATA.keys():
            cat_id = cat_map[cat_name]
            count_result = await session.execute(
                select(func.count(Gift.id)).where(Gift.category_id == cat_id)
            )
            count = count_result.scalar()
            print(f"  {cat_name}: {count} gifts")


if __name__ == "__main__":
    asyncio.run(main())
