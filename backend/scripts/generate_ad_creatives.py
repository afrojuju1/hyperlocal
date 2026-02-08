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

  ComfyUI background-only (3 prompts + 3 images):
    cd backend
    uv run scripts/generate_ad_creatives.py --business-kind hvac --count 3 --engine llm --image-provider comfyui --comfyui-api-url http://127.0.0.1:8188 --out-subdir hvac_comfyui_ad_creatives
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
from hyperlocal.comfyui_provider import (
    build_comfyui_config,
    generate_comfyui_background_image,
    generate_comfyui_image,
)
from hyperlocal.openai_helpers import build_client, generate_image

from hyperlocal.schemas import BrandStyle, BusinessDetails, CopyVariant, CreativeBrief

from scripts.generate_ad_prompts import PromptSpec, build_llm_prompts, build_template_prompts


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
    if value in {"comfyui", "comfy_ui", "comfy"}:
        return "comfyui"
    raise ValueError("image provider must be one of: ollama, sdxl, openai, comfyui")


def _resolve_repo_relative(path: str) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        return str(candidate)
    # Resolve relative workflow paths against repo root so callers can run from `backend/`.
    repo_root = ROOT.parent
    return str((repo_root / candidate).resolve())


def _default_brand_style(kind: str) -> BrandStyle:
    if kind == "hvac":
        return BrandStyle(
            palette=["sky blue", "navy", "white"],
            style_keywords=["clean", "modern", "trustworthy", "photographic"],
            layout_guidance="Large clean areas for headline and CTA; keep background minimal and uncluttered.",
            typography_guidance="Bold sans-serif headline, high contrast, generous spacing.",
        )
    return BrandStyle(
        palette=["coral", "mint green", "sunny yellow", "white"],
        style_keywords=["fresh", "bright", "modern", "tropical", "photographic"],
        layout_guidance="Large clean focal area with ample negative space for headline and CTA.",
        typography_guidance="Bold sans-serif headline, high contrast, generous spacing.",
    )


def _default_copy(kind: str, *, business_name: str, offer: str) -> CopyVariant:
    # Keep this short and legible; ComfyUI overlay will handle layout.
    if kind == "hvac":
        headline = "FREE AC TUNING"
        subhead = "For 30 Days Only"
        body = "Book your free AC tuning today. Fast local service. Limited-time offer."
        cta = "Schedule Now"
        disclaimer = "Limited time. Terms apply."
    else:
        headline = "MANGO DEAL"
        subhead = "Limited Time Offer"
        body = f"{offer}. Fresh, cold, and made to order."
        cta = "Order Today"
        disclaimer = "Limited time. While supplies last."
    return CopyVariant(
        headline=headline,
        subhead=subhead,
        body=body,
        cta=cta,
        disclaimer=disclaimer,
    )


def _brief_from_args(
    *,
    kind: str,
    business_name: str,
    product: str,
    offer: str,
    cta: str,
) -> CreativeBrief:
    style = _default_brand_style(kind)
    return CreativeBrief(
        business_details=BusinessDetails(name=business_name),
        product=product,
        offer=offer,
        tone="clean, modern, direct-response",
        cta=cta,
        constraints=["No people", "High contrast for readability"],
        brand_colors=style.palette,
        style_keywords=style.style_keywords,
    )


