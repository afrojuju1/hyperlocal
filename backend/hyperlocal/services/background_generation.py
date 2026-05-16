from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hyperlocal.comfyui_provider import (
    build_comfyui_config,
    generate_comfyui_background_image,
)
from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.contracts.creative_runs import CreativeRunRequest
from hyperlocal.image_providers import (
    build_ollama_image_config,
    generate_ollama_image,
)
from hyperlocal.openai_helpers import build_client, generate_image
from scripts.generate_ad_prompts import build_llm_prompts, build_template_prompts


@dataclass(frozen=True)
class BackgroundVariant:
    variant_index: int
    prompt_index: int
    image_variation: int
    prompt_slug: str
    prompt_title: str
    prompt: str
    negative_prompt: str
    background_path: str


class BackgroundGenerationService:
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
    ) -> list[BackgroundVariant]:
        prompt_specs = self._build_prompt_specs(request)

        prompt_dir = run_dir / "prompts"
        prompt_dir.mkdir(parents=True, exist_ok=True)

        provider = request.generation.background_provider
        openai_client = None
        openai_model = request.generation.background_model or RUNTIME_CONFIG.image_model
        if provider == "openai":
            if not RUNTIME_CONFIG.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY is not set (required for openai provider)")
            openai_client = build_client(
                base_url=RUNTIME_CONFIG.openai_base_url,
                api_key=RUNTIME_CONFIG.openai_api_key,
            )

        variants: list[BackgroundVariant] = []
        seq = 0
        for i, spec in enumerate(prompt_specs, start=1):
            prompt_txt = prompt_dir / f"{i:02d}__{spec.slug}.prompt.txt"
            negative_txt = prompt_dir / f"{i:02d}__{spec.slug}.negative.txt"
            prompt_txt.write_text(spec.prompt + "\n", encoding="utf-8")
            negative_txt.write_text(spec.negative_prompt + "\n", encoding="utf-8")

            for v in range(1, request.generation.images_per_prompt + 1):
                seq += 1
                out_path = run_dir / "backgrounds" / f"{i:02d}__{spec.slug}__v{v:02d}.png"
                out_path.parent.mkdir(parents=True, exist_ok=True)

                if provider == "ollama":
                    model = request.generation.background_model or self._ollama_config.model
                    ollama_cfg = build_ollama_image_config(
                        model=model,
                        timeout=self._ollama_config.timeout,
                    )
                    generate_ollama_image(
                        prompt=spec.prompt,
                        output_path=str(out_path),
                        config=ollama_cfg,
                    )
                elif provider == "openai":
                    assert openai_client is not None
                    generate_image(
                        client=openai_client,
                        prompt=spec.prompt,
                        output_path=str(out_path),
                        model=openai_model,
                        size=RUNTIME_CONFIG.image_size,
                        quality=RUNTIME_CONFIG.image_quality,
                    )
                elif provider == "comfyui_bg":
                    generate_comfyui_background_image(
                        prompt=spec.prompt,
                        negative_prompt=spec.negative_prompt,
                        output_path=str(out_path),
                        config=self._comfyui_config,
                        seed=request.overlay.seed + seq,
                    )
                else:
                    raise RuntimeError(f"Unsupported background provider: {provider}")

                variants.append(
                    BackgroundVariant(
                        variant_index=seq,
                        prompt_index=i,
                        image_variation=v,
                        prompt_slug=spec.slug,
                        prompt_title=spec.title,
                        prompt=spec.prompt,
                        negative_prompt=spec.negative_prompt,
                        background_path=str(out_path),
                    )
                )

        return variants

    def _build_prompt_specs(self, request: CreativeRunRequest):
        params = dict(
            business_kind=request.campaign.business_kind,
            business_name=request.business.name,
            offer=request.campaign.offer,
            product=request.campaign.product,
            cta=request.campaign.cta,
            text_mode=request.generation.text_mode,
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

    def runtime_meta(self, request: CreativeRunRequest) -> dict[str, str | int]:
        model = request.generation.background_model
        if not model:
            if request.generation.background_provider == "ollama":
                model = RUNTIME_CONFIG.ollama_image_model
            elif request.generation.background_provider == "comfyui_bg":
                model = Path(RUNTIME_CONFIG.comfyui_workflow_path).name
            else:
                model = RUNTIME_CONFIG.image_model
        return {
            "background_provider": request.generation.background_provider,
            "background_model": model,
            "text_model": MODEL_CONFIG.text_model,
            "prompt_engine": request.generation.prompt_engine,
            "text_mode": request.generation.text_mode,
        }
