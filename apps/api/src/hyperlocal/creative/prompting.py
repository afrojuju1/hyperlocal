from __future__ import annotations

"""
Prompt-only generator for ad creative image prompts.

Writes:
  output/prompts/<out-subdir>/<timestamp>/prompts.json
  output/prompts/<out-subdir>/<timestamp>/*.txt

Examples:
  Smoothie prompts (standalone in-image ad experiment):
    cd apps/api
    uv run scripts/generate_ad_prompts.py --business-kind smoothie --engine llm --count 5 --format-hint flyer_poster --text-mode in_image --out-subdir smoothie_prompts

  HVAC prompts (standalone in-image ad experiment):
    cd apps/api
    uv run scripts/generate_ad_prompts.py --business-kind hvac --engine llm --count 5 --format-hint flyer_poster --text-mode in_image --out-subdir hvac_prompts --offer "FREE AC TUNING FOR 30 DAYS"
"""

import argparse
import json
import re
import string
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from hyperlocal.core.config import RUNTIME_CONFIG
from hyperlocal.creative.vertical_config import (
    get_vertical_config,
    vertical_items,
    vertical_mode_list,
    vertical_mode_text,
    vertical_strings,
)
from hyperlocal.integrations.llm import build_llm_clients
from hyperlocal.integrations.openai import chat_json


@dataclass(frozen=True)
class PromptSpec:
    slug: str
    title: str
    prompt: str
    negative_prompt: str
    text_mode: str  # overlay | in_image
    format_hint: str  # ad_creative | flyer | poster | flyer_poster
    business_kind: str
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
    if text_mode == "in_image":
        parts = [
            "Create a finished vertical 6x9 ad creative, not a background for later editing.",
            "The image model owns the full composition: photography, typography, hierarchy, placement, color, and final ad design.",
            "Use a premium campaign-art-direction style with strong visual taste and a clear conversion-focused offer.",
            f"Required visible text, exactly once each: \"{business_name}\" and \"{offer}\".",
            "No other readable words should appear.",
            "The typography may be expressive and integrated into the composition; choose placement, scale, contrast, and hierarchy freely.",
            "Set type directly into the scene or over natural negative space; do not put text inside boxes, banners, strips, stickers, labels, nameplates, white rectangles, or rounded capsules.",
            "Keep cups, packaging, walls, signs, and surfaces plain and unmarked except for the two required text strings.",
            "Do not use full-width pill bars, boxed overlay templates, placeholder copy, lorem ipsum, or generic coupon grids.",
            "No external overlay will be added later, so the generated image must be the finished ad.",
        ]
    else:
        parts = [
            "Portrait 6x9 vertical photographic background.",
            "High-quality, polished, campaign-ready image with strong visual taste.",
            "Use an intentional focal point and keep at least one open, calm area for the later design layer.",
        ]
    parts.extend(vertical_mode_list(business_kind, "constraints", text_mode))
    if text_mode == "overlay":
        parts += [
            "Keep all product and environmental surfaces plain and unmarked.",
            "Avoid graphic-design elements inside the generated scene.",
            "Do not render wall lettering, framed typography, posters, service slogans, prices, phone-number-like digits, vehicle decals, HVAC lettering, or emergency-service text.",
        ]
    return " ".join(parts)


