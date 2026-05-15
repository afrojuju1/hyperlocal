from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    text_model: str = os.getenv("HYPERLOCAL_TEXT_MODEL", "qwen3:8b")


@dataclass(frozen=True)
class RuntimeConfig:
    llm_provider: str = os.getenv("HYPERLOCAL_LLM_PROVIDER", "ollama")
    llm_base_url: str | None = os.getenv("HYPERLOCAL_LLM_BASE_URL")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://100.111.132.114:11434/v1")
    ollama_api_key: str = os.getenv("OLLAMA_API_KEY", "ollama")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")
    image_provider: str = os.getenv("HYPERLOCAL_IMAGE_PROVIDER", "comfyui_bg")
    image_model: str = os.getenv("HYPERLOCAL_IMAGE_MODEL", "gpt-image-1")
    image_size: str = os.getenv("HYPERLOCAL_IMAGE_SIZE", "1024x1536")  # 6x9 aspect
    image_quality: str = os.getenv("HYPERLOCAL_IMAGE_QUALITY", "high")
    ollama_image_model: str = os.getenv("OLLAMA_IMAGE_MODEL", "x/z-image-turbo")
    ollama_image_timeout: float = float(os.getenv("OLLAMA_IMAGE_TIMEOUT", "600"))
    comfyui_api_url: str = os.getenv("COMFYUI_API_URL", "http://100.111.132.114:8188")
    comfyui_workflow_path: str = os.getenv(
        "COMFYUI_WORKFLOW_PATH", "comfyui/workflows/z_image_turbo_background.json"
    )
    comfyui_timeout: float = float(os.getenv("COMFYUI_TIMEOUT", "600"))
    comfyui_output_node: str | None = os.getenv("COMFYUI_OUTPUT_NODE")
    output_dir: str = os.getenv("HYPERLOCAL_OUTPUT_DIR", "output")
    max_image_attempts: int = int(os.getenv("HYPERLOCAL_MAX_IMAGE_ATTEMPTS", "3"))
    qc_enabled: bool = os.getenv("HYPERLOCAL_QC_ENABLED", "0") == "1"
    variants: int = int(os.getenv("HYPERLOCAL_VARIANTS", "1"))
    persist_enabled: bool = os.getenv("HYPERLOCAL_PERSIST_ENABLED", "0") == "1"
    database_url: str | None = os.getenv("DATABASE_URL")
    creative_run_poll_interval: float = float(os.getenv("HYPERLOCAL_CREATIVE_RUN_POLL_INTERVAL", "2"))
    creative_run_max_concurrent: int = int(os.getenv("HYPERLOCAL_CREATIVE_RUN_MAX_CONCURRENT", "1"))
    typst_bin: str = os.getenv("TYPST_BIN", "typst")


MODEL_CONFIG = ModelConfig()
RUNTIME_CONFIG = RuntimeConfig()
