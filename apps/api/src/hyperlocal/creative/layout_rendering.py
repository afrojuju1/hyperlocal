from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Literal

from PIL import Image, ImageDraw, ImageFont

from hyperlocal.creative.contracts import CreativeCopyInput, CreativeRunRequest
from hyperlocal.creative.image_generation import GeneratedCreative
from hyperlocal.creative.vertical_config import vertical_layout_defaults
from hyperlocal.integrations.llm import build_llm_clients
from hyperlocal.integrations.openai import chat_json


TextRole = Literal["headline", "subhead", "offer"]
TextAlign = Literal["left", "center", "right"]
TextValign = Literal["top", "center", "bottom"]


@dataclass(frozen=True)
class LayoutTextElement:
    role: TextRole
    text: str
    x: float
    y: float
    width: float
    height: float
    align: TextAlign = "center"
    valign: TextValign = "center"
    font_role: str = "display"
    color: str = "auto"
    stroke_color: str | None = "auto"
    stroke_width: float = 0.004
    shadow: bool = True
    max_lines: int = 2


@dataclass(frozen=True)
class CreativeLayoutPlan:
    name: str
    elements: list[LayoutTextElement]
    notes: str = ""


@dataclass(frozen=True)
class LayoutRenderResult:
    variant_index: int
    prompt_slug: str
    background_image_url: str
    final_image_url: str
    overlay_template: str
    layout_plan: dict[str, Any]


