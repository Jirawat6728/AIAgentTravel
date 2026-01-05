from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils.thai_date import parse_thai_date_nearest_future
from services.gemini_service import slot_extract_with_gemini
from utils.error_handling import safe_dict, safe_int, safe_str


DEFAULT_SLOTS: Dict[str, Any] = {
    # ✅ ข้อมูลหลัก (Core)
    "origin": None,  # ต้นทาง A
    "destination": None,  # ปลายทาง B
    "start_date": None,  # วันที่
    "days": None,  # จำนวนวัน (days = 1 → 1 วัน, days = 2 → 2 วัน 1 คืน)
    "nights": None,  # จำนวนคืน (deprecated - ใช้ days แทน, nights = days - 1)
    "adults": None,  # จำนวนผู้ใหญ่
    "children": None,  # จำนวนเด็ก
    
    # ✅ ข้อมูลรอง (Secondary)
    "destination_segments": None,  # ปลายทางต่อ C (multi-destination) - list of destinations
    "cabin_class": None,  # ชนิดที่นั่ง: ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST
    "prefer_direct": None,  # บินตรงไม่ต่อเครื่อง (true/false)
    "max_stops": None,  # ต่อเครื่องน้อยที่สุด (0=non-stop, 1=max 1 stop, etc.)
    "prefer_fast": None,  # ระยะเวลาเร็วช้า (true=เร็ว, false=ช้า)
    "max_waiting_time": None,  # รอนานไม่รอนาน (minutes - ถ้า null = ไม่จำกัด)
    "baggage_quantity": None,  # จำนวนกระเป๋า
    "baggage_weight": None,  # น้ำหนักกระเป๋า (kg)
    
    # ✅ Preferences (Optional)
    "budget_level": None,  # budget, normal, luxury
    "style": None,  # chill, fast, adventure
    "area_preference": None,  # เมือง/ย่านที่ต้องการ
}


def iso_date_or_none(s: Any) -> Optional[str]:
    if not s:
        return None
    if isinstance(s, str):
        s = s.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
    return None


def calculate_return_date(start_date: Optional[str], days: Optional[int] = None, nights: Optional[int] = None) -> Optional[str]:
    """คำนวณวันกลับจากวันเดินทางและจำนวนวัน (หรือจำนวนคืน)"""
    if not start_date:
        return None
    
    # ✅ ใช้ days เป็นหลัก, nights เป็น fallback
    if days is not None:
        # days = 1 → 1 วัน (day trip, ไม่พักคืน)
        # days = 2 → 2 วัน (พัก 1 คืน)
        # return_date = start_date + (days - 1) วัน
        try:
            start_dt = date.fromisoformat(start_date)
            return_date = start_dt + timedelta(days=days - 1) if days > 1 else start_dt
            return return_date.isoformat()
        except (ValueError, TypeError):
            return None
    elif nights is not None:
        # Fallback: ใช้ nights (backward compatibility)
        try:
            start_dt = date.fromisoformat(start_date)
            return_date = start_dt + timedelta(days=nights)
            return return_date.isoformat()
        except (ValueError, TypeError):
            return None
    
    return None


def calculate_days_from_dates(start_date: Optional[str], return_date: Optional[str] = None, end_date: Optional[str] = None) -> Optional[int]:
    """คำนวณจำนวนวันจากวันเดินทางและวันกลับ"""
    if not start_date:
        return None
    
    # ใช้ return_date หรือ end_date (ถ้ามี)
    target_date = return_date or end_date
    if not target_date:
        return None
    
    try:
        start_dt = date.fromisoformat(start_date)
        target_dt = date.fromisoformat(target_date)
        
        # คำนวณจำนวนวัน: days = (target_date - start_date) + 1
        # ตัวอย่าง: 3 ม.ค. → 5 ม.ค. = 3 วัน (3, 4, 5)
        days_diff = (target_dt - start_dt).days + 1
        return max(1, days_diff)  # อย่างน้อย 1 วัน
    except (ValueError, TypeError):
        return None


