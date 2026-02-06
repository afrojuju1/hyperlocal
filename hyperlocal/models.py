from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class CreativeRun(Base):
    __tablename__ = "creative_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="RUNNING")
    brief_json: Mapped[dict] = mapped_column(JSON, default=dict)
    brand_style_json: Mapped[dict] = mapped_column(JSON, default=dict)
    model_versions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    variants: Mapped[list["CreativeVariant"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class CreativeVariant(Base):
    __tablename__ = "creative_variants"
    __table_args__ = (
        UniqueConstraint("run_id", "variant_index", name="uq_run_variant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("creative_runs.id"), index=True)
    variant_index: Mapped[int] = mapped_column(Integer)

    copy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_text: Mapped[str] = mapped_column(Text)
    negative_prompt: Mapped[str] = mapped_column(Text)
    image_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    qc_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    qc_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qc_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    run: Mapped[CreativeRun] = relationship(back_populates="variants")


class CreativeAsset(Base):
    __tablename__ = "creative_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(Integer, index=True)
    run_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    variant_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    image_path: Mapped[str] = mapped_column(Text)
    copy_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
