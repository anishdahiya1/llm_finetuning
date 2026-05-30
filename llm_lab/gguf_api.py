from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

app = FastAPI(title="GGUF Inference API", version="0.1.0")

try:
    from llama_cpp import Llama
except Exception:  # pragma: no cover - optional dependency at runtime
    Llama = None

_model: Optional[object] = None


def _load_model() -> object:
    global _model
    if _model is not None:
        return _model

    model_path = os.environ.get("GGUF_MODEL_PATH", "")
    if not model_path:
        raise RuntimeError("Set GGUF_MODEL_PATH to a local .gguf file before starting the API")
    if Llama is None:
        raise RuntimeError("llama-cpp-python is not installed")

    _model = Llama(model_path=str(Path(model_path)), n_ctx=2048, n_threads=max(os.cpu_count() or 2, 2))
    return _model


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/generate")
def generate(prompt: str, max_tokens: int = 128) -> dict[str, object]:
    model = _load_model()
    result = model(prompt, max_tokens=max_tokens, temperature=0.2, top_p=0.95)
    text = result["choices"][0]["text"]
    return {"prompt": prompt, "completion": text, "model_path": os.environ.get("GGUF_MODEL_PATH", "")}
