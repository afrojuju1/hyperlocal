# Ollama Image Gen Experiments (z-image + flux)

Date range: 2026-02-07 to 2026-02-08

## Goals
- Validate Ollama image generation for flyer creatives.
- Compare `x/z-image-turbo` vs `x/flux2-klein`.
- Improve prompt quality for 3 business types (smoothie, plumbing, real estate).
- Test text rendering reliability and identify the safest approach.

## Scripts Added / Updated
- `backend/scripts/test_ollama_image.py` - quick Ollama image sanity test.
- `backend/scripts/generate_backgrounds.py` - early flyer plate/background tests.
- `backend/scripts/generate_creatives.py` - batch creatives with variants.
- `backend/scripts/generate_creatives_advanced.py` - advanced prompt formula (Subject/Scene/Composition/Lighting/Style/Constraints) for ad-style creatives.

## Models Tested
- `x/z-image-turbo:latest`
- `x/flux2-klein:latest`

## Key Findings
1. **Text hallucination is common with z-image**
   - Z-image tends to add random text (often CJK/Chinese) when the prompt implies flyers/posters/ads.
   - Negative prompts are not effective for z-image; the ban must be in the positive prompt.
   - Strong constraints like “no text of any kind” reduce text but do not guarantee it.

2. **Flux handles English text better, but still unreliable**
   - Flux can render the exact business name correctly in some runs.
   - When prompts are pushed toward “ad-like” visuals, text accuracy regresses.
   - Even with strict constraints (exact characters, nameplate, single line), it still mutates letters.

3. **Best visual results require context, not isolated parts**
   - Plumbing images looked “catalog cutout” when isolated.
   - Better results came from realistic service-ready scenes (under-sink, clean bathroom/kitchen context).

4. **OCR is useful for quick validation**
   - `tesseract` was used to validate text accuracy.
   - Consistency checks via OCR saved manual inspection time.

## Best Outputs (Examples)
- Plumbing no-text baseline (service-ready scene):
  - `output/ollama/creatives_v3_notext/20260207_173716/`
- Flux text correctness (closest success for plumbing):
  - `output/ollama/creatives_advanced/20260207_180229/`
- Real estate ad-style visuals (text still inaccurate):
  - `output/ollama/creatives_advanced/20260207_183529/`

## Prompt Techniques That Helped
- Use the 6-block structure: **Subject + Scene + Composition + Lighting + Style + Constraints**.
- Explicitly ban text, logos, decals, and signage inside the prompt itself.
- Constrain composition with **negative space** for later text overlay.
- Avoid “flyer/poster” wording when trying to suppress text hallucinations.

## Recommendations
1. **For production:**
   - Generate **no-text** images and overlay text in post for guaranteed accuracy.
   - Use z-image for backgrounds when text is off.
   - Use flux only if you insist on in-image text, and expect occasional spelling errors.

2. **For prompt iteration:**
   - Keep prompts structured and change **one block at a time**.
   - Use realistic, service-ready context rather than isolated parts.

## Suggested Next Steps
- Add a deterministic text overlay step for the creative pipeline.
- Maintain a library of per-business prompt templates (no-text by default).
- Keep flux as an optional “text-in-image” fallback only when needed.
