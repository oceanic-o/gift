# Azure Deployment Guide (Easy Path)

This guide deploys your project with:

- Frontend: Azure App Service (Docker image)
- Backend API: Azure App Service (Docker image)
- Database: Azure Database for PostgreSQL Flexible Server
- Images: Azure Container Registry (ACR)
- Domain: your purchased domain mapped to frontend and backend subdomains

Recommended domain mapping:

- Frontend: `www.yourdomain.com`
- Backend API: `api.yourdomain.com`
  yes

## 1. Prerequisites

- Azure subscription
- Azure CLI installed (`az --version`)
- A domain from any registrar (GoDaddy, Namecheap, Cloudflare, etc.)
- OpenAI API key for backend env

## 2. Set Variables

Run in terminal and replace placeholders:

```bash
# Azure basics
export SUBSCRIPTION_ID="<your-subscription-id>"
export RG="gift-rg"
export LOCATION="eastus"

# Names must be globally unique and lowercase
export ACR="giftacr12345"
export PLAN="gift-app-plan"
export BACKEND_APP="gift-api-12345"
export FRONTEND_APP="gift-web-12345"

# Postgres
export PG_SERVER="giftpg12345"
export PG_DB="giftdb"
export PG_ADMIN="giftadmin"
export PG_PASSWORD="<StrongPasswordHere>"

# App secrets
export OPENAI_API_KEY="<your-openai-key>"
export JWT_SECRET="<your-long-random-secret>"
```

## 3. Login and Create Core Azure Resources

```bash
az login
az account set --subscription "$SUBSCRIPTION_ID"

az group create --name "$RG" --location "$LOCATION"

az acr create \
  --resource-group "$RG" \
  --name "$ACR" \
  --sku Basic \
  --admin-enabled true

az appservice plan create \
  --name "$PLAN" \
  --resource-group "$RG" \
  --is-linux \
  --sku B1
```

## 4. Create PostgreSQL Flexible Server

```bash
az postgres flexible-server create \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --location "$LOCATION" \
  --admin-user "$PG_ADMIN" \
  --admin-password "$PG_PASSWORD" \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --version 16 \
  --storage-size 32 \
  --database-name "$PG_DB" \
  --public-access 0.0.0.0

# Allow Azure services to reach DB
az postgres flexible-server firewall-rule create \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --rule-name allow-azure \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

Enable pgvector extension once:

```bash
az postgres flexible-server execute \
  --resource-group "$RG" \
  --name "$PG_SERVER" \
  --database-name "$PG_DB" \
  --admin-user "$PG_ADMIN" \
  --admin-password "$PG_PASSWORD" \
  --querytext "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 5. Build and Push Docker Images to ACR

From project root (`/home/samundra/Documents/gift`):

```bash
# Build backend image in ACR
az acr build -r "$ACR" -t gift-backend:latest ./backend

# Get backend default URL for initial frontend build
BACKEND_URL="https://${BACKEND_APP}.azurewebsites.net/api/v1"

# Build frontend image with backend API URL baked in
az acr build \
  -r "$ACR" \
  -t gift-frontend:latest \
  --build-arg VITE_API_BASE_URL="$BACKEND_URL" \
  ./frontend
```

## 6. Create Backend and Frontend App Services (Containers)

```bash
ACR_USER=$(az acr credential show -n "$ACR" --query username -o tsv)
ACR_PASS=$(az acr credential show -n "$ACR" --query passwords[0].value -o tsv)
ACR_URL="https://${ACR}.azurecr.io"

# Backend app
az webapp create \
  --resource-group "$RG" \
  --plan "$PLAN" \
  --name "$BACKEND_APP" \
  --deployment-container-image-name "${ACR}.azurecr.io/gift-backend:latest"

az webapp config container set \
  --resource-group "$RG" \
  --name "$BACKEND_APP" \
  --container-image-name "${ACR}.azurecr.io/gift-backend:latest" \
  --container-registry-url "$ACR_URL" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"

# Frontend app
az webapp create \
  --resource-group "$RG" \
  --plan "$PLAN" \
  --name "$FRONTEND_APP" \
  --deployment-container-image-name "${ACR}.azurecr.io/gift-frontend:latest"

az webapp config container set \
  --resource-group "$RG" \
  --name "$FRONTEND_APP" \
  --container-image-name "${ACR}.azurecr.io/gift-frontend:latest" \
  --container-registry-url "$ACR_URL" \
  --container-registry-user "$ACR_USER" \
  --container-registry-password "$ACR_PASS"
```

