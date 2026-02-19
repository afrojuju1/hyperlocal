# FLUX.2 Klein Text Accuracy Playbook (Ollama)

Date: 2026-02-19  
Scope: Local image generation with `x/flux2-klein:latest` via Ollama for ad creatives that require readable in-image text.

## Why this exists
- Ad creatives fail quickly when headline/offer text is misspelled.
- This guide captures the prompt patterns that improved our HVAC `$70` tune-up ad output.

## What worked
- Put required text first in the prompt, before scene details.
- Wrap each required phrase in quotes and call out exact spelling/capitalization.
- Keep required copy short (headline, offer, CTA) instead of many text elements.
- Specify text placement for each phrase.
- Specify typography style, size intent, and color contrast.
- Keep background/footer areas intentionally empty for later overlays.

## Prompt rules for readable text
- Use flowing prose, not keyword dumps.
- Front-load priorities in this order: required text, layout, subject, scene/style.
- Use explicit text instructions:
  - `The image contains these exact text phrases with exact spelling and capitalization: "AC TUNE-UP SPECIAL", "ONLY $70", "BOOK NOW".`
- Add placement instructions:
  - `Place AC TUNE-UP SPECIAL at upper left, ONLY $70 beneath it, and BOOK NOW in a rounded button at lower left.`
- Add legibility constraints:
  - `bold geometric sans-serif`, `high contrast`, `mobile readability`.
- Use specific color anchors for text/backdrop when needed (hex codes are supported in FLUX guidance).
- Prefer positive phrasing over long lists of negatives.

## Reusable prompt template
```text
A modern local [BUSINESS TYPE] ad with crisp, highly legible typography.
The image contains these exact text phrases with exact spelling and capitalization:
"[HEADLINE]", "[OFFER]", "[CTA]".
Place [HEADLINE] at [POSITION], [OFFER] at [POSITION], and [CTA] inside [BUTTON STYLE] at [POSITION].
Use [FONT STYLE], [TEXT COLOR] on [BACKGROUND COLOR/TREATMENT] with strong contrast and clean spacing for mobile readability.
Show [SUBJECT] in [SCENE], photorealistic style with [LIGHTING].
Keep [AREA] clean and empty for later logo/phone overlay.
```

## Current known-good HVAC example
```text
A modern local HVAC social ad with crisp, highly legible typography. The image contains these exact text phrases with exact spelling and capitalization: "AC TUNE-UP SPECIAL", "ONLY $70", and "BOOK NOW". Place AC TUNE-UP SPECIAL at upper left, ONLY $70 directly beneath it, and BOOK NOW inside a rounded blue button at lower left. Use bold geometric sans-serif lettering, white text color #FFFFFF on a blue gradient panel #0B6DBA with strong contrast and clean spacing for mobile readability. Show a friendly HVAC technician in a blue uniform beside a suburban home and visible outdoor AC condenser in bright summer daylight, photorealistic style. Keep the bottom strip clean and empty for later logo and phone overlay.
```

## Iteration checklist (each new run)
- Verify exact text match for all required phrases.
- Verify CTA is clearly visible and not merged into background.
- Verify offer amount is legible at thumbnail/mobile size.
- Verify no gibberish logos or fake contact info appear.
- If text fails after 3 prompt iterations, switch to no-text background + deterministic text overlay.

## Suggested workflow in this repo
- Generate with: `uv run scripts/generate_hvac_tuneup_70_ad.py`
- Review output in:
  - `backend/output/ollama/hvac_tuneup_70/<timestamp>/creative.png`
  - `backend/output/ollama/hvac_tuneup_70/<timestamp>/prompt.txt`

## References
- Ollama image generation overview: [https://ollama.com/blog/image-generation](https://ollama.com/blog/image-generation)
- FLUX.2 Klein prompting guide: [https://docs.bfl.ai/guides/prompting_guide_flux2_klein](https://docs.bfl.ai/guides/prompting_guide_flux2_klein)
- FLUX.2 typography/text tips: [https://docs.bfl.ai/guides/prompting_guide_flux2](https://docs.bfl.ai/guides/prompting_guide_flux2)
