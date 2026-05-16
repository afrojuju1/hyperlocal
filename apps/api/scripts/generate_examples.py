from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]


TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "CANCELED"}


def _example_label(path: Path) -> str:
    stem = path.stem
    prefix = "creative-run-"
    return stem[len(prefix):] if stem.startswith(prefix) else stem


def _resolve_output_path(path: str | None) -> str:
    if not path:
        return ""
    normalized = Path(path).as_posix()
    if normalized.startswith("/app/output/"):
        return str(REPO_ROOT / "output" / normalized[len("/app/output/"):])
    return path


def _post_run(
    client: httpx.Client,
    api_base_url: str,
    payload: dict[str, Any],
    *,
    retries: int,
) -> int:
    response = _request_with_retry(
        lambda: client.post(
            f"{api_base_url}/api/v1/creative-runs",
            json=payload,
        ),
        retries=retries,
    )
    response.raise_for_status()
    data = response.json()
    return int(data["run_id"])


def _poll_run(
    client: httpx.Client,
    api_base_url: str,
    run_id: int,
    *,
    timeout_seconds: float,
    poll_seconds: float,
) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_stage = ""
    while time.time() < deadline:
        response = _request_with_retry(
            lambda: client.get(f"{api_base_url}/api/v1/creative-runs/{run_id}"),
            retries=3,
        )
        response.raise_for_status()
        data = response.json()
        stage = f"{data['stage']} ({data['progress_pct']}%)"
        if stage != last_stage:
            print(f"  run {run_id}: {stage}", flush=True)
            last_stage = stage
        if data["status"] in TERMINAL_STATUSES:
            return data
        time.sleep(poll_seconds)
    raise TimeoutError(f"Run {run_id} did not finish within {timeout_seconds:.0f}s")


def _request_with_retry(call, *, retries: int) -> httpx.Response:
    attempts = max(1, retries)
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return call()
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt >= attempts:
                break
            time.sleep(min(5.0, 0.5 * attempt))
    assert last_exc is not None
    raise last_exc


def _summarize_artifact(artifact: dict[str, Any]) -> dict[str, Any]:
    qc_enabled = bool(artifact.get("qc_enabled"))
    qc_passed = artifact.get("qc_passed")
    if not qc_enabled:
        qc_status = "off"
    elif qc_passed:
        qc_status = "passed"
    elif artifact.get("qc_retries_exhausted"):
        qc_status = "needs_review"
    else:
        qc_status = "failed"
    return {
        "variant_index": artifact.get("variant_index"),
        "qc_status": qc_status,
        "qc_attempts": artifact.get("qc_attempts", 1),
        "qc_score": artifact.get("qc_score"),
        "qc_reasons": artifact.get("qc_reasons") or [],
        "final_image": _resolve_output_path(artifact.get("final_image_url")),
        "background_image": _resolve_output_path(artifact.get("background_image_url")),
        "qc_report_url": artifact.get("qc_report_url"),
    }


def _print_run_summary(label: str, run: dict[str, Any]) -> None:
    print(f"\n{label}")
    print(f"  run_id: {run['run_id']}")
    print(f"  status: {run['status']}")
    print(f"  stage: {run['stage']} ({run['progress_pct']}%)")
    if run.get("error"):
        print(f"  error: {run['error']}")
    artifacts = [_summarize_artifact(item) for item in run.get("artifacts", [])]
    if not artifacts:
        print("  artifacts: none")
        return
    for artifact in artifacts:
        reasons = ", ".join(artifact["qc_reasons"]) or "none"
        print(
            "  "
            f"variant {artifact['variant_index']}: "
            f"qc={artifact['qc_status']} "
            f"attempts={artifact['qc_attempts']} "
            f"score={artifact['qc_score']} "
            f"reasons={reasons}"
        )
        print(f"    final: {artifact['final_image']}")
        if artifact["qc_report_url"]:
            print(f"    qc_report: {artifact['qc_report_url']}")


def _load_examples(paths: list[Path], examples_dir: Path) -> list[Path]:
    if paths:
        return paths
    return sorted(examples_dir.glob("creative-run-*.json"))


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run and poll creative-run example payloads.")
    parser.add_argument(
        "--api-base-url",
        default=os.getenv("API_BASE_URL", "http://localhost:18000"),
        help="API base URL. Default: http://localhost:18000",
    )
    parser.add_argument(
        "--example",
        action="append",
        type=Path,
        default=[],
        help="Example JSON file to run. May be provided more than once.",
    )
    parser.add_argument(
        "--examples-dir",
        type=Path,
        default=REPO_ROOT / "examples",
        help="Directory scanned for creative-run-*.json when --example is omitted.",
    )
    parser.add_argument("--timeout", type=float, default=1800.0)
    parser.add_argument("--poll", type=float, default=2.0)
    parser.add_argument("--request-retries", type=int, default=8)
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    args = parser.parse_args()

    api_base_url = args.api_base_url.rstrip("/")
    examples = _load_examples([path.resolve() for path in args.example], args.examples_dir.resolve())
    if not examples:
        raise SystemExit("No examples found.")

    summaries: list[dict[str, Any]] = []
    with httpx.Client(timeout=30.0) as client:
        for example in examples:
            payload = json.loads(example.read_text(encoding="utf-8"))
            label = _example_label(example)
            print(f"\nSubmitting {label}: {example}", flush=True)
            run_id = _post_run(
                client,
                api_base_url,
                payload,
                retries=args.request_retries,
            )
            run = _poll_run(
                client,
                api_base_url,
                run_id,
                timeout_seconds=args.timeout,
                poll_seconds=max(0.5, args.poll),
            )
            summary = {
                "example": label,
                "path": str(example),
                "run_id": run["run_id"],
                "status": run["status"],
                "artifacts": [_summarize_artifact(item) for item in run.get("artifacts", [])],
                "manifest_url": run.get("manifest_url"),
            }
            summaries.append(summary)
            if not args.json:
                _print_run_summary(label, run)

    if args.json:
        print(json.dumps(summaries, indent=2) + "\n")

    failed = [item for item in summaries if item["status"] != "SUCCEEDED"]
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
