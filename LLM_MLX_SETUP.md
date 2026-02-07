# vLLM-MLX + SDXL Integration Notes (2026-02-07)

This document summarizes the work completed to switch Hyperlocal to a local vLLM-MLX inference stack, stabilize the pipeline, and get flyer generation running end-to-end.

## High-level Outcome
- Local LLM inference now runs via **vLLM-MLX (OpenAI-compatible)** on the host.
- Image generation runs via **local SDXL** (HF model `stabilityai/sdxl-turbo`).
- The pipeline can successfully generate flyers end-to-end (with QC disabled) on this machine.

---

## Key Architecture Changes

### 1) LLM Provider Abstraction
- Added a dedicated LLM provider layer that supports **vLLM-MLX** and **Ollama**.
- The pipeline now uses distinct **text** and **vision** clients.

New file:
- `backend/hyperlocal/llm_providers.py`

Updated files:
- `backend/hyperlocal/config.py`
- `backend/hyperlocal/pipeline.py`
- `backend/hyperlocal/health.py`

New env vars:
- `HYPERLOCAL_LLM_PROVIDER`
- `HYPERLOCAL_LLM_BASE_URL`
- `HYPERLOCAL_LLM_API_KEY`
- `HYPERLOCAL_TEXT_BASE_URL`
- `HYPERLOCAL_VISION_BASE_URL`

Defaults for vLLM-MLX:
- Models default to `default` when provider is `vllm_mlx`.

---

### 2) vLLM-MLX Server Runner
- Replaced the old MLX server runner with a **vLLM-MLX** runner.
- Supports **text + vision** servers on separate ports.
- Enables HF transfer by default.

File:
- `mlx/run_mlx_servers.sh`

---

### 3) SDXL Model Source
- Switched SDXL to **Hugging Face model** `stabilityai/sdxl-turbo` in docker-compose.
- Previous Civitai file was corrupt/unreliable.

File:
- `docker-compose.yml`

---

### 4) Faster HF Downloads
- Added **hf_transfer** to SDXL dependencies.
- Enabled `HF_HUB_ENABLE_HF_TRANSFER=1` for SDXL container.
- Added a Python Civitai downloader (resume + progress) to replace bash.

Files:
- `sdxl/pyproject.toml`
- `sdxl/uv.lock`
- `sdxl/fetch_civitai_model.py`
- `sdxl/fetch_civitai_model.sh`

---

### 5) Typst Rendering Fix
- Fixed Typst template to comply with Typst function syntax.
- Ensured `#align(top)[ ... ]` has valid body.
- Fixed `#text(...)` calls to use argument order expected by Typst.

File:
- `backend/hyperlocal/typst_renderer.py`

---

## Working Run (Confirmed)
A fast settings run completed end-to-end:

```bash
HYPERLOCAL_QC_ENABLED=0 \
SDXL_API_URL=http://localhost:17860/sdapi/v1/txt2img \
SDXL_STEPS=2 \
SDXL_CFG_SCALE=0 \
HYPERLOCAL_IMAGE_SIZE=512x512 \
uv run backend/scripts/generate_flyer.py
```

Output generated:
- `output/flyer_runs/20260207_063903/variant_01.png`
- `output/flyer_runs/20260207_064012/variant_01.png`
- `output/flyer_runs/20260207_064102/variant_01.png`

---

## Known Issues / Tradeoffs
- **Image quality is still poor** (fast settings and SDXL Turbo on CPU).
- SDXL on CPU is slow for higher quality settings.
- HF downloads are large; token + `hf_transfer` helps but still heavy.

---

## Current Recommended Setup

Start vLLM-MLX locally:
```bash
mlx/run_mlx_servers.sh
```

Run the stack:
```bash
docker compose up -d
```

Run flyer generation:
```bash
HYPERLOCAL_QC_ENABLED=0 uv run backend/scripts/generate_flyer.py
```

---

## Notes for Future Improvements
- Increase SDXL quality:
  - Higher `SDXL_STEPS`
  - Increase image size to 1024x1024 or 1024x1536
  - Use a faster GPU backend
- Add automatic prompt truncation for CLIP 77-token limit
- Add a lightweight “preview mode” vs “quality mode” profile

---

## Files Touched (Summary)
- `backend/hyperlocal/config.py`
- `backend/hyperlocal/pipeline.py`
- `backend/hyperlocal/health.py`
- `backend/hyperlocal/llm_providers.py`
- `backend/hyperlocal/typst_renderer.py`
- `mlx/run_mlx_servers.sh`
- `sdxl/pyproject.toml`
- `sdxl/uv.lock`
- `sdxl/fetch_civitai_model.py`
- `sdxl/fetch_civitai_model.sh`
- `docker-compose.yml`
- `README.md`
- `AGENTS.md`

