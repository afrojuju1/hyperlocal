from __future__ import annotations

import base64
import json
import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from openai import OpenAI


@dataclass
class ImageResult:
    path: str
    revised_prompt: str | None = None


def build_client(*, base_url: str | None = None, api_key: str | None = None) -> OpenAI:
    kwargs: dict[str, Any] = {}
    if base_url:
        kwargs["base_url"] = base_url.rstrip("/")
    if api_key:
        kwargs["api_key"] = api_key
    return OpenAI(**kwargs)


def encode_image_data(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def image_url_from_path(image_path: str, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{encode_image_data(image_path)}"


def chat_content(
    client: OpenAI, model: str, messages: list[dict[str, Any]]
) -> str:
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content or ""


CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _parse_json_like(content: str):
    content = content.strip()
    content = content.replace("```json", "").replace("```", "").strip()
    content = CONTROL_CHARS.sub("", content)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for idx, ch in enumerate(content):
            if ch not in "{[":
                continue
            try:
                obj, _ = decoder.raw_decode(content[idx:])
                return obj
            except json.JSONDecodeError:
                continue

        start = min(
            (pos for pos in (content.find("{"), content.find("[")) if pos != -1),
            default=-1,
        )
        end = max(content.rfind("}"), content.rfind("]"))
        if start != -1 and end != -1 and end > start:
            snippet = content[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                try:
                    return ast.literal_eval(snippet)
                except (ValueError, SyntaxError):
                    pass
        try:
            return ast.literal_eval(content)
        except (ValueError, SyntaxError):
            return None

def chat_json(
    client: OpenAI, model: str, messages: list[dict[str, Any]]
) -> Any:
    content = chat_content(client, model, messages)
    parsed = _parse_json_like(content)
    if parsed is not None:
        return parsed

    repair_prompt = (
        "Fix the following into valid JSON. Return JSON only, no commentary. "
        "Ensure keys/values are properly quoted.\n\n"
        + content
    )
    repaired = chat_content(client, model, messages=[{"role": "user", "content": repair_prompt}])
    parsed = _parse_json_like(repaired)
    if parsed is not None:
        return parsed
    raise json.JSONDecodeError("Failed to parse JSON from model output", content, 0)


def generate_image(
    client: OpenAI,
    prompt: str,
    output_path: str,
    model: str = "gpt-image-1",
    size: str = "1024x1536",
    quality: str = "high",
    background: str = "opaque",
) -> ImageResult:
    response = client.images.generate(
        model=model,
        prompt=prompt,
        size=size,
        quality=quality,
        background=background,
    )
    image_data = response.data[0].b64_json
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(base64.b64decode(image_data))
    revised_prompt = getattr(response.data[0], "revised_prompt", None)
    return ImageResult(path=output_path, revised_prompt=revised_prompt)
