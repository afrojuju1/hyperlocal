# Hyperlocal

Hyperlocal is a canonical async creative-generation pipeline that combines:
- Remote NucBox Ollama (OpenAI-compatible) for text generation
- Remote NucBox ComfyUI/Z-Image Turbo full-ad image generation (`comfyui_bg` default)
- Optional deterministic text overlay with brand kits for legacy/background-overlay mode
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

## NucBox Ollama Text Generation

Text and prompt generation use the NucBox Ollama OpenAI-compatible endpoint over Tailscale:

```bash
HYPERLOCAL_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://100.111.132.114:11434/v1
OLLAMA_API_KEY=ollama
HYPERLOCAL_TEXT_MODEL=qwen3:8b
```

Health check:

```bash
curl http://100.111.132.114:11434/v1/models
```

## NucBox ComfyUI Image Generation

Image generation runs on the NucBox over Tailscale.

```bash
HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg
COMFYUI_API_URL=http://100.111.132.114:8188
COMFYUI_WORKFLOW_PATH=config/comfyui_workflows/z_image_turbo_background.json
COMFYUI_OUTPUT_NODE=10
```

The NucBox ComfyUI service is `comfyui-rocm.service`.
