from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from services.gemini_service import get_gemini_client, GEMINI_MODEL_NAME
from utils.json_utils import get_text_from_parts, safe_extract_json
import json

TRIP_PLANNING_PROMPT = """
You are an intelligent travel planning assistant for a Thai travel agent.
Your goal is to help users plan trips from scratch by asking smart questions and suggesting destinations based on their preferences, festivals, and seasons.

Return ONLY valid JSON. No markdown. No extra text.

Output schema EXACTLY:
{
  "action": "ask_question" | "suggest_destinations" | "ready_to_search",
  "question": "string" | null,
  "suggestions": ["string"] | null,
  "missing_info": ["string"] | null,
  "festival_suggestions": [
    {
      "month": "string",
      "festival": "string",
      "destination": "string",
      "description": "string"
    }
  ] | null
}

Rules:
1. If user has NO destination or very vague request:
   - action = "ask_question"
   - Ask ONE smart question to understand their preferences
   - Focus on: budget, style (relax/chill/adventure), preferred activities, or time period

2. If user mentions a month or festival:
   - action = "suggest_destinations"
   - Provide festival_suggestions with destinations that match that month/festival
   - Include popular festivals in Thailand and nearby countries

3. If user has enough info (destination + date + travelers):
   - action = "ready_to_search"
   - question = null

4. Questions should be:
   - Natural and conversational in Thai
   - One question at a time
   - Helpful and not overwhelming

5. Festival suggestions should include:
   - Thai festivals: Songkran (April), Loy Krathong (November), etc.
   - International festivals: Cherry Blossom (Japan, March-April), etc.
   - Seasonal destinations: Beach (Nov-Feb), Mountain (Dec-Feb), etc.

Examples:
- User: "อยากไปเที่ยว" → Ask about preferences
- User: "อยากไปเที่ยวเดือนมีนาคม" → Suggest destinations for March
- User: "อยากไปดูซากุระ" → Suggest Japan destinations for cherry blossom season
"""

