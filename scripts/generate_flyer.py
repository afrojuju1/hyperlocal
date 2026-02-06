from __future__ import annotations

from dotenv import load_dotenv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.pipeline import FlyerPipeline
from hyperlocal.schemas import CreativeBrief


def smoothie_shop_brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id=1,
        business_name="Sunset Smoothie Co.",
        business_url="https://example.com",
        product="Fresh smoothies and acai bowls",
        offer="Buy one smoothie, get 50% off the second",
        tone="bright, healthy, upbeat",
        cta="Order Today",
        size="6x9",
        audience="local families and gym-goers",
        constraints=[
            "No people",
            "High contrast for readability",
            "Include price/offer clearly",
        ],
        brand_colors=["coral", "mint green", "sunny yellow", "white"],
        style_keywords=["fresh", "modern", "clean", "tropical"],
    )


def main() -> None:
    load_dotenv()
    pipeline = FlyerPipeline()
    brief = smoothie_shop_brief()
    result = pipeline.run(brief)
    print(f"Run complete: {result.output_dir}")
    for variant in result.variants:
        status = "PASS" if variant.qc_passed else "FAIL"
        print(f"Variant {variant.index:02d}: {status} -> {variant.image_path}")


if __name__ == "__main__":
    main()
