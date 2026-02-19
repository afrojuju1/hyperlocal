from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


@dataclass(frozen=True)
class OverlayCopy:
    headline: str
    subhead: str
    offer: str
    cta: str
    footer: str = ""


@dataclass(frozen=True)
class TemplateVariant:
    name: str
    fonts: dict[str, str]
    colors: dict[str, str]
    layout: dict[str, float]


@dataclass(frozen=True)
class BrandKit:
    name: str
    fonts: dict[str, str]
    colors: dict[str, str]
    layout: dict[str, float]
    templates: list[TemplateVariant]


_DEFAULT_FONTS: dict[str, str] = {
    "headline": "DejaVuSans-Bold.ttf",
    "subhead": "DejaVuSans-Bold.ttf",
    "offer": "DejaVuSans-Bold.ttf",
    "cta": "DejaVuSans-Bold.ttf",
    "footer": "DejaVuSans.ttf",
}

_DEFAULT_COLORS: dict[str, str] = {
    "top_panel_bg": "#FFFFFFE0",
    "top_text": "#111111FF",
    "subhead_text": "#111111FF",
    "offer_card_bg": "#FFFFFFE8",
    "offer_text": "#111111FF",
    "cta_bg": "#0B7DE9FF",
    "cta_text": "#FFFFFFFF",
    "footer_bg": "#0B7DE9FF",
    "footer_text": "#FFFFFFFF",
}

_DEFAULT_LAYOUT: dict[str, float] = {
    "margin_ratio": 0.05,
    "panel_padding_ratio": 0.02,
    "corner_radius_ratio": 0.025,
    "top_panel_height_ratio": 0.20,
    "top_panel_width_ratio": 1.00,
    "top_panel_x_ratio": 0.50,
    "top_panel_y_offset_ratio": 0.00,
    "top_headline_split_ratio": 0.58,
    "offer_card_height_ratio": 0.22,
    "offer_panel_width_ratio": 1.00,
    "offer_panel_x_ratio": 0.50,
    "offer_panel_bottom_offset_ratio": 0.00,
    "cta_width_ratio": 0.50,
    "cta_height_ratio": 0.09,
    "cta_x_ratio": 0.50,
    "footer_height_ratio": 0.08,
    "headline_size_ratio": 0.09,
    "subhead_size_ratio": 0.06,
    "offer_size_ratio": 0.055,
    "cta_size_ratio": 0.05,
    "footer_size_ratio": 0.03,
    "headline_max_lines": 1.0,
    "subhead_max_lines": 1.0,
    "offer_max_lines": 2.0,
}


