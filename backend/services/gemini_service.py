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
- ใช้ข้อมูลที่มีอยู่ (ถ้าไม่มีข้อมูลบางอย่างก็ไม่เป็นไร)
- ถ้ามีแค่ destination ก็ตั้งชื่อตาม destination ได้เลย

ตัวอย่างชื่อที่ดี:
- เที่ยวโอซาก้าชิล ๆ 3 คืน
- ทริปครอบครัวภูเก็ตริมทะเล
- เกียวโตใบไม้แดง สบาย ๆ
- โตเกียวสายกิน งบกลาง
- ทริปญี่ปุ่น 5 วัน
- ไปเที่ยวเกาหลี
- ฮ่องกง 3 คืน

ตอบกลับเป็น "ข้อความล้วน" เท่านั้น (ไม่มีเครื่องหมายคำพูด ไม่มี markdown)
"""

CHOICE_TAGS_SYSTEM_PROMPT = """
คุณคือผู้ช่วยสร้างแท็ก (tags) สำหรับช้อยส์ทริปท่องเที่ยว
วิเคราะห์ข้อมูลช้อยส์และสร้างแท็กที่เหมาะสม

กติกา:
- ภาษาไทย
- สั้น กระชับ (1-2 คำ)
- ไม่ต้องใส่อีโมจิ
- ส่งกลับเป็น JSON array ของ strings เท่านั้น

แท็กที่ใช้ได้:
- "บินตรง" (ถ้าเป็น non-stop flight)
- "ถูกสุด" (ถ้าราคาถูกที่สุด)
- "Hot Deal" (ถ้าราคาดีมาก)
- "เร็วสุด" (ถ้าใช้เวลาน้อยที่สุด)
- "คุ้มค่า" (ถ้าราคาและคุณภาพสมดุล)
- "พรีเมียม" (ถ้าแพ็กเกจหรู)
- "แนะนำ" (ถ้าเป็น choice แรกหรือดีมาก)

ตัวอย่าง:
Input: {"is_non_stop": true, "total_price": 15000, "choice_id": 1, "is_cheapest": true}
Output: ["บินตรง", "ถูกสุด", "Hot Deal"]

Input: {"is_non_stop": false, "total_price": 25000, "choice_id": 2, "is_fastest": true}
Output: ["เร็วสุด", "คุ้มค่า"]

