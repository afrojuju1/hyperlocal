from __future__ import annotations

import json
import subprocess
from pathlib import Path

from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief
from hyperlocal.prompt_templates import _format_hours


_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (17, 17, 17),
    "white": (255, 255, 255),
    "navy": (10, 33, 64),
    "gold": (212, 175, 55),
    "blue": (30, 103, 182),
    "red": (200, 32, 32),
    "green": (28, 140, 85),
    "mint green": (152, 255, 204),
    "coral": (255, 127, 80),
    "sunny yellow": (255, 214, 64),
}


def _text(value: str | None) -> str:
    return json.dumps(value or "")


def _color_expr(value: str | None, fallback: tuple[int, int, int]) -> str:
    if not value:
        return f"rgb({fallback[0]}, {fallback[1]}, {fallback[2]})"
    raw = value.strip().lower()
    if raw in _NAMED_COLORS:
        r, g, b = _NAMED_COLORS[raw]
        return f"rgb({r}, {g}, {b})"
    if raw.startswith("#"):
        hex_value = raw.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join([ch * 2 for ch in hex_value])
        if len(hex_value) == 6:
            try:
                r = int(hex_value[0:2], 16)
                g = int(hex_value[2:4], 16)
                b = int(hex_value[4:6], 16)
                return f"rgb({r}, {g}, {b})"
            except ValueError:
                pass
    return f"rgb({fallback[0]}, {fallback[1]}, {fallback[2]})"


def _build_business_block(brief: CreativeBrief) -> str:
    details = brief.business_details
    if not details:
        return ""
    hours_text = _format_hours(details)
    parts = [
        details.name,
        details.address,
        " ".join(
            part for part in [details.city, details.state, details.postal_code] if part
        ),
        details.phone,
        details.website,
        hours_text,
        details.service_area,
    ]
    clean = [part for part in parts if part]
    return " ".join(clean)


def build_typst_document(
    *,
    brief: CreativeBrief,
    style: BrandStyle,
    copy: CopyVariant,
    width_in: float,
    height_in: float,
) -> str:
    palette = style.palette or brief.brand_colors or []
    headline_color = palette[0] if palette else None
    accent_color = palette[1] if len(palette) > 1 else palette[0] if palette else None
    headline_expr = _color_expr(headline_color, (17, 17, 17))
    accent_expr = _color_expr(accent_color, (30, 103, 182))
    body_expr = _color_expr(None, (20, 20, 20))
    business_block = _build_business_block(brief)
    return f"""#set page(width: {width_in}in, height: {height_in}in, margin: (x: 0.35in, y: 0.35in), fill: none)
#set text(size: 18pt, fill: {body_expr})

#align(top)[
#stack(
  spacing: 0.12in,
  [#text({_text(copy.headline)}, size: 48pt, weight: \"bold\", fill: {headline_expr})],
  [#text({_text(copy.subhead)}, size: 26pt, weight: \"semibold\", fill: {accent_expr})],
  [#text({_text(copy.body)}, size: 20pt)],
  [#rect(width: 100%, height: 0.6in, fill: {accent_expr}, radius: 6pt, inset: (x: 0.18in, y: 0.1in))
    #align(center)[#text({_text(copy.cta)}, size: 22pt, weight: \"bold\", fill: white)]
  ],
  [#text({_text(copy.disclaimer or "")}, size: 14pt, fill: rgb(51, 51, 51))],
  [#text({_text(business_block)}, size: 14pt, fill: rgb(17, 17, 17))],
  [#text({_text(brief.audience or "")}, size: 12pt, fill: rgb(85, 85, 85))]
)
]
"""


def render_typst_overlay(
    *,
    brief: CreativeBrief,
    style: BrandStyle,
    copy: CopyVariant,
    output_path: str,
    size: str,
    pixel_size: str | None = None,
    typst_bin: str = "typst",
) -> None:
    size_parts = size.lower().split("x")
    if len(size_parts) != 2:
        raise ValueError(f"Invalid flyer size: {size}")
    width_in = float(size_parts[0])
    height_in = float(size_parts[1])

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    typst_path = output.with_suffix(".typ")
    typst_source = build_typst_document(
        brief=brief,
        style=style,
        copy=copy,
        width_in=width_in,
        height_in=height_in,
    )
    typst_path.write_text(typst_source, encoding="utf-8")

    cmd = [
        typst_bin,
        "compile",
        str(typst_path),
        str(output),
        "--format",
        "png",
    ]
    if pixel_size:
        pixel_parts = pixel_size.lower().split("x")
        if len(pixel_parts) == 2:
            try:
                px_width = int(pixel_parts[0])
                if px_width > 0:
                    ppi = int(round(px_width / width_in))
                    cmd.extend(["--ppi", str(ppi)])
            except ValueError:
                pass
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Typst binary not found. Install typst or set TYPST_BIN."
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            "Typst compilation failed: "
            + (result.stderr.strip() or result.stdout.strip())
        )