class LayoutRenderingService:
    """Renders exact ad typography from an AI layout plan without boxes or coupons."""

    OVERLAY_TEMPLATE = "ai_layout_typography"

    def __init__(self, *, enable_llm: bool = True) -> None:
        self._enable_llm = enable_llm

    def render(
        self,
        *,
        request: CreativeRunRequest,
        run_dir: Path,
        source_images: list[GeneratedCreative],
        copies: list[CreativeCopyInput],
    ) -> list[LayoutRenderResult]:
        if not source_images:
            return []

        out_dir = run_dir / "final"
        plan_dir = run_dir / "layout_plans"
        out_dir.mkdir(parents=True, exist_ok=True)
        plan_dir.mkdir(parents=True, exist_ok=True)

        results: list[LayoutRenderResult] = []
        for source in source_images:
            copy = copies[(source.prompt_index - 1) % len(copies)]
            plan = self._plan_layout(request=request, source=source, copy=copy)
            plan = self._refine_plan_for_image(input_image_path=source.image_path, plan=plan)
            plan = self._apply_brand_defaults(request=request, plan=plan)
            final_path = out_dir / f"{source.variant_index:03d}__{source.prompt_slug}__typography.png"
            self._render_plan(
                input_image_path=source.image_path,
                output_image_path=final_path,
                plan=plan,
            )

            plan_payload = asdict(plan)
            plan_path = plan_dir / f"{source.variant_index:03d}__{source.prompt_slug}.json"
            plan_path.write_text(json.dumps(plan_payload, indent=2) + "\n", encoding="utf-8")

            results.append(
                LayoutRenderResult(
                    variant_index=source.variant_index,
                    prompt_slug=source.prompt_slug,
                    background_image_url=source.image_path,
                    final_image_url=str(final_path),
                    overlay_template=self.OVERLAY_TEMPLATE,
                    layout_plan={
                        "variant_index": source.variant_index,
                        "prompt_slug": source.prompt_slug,
                        "plan_path": str(plan_path),
                        **plan_payload,
                    },
                )
            )

        return results

    def _refine_plan_for_image(
        self,
        *,
        input_image_path: str | Path,
        plan: CreativeLayoutPlan,
    ) -> CreativeLayoutPlan:
        base = Image.open(input_image_path).convert("RGB")
        refined: list[LayoutTextElement] = []
        moved = False
        for element in plan.elements:
            next_element = element
            if element.role == "offer":
                next_element = _choose_calm_offer_zone(base=base, element=element, occupied=refined)
                moved = moved or next_element != element
            refined.append(next_element)

        if not moved:
            return plan
        notes = " ".join(part for part in [plan.notes, "Offer moved to a calmer image zone."] if part)
        return CreativeLayoutPlan(name=plan.name, elements=refined, notes=notes)

    def _apply_brand_defaults(
        self,
        *,
        request: CreativeRunRequest,
        plan: CreativeLayoutPlan,
    ) -> CreativeLayoutPlan:
        defaults = vertical_layout_defaults(request.campaign.business_kind)
        if not defaults:
            return plan

        headline_color = defaults.get("headline_color", "auto")
        offer_color = defaults.get("offer_color", headline_color)
        stroke_color = defaults.get("stroke_color", "auto")

        elements: list[LayoutTextElement] = []
        for element in plan.elements:
            if element.color != "auto":
                elements.append(element)
                continue
            if element.role == "offer":
                elements.append(replace(element, color=offer_color, stroke_color=stroke_color))
            else:
                elements.append(replace(element, color=headline_color, stroke_color=stroke_color))
        return CreativeLayoutPlan(name=plan.name, elements=elements, notes=plan.notes)

    def _plan_layout(
        self,
        *,
        request: CreativeRunRequest,
        source: GeneratedCreative,
        copy: CreativeCopyInput,
    ) -> CreativeLayoutPlan:
        if not self._enable_llm:
            return self._fallback_plan(request=request, source=source, copy=copy)

        try:
            data = self._call_layout_planner(request=request, source=source, copy=copy)
            return self._coerce_plan(data=data, request=request, source=source, copy=copy)
        except Exception as exc:
            fallback = self._fallback_plan(request=request, source=source, copy=copy)
            return CreativeLayoutPlan(
                name=fallback.name,
                elements=fallback.elements,
                notes=f"Fallback layout used because planner failed: {type(exc).__name__}",
            )

    def _call_layout_planner(
        self,
        *,
        request: CreativeRunRequest,
        source: GeneratedCreative,
        copy: CreativeCopyInput,
    ) -> Any:
        llm = build_llm_clients()
        prompt = "\n".join(
            [
                "You are an ad art director planning exact typography placement over a text-free 6x9 generated image.",
                "Return JSON only. Do not include markdown.",
                "",
                "Job:",
                "- Choose the typography hierarchy, placement, alignment, and contrast treatment.",
                "- The background image already exists and must remain photographic.",
                "- The renderer will draw exact text from your plan; do not rewrite the supplied strings.",
                "- Do not add boxes, banners, stickers, coupons, pill bars, button shapes, labels, or panels.",
                "- Use natural negative space and let text sit directly in the composition with stroke/shadow for legibility.",
                "- Use a clean two-element layout: business name plus offer.",
                "- Do not include product, subhead, CTA, phone, website, address, or disclaimer text in the artwork.",
                "",
                "Coordinate system:",
                "- x, y, width, height are normalized 0.0 to 1.0.",
                "- Keep every text box inside a 0.04 safe margin.",
                "- Use no more than 3 elements.",
                "",
                "Return this shape:",
                "{",
                '  "name": "short_snake_case_name",',
                '  "notes": "short rationale",',
                '  "elements": [',
                "    {",
                '      "role": "headline",',
                f'      "text": "{_json_quote(copy.headline)}",',
                '      "x": 0.08, "y": 0.06, "width": 0.84, "height": 0.18,',
                '      "align": "center", "valign": "center",',
                '      "font_role": "display",',
                '      "color": "auto", "stroke_color": "auto",',
                '      "stroke_width": 0.004, "shadow": true, "max_lines": 1',
                "    }",
                "  ]",
                "}",
                "",
                "Allowed exact text strings:",
                f'- headline: "{copy.headline}"',
                f'- offer: "{copy.offer}"',
                "",
                "Brief:",
                f"- business kind: {request.campaign.business_kind}",
                f"- product: {request.campaign.product}",
                f"- offer: {request.campaign.offer}",
                f"- tone: {request.campaign.tone}",
                f"- audience: {request.campaign.audience or 'not specified'}",
                f"- brand colors: {', '.join(request.campaign.brand_colors) or 'not specified'}",
                f"- style keywords: {', '.join(request.campaign.style_keywords) or 'not specified'}",
                f"- user constraints: {', '.join(request.campaign.constraints) or 'none'}",
                "",
                "Source image prompt context:",
                f"- title: {source.prompt_title}",
                f"- prompt: {source.prompt}",
                "",
                "JSON only.",
            ]
        )
        return chat_json(llm.text_client, llm.text_model, messages=[{"role": "user", "content": prompt}])

    def _coerce_plan(
        self,
        *,
        data: Any,
        request: CreativeRunRequest,
        source: GeneratedCreative,
        copy: CreativeCopyInput,
    ) -> CreativeLayoutPlan:
        if not isinstance(data, dict):
            raise ValueError("layout plan must be an object")

        raw_elements = data.get("elements")
        if not isinstance(raw_elements, list):
            raise ValueError("layout plan elements must be a list")

        exact_text_by_role: dict[str, str] = {
            "headline": copy.headline,
            "offer": copy.offer,
        }

        elements: list[LayoutTextElement] = []
        seen_roles: set[str] = set()
        for raw in raw_elements[:3]:
            if not isinstance(raw, dict):
                continue
            role = _coerce_role(raw.get("role"))
            if role is None or role in seen_roles or role not in exact_text_by_role:
                continue
            seen_roles.add(role)
            elements.append(
                LayoutTextElement(
                    role=role,
                    text=exact_text_by_role[role],
                    x=_clamp_float(raw.get("x"), 0.08, 0.03, 0.92),
                    y=_clamp_float(raw.get("y"), 0.08, 0.03, 0.92),
                    width=_clamp_float(raw.get("width"), 0.84, 0.16, 0.94),
                    height=_clamp_float(raw.get("height"), 0.16, 0.06, 0.36),
                    align=_coerce_align(raw.get("align")),
                    valign=_coerce_valign(raw.get("valign")),
                    font_role=_coerce_font_role(raw.get("font_role"), role),
                    color=_coerce_color(raw.get("color"), "auto"),
                    stroke_color=_coerce_optional_color(raw.get("stroke_color"), "auto"),
                    stroke_width=_clamp_float(raw.get("stroke_width"), 0.004, 0.0, 0.012),
                    shadow=bool(raw.get("shadow", True)),
                    max_lines=_coerce_max_lines(raw.get("max_lines"), role),
                )
            )

        roles = {element.role for element in elements}
        if "headline" not in roles or "offer" not in roles:
            raise ValueError("layout plan must include headline and offer")

        normalized = [_normalize_box(element) for element in elements]
        return CreativeLayoutPlan(
            name=_safe_plan_name(str(data.get("name") or f"ai_layout_{source.variant_index}")),
            elements=normalized,
            notes=str(data.get("notes") or ""),
        )

    def _fallback_plan(
        self,
        *,
        request: CreativeRunRequest,
        source: GeneratedCreative,
        copy: CreativeCopyInput,
    ) -> CreativeLayoutPlan:
        variant = (source.variant_index - 1) % 3
        if variant == 1:
            headline = LayoutTextElement(
                role="headline",
                text=copy.headline,
                x=0.07,
                y=0.06,
                width=0.55,
                height=0.18,
                align="left",
                font_role="display",
                max_lines=2,
            )
            offer = LayoutTextElement(
                role="offer",
                text=copy.offer,
                x=0.34,
                y=0.73,
                width=0.58,
                height=0.17,
                align="right",
                font_role="offer",
                max_lines=2,
            )
        elif variant == 2:
            headline = LayoutTextElement(
                role="headline",
                text=copy.headline,
                x=0.34,
                y=0.06,
                width=0.58,
                height=0.17,
                align="right",
                font_role="display",
                max_lines=2,
            )
            offer = LayoutTextElement(
                role="offer",
                text=copy.offer,
                x=0.07,
                y=0.70,
                width=0.62,
                height=0.19,
                align="left",
                font_role="offer",
                max_lines=2,
            )
        else:
            headline = LayoutTextElement(
                role="headline",
                text=copy.headline,
                x=0.08,
                y=0.06,
                width=0.84,
                height=0.17,
                align="center",
                font_role="display",
                max_lines=1,
            )
            offer = LayoutTextElement(
                role="offer",
                text=copy.offer,
                x=0.10,
                y=0.73,
                width=0.80,
                height=0.17,
                align="center",
                font_role="offer",
                max_lines=2,
            )

        return CreativeLayoutPlan(
            name=f"fallback_open_typography_{request.campaign.business_kind}",
            elements=[headline, offer],
            notes="Fallback layout: exact typography directly over the image with no boxes.",
        )

    def _render_plan(
        self,
        *,
        input_image_path: str | Path,
        output_image_path: str | Path,
        plan: CreativeLayoutPlan,
    ) -> None:
        src = Path(input_image_path)
        dst = Path(output_image_path)
        dst.parent.mkdir(parents=True, exist_ok=True)

        base = Image.open(src).convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        for element in plan.elements:
            _draw_element(base=base, draw=draw, element=element)

        Image.alpha_composite(base, overlay).convert("RGB").save(dst, format="PNG")


