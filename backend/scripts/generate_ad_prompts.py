from __future__ import annotations

"""
Prompt-only generator for ad creative image prompts.

Writes:
  output/prompts/<out-subdir>/<timestamp>/prompts.json
  output/prompts/<out-subdir>/<timestamp>/*.txt

Examples:
  Smoothie prompts (overlay text later):
    cd backend
    uv run scripts/generate_ad_prompts.py --business-kind smoothie --engine llm --count 5 --format-hint flyer_poster --text-mode overlay --out-subdir smoothie_prompts

  HVAC prompts (overlay text later):
    cd backend
    uv run scripts/generate_ad_prompts.py --business-kind hvac --engine llm --count 5 --format-hint flyer_poster --text-mode overlay --out-subdir hvac_prompts --offer "FREE AC TUNING FOR 30 DAYS"
"""

import argparse
import json
import re
import string
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.llm_providers import build_llm_clients
from hyperlocal.openai_helpers import chat_json


@dataclass(frozen=True)
class PromptSpec:
    slug: str
    title: str
    prompt: str
    negative_prompt: str
    text_mode: str  # overlay | in_image
    format_hint: str  # ad_creative | flyer | poster | flyer_poster
    business_kind: str  # smoothie | hvac
    business_name: str
    offer: str
    product: str


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = _SLUG_RE.sub("_", value).strip("_")
    return value or "prompt"


def base_constraints(*, business_kind: str, text_mode: str, business_name: str, offer: str) -> str:
    parts = ["Portrait 6x9 composition.", "High-quality lighting, crisp detail, clean styling."]
    if business_kind == "smoothie":
        parts += [
            "Photorealistic commercial food photography.",
            "Unbranded clear cups only.",
            "No visible blender blades, machinery, or product packaging.",
        ]
    else:  # hvac
        parts += [
            "Photorealistic commercial advertising photography.",
            "Clean modern home environment or clean service-ready HVAC context.",
            "No uniforms, clothing, gloves, helmets, or tools in use.",
            "No trucks, vans, or vehicle branding.",
        ]
    parts += [
        "No people, faces, hands, or human-like figures.",
        "No brand marks or packaging graphics.",
        "No logos, labels, menus, signage, decals, stickers, or watermarks.",
        "No icons, symbols, illustrations, diagrams, or UI elements.",
    ]
    if text_mode == "overlay":
        parts += [
            "No text of any kind (letters, numbers, symbols, glyphs, or CJK characters).",
            "Leave generous clean negative space for later text overlay.",
        ]
    else:
        parts.append(
            f"Text required: exact strings \"{business_name}\" and \"{offer}\" only."
        )
        parts.append(
            "Two lines only, plain sans-serif, high legibility, no stylization, no distortion."
        )
        parts.append(
            "Render on a clean white rectangular nameplate, bottom-centered, high contrast."
        )
        parts.append("One instance only; no duplicates. No other text.")
    return " ".join(parts)


def base_negative_prompt(*, business_kind: str, text_mode: str) -> str:
    extra = ""
    if business_kind == "hvac":
        extra = " Avoid workers, uniforms, tools in use, and vehicles."
    if text_mode == "overlay":
        return (
            "Avoid any text, letters, words, numbers, or signage. "
            "Avoid logos, watermarks, labels, menus, and packaging graphics. "
            "Avoid people, faces, hands. Avoid clutter and busy backgrounds."
            + extra
        )
    return (
        "Avoid any extra text beyond the required two lines. "
        "Avoid illegible, misspelled, duplicated, or distorted typography. "
        "Avoid logos, watermarks, labels, menus, signage. "
        "Avoid people, faces, hands. Avoid clutter and busy backgrounds."
        + extra
    )


def _format_prefix(format_hint: str, *, business_kind: str) -> str:
    # Keep this as prompt wording only; constraints handle the heavy lifting.
    if format_hint == "flyer":
        return "direct-mail flyer creative"
    if format_hint == "poster":
        return "poster-style promo creative"
    if format_hint == "flyer_poster":
        return "direct-mail flyer / poster-style promo creative"
    if business_kind == "hvac":
        return "commercial service ad creative image"
    return "commercial ad creative image"


