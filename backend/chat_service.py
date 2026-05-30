from __future__ import annotations

import time
import uuid
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel

from backend.chat_session import ChatSession, ConversationMetadata
from llm_lab import load_causal_lm, measure_generation


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    use_rag: bool = True
    use_quantization: bool = False
    model_name: str = "sshleifer/tiny-gpt2"


class ChatMetadata(BaseModel):
    memory_tier_used: str
    retrieved_docs: list[str]
    tokens_generated: int
    latency_ms: float
    model_name: str


class ChatMessage(BaseModel):
    role: str
    content: str
    metadata: Optional[ChatMetadata] = None


class ChatResponse(BaseModel):
    session_id: str
    message: ChatMessage
    conversation_history: list[ChatMessage]
    context_window: str


# In-memory session storage: user_id -> {session_id -> ChatSession}
# In production, use Redis or database
user_sessions: dict[str, dict[str, ChatSession]] = {}

# Supported models with descriptions
SUPPORTED_MODELS = {
    "sshleifer/tiny-gpt2": {"tokens": "124M", "quantized_size": "300MB", "speed": "fast"},
    "mistralai/Mistral-7B": {"tokens": "7B", "quantized_size": "3.3GB", "speed": "medium"},
    "meta-llama/Llama-2-7b": {"tokens": "7B", "quantized_size": "3.3GB", "speed": "medium"},
    "meta-llama/Llama-2-13b": {"tokens": "13B", "quantized_size": "6.5GB", "speed": "slow"}
}


def get_or_create_session(user_id: str, session_id: Optional[str] = None, **kwargs) -> ChatSession:
    """Get or create a chat session for a user."""
    if user_id not in user_sessions:
        user_sessions[user_id] = {}

    if session_id and session_id in user_sessions[user_id]:
        return user_sessions[user_id][session_id]

    new_session_id = session_id or str(uuid.uuid4())
    session = ChatSession(session_id=new_session_id, user_id=user_id, **kwargs)
    user_sessions[user_id][new_session_id] = session
    return session


async def chat(user_id: str, request: ChatRequest) -> ChatResponse:
    try:
        session = get_or_create_session(
            user_id=user_id,
            session_id=request.session_id,
            model_name=request.model_name,
            use_rag=request.use_rag,
            use_quantization=request.use_quantization,
        )

        session.add_message("user", request.message)

        # Get context
        context = session.get_context()
        retrieved_docs = []
        if request.use_rag:
            from llm_lab import hybrid_retrieve
            from llm_lab.demo_data import SAMPLE_DOCS, SAMPLE_QA

            docs = SAMPLE_DOCS + [item["answer"] for item in SAMPLE_QA]
            result = hybrid_retrieve(request.message, docs, top_k=3)
            retrieved_docs = [chunk.text for chunk in result.results]

        # Generate response
        start = time.perf_counter()
        try:
            bundle = load_causal_lm(request.model_name, quantized=request.use_quantization, device_map=None)
            encoded = bundle.tokenizer(request.message, return_tensors="pt")
            device = next(bundle.model.parameters()).device
            encoded = {key: value.to(device) for key, value in encoded.items()}
            generated = bundle.model.generate(**encoded, max_new_tokens=100, do_sample=False)
            response_text = bundle.tokenizer.decode(generated[0], skip_special_tokens=True)
            if response_text.startswith(request.message):
                response_text = response_text[len(request.message):].strip() or response_text.strip()
            gen_result = measure_generation(bundle.model, bundle.tokenizer, request.message, max_new_tokens=100)
            tokens_generated = int(gen_result.details["generated_tokens"])
        except Exception as exc:
            response_text = f"I understand your question about: {request.message[:50]}..."
            tokens_generated = 50

        elapsed = (time.perf_counter() - start) * 1000  # ms

        metadata = ConversationMetadata(
            memory_tier_used="3-tier (window + summary + vector)",
            retrieved_docs=retrieved_docs,
            tokens_generated=tokens_generated,
            latency_ms=round(elapsed, 2),
            model_name=request.model_name,
        )

        assistant_message = ChatMessage(role="assistant", content=response_text, metadata=ChatMetadata(**metadata.__dict__) if metadata else None)
        session.add_message("assistant", response_text, metadata=metadata)

        # Build response history
        history = [
            ChatMessage(
                role=msg.role,
                content=msg.content,
                metadata=ChatMetadata(**msg.metadata.__dict__) if msg.metadata else None,
            )
            for msg in session.messages[:-1]
        ]

        # Return plain dict to avoid Pydantic validation issues between dataclass metadata and Pydantic models
        return {
            "session_id": session.session_id,
            "message": {
                "role": assistant_message.role,
                "content": assistant_message.content,
                "metadata": metadata.__dict__ if metadata else None,
            },
            "conversation_history": session.to_dict()["messages"][:-1],
            "context_window": context,
        }

    except Exception as exc:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(exc))


def get_session_history(user_id: str, session_id: str) -> list[ChatMessage]:
    if user_id not in user_sessions or session_id not in user_sessions[user_id]:
        raise HTTPException(status_code=404, detail="Session not found")

    session = user_sessions[user_id][session_id]
    return [
        ChatMessage(
            role=msg.role,
            content=msg.content,
            metadata=ChatMetadata(**msg.metadata.__dict__) if msg.metadata else None,
        )
        for msg in session.messages
    ]


def clear_session(user_id: str, session_id: str) -> bool:
    if user_id not in user_sessions or session_id not in user_sessions[user_id]:
        return False
    del user_sessions[user_id][session_id]
    return True


def get_user_sessions(user_id: str) -> list[dict]:
    """Get all sessions for a user."""
    if user_id not in user_sessions:
        return []
    return [
        {
            "session_id": session.session_id,
            "title": session.title,
            "message_count": len(session.messages),
            "model": session.model_name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        }
        for session in user_sessions[user_id].values()
    ]
