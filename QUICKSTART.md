# Quick Start Guide

## Development Setup (5 min)

### 1. Clone & Install

```bash
cd llm-optimization-lab
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Backend

```bash
# Terminal 1
cd backend
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` → Swagger UI for API docs.

### 3. Start Frontend

```bash
# Terminal 2
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000` → dashboard.

### 4. Run Tests

```bash
# Terminal 3
python -m pytest tests/ -v
```

---

## Production Deployment (Docker)

### One Command

```bash
docker-compose up --build
```

- Backend: http://localhost:8000
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Stop

```bash
docker-compose down
```

---

## Cloud Deployment

### AWS EC2

```bash
# SSH into instance
ssh -i key.pem ubuntu@instance-ip

# Install Docker
curl -fsSL https://get.docker.com | sh
docker-compose up -d
```

### Heroku

```bash
heroku create llm-optimization-lab
git push heroku main
heroku logs --tail
```

### Google Cloud Run

```bash
gcloud run deploy \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## What's Running

| Service | URL | Purpose |
| --- | --- | --- |
| Backend API | http://localhost:8000 | FastAPI service with 6 demo endpoints |
| OpenAPI Docs | http://localhost:8000/docs | Auto-generated API documentation |
| Frontend | http://localhost:3000 | React dashboard to interact with demos |

---

## Common Commands

```bash
# Backend only (for development)
cd backend && uvicorn main:app --reload

# Frontend only
cd frontend && npm run dev

# Run linter
python -m ruff check llm_lab backend

# Build Docker images without running
docker-compose build

# See logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Rebuild and restart
docker-compose restart
```

---

## Environment Variables

**Backend** (`backend/config.py`):
- `ENVIRONMENT` = `development` or `production`
- `LOG_LEVEL` = `debug`, `info`, `warning`, `error`

**Frontend** (`.env`):
- `VITE_API_URL` = API endpoint (default: `http://localhost:8000`)

---

## Next Steps

1. ✅ **Run the app locally** — see all 6 demos working
2. ✅ **Deploy to cloud** — prove it works in production
3. ✅ **Show on GitHub** — link to this repo on your resume
4. ✅ **Explain the stack** — highlight full-stack skills in interviews

---

**You're ready to impress!** 🚀
