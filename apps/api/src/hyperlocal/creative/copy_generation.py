from __future__ import annotations

import json
import re
from dataclasses import dataclass

from hyperlocal.creative.contracts import CreativeCopyInput, CreativeRunRequest
from hyperlocal.integrations.llm import build_llm_clients
from hyperlocal.integrations.openai import chat_json


_OFFER_LANGUAGE_RE = re.compile(
    r"(\b\d+\s*%|\$+\s*\d+|\boff\b|\bbuy\b|\bget\b|\bfree\b|\bsave\b|"
    r"\bsaves\b|\bsaving\b|\bsavings\b|\bdeal\b|\bdeals\b|\bdiscount\b|"
    r"\bcoupon\b|\bcoupons\b|\bless\b|\bprice\b|\bhalf[-\s]?price\b|\boffer\b|"
    r"\blimited\s+time\b|\bact\s+fast\b|"
    r"\bfor\s+\d+\s+days\b)",
    re.IGNORECASE,
)


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
            "The offer field is the only place for price, discount, coupon, free, buy/get, savings, or day-count mechanics. "
            "Do not put offer mechanics in headline, subhead, or footer. "
            "Make the headline a short campaign concept or product desire line, not a coupon phrase. "
            f"Business: {request.business.name}. "
            f"Product: {request.campaign.product}. "
            f"Offer exact phrase required in offer field: {request.campaign.offer}. "
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
            footer=request.business.name,
        )

    def _normalize(self, block: CreativeCopyInput, request: CreativeRunRequest) -> CreativeCopyInput:
        def truncate_words(text: str, limit: int) -> str:
            words = [w for w in text.split() if w]
            return " ".join(words[:limit])

        def has_offer_language(text: str) -> bool:
            return bool(_OFFER_LANGUAGE_RE.search(text or ""))

        def remove_offer_language(text: str, fallback: str, limit: int) -> str:
            candidates = [text or ""]
            for separator in (":", " - ", " | "):
                if separator in (text or ""):
                    candidates = [part.strip(" -|") for part in text.split(separator)]
                    break
            for candidate in candidates:
                candidate = candidate.strip()
                if candidate and not has_offer_language(candidate):
                    return truncate_words(candidate, limit)
            return truncate_words(fallback, limit)

        product = request.campaign.product.strip() or request.business.name
        headline_fallback = f"{product} made fresh"
        if request.campaign.business_kind == "hvac":
            subhead_fallback = "Fast local comfort service"
        else:
            subhead_fallback = "Fresh flavor, ready today"

        headline = truncate_words(block.headline or request.business.name, 7)
        subhead = truncate_words(block.subhead or request.campaign.product, 8)
        offer = truncate_words(request.campaign.offer or block.offer, 9)
        cta = truncate_words(block.cta or request.campaign.cta, 4)
        footer_source = block.footer or request.business.name
        footer = truncate_words(footer_source, 8)
        if len([w for w in footer_source.split() if w]) > 8:
            footer = request.business.name

        headline = remove_offer_language(headline, headline_fallback, 7)
        subhead = remove_offer_language(subhead, subhead_fallback, 8)
        footer = remove_offer_language(footer, request.business.name, 8)
        if request.campaign.cta and request.campaign.cta.lower() in footer.lower():
            footer = truncate_words(request.business.name, 8)

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
