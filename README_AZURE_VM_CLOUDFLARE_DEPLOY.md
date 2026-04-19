# Azure VM + Cloudflare Deployment Runbook

This guide deploys the full project to one Azure Ubuntu VM, serves it over `https` behind Nginx, and connects your Cloudflare domain.

Recommended hostnames:
- `gift.yourdomain.com` -> frontend
- `api.yourdomain.com` -> backend API

## Quick Copy-Paste (Fish Shell, Central India)

Use one section at a time.

### Section 1: Set subscription and variables
```fish
set SUB 19589111-1a6c-4f61-8c31-6d2c939b8c33
az account set --subscription $SUB

set RG gift-rg
set VM gift-vm
set USER azureuser
set LOC centralindia
set SIZE Standard_D2s_v3
```

### Section 2A: Recreate resource group (use this if group already exists in wrong region)

```fish
az group delete -n $RG --yes --no-wait
az group wait -n $RG --deleted
az group create -n $RG -l $LOC
```

### Section 2B: Create resource group (use this if group does not exist)

```fish
az group create -n $RG -l $LOC
```

### Section 3: Create VM (single line)

```fish
az vm create -g $RG -n $VM -l $LOC --image Ubuntu2204 --size $SIZE --admin-username $USER --generate-ssh-keys
```

### Section 4: Open ports

```fish
az vm open-port -g $RG -n $VM --port 22
az vm open-port -g $RG -n $VM --port 80
az vm open-port -g $RG -n $VM --port 443
```

### Section 5: Get public IP

```fish
set IP (az vm show -d -g $RG -n $VM --query publicIps -o tsv)
echo $IP
```

### Section 6: SSH to VM

```fish
ssh $USER@$IP
```

## 1. Prerequisites
- Azure subscription + `az` CLI
- Cloudflare-managed domain
- SSH keypair
- OpenAI API key

## 2. Create VM and open only required ports
Run locally:

```bash
az login

RG="gift-rg"
LOCATION="eastus"
VM_NAME="gift-vm"
ADMIN_USER="azureuser"

az group create --name "$RG" --location "$LOCATION"

az vm create \
  --resource-group "$RG" \
  --name "$VM_NAME" \
  --image Ubuntu2204 \
  --size Standard_B2s \
  --admin-username "$ADMIN_USER" \
  --generate-ssh-keys

# Open SSH + web only
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 22
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 80
az vm open-port --resource-group "$RG" --name "$VM_NAME" --port 443

PUBLIC_IP=$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv)
echo "$PUBLIC_IP"
```

## 3. Install Docker + Compose + Nginx on VM
SSH in:

```bash
ssh ${ADMIN_USER}@${PUBLIC_IP}
```

On VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release git nginx

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
$(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker
```

## 4. Copy project + configure env
On VM:

```bash
cd ~
git clone <YOUR_REPO_URL> gift
cd gift
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Set backend env (`backend/.env`) at minimum:
- `OPENAI_API_KEY=<your_key>`
- `SECRET_KEY=<long_random_secret>`
- `ADMIN_EMAIL`, `ADMIN_PASSWORD`
- keep DB URLs as docker defaults unless customized

Set frontend env (`frontend/.env`):

```bash
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1
```

## 5. Start app containers
On VM:

```bash
cd ~/gift/backend
docker compose up -d --build

cd ~/gift/frontend
docker compose up -d --build
```

Verify locally on VM first:

```bash
curl http://localhost:8001/health
curl -I http://localhost:3000
```

## 6. Configure Nginx reverse proxy
Create config:

```bash
sudo tee /etc/nginx/sites-available/gift.conf >/dev/null <<'NGINX'
server {
    listen 80;
    server_name gift.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/gift.conf /etc/nginx/sites-enabled/gift.conf
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

## 7. Cloudflare DNS mapping
In Cloudflare DNS:
- Add `A` record: `gift` -> `<PUBLIC_IP>`
- Add `A` record: `api` -> `<PUBLIC_IP>`

Start with `DNS only` (gray cloud) for first verification.
After traffic works, switch to `Proxied` (orange cloud).

## 8. TLS / SSL mode
Recommended:
1. In Cloudflare SSL/TLS, set mode to `Full` first.
2. Install certificate on origin (VM), then switch to `Full (strict)`.

Simple origin cert path:
- Create Cloudflare Origin Certificate for `gift.yourdomain.com` and `api.yourdomain.com`.
- Install cert/key on VM and add HTTPS server blocks in Nginx.

If you prefer Let’s Encrypt instead:

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d gift.yourdomain.com -d api.yourdomain.com
```

## 9. Deployment verification checklist
Run:

```bash
# backend health via domain
curl https://api.yourdomain.com/health

# docs reachable
curl -I https://api.yourdomain.com/docs

# frontend reachable
curl -I https://gift.yourdomain.com
```

Manual checks:
- login/register works
- recommendations load on landing page
- admin retrain and evaluate complete
- final page download PDF contains gift details + card + letter
- share via email opens mail client tab

## 10. Update / redeploy
On VM:

```bash
cd ~/gift
git pull

cd ~/gift/backend
docker compose up -d --build

cd ~/gift/frontend
docker compose up -d --build
```

## 11. Logs and troubleshooting

```bash
cd ~/gift/backend && docker compose logs -f backend
cd ~/gift/frontend && docker compose logs -f frontend
sudo journalctl -u nginx -f
```

Common issues:
- Cloudflare proxied + non-standard ports (`3000`, `8001`) does not work reliably for web app traffic. Use Nginx on `80/443`.
- Wrong `VITE_API_BASE_URL` causes frontend to call old IP/domain.
- `401` after login means stale browser token; clear local storage and retry.

## 12. Security hardening before production
- Keep only ports `22`, `80`, `443` open on Azure NSG.
- Do not expose postgres/pgadmin publicly.
- Rotate `SECRET_KEY`, admin password, and API keys.
- Restrict backend CORS origins to your frontend domain.
- Add periodic backups for postgres volume/data.
