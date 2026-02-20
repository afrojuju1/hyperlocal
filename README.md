# Hyperlocal

Hyperlocal is a canonical async creative-generation pipeline that combines:
- Local vLLM-MLX (OpenAI-compatible) for text generation
- Provider-pluggable background generation (`ollama`, `sdxl`, `openai`, `comfyui_bg`)
- Deterministic text overlay with brand kits
- Postgres-backed run queue + worker
- On-disk output storage under `output/`

## Quick Start
```bash
cd backend
uv sync
```

## Containers
```bash
docker compose up -d --build
```

Apply schema:
```bash
psql "$DATABASE_URL" -f backend/sql/schema.sql
```

Run worker:
```bash
cd backend
uv run scripts/run_creative_worker.py
```

## Frontend
```bash
cd web
bun install
bun run dev
```

## Ports (Docker)
- Postgres: `55432`
- Backend API: `18000`
- Frontend: `13000`

## Canonical MVP Flow
1. `POST /api/v1/creative-runs` to enqueue a run.
2. Worker claims `QUEUED` runs and executes generation.
3. Poll `GET /api/v1/creative-runs/{run_id}` until terminal status.
4. Read generated files via `/files/*`.

### Endpoints
- `POST /api/v1/creative-runs`
- `GET /api/v1/creative-runs/{run_id}`
- `GET /api/v1/creative-runs/{run_id}/files`

## Notes
- Configure `.env` from `backend/.env.example`.
- Worker process is required for queued run execution.
- Output root: `backend/output/creative_runs/<run_id>/`.

## Local LLM (vllm-mlx)
Install and run local text/vision servers:
```bash
uv tool install vllm-mlx
mlx/run_mlx_servers.sh
```

Set backend to use vllm-mlx:
```bash
HYPERLOCAL_LLM_PROVIDER=vllm_mlx
HYPERLOCAL_TEXT_BASE_URL=http://localhost:11435/v1
HYPERLOCAL_VISION_BASE_URL=http://localhost:11436/v1
HYPERLOCAL_TEXT_MODEL=default
HYPERLOCAL_VISION_MODEL=default
```

## Local SDXL (Optional)
Run local SDXL server:
```bash
cd sdxl
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 17860
```

If backend runs outside Docker:
```bash
HYPERLOCAL_IMAGE_PROVIDER=sdxl
SDXL_API_URL=http://localhost:17860/sdapi/v1/txt2img
```

## Ollama Image Generation
```bash
HYPERLOCAL_IMAGE_PROVIDER=ollama
OLLAMA_IMAGE_MODEL=x/flux2-klein
```

## ComfyUI Background Generation (Optional)
```bash
HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg
COMFYUI_API_URL=http://localhost:8188
COMFYUI_WORKFLOW_PATH=comfyui/workflows/flyer_full.json
COMFYUI_OUTPUT_NODE=
```
