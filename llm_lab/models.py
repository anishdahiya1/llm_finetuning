from __future__ import annotations

from dataclasses import dataclass
from typing import Any

try:
    import torch
except Exception:  # pragma: no cover - optional dependency at runtime
    torch = None

from transformers import AutoModelForCausalLM, AutoTokenizer


@dataclass
class ModelBundle:
    model: Any
    tokenizer: Any


def load_tokenizer(model_name: str, **kwargs):
    return AutoTokenizer.from_pretrained(model_name, **kwargs)


def build_bnb_config(load_in_4bit: bool = True):
    try:
        from transformers import BitsAndBytesConfig
    except Exception as exc:  # pragma: no cover - optional dependency at runtime
        raise RuntimeError("BitsAndBytesConfig requires a recent transformers installation") from exc

    if torch is None:
        raise RuntimeError("torch is required to configure 4-bit quantization")

    return BitsAndBytesConfig(
        load_in_4bit=load_in_4bit,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )


def load_causal_lm(model_name: str, quantized: bool = False, device_map: str | None = "auto", **kwargs):
    load_kwargs = dict(kwargs)
    if quantized:
        load_kwargs["quantization_config"] = build_bnb_config(True)
        if device_map is not None:
            load_kwargs["device_map"] = device_map
    elif torch is not None:
        load_kwargs.setdefault("torch_dtype", torch.float16 if torch.cuda.is_available() else torch.float32)
        if device_map is not None:
            load_kwargs.setdefault("device_map", device_map)

    tokenizer = load_tokenizer(model_name, trust_remote_code=kwargs.get("trust_remote_code", False))
    model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
    tokenizer.pad_token = tokenizer.eos_token if tokenizer.pad_token is None else tokenizer.pad_token
    return ModelBundle(model=model, tokenizer=tokenizer)


def count_trainable_parameters(model) -> dict[str, int]:
    trainable = 0
    total = 0
    for parameter in model.parameters():
        size = parameter.numel()
        total += size
        if parameter.requires_grad:
            trainable += size
    return {"trainable": trainable, "total": total}


def prepare_generation_inputs(tokenizer, prompt: str, device: str | None = None):
    encoded = tokenizer(prompt, return_tensors="pt")
    if torch is not None and device is not None:
        encoded = {key: value.to(device) for key, value in encoded.items()}
    return encoded
