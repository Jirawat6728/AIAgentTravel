from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Optional, Tuple


# Currency conversion rates (approximate, update periodically)
# Source: Typical exchange rates as of 2024-2025
CURRENCY_RATES_TO_THB: Dict[str, float] = {
    "EUR": 38.0,  # 1 EUR ≈ 38 THB
    "JPY": 0.24,  # 1 JPY ≈ 0.24 THB
    "USD": 35.0,  # 1 USD ≈ 35 THB
    "GBP": 44.0,  # 1 GBP ≈ 44 THB
    "THB": 1.0,   # THB to THB = 1
}


def convert_to_thb(amount: float, from_currency: str) -> Tuple[float, str]:
    """
    Convert amount from given currency to THB.
    Returns (converted_amount, "THB")
    """
    if not amount or not from_currency:
        return amount, from_currency or "THB"
    
    from_currency = from_currency.upper().strip()
    if from_currency == "THB":
        return amount, "THB"
    
    rate = CURRENCY_RATES_TO_THB.get(from_currency)
    if rate:
        return round(amount * rate, 2), "THB"
    
    # If currency not found, return original (but log warning in production)
    return amount, from_currency


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

    # Process all flights and hotels
    processed_flights: List[Dict[str, Any]] = []
    processed_hotels: List[Dict[str, Any]] = []

    # Process flights (limit to top 20 for performance)
    for flight_offer in flights[:20]:
        f = flight_offer_to_detailed(flight_offer)
        flight_price_thb = None
        if f.get("price_total") and f.get("currency"):
            flight_price_thb, _ = convert_to_thb(float(f["price_total"]), f["currency"])
        if flight_price_thb is not None:
            # Calculate total duration and number of stops
            segments = f.get("segments") or []
            total_duration_sec = 0
            num_stops = len(segments) - 1  # Number of stops = segments - 1
            is_non_stop = len(segments) == 1
            
            # Calculate total duration from all segments
            for seg in segments:
                duration_str = seg.get("duration") or ""
                # Parse ISO 8601 duration (e.g., "PT4H25M" = 4 hours 25 minutes)
                if duration_str and isinstance(duration_str, str) and duration_str.startswith("PT"):
                    hours = 0
                    minutes = 0
                    try:
                        if "H" in duration_str:
                            hours_part = duration_str.split("H")[0].replace("PT", "")
                            hours = int(hours_part) if hours_part else 0
                            remaining = duration_str.split("H")[1] if "H" in duration_str else ""
                        else:
                            remaining = duration_str.replace("PT", "")
                        if "M" in remaining:
                            minutes_part = remaining.split("M")[0]
                            minutes = int(minutes_part) if minutes_part else 0
                        total_duration_sec += (hours * 3600 + minutes * 60)
                    except (ValueError, AttributeError):
                        pass
            
            processed_flights.append({
                "flight": f,
                "flight_price_thb": flight_price_thb,
                "total_duration_sec": total_duration_sec,
                "num_stops": num_stops,
                "is_non_stop": is_non_stop,
            })

    # Process hotels (limit to top 20 for performance)
    for hotel_item in hotels[:20]:
        h = pick_hotel_fields(hotel_item, nights=nights)
        hotel_price_thb = None
        if h.get("price_total") and h.get("currency"):
            hotel_price_thb, _ = convert_to_thb(float(h["price_total"]), h["currency"])
        if hotel_price_thb is not None:
            processed_hotels.append({
                "hotel": h,
                "hotel_price_thb": hotel_price_thb,
            })

    # Create combinations: Flight + Hotel
    for flight_data in processed_flights:
        for hotel_data in processed_hotels:
            total_thb = round(flight_data["flight_price_thb"] + hotel_data["hotel_price_thb"], 2)
            choices.append({
                "flight": flight_data["flight"],
                "hotel": hotel_data["hotel"],
                "flight_price_thb": flight_data["flight_price_thb"],
                "hotel_price_thb": hotel_data["hotel_price_thb"],
                "total_price": total_thb,
            })

    # Add Flight-only options
    for flight_data in processed_flights:
        choices.append({
            "flight": flight_data["flight"],
            "hotel": None,
            "flight_price_thb": flight_data["flight_price_thb"],
            "hotel_price_thb": None,
            "total_price": flight_data["flight_price_thb"],
        })

    # Add Hotel-only options
    for hotel_data in processed_hotels:
        choices.append({
            "flight": None,
            "hotel": hotel_data["hotel"],
            "flight_price_thb": None,
            "hotel_price_thb": hotel_data["hotel_price_thb"],
            "total_price": hotel_data["hotel_price_thb"],
        })

    # Find fastest non-stop flight for "เร็วสุดสะดวกสุด" choice
    fastest_non_stop_flight = None
    fastest_duration = float('inf')
    
    # Separate non-stop and stop flights
    non_stop_flights = [f for f in processed_flights if f.get("is_non_stop")]
    stop_flights = [f for f in processed_flights if not f.get("is_non_stop")]
    
    # Find fastest non-stop for special "เร็วสุดสะดวกสุด" choice
    for flight_data in non_stop_flights:
        if flight_data.get("total_duration_sec", float('inf')) < fastest_duration:
            fastest_duration = flight_data.get("total_duration_sec", float('inf'))
            fastest_non_stop_flight = flight_data
    
    # Add "เร็วสุดสะดวกสุด" choice if we found a non-stop flight
    if fastest_non_stop_flight and fastest_non_stop_flight.get("flight"):
        fastest_choice = {
            "flight": fastest_non_stop_flight["flight"],
            "hotel": None,  # Day trip, no hotel needed
            "flight_price_thb": fastest_non_stop_flight["flight_price_thb"],
            "hotel_price_thb": None,
            "total_price": fastest_non_stop_flight["flight_price_thb"],
            "is_fastest": True,
            "is_day_trip": True,
            "is_non_stop": True,
        }
        # Insert at the beginning (will be choice 0 or special handling)
        choices.insert(0, fastest_choice)
    
    # Add more non-stop flight-only choices (up to 3 additional)
    non_stop_count = 0
    for flight_data in non_stop_flights:
        # Skip if already added as fastest_choice
        if flight_data == fastest_non_stop_flight:
            continue
        if non_stop_count >= 3:  # Limit to 3 additional non-stop choices
            break
        
        # Add non-stop flight-only choice
        choices.append({
            "flight": flight_data["flight"],
            "hotel": None,
            "flight_price_thb": flight_data["flight_price_thb"],
            "hotel_price_thb": None,
            "total_price": flight_data["flight_price_thb"],
            "is_non_stop": True,
        })
        non_stop_count += 1

    # Sort by total_price (cheapest first)
    choices.sort(key=lambda x: x.get("total_price") or float('inf'))

    # Take top 10 choices (excluding fastest if it's already included)
    # If fastest is in top 10, keep it; otherwise add it separately
    regular_choices = [c for c in choices if not c.get("is_fastest")][:10]
    
    # Add fastest choice separately if it's not in top 10
    if fastest_non_stop_flight and fastest_choice not in regular_choices[:10]:
        # Insert fastest at position 0
        regular_choices.insert(0, fastest_choice)
        # Limit to 10 total
        regular_choices = regular_choices[:10]
    elif fastest_non_stop_flight:
        # Fastest is already in the list, move it to front
        fastest_idx = next((i for i, c in enumerate(regular_choices) if c.get("is_fastest")), None)
        if fastest_idx is not None and fastest_idx > 0:
            regular_choices.insert(0, regular_choices.pop(fastest_idx))
    
    choices = regular_choices if fastest_non_stop_flight else choices[:10]

    # Build final choice objects with labels and titles
    labels = ["เร็วสุดสะดวกสุด", "ถูกสุด", "ประหยัด", "คุ้มค่า", "สมดุล", "สะดวก", "สบาย", "พรีเมียม", "หรูหรา", "สุดพิเศษ", "VIP"]
    emojis = ["⚡", "💰", "💵", "💸", "💳", "⭐", "✨", "🌟", "💎", "👑", "🏆"]

    final_choices: List[Dict[str, Any]] = []
    for idx, choice_data in enumerate(choices):
        choice_id = idx + 1
        is_fastest = choice_data.get("is_fastest", False)
        is_day_trip = choice_data.get("is_day_trip", False)
        
        if is_fastest:
            label = "เร็วสุดสะดวกสุด"
            emoji = "⚡"
        else:
            label = labels[min(idx, len(labels) - 1)]
            emoji = emojis[min(idx, len(emojis) - 1)]
        
        # Determine title based on what's included
        if is_fastest and is_day_trip:
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (1 วันไปกลับ, ไม่มีต่อเครื่อง)"
        elif choice_data.get("flight") and choice_data.get("hotel"):
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (ไฟลต์ + ที่พัก)"
        elif choice_data.get("flight"):
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (ไฟลต์เท่านั้น)"
        elif choice_data.get("hotel"):
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (ที่พักเท่านั้น)"
        else:
            title = f"{emoji} ช้อยส์ {choice_id} – {label}"

        # Build ground transport message
        if is_fastest and is_day_trip:
            ground_transport = "⚡ โหมดเร็วสุด: 1 วันไปกลับ ไม่มีต่อเครื่อง ระยะเวลาสั้นที่สุด เหมาะสำหรับทริปสั้นๆ"
        elif choice_data.get("flight") and choice_data.get("hotel"):
            ground_transport = (
                "ยังไม่ดึงราคาขนส่ง (รถไฟ/รถบัส/เรือ/รถไฟความเร็วสูง) จาก Amadeus self-service\n"
                "คุณสามารถพิมพ์ให้ฉันเพิ่มเส้นทางระหว่างเมืองได้ (แต่จะไม่ใส่ราคา ถ้าไม่มี API จริง)\n"
                + (hotel_note if hotel_note else "")
            ).strip()
        elif choice_data.get("flight"):
            ground_transport = "โหมดประหยัด: เลือกที่พักทีหลัง / หรือให้ฉันหาเพิ่ม (ขึ้นกับ sandbox inventory)"
        elif choice_data.get("hotel"):
            ground_transport = "โหมดสบาย: เน้นที่พักก่อน แล้วค่อยจัดไฟลต์ทีหลัง (หรือให้ฉันหาไฟลต์เพิ่ม)"
        else:
            ground_transport = ""

        # For day trip, use nights=0
        trip_nights = 0 if is_day_trip else nights
        
        # Build itinerary
        if is_day_trip:
            itinerary_text = "🗓 1 วันไปกลับ\n- เดินทางไป: เช้า/เที่ยง\n- เที่ยว/ทำกิจกรรม\n- เดินทางกลับ: เย็น/ค่ำ\n\n⚡ ไม่มีต่อเครื่อง ระยะเวลาสั้นที่สุด"
        else:
            itinerary_text = build_day_by_day(nights=trip_nights, dest_label=dest_label)
        
        final_choice = {
            "id": choice_id,
            "label": label,
            "title": title,
            "recommended": (choice_id == 1) or is_fastest,  # First choice or fastest is recommended
            "flight": choice_data.get("flight"),
            "hotel": choice_data.get("hotel"),
            "ground_transport": ground_transport,
            "itinerary": itinerary_text,
            "currency": "THB",
            "total_price": choice_data.get("total_price"),
            "price_breakdown": {
                "flight_total": choice_data.get("flight_price_thb"),
                "hotel_total": choice_data.get("hotel_price_thb"),
                "currency": "THB",
            },
            "is_fastest": is_fastest,
            "is_day_trip": is_day_trip,
        }
        final_choice["display_text"] = render_choice_text(final_choice)
        final_choices.append(final_choice)

    return final_choices
