from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional


def _airline_name(code: Optional[str]) -> str:
    return code or "Unknown"


def _fmt_time(iso_dt: Optional[str]) -> str:
    if not iso_dt:
        return ""
    m = re.search(r"T(\d{2}:\d{2})", iso_dt)
    return m.group(1) if m else iso_dt


def _plus_day(dep: Optional[str], arr: Optional[str]) -> str:
    try:
        if dep and arr:
            d0 = dep.split("T")[0]
            d1 = arr.split("T")[0]
            if d0 != d1:
                dd0 = date.fromisoformat(d0)
                dd1 = date.fromisoformat(d1)
                diff = (dd1 - dd0).days
                if diff > 0:
                    return f" (+{diff})"
    except Exception:
        pass
    return ""


def _find_included_checked_bags_anywhere(obj: Any) -> Optional[Dict[str, Any]]:
    if isinstance(obj, dict):
        if "includedCheckedBags" in obj:
            v = obj.get("includedCheckedBags")
            return v if isinstance(v, dict) else None
        for v in obj.values():
            found = _find_included_checked_bags_anywhere(v)
            if found:
                return found
    elif isinstance(obj, list):
        for v in obj:
            found = _find_included_checked_bags_anywhere(v)
            if found:
                return found
    return None


def _extract_baggage(offer: Dict[str, Any]) -> Optional[str]:
    bags = _find_included_checked_bags_anywhere(offer)
    if not bags:
        return None
    if bags.get("weight") and bags.get("weightUnit"):
        return f"{bags['weight']} {bags['weightUnit']}"
    if bags.get("quantity") is not None:
        return f"{bags['quantity']} piece(s)"
    return None


def flight_offer_to_detailed(offer: Dict[str, Any]) -> Dict[str, Any]:
    price_total = None
    currency = None
    try:
        p = offer.get("price") or {}
        currency = p.get("currency")
        price_total = float(p.get("grandTotal") or p.get("total") or 0) or None
    except Exception:
        pass

    cabin = None
    try:
        tps = offer.get("travelerPricings") or []
        if tps:
            fd = (tps[0].get("fareDetailsBySegment") or [])
            if fd and isinstance(fd[0], dict):
                cabin = fd[0].get("cabin")
    except Exception:
        pass

    baggage = _extract_baggage(offer)

    segments: List[Dict[str, Any]] = []
    try:
        itins = offer.get("itineraries") or []
        if itins:
            segs = itins[0].get("segments") or []
            for s in segs:
                dep = s.get("departure") or {}
                arr = s.get("arrival") or {}
                segments.append(
                    {
                        "carrier": s.get("carrierCode"),
                        "flight_number": f"{s.get('carrierCode','')}{s.get('number','')}".strip(),
                        "from": dep.get("iataCode"),
                        "to": arr.get("iataCode"),
                        "depart_at": dep.get("at"),
                        "arrive_at": arr.get("at"),
                        "depart_time": _fmt_time(dep.get("at")),
                        "arrive_time": _fmt_time(arr.get("at")),
                        "arrive_plus": _plus_day(dep.get("at"), arr.get("at")),
                        "duration": s.get("duration"),
                        "aircraft_code": (s.get("aircraft") or {}).get("code"),
                    }
                )
    except Exception:
        pass

    return {"currency": currency, "price_total": price_total, "cabin": cabin, "baggage": baggage, "segments": segments, "raw": offer}


def pick_hotel_fields(item: Dict[str, Any], nights: int) -> Dict[str, Any]:
    hotel = (item.get("hotel") or {})
    name = hotel.get("name") or "Unknown Hotel"
    hotel_id = hotel.get("hotelId")
    offers = item.get("offers") or []
    offer0 = offers[0] if offers else {}
    price_total = None
    currency = None
    try:
        p = offer0.get("price") or {}
        currency = p.get("currency")
        price_total = float(p.get("total") or 0) or None
    except Exception:
        pass

    return {
        "hotelName": name,
        "hotelId": hotel_id,
        "offerId": offer0.get("id"),
        "boardType": offer0.get("boardType"),
        "nights": nights,
        "price_total": price_total,
        "currency": currency,
        "raw": item,
    }