ตอบกลับเป็น JSON array เท่านั้น (ไม่มี markdown, ไม่มีข้อความอื่น)
"""


def generate_choice_tags(choice_data: Dict[str, Any], all_choices: List[Dict[str, Any]]) -> List[str]:
    """
    Generate tags for a choice based on its characteristics
    Returns list of tag strings like ["บินตรง", "ถูกสุด", "Hot Deal"]
    """
    try:
        # Analyze choice characteristics
        is_non_stop = choice_data.get("is_non_stop", False)
        choice_id = choice_data.get("id", 0)
        total_price = choice_data.get("total_price")
        
        # Compare with other choices
        is_cheapest = False
        is_fastest = False
        if all_choices and total_price is not None:
            prices = [c.get("total_price") for c in all_choices if c.get("total_price") is not None]
            if prices:
                is_cheapest = total_price == min(prices)
            
            # Check if fastest (non-stop and shortest duration)
            non_stop_choices = [c for c in all_choices if c.get("is_non_stop", False)]
            if non_stop_choices:
                is_fastest = is_non_stop and choice_id == min([c.get("id", 999) for c in non_stop_choices])
        
        payload = {
            "is_non_stop": is_non_stop,
            "total_price": total_price,
            "choice_id": choice_id,
            "is_cheapest": is_cheapest,
            "is_fastest": is_fastest,
            "is_recommended": (choice_id == 1),
        }
        
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": CHOICE_TAGS_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for more consistent tags
                max_output_tokens=100,
            ),
        )
        txt = get_text_from_parts(resp).strip()
        data = safe_extract_json(txt)
        
        if isinstance(data, list):
            # Filter valid tags
            valid_tags = []
            for tag in data:
                if isinstance(tag, str) and tag.strip():
                    valid_tags.append(tag.strip())
            return valid_tags[:5]  # Limit to 5 tags
        
        # Fallback: generate tags based on logic
        tags = []
        if is_non_stop:
            tags.append("บินตรง")
        if is_cheapest:
            tags.append("ถูกสุด")
        if is_cheapest and total_price and total_price < 20000:
            tags.append("Hot Deal")
        if is_fastest:
            tags.append("เร็วสุด")
        if choice_id == 1:
            tags.append("แนะนำ")
        
        return tags[:5]
    except Exception:
        # Fallback: simple logic-based tags
        tags = []
        if choice_data.get("is_non_stop", False):
            tags.append("บินตรง")
        if choice_data.get("id", 0) == 1:
            tags.append("แนะนำ")
        return tags


def generate_trip_title(travel_slots: Dict[str, Any]) -> Optional[str]:
    """
    Generate trip title using Gemini AI.
    Returns None if generation fails (silent failure for non-critical feature).
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Validate required fields
        if not travel_slots:
            logger.warning("generate_trip_title: travel_slots is None or empty")
            return None
        
        destination = travel_slots.get("destination")
        if not destination:
            logger.warning(f"generate_trip_title: No destination in travel_slots: {travel_slots}")
            return None
        
        payload = {
            "origin": travel_slots.get("origin"),
            "destination": destination,
            "start_date": travel_slots.get("start_date"),
            "nights": travel_slots.get("nights"),
            "style": travel_slots.get("style"),
            "budget_level": travel_slots.get("budget_level"),
            "adults": travel_slots.get("adults"),
            "children": travel_slots.get("children"),
            "area_preference": travel_slots.get("area_preference"),
        }
        
        logger.info(f"generate_trip_title: Attempting to generate title for destination={destination}, payload={payload}")
        
        client = get_gemini_client()
        if not client:
            logger.error("generate_trip_title: Gemini client is None - check GEMINI_API_KEY")
            return None
        
        logger.debug(f"generate_trip_title: Calling Gemini API with model={GEMINI_MODEL_NAME}")
        resp = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": TRIP_TITLE_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        
        if not resp:
            logger.warning("generate_trip_title: Gemini API returned None response")
            return None
        
        title = get_text_from_parts(resp).strip()
        if not title:
            logger.warning(f"generate_trip_title: Extracted title is empty, raw response: {resp}")
            return None
        
        logger.debug(f"generate_trip_title: Raw title from Gemini: '{title}'")
        
        # Clean up title
        title = re.sub(r'["""\']', "", title).strip()
        title = re.sub(r"\s+", " ", title).strip()
        
        # Limit length
        final_title = title[:60] if title else None
        
        if final_title:
            logger.info(f"generate_trip_title: Successfully generated title: '{final_title}'")
        else:
            logger.warning(f"generate_trip_title: Title became empty after cleanup")
        
        return final_title
    except Exception as e:
        # Log error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Trip title generation failed: {type(e).__name__}: {str(e)}", exc_info=True)
        return None


