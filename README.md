# Hyperlocal

Hyperlocal is a flyer-generation pipeline that combines:
- Local Ollama (OpenAI-compatible) for text + vision
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

## Local SDXL
Use the bundled SDXL WebUI container:
```bash
docker compose up -d sdxl
```
Place your model file at `sdxl/models/Stable-diffusion/` (see `sdxl/README.md`).

If you run the backend outside Docker, point it to the host port:
```bash
SDXL_API_URL=http://localhost:17860/sdapi/v1/txt2img
```
