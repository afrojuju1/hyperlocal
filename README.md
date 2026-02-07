# Hyperlocal

Hyperlocal is a flyer-generation pipeline that combines:
- Local vLLM-MLX (OpenAI-compatible) for text + vision
- Ollama for final flyer images (default)
- Postgres for persistence
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
uv run scripts/generate_flyer.py
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
- Persistence is optional and controlled by env flags.
- Image generation defaults to Ollama.

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
