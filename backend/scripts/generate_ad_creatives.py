from __future__ import annotations

"""
Generate ad-creative prompts, then generate images for those prompts.

This writes everything (prompts + negatives + images) as flat files into one run directory
under `output/` for easy viewing.

Examples:
  Smoothie (3 prompts + 3 images):
    cd backend
    uv run scripts/generate_ad_creatives.py --business-kind smoothie --count 3 --engine llm --format-hint flyer_poster --text-mode overlay --out-subdir smoothie_ad_creatives

  HVAC (3 prompts + 3 images), using Flux:
    cd backend
    uv run scripts/generate_ad_creatives.py --business-kind hvac --count 3 --engine llm --format-hint flyer_poster --text-mode overlay --out-subdir hvac_ad_creatives --image-model x/flux2-klein:latest

Notes:
  For ComfyUI-ready flyers with deterministic text overlay, use:
    uv run scripts/generate_comfyui_flyers.py
"""

import argparse
import json
import shlex
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.image_providers import (
    build_ollama_image_config,
    build_sdxl_config,
    generate_ollama_image,
    generate_sdxl_image,
)
from hyperlocal.openai_helpers import build_client, generate_image

from scripts.generate_ad_prompts import build_llm_prompts, build_template_prompts


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _normalize_provider(value: str) -> str:
    value = (value or "").strip().lower().replace("-", "_")
    if value in {"sdxl"}:
        return "sdxl"
    if value in {"openai"}:
        return "openai"
    if value in {"ollama"}:
        return "ollama"
    raise ValueError("image provider must be one of: ollama, sdxl, openai")


