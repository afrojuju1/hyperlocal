from __future__ import annotations

from dotenv import load_dotenv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.pipeline import FlyerPipeline
from hyperlocal.schemas import (
    CreativeBrief,
    BusinessDetails,
    BusinessHours,
    BusinessDayHours,
)


def smoothie_shop_brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id=1,
        business_details=BusinessDetails(
            name="Sunset Smoothie Co.",
            address="214 W 7th St",
            city="Austin",
            state="TX",
            postal_code="78701",
            phone="(512) 555-0142",
            website="sunsetsmoothie.co",
            hours=BusinessHours(
                display="Mon-Sat 8am-8pm, Sun 9am-6pm",
                timezone="America/Chicago",
            ),
            service_area="Downtown Austin",
        ),
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

def real_estate_wholesaler_brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id=2,
        business_details=BusinessDetails(
            name="RapidKeys Home Buyers",
            address="3800 N Lamar Blvd, Ste 200",
            city="Austin",
            state="TX",
            postal_code="78756",
            phone="(512) 555-0134",
            website="rapidkeyshomebuyers.com",
            hours=BusinessHours(
                display="Mon-Fri 9am-6pm",
                timezone="America/Chicago",
            ),
            service_area="Austin Metro",
        ),
        product="We buy houses for cash",
        offer="Close in as little as 7 days. No repairs. No agent fees.",
        tone="trustworthy, direct, professional",
        cta="Get Cash Offer",
        size="6x9",
        audience="homeowners needing to sell fast",
        constraints=[
            "No people",
            "Highlight no repairs and no fees",
        ],
        brand_colors=["navy", "gold", "white"],
        style_keywords=["professional", "real-estate", "clean", "photographic"],
    )


def plumbing_hvac_brief() -> CreativeBrief:
    return CreativeBrief(
        campaign_id=3,
        business_details=BusinessDetails(
            name="Northside Plumbing & HVAC",
            address="9150 Burnet Rd, Ste 110",
            city="Austin",
            state="TX",
            postal_code="78758",
            phone="(512) 555-0199",
            website="northsideplumbinghvac.com",
            hours=BusinessHours(
                display="24/7 Emergency Service",
                timezone="America/Chicago",
            ),
            service_area="North & Central Austin",
        ),
        product="24/7 emergency plumbing and AC repair",
        offer="$79 service call. Free diagnostics with repair.",
        tone="reliable, bold, reassuring",
        cta="Call 24/7",
        size="6x9",
        audience="local homeowners and small businesses",
        constraints=[
            "No people",
            "Include 'Licensed & insured'",
            "Highlight same-day service",
        ],
        brand_colors=["blue", "red", "white"],
        style_keywords=["bold", "trustworthy", "industrial", "clean"],
    )


def main() -> None:
    load_dotenv()
    pipeline = FlyerPipeline()
    briefs = [
        smoothie_shop_brief(),
        real_estate_wholesaler_brief(),
        plumbing_hvac_brief(),
    ]
    for brief in briefs:
        name = brief.business_details.name if brief.business_details else "Unknown Business"
        print(f"Generating: {name}")
        result = pipeline.run(brief)
        print(f"Run complete: {result.output_dir}")
        for variant in result.variants:
            status = "PASS" if variant.qc_passed else "FAIL"
            print(f"Variant {variant.index:02d}: {status} -> {variant.image_path}")


if __name__ == "__main__":
    main()