def _template_directions(business_kind: str) -> list[tuple[str, str, str]]:
    if business_kind == "hvac":
        return [
            (
                "interior_vent_airflow",
                "Interior Vent Airflow",
                "Clean modern living room interior with a visible ceiling or wall air vent. "
                "Subtle cool airflow indicated by soft misty light beams (no icons). "
                "Hero elements in lower third, strong negative space above for copy.",
            ),
            (
                "outdoor_condenser",
                "Outdoor Condenser",
                "Clean outdoor AC condenser unit beside a modern home exterior. "
                "Bright daylight, tidy minimal landscaping, no brand labels, no serial plates. "
                "Condenser framed low with generous negative space above.",
            ),
            (
                "register_closeup",
                "Register Close-Up",
                "Close-up of a clean HVAC register/vent with cool air feel (subtle condensation, gentle haze). "
                "Minimal modern background, premium polished look, lots of negative space.",
            ),
            (
                "abstract_cool_gradient",
                "Abstract Cool Gradient",
                "Minimal clean cool-blue to white gradient background with soft realistic shadows "
                "and a subtle vent texture highlight (photographic, not illustration). "
                "Designed to be overlay-friendly with lots of clean space.",
            ),
        ]
    # smoothie
    return [
        (
            "mango_hero_pair",
            "Hero Pair",
            "Two tall unbranded clear mango smoothies side-by-side with condensation. "
            "Fresh mango slices and a few berries, bright appetizing tropical colors. "
            "Hero composition in lower-left third, generous negative space in upper-right.",
        ),
        (
            "mango_pour_splash",
            "Pour Splash",
            "Mango smoothie pouring into a clear cup with a clean dynamic splash arc. "
            "Mango slices in the foreground, frozen droplets, energetic but minimal. "
            "Action centered low, negative space in upper half.",
        ),
        (
            "ingredient_flatlay",
            "Ingredient Flatlay",
            "Top-down flatlay of mango, citrus wedges, mint, ice, and a clear smoothie cup. "
            "Clean modern surface, tidy geometry, editorial food styling. "
            "Leave a large blank area for overlay text.",
        ),
        (
            "tropical_counter_scene",
            "Counter Scene",
            "Bright modern smoothie shop counter scene with a single hero mango smoothie in a clear cup. "
            "Clean minimal background, subtle tropical accents (no signage), airy daylight. "
            "Leave strong negative space above the hero.",
        ),
        (
            "macro_mango_texture",
            "Macro Texture",
            "Macro close-up of a mango smoothie surface swirl with droplets and a hint of cup rim, "
            "plus fresh mango texture and mint nearby. "
            "Abstract but appetizing, plenty of clean negative space.",
        ),
        (
            "minimal_gradient_hero",
            "Minimal Gradient",
            "Single hero mango smoothie in a clear cup on a clean modern surface with a soft coral-to-mango gradient backdrop. "
            "Premium minimal styling, strong negative space for copy.",
        ),
    ]


def _style_variants(business_kind: str) -> list[tuple[str, str, str]]:
    if business_kind == "hvac":
        return [
            ("bright_daylight", "Bright Daylight", "Bright natural daylight, clean crisp shadows, modern home vibe."),
            ("cool_blue", "Cool Blue", "Cool-toned lighting with soft blue highlights, fresh and refreshing feel."),
            ("premium_clean", "Premium Clean", "Premium commercial lighting, subtle rim light, cinematic but clean and minimal."),
        ]
    return [
        ("bright_studio", "Bright Studio", "High-key studio softbox lighting, crisp highlights, clean modern look."),
        ("sunny_window", "Sunny Window", "Natural window light, bright morning feel, gentle shadows, fresh and airy."),
        ("premium_gloss", "Premium Gloss", "Cinematic premium commercial lighting, subtle rim light, glossy highlights, shallow depth of field."),
    ]


