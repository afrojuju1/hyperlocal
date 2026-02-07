from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MODELS = ["x/z-image-turbo", "x/flux2-klein"]
DEFAULT_PROMPTS = [
    "A storefront sign that says \"BAKERY\" in gold letters, photorealistic",
    "A neon sign reading \"OPEN 24 HOURS\" in a rainy city alley at night",
]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test Ollama image generation with one or more models.",
    )
    parser.add_argument(
        "--model",
        action="append",
        dest="models",
        help="Model name (repeatable). Defaults to x/z-image-turbo and x/flux2-klein.",
    )
    parser.add_argument(
        "--prompt",
        action="append",
        dest="prompts",
        help=(
            "Prompt text (repeatable). If one prompt is provided, it is reused for all models. "
            "If multiple prompts are provided, the count must match models."
        ),
    )
    parser.add_argument(
        "--out-dir",
        default="output/ollama",
        help="Directory to write images under (relative to repo root).",
    )
    return parser.parse_args()


def ensure_ollama() -> None:
    if shutil.which("ollama") is None:
        print("Error: ollama CLI not found in PATH.", file=sys.stderr)
        print("Install Ollama and ensure the 'ollama' command is available.", file=sys.stderr)
        sys.exit(1)


def normalize_prompts(models: list[str], prompts: list[str] | None) -> list[str]:
    if not prompts:
        if len(models) <= len(DEFAULT_PROMPTS):
            return DEFAULT_PROMPTS[: len(models)]
        return [DEFAULT_PROMPTS[0]] * len(models)
    if len(prompts) == 1:
        return prompts * len(models)
    if len(prompts) != len(models):
        print(
            "Error: number of prompts must be 1 or match the number of models.",
            file=sys.stderr,
        )
        sys.exit(1)
    return prompts


def collect_image_files(directory: Path) -> set[Path]:
    return {p for p in directory.iterdir() if p.suffix.lower() in IMAGE_SUFFIXES}


def run_model(model: str, prompt: str, out_dir: Path) -> int:
    model_dir = out_dir / model.replace("/", "_")
    model_dir.mkdir(parents=True, exist_ok=True)

    before = collect_image_files(model_dir)

    cmd = ["ollama", "run", model, prompt]
    print(f"\nRunning: {' '.join(cmd)}")
    result = subprocess.run(
        cmd,
        cwd=model_dir,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout.rstrip())
    if result.stderr:
        print(result.stderr.rstrip(), file=sys.stderr)

    if result.returncode != 0:
        print(f"Command failed with exit code {result.returncode}.", file=sys.stderr)
        return result.returncode

    after = collect_image_files(model_dir)
    new_images = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_images:
        latest = new_images[-1].relative_to(REPO_ROOT)
        print(f"Saved image: {latest}")
    else:
        relative = model_dir.relative_to(REPO_ROOT)
        print(
            "No new image file detected. If your terminal supports inline images,"
            " it may have rendered directly. Check the directory:",
        )
        print(f"  {relative}")

    return 0


def main() -> None:
    args = parse_args()
    ensure_ollama()

    models = args.models or DEFAULT_MODELS
    prompts = normalize_prompts(models, args.prompts)

    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    exit_code = 0
    for model, prompt in zip(models, prompts):
        code = run_model(model, prompt, out_dir)
        if code != 0:
            exit_code = code
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
