from __future__ import annotations

import unittest
from dataclasses import dataclass

from hyperlocal.workers.creative_run_worker import CreativeRunWorker


@dataclass
class FakeRun:
    id: int
    request_json: dict


class FakePersistence:
    def __init__(self, run: FakeRun | None):
        self._run = run
        self.failed: list[tuple[int, str, str]] = []

    def claim_next_queued_run(self):
        run = self._run
        self._run = None
        return run

    def mark_run_failed(self, run_id: int, *, error: str, stage: str = "failed") -> None:
        self.failed.append((run_id, error, stage))


class FakePipeline:
    def __init__(self) -> None:
        self.executed: list[int] = []

    def execute(self, run_id: int, request):
        self.executed.append(run_id)


class FailingPipeline(FakePipeline):
    def execute(self, run_id: int, request):
        raise RuntimeError("boom")


REQUEST_PAYLOAD = {
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


class WorkerTransitionTests(unittest.TestCase):
    def test_process_once_executes_pipeline(self) -> None:
        persistence = FakePersistence(FakeRun(id=1, request_json=REQUEST_PAYLOAD))
        worker = CreativeRunWorker(persistence)
        worker._pipeline = FakePipeline()

        processed = worker.process_once()

        self.assertTrue(processed)
        self.assertEqual(worker._pipeline.executed, [1])
        self.assertEqual(persistence.failed, [])

    def test_process_once_marks_failed_on_exception(self) -> None:
        persistence = FakePersistence(FakeRun(id=7, request_json=REQUEST_PAYLOAD))
        worker = CreativeRunWorker(persistence)
        worker._pipeline = FailingPipeline()

        processed = worker.process_once()

        self.assertTrue(processed)
        self.assertEqual(len(persistence.failed), 1)
        run_id, error, stage = persistence.failed[0]
        self.assertEqual(run_id, 7)
        self.assertIn("boom", error)
        self.assertEqual(stage, "failed")


if __name__ == "__main__":
    unittest.main()