## 7. Configure Backend App Settings

```bash
PG_HOST="${PG_SERVER}.postgres.database.azure.com"

az webapp config appsettings set \
  --resource-group "$RG" \
  --name "$BACKEND_APP" \
  --settings \
    WEBSITES_PORT=8000 \
    APP_NAME="Gift Recommendation System" \
    APP_VERSION="1.0.0" \
    DEBUG=false \
    SECRET_KEY="$JWT_SECRET" \
    ALGORITHM="HS256" \
    ACCESS_TOKEN_EXPIRE_MINUTES=60 \
    DATABASE_URL="postgresql+asyncpg://${PG_ADMIN}:${PG_PASSWORD}@${PG_HOST}:5432/${PG_DB}?ssl=require" \
    DATABASE_URL_SYNC="postgresql://${PG_ADMIN}:${PG_PASSWORD}@${PG_HOST}:5432/${PG_DB}?sslmode=require" \
    OPENAI_API_KEY="$OPENAI_API_KEY" \
    OPENAI_EMBEDDING_MODEL="text-embedding-3-small" \
    OPENAI_CHAT_MODEL="gpt-4o-mini" \
    OPENAI_RAG_EMBEDDING_MODEL="text-embedding-3-large" \
    OPENAI_RAG_CHAT_MODEL="gpt-4o" \
    ADMIN_EMAIL="admin@giftapp.com" \
    ADMIN_PASSWORD="ChangeThisAdminPassword123!"
```

Optional: if frontend is hosted on another domain and you need strict CORS, update CORS settings in backend code before production deploy.

## 8. Verify Deployment

```bash
# Backend health
curl "https://${BACKEND_APP}.azurewebsites.net/health"

# Frontend
echo "https://${FRONTEND_APP}.azurewebsites.net"
```

## 9. Link Your Custom Domain

Use two subdomains for clean separation:

- `www.yourdomain.com` -> frontend app
- `api.yourdomain.com` -> backend app

### 9.1 Get domain verification IDs

```bash
FRONT_VER_ID=$(az webapp show -g "$RG" -n "$FRONTEND_APP" --query customDomainVerificationId -o tsv)
BACK_VER_ID=$(az webapp show -g "$RG" -n "$BACKEND_APP" --query customDomainVerificationId -o tsv)

echo "$FRONT_VER_ID"
echo "$BACK_VER_ID"
```

### 9.2 Add DNS records at your domain provider

For `www.yourdomain.com`:

- `CNAME` record: `www` -> `${FRONTEND_APP}.azurewebsites.net`
- `TXT` record: `asuid.www` -> `<FRONT_VER_ID>`

For `api.yourdomain.com`:

- `CNAME` record: `api` -> `${BACKEND_APP}.azurewebsites.net`
- `TXT` record: `asuid.api` -> `<BACK_VER_ID>`

Wait for DNS propagation.

### 9.3 Bind hostnames to App Services

```bash
az webapp config hostname add -g "$RG" -n "$FRONTEND_APP" --hostname "www.yourdomain.com"
az webapp config hostname add -g "$RG" -n "$BACKEND_APP" --hostname "api.yourdomain.com"
```

### 9.4 Enable HTTPS certificates

Easiest way: Azure Portal

- App Service -> `Custom domains` -> select hostname -> `Add binding`
- Choose `App Service Managed Certificate` and bind via SNI SSL.

Repeat for both frontend and backend hostnames.

## 10. Rebuild Frontend Image with Final API Domain

After domain is active, rebuild frontend so it points to your API domain:

```bash
az acr build \
  -r "$ACR" \
  -t gift-frontend:latest \
  --build-arg VITE_API_BASE_URL="https://api.yourdomain.com/api/v1" \
  ./frontend

az webapp restart --resource-group "$RG" --name "$FRONTEND_APP"
```

## 11. Ongoing Ops (Recommended)

- Enable App Service log streaming and diagnostics.
- Use Azure Key Vault for secrets (instead of plain app settings).
- Keep PostgreSQL automatic backups enabled (default in Flexible Server).
- Use staging slots for zero-downtime updates (Standard plan and above).
- Add Azure Monitor alerts for CPU, memory, HTTP 5xx, and DB storage.
