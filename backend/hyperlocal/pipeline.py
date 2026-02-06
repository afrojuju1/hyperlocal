from __future__ import annotations

import json
import time
from pathlib import Path

from hyperlocal.config import MODEL_CONFIG, RUNTIME_CONFIG
from hyperlocal.openai_helpers import (
    build_client,
    chat_json,
    generate_image,
    image_url_from_path,
)
from hyperlocal.prompt_templates import copy_prompt, image_prompt, negative_prompt
from hyperlocal.qc import extract_text, validate_text
from hyperlocal.persistence import PersistenceManager
from hyperlocal.storage import build_storage, key_for_image
from hyperlocal.db import build_sessionmaker
from hyperlocal.schemas import BrandStyle, CopyVariant, CreativeBrief, ImageVariant, PromptPackage, RunResult


class FlyerPipeline:
    def __init__(self) -> None:
        self.local_client = build_client(
            base_url=RUNTIME_CONFIG.ollama_base_url,
            api_key=RUNTIME_CONFIG.ollama_api_key,
        )
        if not RUNTIME_CONFIG.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.remote_client = build_client(api_key=RUNTIME_CONFIG.openai_api_key)
        self.text_model = MODEL_CONFIG.text_model
        self.vision_model = MODEL_CONFIG.vision_model
        self.storage = build_storage()
        self.persistence = None
        if RUNTIME_CONFIG.persist_enabled and RUNTIME_CONFIG.database_url:
            session_factory = build_sessionmaker(RUNTIME_CONFIG.database_url)
            self.persistence = PersistenceManager(session_factory)
        self._active_brief: CreativeBrief | None = None

    def _brand_style_from_images(self, brief: CreativeBrief) -> BrandStyle:
        prompt = (
            "Analyze the brand visuals and return JSON with keys: "
            "palette (array of hex or color names), style_keywords (array), "
            "layout_guidance (string), typography_guidance (string). "
            "Return JSON only, no markdown."
        )
        image_parts = [
            {"type": "image_url", "image_url": {"url": image_url_from_path(path)}}
            for path in brief.reference_images
        ]
        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}] + image_parts,
            }
        ]
        data = chat_json(self.local_client, self.vision_model, messages)
        return BrandStyle(**data)

    def _brand_style_from_text(self, brief: CreativeBrief) -> BrandStyle:
        business_name = self._business_name(brief)
        prompt = (
            "You are a brand designer. Given the business description, return JSON with keys: "
            "palette (array of color names), style_keywords (array), layout_guidance (string), "
            "typography_guidance (string). Return JSON only. "
            f"Business: {business_name}. Product: {brief.product}. Offer: {brief.offer}. "
            f"Tone: {brief.tone}. Audience: {brief.audience or 'local households'}."
        )
        data = chat_json(
            self.local_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return BrandStyle(**data)

    def build_brand_style(self, brief: CreativeBrief) -> BrandStyle:
        if brief.reference_images:
            style = self._brand_style_from_images(brief)
        else:
            style = self._brand_style_from_text(brief)
        return self._sanitize_brand_style(style)

    def _sanitize_brand_style(self, style: BrandStyle) -> BrandStyle:
        banned_tokens = {"people", "person", "faces", "face", "hands", "human", "portrait"}
        filtered_keywords = [
            kw for kw in style.style_keywords if kw.lower() not in banned_tokens
        ]
        layout = style.layout_guidance or ""
        sentences = [s.strip() for s in layout.split(".") if s.strip()]
        clean_sentences = []
        for sentence in sentences:
            lower = sentence.lower()
            if any(token in lower for token in banned_tokens):
                continue
            clean_sentences.append(sentence)
        clean_layout = ". ".join(clean_sentences)
        if clean_layout:
            clean_layout += "."
        return BrandStyle(
            palette=style.palette,
            style_keywords=filtered_keywords,
            layout_guidance=clean_layout,
            typography_guidance=style.typography_guidance,
        )

    def generate_copy_variants(self, brief: CreativeBrief, style: BrandStyle) -> list[CopyVariant]:
        target_count = max(1, RUNTIME_CONFIG.variants)
        prompt = copy_prompt(brief, style, target_count)
        for _ in range(3):
            data = chat_json(
                self.local_client,
                self.text_model,
                messages=[{"role": "user", "content": prompt}],
            )
            variants = self._coerce_copy_variants(data)
            if len(variants) == target_count:
                return [self._ensure_constraints(v, brief, style) for v in variants]
            if len(variants) > target_count:
                trimmed = variants[:target_count]
                return [self._ensure_constraints(v, brief, style) for v in trimmed]
            variants = self._pad_variants(variants, brief, style, target_count)
            if len(variants) == target_count:
                return [self._ensure_constraints(v, brief, style) for v in variants]
        raise ValueError("Copy generation did not return expected variants after retries")

    def _pad_variants(
        self,
        variants: list[CopyVariant],
        brief: CreativeBrief,
        style: BrandStyle,
        target_count: int,
    ) -> list[CopyVariant]:
        needed = target_count - len(variants)
        if needed <= 0:
            return variants
        business_name = self._business_name(brief)
        prompt = (
            "Generate additional flyer copy variants as JSON array with keys: "
            "headline, subhead, body, cta, disclaimer. "
            f"Return exactly {needed} variants. "
            f"Business: {business_name}. Product: {brief.product}. Offer: {brief.offer}. "
            f"Tone: {brief.tone}. Style: {', '.join(style.style_keywords)}."
        )
        data = chat_json(
            self.local_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        extra = self._coerce_copy_variants(data)
        return (variants + extra)[:target_count]

    def _ensure_constraints(
        self, variant: CopyVariant, brief: CreativeBrief, style: BrandStyle
    ) -> CopyVariant:
        if self._within_constraints(variant):
            return variant
        business_name = self._business_name(brief)
        prompt = (
            "Rewrite the flyer copy to fit the strict length constraints. "
            "Return JSON with keys: headline, subhead, body, cta, disclaimer. "
            "Constraints: headline <= 6 words, subhead <= 10 words, body <= 28 words, "
            "cta <= 4 words, disclaimer <= 12 words. "
            f"Business: {business_name}. Product: {brief.product}. Offer: {brief.offer}. "
            f"Tone: {brief.tone}. Style: {', '.join(style.style_keywords)}. "
            "Original copy:\n"
            + json.dumps(variant.model_dump(), indent=2)
        )
        data = chat_json(
            self.local_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return CopyVariant(**data)

    def _within_constraints(self, variant: CopyVariant) -> bool:
        def word_count(text: str) -> int:
            return len([w for w in text.strip().split() if w])

        return all(
            [
                1 <= word_count(variant.headline) <= 6,
                1 <= word_count(variant.subhead) <= 10,
                1 <= word_count(variant.body) <= 28,
                1 <= word_count(variant.cta) <= 4,
                word_count(variant.disclaimer or "") <= 12,
            ]
        )

    def _coerce_copy_variants(self, data: object) -> list[CopyVariant]:
        if isinstance(data, dict):
            if "variants" in data:
                data = data["variants"]
            elif "copy_variants" in data:
                data = data["copy_variants"]
        if isinstance(data, list):
            if all(isinstance(item, dict) for item in data):
                return [CopyVariant(**item) for item in data]
            if all(isinstance(item, str) for item in data):
                return self._repair_copy_variants(data)
        raise ValueError("Copy generation did not return usable JSON variants")

    def _repair_copy_variants(self, items: list[str]) -> list[CopyVariant]:
        prompt = (
            "Convert the following list into JSON array of objects with keys: "
            "headline, subhead, body, cta, disclaimer. "
            "Return JSON only. Input list:\n"
            + json.dumps(items, indent=2)
        )
        data = chat_json(
            self.local_client,
            self.text_model,
            messages=[{"role": "user", "content": prompt}],
        )
        if not isinstance(data, list):
            raise ValueError("Repair failed to produce a JSON array")
        return [CopyVariant(**item) for item in data]

    def build_prompt_packages(
        self, brief: CreativeBrief, style: BrandStyle, variants: list[CopyVariant]
    ) -> list[PromptPackage]:
        packages = []
        neg = negative_prompt()
        for variant in variants:
            packages.append(
                PromptPackage(
                    image_prompt=image_prompt(brief, style, variant),
                    negative_prompt=neg,
                    copy_variant=variant,
                )
            )
        return packages

    def generate_images(
        self, packages: list[PromptPackage], run_dir: str, run_id: int | None
    ) -> list[ImageVariant]:
        variants: list[ImageVariant] = []
        for idx, pkg in enumerate(packages, start=1):
            image_path = str(Path(run_dir) / f"variant_{idx:02d}.png")
            variant_id = None
            if self.persistence and run_id is not None:
                record = self.persistence.create_variant(
                    run_id=run_id,
                    variant_index=idx,
                    copy=pkg.copy_variant,
                    prompt_text=pkg.image_prompt,
                    negative_prompt=pkg.negative_prompt,
                )
                variant_id = record.id
            qc_passed = False
            qc_text = ""
            for attempt in range(1, RUNTIME_CONFIG.max_image_attempts + 1):
                generate_image(
                    client=self.remote_client,
                    prompt=(
                        pkg.image_prompt
                        + "\n\nNegative constraints: "
                        + pkg.negative_prompt
                    ),
                    output_path=image_path,
                    model=RUNTIME_CONFIG.image_model,
                    size=RUNTIME_CONFIG.image_size,
                    quality=RUNTIME_CONFIG.image_quality,
                )
                if not RUNTIME_CONFIG.qc_enabled:
                    qc_passed = True
                    qc_text = "qc disabled"
                else:
                    qc_text = extract_text(self.local_client, self.vision_model, image_path)
                    expected = [
                        pkg.copy_variant.headline,
                        pkg.copy_variant.subhead,
                        pkg.copy_variant.body,
                        pkg.copy_variant.cta,
                        pkg.copy_variant.disclaimer or "",
                    ]
                    required = self._required_details(self._active_brief)
                    expected.extend(required)
                    qc_passed = validate_text(expected, qc_text)
                if qc_passed:
                    break
                time.sleep(1)
            image_url = image_path
            if self.storage and run_id is not None:
                key = key_for_image(run_id, idx)
                image_url = self.storage.upload_file(image_path, key)
            if self.persistence and variant_id is not None:
                self.persistence.update_variant_image(variant_id, image_url)
                self.persistence.update_variant_qc(variant_id, qc_passed, qc_text)
            variants.append(
                ImageVariant(
                    index=idx,
                    prompt=pkg,
                    image_path=image_url,
                    qc_passed=qc_passed,
                    qc_text=qc_text,
                )
            )
        return variants

    def run(self, brief: CreativeBrief) -> RunResult:
        self._active_brief = brief
        run_record = None
        model_versions = {
            "text_model": self.text_model,
            "vision_model": self.vision_model,
            "image_model": RUNTIME_CONFIG.image_model,
        }
        if self.persistence:
            run_record = self.persistence.create_run(brief, model_versions)
        try:
            style = self.build_brand_style(brief)
            if self.persistence and run_record:
                self.persistence.update_run_style(run_record.id, style)
            variants = self.generate_copy_variants(brief, style)
            packages = self.build_prompt_packages(brief, style, variants)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            run_dir = str(Path(RUNTIME_CONFIG.output_dir) / f"flyer_runs/{timestamp}")
            Path(run_dir).mkdir(parents=True, exist_ok=True)
            images = self.generate_images(
                packages, run_dir, run_record.id if run_record else None
            )

            result = RunResult(
                brief=brief,
                brand_style=style,
                variants=images,
                output_dir=run_dir,
            )
            with open(Path(run_dir) / "run.json", "w", encoding="utf-8") as f:
                f.write(result.model_dump_json(indent=2))
            if self.persistence and run_record:
                self.persistence.update_run_status(run_record.id, "COMPLETE")
            return result
        except Exception as exc:
            if self.persistence and run_record:
                self.persistence.update_run_status(run_record.id, "FAILED", str(exc))
            raise
        finally:
            self._active_brief = None

    def _required_details(self, brief: CreativeBrief | None) -> list[str]:
        if not brief:
            return []
        required: list[str] = []
        if brief.constraints:
            required.extend(self._extract_required_from_constraints(brief.constraints))
        details = brief.business_details
        if not details:
            return required
        hours_text = ""
        if details.hours:
            if details.hours.display:
                hours_text = details.hours.display
            else:
                hours_parts: list[str] = []
                for day in details.hours.weekly:
                    if day.closed:
                        hours_parts.append(f\"{day.day} closed\")
                        continue
                    if day.open and day.close:
                        hours_parts.append(f\"{day.day} {day.open}-{day.close}\")
                    elif day.open:
                        hours_parts.append(f\"{day.day} {day.open}\")
                if details.hours.notes:
                    hours_parts.append(details.hours.notes)
                hours_text = \"; \".join(hours_parts)
        for value in [
            details.name,
            details.address,
            details.city,
            details.state,
            details.postal_code,
            details.phone,
            details.website,
            hours_text,
            details.service_area,
        ]:
            if value:
                required.append(value)
        return required

    def _extract_required_from_constraints(self, constraints: list[str]) -> list[str]:
        required: list[str] = []
        for item in constraints:
            text = item.strip()
            if not text:
                continue
            lower = text.lower()
            if "include" not in lower:
                continue
            if "'" in text:
                parts = text.split("'")
                for idx in range(1, len(parts), 2):
                    phrase = parts[idx].strip()
                    if phrase:
                        required.append(phrase)
                continue
            if ":" in text:
                _, value = text.split(":", 1)
                value = value.strip()
                if value:
                    required.append(value)
                continue
        return required

    def _business_name(self, brief: CreativeBrief) -> str:
        if brief.business_details and brief.business_details.name:
            return brief.business_details.name
        return "Unknown Business"
