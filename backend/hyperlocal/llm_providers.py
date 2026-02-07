from __future__ import annotations

import os
from dataclasses import dataclass

from openai import OpenAI

from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.openai_helpers import build_client


@dataclass(frozen=True)
class LLMClients:
    text_client: OpenAI
    vision_client: OpenAI
    text_model: str
    vision_model: str
    provider: str
    text_base_url: str
    vision_base_url: str


def _normalize_provider(provider: str) -> str:
    provider = provider.strip().lower().replace("-", "_")
    return provider or "ollama"


def resolve_llm_base_url(kind: str) -> str:
    if kind not in {"text", "vision"}:
        raise ValueError(f"Unknown LLM kind: {kind}")

    if kind == "text":
        base_url = RUNTIME_CONFIG.text_base_url
    else:
        base_url = RUNTIME_CONFIG.vision_base_url

    if base_url:
        return base_url
    if RUNTIME_CONFIG.llm_base_url:
        return RUNTIME_CONFIG.llm_base_url
    return RUNTIME_CONFIG.ollama_base_url


def resolve_llm_api_key() -> str:
    return RUNTIME_CONFIG.llm_api_key or RUNTIME_CONFIG.ollama_api_key or "ollama"


def build_llm_clients() -> LLMClients:
    provider = _normalize_provider(RUNTIME_CONFIG.llm_provider)
    if provider in {"vllm_mlx", "vllmmlx"}:
        if not (
            RUNTIME_CONFIG.llm_base_url
            or RUNTIME_CONFIG.text_base_url
            or RUNTIME_CONFIG.vision_base_url
        ):
            raise RuntimeError(
                "HYPERLOCAL_LLM_BASE_URL is required for vllm-mlx "
                "(or set HYPERLOCAL_TEXT_BASE_URL / HYPERLOCAL_VISION_BASE_URL)."
            )

    text_model = MODEL_CONFIG.text_model
    vision_model = MODEL_CONFIG.vision_model
    if provider in {"vllm_mlx", "vllmmlx"}:
        if "HYPERLOCAL_TEXT_MODEL" not in os.environ:
            text_model = "default"
        if "HYPERLOCAL_VISION_MODEL" not in os.environ:
            vision_model = "default"

    text_base_url = resolve_llm_base_url("text")
    vision_base_url = resolve_llm_base_url("vision")
    api_key = resolve_llm_api_key()

    return LLMClients(
        text_client=build_client(base_url=text_base_url, api_key=api_key),
        vision_client=build_client(base_url=vision_base_url, api_key=api_key),
        text_model=text_model,
        vision_model=vision_model,
        provider=provider,
        text_base_url=text_base_url,
        vision_base_url=vision_base_url,
    )
