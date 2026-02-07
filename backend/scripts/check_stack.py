from __future__ import annotations

import json

from dotenv import load_dotenv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.health import run_health_checks


def main() -> None:
    load_dotenv()
    report = run_health_checks()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
