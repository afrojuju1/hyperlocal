# Ad-Creative Prompting Notes (HVAC + Smoothie)

Date range: 2026-02-08

## Goals
- Pivot to ad-first prompting (not product shots).
- Test simple, direct prompts vs structured prompts.
- Compare text accuracy and creative quality using Flux.
- Produce quick scripts for rapid iteration.

## New Scripts
- `backend/scripts/generate_hvac_ads.py`
  - Simple HVAC ad prompts with business name + promo text.
  - Uses Flux (`x/flux2-klein:latest`) for improved text accuracy.
  - Output: `output/ollama/hvac_ads/<timestamp>/`
- `backend/scripts/generate_smoothie_ads.py`
  - Simple smoothie ad prompts (BOGO mango offer).
  - Uses Flux (`x/flux2-klein:latest`) for text accuracy.
  - Output: `output/ollama/smoothie_ads/<timestamp>/`

## What Worked Better
- **Simpler prompts** improved alignment with “ad creative” intent compared to over-structured prompts.
- **Flux** was more accurate than z-image for text, but still imperfect.
- Explicit text rules (exact strings, two lines, nameplate, no duplicates) help, but still not fully reliable.

## What Still Needs Work
- Text accuracy is inconsistent even with strict prompt constraints.
- Some outputs still look like product shots rather than ad creatives.
- The best path for guaranteed text is likely **no-text image + overlay**.

## Outputs to Review
- HVAC simple prompts:
  - `output/ollama/hvac_ads/20260207_233532/`
  - `output/ollama/hvac_ads/20260207_233901/` (with strict text rules)
  - `output/ollama/hvac_ads/20260207_234435/` (Flux)
- Smoothie BOGO prompts:
  - `output/ollama/smoothie_ads/20260208_092311/`
  - `output/ollama/smoothie_ads/20260208_092841/` (with strict text rules)

## Recommended Next Steps
1. Decide whether to **keep text in image** or switch to **no-text + overlay**.
2. If keeping text in-image, test a **fixed text block (nameplate)** with limited font size.
3. If switching to overlay, keep prompts text-free and focus on ad layout + negative space.
