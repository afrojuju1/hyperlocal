from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.llm_providers import resolve_llm_base_url


@dataclass
class HealthCheck:
    name: str
    ok: bool
    detail: str


def _check_llm_url(name: str, base_url: str) -> HealthCheck:
    url = base_url.rstrip("/") + "/models"
    try:
        resp = httpx.get(url, timeout=2.5)
        resp.raise_for_status()
        detail = f\"ok ({RUNTIME_CONFIG.llm_provider})\"
        return HealthCheck(name, True, detail)
    except Exception as exc:
        detail = f\"error ({RUNTIME_CONFIG.llm_provider}): {exc}\"
        return HealthCheck(name, False, detail)


def _check_llm() -> list[HealthCheck]:
    text_base = resolve_llm_base_url(\"text\").rstrip(\"/\")
    vision_base = resolve_llm_base_url(\"vision\").rstrip(\"/\")
    unique = {text_base, vision_base}
    if len(unique) == 1:
        base_url = unique.pop()
        return [_check_llm_url(\"llm\", base_url)]
    return [
        _check_llm_url(\"llm_text\", text_base),
        _check_llm_url(\"llm_vision\", vision_base),
    ]


def _check_sdxl() -> HealthCheck:
    base = RUNTIME_CONFIG.sdxl_api_url
    if "/sdapi/v1/" in base:
        base = base.split("/sdapi/v1/")[0]
    url = base.rstrip("/") + "/sdapi/v1/options"
    try:
        resp = httpx.get(url, timeout=2.5)
        resp.raise_for_status()
        return HealthCheck("sdxl", True, "ok")
    except Exception as exc:
        return HealthCheck("sdxl", False, f"error: {exc}")


def _check_comfyui() -> HealthCheck:
    base = RUNTIME_CONFIG.comfyui_api_url.rstrip("/")
    url = base + "/system_stats"
    try:
        resp = httpx.get(url, timeout=2.5)
        resp.raise_for_status()
        return HealthCheck("comfyui", True, "ok")
    except Exception as exc:
        return HealthCheck("comfyui", False, f"error: {exc}")


def run_health_checks() -> dict[str, Any]:
    checks: list[HealthCheck] = [*_check_llm()]
    provider = RUNTIME_CONFIG.image_provider.lower()
    if provider == "sdxl":
        checks.append(_check_sdxl())
    elif provider == "comfyui":
        checks.append(_check_comfyui())
    overall = all(check.ok for check in checks)
    return {
        "ok": overall,
        "checks": {check.name: {"ok": check.ok, "detail": check.detail} for check in checks},
    }
