# 🎁 Gift Recommendation System: AI-Powered Personalization Engine

> **A State-of-the-Art Recommendation Platform combining Modern Web Technologies with Advanced AI Architectures.**

The **Gift Recommendation System** is not just a catalog; it is a sophisticated intelligence engine designed to solve the complex problem of gift-giving through personalized discovery. By leveraging a **Multi-Model Recommendation Architecture** and **Retrieval-Augmented Generation (RAG)**, it provides an unparalleled user experience that feels intuitive, smart, and human.

---

## 🔥 Key Innovations & Features

### 🧠 1. The 5-Engine AI Architecture
Most systems use one model; we use five. Each request is processed through multiple intelligence layers to ensure maximum relevance:
- **RAG (Retrieval-Augmented Generation)**: Uses LLMs (OpenAI) to "understand" the products and provide conversational, reasoned recommendations.
- **Hybrid Neural Logic**: A sophisticated blending of Content-Based (semantic similarity) and Collaborative Filtering (crowd wisdom).
- **Knowledge-Based Filtering**: High-precision rule-matching for strict occasion and budget constraints.
- **Vector Search (pgvector)**: Leveraging high-dimensional embeddings to find gifts based on *meaning*, not just keywords.

### 🎭 2. Immersive Visual Experience
- **3D Packaging Animation**: A premium, multi-stage wrapping animation that creates a moment of delight and anticipation.
- **Modern Glassmorphic UI**: Built with React, Radix UI, and Tailwind CSS for a sleek, premium, and responsive experience.
- **Dynamic Onboarding**: Personalized user journey that adapts the interface immediately based on user gifting style.

### 📊 3. Enterprise-Grade Admin Control
- **Real-time Analytics Dashboard**: Monitor user engagement, interaction heatmaps, and system growth.
- **Automated Model Evaluation**: Built-in tools to calculate Precision, Recall, and F1-scores for every recommendation model.
- **Data Life-cycle Management**: Integrated tools for JSON imports, AI embedding generation, and automated database backups.

### 🔐 4. Secure & Scalable Infrastructure
- **Full Docker Orchestration**: One-command deployment for the entire stack (PostgreSQL, FastAPI, Node.js, pgAdmin, DB-Backup).
- **State-of-the-Art Security**: JWT Authentication with Google OAuth 2.0 integration and encrypted password hashing.
- **Azure Cloud Optimized**: Specifically architected for seamless deployment on **Azure Virtual Machines** and **Azure App Service**.

---

## � 5. Live Cloud Deployment

This project is engineered for high availability and is **actively deployed on an Azure Virtual Machine**.

- **High Availability**: Served via Nginx reverse proxy for high-performance traffic handling.
- **Continuous Deployment**: Integrated with Azure pipelines for seamless updates.
- **Secure Access**: Configured with SSL/TLS encryption via Cloudflare and Let's Encrypt.

> **Note**: For access to the live development instance or more details on the Azure infrastructure, please refer to our [Azure Runbook](README_AZURE_VM_CLOUDFLARE_DEPLOY.md).

---

## �🏗️ 6. Technical Stack

| Category | Technology |
|---|---|
| **Backend** | Python (FastAPI), SQLAlchemy (SQLAlchemy 2.0), Alembic |
| **Frontend** | React, Vite, TypeScript, Tailwind CSS, Radix UI |
| **AI/ML** | OpenAI (GPT-4o / Text-Embeddings), scikit-learn, pgvector |
| **Database** | PostgreSQL 16 (Relational + Vector Store) |
| **DevOps** | Docker, Docker Compose, Nginx |

---

## 🚀 Getting Started

To experience the power of the Gift Recommendation System in your local environment, follow our comprehensive setup guide.

### [👉 View the Full Setup Guide (Recommended)](setup_guide.md)

**Quick Start (Docker):**
```bash
# 1. Start the Backend & Database
cd backend && docker compose up -d --build

# 2. Start the Frontend
cd ../frontend && docker compose up -d --build

# 3. Populate Database (Critical Step)
cd ../backend && bash scripts/restore_db.sh backups/giftdb_20260328_053103.dump
```

---

## 📖 Deep Dives

- **[Backend Architecture](backend/README.md)** — Explaining the 5 AI models and the pgvector database logic.
- **[Frontend UX Journey](frontend/README.md)** — Details on the user flow, animations, and state management.

---

