# Deterministic Overlay + Brand Kits

Use this when you want exact copy every time (no misspellings from in-image text rendering).

## 1) Generate text-free backgrounds

From `backend/`:

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
  --image-provider ollama \
  --image-model x/flux2-klein:latest \
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

- `backend/config/brand_kits/smoothie_default.json`
- `backend/config/brand_kits/hvac_default.json`

Tune colors, fonts, and layout ratios there without changing Python code.

## Dynamic templates

Each brand kit can define a `templates` array.

- Use `--template-mode cycle` to rotate template layouts per image.
- Use `--template-mode random --seed 42` to randomize but keep runs reproducible.
- Use `--template-name <name>` to pin a specific template from the kit.
