from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


RunStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"]
RunStage = Literal[
    "queued",
    "starting",
    "normalizing",
    "copy_generation",
    "prompt_generation",
    "background_render",
    "overlay_render",
    "persisting",
    "completed",
    "failed",
]


class CreativeBusinessInput(BaseModel):
    name: str
    website: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    phone: str | None = None
    service_area: str | None = None


class CreativeCampaignInput(BaseModel):
    campaign_id: int | None = None
    business_kind: Literal["smoothie", "hvac"] = "smoothie"
    product: str
    offer: str
    cta: str
    audience: str | None = None
    tone: str = "clear, direct"
    constraints: list[str] = Field(default_factory=list)
    brand_colors: list[str] = Field(default_factory=list)
    style_keywords: list[str] = Field(default_factory=list)
    format_hint: Literal["ad_creative", "flyer", "poster", "flyer_poster"] = "flyer_poster"


class CreativeGenerationOptions(BaseModel):
    count: int = Field(default=2, ge=1, le=4)
    images_per_prompt: int = Field(default=2, ge=1, le=3)
    prompt_engine: Literal["llm", "template"] = "llm"
    background_provider: Literal["ollama", "sdxl", "openai", "comfyui_bg"] = "comfyui_bg"
    background_model: str | None = None


class CreativeOverlayOptions(BaseModel):
    brand_kit: str = "config/brand_kits/smoothie_default.json"
    template_mode: Literal["static", "cycle", "random"] = "cycle"
    template_name: str | None = None
    seed: int = 42
    copy_mode: Literal["auto", "provided"] = "auto"


class CreativeCopyInput(BaseModel):
    headline: str
    subhead: str = ""
    offer: str
    cta: str
    footer: str = ""


class CreativeOutputOptions(BaseModel):
    subdir: str | None = None


class CreativeRunRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    business: CreativeBusinessInput
    campaign: CreativeCampaignInput
    generation: CreativeGenerationOptions = Field(default_factory=CreativeGenerationOptions)
    overlay: CreativeOverlayOptions = Field(default_factory=CreativeOverlayOptions)
    copy_input: CreativeCopyInput | None = Field(default=None, alias="copy")
    output: CreativeOutputOptions = Field(default_factory=CreativeOutputOptions)

    @field_validator("copy_input")
    @classmethod
    def validate_copy_mode(cls, value: CreativeCopyInput | None, info):
        overlay = info.data.get("overlay")
        if overlay and overlay.copy_mode == "provided" and value is None:
            raise ValueError("copy must be provided when overlay.copy_mode=provided")
        return value


class CreativeArtifact(BaseModel):
    variant_index: int
    prompt_slug: str
    background_image_url: str
    final_image_url: str
    overlay_template: str


class CreativeRunCreateResponse(BaseModel):
    run_id: int
    status: RunStatus
    stage: str
    progress_pct: int


class CreativeRunStatusResponse(BaseModel):
    run_id: int
    status: RunStatus
    stage: str
    progress_pct: int
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    output_dir: str | None = None
    manifest_url: str | None = None
    artifacts: list[CreativeArtifact] = Field(default_factory=list)


class CreativeRunFilesResponse(BaseModel):
    run_id: int
    files: list[str] = Field(default_factory=list)


class CreativeRunResult(BaseModel):
    run_id: int
    output_dir: str
    manifest_path: str
    artifacts: list[CreativeArtifact]
    request: dict[str, Any]
