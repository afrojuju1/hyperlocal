from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from dotenv import load_dotenv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.image_providers import build_ollama_image_config, generate_ollama_image


@dataclass(frozen=True)
class Direction:
    slug: str
    title: str
    subject: str
    scene: str
    composition: str
    lighting: str
    style: str
    constraints: str


@dataclass(frozen=True)
class BusinessConfig:
    slug: str
    name: str
    directions: list[Direction]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_prompt(direction: Direction) -> str:
    # Advanced prompt formula merged into a single prompt string.
    sections = [
        f"Subject: {direction.subject}",
        f"Scene: {direction.scene}",
        f"Composition: {direction.composition}",
        f"Lighting: {direction.lighting}",
        f"Style: {direction.style}",
        f"Constraints: {direction.constraints}",
    ]
    return " ".join(sections)


def build_businesses() -> list[BusinessConfig]:
    smoothie_constraints = (
        "No text, logos, labels, menus, signage, watermarks, or packaging graphics. "
        "No people, faces, or hands. Unbranded clear cups only. "
        "No icons, illustrations, or UI elements."
    )
    plumbing_constraints = (
        "Text required: exact string \"Stan & Sons Plumbing\" "
        "(case and punctuation). Characters must be exactly: "
        "S t a n [space] & [space] S o n s [space] P l u m b i n g. "
        "English-only, Latin letters only, no diacritics. "
        "Single line, plain sans-serif, high legibility, no stylization, "
        "no ligatures, no drop shadow, no distortion. "
        "Render on a plain white rectangular nameplate with black text, "
        "centered, large font size, high contrast. "
        "Place the nameplate bottom-centered only. One instance of the text. "
        "Do not omit, replace, or add characters. "
        "No other text, logos, labels, signage, decals, or watermarks. "
        "No people, faces, hands, uniforms, or tools in use. "
        "No vehicles, icons, mascots, balloons, or unrelated props."
    )

    real_estate_constraints = (
        "Text required: exact string \"RapidKeys Home Buyers\" "
        "(case and punctuation). Characters must be exactly: "
        "R a p i d K e y s [space] H o m e [space] B u y e r s. "
        "English-only, Latin letters only, no diacritics. "
        "Single line, plain sans-serif, high legibility, no stylization, "
        "no ligatures, no drop shadow, no distortion. "
        "Render on a plain white rectangular nameplate with black text, "
        "centered, large font size, high contrast. "
        "Place the nameplate bottom-centered only. One instance of the text. "
        "Do not omit, replace, or add characters. "
        "No other text, logos, labels, signage, decals, or watermarks. "
        "No people, faces, or hands. No vehicles."
    )

    return [
        BusinessConfig(
            slug="smoothie",
            name="Smoothie",
            directions=[
                Direction(
                    slug="hero_cup",
                    title="Hero Cup",
                    subject="Single clear smoothie cup with condensation, mango-forward.",
                    scene="Fresh tropical prep surface with mango, citrus, berries, mint.",
                    composition=(
                        "Portrait 6x9, hero on lower-left third, generous negative space "
                        "top-right for future copy."
                    ),
                    lighting="High-key studio softbox with gentle rim light and crisp highlights.",
                    style="Photorealistic commercial food photography, clean, appetizing, vivid.",
                    constraints=smoothie_constraints,
                ),
                Direction(
                    slug="pour_splash",
                    title="Pour Splash",
                    subject="Smoothie pouring into a clear cup with a dynamic splash arc.",
                    scene="Minimal white studio surface with floating mango/citrus slices.",
                    composition=(
                        "Portrait 6x9, action centered low, negative space in upper half."
                    ),
                    lighting="Crisp studio lighting, motion frozen, sparkling droplets.",
                    style="Photorealistic advertising shot, sharp detail, energetic.",
                    constraints=smoothie_constraints,
                ),
            ],
        ),
        BusinessConfig(
            slug="real_estate",
            name="Real Estate",
            directions=[
                Direction(
                    slug="home_exterior",
                    title="Home Exterior",
                    subject="Clean modern single-family home exterior, warm and inviting.",
                    scene="Quiet residential street, soft daylight, manicured lawn.",
                    composition=(
                        "Portrait 6x9, house in lower/mid frame, strong negative space up top. "
                        "Bottom-centered nameplate only."
                    ),
                    lighting="Bright natural daylight, soft shadows, high clarity.",
                    style=(
                        "Photorealistic real-estate advertising hero image, "
                        "trustworthy and professional."
                    ),
                    constraints=real_estate_constraints,
                ),
                Direction(
                    slug="front_door",
                    title="Front Door Detail",
                    subject="Elegant front door with fresh paint and clean porch detail.",
                    scene="Neutral home exterior, subtle greenery, no signage.",
                    composition=(
                        "Portrait 6x9, door in lower frame, negative space above. "
                        "Bottom-centered nameplate only."
                    ),
                    lighting="Soft golden-hour light, warm highlights, gentle contrast.",
                    style=(
                        "Photorealistic advertising hero image, calm and premium."
                    ),
                    constraints=real_estate_constraints,
                ),
            ],
        ),
        BusinessConfig(
            slug="plumbing",
            name="Plumbing",
            directions=[
                Direction(
                    slug="service_hero",
                    title="Service Hero",
                    subject="Clean copper P-trap with shutoff valves and braided supply lines.",
                    scene=(
                        "Clean modern bathroom vanity with a hint of sink edge, "
                        "service-ready plumbing visible, minimal environment."
                    ),
                    composition=(
                        "Portrait 6x9, hero in lower third, soft negative space above. "
                        "Bottom-centered nameplate only."
                    ),
                    lighting="Soft directional light, crisp highlights, gentle shadow falloff.",
                    style=(
                        "Photorealistic service advertisement, premium and trustworthy, "
                        "not a catalog product shot. Heroic composition, ad-like polish."
                    ),
                    constraints=plumbing_constraints,
                ),
                Direction(
                    slug="faucet_detail",
                    title="Faucet Detail",
                    subject=(
                        "Polished chrome faucet with subtle water droplets and clean sink edge."
                    ),
                    scene=(
                        "Modern sink area with a subtle water flow sparkle, "
                        "neutral background, minimal props."
                    ),
                    composition=(
                        "Portrait 6x9, faucet mid-lower frame, strong negative space up top. "
                        "Bottom-centered nameplate only."
                    ),
                    lighting="Softbox lighting, gentle highlights, controlled reflections.",
                    style=(
                        "Photorealistic advertising hero image, clean and modern, "
                        "not a catalog product shot. Heroic composition, ad-like polish."
                    ),
                    constraints=plumbing_constraints,
                ),
            ],
        ),
    ]


