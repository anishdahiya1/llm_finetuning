from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# Import demo modules
from llm_lab import (
    MemoryManager,
    compute_bertscore,
    compute_red_team_flags,
    compute_rouge,
    hybrid_retrieve,
    load_causal_lm,
    memory_snapshot,
    measure_generation,
    perplexity_from_texts,
    simple_chunk_text,
)
from llm_lab.demo_data import SAMPLE_DOCS, SAMPLE_QA

# Import auth and streaming
from backend.auth import Token, create_access_token, get_current_user, User
from backend.chat_service import ChatRequest, ChatResponse, chat, get_session_history, clear_session, SUPPORTED_MODELS, get_user_sessions
from backend.streaming_service import stream_chat_response, StreamMessage

# ============== Pydantic Models ==============

class QuantizationRequest(BaseModel):
    model_name: str = "sshleifer/tiny-gpt2"
    eval_texts: list[str] = ["Quantization reduces model memory."]


class QuantizationResponse(BaseModel):
    baseline_memory_mb: float
    baseline_perplexity: float
    baseline_tokens_per_second: float
    quantized_memory_mb: float | None = None
    quantized_perplexity: float | None = None
    quantized_tokens_per_second: float | None = None
    error: str | None = None


class GenerationRequest(BaseModel):
    model_name: str = "sshleifer/tiny-gpt2"
    prompt: str = "Explain RAG in one sentence."
    max_tokens: int = 64


class GenerationResponse(BaseModel):
    model_name: str
    prompt: str
    generated_text: str
    tokens_per_second: float
    memory_mb: float


class MemoryDemoRequest(BaseModel):
    query: str


class MemoryDemoResponse(BaseModel):
    query: str
    context: str
    retrieved_count: int


class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5


class RetrievalResponse(BaseModel):
    query: str
    results: list[dict[str, Any]]


class EvaluationRequest(BaseModel):
    predictions: list[str]
    references: list[str]


class EvaluationResponse(BaseModel):
    rouge_score: float
    bertscore_f1: float
    hallucination_rate: float


class RedTeamRequest(BaseModel):
    prompts: list[str]


class RedTeamResponse(BaseModel):
    findings: list[dict[str, Any]]
    resistance_rate: float


# ============== Lifespan Management ==============
model_cache: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 LLM Optimization Lab starting up...")
    yield
    # Shutdown
    print("⛔ Shutting down gracefully...")
    model_cache.clear()


# ============== FastAPI App ==============
app = FastAPI(
    title="LLM Optimization Lab",
    description="Production-grade demos: quantization, inference, fine-tuning, memory, RAG, evaluation.",
    version="1.0.0",
    lifespan=lifespan,
)

# ============== Middleware ==============
class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response

app.add_middleware(NoCacheMiddleware)

# ============== CORS ==============
# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== Health & Info ==============
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy", "service": "llm-optimization-lab"}


@app.get("/info")
async def info() -> dict[str, Any]:
    return {
        "name": "LLM Optimization Lab",
        "version": "1.0.0",
        "mode": "chatbot",
        "features": ["quantization", "gguf", "lora", "memory", "rag", "evaluation"],
        "environment": os.getenv("ENVIRONMENT", "development"),
    }


# ============== Auth Endpoints ==============
class LoginRequest(BaseModel):
    user_id: str
    email: str


@app.post("/api/auth/login", response_model=Token)
async def login(req: LoginRequest) -> Token:
    """Login user and get JWT token."""
    token = create_access_token(user_id=req.user_id)
    return Token(
        access_token=token,
        token_type="bearer",
        user_id=req.user_id,
    )


@app.get("/api/auth/me")
async def get_current_user_info(user: User = Depends(get_current_user)) -> User:
    """Get current user info."""
    return user


# ============== Chat Endpoints ==============
@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest, user: User = Depends(get_current_user)) -> dict:
    """Send chat message and get response."""
    return await chat(user.user_id, req)