def normalize_non_core_defaults(slots: Dict[str, Any]) -> Dict[str, Any]:
    s = dict(slots or {})
    # ✅ style และ budget_level เป็น preference เท่านั้น ไม่ใช่ requirement
    # ไม่เติม default เพื่อให้ระบบ focus กับข้อมูลหลัก (origin, destination, date, adults)
    # style จะถูกเรียนรู้และเติมจาก profile เท่านั้น (optional)
    if "budget_level" not in s:
        s["budget_level"] = None  # ไม่เติม default
    if "style" not in s:
        s["style"] = None  # ไม่เติม default - ให้เรียนรู้จาก profile เท่านั้น
    if "area_preference" not in s:
        s["area_preference"] = None
    
    # ✅ รองรับทั้ง 2 แบบ: วันที่กลับ หรือ จำนวนวัน
    start_date = s.get("start_date") or s.get("departure_date")
    return_date = s.get("return_date")
    end_date = s.get("end_date")
    days = s.get("days")
    nights = s.get("nights")
    
    # 1. ถ้ามี return_date/end_date แต่ไม่มี days → คำนวณ days จากวันที่
    if (return_date or end_date) and not days and start_date:
        calculated_days = calculate_days_from_dates(start_date, return_date=return_date, end_date=end_date)
        if calculated_days:
            s["days"] = calculated_days
            s["nights"] = max(0, calculated_days - 1)  # คำนวณ nights จาก days
    
    # 2. ถ้ามี days แต่ไม่มี return_date/end_date → คำนวณ return_date จาก days
    elif days and not return_date and not end_date and start_date:
        calculated_return_date = calculate_return_date(start_date, days=days, nights=nights)
        if calculated_return_date:
            s["return_date"] = calculated_return_date
            s["end_date"] = calculated_return_date  # ✅ ตั้งค่า end_date ด้วยเพื่อความเข้ากันได้
            if not s.get("nights"):
                s["nights"] = max(0, days - 1)  # คำนวณ nights จาก days
    
    # 3. ถ้ามี nights แต่ไม่มี days และ return_date → คำนวณ days และ return_date จาก nights
    elif nights is not None and not days and not return_date and not end_date and start_date:
        s["days"] = nights + 1  # nights=1 → days=2
        calculated_return_date = calculate_return_date(start_date, nights=nights)
        if calculated_return_date:
            s["return_date"] = calculated_return_date
            s["end_date"] = calculated_return_date
    
    return s


