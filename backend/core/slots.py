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


def autopilot_fill_core_defaults(slots: Dict[str, Any], assumptions: List[str]) -> Dict[str, Any]:
    s = dict(slots or {})
    today = date.today()
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

    m = re.search(r"ไป\s*([^\s]+)\s*จาก\s*([^\s]+)", t)
    if m:
        if not merged.get("destination"):
            merged["destination"] = m.group(1).strip()
            a.append("regex destination from ไปXจากY")
        if not merged.get("origin"):
            merged["origin"] = m.group(2).strip()
            a.append("regex origin from ไปXจากY")

    m = re.search(r"([A-Za-zก-๙\.\s]+?)\s*(?:ไป|→)\s*([A-Za-zก-๙\.\s]+)", t)
    if m:
        if not merged.get("origin"):
            merged["origin"] = m.group(1).strip()
            a.append("regex origin from A->B")
        if not merged.get("destination"):
            merged["destination"] = m.group(2).strip()
            a.append("regex destination from A->B")

    d = parse_thai_date_nearest_future(t)
    if d and not merged.get("start_date"):
        merged["start_date"] = d
        a.append("regex thai date")

    m = re.search(r"(\d+)\s*คืน", t)
    if m:
        merged["nights"] = int(m.group(1))
        a.append("regex nights")

    m = re.search(r"ผู้ใหญ่\s*(\d+)", t)
    if m:
        merged["adults"] = int(m.group(1))
        a.append("regex adults")

    m = re.search(r"เด็ก\s*(\d+)", t)
    if m:
        merged["children"] = int(m.group(1))
        a.append("regex children")
    elif "เด็ก" in t and merged.get("children") is None:
        merged["children"] = 1
        a.append("regex children default 1")

    if merged.get("start_date"):
        merged["start_date"] = iso_date_or_none(merged["start_date"]) or merged["start_date"]

    return merged, (assumptions or []) + a
