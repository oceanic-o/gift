"""
Integration tests for API endpoints with auth, gifts CRUD, admin routes,
recommendations, and RAG — covering lines missed in test_api.py.

All tests use in-memory SQLite and mock out OpenAI/pgvector calls.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from app.main import app
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from app.models.models import UserRole

# ---------------------------------------------------------------------------
# Test DB setup — single shared engine so direct DB writes are visible to app
# ---------------------------------------------------------------------------

_TEST_DB_URL = "sqlite+aiosqlite:///:memory:"
_ext_engine = create_async_engine(_TEST_DB_URL, echo=False, connect_args={"check_same_thread": False})
_ExtSession = async_sessionmaker(_ext_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with _ExtSession() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


_SCHEMA_SQL = [
    """CREATE TABLE users (
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
    )""",
    """CREATE TABLE categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(100) UNIQUE NOT NULL
    )""",
    """CREATE TABLE gifts (
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
    )""",
    """CREATE TABLE interactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        gift_id INTEGER NOT NULL REFERENCES gifts(id),
        interaction_type VARCHAR(20) NOT NULL,
        rating REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        gift_id INTEGER NOT NULL REFERENCES gifts(id),
        score REAL NOT NULL,
        model_type VARCHAR(20) NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE model_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name VARCHAR(100) NOT NULL,
        precision REAL NOT NULL,
        recall REAL NOT NULL,
        f1_score REAL NOT NULL,
        accuracy REAL NOT NULL,
        evaluated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE rag_queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL REFERENCES users(id),
        query TEXT NOT NULL,
        response TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""",
]

_DROP_SQL = [
    "DROP TABLE IF EXISTS interactions",
    "DROP TABLE IF EXISTS recommendations",
    "DROP TABLE IF EXISTS rag_queries",
    "DROP TABLE IF EXISTS model_metrics",
    "DROP TABLE IF EXISTS gifts",
    "DROP TABLE IF EXISTS categories",
    "DROP TABLE IF EXISTS users",
]


@pytest_asyncio.fixture(autouse=True)
async def _setup_ext_db():
    async with _ext_engine.begin() as conn:
        for stmt in _DROP_SQL:
            await conn.execute(text(stmt))
        for stmt in _SCHEMA_SQL:
            await conn.execute(text(stmt))
    yield


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers — use the client (which goes through the override session)
# ---------------------------------------------------------------------------

async def _register(client, email="user@test.com", password="Pass1234!", name="Test"):
    resp = await client.post("/api/v1/auth/register", json={"name": name, "email": email, "password": password})
    return resp


async def _login(client, email, password):
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json().get("access_token")


async def _register_and_login(client, email="user@test.com", password="Pass1234!", name="Test"):
    await _register(client, email=email, password=password, name=name)
    return await _login(client, email, password)


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


async def _make_admin_in_db(client, email="admin@test.com", password="AdminPass1!"):
    """Register a user through the API then set their DB role to admin and return an admin token."""
    reg_resp = await _register(client, email=email, password=password, name="Admin")
    user_id = reg_resp.json()["id"]
    # Update the user's role to 'admin' directly in the DB
    async with _ExtSession() as session:
        await session.execute(
            text("UPDATE users SET role = 'admin' WHERE id = :uid"),
            {"uid": user_id},
        )
        await session.commit()
    token = create_access_token({"sub": str(user_id), "role": "admin"})
    return token, user_id


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/v1/auth/register", json={
        "name": "Alice",
        "email": "alice@test.com",
        "password": "SecurePass1!",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "alice@test.com"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(client):
    payload = {"name": "Bob", "email": "bob@test.com", "password": "SecurePass1!"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_login_success(client):
    await _register(client, "carol@test.com", "SecurePass1!", "Carol")
    token = await _login(client, "carol@test.com", "SecurePass1!")
    assert token is not None


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(client):
    await _register(client, "dave@test.com", "RightPass1!", "Dave")
    resp = await client.post("/api/v1/auth/login", json={
        "email": "dave@test.com",
        "password": "WrongPass1!",
    })
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Gift endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_gifts_empty(client):
    resp = await client.get("/api/v1/gifts/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_categories_empty(client):
    resp = await client.get("/api/v1/categories/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_category_requires_admin(client):
    token = await _register_and_login(client, "plain@test.com", "Pass1234!")
    assert token is not None
    resp = await client.post(
        "/api/v1/categories/",
        json={"name": "Books"},
        headers=_auth_headers(token),
    )
    # Regular user gets 403 Forbidden
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_gift_not_found_returns_404(client):
    resp = await client.get("/api/v1/gifts/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_gift_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "giftsadmin@test.com", "AdminPass1!")

    # Create category first
    resp = await client.post(
        "/api/v1/categories/",
        json={"name": "Gadgets"},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    cat_id = resp.json()["id"]

    # Create gift
    resp = await client.post(
        "/api/v1/gifts/",
        json={
            "title": "Smartwatch",
            "description": "A smart wearable",
            "category_id": cat_id,
            "price": 199.99,
            "occasion": "Birthday",
            "relationship": "Friend",
        },
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    gift_id = resp.json()["id"]
    assert resp.json()["title"] == "Smartwatch"

    # Get gift
    resp = await client.get(f"/api/v1/gifts/{gift_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "Smartwatch"


@pytest.mark.asyncio
async def test_update_gift_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "admin2@test.com", "AdminPass1!")

    # Create category + gift via API
    resp = await client.post(
        "/api/v1/categories/", json={"name": "UpdateCat"},
        headers=_auth_headers(admin_token)
    )
    cat_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/gifts/",
        json={"title": "Old Title", "category_id": cat_id, "price": 10.0},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    gift_id = resp.json()["id"]

    resp = await client.put(
        f"/api/v1/gifts/{gift_id}",
        json={"title": "New Title", "price": 25.0},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_gift_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "admin3@test.com", "AdminPass1!")

    resp = await client.post(
        "/api/v1/categories/", json={"name": "DelCat"},
        headers=_auth_headers(admin_token)
    )
    cat_id = resp.json()["id"]
    resp = await client.post(
        "/api/v1/gifts/",
        json={"title": "Delete Me", "category_id": cat_id, "price": 5.0},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 201
    gift_id = resp.json()["id"]

    resp = await client.delete(
        f"/api/v1/gifts/{gift_id}",
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/gifts/{gift_id}")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Interactions endpoint (FastAPI HTTPBearer returns 403 when no token at all)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_record_interaction_requires_auth(client):
    resp = await client.post("/api/v1/interactions", json={
        "gift_id": 1, "interaction_type": "click"
    })
    # HTTPBearer returns 401 when Authorization header is missing
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_record_interaction_gift_not_found(client):
    token = await _register_and_login(client, "intuser@test.com", "Pass1234!")
    resp = await client.post(
        "/api/v1/interactions",
        json={"gift_id": 99999, "interaction_type": "click"},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Recommendations endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_recommendations_requires_auth(client):
    resp = await client.get("/api/v1/recommendations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_recommendations_returns_list_when_trained(client):
    token = await _register_and_login(client, "recuser@test.com", "Pass1234!")

    mock_recommender = MagicMock()
    mock_recommender._trained = True
    mock_recommender.recommend.return_value = []

    with patch("app.services.recommendation_service.get_recommender", return_value=mock_recommender):
        resp = await client.get(
            "/api/v1/recommendations",
            headers=_auth_headers(token),
        )

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Admin endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_stats_requires_admin_role(client):
    token = await _register_and_login(client, "plain2@test.com", "Pass1234!")
    assert token is not None
    resp = await client.get("/api/v1/admin/stats", headers=_auth_headers(token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "statadmin@test.com", "AdminPass1!")
    resp = await client.get("/api/v1/admin/stats", headers=_auth_headers(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "total_gifts" in data


@pytest.mark.asyncio
async def test_admin_users_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "useradmin@test.com", "AdminPass1!")
    resp = await client.get("/api/v1/admin/users", headers=_auth_headers(admin_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_metrics_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "metadmin@test.com", "AdminPass1!")
    resp = await client.get("/api/v1/admin/metrics", headers=_auth_headers(admin_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_interactions_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "intadmin@test.com", "AdminPass1!")
    resp = await client.get("/api/v1/admin/interactions", headers=_auth_headers(admin_token))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_admin_retrain_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "retrainadmin@test.com", "AdminPass1!")

    mock_recommender = MagicMock()
    mock_recommender.train = AsyncMock()

    with patch("app.services.admin_service.get_recommender", return_value=mock_recommender):
        resp = await client.post("/api/v1/admin/retrain", headers=_auth_headers(admin_token))

    assert resp.status_code == 200
    assert "retrained" in resp.json()["message"].lower()


@pytest.mark.asyncio
async def test_admin_evaluate_as_admin(client):
    admin_token, _ = await _make_admin_in_db(client, "evaladmin@test.com", "AdminPass1!")

    mock_eval_result = MagicMock()
    mock_eval_result.model_dump.return_value = {
        "model_name": "hybrid", "precision": 0.0, "recall": 0.0,
        "f1_score": 0.0, "accuracy": 0.0,
    }
    mock_evaluator = AsyncMock()
    mock_evaluator.evaluate.return_value = mock_eval_result

    with patch("app.services.admin_service.RecommendationEvaluator", return_value=mock_evaluator):
        resp = await client.post("/api/v1/admin/evaluate", headers=_auth_headers(admin_token))

    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# RAG endpoint
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rag_ask_returns_result(client):
    token = await _register_and_login(client, "raguser@test.com", "Pass1234!")

    mock_rag_result = {"answer": "Here are some gifts...", "gifts": []}
    mock_rag_service = AsyncMock()
    mock_rag_service.ask.return_value = mock_rag_result

    with patch("app.api.v1.rag.RAGService", return_value=mock_rag_service):
        resp = await client.post(
            "/api/v1/rag/ask",
            json={"query": "What is a good birthday gift for my friend?"},
            headers=_auth_headers(token),
        )

    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rag_embed_gifts_requires_auth(client):
    # HTTPBearer returns 401 when no Authorization header is present
    resp = await client.post("/api/v1/rag/embed-gifts")
    assert resp.status_code == 401