FESTIVAL_DESTINATIONS = {
    "มกราคม": [
        {"festival": "ตรุษจีน", "destination": "จีน, ฮ่องกง, สิงคโปร์", "description": "เทศกาลตรุษจีน งานเฉลิมฉลองใหญ่"},
        {"festival": "ฤดูหนาว", "destination": "ญี่ปุ่น, เกาหลี", "description": "อากาศหนาว หิมะตก เหมาะกับสกี"},
    ],
    "กุมภาพันธ์": [
        {"festival": "วันวาเลนไทน์", "destination": "ปารีส, เวนิส, เกาะรอมานติก", "description": "เมืองโรแมนติกสำหรับคู่รัก"},
        {"festival": "ฤดูหนาว", "destination": "ญี่ปุ่น, เกาหลี, ยุโรป", "description": "อากาศหนาว หิมะตก"},
    ],
    "มีนาคม": [
        {"festival": "ซากุระ", "destination": "ญี่ปุ่น (โตเกียว, เกียวโต, โอซาก้า)", "description": "ดอกซากุระบานเต็มที่"},
        {"festival": "ฤดูใบไม้ผลิ", "destination": "เกาหลี, ญี่ปุ่น", "description": "อากาศดี ธรรมชาติสวยงาม"},
    ],
    "เมษายน": [
        {"festival": "สงกรานต์", "destination": "ไทย (เชียงใหม่, กรุงเทพ, ภูเก็ต)", "description": "เทศกาลน้ำ สนุกสนาน"},
        {"festival": "ซากุระ", "destination": "ญี่ปุ่น (ฮอกไกโด)", "description": "ซากุระบานช้าในฮอกไกโด"},
    ],
    "พฤษภาคม": [
        {"festival": "ฤดูร้อน", "destination": "เกาะต่างๆ (ภูเก็ต, เกาะสมุย, บาหลี)", "description": "เหมาะกับทะเล ว่ายน้ำ"},
        {"festival": "Golden Week", "destination": "ญี่ปุ่น", "description": "ช่วงวันหยุดยาวของญี่ปุ่น"},
    ],
    "มิถุนายน": [
        {"festival": "ฤดูฝนเริ่มต้น", "destination": "ยุโรป, ญี่ปุ่น", "description": "อากาศดี ไม่ร้อนมาก"},
        {"festival": "ฤดูร้อน", "destination": "เกาะต่างๆ", "description": "เหมาะกับทะเล"},
    ],
    "กรกฎาคม": [
        {"festival": "ฤดูฝน", "destination": "ยุโรป, ญี่ปุ่น", "description": "อากาศดี เหมาะกับเที่ยวเมือง"},
        {"festival": "ฤดูร้อน", "destination": "เกาะต่างๆ", "description": "เหมาะกับทะเล"},
    ],
    "สิงหาคม": [
        {"festival": "ฤดูฝน", "destination": "ยุโรป, ญี่ปุ่น", "description": "อากาศดี เหมาะกับเที่ยวเมือง"},
        {"festival": "Obon Festival", "destination": "ญี่ปุ่น", "description": "เทศกาล Obon งานเฉลิมฉลอง"},
    ],
    "กันยายน": [
        {"festival": "ฤดูใบไม้ร่วงเริ่มต้น", "destination": "ญี่ปุ่น, เกาหลี", "description": "อากาศดี ธรรมชาติสวยงาม"},
        {"festival": "ฤดูฝน", "destination": "ยุโรป", "description": "อากาศดี เหมาะกับเที่ยวเมือง"},
    ],
    "ตุลาคม": [
        {"festival": "ฤดูใบไม้ร่วง", "destination": "ญี่ปุ่น, เกาหลี, ยุโรป", "description": "ใบไม้เปลี่ยนสี สวยงาม"},
        {"festival": "Oktoberfest", "destination": "เยอรมนี", "description": "เทศกาลเบียร์ใหญ่ที่สุดในโลก"},
    ],
    "พฤศจิกายน": [
        {"festival": "ลอยกระทง", "destination": "ไทย (เชียงใหม่, สุโขทัย)", "description": "เทศกาลลอยกระทง สวยงาม"},
        {"festival": "ฤดูใบไม้ร่วง", "destination": "ญี่ปุ่น, เกาหลี", "description": "ใบไม้เปลี่ยนสี สวยงาม"},
    ],
    "ธันวาคม": [
        {"festival": "คริสต์มาส", "destination": "ยุโรป, ญี่ปุ่น, สิงคโปร์", "description": "บรรยากาศคริสต์มาส สวยงาม"},
        {"festival": "ปีใหม่", "destination": "ญี่ปุ่น, เกาหลี, ยุโรป", "description": "เฉลิมฉลองปีใหม่"},
        {"festival": "ฤดูหนาว", "destination": "ญี่ปุ่น, เกาหลี, ยุโรป", "description": "อากาศหนาว หิมะตก"},
    ],
}


def get_missing_slots(slots: Dict[str, Any]) -> List[str]:
    """Identify which critical slots are missing."""
    missing = []
    if not slots.get("destination"):
        missing.append("destination")
    if not slots.get("start_date"):
        missing.append("start_date")
    if slots.get("adults") is None:
        missing.append("adults")
    return missing


