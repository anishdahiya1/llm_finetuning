# Deployment Playbook

## Table of Contents
1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Deployment (Production)](#cloud-deployment)
4. [Monitoring & Troubleshooting](#monitoring--troubleshooting)
5. [Performance Tuning](#performance-tuning)

---

## Local Development

### Requirements
- Python 3.11+
- Node.js 18+
- pip/npm

### Setup (5 minutes)

```bash
# 1. Install Python deps
cd llm-optimization-lab
python -m venv .venv
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate # Mac/Linux
pip install -r requirements.txt

# 2. Install Frontend deps
cd frontend
npm install
cd ..

# 3. Run backend (Terminal 1)
cd backend
uvicorn main:app --reload --port 8000

# 4. Run frontend (Terminal 2)
cd frontend
npm run dev

# 5. Run tests (Terminal 3)
python -m pytest tests/ -v
```

### Verify Setup
- Backend Swagger UI: http://localhost:8000/docs
- Frontend Dashboard: http://localhost:3000
- Health Check: `curl http://localhost:8000/health`

---

## Docker Deployment

### Requirements
- Docker >=20.10
- Docker Compose >=2.0

### One-Command Production Setup

```bash
# Build and run
docker-compose up --build -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:3000

# Stop services
docker-compose down
```

### What Gets Deployed

| Service | Image | Port | Healthcheck |
| --- | --- | --- | --- |
| Backend | llm-optimization-lab:latest | 8000 | GET /health |
| Frontend | llm-opt-frontend:latest | 3000 | HTTP 200 |

### Customize Images

```yaml
# docker-compose.override.yml
services:
  backend:
    environment:
      - ENVIRONMENT=staging
      - LOG_LEVEL=debug
```

---

## Cloud Deployment

### Option 1: AWS Elastic Beanstalk

```bash
# 1. Install EB CLI
pip install awsebcli

# 2. Initialize
eb init -p docker llm-optimization-lab --region us-east-1

# 3. Create environment
eb create production

# 4. Deploy updates
git push
eb deploy

# 5. Monitor
eb logs
eb health
```

**Cost**: ~$5-20/month for micro instance

---

### Option 2: Google Cloud Run

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Enable required services
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com

# 3. Build and push to Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/llm-optimization-lab

# 4. Deploy to Cloud Run
gcloud run deploy llm-optimization-lab \
  --image gcr.io/YOUR_PROJECT_ID/llm-optimization-lab \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8000

# 5. Get URL
gcloud run services describe llm-optimization-lab --region us-central1
```

**Cost**: Free tier includes 2M requests/month

---

### Option 3: Heroku

```bash
# 1. Install Heroku CLI & login
heroku login

# 2. Create app
heroku create llm-optimization-lab

# 3. Add buildpack for Docker
heroku stack:set container

# 4. Deploy
git push heroku main

# 5. View live
heroku open
heroku logs --tail
```

**Cost**: Free tier deprecated; ~$7+/month for hobby dyno

---

### Option 4: DigitalOcean

```bash
# 1. Install doctl
# https://docs.digitalocean.com/reference/doctl/

# 2. Create app.yaml
cat > app.yaml <<EOF
name: llm-optimization-lab
services:
  - name: backend
    github:
      repo: YOUR_GITHUB/llm-optimization-lab
      branch: main
    build_command: npm ci && npm run build
    dockerfile_path: Dockerfile
    envs:
      - key: ENVIRONMENT
        value: production
    http_port: 8000
    health_check:
      http_path: /health
EOF

# 3. Deploy
doctl apps create --spec app.yaml

# 4. Monitor
doctl apps describe <app_id>
```

**Cost**: $12+/month for basic container

---

## Monitoring & Troubleshooting

### Backend Health

```bash
# Check service status
docker-compose ps

# View backend logs
docker-compose logs backend | tail -100

# Check API response time
time curl http://localhost:8000/api/retrieval

# Memory usage
docker stats llm-optimization-lab-backend-1

# Load testing
ab -n 100 -c 10 http://localhost:8000/health
```

### Frontend Issues

```bash
# Check build
docker-compose logs frontend | grep -i error

# Verify API connectivity
curl -H "Origin: http://localhost:3000" http://localhost:8000/info

# Check CORS headers
curl -I http://localhost:8000/api/retrieval
```

### Common Issues & Solutions

#### Issue: "Connection refused" on port 8000
```bash
# Solution: Check if port is already in use
lsof -i :8000  # Mac/Linux
Get-NetTCPConnection -LocalPort 8000  # Windows
# Kill the process and retry
```

#### Issue: Frontend can't reach backend API
```bash
# Solution: Update VITE_API_URL in frontend/.env
VITE_API_URL=http://localhost:8000  # local
VITE_API_URL=https://api.yourdomain.com  # production
npm run dev
```

#### Issue: Model loading fails
```bash
# Solution: Check available disk space
df -h  # Linux/Mac
Get-Volume  # Windows

# Clear cache
rm -rf ~/.cache/huggingface/
```

#### Issue: Out of memory
```bash
# Solution: Limit number of workers
WORKERS=1 docker-compose up
# Or upgrade instance size
```

---

## Performance Tuning

### Backend Optimization

```python
# 1. Increase uvicorn workers for high concurrency
CMD ["uvicorn", "backend.main:app", "--workers", "4"]

# 2. Enable model quantization for efficiency
LLM_LAB_QUANT_MODEL=mistralai/Mistral-7B-v0.1
ENABLE_4BIT_QUANT=true

# 3. Use GPU if available
CUDA_VISIBLE_DEVICES=0

# 4. Cache models in memory
MODEL_CACHE_SIZE_MB=4096
```

### Frontend Optimization

```bash
# 1. Enable production build
npm run build

# 2. Use CDN for assets
# In production, serve dist/ from CloudFront/Cloudflare

# 3. Code splitting and lazy loading
# Already handled by Vite

# 4. Minimize API calls
# Implement debouncing and request batching
```

### Database Optimization (if added)
```sql
-- Add indexes for common queries
CREATE INDEX idx_demo_results_timestamp ON demo_results(timestamp);

-- Use connection pooling
-- Recommended: pgBouncer for PostgreSQL
```

---

## Scaling for Production

### Horizontal Scaling

```yaml
# docker-compose.yml for production scaling
services:
  backend:
    replicas: 3
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
```

### Load Balancing

```bash
# Using Nginx as reverse proxy
# Config: nginx.conf

upstream backend {
    server backend-1:8000;
    server backend-2:8000;
    server backend-3:8000;
}

server {
    listen 80;
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Failover

```bash
# Primary-replica setup for PostgreSQL
# Master: production database
# Replica: read-only copy updated via streaming replication
```

---

## Deployment Checklist (Pre-Production)

```bash
# Code Quality
[ ] ruff check llm_lab backend
[ ] pytest tests/ --cov

# Build & Package
[ ] docker build -t llm-optimization-lab:1.0 .
[ ] docker run -p 8000:8000 llm-optimization-lab:1.0

# Configuration
[ ] Environment variables set (.env file)
[ ] Secrets in secure vault (AWS Secrets Manager / HashiCorp Vault)
[ ] Database credentials rotated
[ ] API keys provisioned

# Monitoring Setup
[ ] CloudWatch / DataDog / Prometheus dashboards
[ ] Alert thresholds configured (CPU >80%, Memory >85%)
[ ] Logging aggregation active (ELK stack / Datadog)

# Security
[ ] SSL/TLS certificate installed
[ ] CORS policy restricted to production domain
[ ] Rate limiting enabled
[ ] WAF rules configured

# Backup & Disaster Recovery
[ ] Database backups scheduled (daily)
[ ] Backup restoration tested
[ ] Disaster recovery plan documented

# Performance
[ ] Load testing passed (100+ concurrent users)
[ ] API response times < 500ms (p95)
[ ] Frontend load time < 3 seconds

# Go-Live
[ ] Status page deployed
[ ] Support documentation ready
[ ] On-call rotation scheduled
[ ] Rollback plan documented
```

---

## Post-Deployment

### Day 1
- [ ] Monitor error rates (target: <0.1%)
- [ ] Track API latency (target: <200ms p95)
- [ ] Test user workflows
- [ ] Verify logging is working

### Week 1
- [ ] Analyze user behavior (analytics)
- [ ] Optimize slow endpoints
- [ ] Fix reported bugs
- [ ] Update documentation

### Ongoing
- [ ] Weekly security scans
- [ ] Monthly performance review
- [ ] Quarterly disaster recovery drills

---

**Ready to deploy! 🚀 Questions? Check ARCHITECTURE.md or README_PRODUCTION.md**
