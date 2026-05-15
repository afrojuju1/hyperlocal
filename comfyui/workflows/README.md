# ComfyUI Workflow Templates

Canonical background generation uses the NucBox ComfyUI/Z-Image Turbo workflow:

- `comfyui/workflows/z_image_turbo_background.json`

The backend replaces placeholder tokens at runtime. Use tokens without quotes and let the code insert JSON-safe values.

Supported placeholders for the canonical workflow:
- `{{PROMPT}}`
- `{{WIDTH}}`, `{{HEIGHT}}`
- `{{SEED}}`
