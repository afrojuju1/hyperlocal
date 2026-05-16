from __future__ import annotations

import time

from hyperlocal.contracts.creative_runs import CreativeRunRequest
from hyperlocal.persistence import PersistenceManager
from hyperlocal.pipelines.creative_runs import CreativeRunPipeline


class CreativeRunWorker:
    def __init__(
        self,
        persistence: PersistenceManager,
        *,
        poll_interval_seconds: float = 2.0,
        max_concurrent_runs: int = 1,
    ) -> None:
        self._persistence = persistence
        self._pipeline = CreativeRunPipeline(persistence)
        self._poll_interval = max(0.2, poll_interval_seconds)
        self._max_concurrent_runs = max(1, max_concurrent_runs)

    def run_forever(self) -> None:
        while True:
            processed_any = False
            for _ in range(self._max_concurrent_runs):
                processed = self.process_once()
                processed_any = processed_any or processed
                if not processed:
                    break
            if not processed_any:
                time.sleep(self._poll_interval)

    def process_once(self) -> bool:
        run = self._persistence.claim_next_queued_run()
        if run is None:
            return False

        run_id = int(run.id)
        try:
            payload = run.request_json or {}
            request = CreativeRunRequest.model_validate(payload)
            self._pipeline.execute(run_id, request)
        except Exception as exc:
            self._persistence.mark_run_failed(run_id, error=str(exc), stage="failed")
        return True
