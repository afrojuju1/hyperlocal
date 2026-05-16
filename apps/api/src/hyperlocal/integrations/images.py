from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from hyperlocal.integrations.openai import ImageResult


@dataclass
class OllamaImageConfig:
    model: str
    timeout: float


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
