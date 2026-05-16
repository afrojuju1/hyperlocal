# Deterministic Overlay + Brand Kits

Use this when you want the older brand-kit template renderer instead of the full-ad AI layout renderer.

## 1) Generate text-free backgrounds in overlay mode

The default product path now generates a text-free source image, plans typography separately, and renders exact text into `final/*.png`. Use `creative_mode=background_overlay` or the one-off script below when you need the older deterministic brand-kit template placement.

```bash
HYPERLOCAL_IMAGE_PROVIDER=comfyui_bg
COMFYUI_API_URL=http://100.111.132.114:8188
COMFYUI_WORKFLOW_PATH=config/comfyui_workflows/z_image_turbo_background.json
COMFYUI_OUTPUT_NODE=10
uv run scripts/run_creative_worker.py
```

For one-off background experiments, the older prompt script can still be used with explicit provider flags.

From `apps/api/`:

```bash
uv run scripts/generate_ad_creatives.py \
  --engine llm \
  --business-kind smoothie \
  --count 2 \
  --images-per-prompt 2 \
  --text-mode overlay \
  --format-hint flyer_poster \
  --business-name "Sunset Smoothie Co." \
  --product "Mango smoothie" \
  --offer "BUY 1 GET 1 50% OFF MANGO SMOOTHIES" \
  --image-provider comfyui_bg \
  --out-subdir smoothie_llm_bogo_overlay
```

## 2) Apply deterministic overlay text

```bash
uv run scripts/render_ad_overlays.py \
  --input-dir output/smoothie_llm_bogo_overlay/<run_timestamp> \
  --brand-kit config/brand_kits/smoothie_default.json \
  --headline "Sunset Smoothie Co." \
  --subhead "MANGO SMOOTHIES" \
  --offer "BUY 1 GET 1 50% OFF" \
  --cta "ORDER NOW" \
  --footer "Limited time. Terms apply." \
  --template-mode cycle \
  --limit 2 \
  --out-subdir smoothie_final_ads
```

## Brand kit files

- `apps/api/config/brand_kits/smoothie_default.json`
- `apps/api/config/brand_kits/hvac_default.json`

Tune colors, fonts, and layout ratios there without changing Python code.

## Dynamic templates

Each brand kit can define a `templates` array.

- Use `--template-mode cycle` to rotate template layouts per image.
- Use `--template-mode random --seed 42` to randomize but keep runs reproducible.
- Use `--template-name <name>` to pin a specific template from the kit.
