from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hyperlocal.integrations.comfyui import (
    build_comfyui_config,
    generate_comfyui_background_image,
)
from hyperlocal.core.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.creative.contracts import CreativeRunRequest
from hyperlocal.creative.qc import (
    BackgroundQcResult,
    build_retry_negative_prompt,
    build_retry_prompt,
    evaluate_background_image,
)
from hyperlocal.integrations.images import (
    build_ollama_image_config,
    generate_ollama_image,
)
from hyperlocal.integrations.openai import build_client, generate_image
from hyperlocal.creative.prompting import build_llm_prompts, build_template_prompts


@dataclass(frozen=True)
class GeneratedCreative:
    variant_index: int
    prompt_index: int
    image_variation: int
    prompt_slug: str
    prompt_title: str
    prompt: str
    negative_prompt: str
    image_path: str
    attempts: int = 1
    qc: dict[str, Any] = field(default_factory=dict)


class ImageGenerationService:
    def __init__(self) -> None:
        self._ollama_config = build_ollama_image_config(
            model=RUNTIME_CONFIG.ollama_image_model,
            timeout=RUNTIME_CONFIG.ollama_image_timeout,
        )
        self._comfyui_config = build_comfyui_config(
            api_url=RUNTIME_CONFIG.comfyui_api_url,
            workflow_path=RUNTIME_CONFIG.comfyui_workflow_path,
            size=RUNTIME_CONFIG.image_size,
            timeout=RUNTIME_CONFIG.comfyui_timeout,
            output_node=RUNTIME_CONFIG.comfyui_output_node,
        )

    def generate(
        self,
        *,
        request: CreativeRunRequest,
        run_dir: Path,
    ) -> list[GeneratedCreative]:
        prompt_specs = self._build_prompt_specs(request)

        prompt_dir = run_dir / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)

        provider = request.generation.image_provider
        openai_client = None
        openai_model = request.generation.image_model or RUNTIME_CONFIG.image_model
        if provider == "openai":
            if not RUNTIME_CONFIG.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not set (required for openai provider)")
            openai_client = build_client(
                base_url=RUNTIME_CONFIG.openai_base_url,
                api_key=RUNTIME_CONFIG.openai_api_key,
            )

        variants: list[GeneratedCreative] = []
        seq = 0
        for i, spec in enumerate(prompt_specs, start=1):
            prompt_txt = prompt_dir / f"{i:02d}__{spec.slug}.prompt.txt"
            negative_txt = prompt_dir / f"{i:02d}__{spec.slug}.negative.txt"
            prompt_txt.write_text(spec.prompt + "\n", encoding="utf-8")
            negative_txt.write_text(spec.negative_prompt + "\n", encoding="utf-8")

            for v in range(1, request.generation.images_per_prompt + 1):
                seq += 1
                out_path = run_dir / "generated_images" / f"{i:02d}__{spec.slug}__v{v:02d}.png"
                out_path.parent.mkdir(parents=True, exist_ok=True)

                render = self._generate_with_qc(
                    request=request,
                    provider=provider,
                    openai_client=openai_client,
                    openai_model=openai_model,
                    prompt=spec.prompt,
                    negative_prompt=spec.negative_prompt,
                    output_path=out_path,
                    seq=seq,
                )

                variants.append(
                    GeneratedCreative(
                        variant_index=seq,
                        prompt_index=i,
                        image_variation=v,
                        prompt_slug=spec.slug,
                        prompt_title=spec.title,
                        prompt=render["prompt"],
                        negative_prompt=render["negative_prompt"],
                        image_path=str(out_path),
                        attempts=int(render["attempts"]),
                        qc=render["qc"],
                    )
                )

        return variants

    def _generate_with_qc(
        self,
        *,
        request: CreativeRunRequest,
        provider: str,
        openai_client,
        openai_model: str,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        seq: int,
    ) -> dict[str, Any]:
        if not self._should_qc(request):
            self._render_image(
                request=request,
                provider=provider,
                openai_client=openai_client,
                openai_model=openai_model,
                prompt=prompt,
                negative_prompt=negative_prompt,
                output_path=output_path,
                seed=request.overlay.seed + seq,
            )
            return {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "attempts": 1,
                "qc": {"enabled": False},
            }

        qc_dir = output_path.parents[1] / "qc"
        attempt_dir = output_path.parent / "attempts"
        qc_dir.mkdir(parents=True, exist_ok=True)
        attempt_dir.mkdir(parents=True, exist_ok=True)

        max_attempts = max(1, RUNTIME_CONFIG.max_image_attempts)
        attempt_prompt = prompt
        attempt_negative = negative_prompt
        best: tuple[float, int, Path, str, str, BackgroundQcResult, Path] | None = None
        reports: list[dict[str, Any]] = []

        for attempt in range(1, max_attempts + 1):
            attempt_path = attempt_dir / f"{output_path.stem}__attempt{attempt:02d}.png"
            self._render_image(
                request=request,
                provider=provider,
                openai_client=openai_client,
                openai_model=openai_model,
                prompt=attempt_prompt,
                negative_prompt=attempt_negative,
                output_path=attempt_path,
                seed=request.overlay.seed + seq + ((attempt - 1) * 9973),
            )

            qc_result = evaluate_background_image(
                image_path=attempt_path,
                business_kind=request.campaign.business_kind,
            )
            report = {
                "enabled": True,
                "attempt": attempt,
                "selected": qc_result.passed,
                "prompt": attempt_prompt,
                "negative_prompt": attempt_negative,
                "image_path": str(attempt_path),
                **qc_result.model_dump(),
            }
            report_path = qc_dir / f"{output_path.stem}__attempt{attempt:02d}.json"
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            report["report_path"] = str(report_path)
            reports.append(report)

            if best is None or qc_result.score < best[0]:
                best = (
                    qc_result.score,
                    attempt,
                    attempt_path,
                    attempt_prompt,
                    attempt_negative,
                    qc_result,
                    report_path,
                )

            if qc_result.passed:
                shutil.copyfile(attempt_path, output_path)
                return {
                    "prompt": attempt_prompt,
                    "negative_prompt": attempt_negative,
                    "attempts": attempt,
                    "qc": {**report, "selected": True, "attempt_reports": reports},
                }

            attempt_prompt = build_retry_prompt(
                prompt=prompt,
                business_kind=request.campaign.business_kind,
                qc_result=qc_result,
            )
            attempt_negative = build_retry_negative_prompt(
                negative_prompt=negative_prompt,
                business_kind=request.campaign.business_kind,
                qc_result=qc_result,
            )

        assert best is not None
        _, best_attempt, best_path, best_prompt, best_negative, best_result, best_report_path = best
        shutil.copyfile(best_path, output_path)
        return {
            "prompt": best_prompt,
            "negative_prompt": best_negative,
            "attempts": max_attempts,
            "qc": {
                "enabled": True,
                "selected": True,
                "selected_after_exhausting_retries": True,
                "attempt": best_attempt,
                "report_path": str(best_report_path),
                "image_path": str(best_path),
                **best_result.model_dump(),
                "attempt_reports": reports,
            },
        }

    def _render_image(
        self,
        *,
        request: CreativeRunRequest,
        provider: str,
        openai_client,
        openai_model: str,
        prompt: str,
        negative_prompt: str,
        output_path: Path,
        seed: int,
    ) -> None:
        if provider == "ollama":
            model = request.generation.image_model or self._ollama_config.model
            ollama_cfg = build_ollama_image_config(
                model=model,
                timeout=self._ollama_config.timeout,
            )
            generate_ollama_image(
                prompt=prompt,
                output_path=str(output_path),
                config=ollama_cfg,
            )
        elif provider == "openai":
            assert openai_client is not None
            generate_image(
                client=openai_client,
                prompt=prompt,
                output_path=str(output_path),
                model=openai_model,
                size=RUNTIME_CONFIG.image_size,
                quality=RUNTIME_CONFIG.image_quality,
            )
        elif provider == "comfyui_bg":
            generate_comfyui_background_image(
                prompt=prompt,
                negative_prompt=negative_prompt,
                output_path=str(output_path),
                config=self._comfyui_config,
                seed=seed,
            )
        else:
            raise RuntimeError(f"Unsupported image provider: {provider}")

    def _should_qc(self, request: CreativeRunRequest) -> bool:
        return RUNTIME_CONFIG.qc_enabled and request.generation.creative_mode == "full_ad"

    def _build_prompt_specs(self, request: CreativeRunRequest):
        text_mode = self._effective_image_text_mode(request)
        params = dict(
            business_kind=request.campaign.business_kind,
            business_name=request.business.name,
            offer=request.campaign.offer,
            product=request.campaign.product,
            cta=request.campaign.cta,
            creative_mode=request.generation.creative_mode,
            tone=request.campaign.tone,
            audience=request.campaign.audience,
            constraints=request.campaign.constraints,
            brand_colors=request.campaign.brand_colors,
            style_keywords=request.campaign.style_keywords,
            text_mode=text_mode,
            format_hint=request.campaign.format_hint,
            count=request.generation.count,
        )
        if request.generation.prompt_engine == "template":
            specs = build_template_prompts(**params)
        else:
            try:
                specs = build_llm_prompts(**params)
            except Exception:
                specs = build_template_prompts(**params)
        if not specs:
            raise RuntimeError("Prompt generation returned zero prompt specs")
        return specs

    def _effective_image_text_mode(self, request: CreativeRunRequest) -> str:
        if request.generation.creative_mode == "full_ad":
            return "overlay"
        return request.generation.text_mode or "overlay"

    def runtime_meta(self, request: CreativeRunRequest) -> dict[str, str | int]:
        model = request.generation.image_model
        if not model:
            if request.generation.image_provider == "ollama":
                model = RUNTIME_CONFIG.ollama_image_model
            elif request.generation.image_provider == "comfyui_bg":
                model = Path(RUNTIME_CONFIG.comfyui_workflow_path).name
            else:
                model = RUNTIME_CONFIG.image_model
        return {
            "image_provider": request.generation.image_provider,
            "image_model": model,
            "background_provider": request.generation.image_provider,
            "background_model": model,
            "text_model": MODEL_CONFIG.text_model,
            "prompt_engine": request.generation.prompt_engine,
            "creative_mode": request.generation.creative_mode,
            "text_mode": self._effective_image_text_mode(request),
            "requested_text_mode": request.generation.text_mode or "in_image",
            "final_typography": "ai_layout" if request.generation.creative_mode == "full_ad" else "brand_kit_overlay",
            "qc_enabled": int(self._should_qc(request)),
            "max_image_attempts": RUNTIME_CONFIG.max_image_attempts,
        }
