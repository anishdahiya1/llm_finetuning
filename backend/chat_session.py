from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from llm_lab import MemoryManager, hybrid_retrieve
from llm_lab.demo_data import SAMPLE_DOCS, SAMPLE_QA


@dataclass
class ConversationMetadata:
    memory_tier_used: str
    retrieved_docs: list[str]
    tokens_generated: int
    latency_ms: float
    model_name: str


@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    metadata: Optional[ConversationMetadata] = None


@dataclass
class ChatSession:
    session_id: str
    user_id: str  # For multi-user isolation
    messages: list[ChatMessage] = field(default_factory=list)
    memory_manager: MemoryManager = field(default_factory=lambda: MemoryManager(window_size=6))
    model_name: str = "sshleifer/tiny-gpt2"
    use_rag: bool = True
    use_quantization: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    title: str = "New Chat"

    def add_message(self, role: str, content: str, metadata: Optional[ConversationMetadata] = None) -> None:
        self.messages.append(ChatMessage(role=role, content=content, metadata=metadata))
        self.memory_manager.add_turn(role, content)
        self.updated_at = datetime.now().isoformat()
        
        # Auto-generate title from first user message
        if role == "user" and self.title == "New Chat":
            # Create title from first user message (first 50 chars)
            title = content[:50].strip()
            if len(content) > 50:
                title += "..."
            self.title = title

    def get_context(self) -> str:
        if not self.messages:
            return ""

        last_user_message = next(
            (msg.content for msg in reversed(self.messages) if msg.role == "user"), ""
        )

        context_parts = []
        if self.use_rag and last_user_message:
            docs = SAMPLE_DOCS + [item["answer"] for item in SAMPLE_QA]
            result = hybrid_retrieve(last_user_message, docs, top_k=3)
            context_parts.append("Retrieved Context:")
            for chunk in result.results:
                context_parts.append(f"- {chunk.text}")

        memory_context = self.memory_manager.build_context(last_user_message, top_k=2)
        context_parts.append("\nMemory Context:")
        context_parts.append(memory_context)

        return "\n".join(context_parts)

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "messages": [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": msg.metadata.__dict__ if msg.metadata else None,
                }
                for msg in self.messages
            ],
            "model_name": self.model_name,
            "use_rag": self.use_rag,
            "use_quantization": self.use_quantization,
        }