SLOT_SYSTEM_PROMPT = """
You are an intelligent slot-extraction engine for a Thai travel agent.
Your goal is to extract travel information from user messages with 100% accuracy.

Return ONLY valid JSON. No markdown. No extra text.

IMPORTANT:
- DO NOT ask user anything.
- Extract/merge slots only.
- Be smart and understand context, synonyms, and variations.
- ✅ Support Correction/Modification: If user corrects previous info (e.g., "เปลี่ยนใจไป X", "ไม่เอา Y แล้ว เอา Z แทน", "Actually, make it X"), extract the NEW value and overwrite the old one.
- ✅ Return only fields mentioned in current message: If user only mentions destination, return only destination (don't output null for other fields, just omit them).

Output schema EXACTLY:
{
  "updated_slots": {
    "origin": null|string,
    "destination": null|string,
    "start_date": null|string,
    "nights": null|number,
    "adults": null|number,
    "children": null|number,
    "destination_segments": null|array<string>,
    "cabin_class": null|string,
    "prefer_direct": null|boolean,
    "max_stops": null|number,
    "prefer_fast": null|boolean,
    "max_waiting_time": null|number,
    "baggage_quantity": null|number,
    "baggage_weight": null|number,
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
   - IMPORTANT: "3 ผู้ใหญ่ 2 เด็ก" = adults=3, children=2 (total 5 people, NOT 4)
   - Handle variations: "ครอบครัว 4 คน" = infer adults + children (but if explicit numbers given, use them exactly)
   - If user says "3 ผู้ใหญ่ 2 เด็ก", extract adults=3, children=2 (do NOT infer as 4 people)
   - If only total mentioned, try to infer from context

5. DESTINATION_SEGMENTS (Multi-destination):
   - Extract from: "ไป A แล้วไป B", "A แล้วต่อ B", "A → B → C"
   - Examples: "ไปโตเกียวแล้วไปโอซาก้า" → destination="โตเกียว", destination_segments=["โอซาก้า"]
   - Examples: "กรุงเทพ ไป โตเกียว แล้วไป โอซาก้า" → origin="กรุงเทพ", destination="โตเกียว", destination_segments=["โอซาก้า"]
   - Store additional destinations in destination_segments array

6. CABIN_CLASS (ชนิดที่นั่ง):
   - Extract from: "อีโคโนมี" → "ECONOMY"
   - Extract from: "พรีเมียม", "พรีเมียม อีโคโนมี" → "PREMIUM_ECONOMY"
   - Extract from: "บิสเนส", "ธุรกิจ" → "BUSINESS"
   - Extract from: "เฟิร์ส", "เฟิร์สคลาส" → "FIRST"
   - Valid values: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST

7. FLIGHT_PREFERENCES:
   - prefer_direct: Extract from "บินตรง", "ไม่ต่อเครื่อง", "direct", "non-stop" → true
   - max_stops: Extract from "ต่อเครื่อง 1 ครั้ง", "max 1 stop" → 1, "ไม่ต่อเครื่อง" → 0
   - prefer_fast: Extract from "เร็ว", "เร็วที่สุด", "fast", "เร็วที่สุด" → true
   - max_waiting_time: Extract from "รอไม่เกิน X ชั่วโมง", "รอสั้น", "short layover" → minutes

8. BAGGAGE:
   - baggage_quantity: Extract from "X กระเป๋า", "X bags", "X pieces" → number
   - baggage_weight: Extract from "X กิโล", "X kg", "X โล" → number (kg)
   - Examples: "2 กระเป๋า 23 กิโล" → baggage_quantity=2, baggage_weight=23

9. AREA_PREFERENCE:
   - Extract from: "พัก X", "ที่ X", "ใน X", "แถว X"
   - Examples: "พักโอซาก้า" → area_preference="โอซาก้า"
   - Examples: "พักป่าตอง" → area_preference="ป่าตอง"
   - Use when destination is broad (country) and user specifies a city/area

10. BUDGET_LEVEL:
   - Extract from: "ถูก", "ประหยัด" → "budget"
   - Extract from: "ปกติ", "กลาง" → "normal"
   - Extract from: "แพง", "หรู" → "luxury"
   - If not mentioned, leave null

11. STYLE:
   - Extract from: "ชิล", "สบาย" → "chill"
   - Extract from: "เร็ว", "เร่งด่วน" → "fast"
   - Extract from: "ผจญภัย" → "adventure"
   - If not mentioned, leave null

12. CONTEXT UNDERSTANDING:
   - "ฉันจะไป..." = future plan, extract all details
   - "อยากไป..." = desire, extract destination and preferences
   - "ไปเที่ยว..." = travel intent, extract all details
   - Understand implicit information from context

13. MERGING:
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

- "ไปโตเกียวแล้วไปโอซาก้าจากกรุงเทพ วันที่ 25 ธ.ค. 7 คืน 2 ผู้ใหญ่ บินตรง"
  → origin="กรุงเทพ", destination="โตเกียว", destination_segments=["โอซาก้า"], start_date="2024-12-25", nights=7, adults=2, prefer_direct=true

- "ไปญี่ปุ่นบิสเนส 2 กระเป๋า 32 กิโล ต่อเครื่องไม่เกิน 1 ครั้ง"
  → destination="ญี่ปุ่น", cabin_class="BUSINESS", baggage_quantity=2, baggage_weight=32, max_stops=1

- "ไปภูเก็ตเร็วที่สุด บินตรง 1 กระเป๋า 20 กิโล"
  → destination="ภูเก็ต", prefer_fast=true, prefer_direct=true, baggage_quantity=1, baggage_weight=20

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
            # ✅ Only update fields that are explicitly mentioned (not None, not empty)
            # Preserve existing values if new message doesn't mention them
            for k, v in upd.items():
                if v is not None and v != "":
                    merged[k] = v
                # ✅ If v is None or empty, keep existing value (don't overwrite)
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
    """
    Convert location name to IATA code using Gemini.
    Handles common abbreviations like "LA" -> "LAX" (Los Angeles).
    """
    """Synchronous helper used by asyncio.to_thread in services.
    
    ✅ Enhanced with Google Maps: Uses Google Maps to get better location context
    before asking Gemini, improving IATA code accuracy.

    Returns a dict with keys: input, iata, name_en, reason.
    """
    location_text = (text or "").strip()
    payload = {"location": location_text}
    
    # ✅ Step 1: Try to enhance location with Google Maps (with timeout)
    enhanced_info = None
    try:
        from services.google_maps_service import enhance_location_for_iata
        # ✅ Limit Google Maps enhancement to 8 seconds max
        enhanced_info = enhance_location_for_iata(location_text, timeout_sec=8.0)
    except Exception:
        pass  # If Google Maps fails, continue with original text
    
    # ✅ Step 2: Build enhanced payload with Google Maps context
    if enhanced_info:
        payload["location"] = location_text
        payload["google_maps_context"] = {
            "formatted_address": enhanced_info.get("geocoded", {}).get("formatted_address"),
            "city": enhanced_info.get("suggested_city"),
            "country": enhanced_info.get("suggested_country"),
            "nearby_airports": [
                {"name": a.get("name")} for a in enhanced_info.get("nearby_airports", [])[:3]
            ],
        }
    
    try:
        # ✅ Step 3: Ask Gemini with enhanced context
        enhanced_prompt = IATA_SYSTEM_PROMPT
        if enhanced_info:
            enhanced_prompt += "\n\nAdditional context from Google Maps (use this to improve accuracy):\n"
            enhanced_prompt += json.dumps(payload.get("google_maps_context", {}), ensure_ascii=False, indent=2)
        
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": enhanced_prompt}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        txt = get_text_from_parts(resp)
        data = safe_extract_json(txt)
        if isinstance(data, dict):
            # normalize
            out = {
                "input": data.get("input") or location_text,
                "iata": data.get("iata"),
                "name_en": data.get("name_en"),
                "reason": data.get("reason") or "ok",
            }
            if isinstance(out["iata"], str):
                out["iata"] = out["iata"].strip().upper()
            if out["iata"] == "":
                out["iata"] = None
            
            # ✅ Add Google Maps enhancement info to reason if available
            if enhanced_info and out.get("iata"):
                out["reason"] = f"{out.get('reason', 'ok')} (enhanced with Google Maps)"
            
            return out
        return {"input": location_text, "iata": None, "name_en": None, "reason": "non_json"}
    except Exception as e:
        return {"input": location_text, "iata": None, "name_en": None, "reason": f"exception:{e}"}


ITINERARY_SYSTEM_PROMPT = """
คุณคือผู้เชี่ยวชาญการวางแผนทริปท่องเที่ยวที่ฉลาดและสมจริง
สร้าง Day-by-Day Itinerary ที่อิงจากข้อมูลจริงที่ให้มา

