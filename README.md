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

```bash
docker compose up -d
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

## Notes
- Configure `.env` from `backend/.env.example`.
- Persistence and storage are optional and controlled by env flags.
