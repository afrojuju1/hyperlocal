from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from hyperlocal.core.config import RUNTIME_CONFIG
from hyperlocal.creative.contracts import (
    CreativeArtifact,
    CreativeCopyInput,
    CreativeRunRequest,
    CreativeRunResult,
)
from hyperlocal.persistence.repository import PersistenceManager
from hyperlocal.creative.copy_generation import CopyGenerationService
from hyperlocal.creative.image_generation import ImageGenerationService
from hyperlocal.creative.layout_rendering import LayoutRenderingService
from hyperlocal.creative.overlay_rendering import OverlayRenderingService


class CreativeRunPipeline:
    PIPELINE_VERSION = "v1"

    def __init__(self, persistence: PersistenceManager) -> None:
        self._persistence = persistence
        self._copy_generation = CopyGenerationService()
        self._image_generation = ImageGenerationService()
        self._layout_rendering = LayoutRenderingService()
        self._overlay_rendering = OverlayRenderingService()

    def execute(self, run_id: int, request: CreativeRunRequest) -> CreativeRunResult:
        run_dir = Path(RUNTIME_CONFIG.output_dir) / "creative_runs" / str(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "manifest.json"

        self._persistence.update_run_progress(
            run_id,
            stage="normalizing",
            progress_pct=5,
            output_dir=str(run_dir),
            pipeline_version=self.PIPELINE_VERSION,
        )

        normalized = self._normalize_request(request)

        if normalized.generation.creative_mode == "full_ad":
            copy_blocks = self._full_ad_copy_blocks(normalized)
        else:
            self._persistence.update_run_progress(run_id, stage="copy_generation", progress_pct=20)
            copy_blocks = self._copy_generation.generate(normalized, normalized.generation.count)

        self._persistence.update_run_progress(run_id, stage="prompt_generation", progress_pct=30)
        self._persistence.update_run_progress(run_id, stage="image_render", progress_pct=45)
        generated_images = self._image_generation.generate(request=normalized, run_dir=run_dir)

        for generated in generated_images:
            copy_block = copy_blocks[(generated.prompt_index - 1) % len(copy_blocks)]
            self._persistence.create_or_update_variant(
                run_id=run_id,
                variant_index=generated.variant_index,
                copy=copy_block,
                prompt_text=generated.prompt,
                negative_prompt=generated.negative_prompt,
                background_image_url=generated.image_path,
            )

        artifacts: list[CreativeArtifact] = []
        layout_plans: list[dict] = []
        if normalized.generation.creative_mode == "full_ad":
            self._persistence.update_run_progress(run_id, stage="typography_render", progress_pct=75)
            typography = self._layout_rendering.render(
                request=normalized,
                run_dir=run_dir,
                source_images=generated_images,
                copies=copy_blocks,
            )
            layout_plans = [rendered.layout_plan for rendered in typography]
            rendered_variants = [
                CreativeArtifact(
                    variant_index=rendered.variant_index,
                    prompt_slug=rendered.prompt_slug,
                    background_image_url=rendered.background_image_url,
                    final_image_url=rendered.final_image_url,
                    overlay_template=rendered.overlay_template,
                )
                for rendered in typography
            ]
        else:
            self._persistence.update_run_progress(run_id, stage="overlay_render", progress_pct=75)
            overlays = self._overlay_rendering.render(
                request=normalized,
                run_dir=run_dir,
                source_images=generated_images,
                copies=copy_blocks,
            )
            rendered_variants = [
                CreativeArtifact(
                    variant_index=rendered.variant_index,
                    prompt_slug=rendered.prompt_slug,
                    background_image_url=rendered.background_image_url,
                    final_image_url=rendered.final_image_url,
                    overlay_template=rendered.overlay_template,
                )
                for rendered in overlays
            ]

        for artifact in rendered_variants:
            self._persistence.update_variant_render(
                run_id=run_id,
                variant_index=artifact.variant_index,
                final_image_url=artifact.final_image_url,
                overlay_template=artifact.overlay_template,
            )
            artifacts.append(artifact)

        self._persistence.update_run_progress(run_id, stage="persisting", progress_pct=92)

        manifest = {
            "created_at": datetime.now().isoformat(),
            "run_id": run_id,
            "pipeline_version": self.PIPELINE_VERSION,
            "request": normalized.model_dump(by_alias=True),
            "runtime": self._image_generation.runtime_meta(normalized),
            "copy_blocks": [copy.model_dump() for copy in copy_blocks],
            "generated_images": [asdict(generated) for generated in generated_images],
            "layout_plans": layout_plans,
            "artifacts": [artifact.model_dump() for artifact in artifacts],
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

        self._persistence.mark_run_succeeded(
            run_id,
            output_dir=str(run_dir),
            stage="completed",
            progress_pct=100,
            manifest_path=str(manifest_path),
        )

        return CreativeRunResult(
            run_id=run_id,
            output_dir=str(run_dir),
            manifest_path=str(manifest_path),
            artifacts=artifacts,
            request=normalized.model_dump(by_alias=True),
        )

    def _normalize_request(self, request: CreativeRunRequest) -> CreativeRunRequest:
        overlay = request.overlay.model_copy()
        if request.campaign.business_kind == "hvac" and overlay.brand_kit == "config/brand_kits/smoothie_default.json":
            overlay.brand_kit = "config/brand_kits/hvac_default.json"

        campaign = request.campaign.model_copy()
        campaign.constraints = [item.strip() for item in campaign.constraints if item.strip()]
        campaign.brand_colors = [item.strip() for item in campaign.brand_colors if item.strip()]
        campaign.style_keywords = [item.strip() for item in campaign.style_keywords if item.strip()]

        copy: CreativeCopyInput | None = request.copy_input
        if overlay.copy_mode == "provided" and copy is None:
            copy = CreativeCopyInput(
                headline=request.business.name,
                subhead=request.campaign.product,
                offer=request.campaign.offer,
                cta=request.campaign.cta,
                footer="Limited time",
            )

        output = request.output.model_copy()
        if not output.subdir:
            output.subdir = "creative_runs"

        return CreativeRunRequest(
            business=request.business,
            campaign=campaign,
            generation=request.generation,
            overlay=overlay,
            copy_input=copy,
            output=output,
        )

    def _full_ad_copy_blocks(self, request: CreativeRunRequest) -> list[CreativeCopyInput]:
        block = CreativeCopyInput(
            headline=request.business.name,
            subhead=request.campaign.product,
            offer=request.campaign.offer,
            cta="",
            footer="",
        )
        return [block for _ in range(request.generation.count)]