def plan_trip_from_scratch(
    user_message: str,
    existing_slots: Dict[str, Any],
    today: str,
) -> Dict[str, Any]:
    """
    Intelligent trip planning: ask questions or suggest destinations based on user input.
    Returns action, question, suggestions, etc.
    """
    payload = {
        "today": today,
        "user_message": user_message,
        "existing_slots": existing_slots,
        "missing_slots": get_missing_slots(existing_slots),
    }

    try:
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": TRIP_PLANNING_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
        )
        txt = get_text_from_parts(resp)
        data = safe_extract_json(txt)
        if data and isinstance(data, dict):
            # Add festival suggestions based on month if mentioned
            if data.get("action") == "suggest_destinations":
                # Try to extract month from user message or existing slots
                month = _extract_month_from_message(user_message, existing_slots)
                if month and month in FESTIVAL_DESTINATIONS:
                    if not data.get("festival_suggestions"):
                        data["festival_suggestions"] = []
                    data["festival_suggestions"].extend(FESTIVAL_DESTINATIONS[month])
            return data
    except Exception:
        pass

    # Fallback: simple logic based on missing slots
    missing = get_missing_slots(existing_slots)
    
    # Check for festival/month keywords in user message
    festival_keywords = {
        "ซากุระ": {"month": "มีนาคม", "destination": "ญี่ปุ่น"},
        "สงกรานต์": {"month": "เมษายน", "destination": "ไทย"},
        "ลอยกระทง": {"month": "พฤศจิกายน", "destination": "ไทย"},
        "คริสต์มาส": {"month": "ธันวาคม", "destination": "ยุโรป"},
        "ปีใหม่": {"month": "ธันวาคม", "destination": "ญี่ปุ่น"},
    }
    
    user_lower = user_message.lower()
    for keyword, info in festival_keywords.items():
        if keyword in user_lower:
            month = info["month"]
            if month in FESTIVAL_DESTINATIONS:
                return {
                    "action": "suggest_destinations",
                    "question": None,
                    "suggestions": [info["destination"]],
                    "missing_info": missing,
                    "festival_suggestions": FESTIVAL_DESTINATIONS[month],
                }
    
    if not existing_slots.get("destination"):
        return {
            "action": "ask_question",
            "question": "อยากไปเที่ยวที่ไหนคะ? หรือมีเดือน/เทศกาลที่อยากไปไหมคะ?",
            "suggestions": ["ญี่ปุ่น", "เกาหลี", "ยุโรป", "เกาะต่างๆ", "ดูซากุระ", "ช่วงสงกรานต์"],
            "missing_info": missing,
            "festival_suggestions": None,
        }
    elif not existing_slots.get("start_date"):
        return {
            "action": "ask_question",
            "question": "อยากไปช่วงไหนคะ? (เช่น เดือนมีนาคม, ดูซากุระ, หรือช่วงสงกรานต์)",
            "suggestions": ["เดือนมีนาคม", "เดือนเมษายน", "ดูซากุระ", "ช่วงสงกรานต์"],
            "missing_info": missing,
            "festival_suggestions": None,
        }
    elif existing_slots.get("adults") is None:
        return {
            "action": "ask_question",
            "question": "ไปกี่คนคะ? (ผู้ใหญ่และเด็ก)",
            "suggestions": ["2 ผู้ใหญ่", "ครอบครัว 4 คน", "ไปคนเดียว"],
            "missing_info": missing,
            "festival_suggestions": None,
        }

    return {
        "action": "ready_to_search",
        "question": None,
        "suggestions": None,
        "missing_info": [],
        "festival_suggestions": None,
    }


def _extract_month_from_message(user_message: str, slots: Dict[str, Any]) -> Optional[str]:
    """Extract month name from message or slots."""
    month_map = {
        "มกราคม": "มกราคม", "ม.ค.": "มกราคม", "january": "มกราคม", "jan": "มกราคม",
        "กุมภาพันธ์": "กุมภาพันธ์", "ก.พ.": "กุมภาพันธ์", "february": "กุมภาพันธ์", "feb": "กุมภาพันธ์",
        "มีนาคม": "มีนาคม", "มี.ค.": "มีนาคม", "march": "มีนาคม", "mar": "มีนาคม",
        "เมษายน": "เมษายน", "เม.ย.": "เมษายน", "april": "เมษายน", "apr": "เมษายน",
        "พฤษภาคม": "พฤษภาคม", "พ.ค.": "พฤษภาคม", "may": "พฤษภาคม",
        "มิถุนายน": "มิถุนายน", "มิ.ย.": "มิถุนายน", "june": "มิถุนายน", "jun": "มิถุนายน",
        "กรกฎาคม": "กรกฎาคม", "ก.ค.": "กรกฎาคม", "july": "กรกฎาคม", "jul": "กรกฎาคม",
        "สิงหาคม": "สิงหาคม", "ส.ค.": "สิงหาคม", "august": "สิงหาคม", "aug": "สิงหาคม",
        "กันยายน": "กันยายน", "ก.ย.": "กันยายน", "september": "กันยายน", "sep": "กันยายน",
        "ตุลาคม": "ตุลาคม", "ต.ค.": "ตุลาคม", "october": "ตุลาคม", "oct": "ตุลาคม",
        "พฤศจิกายน": "พฤศจิกายน", "พ.ย.": "พฤศจิกายน", "november": "พฤศจิกายน", "nov": "พฤศจิกายน",
        "ธันวาคม": "ธันวาคม", "ธ.ค.": "ธันวาคม", "december": "ธันวาคม", "dec": "ธันวาคม",
    }

    text = (user_message or "").lower()
    for key, month in month_map.items():
        if key.lower() in text:
            return month

    # Try to extract from date
    start_date = slots.get("start_date")
    if start_date:
        try:
            d = date.fromisoformat(start_date)
            return month_map.get(d.strftime("%B").lower())
        except Exception:
            pass

    return None

