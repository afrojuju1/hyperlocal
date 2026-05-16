# Agents Guide

## Project Summary
Hyperlocal is a flyer-generation pipeline that uses:
- Remote NucBox Ollama (OpenAI-compatible) for text generation
- Remote NucBox ComfyUI/Z-Image Turbo for full-ad image generation (default)
- Postgres for persistence
- On-disk output storage under `output/`

## Conventions
- Use `uv` for Python dependencies and execution.
- Use Postgres + SQL schema from `backend/sql/schema.sql` (Option B).
- Avoid absolute paths in commands; assume repo root.
- Keep generated images out of git; they go under `output/`.

## Setup
```bash
make setup
```

## Frontend
```bash
make web
```

## Local Infrastructure
```bash
make up
```

## Ports (Docker)
- Postgres: `55432`
- Backend API: `18000`
- Frontend: `13000`

## Database (Option B)
```bash
make db-init
```

## Run Flyer Generation
```bash
make worker
```

## Environment
Use `.env` (see `backend/.env.example`) and set at minimum:
- `DATABASE_URL`
- `OLLAMA_BASE_URL` (NucBox default: `http://100.111.132.114:11434/v1`)
- `HYPERLOCAL_TEXT_MODEL` (default: `qwen3:8b`)
- `COMFYUI_API_URL` (NucBox default: `http://100.111.132.114:8188`)
- `COMFYUI_WORKFLOW_PATH` (default: `config/comfyui_workflows/z_image_turbo_background.json`)

## Text Generation
- Default provider is remote NucBox Ollama via `HYPERLOCAL_LLM_PROVIDER=ollama`.
- The canonical Docker path uses `OLLAMA_BASE_URL=http://100.111.132.114:11434/v1`.

## Image Generation
- Default provider is remote ComfyUI via `HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg`.
- The canonical model files live on the NucBox under `~/ai/ComfyUI/models/`.
- Optional providers remain available in code, but they are not part of the default Docker path.

## Persistence Flow
- `creative_runs` stores the run + brief + model versions
- `creative_variants` stores prompts, copy, QC, and image URL
- `creative_assets` stores the selected/approved asset

## Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **Run quality gates** (if code changed) - Tests, linters, builds
2. **Commit intentionally** - Include all intended changes and no generated output
3. **PUSH TO REMOTE** - This is MANDATORY when the user asks to land the work:
   ```bash
   make check
   git pull --rebase
   git push
   git status  # MUST show "up to date with origin"
   ```
4. **Clean up** - Clear stashes, prune remote branches if relevant
5. **Verify** - All intended changes committed AND pushed
6. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
