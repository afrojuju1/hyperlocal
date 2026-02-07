from __future__ import annotations

import base64
import shutil
import subprocess
import tempfile
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


@dataclass
class OllamaImageConfig:
    model: str
    timeout: float


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


def _collect_images(directory: Path) -> list[Path]:
    image_suffixes = {".png", ".jpg", ".jpeg", ".webp"}
    return [path for path in directory.iterdir() if path.suffix.lower() in image_suffixes]


def generate_ollama_image(
    *,
    prompt: str,
    output_path: str,
    config: OllamaImageConfig,
) -> ImageResult:
    if shutil.which("ollama") is None:
        raise RuntimeError("ollama CLI not found in PATH")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=destination.parent) as tmp_dir:
        tmp_path = Path(tmp_dir)
        before = _collect_images(tmp_path)

        result = subprocess.run(
            ["ollama", "run", config.model, prompt],
            cwd=tmp_path,
            text=True,
            capture_output=True,
            timeout=config.timeout,
        )

        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join(part for part in [stdout, stderr] if part)
            raise RuntimeError(f"Ollama image generation failed.\n{detail}")

        after = _collect_images(tmp_path)
        new_images = sorted(
            [path for path in after if path not in before],
            key=lambda path: path.stat().st_mtime,
        )
        if not new_images:
            raise RuntimeError("Ollama did not produce an image file")

        latest = new_images[-1]
        shutil.move(str(latest), destination)

    return ImageResult(path=str(destination), revised_prompt=None)


def build_ollama_image_config(*, model: str, timeout: float) -> OllamaImageConfig:
    return OllamaImageConfig(model=model, timeout=timeout)
