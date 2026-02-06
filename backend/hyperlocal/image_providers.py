from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from hyperlocal.openai_helpers import ImageResult, generate_image


@dataclass
class SdxlConfig:
    api_url: str
    width: int
    height: int
    steps: int
    cfg_scale: float
    sampler: str


def _parse_size(size: str) -> tuple[int, int]:
    parts = size.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid image size: {size}")
    return int(parts[0]), int(parts[1])


def generate_sdxl_image(
    *,
    prompt: str,
    negative_prompt: str,
    output_path: str,
    config: SdxlConfig,
) -> ImageResult:
    payload: dict[str, Any] = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "steps": config.steps,
        "cfg_scale": config.cfg_scale,
        "width": config.width,
        "height": config.height,
        "sampler_name": config.sampler,
    }
    resp = httpx.post(config.api_url, json=payload, timeout=300.0)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("images"):
        raise RuntimeError("SDXL API returned no images")
    image_b64 = data["images"][0]
    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_b64))
    return ImageResult(path=output_path, revised_prompt=None)


def build_sdxl_config(
    *,
    api_url: str,
    size: str,
    steps: int,
    cfg_scale: float,
    sampler: str,
) -> SdxlConfig:
    width, height = _parse_size(size)
    return SdxlConfig(
        api_url=api_url,
        width=width,
        height=height,
        steps=steps,
        cfg_scale=cfg_scale,
        sampler=sampler,
    )
