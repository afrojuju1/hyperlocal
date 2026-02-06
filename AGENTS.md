# Agents Guide

## Project Summary
Hyperlocal is a flyer-generation pipeline that uses:
- Local Ollama (OpenAI-compatible) for text + vision
- OpenAI image generation for the final flyer image
- Postgres for persistence
- S3-compatible object storage for image assets

## Conventions
- Use `uv` for Python dependencies and execution.
- Use Postgres + SQL schema from `sql/schema.sql` (Option B).
- Avoid absolute paths in commands; assume repo root.
- Keep generated images out of git; they go under `output/`.

## Setup
```bash
uv sync
```

## Local Infrastructure
```bash
docker compose up -d
```

## Database (Option B)
```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

## Run Flyer Generation
```bash
uv run scripts/generate_flyer.py
```

## Environment
Use `.env` (see `.env.example`) and set at minimum:
- `OPENAI_API_KEY`
- `DATABASE_URL`

Optional (S3/MinIO uploads):
- `HYPERLOCAL_STORAGE_ENABLED=1`
- `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET`, `S3_PUBLIC_BASE_URL`

## Persistence Flow
- `creative_runs` stores the run + brief + model versions
- `creative_variants` stores prompts, copy, QC, and image URL
- `creative_assets` stores the selected/approved asset
