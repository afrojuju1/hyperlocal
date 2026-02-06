# Hyperlocal

Hyperlocal is a flyer-generation pipeline that combines:
- Local Ollama (OpenAI-compatible) for text + vision
- OpenAI image generation for final flyer images
- Postgres for persistence
- S3-compatible object storage for assets

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
- MinIO: `19000` (API), `19001` (console)
- Backend API: `18000`
- Frontend: `13000`

## Notes
- Configure `.env` from `backend/.env.example`.
- Persistence and storage are optional and controlled by env flags.
- Image generation defaults to local SDXL (via a running SDXL WebUI/Comfy endpoint).

## Local SDXL
Run a local SDXL endpoint (e.g. Automatic1111) and set:
```bash
SDXL_API_URL=http://localhost:7860/sdapi/v1/txt2img
```