def build_day_by_day(nights: int, dest_label: str) -> List[Dict[str, Any]]:
    days = max(1, nights + 1)
    out: List[Dict[str, Any]] = []
    for d in range(1, days + 1):
        if d == 1:
            out.append({"day": d, "title": f"เดินทาง & {dest_label}", "items": ["ถึงสนามบิน/สถานี", "เข้าเมือง", "เช็คอิน", "เดินเล่นย่านดัง"]})
        elif d == days:
            out.append({"day": d, "title": "เดินทางกลับ", "items": ["เช็คเอาท์", "ไปสนามบิน", "เดินทางกลับ"]})
        else:
            out.append({"day": d, "title": f"เที่ยว {dest_label}", "items": ["ไฮไลต์หลัก 1", "ไฮไลต์หลัก 2", "มื้อเย็น/ตลาด/ช้อปปิ้ง"]})
    return out


def render_choice_text(choice: Dict[str, Any]) -> str:
    lines: List[str] = []
    title = choice.get("title") or choice.get("label") or "ช้อยส์"
    lines.append(title)

    f = choice.get("flight")
    if isinstance(f, dict) and f.get("segments"):
        lines.append("✈️ เที่ยวบิน")
        for i, seg in enumerate(f["segments"], start=1):
            lines.append("")
            lines.append(f"Segment {i}")
            lines.append(f"สายการบิน: {_airline_name(seg.get('carrier'))}")
            lines.append(f"เที่ยวบิน: {seg.get('flight_number')}")
            lines.append(f"เส้นทาง: {seg.get('from')} → {seg.get('to')}")
            lines.append(f"ออก: {seg.get('depart_time')}")
            lines.append(f"ถึง: {seg.get('arrive_time')}{seg.get('arrive_plus')}")
            if seg.get("aircraft_code"):
                lines.append(f"เครื่อง: {seg.get('aircraft_code')}")
            if seg.get("duration"):
                lines.append(f"ระยะเวลา: {seg.get('duration')}")
        if f.get("cabin"):
            lines.append(f"ชั้นโดยสาร: {f.get('cabin')}")
        if f.get("baggage"):
            lines.append(f"กระเป๋าโหลด: {f.get('baggage')}")
        if f.get("price_total") and f.get("currency"):
            lines.append(f"ราคา: {round(float(f['price_total']), 2)} {f['currency']} (ตาม Amadeus)")

    h = choice.get("hotel")
    if isinstance(h, dict):
        lines.append("")
        lines.append("🏨 ที่พัก")
        lines.append(f"โรงแรม: {h.get('hotelName')}")
        if h.get("nights"):
            lines.append(f"จำนวนคืน: {h.get('nights')}")
        if h.get("boardType"):
            lines.append(f"แพ็กเกจ: {h.get('boardType')}")
        if h.get("price_total") and h.get("currency"):
            lines.append(f"ราคา: {round(float(h['price_total']), 2)} {h['currency']} (ตาม Amadeus)")

    gt = choice.get("ground_transport")
    if gt:
        lines.append("")
        lines.append("🚆/🚗 เดินทาง/ขนส่ง")
        lines.append(gt)

    itin = choice.get("itinerary") or []
    if itin:
        lines.append("")
        lines.append("📅 Day-by-Day Itinerary")
        for d in itin:
            lines.append(f"🗓 Day {d.get('day')} – {d.get('title')}")
            for item in (d.get("items") or []):
                lines.append(f"- {item}")

    pb = choice.get("price_breakdown") or {}
    cur = pb.get("currency")
    if cur:
        lines.append("")
        lines.append("💰 สรุปราคา")
        if pb.get("flight_total") is not None:
            lines.append(f"- เที่ยวบิน: {pb.get('flight_total')} {cur}")
        if pb.get("hotel_total") is not None:
            lines.append(f"- ที่พัก: {pb.get('hotel_total')} {cur}")
        if choice.get("total_price") is not None:
            lines.append(f"รวมทั้งหมด: {choice.get('total_price')} {cur}")

    return "\n".join(lines).strip()


