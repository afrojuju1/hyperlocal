# Agents Guide

## Project Summary
Hyperlocal is a flyer-generation pipeline that uses:
- Local vLLM-MLX (OpenAI-compatible) for text + vision
- Ollama for the final flyer image (default)
- Postgres for persistence
- On-disk output storage under `output/`

## Conventions
- Use `uv` for Python dependencies and execution.
- Use Postgres + SQL schema from `backend/sql/schema.sql` (Option B).
- Avoid absolute paths in commands; assume repo root.
- Keep generated images out of git; they go under `output/`.

## Setup
```bash
cd backend
uv sync
```

## Frontend
```bash
cd web
bun install
bun run dev
```

## Local Infrastructure
```bash
docker compose up -d
```

## Ports (Docker)
- Postgres: `55432`
- Redis: `16379`
- Backend API: `18000`
- Frontend: `13000`

## Database (Option B)
```bash
psql "$DATABASE_URL" -f backend/sql/schema.sql
```

## Run Flyer Generation
```bash
uv run scripts/generate_flyer.py
```

## Environment
Use `.env` (see `backend/.env.example`) and set at minimum:
- `DATABASE_URL`
- `SDXL_API_URL` (if using local SDXL, Docker host port defaults to 17860)
- `OLLAMA_IMAGE_MODEL` (if using Ollama image generation, e.g. `x/flux2-klein`)

## Image Generation
- Default provider is Ollama via `HYPERLOCAL_IMAGE_PROVIDER=ollama` and `OLLAMA_IMAGE_MODEL`.
- To use SDXL, set `HYPERLOCAL_IMAGE_PROVIDER=sdxl` and `SDXL_API_URL` (run the local server in `sdxl/` on port `17860`).
- To use OpenAI images, set `HYPERLOCAL_IMAGE_PROVIDER=openai` and `OPENAI_API_KEY`.

## Persistence Flow
- `creative_runs` stores the run + brief + model versions
- `creative_variants` stores prompts, copy, QC, and image URL
- `creative_assets` stores the selected/approved asset
