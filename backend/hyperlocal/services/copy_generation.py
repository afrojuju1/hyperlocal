from __future__ import annotations

import json
from dataclasses import dataclass

from hyperlocal.contracts.creative_runs import CreativeCopyInput, CreativeRunRequest
from hyperlocal.llm_providers import build_llm_clients
from hyperlocal.openai_helpers import chat_json


@dataclass(frozen=True)
class CopyBlock:
    headline: str
    subhead: str
    offer: str
    cta: str
    footer: str

    def to_model(self) -> CreativeCopyInput:
        return CreativeCopyInput(
            headline=self.headline,
            subhead=self.subhead,
            offer=self.offer,
            cta=self.cta,
            footer=self.footer,
        )


class CopyGenerationService:
    def __init__(self) -> None:
        llm = build_llm_clients()
        self._client = llm.text_client
        self._model = llm.text_model

    def generate(self, request: CreativeRunRequest, count: int) -> list[CreativeCopyInput]:
        target = max(1, count)
        if request.overlay.copy_mode == "provided" and request.copy_input is not None:
            return [request.copy_input for _ in range(target)]

        try:
            blocks = self._generate_with_llm(request, target)
        except Exception:
            blocks = []

        if not blocks:
            blocks = [self._fallback(request) for _ in range(target)]

        if len(blocks) < target:
            fallback = self._fallback(request)
            blocks.extend([fallback for _ in range(target - len(blocks))])

        return [self._normalize(block, request) for block in blocks[:target]]

    def _generate_with_llm(self, request: CreativeRunRequest, target: int) -> list[CreativeCopyInput]:
        prompt = (
            "Return JSON array only. "
            f"Create exactly {target} ad copy blocks with keys: headline, subhead, offer, cta, footer. "
            "Rules: concise, direct-response, no emojis, no markdown. "
            "headline <= 7 words; subhead <= 8 words; offer <= 9 words; cta <= 4 words; footer <= 8 words. "
            f"Business: {request.business.name}. "
            f"Product: {request.campaign.product}. "
            f"Offer exact phrase preferred: {request.campaign.offer}. "
            f"CTA exact phrase preferred: {request.campaign.cta}. "
            f"Tone: {request.campaign.tone}. "
            f"Audience: {request.campaign.audience or 'local customers'}. "
            f"Constraints: {', '.join(request.campaign.constraints) if request.campaign.constraints else 'none'}."
        )
        raw = chat_json(self._client, self._model, [{"role": "user", "content": prompt}])
        if isinstance(raw, dict) and isinstance(raw.get("variants"), list):
            raw = raw["variants"]
        if not isinstance(raw, list):
            return []

        blocks: list[CreativeCopyInput] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            try:
                block = CreativeCopyInput(
                    headline=str(item.get("headline") or "").strip(),
                    subhead=str(item.get("subhead") or "").strip(),
                    offer=str(item.get("offer") or "").strip(),
                    cta=str(item.get("cta") or "").strip(),
                    footer=str(item.get("footer") or "").strip(),
                )
            except Exception:
                continue
            blocks.append(block)
        return blocks

    def _fallback(self, request: CreativeRunRequest) -> CreativeCopyInput:
        return CreativeCopyInput(
            headline=request.business.name,
            subhead=request.campaign.product,
            offer=request.campaign.offer,
            cta=request.campaign.cta,
            footer="Limited time offer",
        )

    def _normalize(self, block: CreativeCopyInput, request: CreativeRunRequest) -> CreativeCopyInput:
        def truncate_words(text: str, limit: int) -> str:
            words = [w for w in text.split() if w]
            return " ".join(words[:limit])

        headline = truncate_words(block.headline or request.business.name, 7)
        subhead = truncate_words(block.subhead or request.campaign.product, 8)
        offer = truncate_words(block.offer or request.campaign.offer, 9)
        cta = truncate_words(block.cta or request.campaign.cta, 4)
        footer = truncate_words(block.footer or "Limited time", 8)

        # Guarantee core business offer/cta if model drifts too far.
        if not offer:
            offer = truncate_words(request.campaign.offer, 9)
        if not cta:
            cta = truncate_words(request.campaign.cta, 4)

        return CreativeCopyInput(
            headline=headline,
            subhead=subhead,
            offer=offer,
            cta=cta,
            footer=footer,
        )

    def debug_prompt(self, request: CreativeRunRequest, count: int) -> str:
        return json.dumps(
            {
                "business": request.business.model_dump(),
                "campaign": request.campaign.model_dump(),
                "count": count,
            },
            indent=2,
        )
