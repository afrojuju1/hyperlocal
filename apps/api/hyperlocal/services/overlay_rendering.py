from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from hyperlocal.contracts.creative_runs import CreativeCopyInput, CreativeRunRequest
from hyperlocal.deterministic_overlay import (
    OverlayCopy,
    TemplateVariant,
    compose_deterministic_overlay,
    load_brand_kit,
    resolve_template,
)
from hyperlocal.services.image_generation import GeneratedCreative


@dataclass(frozen=True)
class OverlayVariantResult:
    variant_index: int
    prompt_slug: str
    background_image_url: str
    final_image_url: str
    overlay_template: str


class OverlayRenderingService:
    def render(
        self,
        *,
        request: CreativeRunRequest,
        run_dir: Path,
        source_images: list[GeneratedCreative],
        copies: list[CreativeCopyInput],
    ) -> list[OverlayVariantResult]:
        if not source_images:
            return []

        kit_path = self._resolve_brand_kit_path(request.overlay.brand_kit)
        brand_kit = load_brand_kit(kit_path)

        if request.overlay.template_name:
            selected = resolve_template(brand_kit, name=request.overlay.template_name)
            if selected is None:
                available = ", ".join(t.name for t in brand_kit.templates) or "(none)"
                raise RuntimeError(
                    f'Template "{request.overlay.template_name}" not found in brand kit. Available: {available}'
                )

        rng = random.Random(request.overlay.seed)
        out_dir = run_dir / "final"
        out_dir.mkdir(parents=True, exist_ok=True)

        results: list[OverlayVariantResult] = []
        for idx, source in enumerate(source_images, start=1):
            template = self._select_template(
                mode=request.overlay.template_mode,
                templates=brand_kit.templates,
                index=idx,
                rng=rng,
                forced_name=request.overlay.template_name,
            )
            template_name = template.name if template else "base"
            copy = copies[(source.prompt_index - 1) % len(copies)]

            final_path = out_dir / f"{source.variant_index:03d}__{source.prompt_slug}__{template_name}.png"
            compose_deterministic_overlay(
                input_image_path=source.image_path,
                output_image_path=str(final_path),
                copy=OverlayCopy(
                    headline=copy.headline,
                    subhead=copy.subhead,
                    offer=copy.offer,
                    cta=copy.cta,
                    footer=copy.footer,
                ),
                brand_kit=brand_kit,
                template=template,
            )

            results.append(
                OverlayVariantResult(
                    variant_index=source.variant_index,
                    prompt_slug=source.prompt_slug,
                    background_image_url=source.image_path,
                    final_image_url=str(final_path),
                    overlay_template=template_name,
                )
            )

        return results

    def _resolve_brand_kit_path(self, brand_kit: str) -> str:
        p = Path(brand_kit)
        if p.is_absolute() and p.exists():
            return str(p)
        backend_root = Path(__file__).resolve().parents[2]
        candidate = backend_root / brand_kit
        if candidate.exists():
            return str(candidate)
        repo_candidate = backend_root.parent / brand_kit
        if repo_candidate.exists():
            return str(repo_candidate)
        raise FileNotFoundError(f"Brand kit not found: {brand_kit}")

    def _select_template(
        self,
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
