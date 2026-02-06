from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from hyperlocal.models import CreativeAsset, CreativeRun, CreativeVariant
from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief


@dataclass
class PersistedVariant:
    id: int
    index: int


class PersistenceManager:
    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    def create_run(
        self,
        brief: CreativeBrief,
        model_versions: dict,
        status: str = "RUNNING",
    ) -> CreativeRun:
        with self._session_factory() as session:
            run = CreativeRun(
                campaign_id=brief.campaign_id,
                status=status,
                brief_json=brief.model_dump(),
                model_versions_json=model_versions,
            )
            session.add(run)
            session.commit()
            session.refresh(run)
            return run

    def update_run_style(self, run_id: int, style: BrandStyle) -> None:
        with self._session_factory() as session:
            run = session.get(CreativeRun, run_id)
            if not run:
                return
            run.brand_style_json = style.model_dump()
            session.commit()

    def update_run_status(self, run_id: int, status: str, error: str | None = None) -> None:
        with self._session_factory() as session:
            run = session.get(CreativeRun, run_id)
            if not run:
                return
            run.status = status
            run.error = error
            session.commit()

    def create_variant(
        self,
        run_id: int,
        variant_index: int,
        copy: CopyVariant,
        prompt_text: str,
        negative_prompt: str,
    ) -> PersistedVariant:
        with self._session_factory() as session:
            variant = CreativeVariant(
                run_id=run_id,
                variant_index=variant_index,
                copy_json=copy.model_dump(),
                prompt_text=prompt_text,
                negative_prompt=negative_prompt,
            )
            session.add(variant)
            session.commit()
            session.refresh(variant)
            return PersistedVariant(id=variant.id, index=variant_index)

    def update_variant_image(self, variant_id: int, image_url: str) -> None:
        with self._session_factory() as session:
            variant = session.get(CreativeVariant, variant_id)
            if not variant:
                return
            variant.image_url = image_url
            session.commit()

    def update_variant_qc(
        self,
        variant_id: int,
        qc_passed: bool,
        qc_text: str | None = None,
        qc_score: float | None = None,
    ) -> None:
        with self._session_factory() as session:
            variant = session.get(CreativeVariant, variant_id)
            if not variant:
                return
            variant.qc_passed = qc_passed
            variant.qc_text = qc_text
            variant.qc_score = qc_score
            session.commit()

    def create_asset_from_variant(
        self,
        campaign_id: int,
        run_id: int,
        variant_id: int,
        image_url: str,
        copy_text: Optional[str],
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
