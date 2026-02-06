from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class BusinessDayHours(BaseModel):
    day: str
    open: Optional[str] = None
    close: Optional[str] = None
    closed: bool = False


class BusinessHours(BaseModel):
    timezone: Optional[str] = None
    weekly: List[BusinessDayHours] = Field(default_factory=list)
    notes: Optional[str] = None
    display: Optional[str] = None


class BusinessDetails(BaseModel):
    name: str
    website: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    phone: Optional[str] = None
    hours: Optional[BusinessHours] = None
    service_area: Optional[str] = None


class CreativeBrief(BaseModel):
    campaign_id: Optional[int] = None
    business_details: BusinessDetails
    product: str
    offer: str
    tone: str
    cta: str
    size: str = Field(default="6x9", description="Flyer size, e.g. 6x9")
    audience: Optional[str] = None
    constraints: List[str] = Field(default_factory=list)
    brand_colors: List[str] = Field(default_factory=list)
    style_keywords: List[str] = Field(default_factory=list)
    reference_images: List[str] = Field(default_factory=list, description="Local file paths")


class BrandStyle(BaseModel):
    palette: List[str] = Field(default_factory=list)
    style_keywords: List[str] = Field(default_factory=list)
    layout_guidance: str = ""
    typography_guidance: str = ""


class CopyVariant(BaseModel):
    headline: str
    subhead: str
    body: str
    cta: str
    disclaimer: Optional[str] = None


class PromptPackage(BaseModel):
    image_prompt: str
    negative_prompt: str
    copy_variant: CopyVariant


class ImageVariant(BaseModel):
    index: int
    prompt: PromptPackage
    image_path: str
    qc_passed: bool
    qc_text: Optional[str] = None


class RunResult(BaseModel):
    brief: CreativeBrief
    brand_style: BrandStyle
    variants: List[ImageVariant]
    output_dir: str
