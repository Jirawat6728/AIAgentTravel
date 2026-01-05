from __future__ import annotations

import json
from typing import Any, Dict, Optional

from google.genai import types

from services.gemini_service import get_gemini_client, get_text_from_parts, safe_extract_json, GEMINI_MODEL_NAME


SINGLE_ITEM_INTENT_SYSTEM_PROMPT = """
คุณคือผู้ช่วยวิเคราะห์ความตั้งใจของผู้ใช้ในการค้นหาสิ่งใดสิ่งหนึ่งเฉพาะ (ไม่ใช่ทริปเต็มรูปแบบ)
วิเคราะห์ว่าผู้ใช้ต้องการค้นหาเฉพาะเที่ยวบิน หรือเฉพาะที่พัก หรือต้องการจัดทริปเต็มรูปแบบ

Output schema EXACTLY (JSON only, no markdown):
{
  "intent": "flight_only" | "hotel_only" | "full_trip" | "unknown",
  "confidence": 0.0-1.0,
  "reason": "สั้นๆ ว่าทำไมถึงคิดแบบนี้"
}

Rules:
- "flight_only": เมื่อผู้ใช้พูดถึงเฉพาะเที่ยวบิน, ไฟลต์, บิน, ตั๋วเครื่องบิน, ไม่ได้พูดถึงที่พักหรือทริปเต็มรูปแบบ
  ตัวอย่าง: "หาเที่ยวบิน", "หาไฟลต์", "บินไปกรุงเทพ", "ตั๋วเครื่องบินไปญี่ปุ่น", "เที่ยวบินจากกรุงเทพไปภูเก็ต"
- "hotel_only": เมื่อผู้ใช้พูดถึงเฉพาะที่พัก, โรงแรม, ห้องพัก, ไม่ได้พูดถึงเที่ยวบินหรือทริปเต็มรูปแบบ
  ตัวอย่าง: "หาที่พัก", "หาโรงแรม", "ที่พักในกรุงเทพ", "โรงแรมที่ภูเก็ต", "ห้องพักในกรุงเทพ"
- "full_trip": เมื่อผู้ใช้พูดถึงทริป, เที่ยว, ไปเที่ยว, หรือพูดถึงทั้งเที่ยวบินและที่พัก
  ตัวอย่าง: "ไปเที่ยว", "จัดทริป", "ทริปไปญี่ปุ่น", "เที่ยวภูเก็ต", "ไปเที่ยวพร้อมที่พัก"
- "unknown": เมื่อไม่ชัดเจน

Examples:
- "หาเที่ยวบินจากกรุงเทพไปภูเก็ต" → {"intent": "flight_only", "confidence": 0.95, "reason": "พูดถึงเฉพาะเที่ยวบิน"}
- "หาไฟลต์ไปญี่ปุ่น" → {"intent": "flight_only", "confidence": 0.95, "reason": "พูดถึงเฉพาะไฟลต์"}
- "หาที่พักในกรุงเทพ" → {"intent": "hotel_only", "confidence": 0.95, "reason": "พูดถึงเฉพาะที่พัก"}
- "หาโรงแรมที่ภูเก็ต" → {"intent": "hotel_only", "confidence": 0.95, "reason": "พูดถึงเฉพาะโรงแรม"}
- "ไปเที่ยวภูเก็ต" → {"intent": "full_trip", "confidence": 0.9, "reason": "พูดถึงการเที่ยว"}
- "จัดทริปไปญี่ปุ่น" → {"intent": "full_trip", "confidence": 0.9, "reason": "พูดถึงทริป"}
- "ไปเที่ยวพร้อมที่พัก" → {"intent": "full_trip", "confidence": 0.95, "reason": "พูดถึงทั้งเที่ยวและที่พัก"}
"""


def detect_single_item_intent(user_message: str, existing_slots: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Detect if user wants to search for only flight or only hotel (not full trip)."""
    try:
        payload = {
            "user_message": user_message,
            "existing_slots": existing_slots or {},
        }
        
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": SINGLE_ITEM_INTENT_SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(payload, ensure_ascii=False)}]},
            ],
            config=types.GenerateContentConfig(
                temperature=0.3,
                max_output_tokens=100,
            ),
        )
        
        txt = get_text_from_parts(resp)
        data = safe_extract_json(txt)
        
        if isinstance(data, dict) and data.get("intent"):
            return {
                "intent": data.get("intent", "unknown"),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": data.get("reason", ""),
            }
    except Exception:
        pass
    
    # Fallback: simple keyword-based detection
    user_lower = (user_message or "").lower()
    
    # Flight-only keywords
    flight_keywords = ["เที่ยวบิน", "ไฟลต์", "บิน", "ตั๋วเครื่องบิน", "flight", "ticket"]
    hotel_keywords = ["ที่พัก", "โรงแรม", "ห้องพัก", "hotel", "accommodation"]
    trip_keywords = ["ทริป", "เที่ยว", "ไปเที่ยว", "trip", "vacation", "travel"]
    
    has_flight_keyword = any(kw in user_lower for kw in flight_keywords)
    has_hotel_keyword = any(kw in user_lower for kw in hotel_keywords)
    has_trip_keyword = any(kw in user_lower for kw in trip_keywords)
    
    if has_flight_keyword and not has_hotel_keyword and not has_trip_keyword:
        return {"intent": "flight_only", "confidence": 0.8, "reason": "พบคำที่เกี่ยวข้องกับเที่ยวบินเท่านั้น"}
    elif has_hotel_keyword and not has_flight_keyword and not has_trip_keyword:
        return {"intent": "hotel_only", "confidence": 0.8, "reason": "พบคำที่เกี่ยวข้องกับที่พักเท่านั้น"}
    elif has_trip_keyword or (has_flight_keyword and has_hotel_keyword):
        return {"intent": "full_trip", "confidence": 0.8, "reason": "พบคำที่เกี่ยวข้องกับทริปเต็มรูปแบบ"}
    
    # Default: assume full trip for backward compatibility
    return {"intent": "full_trip", "confidence": 0.5, "reason": "ไม่สามารถระบุได้ชัดเจน ใช้ค่าเริ่มต้นเป็นทริปเต็มรูปแบบ"}

