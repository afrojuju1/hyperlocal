from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.openai_helpers import build_client


@dataclass(frozen=True)
class LLMClients:
    text_client: OpenAI
    text_model: str
    provider: str
    base_url: str


def _normalize_provider(provider: str) -> str:
    provider = provider.strip().lower().replace("-", "_")
    return provider or "ollama"


def resolve_llm_base_url(provider: str | None = None) -> str:
    provider = _normalize_provider(provider or RUNTIME_CONFIG.llm_provider)
    if RUNTIME_CONFIG.llm_base_url:
        return RUNTIME_CONFIG.llm_base_url
    if provider == "openai" and RUNTIME_CONFIG.openai_base_url:
        return RUNTIME_CONFIG.openai_base_url
    return RUNTIME_CONFIG.ollama_base_url


def resolve_llm_api_key(provider: str | None = None) -> str:
    provider = _normalize_provider(provider or RUNTIME_CONFIG.llm_provider)
    if provider == "openai" and RUNTIME_CONFIG.openai_api_key:
        return RUNTIME_CONFIG.openai_api_key
    return RUNTIME_CONFIG.ollama_api_key or "ollama"


def build_llm_clients() -> LLMClients:
    provider = _normalize_provider(RUNTIME_CONFIG.llm_provider)
    text_model = MODEL_CONFIG.text_model

    base_url = resolve_llm_base_url(provider)
    api_key = resolve_llm_api_key(provider)

    return LLMClients(
        text_client=build_client(base_url=base_url, api_key=api_key),
        text_model=text_model,
        provider=provider,
        base_url=base_url,
    )
