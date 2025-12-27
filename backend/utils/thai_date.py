from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Optional

THAI_MONTHS = {
    "ม.ค.": 1, "มกราคม": 1,
    "ก.พ.": 2, "กุมภาพันธ์": 2,
    "มี.ค.": 3, "มีนาคม": 3,
    "เม.ย.": 4, "เมษายน": 4,
    "พ.ค.": 5, "พฤษภาคม": 5,
    "มิ.ย.": 6, "มิถุนายน": 6,
    "ก.ค.": 7, "กรกฎาคม": 7,
    "ส.ค.": 8, "สิงหาคม": 8,
    "ก.ย.": 9, "กันยายน": 9,
    "ต.ค.": 10, "ตุลาคม": 10,
    "พ.ย.": 11, "พฤศจิกายน": 11,
    "ธ.ค.": 12, "ธันวาคม": 12,
}

DATE_RE = re.compile(
    r"(\d{1,2})\s*(ม\.ค\.|ก\.พ\.|มี\.ค\.|เม\.ย\.|พ\.ค\.|มิ\.ย\.|ก\.ค\.|ส\.ค\.|ก\.ย\.|ต\.ค\.|พ\.ย\.|ธ\.ค\.|มกราคม|กุมภาพันธ์|มีนาคม|เมษายน|พฤษภาคม|มิถุนายน|กรกฎาคม|สิงหาคม|กันยายน|ตุลาคม|พฤศจิกายน|ธันวาคม)\s*(\d{4})?"
)

def parse_thai_date_nearest_future(text: str) -> Optional[str]:
    t = (text or "").strip()

    # ISO format (YYYY-MM-DD)
    m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m:
        return m.group(1)

    # Relative dates
    today = date.today()
    if "พรุ่งนี้" in t or "tomorrow" in t.lower():
        return (today + timedelta(days=1)).isoformat()
    if "วันนี้" in t or "today" in t.lower():
        return today.isoformat()
    if "มะรืน" in t or "day after tomorrow" in t.lower():
        return (today + timedelta(days=2)).isoformat()
    
    # Next week/month patterns
    if "อาทิตย์หน้า" in t or "next week" in t.lower():
        return (today + timedelta(days=7)).isoformat()
    if "เดือนหน้า" in t or "next month" in t.lower():
        next_month = today.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        return next_month.isoformat()

    # Thai date format
    m = DATE_RE.search(t)
    if not m:
        return None

    d = int(m.group(1))
    mon_str = m.group(2)
    y = m.group(3)
    mon = THAI_MONTHS.get(mon_str)
    if not mon:
        return None

    if y:
        try:
            return date(int(y), mon, d).isoformat()
        except Exception:
            return None

    # Find nearest future date
    for year in [today.year, today.year + 1]:
        try:
            cand = date(year, mon, d)
            if cand >= today:
                return cand.isoformat()
        except Exception:
            pass
    return None
