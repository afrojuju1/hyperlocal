# ComfyUI Workflow Templates

Canonical image generation uses the NucBox ComfyUI/Z-Image Turbo workflow:

- `config/comfyui_workflows/z_image_turbo_background.json`

The API app replaces placeholder tokens at runtime. Use tokens without quotes and let the code insert JSON-safe values.

Supported placeholders for the canonical workflow:
- `{{PROMPT}}`
- `{{WIDTH}}`, `{{HEIGHT}}`
- `{{SEED}}`
