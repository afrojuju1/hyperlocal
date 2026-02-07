#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download

DEFAULT_MODELS = [
    "mlx-community/Llama-3.2-3B-Instruct-4bit",
    "mlx-community/Qwen3-VL-4B-Instruct-3bit",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Prefetch vllm-mlx model weights into the HF cache")
    parser.add_argument(
        "models",
        nargs="*",
        default=DEFAULT_MODELS,
        help="One or more HF repo IDs to download",
    )
    parser.add_argument("--revision", default=None, help="Optional HF revision")
    parser.add_argument(
        "--cache-dir",
        default=os.getenv("HF_HOME") or None,
        help="Optional HF cache dir (defaults to HF_HOME or default cache)",
    )
    args = parser.parse_args()

    cache_dir = Path(args.cache_dir).expanduser() if args.cache_dir else None

    print("HF transfer:", os.getenv("HF_HUB_ENABLE_HF_TRANSFER", "0"))
    print("HF cache:", cache_dir or "default")

    for repo in args.models:
        print(f"\n==> Downloading {repo}")
        snapshot_download(
            repo_id=repo,
            revision=args.revision,
            cache_dir=str(cache_dir) if cache_dir else None,
            resume_download=True,
        )
        print(f"Done: {repo}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