def autopilot_fill_core_defaults(slots: Dict[str, Any], assumptions: List[str], force_defaults: bool = False) -> Dict[str, Any]:
    """
    Fill core defaults only if user has provided some information (destination or date).
    If force_defaults=True, always fill defaults (for backward compatibility).
    """
    s = dict(slots or {})
    today = date.today()
    
    # Only fill defaults if user has provided at least destination or date
    # This prevents auto-filling when user is just starting to plan
    has_user_input = bool(s.get("destination") or s.get("start_date") or s.get("origin"))
    
    if not force_defaults and not has_user_input:
        # Don't fill defaults yet - let trip planner ask questions first
        # Only fill adults/children if explicitly mentioned
        if s.get("adults") is None:
            s["adults"] = None  # Keep as None to trigger question
        if s.get("children") is None:
            s["children"] = None  # Keep as None
        return s
    
    # Fill defaults as before
    # ✅ IMPORTANT: CORE FIELDS (origin, destination, start_date, adults) should NOT be overridden if user provided them
    # Only fill defaults if core fields are truly missing (None or not set)
    # CORE FIELDS: origin, destination, start_date, adults - these are critical and should never be overridden
    
    # Origin (CORE) - only fill if truly missing (None or not in dict)
    # Note: Empty string "" is treated as user input (will be preserved by orchestrator)
    if "origin" not in s or s.get("origin") is None:
        s["origin"] = "Bangkok"
        assumptions.append("default origin=Bangkok")
    
    # Destination (CORE) - only fill if truly missing (None or not in dict)
    # Note: Empty string "" is treated as user input (will be preserved by orchestrator)
    # ✅ Removed default "Phuket" - let user specify destination
    # if "destination" not in s or s.get("destination") is None:
    #     s["destination"] = "Phuket"
    #     assumptions.append("default destination=Phuket")
    
    # Start date (CORE) - only fill if truly missing
    if not iso_date_or_none(s.get("start_date")):
        s["start_date"] = (today + timedelta(days=30)).isoformat()
        assumptions.append("default start_date=today+30")
    
    # Adults (CORE) - only fill if truly None (preserve existing value)
    # ✅ IMPORTANT: Never override if user has explicitly set adults count
    if s.get("adults") is None:
        s["adults"] = 1  # ✅ Default: 1 adult only if truly missing
        assumptions.append("default adults=1")
    # ✅ If adults is already set (even if 0), preserve it - don't override
    if s.get("children") is None:
        s["children"] = 0
        assumptions.append("default children=0")
    
    # ✅ รองรับทั้ง 2 แบบ: วันที่กลับ หรือ จำนวนวัน
    start_date = s.get("start_date") or s.get("departure_date")
    return_date = s.get("return_date")
    end_date = s.get("end_date")
    days = s.get("days")
    nights = s.get("nights")
    
    # 1. ถ้ามี return_date/end_date แต่ไม่มี days → คำนวณ days จากวันที่
    if (return_date or end_date) and not days and start_date:
        calculated_days = calculate_days_from_dates(start_date, return_date=return_date, end_date=end_date)
        if calculated_days:
            s["days"] = calculated_days
            s["nights"] = max(0, calculated_days - 1)  # คำนวณ nights จาก days
            assumptions.append(f"calculated days={calculated_days} from return_date")
    
    # 2. ถ้ามี days แต่ไม่มี return_date/end_date → คำนวณ return_date จาก days
    elif days and not return_date and not end_date and start_date:
        calculated_return_date = calculate_return_date(start_date, days=days, nights=nights)
        if calculated_return_date:
            s["return_date"] = calculated_return_date
            s["end_date"] = calculated_return_date  # ✅ ตั้งค่า end_date ด้วยเพื่อความเข้ากันได้
            if not s.get("nights"):
                s["nights"] = max(0, days - 1)  # คำนวณ nights จาก days
            assumptions.append(f"calculated return_date from days={days}")
    
    # 3. ถ้ามี nights แต่ไม่มี days และ return_date → คำนวณ days และ return_date จาก nights
    elif nights is not None and not days and not return_date and not end_date and start_date:
        s["days"] = nights + 1  # nights=1 → days=2
        calculated_return_date = calculate_return_date(start_date, nights=nights)
        if calculated_return_date:
            s["return_date"] = calculated_return_date
            s["end_date"] = calculated_return_date
            assumptions.append(f"calculated days={s['days']} and return_date from nights={nights}")
    
    # 4. ถ้าไม่มีอะไรเลย → ใช้ default days=1
    elif not days and not return_date and not end_date and not nights and start_date:
        s["days"] = 1  # ✅ Default: 1 day (day trip, ไม่พักคืน)
        s["nights"] = 0
        assumptions.append("default days=1")
    
    return s