def build_template_prompts(
    *,
    business_kind: str,
    business_name: str,
    offer: str,
    product: str,
    text_mode: str,
    format_hint: str,
    count: int,
) -> list[PromptSpec]:
    constraints = base_constraints(
        business_kind=business_kind, text_mode=text_mode, business_name=business_name, offer=offer
    )
    neg = base_negative_prompt(business_kind=business_kind, text_mode=text_mode)

    directions = _template_directions(business_kind)
    style_variants = _style_variants(business_kind)
    format_prefix = _format_prefix(format_hint, business_kind=business_kind)

    base = (
        f"Create a {format_prefix} for \"{business_name}\". "
        f"Promotion: {offer}. "
        f"Product: {product}. "
    )

    specs: list[PromptSpec] = []
    # For HVAC, we prefer diverse concepts first; for smoothies, lighting/style variants
    # per concept are useful.
    if business_kind == "hvac":
        for v_slug, v_title, variant in style_variants:
            for d_slug, d_title, direction in directions:
                slug = f"{d_slug}__{v_slug}"
                title = f"{d_title} / {v_title}"
                prompt = f"{base}{direction} {variant} {constraints}"
                specs.append(
                    PromptSpec(
                        slug=slug,
                        title=title,
                        prompt=prompt,
                        negative_prompt=neg,
                        text_mode=text_mode,
                        format_hint=format_hint,
                        business_kind=business_kind,
                        business_name=business_name,
                        offer=offer,
                        product=product,
                    )
                )
                if len(specs) >= count:
                    return specs
    else:
        for d_slug, d_title, direction in directions:
            for v_slug, v_title, variant in style_variants:
                slug = f"{d_slug}__{v_slug}"
                title = f"{d_title} / {v_title}"
                prompt = f"{base}{direction} {variant} {constraints}"
                specs.append(
                    PromptSpec(
                        slug=slug,
                        title=title,
                        prompt=prompt,
                        negative_prompt=neg,
                        text_mode=text_mode,
                        format_hint=format_hint,
                        business_kind=business_kind,
                        business_name=business_name,
                        offer=offer,
                        product=product,
                    )
                )
                if len(specs) >= count:
                    return specs
    return specs


