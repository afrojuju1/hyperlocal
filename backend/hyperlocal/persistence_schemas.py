from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


class CreativeRunCreate(BaseModel):
    campaign_id: Optional[int] = None
    status: str = "RUNNING"
    brief_json: dict[str, Any]
    model_versions_json: dict[str, Any]


class CreativeRunRead(CreativeRunCreate):
    id: int
    brand_style_json: dict[str, Any] = {}
    error: Optional[str] = None


class CreativeVariantCreate(BaseModel):
    run_id: int
    variant_index: int
    copy_json: dict[str, Any]
    prompt_text: str
    negative_prompt: str


class CreativeVariantRead(CreativeVariantCreate):
    id: int
    image_url: Optional[str] = None
    qc_passed: bool = False
    qc_text: Optional[str] = None
    qc_score: Optional[float] = None


class CreativeAssetCreate(BaseModel):
    campaign_id: int
    run_id: Optional[int] = None
    variant_id: Optional[int] = None
    image_path: str
    copy_text: Optional[str] = None


class CreativeAssetRead(CreativeAssetCreate):
    id: int
