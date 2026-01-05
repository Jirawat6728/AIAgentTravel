from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from services.gemini_service import get_gemini_client, get_text_from_parts, safe_extract_json, GEMINI_MODEL_NAME
from google.genai import types

SLOT_INTENT_SYSTEM_PROMPT = """
คุณคือผู้ช่วยวิเคราะห์ความตั้งใจของผู้ใช้ในการแก้ไขทริป
วิเคราะห์ว่าผู้ใช้ต้องการแก้ไข slot ไหน (flight, hotel, transport, dates, pax, all)

Output schema EXACTLY (JSON only, no markdown):
{
  "intent": "flight" | "hotel" | "transport" | "dates" | "pax" | "all" | "none",
  "confidence": 0.0-1.0,
  "reason": "สั้นๆ ว่าทำไมถึงคิดแบบนี้"
}

Rules:
- "flight": เมื่อผู้ใช้พูดถึงเที่ยวบิน, ไฟลต์, สายการบิน, เวลาบิน, บินตรง, แวะ
- "hotel": เมื่อผู้ใช้พูดถึงที่พัก, โรงแรม, ราคาที่พัก, เปลี่ยนโรงแรม, เพิ่มที่พัก, ลดที่พัก, จำนวนที่พัก
- "transport": เมื่อผู้ใช้พูดถึงรถ, รถไฟ, รถบัส, เรือ, การเดินทาง
- "dates": เมื่อผู้ใช้พูดถึงวัน, วันที่, ขยับวัน, เปลี่ยนวัน, จำนวนวัน, จำนวนคืน, เพิ่มวัน, ลดวัน
- "pax": เมื่อผู้ใช้พูดถึงจำนวนคน, ผู้ใหญ่, เด็ก, เพิ่มคน, ลดคน, เปลี่ยนจำนวนคน
- "all": เมื่อผู้ใช้พูดถึงหลายอย่างพร้อมกัน หรือเปลี่ยนข้อมูลพื้นฐานมาก
- "none": เมื่อไม่ชัดเจนว่าต้องการแก้ไขอะไร

Examples:
- "ขอไฟลต์เช้ากว่านี้" → {"intent": "flight", "confidence": 0.95, "reason": "พูดถึงไฟลต์"}
- "ขอที่พักถูกลง" → {"intent": "hotel", "confidence": 0.95, "reason": "พูดถึงที่พัก"}
- "เพิ่มที่พัก 1 segment" → {"intent": "hotel", "confidence": 0.9, "reason": "พูดถึงจำนวนที่พัก"}
- "ขยับวัน +1" → {"intent": "dates", "confidence": 0.9, "reason": "พูดถึงวัน"}
- "เปลี่ยนเป็น 5 คืน" → {"intent": "dates", "confidence": 0.9, "reason": "พูดถึงจำนวนคืน"}
- "เพิ่มเด็ก 1" → {"intent": "pax", "confidence": 0.9, "reason": "พูดถึงจำนวนคน"}
- "เปลี่ยนเป็น 3 ผู้ใหญ่" → {"intent": "pax", "confidence": 0.95, "reason": "พูดถึงจำนวนผู้ใหญ่"}
- "ขอรถเช่า" → {"intent": "transport", "confidence": 0.9, "reason": "พูดถึงการเดินทาง"}
"""


def detect_slot_intent(user_message: str, current_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Detect which slot the user wants to edit."""
    try:
        payload = {
            "user_message": user_message,
            "current_plan_summary": {
                "has_flight": bool(current_plan and current_plan.get("flight")),
                "has_hotel": bool(current_plan and current_plan.get("hotel")),
                "has_transport": bool(current_plan and current_plan.get("transport")),
            } if current_plan else None,
        }
        
        resp = get_gemini_client().models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=[
                {"role": "user", "parts": [{"text": SLOT_INTENT_SYSTEM_PROMPT}]},
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
                "intent": data.get("intent", "all"),
                "confidence": float(data.get("confidence", 0.5)),
                "reason": data.get("reason", ""),
            }
    except Exception:
        pass
    
    # Default: assume "all" if we can't detect
    return {"intent": "all", "confidence": 0.5, "reason": "ไม่สามารถระบุได้ชัดเจน"}

