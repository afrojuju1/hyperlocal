from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from api.routes.generate import router as generate_router

app = FastAPI(title="Hyperlocal API")

output_dir = Path("output")
output_dir.mkdir(parents=True, exist_ok=True)

allowed_origins = [
    origin.strip()
    for origin in os.getenv("HYPERLOCAL_CORS_ORIGINS", "http://localhost:13000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(generate_router)

app.mount("/files", StaticFiles(directory=output_dir), name="files")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
