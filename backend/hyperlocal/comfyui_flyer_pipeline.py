from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from hyperlocal.comfyui_provider import build_comfyui_config, generate_comfyui_image
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
        default_workflow = repo_root / "comfyui" / "workflows" / "flyer_ad_v1_template.json"
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

    def _ensure_overlay_fit(self, brief: CreativeBrief, style: BrandStyle, copy: CopyVariant) -> CopyVariant:
        # Conservative limits for the current overlay layout (ad_v1).
        def wc(text: str) -> int:
            return len([w for w in text.strip().split() if w])

        max_chars = {
            "headline": 22,
            "subhead": 34,
            "body": 160,
            "cta": 16,
            "disclaimer": 34,
        }
        ok = (
            1 <= wc(copy.headline) <= 6
            and 1 <= wc(copy.subhead) <= 10
            and 1 <= wc(copy.body) <= 32
            and 1 <= wc(copy.cta) <= 4
            and wc(copy.disclaimer or "") <= 12
            and len(copy.headline) <= max_chars["headline"]
            and len(copy.subhead) <= max_chars["subhead"]
            and len(copy.body) <= max_chars["body"]
            and len(copy.cta) <= max_chars["cta"]
            and len(copy.disclaimer or "") <= max_chars["disclaimer"]
        )
        if ok:
            return copy

        prompt = (
            "Rewrite the flyer copy to fit strict overlay size limits and length constraints. "
            "Return JSON with keys: headline, subhead, body, cta, disclaimer. "
            "Constraints: headline <= 6 words and <= 22 chars; "
            "subhead <= 10 words and <= 34 chars; "
            "body <= 32 words and <= 160 chars; "
            "cta <= 4 words and <= 16 chars; "
            "disclaimer <= 12 words and <= 34 chars. "
            "No emojis. Keep meaning. "
            f"Business: {brief.business_details.name}. Product: {brief.product}. Offer: {brief.offer}. "
            f"Tone: {brief.tone}. Style keywords: {', '.join(style.style_keywords)}. "
            "Original:\n"
            + json.dumps(copy.model_dump(), indent=2)
        )
        data = chat_json(
            self.text_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            rewritten = CopyVariant(**data)
        except Exception:
            rewritten = copy

        # Final hard truncation fallback (avoid crashing image generation).
        def trunc(text: str, limit: int) -> str:
            t = (text or "").strip()
            return t if len(t) <= limit else (t[: max(0, limit - 1)].rstrip() + "…")

        return CopyVariant(
            headline=trunc(rewritten.headline, max_chars["headline"]),
            subhead=trunc(rewritten.subhead, max_chars["subhead"]),
            body=trunc(rewritten.body, max_chars["body"]),
            cta=trunc(rewritten.cta, max_chars["cta"]),
            disclaimer=trunc(rewritten.disclaimer or "", max_chars["disclaimer"]) or None,
        )

    def build_background_prompt(self, brief: CreativeBrief, style: BrandStyle, copy: CopyVariant, idx: int) -> str:
        palette = ", ".join(style.palette or brief.brand_colors or [])
        style_keywords = ", ".join(style.style_keywords or brief.style_keywords or [])
        product_lower = (brief.product or "").lower()
        is_hvac = any(tok in product_lower for tok in ["hvac", "ac", "air", "tune", "cool"]) or "hvac" in (
            brief.offer or ""
        ).lower()
        if is_hvac:
            directions = [
                "Clean modern living room with a subtle visible vent/register; gentle cool airflow suggested by soft realistic haze/light beams (not icons).",
                "Clean outdoor AC condenser beside a modern home exterior; bright daylight; minimal landscaping; no labels/plates.",
                "Premium close-up of a clean HVAC register/vent with crisp highlights; minimal interior background; lots of negative space.",
            ]
        else:
            directions = [
                "Hero mango smoothie in a clear unbranded cup with condensation; mango slices and mint; appetizing and bright.",
                "Clean ingredient flatlay: mango, citrus wedges, mint, ice; tidy geometry; modern surface; airy.",
                "Dynamic mango pour into a clear cup with a clean splash; frozen droplets; energetic but minimal.",
            ]
        direction = directions[(idx - 1) % len(directions)]

        # Align with overlay positions: top banner + body card + CTA + footer card.
        layout = (
            "Layout rules: portrait 6x9. Reserve clean overlay zones: "
            "top third (headline/subhead banner); "
            "center area (body card); "
            "lower area (CTA button); "
            "bottom strip (disclaimer + business details). "
            "Keep those zones simple and uncluttered with smooth gradients or subtle texture."
        )

        return (
            "Create a photorealistic background image for a direct-mail promo flyer. "
            "Do NOT include any text, letters, words, numbers, logos, labels, signage, or typography. "
            f"{layout} "
            f"Scene direction: {direction} "
            f"Visual style: {style_keywords or 'clean, modern, photographic'}. "
            f"Color palette: {palette or 'clean whites, one strong accent color'}. "
            f"Business: {brief.business_details.name}. Product: {brief.product}. Offer: {brief.offer}. "
            "No people, faces, hands. High contrast and printable. No icons or diagrams."
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
        raw_copies = self.generate_copy_variants(brief, style, variants)
        copies = [self._ensure_overlay_fit(brief, style, c) for c in raw_copies]

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
            prompt = self.build_background_prompt(brief, style, copy, idx)
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
                rendered_workflow_path=str(run_dir / f"{prefix}.workflow.json"),
            )
            images.append(str(image_path))

        return ComfyFlyerRun(
            output_dir=str(run_dir),
            brief=brief,
            style=style,
            copies=copies,
            images=images,
        )
