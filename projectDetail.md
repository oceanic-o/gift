# Gift Recommendation System - Project Detail

## 1. Project Summary
This project is a full-stack AI gift recommendation platform with:
- Frontend: React + Vite + TypeScript UI for onboarding, recommendation comparison, gift details, metrics, and admin dashboard.
- Backend: FastAPI + SQLAlchemy + recommendation services (Content, Collaborative, Hybrid, Knowledge, RAG).
- Database: PostgreSQL + pgvector for relational data and vector similarity search.
- Deployment style: Dockerized services for backend, frontend, and database.

The system takes user context inputs (`age`, `gender`, `relationship`, `occasion`, `budget range`, `hobbies`) and compares 5 model outputs side-by-side.

## 2. High-Level Architecture

### Frontend (`/frontend`)
- Stack: React 18, Vite 6, TypeScript, Tailwind CSS, Radix UI, Recharts.
- App flow is orchestrated in `src/app/App.tsx` with step-based screens:
  - `landing` -> `onboarding` -> `form` -> `card` -> `letter` -> `gift` -> `packaging` -> `result`
  - Admin users can open `admin` dashboard.
- API client: `src/lib/api/client.ts` with token-based auth (`Authorization: Bearer <JWT>`), retries, timeout, and centralized error handling.
- Recommendation UI:
  - Calls model comparison endpoint.
  - Renders per-model cards.
  - Opens detailed modal per gift with model metrics and charts.
  - Renders global model metrics history.

### Backend (`/backend`)
- Stack: FastAPI, async SQLAlchemy, Alembic, scikit-learn, pgvector, OpenAI SDK.
- Entry point: `app/main.py`.
- API prefix: `/api/v1`.
- Layered structure:
  - `app/api`: HTTP routes
  - `app/services`: business logic / recommendation orchestration
  - `app/repositories`: DB query layer
  - `app/models`: SQLAlchemy entities
  - `app/schemas`: request/response models
  - `app/core`: settings, security, database, logging, taxonomy

### Database
- Engine: PostgreSQL 16 + pgvector extension.
- Vector field: `gifts.embedding` (`vector(1536)`) with IVFFlat cosine index.
- Stores users, profiles, gifts, interactions, recommendations, RAG queries, evaluation metrics, and imported web gifts.

## 3. Functional Flow (How It Works)
1. User authenticates (local login/register or Google login).
2. User submits recommendation context from form.
3. Frontend calls `GET /api/v1/recommendations/compare`.
4. Backend runs all five model pipelines for the same input:
- Content-based (TF-IDF + embedding cosine blend)
- Collaborative (user-item similarity)
- Hybrid (weighted content + collaborative + knowledge)
- Knowledge-based (rules + keyword overlap)
- RAG (OpenAI + vector retrieval)
5. Backend returns per-model gifts and per-model metric objects.
6. Frontend renders each model card and gift-level detail modal (including confusion matrix-style metrics and score charts where available).
7. User interactions (`click`, `rating`, `purchase`) are stored and used for retraining/evaluation.
8. Admin can retrain, evaluate, ingest data, and inspect schema/stats from dashboard APIs.

## 4. Recommendation Models

### Content-Based
- File: `app/services/recommendation/content_based.py`
- Uses weighted text corpus (`title`, `description`, `occasion`, `relationship`, `tags`, `age_group`) + TF-IDF cosine similarity.
- If embeddings exist, blends TF-IDF score with embedding cosine score.
- Supports filters: occasion, relationship, category, age_group, tags, min/max price.

### Collaborative
- File: `app/services/recommendation/collaborative.py`
- Builds user-item matrix from interactions with weights:
  - purchase = 3
  - rating = 2 (scaled by rating)
  - click = 1
- Uses user-user cosine similarity and weighted aggregation.
- Includes diversity-aware re-ranking (MMR) and popularity fallback.

