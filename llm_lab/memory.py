from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class MemoryHit:
    text: str
    score: float


@dataclass
class MemoryTurn:
    role: str
    content: str


@dataclass
class MemoryManager:
    window_size: int = 6
    summarizer: Callable[[Sequence[MemoryTurn]], str] | None = None
    turns: list[MemoryTurn] = field(default_factory=list)
    summary: str = ""
    archived_turns: list[MemoryTurn] = field(default_factory=list)

    def add_turn(self, role: str, content: str) -> None:
        self.turns.append(MemoryTurn(role=role, content=content))
        self._roll_window()

    def _roll_window(self) -> None:
        overflow = max(len(self.turns) - self.window_size, 0)
        if overflow == 0:
            return

        moved = self.turns[:overflow]
        self.archived_turns.extend(moved)
        self.turns = self.turns[overflow:]
        if self.summarizer is not None:
            self.summary = self.summarizer(self.archived_turns)
        elif self.archived_turns:
            self.summary = self._fallback_summary(self.archived_turns)

    def _fallback_summary(self, turns: Sequence[MemoryTurn]) -> str:
        facts: list[str] = []
        for turn in turns[-12:]:
            snippet = turn.content.strip().replace("\n", " ")
            if len(snippet) > 120:
                snippet = snippet[:117] + "..."
            facts.append(f"{turn.role}: {snippet}")
        return " | ".join(facts)

    def recent_text(self) -> str:
        return "\n".join(f"{turn.role}: {turn.content}" for turn in self.turns)

    def retrieve(self, query: str, top_k: int = 3) -> list[MemoryHit]:
        corpus = [turn.content for turn in self.archived_turns + self.turns]
        if not corpus:
            return []

        vectorizer = TfidfVectorizer().fit(corpus + [query])
        vectors = vectorizer.transform(corpus + [query])
        scores = cosine_similarity(vectors[-1], vectors[:-1]).ravel()
        order = np.argsort(scores)[::-1][:top_k]
        return [MemoryHit(text=corpus[index], score=float(scores[index])) for index in order if scores[index] > 0]

    def build_context(self, query: str, top_k: int = 3) -> str:
        relevant = self.retrieve(query, top_k=top_k)
        relevant_text = "\n".join(f"- {hit.text} (score={hit.score:.3f})" for hit in relevant) or "- none"
        summary = self.summary or "none"
        recent = self.recent_text() or "none"
        return f"Summary:\n{summary}\n\nRelevant memories:\n{relevant_text}\n\nRecent turns:\n{recent}"
