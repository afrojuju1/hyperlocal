from __future__ import annotations

import argparse
import json
import random
from datetime import datetime
from pathlib import Path
import sys

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperlocal.config import RUNTIME_CONFIG
from hyperlocal.deterministic_overlay import (
    OverlayCopy,
    TemplateVariant,
    compose_deterministic_overlay,
    load_brand_kit,
    resolve_template,
)


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _resolve_pngs(input_dir: Path, pattern: str) -> list[Path]:
    files = sorted(p for p in input_dir.glob(pattern) if p.is_file())
    return [p for p in files if "__final" not in p.stem]


def _slug(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_") or "template"


def _choose_template(
    *,
    mode: str,
    templates: list[TemplateVariant],
    index: int,
    rng: random.Random,
    forced_name: str | None,
) -> TemplateVariant | None:
    if not templates:
        return None
    if forced_name:
        for template in templates:
            if template.name == forced_name:
                return template
        return None
    if mode == "static":
        return templates[0]
    if mode == "random":
        return rng.choice(templates)
    return templates[(index - 1) % len(templates)]


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Apply deterministic text overlays to generated ad backgrounds."
    )
    parser.add_argument("--input-dir", required=True, help="Directory containing source PNGs.")
    parser.add_argument(
        "--pattern",
        default="*__v*.png",
        help='Glob pattern for source images (default: "*__v*.png").',
    )
    parser.add_argument(
        "--brand-kit",
        required=True,
        help="Path to brand kit JSON config (colors/fonts/layout).",
    )
    parser.add_argument("--headline", required=True, help="Exact headline text.")
    parser.add_argument("--subhead", default="", help="Exact subhead text.")
    parser.add_argument("--offer", required=True, help="Exact offer text.")
    parser.add_argument("--cta", default="BOOK NOW", help="Exact CTA text.")
    parser.add_argument("--footer", default="", help="Optional footer line.")
    parser.add_argument("--limit", type=int, default=0, help="Max images to render (0 = all).")
    parser.add_argument(
        "--template-mode",
        choices=["static", "cycle", "random"],
        default="cycle",
        help="How to apply brand-kit templates across outputs (default: cycle).",
    )
    parser.add_argument(
        "--template-name",
        default=None,
        help="Use a specific template name from the brand kit.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed used when --template-mode=random.",
    )
    parser.add_argument(
        "--out-subdir",
        default="final_overlays",
        help="Output folder under output/ (default: final_overlays).",
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Optional explicit output dir (overrides --out-subdir).",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    images = _resolve_pngs(input_dir, args.pattern)
    if not images:
        raise RuntimeError(f"No source images found in {input_dir} with pattern {args.pattern}")

    if args.limit and args.limit > 0:
        images = images[: args.limit]

    brand_kit = load_brand_kit(args.brand_kit)
    rng = random.Random(args.seed)
    if args.template_name:
        if not resolve_template(brand_kit, name=args.template_name):
            available = ", ".join(t.name for t in brand_kit.templates) or "(none)"
            raise RuntimeError(
                f'Template "{args.template_name}" not found in brand kit. Available: {available}'
            )

    copy = OverlayCopy(
        headline=args.headline,
        subhead=args.subhead,
        offer=args.offer,
        cta=args.cta,
        footer=args.footer,
    )

    if args.out_dir:
        run_dir = Path(args.out_dir)
    else:
        run_dir = Path(RUNTIME_CONFIG.output_dir) / args.out_subdir / timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    outputs: list[dict[str, str]] = []
    for i, src in enumerate(images, start=1):
        template = _choose_template(
            mode=args.template_mode,
            templates=brand_kit.templates,
            index=i,
            rng=rng,
            forced_name=args.template_name,
        )
        template_name = template.name if template else "base"
        dst = run_dir / f"{src.stem}__{_slug(template_name)}__final.png"
        print(f"Overlay {src} -> {dst}", flush=True)
        compose_deterministic_overlay(
            input_image_path=src,
            output_image_path=dst,
            copy=copy,
            brand_kit=brand_kit,
            template=template,
        )
        outputs.append({"input": str(src), "output": str(dst), "template": template_name})

    manifest = {
        "created_at": datetime.now().isoformat(),
        "input_dir": str(input_dir),
        "source_pattern": args.pattern,
        "brand_kit_path": str(Path(args.brand_kit)),
        "brand_kit_name": brand_kit.name,
        "template_mode": args.template_mode,
        "template_name": args.template_name,
        "seed": args.seed,
        "available_templates": [t.name for t in brand_kit.templates],
        "copy": {
            "headline": copy.headline,
            "subhead": copy.subhead,
            "offer": copy.offer,
            "cta": copy.cta,
            "footer": copy.footer,
        },
        "image_count": len(outputs),
        "images": outputs,
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Run complete: {run_dir}", flush=True)


if __name__ == "__main__":
    main()
