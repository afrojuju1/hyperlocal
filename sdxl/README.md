# SDXL Local Models

This directory stores local SDXL assets. The default flow uses a lightweight
FastAPI server powered by Diffusers.

## Local SDXL Server
```bash
cd sdxl
uv sync
uv run uvicorn server:app --host 0.0.0.0 --port 17860
```

Environment overrides:
- `SDXL_MODEL_ID` (default `stabilityai/sdxl-turbo`)
- `SDXL_DEVICE` (`mps`, `cuda`, or `cpu`)
- `SDXL_DTYPE` (`float16`, `bfloat16`, `float32`)

## Civitai (local .safetensors)
To avoid HF rate limits, download a single-file model from Civitai and point
`SDXL_MODEL_ID` at it. Use a **.safetensors** model version for best results.

```bash
cd sdxl
export CIVITAI_TOKEN=... # optional if the model requires auth
python3 fetch_civitai_model.py <modelVersionId>
```

Then set:
- `SDXL_MODEL_ID=/models/civitai/latest.safetensors`

## Hugging Face CLI (prefetch)
If you hit HF rate limits, prefetch the model with the `hf` CLI so the
server starts from cache.

Host prefetch:
```bash
cd sdxl
uv sync
export HF_TOKEN=... # optional, but avoids rate limits
export HF_HOME="$(pwd)/models/hf"
uv run hf download stabilityai/sdxl-turbo
```

Docker prefetch (uses the `sdxl_hf_cache` volume):
```bash
export HF_TOKEN=... # optional, but avoids rate limits
docker compose run --rm -e HF_TOKEN="$HF_TOKEN" sdxl hf download stabilityai/sdxl-turbo
```

## Local Models
If you want to use local weights, place your model files in:
`sdxl/models/Stable-diffusion/`
