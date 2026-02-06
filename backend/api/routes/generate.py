from __future__ import annotations

from fastapi import APIRouter, HTTPException

from hyperlocal.pipeline import FlyerPipeline
from hyperlocal.schemas import CreativeBrief

router = APIRouter(prefix="/api")


@router.post("/generate")
def generate(brief: CreativeBrief) -> dict:
    try:
        pipeline = FlyerPipeline()
        result = pipeline.run(brief)
        return result.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
