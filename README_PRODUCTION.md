# LLM Optimization Lab — Production-Grade Full-Stack Application

> **Enterprise-ready platform showcasing 6 LLM optimization demos**: quantization, GGUF inference, LoRA fine-tuning, context memory, hybrid RAG, and evaluation.

---

## 🎯 What This Is

A **complete, production-grade application** demonstrating advanced LLM engineering:

| Feature | Demo |
| --- | --- |
| **Quantization** ⚡ | Compare 4-bit vs full precision: memory, latency, perplexity |
| **GGUF Inference** 🏃 | Local inference API with performance benchmarking |
| **LoRA Fine-tuning** 🎓 | Efficient adapter-based training with PEFT + TRL |
| **Context Memory** 🧠 | 3-tier memory system: sliding window + summary + vector retrieval |
| **Hybrid RAG** 🔍 | BM25 + dense retrieval + reranking for fact-grounded answers |
| **Evaluation & Red-teaming** 🛡️ | ROUGE/BERTScore metrics + prompt-injection resistance |

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker (optional)
- Node.js 18+ (for frontend)

### Local Development

```bash
# Backend
cd backend
pip install -r ../requirements.txt
uvicorn main:app --reload

# Frontend (in another terminal)
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 → interact with all 6 demos in real-time.

### Production Deployment

```bash
docker-compose up -d
```

Serves:
- **Backend API**: http://localhost:8000
- **Frontend UI**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs (Swagger)

---

## 🏗️ Architecture

```
┌─────────────────────┐
│   React Dashboard   │  (Tailwind, Recharts, Zustand)
│   Port 3000         │
└───────────┬─────────┘
            │ (HTTP/REST)
┌───────────▼──────────────────────────────────────────┐
│           FastAPI Service Layer (Port 8000)          │
├──────────────────────────────────────────────────────┤
│  /api/quantization  → BitsAndBytes bench             │
│  /api/generation    → Token generation metrics        │
│  /api/memory        → 3-tier memory system           │
│  /api/retrieval     → Hybrid RAG (BM25 + dense)     │
│  /api/evaluation    → ROUGE + BERTScore             │
│  /api/red_team      → Prompt injection detection    │
└──────────┬───────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────┐
│   Shared LLM Lab (llm_lab/)              │
│   - benchmarks.py (memory, latency)      │
│   - models.py (Hugging Face + quant)     │
│   - memory.py (3-tier manager)           │
│   - retrieval.py (BM25 + embeddings)     │
│   - evaluation.py (metrics + red-team)   │
└──────────────────────────────────────────┘
```

---

## 📊 Backend API Endpoints

### Health & Info
- `GET /health` → Service health check
- `GET /info` → Available demos

### Demo Endpoints (all POST)
- `POST /api/quantization` → Compare 4-bit vs full precision
- `POST /api/generation` → Generate text + measure tokens/sec
- `POST /api/memory` → Test 3-tier memory retrieval
- `POST /api/retrieval` → Hybrid RAG search
- `POST /api/evaluation` → Score predictions against references
- `POST /api/red_team` → Check prompt-injection resistance

**Full API documentation**: http://localhost:8000/docs (auto-generated Swagger UI)

---

## 🎨 Frontend Features

- **6 interactive demo cards** — select and run each demo
- **Real-time results** — JSON output with live performance metrics
- **Dark mode dashboard** — professional Tailwind design
- **Error handling** — user-friendly error messages
- **Responsive UI** — works on desktop and tablet

---

## 🐳 Docker Deployment

```bash
# Build and run
docker-compose up --build

# Logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Stop
docker-compose down
```

Images:
- **Backend**: Python 3.11 slim + uvicorn + LLM stack
- **Frontend**: Node.js alpine + Vite optimized build

---

## 🔧 Configuration

### Environment Variables

**Backend** (`backend/config.py`):
```python
DEBUG = True
HOST = "0.0.0.0"
PORT = 8000
WORKERS = 1
LOG_LEVEL = "info"
```

**Frontend** (`.env`):
```
VITE_API_URL=http://localhost:8000
```

### Model Selection

Edit environment variables to swap models:
```bash
LLM_LAB_QUANT_MODEL=mistralai/Mistral-7B-v0.1
LLM_LAB_GGUF_COMPARE_MODEL=gpt2
```

---

## ✅ CI/CD Pipeline

**GitHub Actions** (`.github/workflows/ci.yml`):
- ✔ **Lint**: Ruff static analysis
- ✔ **Test**: Pytest suite
- ✔ **Compile**: Python bytecode validation
- ✔ **Build**: Docker image creation (on main branch)

Run locally:
```bash
python -m ruff check llm_lab backend
python -m compileall llm_lab backend
```

---

## 📦 Project Structure

```
llm-optimization-lab/
├── backend/
│   ├── main.py              # FastAPI app with 6 endpoints
│   └── config.py            # Environment config
├── frontend/
│   ├── src/
│   │   ├── Dashboard.jsx    # Main UI
│   │   ├── App.jsx          # App wrapper
│   │   └── index.css        # Tailwind styles
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── llm_lab/                 # Shared Python package
│   ├── benchmarks.py
│   ├── models.py
│   ├── memory.py
│   ├── retrieval.py
│   ├── evaluation.py
│   └── demo_data.py
├── Dockerfile               # Backend container
├── docker-compose.yml       # Multi-container orchestration
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🎓 What Recruiter Will See

1. **Full-stack capability**: React frontend + FastAPI backend
2. **Production patterns**: Docker, CI/CD, error handling, logging
3. **LLM expertise**: Quantization, RAG, fine-tuning, evaluation
4. **Clean code**: Pydantic models, type hints, modular design
5. **DevOps chops**: Docker Compose, GitHub Actions, deployment-ready

---

## 🚀 Deployment Options

### **Heroku** (Free tier)
```bash
heroku create llm-optimization-lab
git push heroku main
heroku logs --tail
```

### **AWS Elastic Beanstalk**
```bash
eb init
eb create
eb deploy
```

### **Google Cloud Run**
```bash
gcloud run deploy llm-optimization-lab \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

---

## 📝 Requirements

See `requirements.txt` for all dependencies. Key packages:
- `transformers` — Hugging Face models
- `torch` — PyTorch
- `fastapi` — REST API framework
- `pydantic` — Data validation
- `rank-bm25` — BM25 retrieval
- `sentence-transformers` — Dense embeddings
- `evaluate` — ROUGE/BERTScore metrics

---

## 🤝 Contributing

1. Create a feature branch
2. Commit & push
3. Open a PR (CI pipeline runs automatically)

---

## 📧 Contact & Resume

**This app demonstrates**:
- ✅ Full-stack web development (React + FastAPI)
- ✅ Production DevOps (Docker, CI/CD)
- ✅ Advanced NLP/LLM engineering
- ✅ System design & scalability
- ✅ Clean code & testing practices

**Ideal for**: ML Engineer, ML Platform Engineer, or Senior Backend Engineer roles.

---

**Built with ❤️ for engineers who ship production systems.**
