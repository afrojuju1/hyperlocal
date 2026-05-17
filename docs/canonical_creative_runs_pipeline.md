# Canonical Creative Runs Pipeline (MVP)

This repository now has one canonical generation flow:

1. `POST /api/v1/creative-runs` enqueues a run.
2. Worker (`uv run scripts/run_creative_worker.py`) claims `QUEUED` runs.
3. Pipeline stages:
   - normalize input
   - prompt generation for text-free campaign source images
   - image rendering (`comfyui_bg` default; `ollama | openai` remain optional providers)
   - background QC + retry for full-ad runs
   - AI layout planning + exact typography rendering when `creative_mode=full_ad`
   - deterministic overlay rendering only when `creative_mode=background_overlay`
   - persistence + manifest
4. Poll `GET /api/v1/creative-runs/{run_id}` until `SUCCEEDED | FAILED | CANCELED`.

## Run output layout

Each run writes to:

`apps/api/output/creative_runs/<run_id>/`

Contains:
- `prompts/*.prompt.txt`
- `prompts/*.negative.txt`
- `generated_images/*.png`
- `generated_images/attempts/*.png` for QC retry attempts
- `qc/*.json` background QC reports
- `layout_plans/*.json` for full-ad typography plans
- `final/*.png`
- `manifest.json`

## API endpoints

- `POST /api/v1/creative-runs`
- `GET /api/v1/creative-runs/{run_id}`
- `GET /api/v1/creative-runs/{run_id}/files`

Run status artifacts include compact QC metadata:

- `qc_enabled`
- `qc_passed`
- `qc_attempts`
- `qc_score`
- `qc_retries_exhausted`
- `qc_reasons`
- `qc_report_url`

## Worker

Run from `apps/api/`:

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
COMFYUI_WORKFLOW_PATH=config/comfyui_workflows/z_image_turbo_background.json
COMFYUI_OUTPUT_NODE=10
HYPERLOCAL_QC_ENABLED=1
HYPERLOCAL_MAX_IMAGE_ATTEMPTS=3
```

## Example runner

Run one example:

```bash
make generate-example EXAMPLE=hvac
make generate-example EXAMPLE=coffee
```

Run every payload in `examples/`:

```bash
make generate-all-examples
```

## Vertical configuration

Vertical-specific prompt directions, LLM guardrails, layout color defaults, and QC retry wording are configured in:

`apps/api/config/verticals/defaults.json`
