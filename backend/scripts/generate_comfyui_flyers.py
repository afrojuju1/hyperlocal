from __future__ import annotations

"""
ComfyUI-only flyer pipeline runner.

This generates ready-to-go flyer images via ComfyUI (background + deterministic text overlays)
and writes everything as flat files in one directory.

Examples:
  HVAC (3 flyer variants):
    cd backend
    uv run scripts/generate_comfyui_flyers.py --business hvac --variants 3

  Smoothie (3 flyer variants):
    cd backend
    uv run scripts/generate_comfyui_flyers.py --business smoothie --variants 3

  Override checkpoint + sampler knobs (workflow is a template):
    cd backend
    uv run scripts/generate_comfyui_flyers.py --business hvac --ckpt "JuggernautXL_v9.safetensors" --steps 32 --cfg 5.5 --sampler euler --scheduler normal

Notes:
  The default workflow is `comfyui/workflows/flyer_ad_v1_template.json` which adds
  a white body card and footer card for more "ad-ready" layouts.
"""

import argparse
from pathlib import Path
import sys
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.comfyui_flyer_pipeline import ComfyFlyerPipeline, ComfyFlyerSettings
from hyperlocal.schemas import BusinessDetails, CreativeBrief


def hvac_brief(*, business_name: str, offer: str) -> CreativeBrief:
    return CreativeBrief(
        business_details=BusinessDetails(name=business_name),
        product="AC tune-up",
        offer=offer,
        tone="trustworthy, direct, clean",
        cta="Schedule Now",
        audience="local homeowners",
        constraints=["No people", "High contrast for readability"],
        brand_colors=["sky blue", "navy", "white"],
        style_keywords=["clean", "modern", "trustworthy", "photographic"],
    )


def smoothie_brief(*, business_name: str, offer: str) -> CreativeBrief:
    return CreativeBrief(
        business_details=BusinessDetails(name=business_name),
        product="Mango smoothie",
        offer=offer,
        tone="bright, fresh, upbeat",
        cta="Order Today",
        audience="local families and gym-goers",
        constraints=["No people", "High contrast for readability"],
        brand_colors=["coral", "mint green", "sunny yellow", "white"],
        style_keywords=["fresh", "modern", "clean", "tropical", "photographic"],
    )


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate ready-to-go flyers via ComfyUI only.")
    parser.add_argument("--business", choices=["hvac", "smoothie"], default="hvac")
    parser.add_argument("--variants", type=int, default=3)
    parser.add_argument("--business-name", default=None)
    parser.add_argument("--offer", default=None)
    parser.add_argument("--out-subdir", default="comfyui_flyers")
    parser.add_argument("--comfyui-api-url", default=None)
    parser.add_argument("--workflow", default=None, help="Override workflow template path.")

    # Workflow knobs (flyer_ad_v1_template.json supports these).
    parser.add_argument("--ckpt", default="sd_xl_base_1.0.safetensors")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--steps", type=int, default=28)
    parser.add_argument("--cfg", type=float, default=5.5)
    parser.add_argument("--sampler", default="dpmpp_2m_sde")
    parser.add_argument("--scheduler", default="karras")
    parser.add_argument("--denoise", type=float, default=1.0)
    args = parser.parse_args()

    if args.business == "hvac":
        name = args.business_name or "SunPeak HVAC"
        offer = args.offer or "FREE AC TUNING FOR 30 DAYS"
        brief = hvac_brief(business_name=name, offer=offer)
    else:
        name = args.business_name or "Sunset Smoothie Co."
        offer = args.offer or "BUY 1 GET 1 50% OFF MANGO SMOOTHIES"
        brief = smoothie_brief(business_name=name, offer=offer)

    settings = ComfyFlyerSettings(
        ckpt_name=args.ckpt,
        seed=args.seed,
        steps=args.steps,
        cfg=args.cfg,
        sampler_name=args.sampler,
        scheduler=args.scheduler,
        denoise=args.denoise,
    )

    pipeline = ComfyFlyerPipeline(
        comfyui_api_url=args.comfyui_api_url,
        workflow_path=args.workflow,
    )
    result = pipeline.run(brief, variants=args.variants, out_subdir=args.out_subdir, settings=settings)
    print(result.output_dir)


if __name__ == "__main__":
    main()
