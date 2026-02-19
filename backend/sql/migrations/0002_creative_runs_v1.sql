ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS stage VARCHAR(64) NOT NULL DEFAULT 'queued';
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS progress_pct INTEGER NOT NULL DEFAULT 0;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS request_json JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS pipeline_version TEXT;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS output_dir TEXT;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS manifest_path TEXT;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE creative_runs ADD COLUMN IF NOT EXISTS finished_at TIMESTAMPTZ;

UPDATE creative_runs
SET status = CASE
  WHEN status = 'COMPLETE' THEN 'SUCCEEDED'
  WHEN status = 'RUNNING' THEN 'RUNNING'
  WHEN status = 'FAILED' THEN 'FAILED'
  ELSE status
END;

ALTER TABLE creative_variants ADD COLUMN IF NOT EXISTS background_image_url TEXT;
ALTER TABLE creative_variants ADD COLUMN IF NOT EXISTS overlay_template TEXT;
ALTER TABLE creative_variants ADD COLUMN IF NOT EXISTS final_image_url TEXT;

CREATE INDEX IF NOT EXISTS idx_creative_runs_status_created
  ON creative_runs (status, created_at ASC);
