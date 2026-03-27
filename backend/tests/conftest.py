"""
Pytest configuration and shared fixtures.
"""
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.models import User, UserRole, Category, Gift

# In-memory SQLite for tests (no pgvector support, so we mock vector ops)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create fresh database tables for each test."""
    # Note: SQLite doesn't support pgvector, so we remove vector column for unit tests
    async with test_engine.begin() as conn:
        # Create tables without vector column (SQLite compat)
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(_create_test_tables)

    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to the per-test db_session."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


def _create_test_tables(connection):
    """Create test tables without pgvector column."""
    from sqlalchemy import text
    # Ensure schema is always fresh; SQLite can keep old table definitions in the same engine.
    connection.execute(text("DROP TABLE IF EXISTS recommendations"))
    connection.execute(text("DROP TABLE IF EXISTS interactions"))
    connection.execute(text("DROP TABLE IF EXISTS gifts"))
    connection.execute(text("DROP TABLE IF EXISTS user_profiles"))
    connection.execute(text("DROP TABLE IF EXISTS categories"))
    connection.execute(text("DROP TABLE IF EXISTS rag_queries"))
    connection.execute(text("DROP TABLE IF EXISTS model_metrics"))
    connection.execute(text("DROP TABLE IF EXISTS users"))

    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL,
            email VARCHAR(255) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            provider VARCHAR(50),
            google_sub VARCHAR(255),
            avatar_url TEXT,
            given_name VARCHAR(120),
            family_name VARCHAR(120),
            locale VARCHAR(20),
            role VARCHAR(10) NOT NULL DEFAULT 'user',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(100) UNIQUE NOT NULL
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(255) NOT NULL,
            description TEXT,
            category_id INTEGER NOT NULL REFERENCES categories(id),
            price REAL NOT NULL,
            occasion VARCHAR(100),
            relationship VARCHAR(100),
            age_group VARCHAR(50),
            tags TEXT,
            image_url TEXT,
            product_url TEXT,
            embedding BLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            age VARCHAR(20),
            gender VARCHAR(50),
            hobbies TEXT,
            relationship VARCHAR(100),
            occasion VARCHAR(100),
            budget_min REAL,
            budget_max REAL,
            favorite_categories TEXT,
            occasions TEXT,
            gifting_for_ages TEXT,
            interests TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            gift_id INTEGER NOT NULL REFERENCES gifts(id),
            interaction_type VARCHAR(20) NOT NULL,
            rating REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            gift_id INTEGER NOT NULL REFERENCES gifts(id),
            score REAL NOT NULL,
            model_type VARCHAR(20) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS model_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name VARCHAR(100) NOT NULL,
            precision REAL NOT NULL,
            recall REAL NOT NULL,
            f1_score REAL NOT NULL,
            accuracy REAL NOT NULL,
            evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))
    connection.execute(text("""
        CREATE TABLE IF NOT EXISTS rag_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            query TEXT NOT NULL,
            response TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """))


@pytest_asyncio.fixture
async def sample_gifts_data() -> list[dict]:
    """Return sample gift data for testing."""
    return [
        {
            "id": 1,
            "title": "Leather Wallet",
            "description": "Premium slim leather bifold wallet",
            "category_name": "Accessories",
            "price": 45.99,
            "occasion": "Birthday",
            "relationship": "Friend",
        },
        {
            "id": 2,
            "title": "Yoga Mat",
            "description": "Non-slip eco-friendly exercise mat",
            "category_name": "Sports",
            "price": 59.99,
            "occasion": "Birthday",
            "relationship": "Partner",
        },
        {
            "id": 3,
            "title": "Cookbook",
            "description": "Modern cooking techniques for home chefs",
            "category_name": "Books",
            "price": 34.99,
            "occasion": "Christmas",
            "relationship": "Parent",
        },
        {
            "id": 4,
            "title": "Wireless Earbuds",
            "description": "Noise-cancelling Bluetooth audio earbuds",
            "category_name": "Electronics",
            "price": 129.99,
            "occasion": "Graduation",
            "relationship": "Friend",
        },
        {
            "id": 5,
            "title": "Scented Candle Set",
            "description": "Luxury soy wax candle collection",
            "category_name": "Home Decor",
            "price": 35.00,
            "occasion": "Housewarming",
            "relationship": "Colleague",
        },
        {
            "id": 6,
            "title": "Coffee Subscription",
            "description": "Monthly specialty coffee bean delivery",
            "category_name": "Food & Drink",
            "price": 39.99,
            "occasion": "Birthday",
            "relationship": "Colleague",
        },
        {
            "id": 7,
            "title": "Fitness Tracker",
            "description": "Smart wristband with health monitoring",
            "category_name": "Electronics",
            "price": 89.99,
            "occasion": "Graduation",
            "relationship": "Sibling",
        },
        {
            "id": 8,
            "title": "Plant Kit",
            "description": "Indoor herb garden starter kit",
            "category_name": "Gardening",
            "price": 39.99,
            "occasion": "Birthday",
            "relationship": "Sibling",
        },
    ]


@pytest_asyncio.fixture
async def sample_interactions_data() -> list[dict]:
    """Return sample interaction data for testing."""
    return [
        {"user_id": 1, "gift_id": 1, "interaction_type": "purchase", "rating": None},
        {"user_id": 1, "gift_id": 2, "interaction_type": "rating", "rating": 4.5},
        {"user_id": 1, "gift_id": 3, "interaction_type": "click", "rating": None},
        {"user_id": 2, "gift_id": 2, "interaction_type": "purchase", "rating": None},
        {"user_id": 2, "gift_id": 4, "interaction_type": "rating", "rating": 5.0},
        {"user_id": 2, "gift_id": 5, "interaction_type": "click", "rating": None},
        {"user_id": 3, "gift_id": 1, "interaction_type": "rating", "rating": 3.0},
        {"user_id": 3, "gift_id": 6, "interaction_type": "purchase", "rating": None},
        {"user_id": 4, "gift_id": 7, "interaction_type": "rating", "rating": 4.0},
        {"user_id": 4, "gift_id": 8, "interaction_type": "click", "rating": None},
        {"user_id": 5, "gift_id": 3, "interaction_type": "purchase", "rating": None},
        {"user_id": 5, "gift_id": 5, "interaction_type": "rating", "rating": 2.0},
        {"user_id": 6, "gift_id": 4, "interaction_type": "rating", "rating": 4.5},
        {"user_id": 6, "gift_id": 6, "interaction_type": "purchase", "rating": None},
        {"user_id": 7, "gift_id": 7, "interaction_type": "rating", "rating": 3.5},
        {"user_id": 7, "gift_id": 1, "interaction_type": "click", "rating": None},
        {"user_id": 8, "gift_id": 8, "interaction_type": "purchase", "rating": None},
        {"user_id": 8, "gift_id": 2, "interaction_type": "rating", "rating": 4.0},
    ]