def _merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(merged.get(key), dict) and isinstance(value, dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def _coerce_templates(
    *,
    base_fonts: dict[str, str],
    base_colors: dict[str, str],
    base_layout: dict[str, float],
    raw_templates: Any,
) -> list[TemplateVariant]:
    if not isinstance(raw_templates, list):
        return []
    templates: list[TemplateVariant] = []
    for idx, item in enumerate(raw_templates, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or f"template_{idx}")
        fonts = _merge_dict(base_fonts, item.get("fonts", {}))
        colors = _merge_dict(base_colors, item.get("colors", {}))
        layout = _merge_dict(base_layout, item.get("layout", {}))
        templates.append(
            TemplateVariant(
                name=name,
                fonts=fonts,
                colors=colors,
                layout=layout,
            )
        )
    return templates


def load_brand_kit(path: str | Path) -> BrandKit:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    fonts = _merge_dict(_DEFAULT_FONTS, data.get("fonts", {}))
    colors = _merge_dict(_DEFAULT_COLORS, data.get("colors", {}))
    layout = _merge_dict(_DEFAULT_LAYOUT, data.get("layout", {}))
    templates = _coerce_templates(
        base_fonts=fonts,
        base_colors=colors,
        base_layout=layout,
        raw_templates=data.get("templates", []),
    )
    return BrandKit(
        name=str(data.get("name") or p.stem),
        fonts=fonts,
        colors=colors,
        layout=layout,
        templates=templates,
    )


def resolve_template(brand_kit: BrandKit, *, name: str | None = None, index: int | None = None) -> TemplateVariant | None:
    if not brand_kit.templates:
        return None
    if name:
        for template in brand_kit.templates:
            if template.name == name:
                return template
        return None
    if index is not None and 0 <= index < len(brand_kit.templates):
        return brand_kit.templates[index]
    return brand_kit.templates[0]


def _parse_rgba(color: str, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    raw = (color or "").strip()
    if not raw:
        return fallback
    if raw.lower() == "transparent":
        return (0, 0, 0, 0)
    if raw.startswith("#"):
        hex_raw = raw[1:]
        try:
            if len(hex_raw) == 3:  # RGB
                r = int(hex_raw[0] * 2, 16)
                g = int(hex_raw[1] * 2, 16)
                b = int(hex_raw[2] * 2, 16)
                return (r, g, b, 255)
            if len(hex_raw) == 4:  # RGBA
                r = int(hex_raw[0] * 2, 16)
                g = int(hex_raw[1] * 2, 16)
                b = int(hex_raw[2] * 2, 16)
                a = int(hex_raw[3] * 2, 16)
                return (r, g, b, a)
            if len(hex_raw) == 6:  # RRGGBB
                r = int(hex_raw[0:2], 16)
                g = int(hex_raw[2:4], 16)
                b = int(hex_raw[4:6], 16)
                return (r, g, b, 255)
            if len(hex_raw) == 8:  # RRGGBBAA
                r = int(hex_raw[0:2], 16)
                g = int(hex_raw[2:4], 16)
                b = int(hex_raw[4:6], 16)
                a = int(hex_raw[6:8], 16)
                return (r, g, b, a)
        except ValueError:
            return fallback
    return fallback


def _load_font(font_name: str, size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        font_name,
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ]
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    raise RuntimeError(f"Unable to load TrueType font. Tried: {', '.join(candidates)}")


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    stripped = (text or "").strip()
    if not stripped:
        return [""]
    words = stripped.split()
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        width = draw.textbbox((0, 0), candidate, font=font)[2]
        if width <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_text(
    *,
    draw: ImageDraw.ImageDraw,
    text: str,
    font_name: str,
    max_width: int,
    max_height: int,
    max_lines: int,
    start_size: int,
    min_size: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(max(start_size, min_size), min_size - 1, -1):
        font = _load_font(font_name, size)
        lines = _wrap_text(draw, text, font, max_width)
        if len(lines) > max_lines:
            continue
        line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
        spacing = max(2, int(size * 0.20))
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
        widest = max((draw.textbbox((0, 0), line, font=font)[2] for line in lines), default=0)
        if widest <= max_width and total_height <= max_height:
            return font, lines
    raise RuntimeError(f'Text does not fit in layout without alteration: "{text}"')


def _draw_centered_lines(
    *,
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    box: tuple[int, int, int, int],
) -> None:
    line_height = draw.textbbox((0, 0), "Ag", font=font)[3]
    spacing = max(2, int(font.size * 0.20))
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
    x0, y0, x1, y1 = box
    y = y0 + max(0, (y1 - y0 - total_height) // 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = x0 + max(0, (x1 - x0 - line_w) // 2)
        draw.text((x, y), line, font=font, fill=fill)
        y += line_height + spacing


def _clamp_ratio(value: float, default: float = 0.5) -> float:
    try:
        as_float = float(value)
    except (TypeError, ValueError):
        as_float = default
    return max(0.0, min(1.0, as_float))


def _panel_box(
    *,
    canvas_w: int,
    canvas_h: int,
    margin: int,
    panel_w: int,
    panel_h: int,
    x_ratio: float,
    y_top: int,
) -> tuple[int, int, int, int]:
    inner_w = max(1, canvas_w - (2 * margin))
    inner_h = max(1, canvas_h - (2 * margin))
    safe_w = min(max(1, panel_w), inner_w)
    safe_h = min(max(1, panel_h), inner_h)
    x_span = max(0, inner_w - safe_w)
    x0 = margin + int(x_span * _clamp_ratio(x_ratio))
    y_min = margin
    y_max = margin + inner_h - safe_h
    y0 = max(y_min, min(y_max, y_top))
    return (x0, y0, x0 + safe_w, y0 + safe_h)


def compose_deterministic_overlay(
    *,
    input_image_path: str | Path,
    output_image_path: str | Path,
    copy: OverlayCopy,
    brand_kit: BrandKit,
    template: TemplateVariant | None = None,
) -> None:
    src = Path(input_image_path)
    dst = Path(output_image_path)
    dst.parent.mkdir(parents=True, exist_ok=True)

    if template:
        fonts = template.fonts
        colors = template.colors
        layout = template.layout
    else:
        fonts = brand_kit.fonts
        colors = brand_kit.colors
        layout = brand_kit.layout

    base = Image.open(src).convert("RGBA")
    w, h = base.size
    short_side = min(w, h)

    margin = int(short_side * float(layout["margin_ratio"]))
    panel_pad = int(short_side * float(layout["panel_padding_ratio"]))
    radius = int(short_side * float(layout["corner_radius_ratio"]))

    top_h = int(h * float(layout["top_panel_height_ratio"]))
    top_w = int((w - (2 * margin)) * float(layout["top_panel_width_ratio"]))
    top_y = margin + int(h * float(layout["top_panel_y_offset_ratio"]))

    offer_h = int(h * float(layout["offer_card_height_ratio"]))
    offer_w = int((w - (2 * margin)) * float(layout["offer_panel_width_ratio"]))
    footer_h = int(h * float(layout["footer_height_ratio"])) if copy.footer.strip() else 0
    offer_bottom = h - margin - footer_h - int(h * float(layout["offer_panel_bottom_offset_ratio"]))

    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    top_panel = _panel_box(
        canvas_w=w,
        canvas_h=h,
        margin=margin,
        panel_w=top_w,
        panel_h=top_h,
        x_ratio=float(layout["top_panel_x_ratio"]),
        y_top=top_y,
    )
    offer_panel = _panel_box(
        canvas_w=w,
        canvas_h=h,
        margin=margin,
        panel_w=offer_w,
        panel_h=offer_h,
        x_ratio=float(layout["offer_panel_x_ratio"]),
        y_top=offer_bottom - offer_h,
    )
    footer_panel = (margin, h - margin - footer_h, w - margin, h - margin) if footer_h > 0 else None

    draw.rounded_rectangle(
        top_panel,
        radius=radius,
        fill=_parse_rgba(colors["top_panel_bg"], (255, 255, 255, 224)),
    )
    draw.rounded_rectangle(
        offer_panel,
        radius=radius,
        fill=_parse_rgba(colors["offer_card_bg"], (255, 255, 255, 232)),
    )
    if footer_panel:
        draw.rounded_rectangle(
            footer_panel,
            radius=radius,
            fill=_parse_rgba(colors["footer_bg"], (11, 125, 233, 255)),
        )

    top_inner = (
        top_panel[0] + panel_pad,
        top_panel[1] + panel_pad,
        top_panel[2] - panel_pad,
        top_panel[3] - panel_pad,
    )
    if copy.subhead.strip():
        split_ratio = _clamp_ratio(float(layout["top_headline_split_ratio"]), 0.58)
        split_y = top_inner[1] + int((top_inner[3] - top_inner[1]) * split_ratio)
        headline_box = (top_inner[0], top_inner[1], top_inner[2], split_y)
        subhead_box = (top_inner[0], split_y, top_inner[2], top_inner[3])
    else:
        headline_box = top_inner
        subhead_box = None

    headline_font, headline_lines = _fit_text(
        draw=draw,
        text=copy.headline,
        font_name=fonts["headline"],
        max_width=max(1, headline_box[2] - headline_box[0]),
        max_height=max(1, headline_box[3] - headline_box[1]),
        max_lines=max(1, int(layout["headline_max_lines"])),
        start_size=max(12, int(h * float(layout["headline_size_ratio"]))),
        min_size=12,
    )
    _draw_centered_lines(
        draw=draw,
        lines=headline_lines,
        font=headline_font,
        fill=_parse_rgba(colors["top_text"], (17, 17, 17, 255)),
        box=headline_box,
    )

    if subhead_box and copy.subhead.strip():
        sub_font, sub_lines = _fit_text(
            draw=draw,
            text=copy.subhead,
            font_name=fonts["subhead"],
            max_width=max(1, subhead_box[2] - subhead_box[0]),
            max_height=max(1, subhead_box[3] - subhead_box[1]),
            max_lines=max(1, int(layout["subhead_max_lines"])),
            start_size=max(12, int(h * float(layout["subhead_size_ratio"]))),
            min_size=12,
        )
        _draw_centered_lines(
            draw=draw,
            lines=sub_lines,
            font=sub_font,
            fill=_parse_rgba(colors["subhead_text"], (17, 17, 17, 255)),
            box=subhead_box,
        )

    cta_h = int(h * float(layout["cta_height_ratio"]))
    offer_inner_w = max(1, offer_panel[2] - offer_panel[0])
    offer_inner_h = max(1, offer_panel[3] - offer_panel[1])
    cta_w = int(offer_inner_w * float(layout["cta_width_ratio"]))
    cta_w = max(1, min(cta_w, max(1, offer_inner_w - (panel_pad * 2))))
    cta_h = max(1, min(cta_h, max(1, offer_inner_h - (panel_pad * 2))))
    cta_x_ratio = _clamp_ratio(float(layout["cta_x_ratio"]), 0.5)
    cta_left = offer_panel[0] + int(max(0, (offer_inner_w - cta_w)) * cta_x_ratio)
    cta_box = (
        cta_left,
        offer_panel[3] - panel_pad - cta_h,
        cta_left + cta_w,
        offer_panel[3] - panel_pad,
    )
    draw.rounded_rectangle(
        cta_box,
        radius=max(8, int(radius * 0.8)),
        fill=_parse_rgba(colors["cta_bg"], (11, 125, 233, 255)),
    )

    offer_box = (
        offer_panel[0] + panel_pad,
        offer_panel[1] + panel_pad,
        offer_panel[2] - panel_pad,
        cta_box[1] - panel_pad,
    )
    offer_font, offer_lines = _fit_text(
        draw=draw,
        text=copy.offer,
        font_name=fonts["offer"],
        max_width=max(1, offer_box[2] - offer_box[0]),
        max_height=max(1, offer_box[3] - offer_box[1]),
        max_lines=max(1, int(layout["offer_max_lines"])),
        start_size=max(12, int(h * float(layout["offer_size_ratio"]))),
        min_size=12,
    )
    _draw_centered_lines(
        draw=draw,
        lines=offer_lines,
        font=offer_font,
        fill=_parse_rgba(colors["offer_text"], (17, 17, 17, 255)),
        box=offer_box,
    )

    cta_font, cta_lines = _fit_text(
        draw=draw,
        text=copy.cta,
        font_name=fonts["cta"],
        max_width=max(1, cta_box[2] - cta_box[0] - panel_pad),
        max_height=max(1, cta_box[3] - cta_box[1] - panel_pad),
        max_lines=1,
        start_size=max(12, int(h * float(layout["cta_size_ratio"]))),
        min_size=12,
    )
    _draw_centered_lines(
        draw=draw,
        lines=cta_lines,
        font=cta_font,
        fill=_parse_rgba(colors["cta_text"], (255, 255, 255, 255)),
        box=cta_box,
    )

    if footer_panel and copy.footer.strip():
        footer_font, footer_lines = _fit_text(
            draw=draw,
            text=copy.footer,
            font_name=fonts["footer"],
            max_width=max(1, footer_panel[2] - footer_panel[0] - (panel_pad * 2)),
            max_height=max(1, footer_panel[3] - footer_panel[1] - (panel_pad * 2)),
            max_lines=1,
            start_size=max(10, int(h * float(layout["footer_size_ratio"]))),
            min_size=10,
        )
        _draw_centered_lines(
            draw=draw,
            lines=footer_lines,
            font=footer_font,
            fill=_parse_rgba(colors["footer_text"], (255, 255, 255, 255)),
            box=footer_panel,
        )

    final = Image.alpha_composite(base, overlay).convert("RGB")
    final.save(dst, format="PNG")
