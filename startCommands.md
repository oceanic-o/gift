# Start Commands (Local + Azure)

This file is command-only quick reference.

## A) Local Run Commands

### 1. Go to project
```bash
cd /home/samundra/Documents/gift
```

### 2. Create env files (first time only)
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### 3. Set required values
- In `backend/.env`: set `OPENAI_API_KEY` and `SECRET_KEY`
- In `frontend/.env`: set
```bash
VITE_API_BASE_URL=http://localhost:8001/api/v1
```

### 4. Start backend stack first
```bash
cd backend
docker compose up -d --build
```

### 5. Start frontend stack
```bash
cd ../frontend
docker compose up -d --build
```

### 6. Open URLs
- Frontend: `http://localhost:3000`
- Backend API docs: `http://localhost:8001/docs`
- Backend health: `http://localhost:8001/health`
- PgAdmin: `http://localhost:5050`

### 7. Logs
```bash
cd /home/samundra/Documents/gift/backend
docker compose logs -f backend

cd /home/samundra/Documents/gift/frontend
docker compose logs -f frontend
```

### 8. Stop
```bash
cd /home/samundra/Documents/gift/frontend
docker compose down

cd /home/samundra/Documents/gift/backend
docker compose down
```

## B) Azure VM Run Commands (Public IP)

### 1. Start services on VM
```bash
cd ~/gift/backend
docker compose up -d --build

cd ~/gift/frontend
docker compose up -d --build
```

### 2. Verify from VM
```bash
curl http://localhost:8001/health
```

### 3. Verify from your laptop/browser
Use VM public IP:
- Frontend: `http://<VM_PUBLIC_IP>:3000`
- Backend docs: `http://<VM_PUBLIC_IP>:8001/docs`
- Backend health: `http://<VM_PUBLIC_IP>:8001/health`

### 4. Update frontend API URL on VM (if IP changed)
```bash
cd ~/gift
sed -i 's|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://<VM_PUBLIC_IP>:8001/api/v1|' frontend/.env

cd ~/gift/frontend
docker compose up -d --build
```

### 5. Restart commands
```bash
cd ~/gift/backend && docker compose restart
cd ~/gift/frontend && docker compose restart
```

### 6. Stop commands
```bash
cd ~/gift/frontend && docker compose down
cd ~/gift/backend && docker compose down
```

## C) Optional: Reset Everything (Local or VM)
Use only when needed.

```bash
cd /home/samundra/Documents/gift/frontend && docker compose down -v
cd /home/samundra/Documents/gift/backend && docker compose down -v

docker system prune -f
```