def base_negative_prompt(*, business_kind: str, text_mode: str) -> str:
    extra = vertical_mode_text(business_kind, "negative_prompt_extra", text_mode)
    if extra:
        extra = f" {extra}"
    if text_mode == "overlay":
        return (
            "Avoid readable text, misspelled words, coupons, labels, logos, watermarks, menus, and signage. "
            "Avoid numbers, percent signs, offer copy, and business-name lettering. "
            "Avoid currency symbols, 24/7 lettering, wall lettering, decals, truck graphics, service slogans, poster text, and phone-number-like marks. "
            "Avoid framed wall art with letters, typography posters, and decorative word art. "
            "Avoid distorted faces, extra fingers, broken anatomy, cluttered coupon layouts, and low-quality artifacts."
            + extra
        )
    return (
        "Avoid misspelled, duplicated, or distorted required text. "
        "Avoid extra readable words beyond the two required text strings. "
        "Avoid text boxes, white rectangles, bottom rounded capsules, banners, strips, stickers, labels, nameplates, and coupon panels. "
        "Avoid logos, marks, fake branding, fake menus, or text on cups and packaging. "
        "Avoid extra invented offers, fake phone numbers, fake URLs, fake addresses, placeholder copy, lorem ipsum, and generic logo marks. "
        "Avoid illegible, misspelled, duplicated, or distorted typography. "
        "Avoid logos, watermarks, labels, menus, signage. "
        "Avoid distorted faces, broken anatomy, cluttered layouts, and low-quality artifacts."
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
    if get_vertical_config(business_kind).get("label") == "home-service":
        return "commercial service ad creative image"
    return "commercial ad creative image"


def _background_intro(*, business_kind: str, product: str, text_mode: str) -> str:
    if text_mode == "overlay":
        vertical = get_vertical_config(business_kind)
        subject = str(vertical.get("overlay_subject") or "{product} as a realistic product or lifestyle scene")
        subject = subject.format(product=product)
        return (
            "Create a vertical 6x9 photorealistic text-free source image for later ad typography. "
            f"Main visual subject: {subject}. "
        )
    return (
        f"Create a vertical 6x9 photorealistic campaign image for a local {business_kind} business. "
        f"Main product or subject: {product}. "
    )


def _brief_context(
    *,
    tone: str = "",
    audience: str | None = None,
    constraints: list[str] | None = None,
    brand_colors: list[str] | None = None,
    style_keywords: list[str] | None = None,
    include_brand_colors: bool = True,
) -> str:
    parts: list[str] = []
    if tone:
        parts.append(f"Tone: {tone}.")
    if audience:
        parts.append(f"Audience: {audience}.")
    if constraints:
        parts.append(f"User constraints: {', '.join(constraints)}.")
    if brand_colors and include_brand_colors:
        parts.append(f"Brand color direction: {', '.join(brand_colors)}.")
    if style_keywords:
        parts.append(f"Style keywords: {', '.join(style_keywords)}.")
    return " ".join(parts)


_TEXT_HAZARD_RE = re.compile(
    r"\b(text|signs?|logos?|labels?|decals?|address|paperwork|documents?|phone|numbers?|coupons?|brands?|letters?|marks?)\b",
    re.IGNORECASE,
)


def _visual_constraints_for_prompt(
    constraints: list[str] | None,
    *,
    text_mode: str,
) -> list[str] | None:
    if text_mode != "overlay" or not constraints:
        return constraints
    return [item for item in constraints if not _TEXT_HAZARD_RE.search(item)]


def _visual_audience_for_prompt(
    audience: str | None,
    *,
    business_kind: str,
    text_mode: str,
) -> str | None:
    if text_mode != "overlay" or not audience:
        return audience
    cleaned = audience
    for item in get_vertical_config(business_kind).get("audience_replacements", []):
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern") or "")
        replacement = str(item.get("replacement") or "")
        if pattern:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def _template_directions(business_kind: str) -> list[tuple[str, str, str]]:
    return vertical_items(business_kind, "template_directions")


def _style_variants(business_kind: str) -> list[tuple[str, str, str]]:
    return vertical_items(business_kind, "style_variants")


def build_template_prompts(
    *,
    business_kind: str,
    business_name: str,
    offer: str,
    product: str,
    text_mode: str,
    format_hint: str,
    count: int,
    cta: str = "ORDER NOW",
    creative_mode: str | None = None,
    tone: str = "",
    audience: str | None = None,
    constraints: list[str] | None = None,
    brand_colors: list[str] | None = None,
    style_keywords: list[str] | None = None,
) -> list[PromptSpec]:
    base_rules = base_constraints(
        business_kind=business_kind,
        text_mode=text_mode,
        business_name=business_name,
        offer=offer,
    )
    brief_context = _brief_context(
        tone=tone,
        audience=_visual_audience_for_prompt(
            audience,
            business_kind=business_kind,
            text_mode=text_mode,
        ),
        constraints=_visual_constraints_for_prompt(constraints, text_mode=text_mode),
        brand_colors=brand_colors,
        style_keywords=style_keywords,
        include_brand_colors=text_mode != "overlay",
    )
    neg = base_negative_prompt(business_kind=business_kind, text_mode=text_mode)

    directions = _template_directions(business_kind)
    style_variants = _style_variants(business_kind)

    base = _background_intro(business_kind=business_kind, product=product, text_mode=text_mode)

    specs: list[PromptSpec] = []
    # Service categories benefit from diverse concepts first; for smoothies, lighting/style
    # variants per product concept are useful.
    if business_kind in {"hvac", "real_estate"}:
        for v_slug, v_title, variant in style_variants:
            for d_slug, d_title, direction in directions:
                slug = f"{d_slug}__{v_slug}"
                title = f"{d_title} / {v_title}"
                prompt = " ".join(
                    part for part in [base, direction, variant, brief_context, base_rules] if part
                )
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
                prompt = " ".join(
                    part for part in [base, direction, variant, brief_context, base_rules] if part
                )
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
    cta: str = "ORDER NOW",
    creative_mode: str | None = None,
    tone: str = "",
    audience: str | None = None,
    constraints: list[str] | None = None,
    brand_colors: list[str] | None = None,
    style_keywords: list[str] | None = None,
) -> list[PromptSpec]:
    llm = build_llm_clients()
    base_rules = base_constraints(
        business_kind=business_kind,
        text_mode=text_mode,
        business_name=business_name,
        offer=offer,
    )
    brief_context = _brief_context(
        tone=tone,
        audience=_visual_audience_for_prompt(
            audience,
            business_kind=business_kind,
            text_mode=text_mode,
        ),
        constraints=_visual_constraints_for_prompt(constraints, text_mode=text_mode),
        brand_colors=brand_colors,
        style_keywords=style_keywords,
        include_brand_colors=text_mode != "overlay",
    )
    neg = base_negative_prompt(business_kind=business_kind, text_mode=text_mode)
    format_prefix = _format_prefix(format_hint, business_kind=business_kind)
    format_instruction = (
        f"Make it clearly a {format_prefix}."
        if text_mode == "in_image"
        else "The final output is a flyer or poster, but each image prompt must describe only a text-free photographic source scene."
    )

    def _candidate_is_valid(item: dict) -> bool:
        if text_mode != "overlay":
            return True
        text = " ".join(
            str(item.get(k, "") or "")
            for k in ["subject", "scene", "composition", "lighting", "style"]
        ).lower()
        hard_rejects = [
            "readable headline",
            "readable coupon",
            "readable logo",
            "company logo",
            "brand logo",
            "watermark",
            "typography layout",
            "flyer text",
            "text placeholder",
            "branded",
            "uniform",
            "badge",
            "patch",
            "lettering",
            "label",
            "sign",
            "decal",
            "truck",
            "vehicle",
            "van",
            "display",
            "screen",
            "icon",
            "premium hvac service",
            "service in action",
            "24/7",
            "$",
            "%",
            "price",
            "phone number",
        ]
        hard_rejects.extend(vertical_strings(business_kind, "candidate_reject_terms"))
        if any(token in text for token in hard_rejects):
            return False
        if re.search(r"\d", text):
            return False
        return True

    def _ascii_title(value: str) -> str:
        # Keep filenames/UI clean; prompt content is what matters.
        clean = "".join(ch for ch in value if ch in string.printable).strip()
        return " ".join(clean.split())

    vertical_direction = str(get_vertical_config(business_kind).get("llm_art_direction") or "")
    if vertical_direction:
        vertical_direction = f"{vertical_direction} "
    overlay_guardrails = " ".join(vertical_strings(business_kind, "overlay_guardrails"))
    prompt_parts = [
        "Generate bold, high-converting image prompt specs for a local business promotion. ",
        f"Return exactly {count} items as a JSON array. ",
        "Each item must include keys: slug, title, subject, scene, composition, lighting, style, constraints. ",
        f"Rules: portrait 6x9; write concise but vivid image-model prompts. {format_instruction} ",
        "No emojis in title. Prefer photorealistic, cinematic, editorial, or premium commercial photography. ",
        "Avoid sterile product-on-white compositions unless the concept truly needs them. ",
        "Use texture, motion, human context, atmosphere, props, color contrast, and depth when useful. ",
        (
            f"Business name: {business_name}. Product: {product}. Offer: {offer}. "
            if text_mode == "in_image"
            else f"Business name: {business_name}. Product/service category: {business_kind}. Offer: {offer}. CTA: {cta}. "
        ),
        f"{brief_context} " if brief_context else "",
        (
            "Use only the business name and offer as required visible text in the generated ad. "
            "Give the image model creative freedom over typography placement, hierarchy, and color. "
            if text_mode == "in_image"
            else "Use the business and offer only as strategy context; do not put exact offer, CTA, prices, digits, business name, or service slogans into the image prompt text. "
        ),
        (
            "Text policy: in_image. The generated image is the final ad with integrated typography; do not reserve space for later overlay. "
            if text_mode == "in_image"
            else "Text policy: overlay. The generated image must not contain readable text, logos, menus, labels, watermarks, or coupon typography because copy is added later. "
        ),
        f"Business vertical: {business_kind}. ",
        vertical_direction,
        f"{overlay_guardrails} " if text_mode == "overlay" and overlay_guardrails else "",
        (
            f"Creative goal: make each {business_kind} {format_prefix} feel like a complete finished ad, not an empty template. "
            if text_mode == "in_image"
            else f"Creative goal: make each {business_kind} {format_prefix} feel like a distinct campaign source image with one calm negative-space area, not an empty template. "
        ),
        "For overlay mode, avoid concepts that require signs, walls with lettering, service trucks with decals, phone numbers, prices, or visible typography. ",
        "Return only JSON. Do not include markdown. Invent unique concepts for this brief. ",
        "Each JSON object must use these string fields: slug, title, subject, scene, composition, lighting, style, constraints. ",
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

        # Merge into a single prompt string; keep the structure for readability.
        merged = " ".join(
            part
            for part in [
                f"Subject: {subject}" if subject else "",
                f"Scene: {scene}" if scene else "",
                f"Composition: {composition}" if composition else "",
                f"Lighting: {lighting}" if lighting else "",
                f"Style: {style}" if style else "",
            ]
            if part
        )
        full = (
            _background_intro(business_kind=business_kind, product=product, text_mode=text_mode)
            +
            f"{merged} {brief_context} {base_rules}"
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
            cta=cta,
            text_mode=text_mode,
            format_hint=format_hint,
            count=count,
            creative_mode=creative_mode,
            tone=tone,
            audience=audience,
            constraints=constraints,
            brand_colors=brand_colors,
            style_keywords=style_keywords,
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
    parser.add_argument("--business-kind", choices=["smoothie", "hvac", "real_estate"], default="smoothie")
    parser.add_argument("--text-mode", choices=["overlay", "in_image"], default="in_image")
    parser.add_argument(
        "--format-hint",
        choices=["ad_creative", "flyer", "poster", "flyer_poster"],
        default="ad_creative",
        help="Wording hint to include in the prompt (can affect downstream image results).",
    )
    parser.add_argument("--business-name", default="Sunset Smoothie Co.")
    parser.add_argument("--product", default="Mango smoothie")
    parser.add_argument("--cta", default="ORDER NOW")
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
            cta=args.cta,
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
            cta=args.cta,
            text_mode=args.text_mode,
            format_hint=args.format_hint,
            count=max(1, args.count),
        )

    run_dir = Path(RUNTIME_CONFIG.output_dir) / "prompts" / args.out_subdir / timestamp()
    save_specs(run_dir, specs)
    print(f"Wrote {len(specs)} prompt specs to {run_dir}")


if __name__ == "__main__":
    main()
