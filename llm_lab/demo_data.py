from __future__ import annotations

SAMPLE_DOCS = [
    "Retrieval-augmented generation combines search and generation so the model answers from evidence instead of memory alone.",
    "Quantization reduces model memory by storing weights with fewer bits, often with a small quality tradeoff.",
    "LoRA fine-tuning updates a low-rank adapter instead of every weight, which keeps training cheap.",
    "A memory system can combine a short sliding window, a summary buffer, and semantic retrieval of old turns.",
    "Hybrid RAG often improves factual accuracy because BM25 captures exact terms while embeddings capture meaning.",
    "Evaluation should track both accuracy metrics and robustness against prompt injection or leakage attempts.",
]

SAMPLE_QA = [
    {
        "question": "Why combine BM25 with embeddings?",
        "answer": "BM25 recovers exact keyword matches while embeddings recover semantic matches, so the system is stronger on factual retrieval.",
    },
    {
        "question": "What does LoRA change during fine-tuning?",
        "answer": "LoRA trains small low-rank adapter matrices while the base model stays frozen.",
    },
    {
        "question": "What problem does context memory solve?",
        "answer": "It keeps long-running conversations coherent by preserving recent turns, condensed summaries, and searchable old facts.",
    },
]
