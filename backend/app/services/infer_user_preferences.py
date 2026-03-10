"""
Infer User Preferences from First Message (และข้อความแชท)
เมื่อ User ใหม่ยังไม่มีประวัติเลือก (choice history) หรือ travelPreferences
ให้ AI เรียนรู้และรู้จักพฤติกรรม/ความชอบจากข้อความแรกได้ทันที
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


def _get_db():
    try:
        from app.storage.connection_manager import ConnectionManager
        return ConnectionManager.get_instance().get_mongo_database()
    except Exception:
        return None


def infer_travel_preferences_from_text(message: str) -> Dict[str, Any]:
    """
    ดึงความชอบจากการเดินทางจากข้อความ (คำหลัก + pattern)
    ไม่ใช้ LLM เพื่อความเร็ว — ใช้กับ User ใหม่ที่ยังไม่มีประวัติ
    """
    if not message or not isinstance(message, str):
        return {}
    text = message.strip().lower()
    out: Dict[str, Any] = {}

    # Budget
    if any(k in text for k in ["ประหยัด", "ราคาถูก", "budget", "low cost", "ต้นทุนต่ำ", "ไม่แพง"]):
        out["budget_level"] = "low"
    elif any(k in text for k in ["บิสซิเนส", "business", "ชั้นธุรกิจ", "ฟิร์สคลาส", "5 ดาว", "five star", "luxury", "พรีเมียม"]):
        out["budget_level"] = "high"
    else:
        out.setdefault("budget_level", "mid")

    # Price range: "ราคา 5000-15000", "5,000 ถึง 15,000", "5000 - 15000 บาท"
    range_match = re.search(
        r'(?:ราคา|งบ|budget|price)?\s*(\d[\d,]*)\s*[-–~ถึง]\s*(\d[\d,]*)\s*(?:บาท|baht|thb)?',
        text, re.IGNORECASE
    )
    if range_match:
        lo = int(range_match.group(1).replace(",", ""))
        hi = int(range_match.group(2).replace(",", ""))
        if lo > hi:
            lo, hi = hi, lo
        out["min_price"] = lo
        out["max_price"] = hi
    else:
        max_match = re.search(
            r'(?:ไม่เกิน|ไม่เกินs?|max|ไม่เกินราคา|งบไม่เกิน|ราคาไม่เกิน|under)\s*(\d[\d,]*)\s*(?:บาท|baht|thb)?',
            text, re.IGNORECASE
        )
        if max_match:
            out["max_price"] = int(max_match.group(1).replace(",", ""))
        min_match = re.search(
            r'(?:ตั้งแต่|อย่างน้อย|ขั้นต่ำ|min|ราคาตั้งแต่|from)\s*(\d[\d,]*)\s*(?:บาท|baht|thb)?',
            text, re.IGNORECASE
        )
        if min_match:
            out["min_price"] = int(min_match.group(1).replace(",", ""))

    # Travel style
    if any(k in text for k in ["พักผ่อน", "relax", "สปา", "spa", "ชายหาด", "beach", "นอนพัก"]):
        out["travel_style"] = "relaxation"
    elif any(k in text for k in ["ผจญภัย", "adventure", "เดินป่า", "trekking", "ลุย"]):
        out["travel_style"] = "adventure"
    elif any(k in text for k in ["เที่ยวชม", "culture", "วัฒนธรรม", "ช้อป"]):
        out["travel_style"] = "culture"

    # Travelers (จำนวนคน)
    m = re.search(r"(\d+)\s*คน", text)
    if m:
        out["travelers"] = int(m.group(1))
    for pattern in [r"ครอบครัว\s*(\d+)", r"(\d+)\s*ผู้ใหญ่", r"(\d+)\s*adult"]:
        m = re.search(pattern, text)
        if m:
            out["travelers"] = int(m.group(1))
            break
    if "ครอบครัว" in text or "เด็ก" in text or "family" in text:
        out["has_children"] = True

    # บินตรง
    if any(k in text for k in ["บินตรง", "direct", "ไม่ต่อ", "nonstop", "non-stop"]):
        out["prefer_direct_flight"] = True

    # ช่วงเวลาออกเดินทาง
    if any(k in text for k in ["เช้า", "ตอนเช้า", "เช้าตรู่", "morning"]):
        out["preferred_departure_time"] = "morning"
    elif any(k in text for k in ["บ่าย", "ตอนบ่าย", "afternoon"]):
        out["preferred_departure_time"] = "afternoon"
    elif any(k in text for k in ["เย็น", "ตอนเย็น", "evening"]):
        out["preferred_departure_time"] = "evening"
    elif any(k in text for k in ["ค่ำ", "กลางคืน", "ดึก", "night", "red-eye", "red eye"]):
        out["preferred_departure_time"] = "night"
    else:
        time_match = re.search(r'(?:ออก|บิน|เดินทาง)\s*(?:เวลา\s*)?(\d{1,2})[:\.](\d{2})', text)
        if time_match:
            hh, mm = int(time_match.group(1)), int(time_match.group(2))
            if 0 <= hh <= 23 and 0 <= mm <= 59:
                out["preferred_departure_time"] = f"{hh:02d}:{mm:02d}"

    # จุดหมายปลายทาง (เมือง/ประเทศที่พบบ่อย)
    destinations = []
    city_country = [
        ("พัทยา", "pattaya"), ("ภูเก็ต", "phuket"), ("เชียงใหม่", "chiang mai"), ("เกาหลี", "korea"), ("เกาหลีใต้", "south korea"),
        ("ญี่ปุ่น", "japan"), ("โตเกียว", "tokyo"), ("โอซาก้า", "osaka"), ("จีน", "china"), ("ฮ่องกง", "hong kong"),
        ("สิงคโปร์", "singapore"), ("เวียดนาม", "vietnam"), ("มาเลเซีย", "malaysia"), ("บาหลี", "bali"), ("ยุโรป", "europe"),
        ("ลอนดอน", "london"), ("ปารีส", "paris"), ("กรุงเทพ", "bangkok"), ("ต่างประเทศ", "abroad"),
    ]
    for th, en in city_country:
        if th in text or en in text:
            destinations.append(th)
    if destinations:
        out["preferred_destinations"] = destinations[:5]

    # ต้นทาง
    if "จากกรุงเทพ" in text or "จาก bkk" in text or "จากดอนเมือง" in text or "จาก dmk" in text:
        out["origin_city"] = "Bangkok"

    return out


async def infer_and_save_user_preferences_from_message(
    user_id: str,
    message: str,
    *,
    only_if_empty: bool = True,
) -> bool:
    """
    อนุมานความชอบจากข้อความแล้ว merge ลง user document
    เรียกเมื่อ User ใหม่ส่งข้อความแรก (หรือครั้งแรกในแชท) เพื่อให้ AI รู้จักพฤติกรรม/ความชอบทันที
    only_if_empty=True: จะ merge เฉพาะเมื่อ user ยังไม่มี travelPreferences หรือมีน้อย
    """
    if not user_id or user_id == "anonymous" or not message:
        return False
    db = _get_db()
    if not db:
        return False
    try:
        users = db["users"]
        user = await users.find_one({"user_id": user_id}, {"preferences": 1})
        if not user:
            return False
        prefs = user.get("preferences") or {}
        travel = prefs.get("travelPreferences") or {}

        if only_if_empty:
            # ถ้ามี travelPreferences เต็มอยู่แล้ว (มีหลาย key) ไม่ overwrite
            if len(travel) >= 3 and travel.get("budget_level") and travel.get("preferred_destinations"):
                return False
            # ถ้ามี choice history เยอะ แสดงว่าไม่ใช่ new user — ไม่ต้อง infer จากข้อความ
            from app.services.selection_preferences import COLLECTION_CHOICE_HISTORY
            col = db[COLLECTION_CHOICE_HISTORY]
            count = await col.count_documents({"user_id": user_id})
            if count > 5:
                return False

        inferred = infer_travel_preferences_from_text(message)
        if not inferred:
            return False

        # Merge: inferred ไม่ overwrite ค่าที่ user ตั้งไว้แล้ว
        merged = {**inferred, **travel}
        if "preferred_destinations" in inferred and "preferred_destinations" in travel:
            # รวม list ไม่ replace
            existing = travel.get("preferred_destinations") or []
            new_list = list(dict.fromkeys((inferred.get("preferred_destinations") or []) + existing))[:10]
            merged["preferred_destinations"] = new_list

        await users.update_one(
            {"user_id": user_id},
            {"$set": {"preferences.travelPreferences": merged, "preferences.inferred_from_chat": True}},
        )
        logger.info(f"Inferred preferences for user {user_id[:12]}...: {list(merged.keys())}")
        return True
    except Exception as e:
        logger.debug(f"infer_and_save_user_preferences_from_message: {e}")
        return False
