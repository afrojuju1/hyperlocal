# NucBox Inference Setup

Hyperlocal uses the NucBox for the default inference path:

- Text and prompt generation: NucBox Ollama OpenAI-compatible API.
- Background image generation: NucBox ComfyUI/Z-Image Turbo over Tailscale.
- Deterministic overlay rendering: backend worker after the background is generated.

## Text LLM

Docker compose points text generation at NucBox Ollama:

```bash
HYPERLOCAL_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://100.111.132.114:11434/v1
OLLAMA_API_KEY=ollama
HYPERLOCAL_TEXT_MODEL=qwen3:8b
```

Health check:

```bash
curl http://100.111.132.114:11434/v1/models
```

Expected service on the NucBox:

```bash
ssh ade-nucbox-k8-plus 'systemctl --user status ollama.service'
```

## Background Images

Use the NucBox ComfyUI ROCm service:

```bash
HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg
COMFYUI_API_URL=http://100.111.132.114:8188
COMFYUI_WORKFLOW_PATH=comfyui/workflows/z_image_turbo_background.json
COMFYUI_OUTPUT_NODE=10
```

Required model files on the NucBox:

- `~/ai/ComfyUI/models/diffusion_models/z_image_turbo_nvfp4.safetensors`
- `~/ai/ComfyUI/models/text_encoders/qwen_3_4b_fp4_mixed.safetensors`
- `~/ai/ComfyUI/models/vae/ae.safetensors`

Service controls:

```bash
ssh ade-nucbox-k8-plus 'systemctl --user status comfyui-rocm.service'
ssh ade-nucbox-k8-plus 'systemctl --user enable --now comfyui-rocm.service'
```

Health check:

```bash
curl http://100.111.132.114:8188/system_stats
```
