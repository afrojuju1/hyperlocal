# Hyperlocal

Hyperlocal is a creative-generation pipeline that combines:
- Local vLLM-MLX (OpenAI-compatible) for text + vision
- Provider-pluggable background generation (Ollama/SDXL/OpenAI/ComfyUI-bg)
- Deterministic text overlay with brand kits
- Postgres-backed async run queue + worker
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

```bash
psql "$DATABASE_URL" -f backend/sql/schema.sql
```

```bash
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
- Redis: `16379`
- Backend API: `18000`
- Frontend: `13000`

## Notes
- Configure `.env` from `backend/.env.example`.
- Canonical API is async run-based under `/api/v1/creative-runs`.
- Worker process is required for queued run execution.
- Image generation defaults to Ollama + deterministic overlays.

## Canonical MVP Flow
1. `POST /api/v1/creative-runs` to enqueue a run.
2. Worker processes queued runs (`uv run scripts/run_creative_worker.py`).
3. Poll `GET /api/v1/creative-runs/{run_id}` until terminal status.
4. Fetch generated files via `/files/*`.

### Endpoints
- `POST /api/v1/creative-runs`
- `GET /api/v1/creative-runs/{run_id}`
- `GET /api/v1/creative-runs/{run_id}/files`
- Compatibility shim (temporary): `POST /api/generate`

### Worker
Run locally from `backend/`:
```bash
uv run scripts/run_creative_worker.py
```

Worker env knobs:
```bash
HYPERLOCAL_CREATIVE_RUN_POLL_INTERVAL=2
HYPERLOCAL_CREATIVE_RUN_MAX_CONCURRENT=1
```

## Local LLM (vllm-mlx)
Install and run the local LLM server:
```bash
uv tool install vllm-mlx
mlx/run_mlx_servers.sh
```

Set the backend to use vllm-mlx (host ports assume local run):
```bash
HYPERLOCAL_LLM_PROVIDER=vllm_mlx
HYPERLOCAL_TEXT_BASE_URL=http://localhost:11435/v1
HYPERLOCAL_VISION_BASE_URL=http://localhost:11436/v1
HYPERLOCAL_TEXT_MODEL=default
HYPERLOCAL_VISION_MODEL=default
```

## Local SDXL (Optional)
Run the local SDXL server:
```bash
cd sdxl
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 17860
```

If you run the backend outside Docker, point it to the host port:
```bash
HYPERLOCAL_IMAGE_PROVIDER=sdxl
SDXL_API_URL=http://localhost:17860/sdapi/v1/txt2img
```

## Ollama Image Generation (Default)
Ollama image generation uses the local `ollama` CLI.

Set the backend to use Ollama:
```bash
HYPERLOCAL_IMAGE_PROVIDER=ollama
OLLAMA_IMAGE_MODEL=x/flux2-klein
```

## ComfyUI (Full Flyer Image)
ComfyUI generates the final flyer image directly (no Typst overlay). Recommended port: `8188`.

1. Install and run ComfyUI on a free port (example `8188`).
2. Build a workflow that:
   - Generates a background image from a prompt/negative prompt
   - Renders text blocks (headline, subhead, body, CTA, disclaimer, business block, audience)
   - Composites them into a final 6x9 image
3. Export the workflow JSON and place it at `comfyui/workflows/flyer_full.json`.
4. If your workflow has multiple outputs, set `COMFYUI_OUTPUT_NODE` to the node id that writes the final image.

Set the backend to use ComfyUI:
```bash
HYPERLOCAL_IMAGE_PROVIDER=comfyui
COMFYUI_API_URL=http://localhost:8188
COMFYUI_WORKFLOW_PATH=comfyui/workflows/flyer_full.json
COMFYUI_OUTPUT_NODE=
```

Workflow placeholders (use these tokens in the JSON):
- `{{PROMPT}}`, `{{NEGATIVE_PROMPT}}`
- `{{WIDTH}}`, `{{HEIGHT}}`
- `{{HEADLINE}}`, `{{SUBHEAD}}`, `{{BODY}}`, `{{CTA}}`, `{{DISCLAIMER}}`
- `{{BUSINESS_BLOCK}}`, `{{AUDIENCE}}`
- `{{PALETTE}}`, `{{STYLE_KEYWORDS}}`, `{{LAYOUT_GUIDANCE}}`
- `{{BUSINESS_NAME}}`, `{{PRODUCT}}`, `{{OFFER}}`, `{{CONSTRAINTS}}`

## Deprecated Script Flows
Legacy script flows were moved to `backend/scripts/archive/` and replaced with deprecation wrappers.  
See `backend/scripts/archive/README.md` for replacement commands.
