from __future__ import annotations

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
    prompt: str


@dataclass(frozen=True)
class Variant:
    slug: str
    title: str
    prompt: str


@dataclass(frozen=True)
class BusinessConfig:
    slug: str
    name: str
    base_prompt: str
    directions: list[Direction]
    focus_variant_prompt: str


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def base_directive(*, allow_characters: bool, text_policy: str | None = None) -> str:
    parts = [
        "Commercial creative image, product photo style.",
        "Portrait 6x9 composition.",
        "No people, human faces, human hands, or human-like figures.",
        "No uniforms, clothing, gloves, helmets, or tools in use.",
        "No brand marks or packaging graphics.",
        "No icons, symbols, illustrations, diagrams, or UI elements.",
        "High-quality lighting, crisp detail, clean styling.",
    ]
    if text_policy:
        parts.append(text_policy)
        parts.append("No logos, labels, decals, or watermarks.")
    else:
        parts.append(
            "No text of any kind (letters, numbers, symbols, glyphs, or CJK characters)."
        )
        parts.append(
            "No logos, labels, menus, signage, decals, stickers, engravings, or watermarks."
        )
        parts.append("Blank surfaces only, no printed markings.")
    if allow_characters:
        parts.append(
            "Non-human mascots or stylized characters are allowed when direction calls for it."
        )
    return " ".join(parts)


def build_businesses() -> list[BusinessConfig]:
    smoothie_directive = base_directive(allow_characters=False)
    smoothie_base = (
        f"{smoothie_directive} "
        "Photorealistic smoothie creative. "
        "Theme: fresh tropical smoothie shop. "
        "Bright and appetizing. "
        "Palette: coral, mint green, sunny yellow, white. "
        "Unbranded clear cups only. "
        "Avoid: labels, branding, menus, signage."
    )
    plumbing_directive = base_directive(allow_characters=True)
    plumbing_base = (
        f"{plumbing_directive} "
        "Plumbing & HVAC advertising hero image, flyer-ready background (no text). "
        "Clean, technical, trustworthy, professional service vibe. "
        "Blank surfaces only, avoid stickers or printed markings. "
        "Avoid: brand marks, truck logos, uniforms, clothing, mascots, balloons, workers. "
        "Avoid vehicles, icons, toys, and props unrelated to plumbing. "
        "Palette: neutral metallic steel and copper with soft cool-gray gradients. "
    )

    return [
        BusinessConfig(
            slug="smoothie",
            name="Smoothie",
            base_prompt=smoothie_base,
            directions=[
                Direction(
                    slug="hero_cup",
                    title="Hero Cup + Ingredients",
                    prompt=(
                        "Single clear smoothie cup with condensation, lid on. "
                        "Surround with mango slices, citrus wedges, berries, and mint. "
                        "Shallow depth of field, soft studio background, vibrant colors."
                    ),
                ),
                Direction(
                    slug="pour_splash",
                    title="Pour / Splash Action",
                    prompt=(
                        "Smoothie pouring into a clear cup with dynamic splash. "
                        "Mango and citrus pieces mid-air, motion frozen, studio lighting."
                    ),
                ),
            ],
            focus_variant_prompt=(
                "Mango-forward ingredients, rich golden mango tones, mango slices dominant."
            ),
        ),
        BusinessConfig(
            slug="plumbing",
            name="Plumbing",
            base_prompt=plumbing_base,
            directions=[
                Direction(
                    slug="pipe_hero",
                    title="Pipe Hero",
                    prompt=(
                        "Hero composition inside a clean under-sink cabinet, service-ready scene. "
                        "Focus on a copper P-trap, shutoff valves, and braided supply lines; "
                        "everything clean, organized, and minimal. "
                        "Add a folded solid-color blue towel as a subtle accent (no patterns). "
                        "Subtle water droplets for energy, no spills. "
                        "Foreground sharp, background softly blurred, large negative space in upper half. "
                        "Soft directional lighting, gentle gradients, grounded shadows, cinematic depth. "
                        "No people, no uniforms, no clothing, no gloves, no tools in use. "
                        "No mascots, no balloons, no spheres, no vehicles, no icons, no toys."
                    ),
                ),
                Direction(
                    slug="mascot_hero",
                    title="Mascot Hero",
                    prompt=(
                        "Friendly non-human mascot character (robot or otter) holding a wrench. "
                        "Placed beside clean pipes and fittings with subtle water droplets. "
                        "Stylized 3D or anime-inspired render, clean studio background."
                    ),
                ),
            ],
            focus_variant_prompt=(
                "Copper-forward materials, warm metallic tones, clean fittings in focus."
            ),
        ),
    ]


def build_variants(focus_prompt: str) -> list[Variant]:
    return [
        Variant(
            slug="lighting_bright",
            title="Lighting: Bright Studio",
            prompt="Bright studio lighting, high-key, clean white bounce, crisp highlights.",
        ),
        Variant(
            slug="focus_primary",
            title="Focus: Primary Ingredient/Material",
            prompt=focus_prompt,
        ),
        Variant(
            slug="composition_wide",
            title="Composition: Wide Negative Space",
            prompt="Wider composition with generous negative space for future text overlay.",
        ),
    ]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_prompt(path: Path, prompt: str) -> None:
    path.write_text(prompt)


def main() -> None:
    load_dotenv()

    businesses = build_businesses()

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / "creatives_v3" / timestamp()
    ensure_dir(run_dir)

    model = RUNTIME_CONFIG.ollama_image_model
    config = build_ollama_image_config(
        model=model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    for business in businesses:
        variants = build_variants(business.focus_variant_prompt)
        for direction in business.directions:
            for variant in variants:
                prompt = f"{business.base_prompt} {direction.prompt} {variant.prompt}"
                filename = f"{business.slug}__{direction.slug}__{variant.slug}.png"
                image_path = run_dir / filename
                prompt_path = run_dir / f"{business.slug}__{direction.slug}__{variant.slug}.txt"

                print(
                    f"Generating {business.name} / {direction.title} / {variant.title} -> {image_path}"
                )
                generate_ollama_image(
                    prompt=prompt,
                    output_path=str(image_path),
                    config=config,
                )
                save_prompt(prompt_path, prompt)
                print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
