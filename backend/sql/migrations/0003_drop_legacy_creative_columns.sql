ALTER TABLE creative_runs DROP COLUMN IF EXISTS brief_json;
ALTER TABLE creative_runs DROP COLUMN IF EXISTS brand_style_json;
ALTER TABLE creative_runs DROP COLUMN IF EXISTS model_versions_json;

ALTER TABLE creative_variants DROP COLUMN IF EXISTS image_url;
