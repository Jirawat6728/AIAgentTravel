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
You are an intelligent slot-extraction engine for a Thai travel agent.
Your goal is to extract travel information from user messages with 100% accuracy.

Return ONLY valid JSON. No markdown. No extra text.

IMPORTANT:
- DO NOT ask user anything.
- Extract/merge slots only.
- Be smart and understand context, synonyms, and variations.

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

Extraction Rules (BE VERY SMART):

1. ORIGIN & DESTINATION:
   - Extract from patterns: "ไป X จาก Y", "จาก X ไป Y", "X ไป Y", "X → Y", "X to Y"
   - Understand synonyms: "กรุงเทพ" = "Bangkok" = "BKK", "ภูเก็ต" = "Phuket" = "HKT"
   - Handle country names: "ญี่ปุ่น" = "Japan", "เกาหลี" = "Korea"
   - If destination is a country (ญี่ปุ่น, Japan) and user mentions a city (โอซาก้า, Tokyo), use city as area_preference

2. DATES:
   - Parse Thai dates: "25 ธ.ค." = "25 ธันวาคม" = "December 25"
   - Parse formats: "25/12", "25-12", "2024-12-25", "25 Dec 2024"
   - Relative dates: "พรุ่งนี้" = tomorrow, "วันนี้" = today, "อาทิตย์หน้า" = next week
   - If no year, pick nearest future date from today
   - Normalize to ISO format: YYYY-MM-DD

3. NIGHTS:
   - Extract from: "3 คืน", "3 nights", "พัก 3 คืน", "3 วัน 2 คืน" (use nights, not days)
   - If user says "4 วัน 3 คืน", extract nights=3 (nights is more accurate)
   - If user says "4 วัน" without "คืน", calculate: nights = days - 1 (if days > 1)
   - Understand: "1 วัน" = 0 nights (day trip), "2 วัน" = 1 night

4. TRAVELERS:
   - Extract adults: "2 ผู้ใหญ่", "2 adults", "2 คน" (if context suggests adults)
   - Extract children: "1 เด็ก", "1 child", "1 kid"
   - Handle variations: "ครอบครัว 4 คน" = infer adults + children
   - If only total mentioned, try to infer from context

5. AREA_PREFERENCE:
   - Extract from: "พัก X", "ที่ X", "ใน X", "แถว X"
   - Examples: "พักโอซาก้า" → area_preference="โอซาก้า"
   - Examples: "พักป่าตอง" → area_preference="ป่าตอง"
   - Use when destination is broad (country) and user specifies a city/area

6. BUDGET_LEVEL:
   - Extract from: "ถูก", "ประหยัด" → "budget"
   - Extract from: "ปกติ", "กลาง" → "normal"
   - Extract from: "แพง", "หรู" → "luxury"
   - If not mentioned, leave null

7. STYLE:
   - Extract from: "ชิล", "สบาย" → "chill"
   - Extract from: "เร็ว", "เร่งด่วน" → "fast"
   - Extract from: "ผจญภัย" → "adventure"
   - If not mentioned, leave null

8. CONTEXT UNDERSTANDING:
   - "ฉันจะไป..." = future plan, extract all details
   - "อยากไป..." = desire, extract destination and preferences
   - "ไปเที่ยว..." = travel intent, extract all details
   - Understand implicit information from context

9. MERGING:
   - Merge with existing_slots (from previous messages)
   - Only update fields that are explicitly mentioned or can be inferred
   - Preserve existing values if new message doesn't mention them

Examples:
- "ฉันจะไปภูเก็ตจากกรุงเทพวันที่ 25 ธ.ค. พักป่าตอง 3 คืน ไป 2 ผู้ใหญ่ 1 เด็ก"
  → origin="กรุงเทพ", destination="ภูเก็ต", start_date="2024-12-25", nights=3, adults=2, children=1, area_preference="ป่าตอง"

- "ฉันจะไปญี่ปุ่นจากเชียงใหม่วันที่ 31 ธ.ค. พักโอซาก้า 4วัน 3 คืน ไป 2 ผู้ใหญ่ 1 เด็ก"
  → origin="เชียงใหม่", destination="ญี่ปุ่น", start_date="2024-12-31", nights=3, adults=2, children=1, area_preference="โอซาก้า"

- "ไปเกาหลี 5 วัน 4 คืน"
  → destination="เกาหลี", nights=4 (not 5, because nights is more specific)

Be extremely accurate and extract ALL information that can be inferred from the message.
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


# =============================================================================
# Location -> IATA (always via Gemini)
# =============================================================================

IATA_SYSTEM_PROMPT = """
You are an aviation location resolver.
Convert a location name (Thai or English) to the best matching IATA airport code (3 letters).

Rules:
- Return ONLY valid JSON. No markdown. No extra text.
- If the input is already an IATA code, return it unchanged.
- If multiple airports exist, pick the main commercial airport that best matches typical travel intent.
- If unknown, set iata to null and provide a short reason.

Output schema EXACTLY:
{
  "input": "<original>",
  "iata": "ABC" | null,
  "name_en": "<best english city/airport name>" | null,
  "reason": "<short reason>"
}
"""


def location_to_iata_with_gemini(text: str) -> Dict[str, Any]:
    """Synchronous helper used by asyncio.to_thread in services.

    Returns a dict with keys: input, iata, name_en, reason.
    """
    payload = {"location": (text or "").strip()}
    try:
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": IATA_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        txt = get_text_from_parts(resp)
        data = safe_extract_json(txt)
        if isinstance(data, dict):
            # normalize
            out = {
                "input": data.get("input") or payload["location"],
                "iata": data.get("iata"),
                "name_en": data.get("name_en"),
                "reason": data.get("reason") or "ok",
            }
            if isinstance(out["iata"], str):
                out["iata"] = out["iata"].strip().upper()
            if out["iata"] == "":
                out["iata"] = None
            return out
        return {"input": payload["location"], "iata": None, "name_en": None, "reason": "non_json"}
    except Exception as e:
        return {"input": payload["location"], "iata": None, "name_en": None, "reason": f"exception:{e}"}
