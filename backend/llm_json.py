import json
from typing import Any, Dict, Optional
from llm_gemini_cli import gemini_cli_generate

def safe_extract_json(text: str) -> Optional[dict]:
    # ใช้ของเดิมคุณก็ได้ อันนี้สั้นๆ
    text = (text or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(text[start:end+1])
    except Exception:
        return None

def gemini_cli_generate_json(
    system_prompt: str,
    payload: Dict[str, Any],
    *,
    model: str,
    timeout_s: int = 60,
) -> Dict[str, Any]:
    prompt = (
        "SYSTEM:\n"
        f"{system_prompt}\n\n"
        "USER:\n"
        f"{json.dumps(payload, ensure_ascii=False)}\n\n"
        "ABSOLUTE: Output ONLY one valid JSON object. No markdown. No extra text."
    )

    raw = gemini_cli_generate(prompt, model=model, timeout_s=timeout_s, sandbox=True)
    data = safe_extract_json(raw)
    if not isinstance(data, dict):
        # fallback ให้ไม่พังทั้งระบบ
        return {"_raw": raw, "_parse_error": True}
    return data