def build_llm_prompts(
    *,
    business_kind: str,
    business_name: str,
    offer: str,
    product: str,
    text_mode: str,
    format_hint: str,
    count: int,
) -> list[PromptSpec]:
    llm = build_llm_clients()
    constraints = base_constraints(
        business_kind=business_kind, text_mode=text_mode, business_name=business_name, offer=offer
    )
    neg = base_negative_prompt(business_kind=business_kind, text_mode=text_mode)
    format_prefix = _format_prefix(format_hint, business_kind=business_kind)
    format_instruction = f"Make it clearly a {format_prefix}."

    def _candidate_is_valid(item: dict) -> bool:
        # We use hard bans because we append base constraints; we don't want conflicts
        # like "add logo sticker" that fight "no logos" and confuse the image model.
        if business_kind == "hvac":
            pos_text = " ".join(
                str(item.get(k, "") or "")
                for k in ["title", "subject", "scene", "composition", "lighting", "style"]
            ).lower()
            constraints_text = str(item.get("constraints", "") or "").lower()

            banned_phrases_anywhere = [
                "sticker",
                "watermark",
                "graph",
                "chart",
                "diagram",
                "infographic",
                "thermostat",
                "placeholder",
                "badge",
                "seal",
                "corner logo",
                "text placeholder",
                "logo sticker",
                "logo in corner",
                "company logo",
            ]
            if any(tok in pos_text for tok in banned_phrases_anywhere):
                return False
            if any(tok in constraints_text for tok in ["logo in corner", "logo sticker", "company logo"]):
                return False

            # Disallow positive "illustration/icon" vibes in the main fields. Allow negations in constraints.
            banned_positive_tokens = ["illustration", "icon", "ui", "infographic", "diagram", "graph", "chart"]
            if any(tok in pos_text for tok in banned_positive_tokens):
                return False

            # If constraints mention these, they must be in a negative form.
            soft_banned = ["logo", "icons", "icon", "illustration", "diagram", "graph", "ui", "thermostat", "text"]
            for tok in soft_banned:
                if tok not in constraints_text:
                    continue
                if f"no {tok}" in constraints_text or f"avoid {tok}" in constraints_text:
                    continue
                # Allow "no logos" plural.
                if tok == "logo" and ("no logos" in constraints_text or "avoid logos" in constraints_text):
                    continue
                return False
        return True

    def _ascii_title(value: str) -> str:
        # Keep filenames/UI clean; prompt content is what matters.
        clean = "".join(ch for ch in value if ch in string.printable).strip()
        return " ".join(clean.split())

    schema_example = (
        "["
        "{"
        "\"slug\":\"mango_hero_pair\","
        "\"title\":\"Mango Hero Pair\","
        "\"subject\":\"Two clear mango smoothies with condensation\","
        "\"scene\":\"Clean tropical prep surface with mango slices and mint\","
        "\"composition\":\"Portrait 6x9, hero in lower-left, large negative space upper-right\","
        "\"lighting\":\"Bright studio softbox, crisp highlights\","
        "\"style\":\"Photorealistic commercial food photography, modern\","
        "\"constraints\":\"No people. No branding. Overlay-safe negative space.\""
        "}"
        "]"
    )

    hvac_concepts = (
        "HVAC concept options (pick from these; do not invent diagrams/graphs/UI): "
        "1) Clean modern living room with a visible vent and subtle cool airflow. "
        "2) Outdoor AC condenser beside a modern home exterior (no labels/plates). "
        "3) Close-up of a clean HVAC register/vent with premium lighting. "
        "4) Abstract cool-blue photographic gradient background with realistic shadows (no icons)."
    )
    vertical_extra = (hvac_concepts + " ") if business_kind == "hvac" else ""

    # For HVAC we get better compliance by asking the model to refine safe seeds rather than inventing
    # infographic-like concepts (graphs, icons, thermostats, etc).
    seeds = None
    if business_kind == "hvac":
        seeds = [
            {
                "slug": "interior_vent_airflow",
                "title": "Interior Vent Airflow",
                "subject": "Clean modern living room with a visible air vent",
                "scene": "Minimal contemporary home interior, tidy surfaces, cool air feel",
                "composition": "Portrait 6x9; vent/hero in lower third; large clean negative space in upper half for overlay copy",
                "lighting": "Bright natural daylight with soft shadows, crisp highlights",
                "style": "Photorealistic commercial advertising photography, premium and clean",
                "constraints": "No people. No branding. No tools in use. Overlay-safe negative space.",
            },
            {
                "slug": "outdoor_condenser",
                "title": "Outdoor Condenser",
                "subject": "Clean outdoor AC condenser unit",
                "scene": "Modern home exterior in bright daylight, minimal landscaping, no labels or plates",
                "composition": "Portrait 6x9; condenser framed low; generous negative space above for overlay copy",
                "lighting": "Sunny daylight, soft controlled shadows, high clarity",
                "style": "Photorealistic commercial service ad photography, modern and trustworthy",
                "constraints": "No people. No vehicles. No branding. Overlay-safe negative space.",
            },
            {
                "slug": "register_closeup",
                "title": "Register Close-Up",
                "subject": "Close-up of a clean HVAC register/vent",
                "scene": "Minimal modern interior background, subtle cool haze (not icons) to imply airflow",
                "composition": "Portrait 6x9; register in lower-left; clean empty space top-right for overlay copy",
                "lighting": "Premium softbox lighting with gentle rim light, crisp metal highlights",
                "style": "Photorealistic commercial advertising close-up, clean and minimal",
                "constraints": "No people. No logos. No UI. Overlay-safe negative space.",
            },
        ]

    seed_text = ""
    if seeds:
        seed_text = (
            "Refine and improve these seed specs (keep slug; keep them photorealistic; "
            "do not introduce banned elements): "
            + json.dumps(seeds, indent=2)
            + " "
        )

    prompt_parts = [
        "Generate high-quality image prompt specs for a local business promotion. ",
        f"Return exactly {count} items as a JSON array. ",
        "Each item must include keys: slug, title, subject, scene, composition, lighting, style, constraints. ",
        f"Rules: portrait 6x9; keep prompts concise and image-model friendly. {format_instruction} ",
        "No emojis in title. Prefer photorealistic commercial photography (not illustration). ",
        "If smoothie: unbranded clear cups only; avoid visible blender blades/machinery; avoid weird artifacts like steam. ",
        "If HVAC: clean modern home/HVAC context; avoid workers/uniforms/tools-in-use/vehicles; avoid thermostat UI. ",
        "If HVAC: do not mention logos/stickers/watermarks. Do not mention icons, diagrams, charts, or illustrations. ",
        "Do not mention text placeholders. ",
        "Keep the scene realistic and appetizing/clean; avoid gimmicky props. ",
        f"Business name: {business_name}. Product: {product}. Offer: {offer}. ",
        f"Text policy: {text_mode} (overlay means no in-image text). ",
        f"Business vertical: {business_kind}. ",
        "For HVAC: show clean modern home/HVAC context, no workers, no uniforms, no tools in use, no vehicles. ",
        "For smoothies: commercial food photography with unbranded clear cups. ",
        f"Creative goal: modern, appetizing {business_kind} {format_prefix} visuals with strong negative space for copy overlay. ",
        vertical_extra,
        seed_text,
        "Output format example (use this exact JSON shape, but with your own content): ",
        schema_example,
        " ",
        "Return JSON only, no markdown.",
    ]
    prompt = "".join(prompt_parts)
    data = chat_json(llm.text_client, llm.text_model, messages=[{"role": "user", "content": prompt}])
    if not isinstance(data, list):
        raise RuntimeError("Model did not return a JSON array.")

    specs: list[PromptSpec] = []
    for idx, item in enumerate(data[:count]):
        if not isinstance(item, dict):
            continue
        if not _candidate_is_valid(item):
            continue
        slug = slugify(str(item.get("slug") or f"llm_{idx+1}"))
        title = _ascii_title(str(item.get("title") or slug)) or slug
        subject = str(item.get("subject") or "")
        scene = str(item.get("scene") or "")
        composition = str(item.get("composition") or "")
        lighting = str(item.get("lighting") or "")
        style = str(item.get("style") or "")
        extra_constraints = str(item.get("constraints") or "")

        # Merge into a single prompt string; keep the structure for readability.
        merged = " ".join(
            part
            for part in [
                f"Subject: {subject}" if subject else "",
                f"Scene: {scene}" if scene else "",
                f"Composition: {composition}" if composition else "",
                f"Lighting: {lighting}" if lighting else "",
                f"Style: {style}" if style else "",
                f"Constraints: {extra_constraints}" if extra_constraints else "",
            ]
            if part
        )
        full = (
            f"Create a {format_prefix} for \"{business_name}\". "
            f"Promotion: {offer}. Product: {product}. "
            f"{merged} {constraints}"
        ).strip()

        specs.append(
            PromptSpec(
                slug=slug,
                title=title,
                prompt=full,
                negative_prompt=neg,
                text_mode=text_mode,
                format_hint=format_hint,
                business_kind=business_kind,
                business_name=business_name,
                offer=offer,
                product=product,
            )
        )

    # If the model under-produced (or we filtered bad candidates), fall back to templates to fill.
    if len(specs) < count:
        filler = build_template_prompts(
            business_kind=business_kind,
            business_name=business_name,
            offer=offer,
            product=product,
            text_mode=text_mode,
            format_hint=format_hint,
            count=count,
        )
        for spec in filler:
            if len(specs) >= count:
                break
            spec_slug = f"fill_{spec.slug}"
            specs.append(
                PromptSpec(
                    slug=spec_slug,
                    title=f"Fill: {spec.title}",
                    prompt=spec.prompt,
                    negative_prompt=spec.negative_prompt,
                    text_mode=spec.text_mode,
                    format_hint=spec.format_hint,
                    business_kind=spec.business_kind,
                    business_name=spec.business_name,
                    offer=spec.offer,
                    product=spec.product,
                )
            )
    return specs[:count]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_specs(run_dir: Path, specs: list[PromptSpec]) -> None:
    ensure_dir(run_dir)
    (run_dir / "prompts.json").write_text(
        json.dumps([asdict(s) for s in specs], indent=2) + "\n"
    )
    for spec in specs:
        (run_dir / f"{spec.slug}.txt").write_text(spec.prompt + "\n")


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate ad-creative image prompts (prompt-only).")
    parser.add_argument("--engine", choices=["template", "llm"], default="template")
    parser.add_argument("--count", type=int, default=6, help="Number of prompts to generate.")
    parser.add_argument("--business-kind", choices=["smoothie", "hvac"], default="smoothie")
    parser.add_argument("--text-mode", choices=["overlay", "in_image"], default="overlay")
    parser.add_argument(
        "--format-hint",
        choices=["ad_creative", "flyer", "poster", "flyer_poster"],
        default="ad_creative",
        help="Wording hint to include in the prompt (can affect downstream image results).",
    )
    parser.add_argument("--business-name", default="Sunset Smoothie Co.")
    parser.add_argument("--product", default="Mango smoothie")
    parser.add_argument(
        "--offer",
        default="BUY 1 GET 1 50% OFF MANGO SMOOTHIES",
        help="Offer text (also used as the required text when --text-mode=in_image).",
    )
    parser.add_argument(
        "--out-subdir",
        default="smoothie_ads",
        help="Output folder under output/prompts/ (default: smoothie_ads).",
    )
    args = parser.parse_args()

    if args.engine == "llm":
        specs = build_llm_prompts(
            business_kind=args.business_kind,
            business_name=args.business_name,
            offer=args.offer,
            product=args.product,
            text_mode=args.text_mode,
            format_hint=args.format_hint,
            count=max(1, args.count),
        )
    else:
        specs = build_template_prompts(
            business_kind=args.business_kind,
            business_name=args.business_name,
            offer=args.offer,
            product=args.product,
            text_mode=args.text_mode,
            format_hint=args.format_hint,
            count=max(1, args.count),
        )

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "prompts" / args.out_subdir / timestamp()
    save_specs(run_dir, specs)
    print(f"Wrote {len(specs)} prompt specs to {run_dir}")


if __name__ == "__main__":
    main()
