from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from hyperlocal.core.config import RUNTIME_CONFIG
from hyperlocal.creative.contracts import (
    CreativeArtifact,
    CreativeRunCreateResponse,
    CreativeRunFilesResponse,
    CreativeRunRequest,
    CreativeRunStatusResponse,
)
from hyperlocal.persistence.db import build_sessionmaker, init_db
from hyperlocal.persistence.repository import PersistenceManager

router = APIRouter(prefix="/api/v1", tags=["creative-runs"])


@lru_cache(maxsize=1)
def _manager() -> PersistenceManager:
    if not RUNTIME_CONFIG.database_url:
        raise RuntimeError("DATABASE_URL is not configured")
    init_db(RUNTIME_CONFIG.database_url)
    return PersistenceManager(build_sessionmaker(RUNTIME_CONFIG.database_url))


def _files_url_from_path(path: str | None) -> str | None:
    if not path:
        return None
    p = Path(path)
    as_posix = p.as_posix()
    marker = "/output/"
    if marker in as_posix:
        rel = as_posix.split(marker, 1)[1]
        return f"/files/{rel}"
    if as_posix.startswith("output/"):
        return f"/files/{as_posix[len('output/') :]}"
    return f"/files/{as_posix}"


@router.post("/creative-runs", response_model=CreativeRunCreateResponse)
def create_creative_run(request: CreativeRunRequest) -> CreativeRunCreateResponse:
    try:
        manager = _manager()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    run = manager.create_run_request(
        request_payload=request.model_dump(by_alias=True),
        campaign_id=request.campaign.campaign_id,
        status="QUEUED",
        stage="queued",
        pipeline_version="v1",
    )
    return CreativeRunCreateResponse(
        run_id=run.id,
        status=run.status,
        stage=run.stage,
        progress_pct=run.progress_pct,
    )


@router.get("/creative-runs/{run_id}", response_model=CreativeRunStatusResponse)
def get_creative_run_status(run_id: int) -> CreativeRunStatusResponse:
    try:
        manager = _manager()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    run = manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    variants = manager.get_variants(run_id)
    artifacts: list[CreativeArtifact] = []
    for variant in variants:
        if not variant.final_image_url:
            continue
        artifacts.append(
            CreativeArtifact(
                variant_index=variant.variant_index,
                prompt_slug=f"variant_{variant.variant_index:03d}",
                background_image_url=variant.background_image_url or "",
                final_image_url=variant.final_image_url,
                overlay_template=variant.overlay_template or "base",
                **_artifact_qc_fields(variant.qc_text),
            )
        )

    return CreativeRunStatusResponse(
        run_id=run.id,
        status=run.status,
        stage=run.stage,
        progress_pct=run.progress_pct,
        created_at=run.created_at,
        started_at=run.started_at,
        finished_at=run.finished_at,
        error=run.error,
        output_dir=run.output_dir,
        manifest_url=_files_url_from_path(run.manifest_path),
        artifacts=artifacts,
    )


@router.get("/creative-runs/{run_id}/files", response_model=CreativeRunFilesResponse)
def get_creative_run_files(run_id: int) -> CreativeRunFilesResponse:
    try:
        manager = _manager()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    run = manager.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    if not run.output_dir:
        return CreativeRunFilesResponse(run_id=run_id, files=[])

    root = Path(run.output_dir)
    if not root.exists() or not root.is_dir():
        return CreativeRunFilesResponse(run_id=run_id, files=[])

    files = [
        str(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    ]
    return CreativeRunFilesResponse(run_id=run_id, files=files)


def _artifact_qc_fields(raw_qc: str | None) -> dict[str, Any]:
    if not raw_qc:
        return {}
    try:
        qc = json.loads(raw_qc)
    except json.JSONDecodeError:
        return {"qc_enabled": True, "qc_reasons": [raw_qc]}
    if not isinstance(qc, dict):
        return {}
    return {
        "qc_enabled": bool(qc.get("enabled")),
        "qc_passed": qc.get("passed"),
        "qc_score": _coerce_optional_float(qc.get("score")),
        "qc_attempts": int(qc.get("attempts") or 1),
        "qc_retries_exhausted": bool(qc.get("retries_exhausted")),
        "qc_reasons": list(qc.get("reasons") or []),
        "qc_report_url": _files_url_from_path(qc.get("report_path")),
    }


def _coerce_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