### Hybrid
- File: `app/services/recommendation/hybrid.py`
- Merges Content + Collaborative + Knowledge scores.
- Handles cold-start and redistributes weights when collaborative signal is weak.
- Applies additional demographic mismatch penalties.

### Knowledge-Based
- File: `app/services/recommendation/knowledge_based.py`
- Rule/keyword scoring using:
  - occasion match
  - relationship match
  - budget fit
  - hobby overlap
  - age/gender keyword bonus
  - combo bonuses

### RAG
- File: `app/services/rag/rag_service.py`
- Pipeline:
  - query embedding -> pgvector retrieval -> context build -> OpenAI chat completion.
- Stores query/response in `rag_queries`.
- Can ingest external web gift ideas (optional provider configs).

## 5. Evaluation & Metrics
- File: `app/services/evaluation/evaluator.py`
- Core evaluation:
  - 80/20 split
  - Precision, Recall, F1, Accuracy
  - Confusion Matrix
  - optional K-fold cross validation
- Metrics persisted in `model_metrics` table.
- Exposed to frontend for charts and historical trend display.

## 6. API Catalog
Base URL: `/api/v1`

### Auth
- `POST /auth/register` - create account
- `POST /auth/login` - login and receive JWT
- `POST /auth/google` - Google token login

### Users / Profile
- `GET /users/me/profile` - current user profile
- `PUT /users/me/profile` - create/update profile
- `POST /users/me/preferences` - save onboarding preferences
- `POST /users/me/password` - change password
- `GET /users/me/home-recommendations` - personalized home feed
- `GET /users/public-reviews?limit=` - public recent review cards for landing page

### Gifts / Categories
- `GET /gifts` - list gifts with filters (`occasion`, `relationship`, `min_price`, `max_price`, `category_id`, `skip`, `limit`)
- `GET /gifts/{gift_id}` - single gift
- `POST /gifts` - create gift (admin)
- `PUT /gifts/{gift_id}` - update gift (admin)
- `DELETE /gifts/{gift_id}` - delete gift (admin)
- `GET /categories` - list categories
- `POST /categories` - create category (admin)

### Recommendations / Interactions
- `POST /interactions` - record interaction (`click`, `rating`, `purchase`)
- `GET /recommendations` - standard personalized recommendations
- `GET /recommendations/minimal` - lightweight grid recommendations
- `GET /recommendations/{gift_id}/details` - gift details + per-gift metrics
- `GET /recommendations/compare` - run and compare all 5 models
- `GET /recommendations/metrics?limit=` - model metrics history (logged-in users)

### RAG
- `POST /rag/ask` - ask RAG advisor
- `POST /rag/embed-gifts` - generate embeddings for gifts

### Taxonomy
- `GET /taxonomy/hobbies`
- `GET /taxonomy/age-groups`
- `GET /taxonomy/relationships`
- `GET /taxonomy/occasions`
- `GET /taxonomy/genders`
- `GET /taxonomy/budgets`
- `GET /taxonomy/age-rules`

### Admin
- `GET /admin/stats`
- `GET /admin/metrics`
- `GET /admin/users`
- `DELETE /admin/users/{user_id}`
- `PATCH /admin/users/{user_id}/role`
- `GET /admin/interactions`
- `DELETE /admin/interactions/{interaction_id}`
- `POST /admin/gifts/import`
- `POST /admin/catalog/reset`
- `GET /admin/dataset/metadata`
- `GET /admin/db/schema`
- `POST /admin/db/query`
- `POST /admin/embeddings`
- `POST /admin/web-gifts/ingest`
- `POST /admin/retrain`
- `POST /admin/evaluate`
- `POST /admin/tune`
- `GET /admin/settings`
- `PATCH /admin/settings`

### Health / Root
- `GET /health`
- `GET /`

## 7. Database Schema

### Enum Types
- `userrole`: `admin`, `user`
- `interactiontype`: `click`, `rating`, `purchase`
- `modeltype`: `content_based`, `collaborative`, `hybrid`, `rag`, `knowledge_based`

