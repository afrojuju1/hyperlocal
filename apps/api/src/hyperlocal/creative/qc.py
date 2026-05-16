from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from openai import OpenAI
from PIL import Image

from hyperlocal.creative.vertical_config import vertical_qc_config
from hyperlocal.integrations.openai import chat_content, image_url_from_path


_DEFAULT_TEXT_SCORE_THRESHOLD = 34.0
_DEFAULT_CALM_ZONE_SCORE_THRESHOLD = 88.0


@dataclass(frozen=True)
class BackgroundQcResult:
    passed: bool
    score: float
    reasons: list[str]
    metrics: dict[str, Any]

    def model_dump(self) -> dict[str, Any]:
        return asdict(self)


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


def evaluate_background_image(
    *,
    image_path: str | Path,
    business_kind: str,
) -> BackgroundQcResult:
    """Cheap deterministic QC for text-free source images before typography rendering."""
    cfg = vertical_qc_config(business_kind)
    text_threshold = float(cfg.get("text_score_threshold", _DEFAULT_TEXT_SCORE_THRESHOLD))
    calm_threshold = float(cfg.get("calm_zone_score_threshold", _DEFAULT_CALM_ZONE_SCORE_THRESHOLD))

    base = Image.open(image_path).convert("RGB")
    text_score = _text_artifact_score(base)
    calm_metrics = _calm_zone_metrics(base)
    calm_score = float(calm_metrics["best_score"])

    reasons: list[str] = []
    if text_score > text_threshold:
        reasons.append("possible_background_text")
    if calm_score > calm_threshold:
        reasons.append("no_calm_typography_zone")

    score = round(text_score + max(0.0, calm_score - calm_threshold), 3)
    metrics: dict[str, Any] = {
        "text_score": round(text_score, 3),
        "text_score_threshold": text_threshold,
        "best_calm_zone_score": round(calm_score, 3),
        "calm_zone_score_threshold": calm_threshold,
        **calm_metrics,
    }
    return BackgroundQcResult(
        passed=not reasons,
        score=score,
        reasons=reasons,
        metrics=metrics,
    )


def build_retry_prompt(
    *,
    prompt: str,
    business_kind: str,
    qc_result: BackgroundQcResult,
) -> str:
    cfg = vertical_qc_config(business_kind)
    retry_append = str(cfg.get("retry_prompt_append") or "").strip()
    reason_guidance = _retry_reason_guidance(qc_result.reasons)
    return " ".join(part for part in [prompt, retry_append, reason_guidance] if part).strip()


def build_retry_negative_prompt(
    *,
    negative_prompt: str,
    business_kind: str,
    qc_result: BackgroundQcResult,
) -> str:
    cfg = vertical_qc_config(business_kind)
    retry_append = str(cfg.get("retry_negative_append") or "").strip()
    reason_guidance = _retry_reason_negative_guidance(qc_result.reasons)
    return " ".join(part for part in [negative_prompt, retry_append, reason_guidance] if part).strip()


def _retry_reason_guidance(reasons: list[str]) -> str:
    parts: list[str] = []
    if "possible_background_text" in reasons:
        parts.append(
            "Remove all text-like shapes: signs, labels, logos, numbers, letters, decals, badges, screens, menus, and decorative glyph marks."
        )
    if "no_calm_typography_zone" in reasons:
        parts.append(
            "Simplify the composition with a calmer open area of plain wall, sky, counter, floor, or soft background texture."
        )
    return " ".join(parts)


def _retry_reason_negative_guidance(reasons: list[str]) -> str:
    parts: list[str] = []
    if "possible_background_text" in reasons:
        parts.append(
            "No text-like strokes, no glyph clusters, no readable or pseudo-readable markings, no numbers, no lettering."
        )
    if "no_calm_typography_zone" in reasons:
        parts.append("No high-detail clutter across the entire frame, no dense patterns in every possible text area.")
    return " ".join(parts)