def _json_quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _safe_plan_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value.lower()).strip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned or "ai_layout"


def _coerce_role(value: Any) -> TextRole | None:
    role = str(value or "").strip().lower()
    if role in {"business", "brand", "name"}:
        role = "headline"
    if role in {"product", "body"}:
        role = "subhead"
    if role in {"deal", "promo", "promotion"}:
        role = "offer"
    if role in {"headline", "subhead", "offer"}:
        return role  # type: ignore[return-value]
    return None


def _coerce_align(value: Any) -> TextAlign:
    align = str(value or "").strip().lower()
    if align in {"left", "center", "right"}:
        return align  # type: ignore[return-value]
    return "center"


def _coerce_valign(value: Any) -> TextValign:
    valign = str(value or "").strip().lower()
    if valign in {"top", "center", "bottom"}:
        return valign  # type: ignore[return-value]
    return "center"


def _coerce_font_role(value: Any, role: TextRole) -> str:
    font_role = str(value or "").strip().lower()
    if font_role in {"display", "offer", "bold", "serif", "sans"}:
        return font_role
    if role == "headline":
        return "display"
    if role == "offer":
        return "offer"
    return "sans"


def _coerce_max_lines(value: Any, role: TextRole) -> int:
    default = 2 if role in {"headline", "offer"} else 1
    max_lines = int(_clamp_float(value, default, 1, 3))
    if role == "offer":
        return max(2, max_lines)
    return max_lines