def resolve_businesses(target: str, businesses: list[BusinessConfig]) -> list[BusinessConfig]:
    if target == "all":
        return businesses
    selected = [b for b in businesses if b.slug == target]
    if not selected:
        raise ValueError(f"Unknown business '{target}'. Options: all, " + ", ".join(b.slug for b in businesses))
    return selected


def resolve_directions(target: str | None, directions: list[Direction]) -> list[Direction]:
    if not target:
        return directions
    requested = {slug.strip() for slug in target.split(",") if slug.strip()}
    selected = [d for d in directions if d.slug in requested]
    if not selected:
        raise ValueError(
            "Unknown direction(s). Options: " + ", ".join(d.slug for d in directions)
        )
    return selected


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Generate creatives using the advanced Z-Image prompt formula."
    )
    parser.add_argument(
        "--business",
        default="all",
        help="smoothie, plumbing, real_estate, or all",
    )
    parser.add_argument(
        "--direction",
        default=None,
        help="comma-separated direction slugs (e.g., hero_cup,service_hero)",
    )
    parser.add_argument(
        "--model",
        default=RUNTIME_CONFIG.ollama_image_model,
        help="Ollama image model (default from env/config).",
    )
    args = parser.parse_args()

    businesses = resolve_businesses(args.business, build_businesses())

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / "creatives_advanced" / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    config = build_ollama_image_config(
        model=args.model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    for business in businesses:
        directions = resolve_directions(args.direction, business.directions)
        for direction in directions:
            prompt = build_prompt(direction)
            filename = f"{business.slug}__{direction.slug}.png"
            image_path = run_dir / filename
            prompt_path = run_dir / f"{business.slug}__{direction.slug}.txt"

            print(f"Generating {business.name} / {direction.title} -> {image_path}")
            generate_ollama_image(
                prompt=prompt,
                output_path=str(image_path),
                config=config,
            )
            prompt_path.write_text(prompt)
            print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