def build_plan_choices_3(search_results: Dict[str, Any], travel_slots: Dict[str, Any], debug: Dict[str, Any]) -> List[Dict[str, Any]]:
    flights = (search_results or {}).get("flights", {}).get("data") or []
    hotels = (search_results or {}).get("hotels", {}).get("data") or []

    nights = int(travel_slots.get("nights") or 3)
    dest_label = str(travel_slots.get("destination") or "").strip() or "ปลายทาง"

    hotel_note = ""
    picked = (debug or {}).get("hotel_pack")
    if isinstance(picked, dict) and picked.get("cityCode") and picked.get("checkInDate"):
        if picked.get("cityCode") != (debug or {}).get("dest_air"):
            hotel_note = f"หมายเหตุ: โรงแรมเป็นเมือง {picked.get('cityCode')} (fallback) เพราะปลายทางใน sandbox ไม่พบราคาในช่วงวันนั้น"

    choices: List[Dict[str, Any]] = []

    if flights and hotels:
        f = flight_offer_to_detailed(flights[0])
        h = pick_hotel_fields(hotels[0], nights=nights)

        currency = h.get("currency") or f.get("currency")
        total = None
        if currency and f.get("price_total") and h.get("price_total"):
            total = round(float(f["price_total"]) + float(h["price_total"]), 2)

        c1 = {
            "id": 1,
            "label": "ช้อยส์ 1",
            "title": "🟢 ช้อยส์ 1 (แนะนำ) – คลาสสิก คุ้มค่า",
            "recommended": True,
            "flight": f,
            "hotel": h,
            "ground_transport": (
                "ยังไม่ดึงราคาขนส่ง (รถไฟ/รถบัส/เรือ/รถไฟความเร็วสูง) จาก Amadeus self-service\n"
                "คุณสามารถพิมพ์ให้ฉันเพิ่มเส้นทางระหว่างเมืองได้ (แต่จะไม่ใส่ราคา ถ้าไม่มี API จริง)\n"
                + (hotel_note if hotel_note else "")
            ).strip(),
            "itinerary": build_day_by_day(nights=nights, dest_label=dest_label),
            "currency": currency,
            "total_price": total,
            "price_breakdown": {
                "flight_total": round(float(f["price_total"]), 2) if f.get("price_total") else None,
                "hotel_total": round(float(h["price_total"]), 2) if h.get("price_total") else None,
                "currency": currency,
            },
        }
        c1["display_text"] = render_choice_text(c1)
        choices.append(c1)

    if flights:
        f2 = flight_offer_to_detailed(flights[min(1, len(flights) - 1)])
        c2 = {
            "id": len(choices) + 1,
            "label": "ช้อยส์ 2",
            "title": "🔵 ช้อยส์ 2 – ประหยัด",
            "recommended": False,
            "flight": f2,
            "hotel": None,
            "ground_transport": "โหมดประหยัด: เลือกที่พักทีหลัง / หรือให้ฉันหาเพิ่ม (ขึ้นกับ sandbox inventory)",
            "itinerary": build_day_by_day(nights=nights, dest_label=dest_label),
            "currency": f2.get("currency"),
            "total_price": round(float(f2["price_total"]), 2) if f2.get("price_total") else None,
            "price_breakdown": {"flight_total": round(float(f2["price_total"]), 2) if f2.get("price_total") else None, "hotel_total": None, "currency": f2.get("currency")},
        }
        c2["display_text"] = render_choice_text(c2)
        choices.append(c2)

    if hotels:
        h3 = pick_hotel_fields(hotels[min(1, len(hotels) - 1)], nights=nights)
        c3 = {
            "id": len(choices) + 1,
            "label": "ช้อยส์ 3",
            "title": "🟣 ช้อยส์ 3 – สบาย พรีเมียม",
            "recommended": False,
            "flight": None,
            "hotel": h3,
            "ground_transport": "โหมดสบาย: เน้นที่พักก่อน แล้วค่อยจัดไฟลต์ทีหลัง (หรือให้ฉันหาไฟลต์เพิ่ม)",
            "itinerary": build_day_by_day(nights=nights, dest_label=dest_label),
            "currency": h3.get("currency"),
            "total_price": round(float(h3["price_total"]), 2) if h3.get("price_total") else None,
            "price_breakdown": {"flight_total": None, "hotel_total": round(float(h3["price_total"]), 2) if h3.get("price_total") else None, "currency": h3.get("currency")},
        }
        c3["display_text"] = render_choice_text(c3)
        choices.append(c3)

    return choices[:3]