def write_flat_files(run_dir: Path, *, specs: list[object], meta: dict) -> None:
    ensure_dir(run_dir)
    (run_dir / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    (run_dir / "prompts.json").write_text(
        json.dumps([asdict(s) for s in specs], indent=2) + "\n"
    )
    for i, spec in enumerate(specs, start=1):
        prefix = f"{i:02d}__{spec.slug}"
        (run_dir / f"{prefix}.prompt.txt").write_text(spec.prompt + "\n")
        (run_dir / f"{prefix}.negative.txt").write_text(spec.negative_prompt + "\n")


def main() -> None:
    load_dotenv()

    smoothie_default_business = "Sunset Smoothie Co."
    smoothie_default_product = "Mango smoothie"
    smoothie_default_offer = "BUY 1 GET 1 50% OFF MANGO SMOOTHIES"
    hvac_default_business = "SunPeak HVAC"
    hvac_default_product = "AC tune-up"
    hvac_default_offer = "FREE AC TUNING FOR 30 DAYS"

    parser = argparse.ArgumentParser(
        description="Generate ad prompts and then generate images for them (flat files in one directory)."
    )
    parser.add_argument("--engine", choices=["llm", "template"], default="llm")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--business-kind", choices=["smoothie", "hvac"], default="smoothie")
    parser.add_argument("--text-mode", choices=["overlay", "in_image"], default="overlay")
    parser.add_argument(
        "--format-hint",
        choices=["ad_creative", "flyer", "poster", "flyer_poster"],
        default="flyer_poster",
    )
    parser.add_argument("--business-name", default=smoothie_default_business)
    parser.add_argument("--product", default=smoothie_default_product)
    parser.add_argument("--offer", default=smoothie_default_offer)
    parser.add_argument(
        "--image-provider",
        choices=["ollama", "sdxl", "openai"],
        default=RUNTIME_CONFIG.image_provider.lower(),
    )
    parser.add_argument(
        "--image-model",
        default=None,
        help="Override image model (ollama/openai). Defaults to env/config.",
    )
    parser.add_argument(
        "--out-subdir",
        default="ad_creatives",
        help="Output folder under output/ (default: ad_creatives).",
    )
    args = parser.parse_args()

    count = max(1, args.count)
    provider = _normalize_provider(args.image_provider)

    # If user switches to HVAC but didn't explicitly override business/product/offer,
    # apply HVAC defaults.
    if args.business_kind == "hvac":
        if args.business_name == smoothie_default_business:
            args.business_name = hvac_default_business
        if args.product == smoothie_default_product:
            args.product = hvac_default_product
        if args.offer == smoothie_default_offer:
            args.offer = hvac_default_offer

    meta_count = count
    if args.engine == "llm":
        specs = build_llm_prompts(
            business_kind=args.business_kind,
            business_name=args.business_name,
            offer=args.offer,
            product=args.product,
            text_mode=args.text_mode,
            format_hint=args.format_hint,
            count=count,
        )
    else:
        specs = build_template_prompts(
            business_kind=args.business_kind,
            business_name=args.business_name,
            offer=args.offer,
            product=args.product,
            text_mode=args.text_mode,
            format_hint=args.format_hint,
            count=count,
        )

    run_dir = Path(RUNTIME_CONFIG.output_dir) / args.out_subdir / timestamp()

    meta = {
        "created_at": datetime.now().isoformat(),
        "engine": args.engine,
        "count": meta_count,
        "business_kind": args.business_kind,
        "text_mode": args.text_mode,
        "format_hint": args.format_hint,
        "business_name": args.business_name,
        "product": args.product,
        "offer": args.offer,
        "llm_provider": RUNTIME_CONFIG.llm_provider,
        "text_model": MODEL_CONFIG.text_model,
        "image_provider": provider,
        "image_model": args.image_model,
        "command": " ".join(shlex.quote(p) for p in sys.argv),
    }

    write_flat_files(run_dir, specs=specs, meta=meta)

    # Generate images in the same directory as the prompts.
    if provider == "ollama":
        model = args.image_model or RUNTIME_CONFIG.ollama_image_model
        config = build_ollama_image_config(
            model=model,
            timeout=RUNTIME_CONFIG.ollama_image_timeout,
        )
        meta["image_model"] = model
        (run_dir / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")

        for i, spec in enumerate(specs, start=1):
            image_path = run_dir / f"{i:02d}__{spec.slug}.png"
            print(f"Generating image {i}/{len(specs)} -> {image_path}", flush=True)
            generate_ollama_image(prompt=spec.prompt, output_path=str(image_path), config=config)

    elif provider == "sdxl":
        config = build_sdxl_config(
            api_url=RUNTIME_CONFIG.sdxl_api_url,
            size=RUNTIME_CONFIG.image_size,
            steps=RUNTIME_CONFIG.sdxl_steps,
            cfg_scale=RUNTIME_CONFIG.sdxl_cfg_scale,
            sampler=RUNTIME_CONFIG.sdxl_sampler,
        )
        for i, spec in enumerate(specs, start=1):
            image_path = run_dir / f"{i:02d}__{spec.slug}.png"
            print(f"Generating image {i}/{len(specs)} -> {image_path}", flush=True)
            generate_sdxl_image(
                prompt=spec.prompt,
                negative_prompt=spec.negative_prompt,
                output_path=str(image_path),
                config=config,
            )

    else:  # openai
        if not RUNTIME_CONFIG.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set (required for openai image provider)")
        client = build_client(
            base_url=RUNTIME_CONFIG.openai_base_url,
            api_key=RUNTIME_CONFIG.openai_api_key,
        )
        model = args.image_model or RUNTIME_CONFIG.image_model
        meta["image_model"] = model
        (run_dir / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
        for i, spec in enumerate(specs, start=1):
            image_path = run_dir / f"{i:02d}__{spec.slug}.png"
            print(f"Generating image {i}/{len(specs)} -> {image_path}", flush=True)
            generate_image(
                client=client,
                prompt=spec.prompt,
                output_path=str(image_path),
                model=model,
                size=RUNTIME_CONFIG.image_size,
                quality=RUNTIME_CONFIG.image_quality,
            )

    print(f"Run complete: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