def slot_extract_merge(today: str, user_id: str, user_message: str, existing: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """
    Extract slots from user message using LLM
    ใช้ Smart Merge เพื่อป้องกันข้อมูลหาย
    
    หลักการ:
    - LLM แค่ extract ข้อมูลใหม่ (ไม่ต้องเก็บ state)
    - Code จะทำการ merge กับ existing state
    """
    merged, assumptions = slot_extract_with_gemini(today=today, user_id=user_id, user_message=user_message, existing_travel_slots=existing)
    
    # ✅ Smart Merge: Preserve existing values - only update if new value is not None and not empty
    # Start with existing values (Single Source of Truth)
    result = dict(existing or {})
    
    # ✅ Detect correction intent (การเปลี่ยนใจ)
    # ถ้าผู้ใช้พูดถึง "เปลี่ยน", "ไม่เอา", "แทน" → ให้เขียนทับได้ (correction mode)
    t = (user_message or "").strip().lower()
    is_correction = any(kw in t for kw in [
        "เปลี่ยนใจ", "เปลี่ยน", "แก้ไข", "ไม่เอา", "เอา", "แทน",
        "change", "instead", "not", "replace", "edit"
    ])
    
    # Only update fields that have non-empty values in merged
    # ✅ ถ้าเป็น correction mode → เขียนทับได้เลย
    # ✅ ถ้าไม่ใช่ correction mode → ใช้ Smart Merge (ป้องกันข้อมูลหาย)
    for k, v in (merged or {}).items():
        if v is not None and v != "":
            if is_correction:
                # ✅ Correction mode: เขียนทับข้อมูลเดิมได้
                result[k] = v
            else:
                # ✅ Smart Merge: อัปเดตเฉพาะเมื่อไม่มีค่าเดิม
                if k not in result or result[k] is None or result[k] == "":
                    result[k] = v
                elif v is not None and v != "":
                    # ถ้ามีค่าใหม่และไม่ใช่ None/empty ให้อัปเดต (รองรับการแก้ไข)
                    result[k] = v
    
    merged = result

    # normalize date if present
    if merged.get("start_date"):
        merged["start_date"] = iso_date_or_none(merged["start_date"]) or merged["start_date"]

    # deterministic fallback to fill obvious fields if Gemini misses
    t = (user_message or "").strip()
    a: List[str] = []

    # Pattern 1: "ไป X จาก Y"
    m = re.search(r"ไป\s*([^\s]+(?:\s+[^\s]+)*?)\s*จาก\s*([^\s]+(?:\s+[^\s]+)*)", t)
    if m:
        if not merged.get("destination"):
            merged["destination"] = m.group(1).strip()
            a.append("regex destination from ไปXจากY")
        if not merged.get("origin"):
            merged["origin"] = m.group(2).strip()
            a.append("regex origin from ไปXจากY")

    # Pattern 2: "X ไป Y" or "X → Y" or "X-Y" or "X to Y" (more flexible)
    m = re.search(r"([A-Za-zก-๙\.\s]+?)\s*(?:ไป|→|to|-)\s*([A-Za-zก-๙\.\s]+)", t)
    if m:
        origin_candidate = m.group(1).strip()
        dest_candidate = m.group(2).strip()
        # Skip if it's part of "ไป X จาก Y" pattern
        if "จาก" not in origin_candidate and "ไป" not in origin_candidate:
            if not merged.get("origin"):
                merged["origin"] = origin_candidate
                a.append("regex origin from A->B")
            if not merged.get("destination"):
                merged["destination"] = dest_candidate
                a.append("regex destination from A->B")

    # Pattern 3: "จาก X ไป Y"
    m = re.search(r"จาก\s*([A-Za-zก-๙\.\s]+?)\s*ไป\s*([A-Za-zก-๙\.\s]+)", t)
    if m:
        if not merged.get("origin"):
            merged["origin"] = m.group(1).strip()
            a.append("regex origin from จากXไปY")
        if not merged.get("destination"):
            merged["destination"] = m.group(2).strip()
            a.append("regex destination from จากXไปY")

    # Date parsing (with more patterns)
    d = parse_thai_date_nearest_future(t)
    if d and not merged.get("start_date"):
        merged["start_date"] = d
        a.append("regex thai date")

    # Nights parsing (improved - handle "4วัน 3 คืน" correctly)
    # Priority: "คืน" > "วัน" (nights is more specific)
    nights_from_cuen = None
    m = re.search(r"(\d+)\s*คืน", t)
    if m:
        nights_from_cuen = int(m.group(1))
        merged["nights"] = nights_from_cuen
        a.append("regex nights from คืน")
    
    # If no "คืน" found, try "วัน" but calculate nights
    if nights_from_cuen is None:
        m = re.search(r"(\d+)\s*วัน", t)
        if m:
            days = int(m.group(1))
            # If days > 1, nights = days - 1 (e.g., "2 วัน" = 1 night)
            # If days = 1, it's a day trip (0 nights)
            if days > 1:
                merged["nights"] = days - 1
                a.append(f"regex nights from วัน (calculated: {days} วัน = {days-1} คืน)")
            elif days == 1:
                merged["nights"] = 0
                a.append("regex nights from วัน (1 วัน = 0 คืน)")

    # Adults parsing (more patterns)
    # ✅ รองรับทั้ง "ผู้ใหญ่ 3" และ "3 ผู้ใหญ่"
    m = re.search(r"ผู้ใหญ่\s*(\d+)", t)
    if m:
        merged["adults"] = int(m.group(1))
        a.append("regex adults from ผู้ใหญ่ X")
    else:
        # ✅ รองรับ "3 ผู้ใหญ่"
        m = re.search(r"(\d+)\s*ผู้ใหญ่", t)
        if m:
            merged["adults"] = int(m.group(1))
            a.append("regex adults from X ผู้ใหญ่")
        else:
            # Try "X คน" if context suggests adults
            m = re.search(r"(\d+)\s*คน", t)
            if m and "เด็ก" not in t[:t.find(m.group(0)) if m.start() > 0 else len(t)]:
                # If "คน" appears before "เด็ก", it might be adults
                if not merged.get("adults"):
                    merged["adults"] = int(m.group(1))
                    a.append("regex adults from คน")

    # Children parsing (more patterns)
    m = re.search(r"เด็ก\s*(\d+)", t)
    if m:
        merged["children"] = int(m.group(1))
        a.append("regex children")
    elif "เด็ก" in t and merged.get("children") is None:
        # If "เด็ก" mentioned but no number, default to 1
        merged["children"] = 1
        a.append("regex children default 1")

    # Area preference parsing (from "พัก X", "ที่ X", "ใน X", "แถว X")
    area_patterns = [
        r"พัก\s+([A-Za-zก-๙\.\s]+?)(?:\s|$|,|\.|คืน|วัน)",
        r"ที่\s+([A-Za-zก-๙\.\s]+?)(?:\s|$|,|\.)",
        r"ใน\s+([A-Za-zก-๙\.\s]+?)(?:\s|$|,|\.)",
        r"แถว\s+([A-Za-zก-๙\.\s]+?)(?:\s|$|,|\.)",
    ]
    for pattern in area_patterns:
        m = re.search(pattern, t)
        if m:
            area = m.group(1).strip()
            # Filter out common words that aren't locations
            if area and area not in ["นั้น", "นี้", "ไหน", "ที่", "ใน", "แถว"]:
                if not merged.get("area_preference"):
                    merged["area_preference"] = area
                    a.append(f"regex area_preference from {pattern[:10]}")
                break

    if merged.get("start_date"):
        merged["start_date"] = iso_date_or_none(merged["start_date"]) or merged["start_date"]

    # Clean up extracted values (remove extra spaces, normalize)
    for key in ["origin", "destination", "area_preference"]:
        if merged.get(key) and isinstance(merged[key], str):
            merged[key] = re.sub(r"\s+", " ", merged[key].strip())

    # Validate nights (should be non-negative integer)
    if merged.get("nights") is not None:
        try:
            nights_val = int(merged["nights"])
            if nights_val < 0:
                merged["nights"] = None
            else:
                merged["nights"] = nights_val
        except (ValueError, TypeError):
            merged["nights"] = None

    # Validate adults and children (should be non-negative integers)
    for key in ["adults", "children"]:
        if merged.get(key) is not None:
            try:
                val = int(merged[key])
                if val < 0:
                    merged[key] = None
                else:
                    merged[key] = val
            except (ValueError, TypeError):
                merged[key] = None

    return merged, (assumptions or []) + a
