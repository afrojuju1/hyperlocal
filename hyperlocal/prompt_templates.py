from __future__ import annotations

from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief


def copy_prompt(brief: CreativeBrief, style: BrandStyle, variants: int) -> str:
    palette = ", ".join(style.palette or brief.brand_colors or [])
    style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
    return (
        "You are a direct-response copywriter for a mailer flyer. "
        f"Return exactly {variants} copy variants as JSON array. "
        "Each variant must include: headline, subhead, body, cta, disclaimer. "
        "Constraints: headline <= 6 words, subhead <= 10 words, body <= 28 words, "
        "cta <= 4 words, disclaimer <= 12 words. "
        "Keep text clean and printable. Avoid emojis. English only. "
        f"Business: {brief.business_name}. "
        f"Product: {brief.product}. Offer: {brief.offer}. Tone: {brief.tone}. "
        f"Audience: {brief.audience or 'local households'}. "
        f"Palette: {palette or 'not specified'}. "
        f"Style: {style_keywords or 'modern, friendly'}. "
        "Return JSON only, no markdown."
    )


def image_prompt(brief: CreativeBrief, style: BrandStyle, copy: CopyVariant) -> str:
    palette = ", ".join(style.palette or brief.brand_colors or [])
    style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
    layout_guidance = style.layout_guidance or (
        "Clear text zones with high contrast; large headline at top; body mid; CTA button bottom."
    )
    constraints = "; ".join(brief.constraints or [])
    return (
        "Design a 6x9 inch direct-mail flyer image. "
        "Include the exact text below, spelled exactly and legible. "
        "Use a clean, modern layout with strong hierarchy. "
        f"Visual style: {style_keywords or 'bright, fresh, modern'}. "
        f"Color palette: {palette or 'vibrant fruit colors, fresh greens, clean whites'}. "
        f"Layout guidance: {layout_guidance}. "
        f"Business: {brief.business_name}. Product: {brief.product}. Offer: {brief.offer}. "
        f"Constraints: {constraints or 'No people; no faces; no extra slogans'}. "
        "Text must be fully readable and centered on safe margins. "
        "\nExact text to include (keep line breaks as written):\n"
        f"{copy.headline}\n"
        f"{copy.subhead}\n"
        f"{copy.body}\n"
        f"{copy.cta}\n"
        f"{copy.disclaimer or ''}\n"
        "\nMake the background visually rich but not busy, so the text remains crisp."
    )


def negative_prompt() -> str:
    return (
        "Avoid illegible or distorted text, cluttered layouts, and low contrast. "
        "Avoid extra text not provided. Avoid faces, hands, or people."
    )
