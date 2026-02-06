# Hyperlocal

Hyperlocal is a flyer-generation pipeline that combines:
- Local Ollama (OpenAI-compatible) for text + vision
- OpenAI image generation for final flyer images
- Postgres for persistence
- S3-compatible object storage for assets

## Quick Start
```bash
uv sync
```

```bash
docker compose up -d
```

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

```bash
uv run scripts/generate_flyer.py
```

## Notes
- Configure `.env` from `.env.example`.
- Persistence and storage are optional and controlled by env flags.
