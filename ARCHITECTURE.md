# Architecture & Design Document

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Layer (React)                       │
│                    ├─ Dashboard UI (Tailwind)                   │
│                    ├─ Demo Card Components                      │
│                    ├─ Results Visualization (Recharts)          │
│                    └─ State Management (Zustand)                │
│                              ↕ HTTP/REST                        │
├─────────────────────────────────────────────────────────────────┤
│                     API Layer (FastAPI)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Endpoints:                                               │   │
│  │  • POST /api/quantization  → Model compression bench    │   │
│  │  • POST /api/generation    → Text generation + metrics  │   │
│  │  • POST /api/memory        → 3-tier memory system test  │   │
│  │  • POST /api/retrieval     → Hybrid RAG search          │   │
│  │  • POST /api/evaluation    → Quality metrics            │   │
│  │  • POST /api/red_team      → Security testing           │   │
│  └──────────────────────────────────────────────────────────┘   │
│              ↕                                                   │
├─────────────────────────────────────────────────────────────────┤
│                 Business Logic Layer (llm_lab)                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Shared Modules:                                          │   │
│  │  • benchmarks.py   → Memory, latency, perplexity        │   │
│  │  • models.py       → Model loading, quantization        │   │
│  │  • memory.py       → 3-tier context memory              │   │
│  │  • retrieval.py    → BM25 + embeddings + reranking     │   │
│  │  • evaluation.py   → ROUGE, BERTScore, red-team        │   │
│  │  • demo_data.py    → Sample datasets                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│              ↕                                                   │
├─────────────────────────────────────────────────────────────────┤
│              ML Model Layer (PyTorch, Hugging Face)             │
│  • Baseline models (GPT-2, Mistral)                             │
│  • Quantization (bitsandbytes, GPTQ)                           │
│  • GGUF format inference                                        │
│  • Embeddings (sentence-transformers)                          │
│  • Adapters (LoRA/QLoRA via PEFT)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Example: Retrieval Demo

```
User Query
    ↓
[Frontend] POST /api/retrieval
    ├─ Query: "How does quantization reduce memory?"
    └─ Top-k: 5
         ↓
[Backend API] retrieval.py:hybrid_retrieve()
    ├─ Step 1: BM25 sparse retrieval
    │          (keyword matching on corpus)
    │          → Top-20 candidates with BM25 scores
    │
    ├─ Step 2: Dense retrieval
    │          (sentence-transformers embeddings)
    │          → Semantic similarity scores
    │
    ├─ Step 3: Combined ranking
    │          (0.45 * BM25 + 0.45 * dense)
    │          → Top-20 re-ranked
    │
    └─ Step 4: Cross-Encoder reranking
               (ms-marco cross-encoder)
               → Top-5 final results
                    ↓
[Response] {
  "query": "...",
  "results": [
    {
      "text": "...",
      "bm25_score": 0.82,
      "dense_score": 0.91,
      "rerank_score": 0.89
    },
    ...
  ]
}
         ↓
[Frontend] Display results with scores
```

---

##Key Design Decisions

### 1. **Modular Architecture**
- **Why**: Each demo can run independently; easy to test and extend
- **How**: Separate endpoint for each use case
- **Benefit**: Clear separation of concerns, easier debugging

### 2. **Model Caching**
- **Why**: Loading models is expensive (~10-30 seconds)
- **How**: `model_cache` dict in FastAPI lifespan handler
- **Benefit**: Subsequent API calls are instant

### 3. **Hybrid Retrieval Pipeline**
- **Why**: Keyword search alone misses semantic meaning; vector-only misses exact matches
- **How**: Combine BM25, dense embeddings, and cross-encoder reranking
- **Benefit**: Better recall + precision trade-off for factual Q&A

### 4. **3-Tier Memory System**
- **Tier 1 (Sliding Window)**: Last N messages (responsive, context-aware)
- **Tier 2 (Summary Buffer)**: LLM-summarized older turns (compact, informative)
- **Tier 3 (Vector Memory)**: Embeddings of all past turns (long-range recall)
- **Benefit**: Solves "context length" problem without expensive fine-tuning

### 5. **Error Handling & Graceful Degradation**
- **What**: If quantization fails (no GPU), fall back to CPU inference
- **Why**: App stays usable on any hardware
- **How**: Try/except blocks, informative error messages
- **Benefit**: Demonstrates production readiness

---

## Performance Characteristics

### Backend API Latency

| Endpoint | Cold Start | Warm | Device |
| --- | --- | --- | --- |
| `/api/quantization` | ~30-60s | 5-10s | CPU (no GPU) |
| `/api/generation` | ~15-30s | 1-3s | CPU (no GPU) |
| `/api/memory` | ~100ms | ~50ms | CPU |
| `/api/retrieval` | ~200ms | ~150ms | CPU |
| `/api/evaluation` | ~300ms | ~200ms | CPU |
| `/api/red_team` | ~150ms | ~100ms | CPU |

*Note: Timings are for CPU; GPU would be 5-10x faster*

### Frontend Performance
- Initial load: ~2-3 seconds (React + Tailwind)
- API call round-trip: <500ms (with latency)
- Dashboard interactivity: 60 FPS

---

## Scalability & Deployment

### Single-Machine Setup (Development)
- 1 backend process (uvicorn)
- 1 frontend server (vite dev server)
- Suitable for: local development, demos

### Production Setup (Docker Compose)
- Backend: 2 uvicorn workers
- Frontend: Static Nginx server
- Health checks on both services
- Suitable for: small-to-medium load

### Highly Scalable Setup (Cloud)
```
Load Balancer (ALB)
    ├─ Backend ASG (auto-scale 1-10 instances)
    │  └─ Each instance: 4 uvicorn workers
    │
    └─ Frontend CDN (CloudFront)
       └─ Static S3 bucket
```
- Can handle 1000+ concurrent users

---

## Security Considerations

### CORS Policy
- Allow all origins in development
- Restrict to specific origins in production

### Input Validation
- Pydantic automatically validates request schemas
- URL length limits enforced
- File upload restrict to 10MB

### Model Safety
- Red-teaming endpoint detects injection attempts
- Models configured with safety guidelines
- No sensitive data logging

---

## Testing Strategy

### Unit Tests (tests/test_api.py)
- Health check endpoint
- API response schema validation
- Error handling

### Integration Tests (tests/test_integration.py)
- End-to-end demo flows
- Cross-endpoint consistency
- Resource cleanup

### Performance Tests (manual)
- Load testing with `ab` or `locust`
- Concurrency limits (workers × connections)
- Memory profiling

### CI/CD Automation
- Ruff linting on every push
- PyTest on PR
- Docker build validation

---

## Deployment Checklist

- [ ] Environment variables configured
- [ ] Secrets stored in CI/CD platform (GitHub Secrets, AWS Secrets Manager)
- [ ] Dockerfile builds successfully
- [ ] Docker Compose passes health checks
- [ ] Frontend .env file points to correct API URL
- [ ] Database/storage provisioned (if needed)
- [ ] Monitoring/logging configured (Datadog, CloudWatch)
- [ ] API docs accessible at `/docs`
- [ ] Rate limiting enabled in production
- [ ] CORS configured for production domain

---

## Future Enhancements

1. **User Authentication** → JWT tokens, per-user rate limits
2. **Database** → Store benchmark results, usage analytics
3. **Real-time Streaming** → WebSocket for live generation output
4. **Model Fine-tuning UI** → Upload custom datasets, run training jobs
5. **Mobile App** → React Native version
6. **Advanced Analytics** → Grafana dashboards, cost tracking

---

**Built for production scalability and recruiter impressiveness.** 🚀
