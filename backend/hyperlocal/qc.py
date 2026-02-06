from __future__ import annotations

import re
from difflib import SequenceMatcher

from openai import OpenAI

from hyperlocal.openai_helpers import chat_content, image_url_from_path


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_text(client: OpenAI, model: str, image_path: str) -> str:
    prompt = (
        "Extract all visible text from this flyer image. "
        "Return only the text, preserve line breaks when possible."
    )
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": image_url_from_path(image_path)}},
            ],
        }
    ]
    return chat_content(client, model, messages).strip()


def _phrase_match(needle: str, haystack: str) -> bool:
    if not needle:
        return True
    if needle in haystack:
        return True
    ratio = SequenceMatcher(None, needle, haystack).ratio()
    return ratio >= 0.75


def validate_text(expected_phrases: list[str], ocr_text: str) -> bool:
    normalized_ocr = _normalize(ocr_text)
    for phrase in expected_phrases:
        normalized_phrase = _normalize(phrase)
        if not normalized_phrase:
            continue
        if normalized_phrase in normalized_ocr:
            continue
        if not _phrase_match(normalized_phrase, normalized_ocr):
            return False
    return True
