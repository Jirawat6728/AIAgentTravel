from __future__ import annotations

import re
from datetime import date
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

    m = re.search(r"(\d{4}-\d{2}-\d{2})", t)
    if m:
        return m.group(1)

    m = DATE_RE.search(t)
    if not m:
        return None

    d = int(m.group(1))
    mon_str = m.group(2)
    y = m.group(3)
    mon = THAI_MONTHS.get(mon_str)
    if not mon:
        return None

    today = date.today()
    if y:
        try:
            return date(int(y), mon, d).isoformat()
        except Exception:
            return None

    for year in [today.year, today.year + 1]:
        try:
            cand = date(year, mon, d)
            if cand >= today:
                return cand.isoformat()
        except Exception:
            pass
    return None
