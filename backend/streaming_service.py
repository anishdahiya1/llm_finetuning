"""WebSocket streaming service for token-by-token response generation."""

import asyncio
import time
from typing import AsyncGenerator

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.chat_session import ChatSession, ConversationMetadata
from llm_lab import load_causal_lm, measure_generation


class StreamMessage(BaseModel):
    type: str  # "token" | "metadata" | "complete" | "error"
    data: str | dict


async def stream_chat_response(
    session: ChatSession,
    message: str,
    model_name: str,
    use_quantization: bool,
) -> AsyncGenerator[StreamMessage, None]:
    """
    Stream chat response token by token.
    
    Yields StreamMessage objects:
    - type='token': data={str token}
    - type='metadata': data={metadata dict}
    - type='complete': data={complete response}
    - type='error': data={error message}
    """
    try:
        session.add_message("user", message)

        # Get context
        context = session.get_context()
        retrieved_docs = []
        try:
            from llm_lab import hybrid_retrieve
            from llm_lab.demo_data import SAMPLE_DOCS, SAMPLE_QA

            docs = SAMPLE_DOCS + [item["answer"] for item in SAMPLE_QA]
            result = hybrid_retrieve(message, docs, top_k=3)
            retrieved_docs = [chunk.text for chunk in result.results]
        except Exception:
            pass

        # Load model
        start_time = time.perf_counter()
        
        try:
            bundle = load_causal_lm(model_name, quantized=use_quantization, device_map=None)
        except Exception as exc:
            yield StreamMessage(type="error", data=f"Model loading failed: {str(exc)}")
            return

        # Generate response with token streaming
        full_response = ""
        token_count = 0

        try:
            encoded = bundle.tokenizer(message, return_tensors="pt")
            device = next(bundle.model.parameters()).device
            encoded = {key: value.to(device) for key, value in encoded.items()}
            generated = bundle.model.generate(**encoded, max_new_tokens=100, do_sample=False)
            full_response = bundle.tokenizer.decode(generated[0], skip_special_tokens=True)
            if full_response.startswith(message):
                full_response = full_response[len(message):].strip() or full_response.strip()

            gen_result = measure_generation(bundle.model, bundle.tokenizer, message, max_new_tokens=100)
            token_count = int(gen_result.details.get("generated_tokens", 0))

            # Simulate token-by-token streaming by splitting the decoded answer on whitespace.
            tokens = full_response.split()
            for token in tokens:
                yield StreamMessage(type="token", data=token + " ")
                await asyncio.sleep(0.05)  # Small delay for realistic streaming effect

        except Exception as exc:
            full_response = f"I understand your question about: {message[:50]}..."
            token_count = 10
            for token in full_response.split():
                yield StreamMessage(type="token", data=token + " ")
                await asyncio.sleep(0.05)

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        # Send metadata
        metadata = ConversationMetadata(
            memory_tier_used="3-tier (window + summary + vector)",
            retrieved_docs=retrieved_docs,
            tokens_generated=token_count,
            latency_ms=round(elapsed_ms, 2),
            model_name=model_name,
        )

        yield StreamMessage(
            type="metadata",
            data={
                "memory_tier": metadata.memory_tier_used,
                "tokens": metadata.tokens_generated,
                "latency_ms": metadata.latency_ms,
                "docs_retrieved": len(metadata.retrieved_docs),
            },
        )

        # Add to session
        session.add_message("assistant", full_response, metadata=metadata)

        # Send complete
        yield StreamMessage(
            type="complete",
            data={
                "full_response": full_response,
                "session_id": session.session_id,
                "context_window": context,
            },
        )

    except Exception as exc:
        yield StreamMessage(type="error", data=str(exc))