### `users`
- `id` (PK)
- `name` (required)
- `email` (unique, indexed, required)
- `password_hash` (required)
- `provider`, `google_sub`, `avatar_url`, `given_name`, `family_name`, `locale`
- `role` (`userrole`, default `user`)
- `created_at`

Relationships:
- one-to-many: `interactions`, `recommendations`, `rag_queries`
- one-to-one: `user_profiles`

### `user_profiles`
- `id` (PK)
- `user_id` (FK -> users.id, unique)
- `age`, `gender`, `hobbies`, `relationship`, `occasion`
- `budget_min`, `budget_max`
- `favorite_categories` (JSON)
- `occasions` (JSON)
- `gifting_for_ages` (JSON)
- `interests` (JSON)
- `updated_at`

### `categories`
- `id` (PK)
- `name` (unique, indexed, required)

### `gifts`
- `id` (PK)
- `title` (indexed, required)
- `description`
- `category_id` (FK -> categories.id)
- `price` (>= 0)
- `occasion`, `relationship`, `age_group`, `tags`
- `image_url`, `product_url`
- `embedding` (`vector(1536)`, optional)
- `created_at`

Indexes:
- `(occasion, relationship)` composite index
- `embedding` IVFFlat cosine index

### `interactions`
- `id` (PK)
- `user_id` (FK -> users.id)
- `gift_id` (FK -> gifts.id)
- `interaction_type` (`interactiontype`)
- `rating` (required for `rating` type; 1..5)
- `timestamp`

### `recommendations`
- `id` (PK)
- `user_id` (FK -> users.id)
- `gift_id` (FK -> gifts.id)
- `score` (0..1)
- `model_type` (`modeltype`)
- `created_at`

### `web_gifts`
- `id` (PK)
- `gift_id` (FK -> gifts.id, unique)
- `source`, `source_url` (unique), `query`, `provider`, `raw_payload`
- `created_at`

### `model_metrics`
- `id` (PK)
- `model_name`
- `precision`, `recall`, `f1_score`, `accuracy`
- `evaluated_at`

### `rag_queries`
- `id` (PK)
- `user_id` (FK -> users.id)
- `query`, `response`
- `created_at`

## 8. Docker Services in Current Project
Defined in `backend/docker-compose.yml` and `frontend/docker-compose.yml`:
- `postgres` (pgvector image)
- `db-backup` (daily backup, keeps latest 2 dumps)
- `backend` (FastAPI)
- `pgadmin`
- `frontend` (Nginx serving Vite build)

## 9. Important Runtime Environment Variables

### Backend
- `DATABASE_URL`, `DATABASE_URL_SYNC`
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `OPENAI_API_KEY`, `OPENAI_EMBEDDING_MODEL`, `OPENAI_CHAT_MODEL`
- `OPENAI_RAG_EMBEDDING_MODEL`, `OPENAI_RAG_CHAT_MODEL`
- `CONTENT_WEIGHT`, `COLLABORATIVE_WEIGHT`, `KNOWLEDGE_WEIGHT`
- `BOOST_WEIGHT_HOBBIES`, `BOOST_WEIGHT_OCCASION`, `BOOST_WEIGHT_RELATIONSHIP`, `BOOST_WEIGHT_AGE`, `BOOST_WEIGHT_GENDER`, `BOOST_WEIGHT_PRICE`
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- `AUTO_EVALUATE_ON_STARTUP`

### Frontend
- `VITE_API_BASE_URL`
- `VITE_GOOGLE_CLIENT_ID`

## 10. Notes for Maintenance
- Recommendation quality depends heavily on interaction data (`interactions` table).
- For model comparison quality graphs, ensure regular evaluation runs (`POST /admin/evaluate`).
- RAG quality depends on embeddings availability (`POST /admin/embeddings` / `/rag/embed-gifts`) and valid OpenAI key.
