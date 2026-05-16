from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from hyperlocal.api.main import app


@dataclass
class FakeRun:
    id: int
    status: str
    stage: str
    progress_pct: int
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: str | None = None
    output_dir: str | None = "output/creative_runs/1"
    manifest_path: str | None = "output/creative_runs/1/manifest.json"


@dataclass
class FakeVariant:
    variant_index: int
    final_image_url: str
    overlay_template: str
    background_image_url: str | None = None


class FakeManager:
    def __init__(self):
        self._run = FakeRun(
            id=1,
            status="QUEUED",
            stage="queued",
            progress_pct=0,
            created_at=datetime.now(timezone.utc),
        )

    def create_run_request(self, **kwargs):
        return self._run

    def get_run(self, run_id: int):
        if run_id != 1:
            return None
        return self._run

    def get_variants(self, run_id: int):
        if run_id != 1:
            return []
        return [
            FakeVariant(
                variant_index=1,
                final_image_url="output/creative_runs/1/final/001.png",
                overlay_template="classic_center",
                background_image_url="output/creative_runs/1/generated_images/001.png",
            )
        ]


class CreativeRunsApiTests(unittest.TestCase):
    def test_create_and_status(self) -> None:
        payload = {
            "business": {"name": "Sunset Smoothie Co."},
            "campaign": {
                "business_kind": "smoothie",
                "product": "Mango smoothie",
                "offer": "BUY 1 GET 1 50% OFF",
                "cta": "ORDER NOW",
            },
            "generation": {
                "count": 1,
                "images_per_prompt": 1,
                "prompt_engine": "template",
                "background_provider": "comfyui_bg",
            },
            "overlay": {
                "brand_kit": "config/brand_kits/smoothie_default.json",
                "template_mode": "cycle",
                "seed": 42,
                "copy_mode": "auto",
            },
            "output": {"subdir": "creative_runs"},
        }

        fake_manager = FakeManager()
        with patch("hyperlocal.api.routes.creative_runs._manager", return_value=fake_manager):
            client = TestClient(app)
            create_resp = client.post("/api/v1/creative-runs", json=payload)
            self.assertEqual(create_resp.status_code, 200)
            self.assertEqual(create_resp.json()["run_id"], 1)

            status_resp = client.get("/api/v1/creative-runs/1")
            self.assertEqual(status_resp.status_code, 200)
            data = status_resp.json()
            self.assertEqual(data["status"], "QUEUED")
            self.assertEqual(len(data["artifacts"]), 1)


if __name__ == "__main__":
    unittest.main()