def _clamp_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(low, min(high, number))


def _coerce_color(value: Any, default: str) -> str:
    raw = str(value or "").strip()
    if raw.lower() == "auto":
        return "auto"
    if _is_hex_color(raw):
        return raw
    return default


def _coerce_optional_color(value: Any, default: str | None) -> str | None:
    if value is None:
        return default
    raw = str(value).strip()
    if raw.lower() in {"none", "null", "transparent"}:
        return None
    return _coerce_color(raw, default or "auto")


def _is_hex_color(value: str) -> bool:
    if not value.startswith("#"):
        return False
    raw = value[1:]
    return len(raw) in {6, 8} and all(ch in "0123456789abcdefABCDEF" for ch in raw)


def _normalize_box(element: LayoutTextElement) -> LayoutTextElement:
    width = max(0.16, min(0.94, element.width))
    height = max(0.06, min(0.36, element.height))
    x = max(0.03, min(0.97 - width, element.x))
    y = max(0.03, min(0.97 - height, element.y))
    return LayoutTextElement(
        role=element.role,
        text=element.text,
        x=x,
        y=y,
        width=width,
        height=height,
        align=element.align,
        valign=element.valign,
        font_role=element.font_role,
        color=element.color,
        stroke_color=element.stroke_color,
        stroke_width=element.stroke_width,
        shadow=element.shadow,
        max_lines=element.max_lines,
    )


def _choose_calm_offer_zone(
    *,
    base: Image.Image,
    element: LayoutTextElement,
    occupied: list[LayoutTextElement],
) -> LayoutTextElement:
    candidate_ys = [element.y, 0.24, 0.30, 0.62, 0.70, 0.78]
    candidates = [
        _normalize_box(replace(element, y=y))
        for y in candidate_ys
    ]
    scored = [
        (_zone_score(base=base, element=candidate, occupied=occupied), candidate)
        for candidate in candidates
    ]
    current_score = _zone_score(base=base, element=element, occupied=occupied)
    best_score, best = min(scored, key=lambda item: item[0])
    in_central_band = 0.28 <= element.y <= 0.62
    if in_central_band or best_score + 8 < current_score:
        return best
    return element


