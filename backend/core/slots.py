from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

from utils.thai_date import parse_thai_date_nearest_future
from services.gemini_service import slot_extract_with_gemini


DEFAULT_SLOTS: Dict[str, Any] = {
    "origin": None,
    "destination": None,
    "start_date": None,
    "nights": None,
    "adults": None,
    "children": None,
    "budget_level": None,
    "style": None,
    "area_preference": None,
}


def iso_date_or_none(s: Any) -> Optional[str]:
    if not s:
        return None
    if isinstance(s, str):
        s = s.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            return s
    return None


def normalize_non_core_defaults(slots: Dict[str, Any]) -> Dict[str, Any]:
    s = dict(slots or {})
    if not s.get("budget_level"):
        s["budget_level"] = "normal"
    if not s.get("style"):
        s["style"] = "chill"
    if "area_preference" not in s:
        s["area_preference"] = None
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
    if not s.get("origin"):
        s["origin"] = "Bangkok"
        assumptions.append("default origin=Bangkok")
    if not s.get("destination"):
        s["destination"] = "Phuket"
        assumptions.append("default destination=Phuket")
    if not iso_date_or_none(s.get("start_date")):
        s["start_date"] = (today + timedelta(days=30)).isoformat()
        assumptions.append("default start_date=today+30")
    if not s.get("nights"):
        s["nights"] = 3
        assumptions.append("default nights=3")
    if s.get("adults") is None:
        s["adults"] = 2
        assumptions.append("default adults=2")
    if s.get("children") is None:
        s["children"] = 0
        assumptions.append("default children=0")
    return s


def slot_extract_merge(today: str, user_id: str, user_message: str, existing: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    merged, assumptions = slot_extract_with_gemini(today=today, user_id=user_id, user_message=user_message, existing_travel_slots=existing)
    merged = dict(existing or {}) | dict(merged or {})

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
    m = re.search(r"ผู้ใหญ่\s*(\d+)", t)
    if m:
        merged["adults"] = int(m.group(1))
        a.append("regex adults")
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
