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
class PromptSpec:
    slug: str
    title: str
    prompt: str


BUSINESS_NAME = "Sunset Smoothie Co."
OFFER_TEXT = "BUY 1 GET 1 FREE MANGO SMOOTHIES"
TEXT_RULES = (
    f"Text required: exact strings \"{BUSINESS_NAME}\" and "
    f"\"{OFFER_TEXT}\" only. Two lines only. Characters must be exactly: "
    "S u n s e t [space] S m o o t h i e [space] C o . "
    "and B U Y [space] 1 [space] G E T [space] 1 [space] F R E E "
    "[space] M A N G O [space] S M O O T H I E S. "
    "Plain sans-serif, high legibility, no stylization, no distortion, no ligatures. "
    "Render on a clean white nameplate, centered at the bottom, high contrast. "
    "One instance only, no duplicates. "
    "No other text, logos, labels, signage, decals, or watermarks."
)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_prompt_1() -> PromptSpec:
    return PromptSpec(
        slug="mango_bogo_hero",
        title="Mango BOGO Hero",
        prompt=(
            f"Create a smoothie shop ad creative for \"{BUSINESS_NAME}\". "
            "Show two tall clear mango smoothies side-by-side with condensation, "
            "fresh mango slices and a few berries, bright appetizing colors. "
            "Portrait 6x9, ad-ready with open space for copy. "
            f"{TEXT_RULES} "
            "No people, no clutter, no extra props."
        ),
    )


def build_prompt_2() -> PromptSpec:
    return PromptSpec(
        slug="mango_pour_bogo",
        title="Mango Pour BOGO",
        prompt=(
            f"Create a smoothie shop promo creative for \"{BUSINESS_NAME}\". "
            "Show a mango smoothie pour into a clear cup with a clean splash, "
            "mango slices in the foreground, bright tropical feel. "
            "Portrait 6x9, ad-ready with open space for copy. "
            f"{TEXT_RULES} "
            "No people, no clutter, no extra props."
        ),
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_prompt(path: Path, prompt: str) -> None:
    path.write_text(prompt)


def main() -> None:
    load_dotenv()

    run_dir = (
        Path(RUNTIME_CONFIG.output_dir) / "ollama" / "smoothie_ads" / timestamp()
    )
    ensure_dir(run_dir)

    config = build_ollama_image_config(
        model="x/flux2-klein:latest",
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    prompts = [build_prompt_1(), build_prompt_2()]
    for spec in prompts:
        image_path = run_dir / f"smoothie__{spec.slug}.png"
        prompt_path = run_dir / f"smoothie__{spec.slug}.txt"
        print(f"Generating Smoothie / {spec.title} -> {image_path}")
        generate_ollama_image(
            prompt=spec.prompt,
            output_path=str(image_path),
            config=config,
        )
        save_prompt(prompt_path, spec.prompt)
        print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
