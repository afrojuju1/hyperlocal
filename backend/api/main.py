from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Hyperlocal API")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