def _zone_score(
    *,
    base: Image.Image,
    element: LayoutTextElement,
    occupied: list[LayoutTextElement],
) -> float:
    w, h = base.size
    box = (
        int(w * element.x),
        int(h * element.y),
        int(w * (element.x + element.width)),
        int(h * (element.y + element.height)),
    )
    x0 = max(0, min(w - 1, box[0]))
    y0 = max(0, min(h - 1, box[1]))
    x1 = max(x0 + 1, min(w, box[2]))
    y1 = max(y0 + 1, min(h, box[3]))
    crop = base.crop((x0, y0, x1, y1)).convert("L").resize((48, 48))
    px = crop.load()
    values = [px[x, y] for y in range(48) for x in range(48)]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    edge_total = 0
    edge_count = 0
    for y in range(48):
        for x in range(47):
            edge_total += abs(px[x, y] - px[x + 1, y])
            edge_count += 1
    for y in range(47):
        for x in range(48):
            edge_total += abs(px[x, y] - px[x, y + 1])
            edge_count += 1
    edge = edge_total / max(1, edge_count)
    score = (variance ** 0.5) + (edge * 1.5)

    if 0.28 <= element.y <= 0.62:
        score += 18

    for other in occupied:
        if _overlap_area_ratio(element, other) > 0:
            score += 90
    return score


def _overlap_area_ratio(a: LayoutTextElement, b: LayoutTextElement) -> float:
    ax0, ay0, ax1, ay1 = a.x, a.y, a.x + a.width, a.y + a.height
    bx0, by0, bx1, by1 = b.x, b.y, b.x + b.width, b.y + b.height
    overlap_w = max(0.0, min(ax1, bx1) - max(ax0, bx0))
    overlap_h = max(0.0, min(ay1, by1) - max(ay0, by0))
    overlap = overlap_w * overlap_h
    area = max(0.0001, a.width * a.height)
    return overlap / area


