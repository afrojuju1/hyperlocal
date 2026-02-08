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


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


BUSINESS_NAME = "SunPeak HVAC"
PROMO_TEXT = "20% OFF AC TUNING"
TEXT_RULES = (
    f"Text required: exact strings \"{BUSINESS_NAME}\" and \"{PROMO_TEXT}\" only. "
    "Two lines, plain sans-serif, high legibility, no stylization, no distortion. "
    "Bottom-centered, high contrast on clean background. "
    "No other text, logos, labels, signage, decals, or watermarks."
)


def build_simple_prompt_1() -> PromptSpec:
    return PromptSpec(
        slug="simple_interior",
        title="Simple Interior Ad",
        prompt=(
            f"Create an HVAC service ad creative for \"{BUSINESS_NAME}\". "
            "Show a clean modern home interior with a visible air vent and cool airflow. "
            "Portrait 6x9, ad-ready with open space for copy. "
            f"{TEXT_RULES} "
            "No clutter, no people."
        ),
    )


def build_simple_prompt_2() -> PromptSpec:
    return PromptSpec(
        slug="simple_outdoor",
        title="Simple Outdoor Ad",
        prompt=(
            f"Create an HVAC tune-up promo creative for \"{BUSINESS_NAME}\". "
            "Show a clean outdoor AC condenser at a modern home in bright daylight. "
            "Portrait 6x9, ad-ready with open space for copy. "
            f"{TEXT_RULES} "
            "No clutter, no people."
        ),
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_prompt(path: Path, prompt: str) -> None:
    path.write_text(prompt)


def main() -> None:
    load_dotenv()

    run_dir = (
        Path(RUNTIME_CONFIG.output_dir) / "ollama" / "hvac_ads" / timestamp()
    )
    ensure_dir(run_dir)

    config = build_ollama_image_config(
        model="x/flux2-klein:latest",
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    prompts = [build_simple_prompt_1(), build_simple_prompt_2()]
    for spec in prompts:
        image_path = run_dir / f"hvac__{spec.slug}.png"
        prompt_path = run_dir / f"hvac__{spec.slug}.txt"
        print(f"Generating HVAC / {spec.title} -> {image_path}")
        generate_ollama_image(
            prompt=spec.prompt,
            output_path=str(image_path),
            config=config,
        )
        save_prompt(prompt_path, spec.prompt)
        print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
