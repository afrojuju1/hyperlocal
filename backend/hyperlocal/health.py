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
        detail = f"ok ({RUNTIME_CONFIG.llm_provider})"
        return HealthCheck(name, True, detail)
    except Exception as exc:
        detail = f"error ({RUNTIME_CONFIG.llm_provider}): {exc}"
        return HealthCheck(name, False, detail)


def _check_llm() -> list[HealthCheck]:
    return [_check_llm_url("llm", resolve_llm_base_url().rstrip("/"))]


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
    if provider in {"comfyui", "comfyui_bg"}:
        checks.append(_check_comfyui())
    overall = all(check.ok for check in checks)
    return {
        "ok": overall,
        "checks": {check.name: {"ok": check.ok, "detail": check.detail} for check in checks},
    }
