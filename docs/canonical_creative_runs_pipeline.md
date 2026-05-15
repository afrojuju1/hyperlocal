# Canonical Creative Runs Pipeline (MVP)

This repository now has one canonical generation flow:

1. `POST /api/v1/creative-runs` enqueues a run.
2. Worker (`uv run scripts/run_creative_worker.py`) claims `QUEUED` runs.
3. Pipeline stages:
   - normalize input
   - copy generation (`auto` or provided)
   - prompt generation for text-free backgrounds
   - background rendering (`comfyui_bg` default; `ollama | sdxl | openai` remain optional providers)
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
HYPERLOCAL_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://100.111.132.114:11434/v1
OLLAMA_API_KEY=ollama
HYPERLOCAL_TEXT_MODEL=qwen3:8b
HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg
COMFYUI_API_URL=http://100.111.132.114:8188
COMFYUI_WORKFLOW_PATH=comfyui/workflows/z_image_turbo_background.json
COMFYUI_OUTPUT_NODE=10
```
