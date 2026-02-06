CREATE TABLE IF NOT EXISTS creative_runs (
  id SERIAL PRIMARY KEY,
  campaign_id INTEGER,
  status VARCHAR(32) NOT NULL DEFAULT 'RUNNING',
  brief_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  brand_style_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  model_versions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_creative_runs_campaign_created
  ON creative_runs (campaign_id, created_at DESC);

CREATE TABLE IF NOT EXISTS creative_variants (
  id SERIAL PRIMARY KEY,
  run_id INTEGER NOT NULL REFERENCES creative_runs(id) ON DELETE CASCADE,
  variant_index INTEGER NOT NULL,
  copy_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  prompt_text TEXT NOT NULL,
  negative_prompt TEXT NOT NULL,
  image_url TEXT,
  qc_passed BOOLEAN NOT NULL DEFAULT false,
  qc_text TEXT,
  qc_score DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_run_variant UNIQUE (run_id, variant_index)
);

CREATE INDEX IF NOT EXISTS idx_creative_variants_run
  ON creative_variants (run_id, variant_index);

CREATE TABLE IF NOT EXISTS creative_assets (
  id SERIAL PRIMARY KEY,
  campaign_id INTEGER NOT NULL,
  run_id INTEGER,
  variant_id INTEGER,
  image_path TEXT NOT NULL,
  copy_text TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_creative_assets_campaign
  ON creative_assets (campaign_id);
