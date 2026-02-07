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
            slug="flat_lay",
            title="Ingredient Flat Lay",
            prompt=(
                f"{base} "
                "Top-down flat lay of sliced mango, citrus, berries, and mint. "
                "A smoothie cup partially visible at the edge. "
                "Clean white surface with subtle color accents, tidy arrangement."
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
        PromptRecipe(
            slug="counter_lifestyle",
            title="Counter Lifestyle",
            prompt=(
                f"{base} "
                "Cafe counter scene with two clear smoothie cups, fruit bowl nearby. "
                "Morning natural light, warm tone, shallow depth of field."
            ),
        ),
    ]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_prompt(path: Path, prompt: str) -> None:
    path.write_text(prompt)


def main() -> None:
    load_dotenv()

    models = ["x/flux2-klein", "x/z-image-turbo"]
    recipes = build_recipes()

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / "creatives_v1" / timestamp()
    ensure_dir(run_dir)

    for model in models:
        config = build_ollama_image_config(
            model=model,
            timeout=RUNTIME_CONFIG.ollama_image_timeout,
        )
        model_dir = run_dir / model.replace("/", "_")
        ensure_dir(model_dir)

        for recipe in recipes:
            recipe_dir = model_dir / recipe.slug
            ensure_dir(recipe_dir)
            image_path = recipe_dir / "creative.png"
            prompt_path = recipe_dir / "prompt.txt"

            print(f"Generating {recipe.title} with {model} -> {image_path}")
            generate_ollama_image(
                prompt=recipe.prompt,
                output_path=str(image_path),
                config=config,
            )
            save_prompt(prompt_path, recipe.prompt)
            print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
