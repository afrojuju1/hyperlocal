# Canonical Creative Runs Pipeline (MVP)

This repository now has one canonical generation flow:

1. `POST /api/v1/creative-runs` enqueues a run.
2. Worker (`uv run scripts/run_creative_worker.py`) claims `QUEUED` runs.
3. Pipeline stages:
   - normalize input
   - copy generation (`auto` or provided)
   - prompt generation for text-free backgrounds
   - background rendering (`ollama | sdxl | openai | comfyui_bg`)
   - deterministic overlay rendering (brand kit templates)
   - persistence + manifest
4. Poll `GET /api/v1/creative-runs/{run_id}` until `SUCCEEDED | FAILED | CANCELED`.

## Run output layout

Each run writes to:

`backend/output/creative_runs/<run_id>/`

Contains:
- `prompts/*.prompt.txt`
- `prompts/*.negative.txt`
- `backgrounds/*.png`
- `final/*.png`
- `manifest.json`

## API endpoints

- `POST /api/v1/creative-runs`
- `GET /api/v1/creative-runs/{run_id}`
- `GET /api/v1/creative-runs/{run_id}/files`

## Worker

Run from `backend/`:

```bash
uv run scripts/run_creative_worker.py
```

Optional env knobs:

```bash
HYPERLOCAL_CREATIVE_RUN_POLL_INTERVAL=2
HYPERLOCAL_CREATIVE_RUN_MAX_CONCURRENT=1
```
