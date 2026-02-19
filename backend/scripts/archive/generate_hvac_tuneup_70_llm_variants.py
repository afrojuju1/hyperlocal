from __future__ import annotations

import argparse
import json
import re
import subprocess
import string
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.image_providers import build_ollama_image_config, generate_ollama_image


DEFAULT_IMAGE_MODEL = "x/flux2-klein:latest"
DEFAULT_TEXT_MODEL = "qwen2.5:7b"
DEFAULT_SUBJECTS = [
    "A friendly HVAC technician standing beside an outdoor AC condenser, smiling at camera",
    "A friendly HVAC technician actively servicing an outdoor AC condenser with gauges/tools visible",
]


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    return value or "variant"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Use an LLM to generate 2 HVAC ad prompt variants, then render 2 images per variant."
    )
    parser.add_argument("--business-name", default="SunPeak HVAC")
    parser.add_argument("--headline", default="AC TUNE-UP SPECIAL")
    parser.add_argument("--offer", default="ONLY $70")
    parser.add_argument("--cta", default="BOOK NOW")
    parser.add_argument("--count", type=int, default=2, help="Prompt variants to generate.")
    parser.add_argument("--images-per-prompt", type=int, default=2)
    parser.add_argument("--text-model", default=DEFAULT_TEXT_MODEL, help="Ollama text model for prompt generation.")
    parser.add_argument("--image-model", default=DEFAULT_IMAGE_MODEL)
    parser.add_argument(
        "--subject",
        action="append",
        dest="subjects",
        help=(
            "Primary subject variation (repeatable). "
            "If omitted, two HVAC technician subject defaults are used."
        ),
    )
    parser.add_argument(
        "--out-subdir",
        default="hvac_tuneup_70_llm_variants",
        help="Output folder under output/ollama/.",
    )
    return parser.parse_args()


def generate_prompt_variants(
    *,
    text_model: str,
    business_name: str,
    headline: str,
    offer: str,
    cta: str,
    count: int,
    subjects: list[str],
) -> list[dict[str, str]]:
    numbered_subjects = " ".join(
        f"{idx + 1}) {subject}."
        for idx, subject in enumerate(subjects)
    )
    user_prompt = (
        "Generate exactly "
        f"{count} high-quality image prompts for a local HVAC ad creative. "
        "Return JSON only as an array of objects with keys: slug, title, prompt. "
        "Each prompt must be one paragraph and must include these exact in-image text phrases: "
        f"\"{headline}\", \"{offer}\", \"{cta}\". "
        "Use each phrase exactly once. Do not include any other text in the image. "
        "Prompt style goals: photorealistic, modern, trustworthy, mobile-readable. "
        "Visual requirements: friendly HVAC technician, suburban home exterior, visible outdoor AC condenser, "
        "blue high-contrast text panel, clear CTA button, clean footer strip for later logo/phone overlay. "
        "Variation rules: make each option clearly different in primary subject, layout/composition, and lighting direction. "
        "Use these subject options, one unique option per prompt variant: "
        f"{numbered_subjects} "
        "Include the chosen subject description explicitly in each prompt. "
        "Render exactly 3 text blocks only: headline, offer, CTA. "
        "Do not add fake logos, phone numbers, seals, or badge text. "
        f"Business context: {business_name}. "
        "JSON example: "
        "[{\"slug\":\"offer_first\",\"title\":\"Offer First\",\"prompt\":\"...\"}]"
    )

    cmd = ["ollama", "run", text_model, user_prompt]
    result = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
        timeout=180,
    )
    if result.returncode != 0:
        detail = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part)
        raise RuntimeError(f"Ollama text generation failed.\n{detail}")

    content = (result.stdout or "").strip()
    content = content.replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        start = content.find("[")
        end = content.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise
        data = json.loads(content[start : end + 1])

    if not isinstance(data, list):
        raise RuntimeError("LLM did not return a list of prompt variants.")

    variants: list[dict[str, str]] = []
    required_phrases = [headline, offer, cta]
    for item in data[:count]:
        if not isinstance(item, dict):
            continue
        raw_title = str(item.get("title") or "Variant").strip()
        title = "".join(ch for ch in raw_title if ch in string.printable).strip() or "Variant"
        prompt_text = str(item.get("prompt") or "").strip()
        if not prompt_text:
            continue
        missing = [phrase for phrase in required_phrases if phrase.lower() not in prompt_text.lower()]
        if missing:
            prompt_text = (
                prompt_text
                + " Include these exact in-image text phrases once each: "
                + ", ".join(f"\"{phrase}\"" for phrase in missing)
                + ". Do not include any other text."
            )
        prompt_text = (
            prompt_text
            + " Render exactly 3 text blocks only: "
            + ", ".join(f"\"{phrase}\"" for phrase in required_phrases)
            + ". Use each phrase once."
        )
        slug = slugify(str(item.get("slug") or title))
        variants.append({"slug": slug, "title": title, "prompt": prompt_text})

    if len(variants) < count:
        raise RuntimeError(
            f"LLM returned {len(variants)} usable prompt variants; expected {count}."
        )

    # Force one explicit subject per variant to guarantee subject diversity in the final prompt text.
    for idx, variant in enumerate(variants):
        subject = subjects[idx % len(subjects)]
        variant["prompt"] = f"Primary subject: {subject}. {variant['prompt']}"

    return variants


def main() -> None:
    args = parse_args()
    load_dotenv()

    count = max(1, args.count)
    images_per_prompt = max(1, args.images_per_prompt)
    subjects = [s.strip() for s in (args.subjects or DEFAULT_SUBJECTS) if s and s.strip()]
    if not subjects:
        raise RuntimeError("At least one subject variation is required.")

    variants = generate_prompt_variants(
        text_model=args.text_model,
        business_name=args.business_name,
        headline=args.headline,
        offer=args.offer,
        cta=args.cta,
        count=count,
        subjects=subjects,
    )

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "ollama" / args.out_subdir / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    config = build_ollama_image_config(
        model=args.image_model,
        timeout=RUNTIME_CONFIG.ollama_image_timeout,
    )

    manifest = {
        "created_at": datetime.now().isoformat(),
        "business_name": args.business_name,
        "headline": args.headline,
        "offer": args.offer,
        "cta": args.cta,
        "prompt_count": count,
        "images_per_prompt": images_per_prompt,
        "llm_provider": "ollama_cli",
        "text_model": args.text_model,
        "image_model": args.image_model,
        "subjects": subjects,
        "variants": variants,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print(f"Run directory: {run_dir}")
    for i, variant in enumerate(variants, start=1):
        prompt_path = run_dir / f"{i:02d}__{variant['slug']}.prompt.txt"
        prompt_path.write_text(variant["prompt"] + "\n")
        print(f"Prompt {i}/{len(variants)}: {variant['title']}")
        print(f"Prompt file: {prompt_path}")
        for v in range(1, images_per_prompt + 1):
            image_path = run_dir / f"{i:02d}__{variant['slug']}__v{v:02d}.png"
            print(f"Generating image {i}/{len(variants)} variation {v}/{images_per_prompt} -> {image_path}")
            generate_ollama_image(
                prompt=variant["prompt"],
                output_path=str(image_path),
                config=config,
            )
            print(f"Image: {image_path}")

    print("Done.")


if __name__ == "__main__":
    main()