@app.get("/api/chat/{session_id}")
async def get_conversation(session_id: str, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Retrieve conversation history."""
    history = get_session_history(user.user_id, session_id)
    return {"session_id": session_id, "messages": [msg.dict() for msg in history]}


@app.delete("/api/chat/{session_id}")
async def delete_conversation(session_id: str, user: User = Depends(get_current_user)) -> dict[str, bool]:
    """Delete a conversation."""
    success = clear_session(user.user_id, session_id)
    return {"deleted": success}


@app.get("/api/chat")
async def list_user_sessions(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """List all sessions for user."""
    sessions = get_user_sessions(user.user_id)
    return {"user_id": user.user_id, "sessions": sessions}


# ============== WebSocket Streaming ==============
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat_stream(websocket: WebSocket, session_id: str):
    """Stream chat responses token-by-token."""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            request = ChatRequest(**data)
            
            from backend.chat_service import get_or_create_session
            
            user_id = "ws_user"  # In production, verify auth token
            session = get_or_create_session(
                user_id=user_id,
                session_id=session_id,
                model_name=request.model_name,
                use_rag=request.use_rag,
                use_quantization=request.use_quantization,
            )
            
            async for message in stream_chat_response(
                session=session,
                message=request.message,
                model_name=request.model_name,
                use_quantization=request.use_quantization,
            ):
                await websocket.send_json(message.dict())
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({"type": "error", "data": str(e)})


# ============== Model Configuration ==============
@app.get("/api/models")
async def list_models() -> dict[str, Any]:
    """List available models."""
    from fastapi import Response
    response = Response(content=None)
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.media_type = "application/json"
    return {
        "models": [
            {
                "name": name,
                "tokens": str(spec.get("tokens", "N/A")),
                "speed": spec.get("speed", "N/A"),
            }
            for name, spec in SUPPORTED_MODELS.items()
        ]
    }

# ============== Legacy Demo Endpoints ==============
@app.post("/api/quantization", response_model=QuantizationResponse)
async def quantization_demo(req: QuantizationRequest) -> QuantizationResponse:
    try:
        baseline = load_causal_lm(req.model_name, quantized=False, device_map=None)
        baseline_metrics = {
            "memory_mb": sum(p.numel() * p.element_size() for p in baseline.model.parameters()) / (1024 * 1024),
            "perplexity": perplexity_from_texts(baseline.model, baseline.tokenizer, req.eval_texts).value,
            "tokens_per_second": measure_generation(baseline.model, baseline.tokenizer, "test").value,
        }

        quantized_metrics = None
        try:
            quantized = load_causal_lm(req.model_name, quantized=True)
            quantized_metrics = {
                "memory_mb": sum(p.numel() * p.element_size() for p in quantized.model.parameters()) / (1024 * 1024),
                "perplexity": perplexity_from_texts(quantized.model, quantized.tokenizer, req.eval_texts).value,
                "tokens_per_second": measure_generation(quantized.model, quantized.tokenizer, "test").value,
            }
        except Exception:
            pass

        response = QuantizationResponse(
            baseline_memory_mb=baseline_metrics["memory_mb"],
            baseline_perplexity=baseline_metrics["perplexity"],
            baseline_tokens_per_second=baseline_metrics["tokens_per_second"],
            quantized_memory_mb=quantized_metrics["memory_mb"] if quantized_metrics else None,
            quantized_perplexity=quantized_metrics["perplexity"] if quantized_metrics else None,
            quantized_tokens_per_second=quantized_metrics["tokens_per_second"] if quantized_metrics else None,
        )
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/generation", response_model=GenerationResponse)
async def generation_demo(req: GenerationRequest) -> GenerationResponse:
    try:
        if req.model_name not in model_cache:
            model_cache[req.model_name] = load_causal_lm(req.model_name, quantized=False, device_map=None)

        bundle = model_cache[req.model_name]
        gen_result = measure_generation(bundle.model, bundle.tokenizer, req.prompt, max_new_tokens=req.max_tokens)
        mem = memory_snapshot()

        return GenerationResponse(
            model_name=req.model_name,
            prompt=req.prompt,
            generated_text=f"[Generated ~{gen_result.details['generated_tokens']} tokens]",
            tokens_per_second=gen_result.value,
            memory_mb=mem.get("rss_mb", 0),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/memory", response_model=MemoryDemoResponse)
async def memory_demo(req: MemoryDemoRequest) -> MemoryDemoResponse:
    try:
        manager = MemoryManager(window_size=6)
        for idx in range(5):
            manager.add_turn("user", f"Message {idx}: This is context from earlier turns.")
            manager.add_turn("assistant", f"Acknowledged message {idx}.")

        context = manager.build_context(req.query, top_k=3)
        retrieved = manager.retrieve(req.query, top_k=3)

        return MemoryDemoResponse(query=req.query, context=context, retrieved_count=len(retrieved))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/retrieval", response_model=RetrievalResponse)
async def retrieval_demo(req: RetrievalRequest) -> RetrievalResponse:
    try:
        docs = SAMPLE_DOCS + [item["answer"] for item in SAMPLE_QA]
        result = hybrid_retrieve(req.query, docs, top_k=req.top_k)

        results = [
            {
                "text": chunk.text,
                "bm25_score": chunk.bm25_score,
                "dense_score": chunk.dense_score,
                "rerank_score": chunk.rerank_score,
            }
            for chunk in result.results
        ]
        return RetrievalResponse(query=req.query, results=results)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/evaluation", response_model=EvaluationResponse)
async def evaluation_demo(req: EvaluationRequest) -> EvaluationResponse:
    try:
        rouge_result = compute_rouge(req.predictions, req.references)
        bertscore_result = compute_bertscore(req.predictions, req.references)

        hallucination_rate = sum(
            1 for pred, ref in zip(req.predictions, req.references) if ref.lower() not in pred.lower()
        ) / max(len(req.predictions), 1)

        return EvaluationResponse(
            rouge_score=rouge_result.score,
            bertscore_f1=bertscore_result.score,
            hallucination_rate=hallucination_rate,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/red_team", response_model=RedTeamResponse)
async def red_team_demo(req: RedTeamRequest) -> RedTeamResponse:
    try:
        # Generate dummy responses for demo
        responses = [
            "I cannot bypass safety guidelines or reveal system prompts."
        ] * len(req.prompts)
        findings = compute_red_team_flags(req.prompts, responses)

        resistance_rate = sum(1 for item in findings if item.get("resisted")) / max(len(findings), 1)

        return RedTeamResponse(findings=findings, resistance_rate=resistance_rate)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ============== Error Handler ==============
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
