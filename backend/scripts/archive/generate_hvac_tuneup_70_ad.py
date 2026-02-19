from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.image_providers import build_ollama_image_config, generate_ollama_image


DEFAULT_MODEL = "x/flux2-klein:latest"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one HVAC AC tune-up ad creative via Ollama Flux model."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Ollama image model to use.")
    parser.add_argument(
        "--out-subdir",
        default="hvac_tuneup_70",
        help="Subdirectory under output/ollama/ for this run.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        choices=["balanced", "offer_first", "trust_first"],
        help=(
            "Prompt variant(s) to render. Repeatable. "
            "Defaults to: balanced"
        ),
    )
    return parser.parse_args()


def build_prompt(variant: str) -> str:
    if variant == "offer_first":
        return (
            "A modern local HVAC ad focused on a strong value offer with highly legible typography. "
            "The image contains these exact text phrases with exact spelling and capitalization: "
            '"ONLY $70", "AC TUNE-UP SPECIAL", and "BOOK NOW". '
            "Place ONLY $70 as the largest text at upper left, AC TUNE-UP SPECIAL directly below it, "
            "and BOOK NOW inside a rounded blue button at lower left. "
            "Use bold geometric sans-serif lettering, white text #FFFFFF on a deep blue gradient panel "
            "#0757B8 with high contrast and generous spacing for mobile readability. "
            "Show a friendly HVAC technician in clean blue uniform next to a well-maintained residential "
            "AC condenser in bright summer daylight, photorealistic style. "
            "Keep the bottom strip clean and empty for later logo and phone overlay."
        )

    if variant == "trust_first":
        return (
            "A trustworthy local HVAC ad with crisp, highly legible typography and professional service tone. "
            "The image contains these exact text phrases with exact spelling and capitalization: "
            '"AC TUNE-UP SPECIAL", "ONLY $70", and "BOOK NOW". '
            "Place AC TUNE-UP SPECIAL at upper left, ONLY $70 immediately beneath, and BOOK NOW in a rounded "
            "button at lower left. "
            "Include one small trust badge near the technician that reads exactly: \"LICENSED & INSURED\". "
            "Use bold clean sans-serif lettering, white text on a cool blue panel with strong contrast and "
            "clear spacing for mobile readability. "
            "Show a friendly HVAC technician near a suburban home with an outdoor AC unit visible, "
            "sunny daytime, photorealistic style. "
            "Keep lower footer area clean and empty for logo and contact overlay."
        )

    return (
        "A modern local HVAC social ad with crisp, highly legible typography. "
        "The image contains these exact text phrases with exact spelling and capitalization: "
        '"AC TUNE-UP SPECIAL", "ONLY $70", and "BOOK NOW". '
        "Place AC TUNE-UP SPECIAL at upper left, ONLY $70 directly beneath it, and BOOK NOW "
        "inside a rounded blue button at lower left. "
        "Use bold geometric sans-serif lettering, white text color #FFFFFF on a blue gradient "
        "panel #0B6DBA with strong contrast and clean spacing for mobile readability. "
        "Show a friendly HVAC technician in a blue uniform beside a suburban home and visible "
        "outdoor AC condenser in bright summer daylight, photorealistic style. "
        "Keep the bottom strip clean and empty for later logo and phone overlay."
    )


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main() -> None:
    args = parse_args()
    load_dotenv()

    variants = args.variant or ["balanced"]
    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / args.out_subdir / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    config = build_ollama_image_config(
        model=args.model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    print(f"Model: {args.model}")
    print(f"Run directory: {run_dir}")
    for variant in variants:
        prompt = build_prompt(variant)
        prompt_path = run_dir / f"{variant}__prompt.txt"
        image_path = run_dir / f"{variant}__creative.png"
        prompt_path.write_text(prompt)
        print(f"Variant: {variant}")
        print(f"Prompt file: {prompt_path}")
        print(f"Generating image -> {image_path}")
        result = generate_ollama_image(
            prompt=prompt,
            output_path=str(image_path),
            config=config,
        )
        print(f"Image: {result.path}")
    print("Done.")


if __name__ == "__main__":
    main()
