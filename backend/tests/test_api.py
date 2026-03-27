"""
Integration Tests: API Endpoints (using httpx + in-memory SQLite)

Note: These tests mock the database dependency to avoid PostgreSQL/pgvector
requirements in CI/CD. For full integration tests, use a real test database.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.models.models import UserRole

# ---------------------------------------------------------------------------
# In-memory SQLite engine for API tests (no pgvector)
# ---------------------------------------------------------------------------
_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_test_engine = create_async_engine(_TEST_DB_URL, echo=False)
_TestSession = async_sessionmaker(_test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    """FastAPI dependency override: use in-memory SQLite instead of PostgreSQL."""
    async with _TestSession() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _setup_test_db():
    """Create tables in the SQLite test DB before each test, drop after."""
    from sqlalchemy import text
    async with _test_engine.begin() as conn:
        # Drop & recreate minimal schema (no pgvector Vector column)
        await conn.execute(text("DROP TABLE IF EXISTS interactions"))
        await conn.execute(text("DROP TABLE IF EXISTS recommendations"))
        await conn.execute(text("DROP TABLE IF EXISTS rag_queries"))
        await conn.execute(text("DROP TABLE IF EXISTS model_metrics"))
        await conn.execute(text("DROP TABLE IF EXISTS gifts"))
        await conn.execute(text("DROP TABLE IF EXISTS categories"))
        await conn.execute(text("DROP TABLE IF EXISTS users"))
        await conn.execute(text("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(10) NOT NULL DEFAULT 'user',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
        await conn.execute(text("""
            CREATE TABLE categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name VARCHAR(100) UNIQUE NOT NULL
            )"""))
        await conn.execute(text("""
            CREATE TABLE gifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title VARCHAR(255) NOT NULL,
                description TEXT,
                category_id INTEGER NOT NULL REFERENCES categories(id),
                price REAL NOT NULL,
                occasion VARCHAR(100),
                relationship VARCHAR(100),
                image_url TEXT,
                product_url TEXT,
                embedding BLOB,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
        await conn.execute(text("""
            CREATE TABLE interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                gift_id INTEGER NOT NULL REFERENCES gifts(id),
                interaction_type VARCHAR(20) NOT NULL,
                rating REAL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
        await conn.execute(text("""
            CREATE TABLE recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                gift_id INTEGER NOT NULL REFERENCES gifts(id),
                score REAL NOT NULL,
                model_type VARCHAR(20) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
        await conn.execute(text("""
            CREATE TABLE model_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name VARCHAR(100) NOT NULL,
                precision REAL NOT NULL,
                recall REAL NOT NULL,
                f1_score REAL NOT NULL,
                accuracy REAL NOT NULL,
                evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
        await conn.execute(text("""
            CREATE TABLE rag_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id),
                query TEXT NOT NULL,
                response TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )"""))
    yield


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    """Health endpoint should return 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    """Root endpoint should return welcome message."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "docs" in data


@pytest.mark.asyncio
async def test_openapi_docs_available(client):
    """OpenAPI documentation should be accessible."""
    response = await client.get("/docs")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_register_invalid_email(client):
    """Registration with invalid email should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": "not-an-email", "password": "Password123!"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_auth_register_short_password(client):
    """Registration with short password should return 422."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": "test@example.com", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_recommendations_requires_auth(client):
    """Recommendations endpoint should require authentication (401 = no credentials)."""
    response = await client.get("/api/v1/recommendations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_interactions_requires_auth(client):
    """Interactions endpoint should require authentication (401 = no credentials)."""
    response = await client.post(
        "/api/v1/interactions",
        json={"gift_id": 1, "interaction_type": "click"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_requires_auth(client):
    """Admin stats should require authentication (401 = no credentials)."""
    response = await client.get("/api/v1/admin/stats")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_admin_evaluate_requires_auth(client):
    """Admin evaluate should require authentication (401 = no credentials)."""
    response = await client.post("/api/v1/admin/evaluate")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_gifts_list_public(client):
    """Gift list should be publicly accessible (returns 200 or requires no auth)."""
    # This will likely fail due to DB not being set up in unit tests
    # but the route itself should be reachable (no 401/403)
    response = await client.get("/api/v1/gifts/")
    # Either 200 (success) or 500 (DB error in test env) — not an auth error
    assert response.status_code not in (401, 403)


@pytest.mark.asyncio
async def test_rag_ask_requires_auth(client):
    """RAG ask endpoint should require authentication (401 = no credentials)."""
    response = await client.post(
        "/api/v1/rag/ask",
        json={"query": "What gift should I get for my mom?"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    """Invalid token should return 401."""
    response = await client.get(
        "/api/v1/recommendations",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
