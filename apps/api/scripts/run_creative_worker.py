from __future__ import annotations

import argparse
from dotenv import load_dotenv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.db import build_sessionmaker, init_db
from hyperlocal.persistence import PersistenceManager
from hyperlocal.workers.creative_run_worker import CreativeRunWorker


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run creative-runs worker loop.")
    parser.add_argument("--poll", type=float, default=RUNTIME_CONFIG.creative_run_poll_interval)
    parser.add_argument("--max-concurrent", type=int, default=RUNTIME_CONFIG.creative_run_max_concurrent)
    args = parser.parse_args()

    if not RUNTIME_CONFIG.database_url:
        raise RuntimeError("DATABASE_URL is required to run creative worker")

    init_db(RUNTIME_CONFIG.database_url)
    manager = PersistenceManager(build_sessionmaker(RUNTIME_CONFIG.database_url))
    worker = CreativeRunWorker(
        manager,
        poll_interval_seconds=args.poll,
        max_concurrent_runs=args.max_concurrent,
    )
    worker.run_forever()


if __name__ == "__main__":
    main()
