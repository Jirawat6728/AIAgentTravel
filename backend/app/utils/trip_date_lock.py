"""
ล็อกการทำรายการจอง/ชำระ/แก้ไขเมื่อเลยวันสิ้นสุดทริป (สอดคล้องกับ frontend tripDateLock.js)
ใช้ timezone Asia/Bangkok เป็นวันปฏิทิน
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

# Windows มักไม่มี IANA DB ในตัว — ต้อง pip install tzdata หรือใช้ UTC+7 แทน Asia/Bangkok
_BANGKOK_OFFSET = timezone(timedelta(hours=7))


def _today_calendar_date(tz_name: str) -> date:
    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except Exception:
        if tz_name == "Asia/Bangkok":
            return datetime.now(_BANGKOK_OFFSET).date()
        raise

DATE_KEYS_START = ("departure_date", "check_in", "pickup_date", "start_date")
DATE_KEYS_END = ("return_date", "check_out", "dropoff_date", "end_date")
ARRAY_KEYS = ("flights", "accommodations", "accommodation", "ground_transport", "segments", "outbound", "inbound")
NEST_KEYS = ("flight", "hotel", "accommodation", "ground_transport", "transport", "car", "travel", "requirements", "selected_option", "raw_data")


def _extract_ymd(val: Any) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()[:10]
    if len(s) < 10 or s[4] != "-" or s[7] != "-":
        return None
    parts = s.split("-")
    if len(parts) != 3:
        return None
    try:
        int(parts[0])
        int(parts[1])
        int(parts[2])
    except ValueError:
        return None
    return s


def _scan_object(obj: Any, starts: List[str], ends: List[str], visited: Set[int]) -> None:
    if obj is None or not isinstance(obj, dict):
        return
    oid = id(obj)
    if oid in visited:
        return
    visited.add(oid)

    for k in DATE_KEYS_START:
        y = _extract_ymd(obj.get(k))
        if y:
            starts.append(y)
    for k in DATE_KEYS_END:
        y = _extract_ymd(obj.get(k))
        if y:
            ends.append(y)

    for k in ARRAY_KEYS:
        arr = obj.get(k)
        if isinstance(arr, list):
            for item in arr:
                _scan_object(item, starts, ends, visited)

    for k in NEST_KEYS:
        child = obj.get(k)
        if child is not None and isinstance(child, dict):
            _scan_object(child, starts, ends, visited)


def is_travel_past_deadline(
    travel_slots: Optional[Dict[str, Any]],
    plan: Optional[Dict[str, Any]] = None,
    tz_name: str = "Asia/Bangkok",
) -> bool:
    starts: List[str] = []
    ends: List[str] = []
    visited: Set[int] = set()

    if travel_slots and isinstance(travel_slots, dict):
        _scan_object(travel_slots, starts, ends, visited)
    if plan and isinstance(plan, dict):
        _scan_object(plan, starts, ends, visited)

    if not starts and not ends:
        return False

    if ends:
        deadline_str = max(ends)
    else:
        deadline_str = max(starts)

    y, m, d = map(int, deadline_str.split("-"))
    deadline = date(y, m, d)
    today = _today_calendar_date(tz_name)
    return today > deadline


PAST_DEADLINE_DETAIL_TH = (
    "ทริปนี้เลยวันเดินทางแล้ว ไม่สามารถทำรายการเพิ่มได้ — ดูข้อมูลย้อนหลังได้ที่การจองของฉันหรือประวัติแชท"
)