กติกา:
- ภาษาไทย
- สร้าง itinerary ที่สมจริงและปฏิบัติได้จริง
- อิงจากข้อมูลเที่ยวบิน, ที่พัก, และการขนส่งที่ให้มา
- แนะนำสถานที่ท่องเที่ยวที่เหมาะสมกับแต่ละเมืองและสไตล์การท่องเที่ยว
- พิจารณาเวลาเดินทางและระยะเวลาที่พักในแต่ละเมือง
- แบ่งกิจกรรมตามวันอย่างสมเหตุสมผล (3-5 กิจกรรมต่อวัน)
- ใช้ชื่อเมืองจริงจากข้อมูล (เช่น IATA codes: NRT=โตเกียว, KIX=โอซาก้า, BKK=กรุงเทพ)

Output schema EXACTLY (JSON only, no markdown):
{
  "days": [
    {
      "day": 1,
      "title": "ชื่อวัน (เช่น 'เดินทางถึงโตเกียว' หรือ 'เที่ยวโอซาก้า')",
      "items": [
        "กิจกรรมที่ 1 (สั้น กระชับ 1-2 ประโยค)",
        "กิจกรรมที่ 2",
        "กิจกรรมที่ 3",
        "กิจกรรมที่ 4 (ถ้ามี)"
      ]
    }
  ]
}

