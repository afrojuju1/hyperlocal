from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from hyperlocal.comfyui_provider import (
    build_comfyui_config,
    generate_comfyui_image,
    render_comfyui_workflow_template,
)
from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.llm_providers import build_llm_clients
from hyperlocal.openai_helpers import chat_json
from hyperlocal.prompt_templates import business_block
from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


@dataclass(frozen=True)
class ComfyFlyerSettings:
    ckpt_name: str = "sd_xl_base_1.0.safetensors"
    seed: int = 42
    steps: int = 30
    cfg: float = 6.5
    sampler_name: str = "euler"
    scheduler: str = "normal"
    denoise: float = 1.0


@dataclass(frozen=True)
class ComfyFlyerRun:
    output_dir: str
    brief: CreativeBrief
    style: BrandStyle
    copies: list[CopyVariant]
    images: list[str]


class ComfyFlyerPipeline:
    """
    ComfyUI-only flyer pipeline.

    Generates:
    - Brand style (text-only) via LLM
    - Copy variants via LLM
    - Background prompt (text-free) via a deterministic prompt template
    - Final flyer images via ComfyUI workflow with reliable text overlays
    """

    def __init__(
        self,
        *,
        comfyui_api_url: str | None = None,
        workflow_path: str | None = None,
        timeout: float | None = None,
        output_node: str | None = None,
    ) -> None:
        llm_clients = build_llm_clients()
        self.text_client = llm_clients.text_client
        self.text_model = llm_clients.text_model

        self.comfyui_api_url = comfyui_api_url or RUNTIME_CONFIG.comfyui_api_url
        # Resolve workflow path relative to repo root even when invoked from `backend/`.
        backend_root = Path(__file__).resolve().parents[1]
        repo_root = backend_root.parent
        default_workflow = repo_root / "comfyui" / "workflows" / "flyer_full_template.json"
        if workflow_path:
            wf = Path(workflow_path)
            self.workflow_path = str(wf if wf.is_absolute() else (repo_root / wf))
        else:
            self.workflow_path = str(default_workflow)
        self.timeout = float(timeout if timeout is not None else RUNTIME_CONFIG.comfyui_timeout)
        self.output_node = output_node if output_node is not None else RUNTIME_CONFIG.comfyui_output_node

    def _brand_style_from_text(self, brief: CreativeBrief) -> BrandStyle:
        business_name = brief.business_details.name
        prompt = (
            "You are a brand designer for direct-mail flyers. Return JSON with keys: "
            "palette (array of color names), style_keywords (array), layout_guidance (string), "
            "typography_guidance (string). Return JSON only. "
            f"Business: {business_name}. Product: {brief.product}. Offer: {brief.offer}. "
            f"Tone: {brief.tone}. Audience: {brief.audience or 'local households'}."
        )
        data = chat_json(
            self.text_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return BrandStyle(**data)

    def build_brand_style(self, brief: CreativeBrief) -> BrandStyle:
        style = self._brand_style_from_text(brief)
        # Minimal sanitization: keep it printable and avoid humans.
        banned = {"people", "person", "faces", "face", "hands", "human", "portrait"}
        style_keywords = [kw for kw in style.style_keywords if kw.lower() not in banned]
        return BrandStyle(
            palette=style.palette,
            style_keywords=style_keywords,
            layout_guidance=style.layout_guidance or "",
            typography_guidance=style.typography_guidance or "",
        )

    def generate_copy_variants(self, brief: CreativeBrief, style: BrandStyle, variants: int) -> list[CopyVariant]:
        from hyperlocal.prompt_templates import copy_prompt

        target = max(1, variants)
        prompt = copy_prompt(brief, style, target)
        data = chat_json(
            self.text_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        if isinstance(data, list):
            copies = [CopyVariant(**item) for item in data if isinstance(item, dict)]
        else:
            copies = []
        if len(copies) >= target:
            return copies[:target]
        # Fallback: deterministic copy so image generation can proceed.
        fallback = CopyVariant(
            headline=brief.product[:36] or brief.business_details.name,
            subhead="Limited Time Offer",
            body=f"{brief.offer}.",
            cta=brief.cta or "Call Today",
            disclaimer="Terms apply.",
        )
        while len(copies) < target:
            copies.append(fallback)
        return copies

    def build_background_prompt(self, brief: CreativeBrief, style: BrandStyle, copy: CopyVariant) -> str:
        palette = ", ".join(style.palette or brief.brand_colors or [])
        style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
        # Align with flyer_full overlay positions: top banner + body area + CTA + footer.
        return (
            "Create a photorealistic background image for a 6x9 direct-mail promo flyer. "
            "Do NOT include any text, letters, words, logos, signage, menus, labels, or typography. "
            "Design the composition to leave clean space for overlays: "
            "top third reserved for headline/subhead; mid area reserved for body; "
            "lower area reserved for a CTA button and footer details. "
            "Keep those regions simple and uncluttered. "
            f"Visual style: {style_keywords or 'clean, modern, photographic'}. "
            f"Color palette: {palette or 'clean whites, one strong accent color'}. "
            f"Business: {brief.business_details.name}. Product: {brief.product}. Offer: {brief.offer}. "
            "No people, faces, hands. High contrast and printable."
        )

    def run(
        self,
        brief: CreativeBrief,
        *,
        variants: int = 3,
        out_subdir: str = "comfyui_flyers",
        settings: ComfyFlyerSettings | None = None,
    ) -> ComfyFlyerRun:
        settings = settings or ComfyFlyerSettings()

        run_dir = Path(RUNTIME_CONFIG.output_dir) / out_subdir / timestamp()
        run_dir.mkdir(parents=True, exist_ok=True)

        style = self.build_brand_style(brief)
        copies = self.generate_copy_variants(brief, style, variants)

        config = build_comfyui_config(
            api_url=self.comfyui_api_url,
            workflow_path=self.workflow_path,
            size=RUNTIME_CONFIG.image_size,
            timeout=self.timeout,
            output_node=self.output_node,
        )

        # Save run metadata for easy review.
        manifest = {
            "created_at": datetime.now().isoformat(),
            "pipeline": "ComfyFlyerPipeline",
            "comfyui_api_url": self.comfyui_api_url,
            "workflow_path": self.workflow_path,
            "variants": variants,
            "settings": {
                "ckpt_name": settings.ckpt_name,
                "seed": settings.seed,
                "steps": settings.steps,
                "cfg": settings.cfg,
                "sampler_name": settings.sampler_name,
                "scheduler": settings.scheduler,
                "denoise": settings.denoise,
            },
            "text_model": MODEL_CONFIG.text_model,
            "business_block": business_block(brief),
        }
        (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        (run_dir / "brief.json").write_text(json.dumps(brief.model_dump(), indent=2) + "\n")
        (run_dir / "brand_style.json").write_text(json.dumps(style.model_dump(), indent=2) + "\n")

        images: list[str] = []
        for idx, copy in enumerate(copies, start=1):
            prompt = self.build_background_prompt(brief, style, copy)
            negative = (
                "text, letters, words, numbers, logos, watermarks, labels, signage, "
                "icons, diagrams, charts, UI, people, faces, hands, clutter"
            )

            prefix = f"variant_{idx:02d}"
            (run_dir / f"{prefix}.prompt.txt").write_text(prompt + "\n")
            (run_dir / f"{prefix}.negative.txt").write_text(negative + "\n")
            (run_dir / f"{prefix}.copy.json").write_text(
                json.dumps(copy.model_dump(), indent=2) + "\n"
            )

            # Provide workflow knobs via placeholders (flyer_full_template.json).
            overrides = {
                "CKPT_NAME": settings.ckpt_name,
                "SEED": settings.seed + idx,
                "STEPS": settings.steps,
                "CFG": settings.cfg,
                "SAMPLER_NAME": settings.sampler_name,
                "SCHEDULER": settings.scheduler,
                "DENOISE": settings.denoise,
            }
            rendered = render_comfyui_workflow_template(config.workflow_path, {
                # Rendered workflow should include the exact per-variant copy/prompt too.
                "PROMPT": prompt,
                "NEGATIVE_PROMPT": negative,
                "WIDTH": config.width,
                "HEIGHT": config.height,
                "CKPT_NAME": settings.ckpt_name,
                "SEED": settings.seed + idx,
                "STEPS": settings.steps,
                "CFG": settings.cfg,
                "SAMPLER_NAME": settings.sampler_name,
                "SCHEDULER": settings.scheduler,
                "DENOISE": settings.denoise,
                # The rest are filled by generate_comfyui_image, but we save a rendered copy here
                # for debugging; we still call generate_comfyui_image for actual generation.
                "FONT_PATH": "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
                "HEADLINE": copy.headline,
                "SUBHEAD": copy.subhead,
                "BODY": copy.body,
                "CTA": copy.cta,
                "DISCLAIMER": copy.disclaimer or "",
                "BUSINESS_BLOCK": business_block(brief),
                "AUDIENCE": brief.audience or "",
                "PALETTE": ", ".join(style.palette or []),
                "STYLE_KEYWORDS": ", ".join(style.style_keywords or []),
                "LAYOUT_GUIDANCE": style.layout_guidance or "",
                "BUSINESS_NAME": brief.business_details.name,
                "PRODUCT": brief.product,
                "OFFER": brief.offer,
                "CONSTRAINTS": "; ".join(brief.constraints or []),
                "PRIMARY_COLOR": "#1e67b6",
                "ACCENT_COLOR": "#62b6ff",
                "TEXT_DARK": "#111111",
                "TEXT_MUTED": "#333333",
                "TEXT_LIGHT": "#ffffff",
            })
            (run_dir / f"{prefix}.workflow.json").write_text(json.dumps(rendered, indent=2) + "\n")

            image_path = run_dir / f"{prefix}.png"
            generate_comfyui_image(
                prompt=prompt,
                negative_prompt=negative,
                output_path=str(image_path),
                config=config,
                brief=brief,
                style=style,
                copy=copy,
                workflow_overrides=overrides,
            )
            images.append(str(image_path))

        return ComfyFlyerRun(
            output_dir=str(run_dir),
            brief=brief,
            style=style,
            copies=copies,
            images=images,
        )