def _calm_zone_metrics(base: Image.Image) -> dict[str, Any]:
    candidate_boxes = [
        {"x": 0.08, "y": 0.06, "width": 0.84, "height": 0.16},
        {"x": 0.08, "y": 0.22, "width": 0.84, "height": 0.16},
        {"x": 0.08, "y": 0.38, "width": 0.84, "height": 0.16},
        {"x": 0.08, "y": 0.58, "width": 0.84, "height": 0.16},
        {"x": 0.08, "y": 0.74, "width": 0.84, "height": 0.16},
    ]
    scored = [
        {
            **box,
            "score": round(_zone_score(base=base, box=box), 3),
        }
        for box in candidate_boxes
    ]
    best = min(scored, key=lambda item: float(item["score"]))
    return {
        "best_calm_zone": best,
        "best_score": float(best["score"]),
        "candidate_zones": scored,
    }


def _zone_score(*, base: Image.Image, box: dict[str, float]) -> float:
    w, h = base.size
    x0 = int(w * box["x"])
    y0 = int(h * box["y"])
    x1 = int(w * (box["x"] + box["width"]))
    y1 = int(h * (box["y"] + box["height"]))
    x0 = max(0, min(w - 1, x0))
    y0 = max(0, min(h - 1, y0))
    x1 = max(x0 + 1, min(w, x1))
    y1 = max(y0 + 1, min(h, y1))
    crop = base.crop((x0, y0, x1, y1)).convert("L").resize((48, 48))
    px = crop.load()
    values = [px[x, y] for y in range(48) for x in range(48)]
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)

    edge_total = 0
    edge_count = 0
    for y in range(48):
        for x in range(47):
            edge_total += abs(px[x, y] - px[x + 1, y])
            edge_count += 1
    for y in range(47):
        for x in range(48):
            edge_total += abs(px[x, y] - px[x, y + 1])
            edge_count += 1
    edge = edge_total / max(1, edge_count)
    return (variance ** 0.5) + (edge * 1.5)


def _text_artifact_score(base: Image.Image) -> float:
    width = 320
    height = max(1, round(base.height * (width / base.width)))
    gray = base.convert("L").resize((width, height))
    tile_w = 20
    tile_h = 12
    textlike_tiles = 0
    total_tiles = 0
    row_counts: list[int] = []

    for y in range(0, max(1, height - tile_h + 1), tile_h):
        row_count = 0
        for x in range(0, max(1, width - tile_w + 1), tile_w):
            crop = gray.crop((x, y, min(width, x + tile_w), min(height, y + tile_h)))
            if _tile_is_textlike(crop):
                textlike_tiles += 1
                row_count += 1
            total_tiles += 1
        row_counts.append(row_count)

    if total_tiles == 0:
        return 0.0
    tiles_per_row = max(1, width // tile_w)
    density = textlike_tiles / total_tiles
    row_concentration = (max(row_counts) / tiles_per_row) if row_counts else 0.0
    return (density * 100.0) + (row_concentration * 80.0)


def _tile_is_textlike(tile: Image.Image) -> bool:
    width, height = tile.size
    px = tile.load()
    values = [px[x, y] for y in range(height) for x in range(width)]
    if not values:
        return False

    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / len(values)
    stddev = variance ** 0.5

    edge_total = 0
    edge_count = 0
    for y in range(height):
        for x in range(max(0, width - 1)):
            edge_total += abs(px[x, y] - px[x + 1, y])
            edge_count += 1
    for y in range(max(0, height - 1)):
        for x in range(width):
            edge_total += abs(px[x, y] - px[x, y + 1])
            edge_count += 1
    edge = edge_total / max(1, edge_count)

    dark_ratio = sum(1 for value in values if value < 72) / len(values)
    light_ratio = sum(1 for value in values if value > 184) / len(values)
    extreme_ratio = min(dark_ratio, light_ratio)

    return stddev > 36 and edge > 20 and 0.015 <= extreme_ratio <= 0.48