คำแนะนำการสร้าง itinerary:
1. วันแรก (Day 1):
   - เริ่มจากเวลาเที่ยวบินถึง (arrive_time)
   - กิจกรรมเบาๆ: ถึงสนามบิน → เดินทางเข้าเมือง → เช็คอินโรงแรม
   - กิจกรรมช่วงเย็น: เดินเล่นย่านใกล้โรงแรม, อาหารเย็น, พักผ่อน
   - พิจารณา jet lag ถ้าเป็นเที่ยวบินข้ามทวีป

2. วันกลาง (Day 2 ถึง วันสุดท้าย-1):
   - กิจกรรมท่องเที่ยวหลัก: สถานที่สำคัญ, พิพิธภัณฑ์, วัด, ธรรมชาติ
   - อาหาร: อาหารท้องถิ่น, ร้านดัง, ตลาด
   - ช้อปปิ้ง: ย่านช้อปปิ้ง, ของฝาก
   - พิจารณาสไตล์การท่องเที่ยว (chill=สบายๆ, adventure=ผจญภัย, etc.)
   - ถ้ามีหลายเมือง: แบ่งกิจกรรมตามเมืองที่พักในแต่ละวัน

3. วันสุดท้าย:
   - เช็คเอาท์จากโรงแรม
   - กิจกรรมเบาๆ หรือช้อปปิ้งของฝาก (ถ้ามีเวลา)
   - เดินทางไปสนามบิน
   - พิจารณาเวลาเที่ยวบินออก (depart_time)

4. การขนส่งระหว่างเมือง:
   - ถ้ามีหลาย segments: พิจารณาเวลาเดินทางระหว่างเมือง
   - ใช้ข้อมูลการขนส่งที่มี (รถไฟ, รถบัส, เรือ) ในการวางแผน
   - แนะนำวิธีการเดินทางที่เหมาะสม

5. สถานที่ท่องเที่ยว:
   - แนะนำสถานที่ที่เหมาะสมกับเมืองนั้นๆ
   - พิจารณา budget_level (budget=ฟรี/ถูก, luxury=หรูหรา)
   - พิจารณา style (chill=สบายๆ, fast=เร่งด่วน, adventure=ผจญภัย)

6. ครอบครัว:
   - ถ้ามี children: แนะนำกิจกรรมที่เหมาะกับเด็ก
   - พิจารณาเวลาและความเหนื่อยล้า

