from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from hyperlocal.openai_helpers import ImageResult
from hyperlocal.prompt_templates import business_block
from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief


_PLACEHOLDER_PATTERN = re.compile(r"\{\{[^}]+\}\}")
_NAMED_COLORS: dict[str, str] = {
    "black": "#111111",
    "white": "#ffffff",
    "navy": "#0a2140",
    "gold": "#d4af37",
    "blue": "#1e67b6",
    "red": "#c82020",
    "green": "#1c8c55",
    "mint green": "#98ffcc",
    "coral": "#ff7f50",
    "sunny yellow": "#ffd640",
    "coral_red": "#ff6f61",
    "soft grey": "#d9d9d9",
    "soft gray": "#d9d9d9",
    "citrus yellow": "#ffd640",
    "sky blue": "#62b6ff",
    "mushroom tan": "#cdb79e",
    "powder pink": "#ffd1dc",
}


@dataclass
class ComfyUiConfig:
    api_url: str
    workflow_path: str
    width: int
    height: int
    timeout: float
    output_node: str | None = None


def _parse_size(size: str) -> tuple[int, int]:
    parts = size.lower().split("x")
    if len(parts) != 2:
        raise ValueError(f"Invalid image size: {size}")
    return int(parts[0]), int(parts[1])


def build_comfyui_config(
    *,
    api_url: str,
    workflow_path: str,
    size: str,
    timeout: float,
    output_node: str | None,
) -> ComfyUiConfig:
    width, height = _parse_size(size)
    return ComfyUiConfig(
        api_url=api_url.rstrip("/"),
        workflow_path=workflow_path,
        width=width,
        height=height,
        timeout=timeout,
        output_node=output_node,
    )


def _render_workflow_template(path: str, values: dict[str, Any]) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    for key, value in values.items():
        token = f"{{{{{key}}}}}"
        if token not in text:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            replacement = str(value)
        else:
            replacement = json.dumps("" if value is None else str(value))
        text = text.replace(token, replacement)
    unresolved = sorted(set(_PLACEHOLDER_PATTERN.findall(text)))
    if unresolved:
        raise RuntimeError(
            "Unresolved workflow placeholders: " + ", ".join(unresolved)
        )
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Workflow JSON invalid after substitution: {exc}"
        ) from exc


def render_comfyui_workflow_template(path: str, values: dict[str, Any]) -> dict[str, Any]:
    """Public wrapper so callers can save the rendered workflow for debugging/repro."""
    return _render_workflow_template(path, values)


def _normalize_hex(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip().lower()
    if raw in _NAMED_COLORS:
        return _NAMED_COLORS[raw]
    if raw.startswith("#"):
        hex_value = raw.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) == 6:
            return f"#{hex_value}"
    return None


def _resolve_palette_hex(palette: list[str], fallback: str) -> str:
    for item in palette:
        resolved = _normalize_hex(item)
        if resolved:
            return resolved
    return fallback


def _default_font_path() -> str:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return path
    return "Arial Unicode.ttf"


def _select_image_ref(
    outputs: dict[str, Any], preferred_node: str | None
) -> dict[str, Any]:
    if preferred_node and preferred_node in outputs:
        node = outputs[preferred_node]
        if node.get("images"):
            return node["images"][0]
    for node in outputs.values():
        images = node.get("images")
        if images:
            return images[0]
    raise RuntimeError("ComfyUI returned no images in outputs")


def _download_image(
    client: httpx.Client,
    *,
    api_url: str,
    image_ref: dict[str, Any],
    output_path: str,
) -> None:
    filename = image_ref.get("filename")
    if not filename:
        raise RuntimeError("ComfyUI image reference missing filename")
    params = {
        "filename": filename,
        "subfolder": image_ref.get("subfolder", ""),
        "type": image_ref.get("type", "output"),
    }
    resp = client.get(f"{api_url}/view", params=params)
    resp.raise_for_status()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(resp.content)


