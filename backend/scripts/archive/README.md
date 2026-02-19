# Archived Script Flows (Deprecated)

These scripts were moved from `backend/scripts/` to reduce MVP ambiguity.

| Old script | Status | Canonical replacement |
|---|---|---|
| `generate_hvac_ads.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --business-kind hvac --text-mode overlay --format-hint flyer_poster --out-subdir ad_creatives` |
| `generate_smoothie_ads.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --business-kind smoothie --text-mode overlay --format-hint flyer_poster --out-subdir ad_creatives` |
| `generate_hvac_tuneup_70_ad.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --business-kind hvac --offer "ONLY $70" --text-mode overlay --out-subdir hvac_tuneup_70` |
| `generate_hvac_tuneup_70_llm_variants.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --business-kind hvac --count 2 --images-per-prompt 2 --text-mode overlay --out-subdir hvac_llm_variants` |
| `generate_creatives.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --engine llm --text-mode overlay --out-subdir ad_creatives` |
| `generate_creatives_advanced.py` | Deprecated | `uv run scripts/generate_ad_prompts.py --engine llm --text-mode overlay --out-subdir prompts` |
| `generate_backgrounds.py` | Deprecated | `uv run scripts/generate_ad_creatives.py --text-mode overlay --out-subdir backgrounds` |

Wrappers remain at original paths and print this mapping to keep compatibility during migration.
