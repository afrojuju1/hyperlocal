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
class PromptRecipe:
    slug: str
    title: str
    prompt: str


@dataclass(frozen=True)
class PromptVariant:
    slug: str
    title: str
    prompt: str


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def base_directive() -> str:
    return (
        "Photorealistic smoothie creative for a flyer. "
        "Portrait 6x9 composition, bright and appetizing. "
        "No text, letters, numbers, logos, labels, menus, or signage. "
        "No people, faces, or hands. No brand marks or packaging graphics. "
        "Unbranded clear cups only. High-quality lighting, crisp detail, clean styling."
    )


def build_recipes() -> list[PromptRecipe]:
    base = base_directive()
    return [
        PromptRecipe(
            slug="hero_cup",
            title="Hero Cup + Ingredients",
            prompt=(
                f"{base} "
                "Single clear smoothie cup with condensation, lid on. "
                "Surround with mango slices, citrus wedges, berries, and mint. "
                "Shallow depth of field, soft studio background, vibrant colors."
            ),
        ),
        PromptRecipe(
            slug="pour_splash",
            title="Pour / Splash Action",
            prompt=(
                f"{base} "
                "Smoothie pouring into a clear cup with dynamic splash. "
                "Mango and citrus pieces mid-air, motion frozen, studio lighting."
            ),
        ),
    ]


def build_variants() -> list[PromptVariant]:
    return [
        PromptVariant(
            slug="lighting_bright",
            title="Lighting: Bright Studio",
            prompt="Bright studio lighting, high-key, clean white bounce, crisp highlights.",
        ),
        PromptVariant(
            slug="ingredient_mango",
            title="Ingredient Focus: Mango",
            prompt="Mango-forward ingredients, rich golden mango tones, mango slices dominant.",
        ),
        PromptVariant(
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

    recipes = build_recipes()
    variants = build_variants()

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / "creatives_v2" / timestamp()
    ensure_dir(run_dir)

    model = "x/z-image-turbo"
    config = build_ollama_image_config(
        model=model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    for recipe in recipes:
        for variant in variants:
            prompt = f"{recipe.prompt} {variant.prompt}"
            filename = f"{recipe.slug}__{variant.slug}.png"
            image_path = run_dir / filename
            prompt_path = run_dir / f"{recipe.slug}__{variant.slug}.txt"

            print(f"Generating {recipe.title} / {variant.title} -> {image_path}")
            generate_ollama_image(
                prompt=prompt,
                output_path=str(image_path),
                config=config,
            )
            save_prompt(prompt_path, prompt)
            print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
