from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def _config_path() -> Path:
    app_root = Path(__file__).resolve().parents[3]
    return app_root / "config" / "verticals" / "defaults.json"


@lru_cache(maxsize=1)
def load_vertical_configs() -> dict[str, dict[str, Any]]:
    data = json.loads(_config_path().read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("vertical config must be a JSON object")
    return {str(key): value for key, value in data.items() if isinstance(value, dict)}


def get_vertical_config(business_kind: str) -> dict[str, Any]:
    configs = load_vertical_configs()
    try:
        return configs[business_kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported business_kind: {business_kind}") from exc


def vertical_mode_list(
    business_kind: str,
    field: str,
    text_mode: str,
) -> list[str]:
    raw = get_vertical_config(business_kind).get(field, {})
    if not isinstance(raw, dict):
        return []
    values = raw.get(text_mode) or raw.get("overlay") or []
    if not isinstance(values, list):
        return []
    return [str(item) for item in values if str(item).strip()]


def vertical_mode_text(
    business_kind: str,
    field: str,
    text_mode: str,
) -> str:
    raw = get_vertical_config(business_kind).get(field, {})
    if not isinstance(raw, dict):
        return ""
    return str(raw.get(text_mode) or raw.get("overlay") or "").strip()


def vertical_items(
    business_kind: str,
    field: str,
) -> list[tuple[str, str, str]]:
    raw = get_vertical_config(business_kind).get(field, [])
    if not isinstance(raw, list):
        return []
    items: list[tuple[str, str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        slug = str(item.get("slug") or "").strip()
        title = str(item.get("title") or "").strip()
        prompt = str(item.get("prompt") or "").strip()
        if slug and title and prompt:
            items.append((slug, title, prompt))
    return items


def vertical_strings(business_kind: str, field: str) -> list[str]:
    raw = get_vertical_config(business_kind).get(field, [])
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def vertical_layout_defaults(business_kind: str) -> dict[str, str]:
    raw = get_vertical_config(business_kind).get("layout", {})
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items() if str(value).strip()}


def vertical_qc_config(business_kind: str) -> dict[str, Any]:
    raw = get_vertical_config(business_kind).get("qc", {})
    if not isinstance(raw, dict):
        return {}
    return raw
