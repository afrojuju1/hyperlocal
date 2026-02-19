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
class PromptJob:
    slug: str
    name: str
    prompt: str


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def build_base_directive() -> str:
    return (
        "Create a full-bleed 6x9 inch portrait flyer design WITHOUT ANY TEXT. "
        "This should feel like a creative, modern flyer with dynamic composition, "
        "not a postcard template. "
        "Do NOT include any letters, numbers, words, logos, signage, labels, menus, or UI. "
        "Do NOT create a poster, book cover, magazine, brochure, billboard, or framed mockup. "
        "No people, faces, or hands. No product packaging or product mockups. "
        "Design direction: asymmetrical layout, layered depth, overlapping shapes, "
        "diagonal energy, soft gradients, and subtle textures. "
        "Leave intentional blank zones for text overlay, but avoid rigid bands or boxed panels. "
        "No borders, no frames, no centered template look."
    )


def build_jobs() -> list[PromptJob]:
    base = build_base_directive()
    return [
        PromptJob(
            slug="sunset_smoothie",
            name="Sunset Smoothie Co.",
            prompt=(
                f"{base} "
                "Theme: fresh tropical smoothie shop. "
                "Palette: coral, mint green, sunny yellow, white. "
                "Visuals: abstract citrus slices, soft leaf silhouettes, gentle liquid gradients, "
                "a subtle hero image zone (no products). "
                "Lighting: bright high-key, crisp, clean. "
                "Avoid: cups, straws, fruit labels, menus, signage."
            ),
        ),
        PromptJob(
            slug="rapidkeys_home_buyers",
            name="RapidKeys Home Buyers",
            prompt=(
                f"{base} "
                "Theme: professional real estate cash buyer. "
                "Palette: navy, gold, white. "
                "Visuals: subtle architectural geometry, clean lines, light stone textures, "
                "abstract skyline shapes, a calm hero zone with minimal detail. "
                "Lighting: neutral, polished, minimal contrast. "
                "Avoid: houses with signs, keys, dollar symbols, or branded elements."
            ),
        ),
        PromptJob(
            slug="northside_plumbing_hvac",
            name="Northside Plumbing & HVAC",
            prompt=(
                f"{base} "
                "Theme: plumbing & HVAC service. "
                "Palette: blue, red, white. "
                "Visuals: abstract pipe arcs, metallic gradients, subtle grid pattern, "
                "clean industrial cues, a simplified tech hero zone. "
                "Lighting: slightly cooler, crisp and technical. "
                "Avoid: tools, gauges, labels, or any text."
            ),
        ),
    ]


def main() -> None:
    load_dotenv()

    config = build_ollama_image_config(
        model=RUNTIME_CONFIG.ollama_image_model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    out_root = Path(RUNTIME_CONFIG.output_dir) / "ollama" / "flyer_plates_v2"
    out_root.mkdir(parents=True, exist_ok=True)

    for job in build_jobs():
        out_dir = out_root / job.slug
        out_dir.mkdir(parents=True, exist_ok=True)
        image_path = out_dir / f"background_{timestamp()}.png"
        print(f"Generating {job.name} -> {image_path}")
        generate_ollama_image(
            prompt=job.prompt,
            output_path=str(image_path),
            config=config,
        )
        print(f"Saved: {image_path}")


if __name__ == "__main__":
    main()
