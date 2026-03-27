# Simple Azure Deployment (No Domain, Public IP Access)

This method deploys your full Dockerized project on one Azure Ubuntu VM and lets you access it directly by VM public IP.

You will get:
- Frontend: `http://<VM_PUBLIC_IP>:3000`
- Backend API: `http://<VM_PUBLIC_IP>:8001`
- API docs: `http://<VM_PUBLIC_IP>:8001/docs`
- PgAdmin: `http://<VM_PUBLIC_IP>:5050`

## 1. Create Azure VM
Run these from your local machine:

```bash
az login

# Variables
RG="gift-rg"
LOCATION="eastus"
VM_NAME="gift-vm"
ADMIN_USER="azureuser"

# Create resource group
az group create --name "$RG" --location "$LOCATION"

# Create VM (Ubuntu)
az vm create \
  --resource-group "$RG" \
  --name "$VM_NAME" \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username "$ADMIN_USER" \
  --generate-ssh-keys

# Open required ports
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 22
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 3000
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 8001
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 5050

# Get public IP
PUBLIC_IP=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)
echo "$PUBLIC_IP"
```

## 2. Install Docker + Compose on VM
SSH into VM:

```bash
ssh ${ADMIN_USER}@${PUBLIC_IP}
```

Inside VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release git

# Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Allow non-root docker usage
sudo usermod -aG docker $USER
newgrp docker

docker --version
docker compose version
```

## 3. Copy Project to VM
Option A (recommended): use git clone on VM.

```bash
# On VM
cd ~
git clone <YOUR_REPO_URL> gift
cd gift
```

Option B: copy current local folder to VM.

```bash
# Run on your local machine
scp -r /home/samundra/Documents/gift ${ADMIN_USER}@${PUBLIC_IP}:~/gift
```

## 4. Prepare Environment Files
On VM inside project root (`~/gift`):

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit backend env and set at least:
- `OPENAI_API_KEY=<your_key>`
- `SECRET_KEY=<strong_random_string>`
- keep DB URLs as default for docker-compose internal postgres

Edit frontend env:
- `VITE_API_BASE_URL=http://<VM_PUBLIC_IP>:8001/api/v1`
- `VITE_GOOGLE_CLIENT_ID=` (optional)

## 5. Start Backend Then Frontend

```bash
# Start backend stack first (postgres, backend, pgadmin, backup)
cd ~/gift/backend
docker compose up -d --build

# Start frontend stack
cd ~/gift/frontend
docker compose up -d --build
```

## 6. Verify

```bash
# Backend health
curl http://<VM_PUBLIC_IP>:8001/health

# Backend docs
# open in browser: http://<VM_PUBLIC_IP>:8001/docs

# Frontend
# open in browser: http://<VM_PUBLIC_IP>:3000
```

## 7. Useful Commands (VM)

```bash
# Check containers
docker ps

# Logs
cd ~/gift/backend && docker compose logs -f backend
cd ~/gift/frontend && docker compose logs -f frontend

# Restart
cd ~/gift/backend && docker compose restart
cd ~/gift/frontend && docker compose restart

# Stop all
cd ~/gift/frontend && docker compose down
cd ~/gift/backend && docker compose down
```

## 8. Important Notes
- This is the fastest deployment path for submission/demo.
- Access is HTTP on open ports (not HTTPS).
- If you need HTTPS and single URL later, add Nginx + SSL (or move to Azure App Service + custom domain).
