from __future__ import annotations

from fastapi import APIRouter, HTTPException

from hyperlocal.contracts.creative_runs import (
    CreativeBusinessInput,
    CreativeCampaignInput,
    CreativeGenerationOptions,
    CreativeOutputOptions,
    CreativeOverlayOptions,
    CreativeRunRequest,
)
from hyperlocal.db import build_sessionmaker, init_db
from hyperlocal.persistence import PersistenceManager
from hyperlocal.pipelines.creative_runs import CreativeRunPipeline
from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.schemas import CreativeBrief

router = APIRouter(prefix="/api")


def _manager() -> PersistenceManager:
    if not RUNTIME_CONFIG.database_url:
        raise RuntimeError("DATABASE_URL is required for /api/generate compatibility shim")
    init_db(RUNTIME_CONFIG.database_url)
    return PersistenceManager(build_sessionmaker(RUNTIME_CONFIG.database_url))


def _infer_business_kind(brief: CreativeBrief) -> str:
    text = f"{brief.product} {brief.offer}".lower()
    if any(token in text for token in ["hvac", "ac", "tune-up", "air"]):
        return "hvac"
    return "smoothie"


def _to_creative_run_request(brief: CreativeBrief) -> CreativeRunRequest:
    details = brief.business_details
    provider = (RUNTIME_CONFIG.image_provider or "ollama").lower().replace("-", "_")
    if provider == "comfyui":
        provider = "comfyui_bg"
    if provider not in {"ollama", "sdxl", "openai", "comfyui_bg"}:
        provider = "ollama"
    background_model = (
        RUNTIME_CONFIG.ollama_image_model
        if provider == "ollama"
        else RUNTIME_CONFIG.image_model
    )
    return CreativeRunRequest(
        business=CreativeBusinessInput(
            name=details.name,
            website=details.website,
            address=details.address,
            city=details.city,
            state=details.state,
            postal_code=details.postal_code,
            phone=details.phone,
            service_area=details.service_area,
        ),
        campaign=CreativeCampaignInput(
            campaign_id=brief.campaign_id,
            business_kind=_infer_business_kind(brief),
            product=brief.product,
            offer=brief.offer,
            cta=brief.cta,
            audience=brief.audience,
            tone=brief.tone,
            constraints=brief.constraints,
            brand_colors=brief.brand_colors,
            style_keywords=brief.style_keywords,
            format_hint="flyer_poster",
        ),
        generation=CreativeGenerationOptions(
            count=max(1, min(4, RUNTIME_CONFIG.variants)),
            images_per_prompt=1,
            prompt_engine="llm",
            background_provider=provider,
            background_model=background_model,
        ),
        overlay=CreativeOverlayOptions(
            brand_kit="config/brand_kits/hvac_default.json"
            if _infer_business_kind(brief) == "hvac"
            else "config/brand_kits/smoothie_default.json",
            template_mode="cycle",
            seed=42,
            copy_mode="auto",
        ),
        output=CreativeOutputOptions(subdir="creative_runs"),
    )


@router.post("/generate")
def generate(brief: CreativeBrief) -> dict:
    manager: PersistenceManager | None = None
    run_id: int | None = None
    try:
        manager = _manager()
        request = _to_creative_run_request(brief)

        run = manager.create_run_request(
            request_payload=request.model_dump(by_alias=True),
            campaign_id=request.campaign.campaign_id,
            status="RUNNING",
            stage="starting",
            pipeline_version="v1",
        )
        run_id = run.id

        pipeline = CreativeRunPipeline(manager)
        result = pipeline.execute(run.id, request)

        return {
            "output_dir": result.output_dir,
            "variants": [
                {
                    "index": item.variant_index,
                    "image_path": item.final_image_url,
                    "qc_passed": True,
                    "qc_text": "compatibility shim",
                }
                for item in result.artifacts
            ],
        }
    except Exception as exc:
        if manager is not None and run_id is not None:
            try:
                manager.mark_run_failed(run_id, error=str(exc), stage="failed")
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(exc))
