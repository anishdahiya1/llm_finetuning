from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from rank_bm25 import BM25Okapi
except Exception:  # pragma: no cover - optional dependency at runtime
    BM25Okapi = None


@dataclass
class RetrievedChunk:
    text: str
    bm25_score: float
    dense_score: float
    rerank_score: float


@dataclass
class HybridRetrievalResult:
    query: str
    results: list[RetrievedChunk]


def simple_chunk_text(text: str, max_chars: int = 500) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        sentences = paragraph.replace("\n", " ").split(". ")
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > max_chars and current:
                chunks.append(current.strip())
                current = sentence
            else:
                current = candidate
        if current:
            chunks.append(current.strip())
    return chunks


def _tokenize(text: str) -> list[str]:
    return [token for token in " ".join(text.lower().split()).replace(".", " ").replace(",", " ").split(" ") if token]


def _bm25_scores(query: str, documents: Sequence[str]) -> np.ndarray:
    if BM25Okapi is None:
        vectorizer = TfidfVectorizer().fit(documents + [query])
        matrix = vectorizer.transform(documents + [query])
        return cosine_similarity(matrix[-1], matrix[:-1]).ravel()

    tokenized = [_tokenize(document) for document in documents]
    query_tokens = _tokenize(query)
    bm25 = BM25Okapi(tokenized)
    return np.asarray(bm25.get_scores(query_tokens), dtype=float)


def _dense_scores(query: str, documents: Sequence[str]) -> np.ndarray:
    try:
        from sentence_transformers import SentenceTransformer

        encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        embeddings = encoder.encode([query, *documents], normalize_embeddings=True)
        return cosine_similarity([embeddings[0]], embeddings[1:]).ravel()
    except Exception:
        vectorizer = TfidfVectorizer().fit(documents + [query])
        matrix = vectorizer.transform(documents + [query])
        return cosine_similarity(matrix[-1], matrix[:-1]).ravel()


def _rerank(query: str, documents: Sequence[str], bm25_scores: np.ndarray, dense_scores: np.ndarray) -> np.ndarray:
    try:
        from sentence_transformers import CrossEncoder

        reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [(query, document) for document in documents]
        return np.asarray(reranker.predict(pairs), dtype=float)
    except Exception:
        return 0.5 * bm25_scores + 0.5 * dense_scores


def hybrid_retrieve(query: str, documents: Sequence[str], top_k: int = 5, candidate_k: int = 20) -> HybridRetrievalResult:
    if not documents:
        return HybridRetrievalResult(query=query, results=[])

    bm25_scores = _bm25_scores(query, documents)
    dense_scores = _dense_scores(query, documents)
    combined = 0.45 * bm25_scores + 0.45 * dense_scores
    candidate_indices = np.argsort(combined)[::-1][: min(candidate_k, len(documents))]

    candidate_docs = [documents[index] for index in candidate_indices]
    candidate_bm25 = bm25_scores[candidate_indices]
    candidate_dense = dense_scores[candidate_indices]
    candidate_rerank = _rerank(query, candidate_docs, candidate_bm25, candidate_dense)

    final_order = np.argsort(candidate_rerank)[::-1][: min(top_k, len(candidate_docs))]
    results = [
        RetrievedChunk(
            text=candidate_docs[index],
            bm25_score=float(candidate_bm25[index]),
            dense_score=float(candidate_dense[index]),
            rerank_score=float(candidate_rerank[index]),
        )
        for index in final_order
    ]
    return HybridRetrievalResult(query=query, results=results)
