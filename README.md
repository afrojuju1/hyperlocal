# Hyperlocal

Hyperlocal is a flyer-generation pipeline that combines:
- Local vLLM-MLX (OpenAI-compatible) for text + vision
- Local SDXL for final flyer images
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
- Image generation defaults to local SDXL (via a running SDXL WebUI/Comfy endpoint).

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

## Local SDXL
Run the local SDXL server:
```bash
cd sdxl
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 17860
```

If you run the backend outside Docker, point it to the host port:
```bash
SDXL_API_URL=http://localhost:17860/sdapi/v1/txt2img
```
