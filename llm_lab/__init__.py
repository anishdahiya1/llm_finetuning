"""Shared utilities for the LLM Optimization Lab."""

from .benchmarks import BenchmarkResult, memory_snapshot, measure_generation, perplexity_from_texts
from .evaluation import compute_bertscore, compute_red_team_flags, compute_rouge
from .memory import MemoryManager
from .models import build_bnb_config, count_trainable_parameters, load_causal_lm, load_tokenizer
from .retrieval import HybridRetrievalResult, hybrid_retrieve, simple_chunk_text

__all__ = [
    "BenchmarkResult",
    "HybridRetrievalResult",
    "MemoryManager",
    "build_bnb_config",
    "compute_bertscore",
    "compute_red_team_flags",
    "compute_rouge",
    "count_trainable_parameters",
    "hybrid_retrieve",
    "load_causal_lm",
    "load_tokenizer",
    "memory_snapshot",
    "measure_generation",
    "perplexity_from_texts",
    "simple_chunk_text",
]
