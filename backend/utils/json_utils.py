from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from google.genai import types


def extract_json_object(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def safe_extract_json(text: str) -> Optional[dict]:
    try:
        return json.loads(extract_json_object(text))
    except Exception:
        return None


def get_parts(resp: types.GenerateContentResponse) -> list:
    try:
        cand = resp.candidates[0]
        content = getattr(cand, "content", None)
        return getattr(content, "parts", None) or []
    except Exception:
        return []


def get_text_from_parts(resp: types.GenerateContentResponse) -> str:
    texts: List[str] = []
    for p in get_parts(resp):
        t = getattr(p, "text", None)
        if t:
            texts.append(t)
    return "\n".join(texts).strip()
