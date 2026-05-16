from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


RunStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELED"]
RunStage = Literal[
    "queued",
    "starting",
    "normalizing",
    "copy_generation",
    "prompt_generation",
    "image_render",
    "background_render",
    "typography_render",
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
    business_kind: Literal["smoothie", "hvac", "real_estate"] = "smoothie"
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
    creative_mode: Literal["full_ad", "background_overlay"] = "full_ad"
    image_provider: Literal["ollama", "openai", "comfyui_bg"] = "comfyui_bg"
    image_model: str | None = None
    # Backward-compatible request fields. Prefer creative_mode/image_provider/image_model.
    background_provider: Literal["ollama", "openai", "comfyui_bg"] | None = None
    background_model: str | None = None
    # Backward-compatible input. API creative runs now render exact typography after
    # text-free image generation, so normalized requests use overlay mode.
    text_mode: Literal["in_image", "overlay"] | None = None

    @model_validator(mode="after")
    def normalize_generation_aliases(self):
        fields_set = self.model_fields_set
        if (
            "background_provider" in fields_set
            and "image_provider" not in fields_set
            and self.background_provider is not None
        ):
            self.image_provider = self.background_provider
        self.background_provider = self.image_provider

        if (
            "background_model" in fields_set
            and "image_model" not in fields_set
            and self.background_model is not None
        ):
            self.image_model = self.background_model
        self.background_model = self.image_model

        if (
            "text_mode" in fields_set
            and "creative_mode" not in fields_set
            and self.text_mode is not None
        ):
            self.creative_mode = "full_ad" if self.text_mode == "in_image" else "background_overlay"
        self.text_mode = "overlay"

        return self


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
    qc_enabled: bool = False
    qc_passed: bool | None = None
    qc_score: float | None = None
    qc_attempts: int = 1
    qc_retries_exhausted: bool = False
    qc_reasons: list[str] = Field(default_factory=list)
    qc_report_url: str | None = None


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