สำคัญ: สร้าง itinerary ที่สมจริงและทำได้จริง ไม่ควรมีกิจกรรมมากเกินไปใน 1 วัน
"""


def generate_smart_itinerary_with_gemini(
    choice_data: Dict[str, Any],
    travel_slots: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    สร้าง Day-by-Day Itinerary ที่ฉลาดและสมจริงโดยใช้ Gemini
    อิงจากข้อมูลเที่ยวบิน, ที่พัก, และการขนส่งจริง
    """
    try:
        # สร้างข้อมูลสำหรับ Gemini
        flight_obj = choice_data.get("flight", {})
        hotel_obj = choice_data.get("hotel", {})
        transport_obj = choice_data.get("transport", {})
        
        flight_segments = flight_obj.get("segments", []) if isinstance(flight_obj, dict) else []
        hotel_segments = hotel_obj.get("segments", []) if isinstance(hotel_obj, dict) and hotel_obj.get("segments") else None
        transport_segments = transport_obj.get("segments", []) if isinstance(transport_obj, dict) else []
        
        # สร้างข้อมูลสรุปสำหรับ Gemini (ละเอียดมากขึ้น)
        itinerary_context = {
            "travel_info": {
                "origin": travel_slots.get("origin"),
                "destination": travel_slots.get("destination"),
                "start_date": travel_slots.get("start_date"),
                "nights": travel_slots.get("nights"),
                "adults": travel_slots.get("adults"),
                "children": travel_slots.get("children"),
                "style": travel_slots.get("style"),  # chill, fast, adventure, etc.
                "budget_level": travel_slots.get("budget_level"),  # budget, normal, luxury
                "area_preference": travel_slots.get("area_preference"),  # เมือง/ย่านที่ต้องการ
            },
            "flight_segments": [
                {
                    "segment_number": i + 1,
                    "from_city": seg.get("from"),
                    "to_city": seg.get("to"),
                    "depart_time": seg.get("depart_time"),
                    "arrive_time": seg.get("arrive_time"),
                    "arrive_plus": seg.get("arrive_plus"),  # +1 day if applicable
                    "duration": seg.get("duration"),  # flight duration
                }
                for i, seg in enumerate(flight_segments)
            ],
            "hotel_segments": (
                [
                    {
                        "segment_number": i + 1,
                        "city_code": seg.get("cityCode"),
                        "hotel_name": seg.get("hotelName"),
                        "nights": seg.get("nights"),
                        "board_type": seg.get("boardType"),  # breakfast, half board, etc.
                    }
                    for i, seg in enumerate(hotel_segments)
                ]
                if hotel_segments
                else [
                    {
                        "segment_number": 1,
                        "city_code": hotel_obj.get("cityCode"),
                        "hotel_name": hotel_obj.get("hotelName"),
                        "nights": hotel_obj.get("nights"),
                        "board_type": hotel_obj.get("boardType"),
                    }
                ]
            ),
            "transport_options": [
                {
                    "segment_number": seg.get("segment"),
                    "from_city": seg.get("from"),
                    "to_city": seg.get("to"),
                    "available_transport": {
                        "train": seg.get("train", {}).get("available", False),
                        "bus": seg.get("bus", {}).get("available", False),
                        "ferry": seg.get("ferry", {}).get("available", False),
                    },
                    "train_info": (
                        seg.get("train", {}).get("data", [{}])[0]
                        if seg.get("train", {}).get("data")
                        else None
                    ),
                    "bus_info": (
                        seg.get("bus", {}).get("data", [{}])[0]
                        if seg.get("bus", {}).get("data")
                        else None
                    ),
                    "ferry_info": (
                        seg.get("ferry", {}).get("data", [{}])[0]
                        if seg.get("ferry", {}).get("data")
                        else None
                    ),
                }
                for seg in transport_segments
            ],
        }
        
        # เรียกใช้ Gemini (with timeout protection)
        try:
            resp = get_gemini_client().models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=[
                    {"role": "user", "parts": [{"text": ITINERARY_SYSTEM_PROMPT}]},
                    {"role": "user", "parts": [{"text": json.dumps(itinerary_context, ensure_ascii=False, indent=2)}]},
                ],
                config=types.GenerateContentConfig(
                    temperature=0.7,  # Creative but consistent
                    max_output_tokens=2000,  # Limit output size
                ),
            )
            
            txt = get_text_from_parts(resp)
            data = safe_extract_json(txt)
            
            if isinstance(data, dict) and "days" in data:
                days = data.get("days", [])
                if isinstance(days, list) and len(days) > 0:
                    # Validate days structure
                    valid_days = []
                    for day in days:
                        if isinstance(day, dict) and "day" in day and "title" in day and "items" in day:
                            # Ensure items is a list
                            if isinstance(day["items"], list):
                                valid_days.append(day)
                    if len(valid_days) > 0:
                        return valid_days
        except Exception as gemini_error:
            # Log error but don't fail - will use fallback
            pass
        
        # Fallback: ถ้า Gemini ไม่ได้ผลลัพธ์ที่ถูกต้อง
        return None
    except Exception as e:
        # ถ้าเกิด error ให้ return None เพื่อใช้ fallback
        return None
