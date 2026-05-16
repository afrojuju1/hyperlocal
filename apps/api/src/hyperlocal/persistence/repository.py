from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from hyperlocal.persistence.models import CreativeAsset, CreativeRun, CreativeVariant
from hyperlocal.creative.schemas import CopyVariant


@dataclass
class PersistedVariant:
    id: int
    index: int


class PersistenceManager:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def create_run_request(
        self,
        *,
        request_payload: dict,
        campaign_id: int | None,
        status: str = "QUEUED",
        stage: str = "queued",
        pipeline_version: str = "v1",
    ) -> CreativeRun:
        with self._session_factory() as session:
            run = CreativeRun(
                campaign_id=campaign_id,
                status=status,
                stage=stage,
                progress_pct=0,
                request_json=request_payload,
                pipeline_version=pipeline_version,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def claim_next_queued_run(self) -> CreativeRun | None:
        with self._session_factory() as session:
            with session.begin():
                run = (
                    session.execute(
                        select(CreativeRun)
                        .where(CreativeRun.status == "QUEUED")
                        .order_by(CreativeRun.created_at.asc(), CreativeRun.id.asc())
                        .with_for_update(skip_locked=True)
                        .limit(1)
                    )
                    .scalars()
                    .first()
                )
                if run is None:
                    return None
                run.status = "RUNNING"
                run.stage = "starting"
                run.progress_pct = max(run.progress_pct or 0, 1)
                run.started_at = run.started_at or datetime.now(timezone.utc)
                run.updated_at = datetime.now(timezone.utc)

            session.refresh(run)
            return run

    def get_run(self, run_id: int) -> CreativeRun | None:
        with self._session_factory() as session:
            return session.get(CreativeRun, run_id)

    def get_variants(self, run_id: int) -> list[CreativeVariant]:
        with self._session_factory() as session:
            rows = (
                session.execute(
                    select(CreativeVariant)
                    .where(CreativeVariant.run_id == run_id)
                    .order_by(CreativeVariant.variant_index.asc())
                )
                .scalars()
                .all()
            )
            return list(rows)

    def update_run_progress(
        self,
        run_id: int,
        *,
        stage: str,
        progress_pct: int | None = None,
        output_dir: str | None = None,
        pipeline_version: str | None = None,
        error: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            run = session.get(CreativeRun, run_id)
            if not run:
                return
            run.stage = stage
            if progress_pct is not None:
                run.progress_pct = max(0, min(100, int(progress_pct)))
            if output_dir is not None:
                run.output_dir = output_dir
            if pipeline_version is not None:
                run.pipeline_version = pipeline_version
            if error is not None:
                run.error = error
            run.updated_at = datetime.now(timezone.utc)
            session.commit()

    def mark_run_succeeded(
        self,
        run_id: int,
        *,
        output_dir: str,
        stage: str = "completed",
        progress_pct: int = 100,
        manifest_path: str | None = None,
    ) -> None:
        with self._session_factory() as session:
            run = session.get(CreativeRun, run_id)
            if not run:
                return
            run.status = "SUCCEEDED"
            run.stage = stage
            run.progress_pct = max(0, min(100, int(progress_pct)))
            run.output_dir = output_dir
            if manifest_path is not None:
                run.manifest_path = manifest_path
            run.finished_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            session.commit()

    def mark_run_failed(
        self,
        run_id: int,
        *,
        error: str,
        stage: str = "failed",
    ) -> None:
        with self._session_factory() as session:
            run = session.get(CreativeRun, run_id)
            if not run:
                return
            run.status = "FAILED"
            run.stage = stage
            run.error = error
            run.finished_at = datetime.now(timezone.utc)
            run.updated_at = datetime.now(timezone.utc)
            session.commit()

    def create_or_update_variant(
        self,
        *,
        run_id: int,
        variant_index: int,
        copy: CopyVariant,
        prompt_text: str,
        negative_prompt: str,
        background_image_url: str | None = None,
        qc_summary: dict[str, Any] | None = None,
    ) -> PersistedVariant:
        qc_text = json.dumps(qc_summary, sort_keys=True) if qc_summary is not None else None
        qc_passed = bool(qc_summary.get("passed")) if qc_summary else False
        qc_score = _coerce_optional_float(qc_summary.get("score")) if qc_summary else None
        with self._session_factory() as session:
            variant = (
                session.execute(
                    select(CreativeVariant).where(
                        CreativeVariant.run_id == run_id,
                        CreativeVariant.variant_index == variant_index,
                    )
                )
                .scalars()
                .first()
            )
            if variant is None:
                variant = CreativeVariant(
                    run_id=run_id,
                    variant_index=variant_index,
                    copy_json=copy.model_dump(),
                    prompt_text=prompt_text,
                    negative_prompt=negative_prompt,
                    background_image_url=background_image_url,
                    qc_passed=qc_passed,
                    qc_text=qc_text,
                    qc_score=qc_score,
                )
                session.add(variant)
            else:
                variant.copy_json = copy.model_dump()
                variant.prompt_text = prompt_text
                variant.negative_prompt = negative_prompt
                if background_image_url is not None:
                    variant.background_image_url = background_image_url
                if qc_summary is not None:
                    variant.qc_passed = qc_passed
                    variant.qc_text = qc_text
                    variant.qc_score = qc_score
            session.commit()
            session.refresh(variant)
            return PersistedVariant(id=variant.id, index=variant_index)

    def update_variant_render(
        self,
        *,
        run_id: int,
        variant_index: int,
        final_image_url: str,
        overlay_template: str,
    ) -> None:
        with self._session_factory() as session:
            variant = (
                session.execute(
                    select(CreativeVariant).where(
                        CreativeVariant.run_id == run_id,
                        CreativeVariant.variant_index == variant_index,
                    )
                )
                .scalars()
                .first()
            )
            if not variant:
                return
            variant.final_image_url = final_image_url
            variant.overlay_template = overlay_template
            session.commit()

    def create_asset_from_variant(
        self,
        campaign_id: int,
        run_id: int,
        variant_id: int,
        image_url: str,
        copy_text: str | None,
    ) -> CreativeAsset:
        with self._session_factory() as session:
            asset = CreativeAsset(
                campaign_id=campaign_id,
                run_id=run_id,
                variant_id=variant_id,
                image_path=image_url,
                copy_text=copy_text,
            )
            session.add(asset)
            session.commit()
            session.refresh(asset)
            return asset


def _coerce_optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
