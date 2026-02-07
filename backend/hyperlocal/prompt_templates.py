from __future__ import annotations

from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief, BusinessDetails, BusinessHours


def _format_hours(details: BusinessDetails | None) -> str:
    if not details or not details.hours:
        return ""
    hours = details.hours
    if hours.display:
        return hours.display
    parts: list[str] = []
    for day in hours.weekly:
        if day.closed:
            parts.append(f"{day.day} closed")
            continue
        if day.open and day.close:
            parts.append(f"{day.day} {day.open}-{day.close}")
        elif day.open:
            parts.append(f"{day.day} {day.open}")
    if hours.notes:
        parts.append(hours.notes)
    return "; ".join(parts)


def copy_prompt(brief: CreativeBrief, style: BrandStyle, variants: int) -> str:
    palette = ", ".join(style.palette or brief.brand_colors or [])
    style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
    constraints = "; ".join(brief.constraints or [])
    details = brief.business_details
    details_text = ""
    business_name = ""
    if details:
        business_name = details.name
        hours_text = _format_hours(details)
        details_text = (
            f"Business details: name {details.name}. address {details.address or ''}, "
            f"{details.city or ''} {details.state or ''} {details.postal_code or ''}. "
            f"Phone {details.phone or ''}. Hours {hours_text or ''}. "
            f"Service area {details.service_area or ''}. Website {details.website or ''}. "
        )
    return (
        "You are a direct-response copywriter for a mailer flyer. "
        f"Return exactly {variants} copy variants as JSON array. "
        "Each variant must include: headline, subhead, body, cta, disclaimer. "
        "Constraints: headline <= 6 words, subhead <= 10 words, body <= 28 words, "
        "cta <= 4 words, disclaimer <= 12 words. "
        "Keep text clean and printable. Avoid emojis. English only. "
        "Include the business name in the copy. "
        f"Preferred CTA: {brief.cta}. Use it as the CTA if possible. "
        f"Required details: {constraints or 'none'}. "
        f"{details_text}"
        f"Business: {business_name or 'not specified'}. "
        f"Product: {brief.product}. Offer: {brief.offer}. Tone: {brief.tone}. "
        f"Audience: {brief.audience or 'local households'}. "
        f"Palette: {palette or 'not specified'}. "
        f"Style: {style_keywords or 'modern, friendly'}. "
        "Return JSON only, no markdown."
    )


def background_prompt(brief: CreativeBrief, style: BrandStyle, copy: CopyVariant) -> str:
    palette = ", ".join(style.palette or brief.brand_colors or [])
    style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
    layout_guidance = style.layout_guidance or (
        "Large clean focal area with soft gradients, a clear visual anchor, and ample negative space."
    )
    constraints = "; ".join(brief.constraints or [])
    details = brief.business_details
    business_name = details.name if details else ""
    return (
        "Create a background-only image for a 6x9 inch direct-mail flyer. "
        "Do NOT include any text, letters, words, logos, signage, or typography. "
        "Leave ample clean space for a text overlay. "
        f"Visual style: {style_keywords or 'bright, fresh, modern'}. "
        f"Color palette: {palette or 'vibrant fruit colors, fresh greens, clean whites'}. "
        f"Layout guidance: {layout_guidance}. "
        f"Business: {business_name or 'not specified'}. Product: {brief.product}. Offer: {brief.offer}. "
        f"Constraints: {constraints or 'No people; no faces; no extra slogans'}. "
        "Use high-quality lighting and depth. Make the background visually rich but not busy."
    )


def image_prompt(brief: CreativeBrief, style: BrandStyle, copy: CopyVariant) -> str:
    return background_prompt(brief, style, copy)


def negative_prompt() -> str:
    return (
        "Avoid any text, letters, words, or signage. Avoid illegible or distorted text, "
        "cluttered layouts, and low contrast. Avoid extra text not provided. "
        "Avoid faces, hands, or people."
    )
