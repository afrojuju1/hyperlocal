#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import hf_hub_download


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download SDXL base checkpoint using HF Transfer."
    )
    parser.add_argument(
        "--repo",
        default="stabilityai/stable-diffusion-xl-base-1.0",
        help="Hugging Face repo id",
    )
    parser.add_argument(
        "--filename",
        default="sd_xl_base_1.0.safetensors",
        help="Checkpoint filename to download",
    )
    parser.add_argument(
        "--out-dir",
        default="comfyui/ComfyUI/models/checkpoints",
        help="Destination directory (will be created if missing)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Enable hf_transfer for fast downloads if installed.
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    print(f"Downloading {args.repo}:{args.filename}")
    print(f"Destination: {out_dir}")
    path = hf_hub_download(
        repo_id=args.repo,
        filename=args.filename,
        local_dir=str(out_dir),
        local_dir_use_symlinks=False,
    )
    print(f"Downloaded to: {path}")


if __name__ == "__main__":
    main()