def generate_comfyui_background_image(
    *,
    prompt: str,
    negative_prompt: str,
    output_path: str,
    config: ComfyUiConfig,
    seed: int = 42,
) -> ImageResult:
    """
    Generate a single image via ComfyUI using a workflow template that only depends on:
    PROMPT, NEGATIVE_PROMPT, WIDTH, HEIGHT (and optionally SEED).

    This is useful for background-only or ad-creative generation where we don't want
    flyer text/layout overlays.
    """
    values = {
        "PROMPT": prompt,
        "NEGATIVE_PROMPT": negative_prompt,
        "WIDTH": config.width,
        "HEIGHT": config.height,
        "SEED": seed,
    }
    workflow = _render_workflow_template(config.workflow_path, values)
    timeout = max(10.0, float(config.timeout))
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{config.api_url}/prompt", json={"prompt": workflow})
        resp.raise_for_status()
        data = resp.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
        deadline = time.time() + timeout
        outputs: dict[str, Any] | None = None
        while time.time() < deadline:
            hist_resp = client.get(f"{config.api_url}/history/{prompt_id}")
            if hist_resp.status_code == 200:
                history = hist_resp.json().get(prompt_id)
                if history:
                    outputs = history.get("outputs")
                    if outputs:
                        break
            time.sleep(0.5)
        if not outputs:
            raise RuntimeError("ComfyUI did not produce outputs before timeout")
        image_ref = _select_image_ref(outputs, config.output_node)
        _download_image(
            client,
            api_url=config.api_url,
            image_ref=image_ref,
            output_path=output_path,
        )
    return ImageResult(path=output_path, revised_prompt=None)


def generate_comfyui_image(
    *,
    prompt: str,
    negative_prompt: str,
    output_path: str,
    config: ComfyUiConfig,
    brief: CreativeBrief,
    style: BrandStyle,
    copy: CopyVariant,
    workflow_overrides: dict[str, Any] | None = None,
    rendered_workflow_path: str | None = None,
) -> ImageResult:
    palette_items = style.palette or brief.brand_colors or []
    palette = ", ".join(palette_items)
    style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
    constraints = "; ".join(brief.constraints or [])
    business_name = brief.business_details.name if brief.business_details else ""
    primary_hex = _resolve_palette_hex(palette_items, "#1e67b6")
    accent_hex = _resolve_palette_hex(palette_items[1:], primary_hex)
    values = {
        "PROMPT": prompt,
        "NEGATIVE_PROMPT": negative_prompt,
        "WIDTH": config.width,
        "HEIGHT": config.height,
        "FONT_PATH": _default_font_path(),
        "HEADLINE": copy.headline,
        "SUBHEAD": copy.subhead,
        "BODY": copy.body,
        "CTA": copy.cta,
        "DISCLAIMER": copy.disclaimer or "",
        "BUSINESS_BLOCK": business_block(brief),
        "AUDIENCE": brief.audience or "",
        "PALETTE": palette,
        "STYLE_KEYWORDS": style_keywords,
        "LAYOUT_GUIDANCE": style.layout_guidance or "",
        "BUSINESS_NAME": business_name,
        "PRODUCT": brief.product,
        "OFFER": brief.offer,
        "CONSTRAINTS": constraints,
        "PRIMARY_COLOR": primary_hex,
        "ACCENT_COLOR": accent_hex,
        "TEXT_DARK": "#111111",
        "TEXT_MUTED": "#333333",
        "TEXT_LIGHT": "#ffffff",
    }
    if workflow_overrides:
        # Allow workflows to accept additional knobs like CKPT_NAME, STEPS, CFG, SEED, etc.
        values.update(workflow_overrides)
    workflow = _render_workflow_template(config.workflow_path, values)
    if rendered_workflow_path:
        Path(rendered_workflow_path).parent.mkdir(parents=True, exist_ok=True)
        Path(rendered_workflow_path).write_text(json.dumps(workflow, indent=2) + "\n")
    timeout = max(10.0, float(config.timeout))
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(f"{config.api_url}/prompt", json={"prompt": workflow})
        resp.raise_for_status()
        data = resp.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError("ComfyUI did not return a prompt_id")
        deadline = time.time() + timeout
        outputs: dict[str, Any] | None = None
        while time.time() < deadline:
            hist_resp = client.get(f"{config.api_url}/history/{prompt_id}")
            if hist_resp.status_code == 200:
                history = hist_resp.json().get(prompt_id)
                if history:
                    outputs = history.get("outputs")
                    if outputs:
                        break
            time.sleep(0.5)
        if not outputs:
            raise RuntimeError("ComfyUI did not produce outputs before timeout")
        image_ref = _select_image_ref(outputs, config.output_node)
        _download_image(
            client,
            api_url=config.api_url,
            image_ref=image_ref,
            output_path=output_path,
        )
    return ImageResult(path=output_path, revised_prompt=None)
