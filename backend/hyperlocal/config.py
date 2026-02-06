from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    text_model: str = os.getenv("HYPERLOCAL_TEXT_MODEL", "qwen2.5:7b")
    text_backup: str = os.getenv("HYPERLOCAL_TEXT_MODEL_BACKUP", "llama3.1:8b")
    vision_model: str = os.getenv("HYPERLOCAL_VISION_MODEL", "llama3.2-vision:latest")
    vision_backup: str = os.getenv("HYPERLOCAL_VISION_MODEL_BACKUP", "llava:latest")


@dataclass(frozen=True)
class RuntimeConfig:
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    ollama_api_key: str = os.getenv("OLLAMA_API_KEY", "ollama")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    image_provider: str = os.getenv("HYPERLOCAL_IMAGE_PROVIDER", "sdxl")
    image_model: str = os.getenv("HYPERLOCAL_IMAGE_MODEL", "gpt-image-1")
    image_size: str = os.getenv("HYPERLOCAL_IMAGE_SIZE", "1024x1536")  # 6x9 aspect
    image_quality: str = os.getenv("HYPERLOCAL_IMAGE_QUALITY", "high")
    sdxl_api_url: str = os.getenv(
        "SDXL_API_URL", "http://host.docker.internal:7860/sdapi/v1/txt2img"
    )
    sdxl_steps: int = int(os.getenv("SDXL_STEPS", "6"))
    sdxl_cfg_scale: float = float(os.getenv("SDXL_CFG_SCALE", "1.5"))
    sdxl_sampler: str = os.getenv("SDXL_SAMPLER", "Euler a")
    output_dir: str = os.getenv("HYPERLOCAL_OUTPUT_DIR", "output")
    max_image_attempts: int = int(os.getenv("HYPERLOCAL_MAX_IMAGE_ATTEMPTS", "3"))
    qc_enabled: bool = os.getenv("HYPERLOCAL_QC_ENABLED", "1") == "1"
    variants: int = int(os.getenv("HYPERLOCAL_VARIANTS", "1"))
    persist_enabled: bool = os.getenv("HYPERLOCAL_PERSIST_ENABLED", "0") == "1"
    database_url: str | None = os.getenv("DATABASE_URL")


MODEL_CONFIG = ModelConfig()
RUNTIME_CONFIG = RuntimeConfig()
