from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from google.genai import types

from core.config import get_gemini_client, GEMINI_MODEL_NAME
from utils.json_utils import get_text_from_parts, safe_extract_json

TRIP_TITLE_SYSTEM_PROMPT = """
คุณคือผู้ช่วยตั้งชื่อทริปท่องเที่ยวสำหรับแอป
ตั้งชื่อสั้น กระชับ เป็นมิตร คล้ายชื่อทริปในแอปท่องเที่ยว

กติกา:
- ภาษาไทย
- ไม่เกิน 10 คำ
- ไม่ต้องใส่อีโมจิ
- ไม่ต้องใส่เครื่องหมายคำพูด
- หลีกเลี่ยงวันที่แบบตัวเลขยาว (เช่น 2025-12-26)

ตัวอย่างชื่อที่ดี:
- เที่ยวโอซาก้าชิล ๆ 3 คืน
- ทริปครอบครัวภูเก็ตริมทะเล
- เกียวโตใบไม้แดง สบาย ๆ
- โตเกียวสายกิน งบกลาง

ตอบกลับเป็น "ข้อความล้วน" เท่านั้น
"""


def generate_trip_title(travel_slots: Dict[str, Any]) -> Optional[str]:
    try:
        payload = {
            "origin": travel_slots.get("origin"),
            "destination": travel_slots.get("destination"),
            "start_date": travel_slots.get("start_date"),
            "nights": travel_slots.get("nights"),
            "style": travel_slots.get("style"),
            "budget_level": travel_slots.get("budget_level"),
            "adults": travel_slots.get("adults"),
            "children": travel_slots.get("children"),
            "area_preference": travel_slots.get("area_preference"),
        }
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": TRIP_TITLE_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        title = get_text_from_parts(resp).strip()
        title = re.sub(r'["“”\']', "", title).strip()
        title = re.sub(r"\s+", " ", title).strip()
        return title[:60] if title else None
    except Exception:
        return None


SLOT_SYSTEM_PROMPT = """
You are a slot-extraction engine for a Thai travel agent.
Return ONLY valid JSON. No markdown. No extra text.

IMPORTANT:
- DO NOT ask user anything.
- Extract/merge slots only.

Output schema EXACTLY:
{
  "updated_slots": {
    "origin": null|string,
    "destination": null|string,
    "start_date": null|string,
    "nights": null|number,
    "adults": null|number,
    "children": null|number,
    "budget_level": null|string,
    "style": null|string,
    "area_preference": null|string
  },
  "assumptions": ["string"]
}

Rules:
- Normalize start_date to ISO YYYY-MM-DD when possible.
- If date without year, pick nearest future date from today's date.
- If budget/style missing -> leave null (backend will default).
"""


def slot_extract_with_gemini(today: str, user_id: str, user_message: str, existing_travel_slots: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    payload = {
        "today": today,
        "user_id": user_id,
        "user_message": user_message,
        "existing_travel_slots": existing_travel_slots,
    }
    merged = dict(existing_travel_slots or {})
    assumptions: List[str] = []
    try:
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": SLOT_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        txt = get_text_from_parts(resp)
        data = safe_extract_json(txt)
        if data and isinstance(data, dict) and "updated_slots" in data:
            upd = data.get("updated_slots") or {}
            for k, v in upd.items():
                if v is not None and v != "":
                    merged[k] = v
            assumptions = data.get("assumptions") or []
    except Exception:
        pass
    return merged, assumptions
