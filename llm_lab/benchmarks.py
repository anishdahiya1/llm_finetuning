from __future__ import annotations

from dataclasses import dataclass
from math import exp
from time import perf_counter
from typing import Iterable, Sequence

import psutil

try:
    import torch
except Exception:  # pragma: no cover - optional dependency at runtime
    torch = None


@dataclass
class BenchmarkResult:
    name: str
    value: float
    unit: str
    details: dict[str, float | int | str]


def memory_snapshot() -> dict[str, float]:
    process = psutil.Process()
    snapshot = {"rss_mb": process.memory_info().rss / (1024 * 1024)}
    if torch is not None and torch.cuda.is_available():
        snapshot.update(
            {
                "cuda_allocated_mb": torch.cuda.memory_allocated() / (1024 * 1024),
                "cuda_reserved_mb": torch.cuda.memory_reserved() / (1024 * 1024),
                "cuda_max_allocated_mb": torch.cuda.max_memory_allocated() / (1024 * 1024),
            }
        )
    return snapshot


def _select_device(model) -> str:
    if torch is None:
        return "cpu"
    try:
        return next(model.parameters()).device.type
    except Exception:
        return "cuda" if torch.cuda.is_available() else "cpu"


def perplexity_from_texts(model, tokenizer, texts: Sequence[str], max_length: int = 256) -> BenchmarkResult:
    if torch is None:
        raise RuntimeError("torch is required to measure perplexity")

    device = _select_device(model)
    encoded = tokenizer(
        list(texts),
        return_tensors="pt",
        padding=True,
        truncation=True,
        max_length=max_length,
    )
    input_ids = encoded["input_ids"].to(device)
    attention_mask = encoded["attention_mask"].to(device)
    labels = input_ids.clone()
    labels[attention_mask == 0] = -100

    model.eval()
    with torch.no_grad():
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)

    loss = float(outputs.loss.detach().cpu().item())
    return BenchmarkResult(
        name="perplexity",
        value=exp(loss),
        unit="ppl",
        details={"loss": loss, "num_texts": len(texts)},
    )


def measure_generation(model, tokenizer, prompt: str, max_new_tokens: int = 64) -> BenchmarkResult:
    if torch is None:
        raise RuntimeError("torch is required to measure generation speed")

    device = _select_device(model)
    encoded = tokenizer(prompt, return_tensors="pt").to(device)

    model.eval()
    start = perf_counter()
    with torch.no_grad():
        generated = model.generate(**encoded, max_new_tokens=max_new_tokens, do_sample=False)
    elapsed = perf_counter() - start

    prompt_len = int(encoded["input_ids"].shape[-1])
    total_tokens = int(generated.shape[-1])
    new_tokens = max(total_tokens - prompt_len, 1)
    tokens_per_second = new_tokens / max(elapsed, 1e-9)
    return BenchmarkResult(
        name="tokens_per_second",
        value=tokens_per_second,
        unit="tok/s",
        details={"elapsed_seconds": elapsed, "generated_tokens": new_tokens, "prompt_tokens": prompt_len},
    )


def estimate_parameter_size_mb(model) -> float:
    total_bytes = 0
    for parameter in model.parameters():
        total_bytes += parameter.numel() * parameter.element_size()
    return total_bytes / (1024 * 1024)


def count_parameters(model) -> dict[str, int]:
    trainable = 0
    total = 0
    for parameter in model.parameters():
        count = parameter.numel()
        total += count
        if parameter.requires_grad:
            trainable += count
    return {"trainable": trainable, "total": total}