def _spec_from_custom_prompt(
    *,
    business_kind: str,
    business_name: str,
    product: str,
    offer: str,
    format_hint: str,
    text_mode: str,
    prompt: str,
    negative_prompt: str,
) -> PromptSpec:
    return PromptSpec(
        slug="custom",
        title="Custom Prompt",
        prompt=prompt.strip(),
        negative_prompt=negative_prompt.strip(),
        text_mode=text_mode,
        format_hint=format_hint,
        business_kind=business_kind,
        business_name=business_name,
        offer=offer,
        product=product,
    )


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
        choices=["ollama", "sdxl", "openai", "comfyui"],
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
    parser.add_argument(
        "--comfyui-api-url",
        default=RUNTIME_CONFIG.comfyui_api_url,
        help="ComfyUI API URL (default from env/config).",
    )
    parser.add_argument(
        "--comfyui-kind",
        choices=["background", "flyer"],
        default="background",
        help="ComfyUI rendering mode: background-only or full flyer with overlays.",
    )
    parser.add_argument(
        "--comfyui-workflow",
        default=None,
        help="Workflow JSON template path (repo-relative). Defaults depend on --comfyui-kind.",
    )
    parser.add_argument(
        "--comfyui-timeout",
        type=float,
        default=RUNTIME_CONFIG.comfyui_timeout,
        help="ComfyUI timeout in seconds (default from env/config).",
    )
    parser.add_argument(
        "--comfyui-output-node",
        default=RUNTIME_CONFIG.comfyui_output_node,
        help="Optional ComfyUI output node id/name to prefer when downloading images.",
    )
    parser.add_argument(
        "--prompt",
        default=None,
        help="Optional: provide a single custom prompt (skips prompt generation).",
    )
    parser.add_argument(
        "--negative-prompt",
        default=None,
        help="Optional: provide a single custom negative prompt (used with --prompt).",
    )
    parser.add_argument("--headline", default=None, help="ComfyUI flyer mode override.")
    parser.add_argument("--subhead", default=None, help="ComfyUI flyer mode override.")
    parser.add_argument("--body", default=None, help="ComfyUI flyer mode override.")
    parser.add_argument("--cta", default=None, help="ComfyUI flyer mode override.")
    parser.add_argument("--disclaimer", default=None, help="ComfyUI flyer mode override.")
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

    if args.prompt:
        negative_prompt = args.negative_prompt or "Avoid text, logos, watermarks, people, faces, hands, clutter."
        specs = [
            _spec_from_custom_prompt(
                business_kind=args.business_kind,
                business_name=args.business_name,
                product=args.product,
                offer=args.offer,
                format_hint=args.format_hint,
                text_mode=args.text_mode,
                prompt=args.prompt,
                negative_prompt=negative_prompt,
            )
        ]
        count = 1
        meta_count = 1
    else:
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
        "comfyui_api_url": args.comfyui_api_url if provider == "comfyui" else None,
        "comfyui_workflow": args.comfyui_workflow if provider == "comfyui" else None,
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

    elif provider == "comfyui":
        if args.comfyui_workflow:
            workflow_path = _resolve_repo_relative(args.comfyui_workflow)
        else:
            workflow_path = _resolve_repo_relative(
                "comfyui/workflows/flyer_full.json"
                if args.comfyui_kind == "flyer"
                else "comfyui/workflows/ad_background.json"
            )
        config = build_comfyui_config(
            api_url=args.comfyui_api_url,
            workflow_path=workflow_path,
            size=RUNTIME_CONFIG.image_size,
            timeout=args.comfyui_timeout,
            output_node=args.comfyui_output_node,
        )
        if args.comfyui_kind == "flyer":
            style = _default_brand_style(args.business_kind)
            copy = _default_copy(
                args.business_kind, business_name=args.business_name, offer=args.offer
            )
            if args.headline:
                copy = copy.model_copy(update={"headline": args.headline})
            if args.subhead:
                copy = copy.model_copy(update={"subhead": args.subhead})
            if args.body:
                copy = copy.model_copy(update={"body": args.body})
            if args.cta:
                copy = copy.model_copy(update={"cta": args.cta})
            if args.disclaimer:
                copy = copy.model_copy(update={"disclaimer": args.disclaimer})
            brief = _brief_from_args(
                kind=args.business_kind,
                business_name=args.business_name,
                product=args.product,
                offer=args.offer,
                cta=copy.cta,
            )
            (run_dir / "copy.json").write_text(json.dumps(copy.model_dump(), indent=2) + "\n")
            (run_dir / "brand_style.json").write_text(json.dumps(style.model_dump(), indent=2) + "\n")

            for i, spec in enumerate(specs, start=1):
                image_path = run_dir / f"{i:02d}__{spec.slug}.png"
                print(f"Generating image {i}/{len(specs)} -> {image_path}", flush=True)
                generate_comfyui_image(
                    prompt=spec.prompt,
                    negative_prompt=spec.negative_prompt,
                    output_path=str(image_path),
                    config=config,
                    brief=brief,
                    style=style,
                    copy=copy,
                )
        else:
            # Keep per-image seeds stable within a run, but distinct across images.
            base_seed = int(datetime.now().strftime("%Y%m%d%H%M%S"))
            for i, spec in enumerate(specs, start=1):
                image_path = run_dir / f"{i:02d}__{spec.slug}.png"
                seed = base_seed + i
                print(f"Generating image {i}/{len(specs)} -> {image_path}", flush=True)
                generate_comfyui_background_image(
                    prompt=spec.prompt,
                    negative_prompt=spec.negative_prompt,
                    output_path=str(image_path),
                    config=config,
                    seed=seed,
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