def _draw_element(
    *,
    base: Image.Image,
    draw: ImageDraw.ImageDraw,
    element: LayoutTextElement,
) -> None:
    w, h = base.size
    box = (
        int(w * element.x),
        int(h * element.y),
        int(w * (element.x + element.width)),
        int(h * (element.y + element.height)),
    )
    short_side = min(w, h)
    pad = max(2, int(short_side * 0.006))
    text_box = (box[0] + pad, box[1] + pad, box[2] - pad, box[3] - pad)
    stroke_width = max(0, int(short_side * element.stroke_width))

    fill, stroke = _resolve_colors(base=base, box=text_box, element=element)
    start_size = max(14, int((text_box[3] - text_box[1]) * 0.72))
    min_size = max(12, int(short_side * 0.026))
    font, lines = _fit_text(
        draw=draw,
        text=element.text,
        font_role=element.font_role,
        max_width=max(1, text_box[2] - text_box[0] - (stroke_width * 2)),
        max_height=max(1, text_box[3] - text_box[1] - (stroke_width * 2)),
        max_lines=element.max_lines,
        start_size=start_size,
        min_size=min_size,
        stroke_width=stroke_width,
    )

    line_height = _line_height(draw, font, stroke_width)
    spacing = max(2, int(font.size * 0.12))
    total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
    if element.valign == "top":
        y = text_box[1]
    elif element.valign == "bottom":
        y = text_box[3] - total_height
    else:
        y = text_box[1] + max(0, (text_box[3] - text_box[1] - total_height) // 2)

    shadow_offset = max(2, int(short_side * 0.006))
    for line in lines:
        line_width = _text_width(draw, line, font, stroke_width)
        if element.align == "left":
            x = text_box[0]
        elif element.align == "right":
            x = text_box[2] - line_width
        else:
            x = text_box[0] + max(0, (text_box[2] - text_box[0] - line_width) // 2)

        if element.shadow:
            shadow_fill = (0, 0, 0, 112) if _relative_luminance(fill) > 150 else (255, 255, 255, 96)
            draw.text(
                (x + shadow_offset, y + shadow_offset),
                line,
                font=font,
                fill=shadow_fill,
                stroke_width=stroke_width,
                stroke_fill=shadow_fill,
            )

        draw.text(
            (x, y),
            line,
            font=font,
            fill=fill,
            stroke_width=stroke_width,
            stroke_fill=stroke if stroke_width else fill,
        )
        y += line_height + spacing


def _resolve_colors(
    *,
    base: Image.Image,
    box: tuple[int, int, int, int],
    element: LayoutTextElement,
) -> tuple[tuple[int, int, int, int], tuple[int, int, int, int]]:
    luminance = _box_luminance(base, box)
    if element.color == "auto":
        if luminance > 140:
            fill = (18, 86, 47, 255)
            stroke = (255, 255, 247, 232)
        else:
            fill = (255, 255, 248, 255)
            stroke = (13, 50, 30, 232)
    else:
        fill = _parse_color(element.color, fallback=(255, 255, 248, 255))
        if element.stroke_color == "auto":
            stroke = (13, 50, 30, 232) if _relative_luminance(fill) > 150 else (255, 255, 247, 232)
        elif element.stroke_color is None:
            stroke = fill
        else:
            stroke = _parse_color(element.stroke_color, fallback=(13, 50, 30, 232))
    return fill, stroke


def _parse_color(value: str, *, fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    if not _is_hex_color(value):
        return fallback
    raw = value[1:]
    try:
        red = int(raw[0:2], 16)
        green = int(raw[2:4], 16)
        blue = int(raw[4:6], 16)
        alpha = int(raw[6:8], 16) if len(raw) == 8 else 255
    except ValueError:
        return fallback
    return (red, green, blue, alpha)


def _box_luminance(base: Image.Image, box: tuple[int, int, int, int]) -> float:
    w, h = base.size
    x0 = max(0, min(w - 1, box[0]))
    y0 = max(0, min(h - 1, box[1]))
    x1 = max(x0 + 1, min(w, box[2]))
    y1 = max(y0 + 1, min(h, box[3]))
    sample = base.crop((x0, y0, x1, y1)).convert("L").resize((1, 1))
    return float(sample.getpixel((0, 0)))


def _relative_luminance(color: tuple[int, int, int, int]) -> float:
    return (0.2126 * color[0]) + (0.7152 * color[1]) + (0.0722 * color[2])


def _fit_text(
    *,
    draw: ImageDraw.ImageDraw,
    text: str,
    font_role: str,
    max_width: int,
    max_height: int,
    max_lines: int,
    start_size: int,
    min_size: int,
    stroke_width: int,
) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    last_font: ImageFont.FreeTypeFont | None = None
    last_lines: list[str] = [text]
    for size in range(max(start_size, min_size), min_size - 1, -1):
        font = _load_font(font_role, size)
        lines = _wrap_text(draw=draw, text=text, font=font, max_width=max_width, stroke_width=stroke_width)
        last_font = font
        last_lines = lines
        if len(lines) > max_lines:
            continue
        line_height = _line_height(draw, font, stroke_width)
        spacing = max(2, int(size * 0.12))
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * spacing
        widest = max((_text_width(draw, line, font, stroke_width) for line in lines), default=0)
        if widest <= max_width and total_height <= max_height:
            return font, lines
    if last_font is None:
        raise RuntimeError("Unable to load a font")
    return last_font, last_lines[:max_lines]


def _wrap_text(
    *,
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    stroke_width: int,
) -> list[str]:
    words = (text or "").strip().split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_width(draw, candidate, font, stroke_width) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _line_height(draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, stroke_width: int) -> int:
    bbox = draw.textbbox((0, 0), "Ag", font=font, stroke_width=stroke_width)
    return max(1, bbox[3] - bbox[1])


def _text_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    stroke_width: int,
) -> int:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke_width)
    return max(1, bbox[2] - bbox[0])


def _load_font(font_role: str, size: int) -> ImageFont.FreeTypeFont:
    display_fonts = [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "DejaVuSerif-Bold.ttf",
    ]
    offer_fonts = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    sans_fonts = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "DejaVuSans.ttf",
    ]
    if font_role in {"display", "serif"}:
        candidates = display_fonts + offer_fonts + sans_fonts
    elif font_role in {"offer", "bold"}:
        candidates = offer_fonts + display_fonts + sans_fonts
    else:
        candidates = sans_fonts + offer_fonts + display_fonts

    seen: set[str] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            return ImageFont.truetype(candidate, size=size)
        except OSError:
            continue
    raise RuntimeError(f"Unable to load TrueType font for role {font_role}")
