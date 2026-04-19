# Gift Recommendation System - Setup Guide

This guide provide detailed, step-by-step instructions to set up the Gift Recommendation System.

## 📋 Prerequisites

Ensure you have the following installed:
- **Docker & Docker Compose**: (Recommended) [Install here](https://docs.docker.com/get-docker/)
- **Python 3.11+**: [Install here](https://www.python.org/downloads/)
- **Node.js 20+**: [Install here](https://nodejs.org/)

---

## 🔑 1. API Keys & External Services

The system requires two main external configurations to function fully.

### A. OpenAI API Key (Required for AI Recommendations)
1.  Go to [platform.openai.com](https://platform.openai.com/).
2.  Sign in or create an account.
3.  Go to **API Keys** and click **Create new secret key**.
4.  Copy the key (it starts with `sk-...`).
5.  **Usage**: Paste this into `backend/.env` as `OPENAI_API_KEY`.

### B. Google OAuth Client ID (Optional — for Google Login)
1.  Go to [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project.
3.  Go to **APIs & Services > Credentials**.
4.  Click **Create Credentials > OAuth client ID**.
5.  Select **Web application**.
6.  Add `http://localhost:3000` to **Authorized JavaScript origins**.
7.  Add `http://localhost:3000` to **Authorized redirect URIs**.
8.  Copy the **Client ID**.
9.  **Usage**: Paste this into `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`.

---

## 🐳 2. Docker Setup (Main Method)

### Step 1: Initialize Environment Files
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```
Update `backend/.env` with your `OPENAI_API_KEY` and a random `SECRET_KEY`.

### Step 2: Start the Services
```bash
# Start backend first (it creates the network)
cd backend
docker compose up -d --build

# Wait 5 seconds, then start frontend
cd ../frontend
docker compose up -d --build
```

### Step 3: Populate Database from Backup
To get all the existing gift data and profiles, you **must** restore from a backup:
```bash
cd backend
# Use the latest dump file from the backups/ folder
bash scripts/restore_db.sh backups/giftdb_20260328_053103.dump
```
*Type 'yes' when prompted. This will populate all tables with the project data.*

### Step 4: Verify
- **Frontend**: [http://localhost:3000](http://localhost:3000)
- **API Docs**: [http://localhost:8001/docs](http://localhost:8001/docs) (Backend port in Docker is 8001)

---

## 🛠️ 3. Local Setup (Manual Method)

### Backend Setup
1.  `cd backend`
2.  `python -m venv .venv` && `source .venv/bin/activate`
3.  `pip install -r requirements.txt`
4.  Ensure a local PostgreSQL (with `pgvector` extension) is running.
5.  `alembic upgrade head`
6.  `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`

### Frontend Setup
1.  `cd frontend`
2.  `npm install`
3.  `npm run dev` (Runs on [http://localhost:5173](http://localhost:5173))

---

## 📊 Database Management

- **Generating AI Embeddings**: If you add new gifts manually, you must generate their "meaning fingerprints" (embeddings) for the AI model to find them:
  ```bash
  docker exec -it gift_backend python app/main.py --embed-gifts
  # OR use the Admin Dashboard UI -> Data Tools -> Generate Embeddings
  ```
- **PgAdmin**: Access [http://localhost:5050](http://localhost:5050) with `admin@giftapp.com` / `AdminSecurePass123!`.

---

## 🔍 Troubleshooting

- **Check Logs**: `docker compose logs -f backend` (in the `backend/` directory).
- **Network Errors**: Ensure `VITE_API_BASE_URL` in `frontend/.env` is `http://localhost:8001/api/v1` for Docker.
