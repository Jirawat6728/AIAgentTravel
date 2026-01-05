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
    """Convert airline IATA code to full name"""
    if not code:
        return "Unknown"
    
    # Airline code to name mapping (common airlines)
    airline_names = {
        "TG": "Thai Airways",
        "FD": "Thai AirAsia",
        "SL": "Thai Lion Air",
        "PG": "Bangkok Airways",
        "VZ": "Thai Vietjet Air",
        "WE": "Thai Smile",
        "XJ": "Thai AirAsia X",
        "DD": "Nok Air",
        "Z2": "AirAsia Philippines",
        "AK": "AirAsia",
        "D7": "AirAsia X",
        "QZ": "Indonesia AirAsia",
        "JT": "Lion Air",
        "SJ": "Sriwijaya Air",
        "GA": "Garuda Indonesia",
        "SQ": "Singapore Airlines",
        "MI": "SilkAir",
        "TR": "Scoot",
        "3K": "Jetstar Asia",
        "QF": "Qantas",
        "JQ": "Jetstar",
        "MH": "Malaysia Airlines",
        "AK": "AirAsia",
        "OD": "Malindo Air",
        "D7": "AirAsia X",
        "VN": "Vietnam Airlines",
        "VJ": "Vietjet Air",
        "BL": "Jetstar Pacific",
        "CX": "Cathay Pacific",
        "KA": "Cathay Dragon",
        "HX": "Hong Kong Airlines",
        "UO": "Hong Kong Express",
        "JL": "Japan Airlines",
        "NH": "All Nippon Airways",
        "MM": "Peach Aviation",
        "GK": "Jetstar Japan",
        "KE": "Korean Air",
        "OZ": "Asiana Airlines",
        "TW": "T'way Air",
        "7C": "Jeju Air",
        "ZE": "Eastar Jet",
        "CA": "Air China",
        "CZ": "China Southern Airlines",
        "MU": "China Eastern Airlines",
        "3U": "Sichuan Airlines",
        "9C": "Spring Airlines",
        "HO": "Juneyao Airlines",
        "FM": "Shanghai Airlines",
        "MF": "Xiamen Airlines",
    }
    
    return airline_names.get(code.upper(), code)  # Return full name if found, otherwise return code


def _aircraft_name(code: Optional[str]) -> str:
    """Convert aircraft code to full name"""
    if not code:
        return "Unknown"
    
    # Aircraft code to name mapping
    aircraft_names = {
        "737": "Boeing 737",
        "738": "Boeing 737-800",
        "739": "Boeing 737-900",
        "73H": "Boeing 737-800",
        "73M": "Boeing 737 MAX",
        "320": "Airbus A320",
        "321": "Airbus A321",
        "32A": "Airbus A320",
        "32B": "Airbus A321",
        "32N": "Airbus A320neo",
        "32Q": "Airbus A321neo",
        "330": "Airbus A330",
        "332": "Airbus A330-200",
        "333": "Airbus A330-300",
        "350": "Airbus A350",
        "351": "Airbus A350-1000",
        "359": "Airbus A350-900",
        "380": "Airbus A380",
        "777": "Boeing 777",
        "77W": "Boeing 777-300ER",
        "787": "Boeing 787",
        "788": "Boeing 787-8",
        "789": "Boeing 787-9",
        "78X": "Boeing 787-10",
        "AT7": "ATR 72",
        "ATR": "ATR 72",
        "CRJ": "Bombardier CRJ",
        "E90": "Embraer E190",
        "E95": "Embraer E195",
    }
    
    return aircraft_names.get(code.upper(), f"เครื่องบิน {code}")  # Return full name if found, otherwise return formatted code


def _format_duration(duration_str: Optional[str]) -> str:
    """Convert ISO 8601 duration (PT1H15M) to readable format (1 ชั่วโมง 15 นาที)"""
    if not duration_str or not isinstance(duration_str, str):
        return ""
    
    # Parse ISO 8601 duration (e.g., "PT4H25M" = 4 hours 25 minutes)
    if duration_str.startswith("PT"):
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
            
            # Format as readable Thai text
            parts = []
            if hours > 0:
                parts.append(f"{hours} ชั่วโมง")
            if minutes > 0:
                parts.append(f"{minutes} นาที")
            
            if parts:
                return " ".join(parts)
            else:
                return "ไม่ระบุ"
        except (ValueError, AttributeError):
            return duration_str  # Return original if parsing fails
    
    return duration_str  # Return original if not ISO 8601 format


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


def _extract_flight_details(offer: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract detailed flight information from Amadeus offer
    Returns comprehensive flight details including pricing, conditions, baggage, etc.
    """
    details = {
        "price_per_person": None,
        "changeable": None,
        "refundable": None,
        "hand_baggage": None,
        "checked_baggage": None,
        "meals": None,
        "seat_selection": None,
        "wifi": None,
        "promotions": [],
    }
    
    try:
        # Price per person
        price_info = offer.get("price") or {}
        traveler_pricings = offer.get("travelerPricings") or []
        if traveler_pricings:
            first_traveler = traveler_pricings[0]
            traveler_price = first_traveler.get("price") or {}
            total = traveler_price.get("total")
            if total:
                details["price_per_person"] = float(total)
        
        # Conditions (changeable, refundable)
        fare_details = []
        for tp in traveler_pricings:
            fare_details_by_segment = tp.get("fareDetailsBySegment") or []
            fare_details.extend(fare_details_by_segment)
        
        if fare_details:
            first_fare = fare_details[0]
            # Check for changeable/refundable info
            included_checked_bags = first_fare.get("includedCheckedBags")
            if included_checked_bags:
                details["checked_baggage"] = f"{included_checked_bags.get('quantity', 0)} piece(s)"
            
            # Cabin class might indicate services
            cabin = first_fare.get("cabin")
            if cabin:
                if cabin.upper() in ["BUSINESS", "FIRST"]:
                    details["meals"] = "รวมอาหารบนเครื่อง"
                    details["seat_selection"] = "เลือกที่นั่งได้"
                    details["wifi"] = "Wi-Fi บนเครื่อง (บางสายการบิน)"
        
        # Hand baggage (usually 1 piece for all airlines)
        details["hand_baggage"] = "1 กระเป๋าถือ (7-10 kg)"
        
        # Check for promotions or special offers
        # Note: Amadeus might not always have promotion data in sandbox
        # We'll add mock promotions for demonstration
        price_total = price_info.get("grandTotal") or price_info.get("total")
        if price_total:
            price_float = float(price_total)
            # Mock promotion logic (in production, this would come from Amadeus)
            if price_float < 15000:
                details["promotions"].append({
                    "name": "Early Bird Special",
                    "type": "ส่วนลด",
                    "discount": "ลด 5%",
                    "code": None,
                    "extra_baggage": None,
                    "seat_upgrade": None,
                    "benefit": "ประหยัด 5% สำหรับการจองล่วงหน้า",
                    "conditions": "ใช้ได้กับไฟท์นี้",
                    "expiry": None,
                    "applicable": True,
                })
        
    except Exception:
        pass
    
    return details


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

    # Extract detailed flight information
    flight_details = _extract_flight_details(offer)
    
    return {
        "currency": currency,
        "price_total": price_total,
        "cabin": cabin,
        "baggage": baggage,
        "segments": segments,
        "raw": offer,
        "details": flight_details,  # ✅ เพิ่มข้อมูลรายละเอียด
    }


def pick_hotel_fields(item: Dict[str, Any], nights: int) -> Dict[str, Any]:
    """
    Extract hotel fields from Amadeus hotel offer.
    Also attempts to extract coordinates if available.
    """
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

    # ✅ Try to extract coordinates from hotel data
    latitude = None
    longitude = None
    address = None
    city_code = None
    
    try:
        # Try from hotel.geoCode
        geo_code = hotel.get("geoCode")
        if geo_code:
            latitude = geo_code.get("latitude")
            longitude = geo_code.get("longitude")
        
        # Try from hotel.address
        hotel_address = hotel.get("address")
        if hotel_address:
            address = hotel_address.get("lines") or []
            if isinstance(address, list) and address:
                address = ", ".join(address)
            elif isinstance(address, str):
                pass
            else:
                address = None
            city_code = hotel_address.get("cityCode")
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
        "latitude": latitude,  # ✅ เพิ่ม coordinates
        "longitude": longitude,  # ✅ เพิ่ม coordinates
        "address": address,  # ✅ เพิ่ม address
        "cityCode": city_code,  # ✅ เพิ่ม cityCode
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
    """
    สร้างข้อความสั้นๆ สำหรับแสดงในแชท
    แสดงแค่ประเภทข้อมูลที่มี (ไฟลต์ + ที่พัก) 
    รายละเอียดทั้งหมดจะแสดงใน PlanChoiceCard
    """
    lines: List[str] = []
    title = choice.get("title") or choice.get("label") or "ช้อยส์"
    
    # ✅ แสดงแค่ประเภทข้อมูลที่มี
    components = []
    if choice.get("flight"):
        components.append("ไฟลต์")
    if choice.get("hotel"):
        components.append("ที่พัก")
    if choice.get("transport") or choice.get("car"):
        components.append("การเดินทาง")
    
    if components:
        title_with_components = f"{title} ({' + '.join(components)})"
    else:
        title_with_components = title

    lines.append(title_with_components)
    lines.append("💡 กดการ์ดเพื่อดูรายละเอียดเพิ่มเติม")

    return "\n".join(lines).strip()


def _generate_mock_transport_data(
    origin: str,
    destination: str,
    transport_type: str,
) -> Dict[str, Any]:
    """
    สร้างข้อมูลการขนส่งจำลองเมื่อไม่มี API จริง
    """
    # ข้อมูลจำลองสำหรับการขนส่งระหว่างเมือง
    mock_data = {
        "train": {
            "type": "train",
            "from": origin,
            "to": destination,
            "operator": "รถไฟท้องถิ่น",
            "duration": "2-4 ชั่วโมง",
            "price": None,  # ไม่มีราคาจริง
            "note": "ข้อมูลจำลอง - ไม่มีราคาจริง",
        },
        "bus": {
            "type": "bus",
            "from": origin,
            "to": destination,
            "operator": "รถโดยสารประจำทาง",
            "duration": "3-6 ชั่วโมง",
            "price": None,
            "note": "ข้อมูลจำลอง - ไม่มีราคาจริง",
        },
        "ferry": {
            "type": "ferry",
            "from": origin,
            "to": destination,
            "operator": "เรือข้ามฟาก",
            "duration": "1-3 ชั่วโมง",
            "price": None,
            "note": "ข้อมูลจำลอง - ไม่มีราคาจริง",
        },
    }
    return mock_data.get(transport_type, {})


async def attempt_fetch_other_transport_async(
    client,  # AmadeusClient (optional, can be None)
    flight_segments: List[Dict[str, Any]],  # ✅ รับ flight segments แทน origin/destination เดียว
    start_date: str,
) -> List[Dict[str, Any]]:
    """
    Attempt to fetch transport data for buses, trains, electric trains, and ferries.
    รองรับหลาย segments เหมือนกับเที่ยวบิน
    ✅ OPTIMIZED: ทำงานแบบ parallel - ค้นหา train, bus, ferry พร้อมกัน และค้นหาทุก segments พร้อมกัน
    Returns a list of transport status for each segment.
    """
    import asyncio
    from services.amadeus_service import _search_trains, _search_buses, _search_ferries
    
    # ✅ ใช้ข้อมูลจำลองทันที (ไม่ต้องรอ API calls) เพื่อความเร็ว
    transport_segments: List[Dict[str, Any]] = []
    
    # สร้างข้อมูลจำลองสำหรับทุก segments ก่อน
    for seg_idx, flight_seg in enumerate(flight_segments):
        origin_iata = flight_seg.get("from")
        destination_iata = flight_seg.get("to")
        
        if not origin_iata or not destination_iata:
            continue
        
        segment_transport = {
            "segment": seg_idx + 1,
            "from": origin_iata,
            "to": destination_iata,
            "bus": {"available": False, "reason": "ยังไม่ได้ลองดึงข้อมูล", "data": []},
            "train": {"available": False, "reason": "ยังไม่ได้ลองดึงข้อมูล", "data": []},
            "metro": {"available": False, "reason": "Amadeus API ไม่มี endpoint สำหรับรถไฟฟ้า (Metro/Subway)", "data": []},
            "ferry": {"available": False, "reason": "ยังไม่ได้ลองดึงข้อมูล", "data": []},
        }
        
        # ✅ ใช้ข้อมูลจำลองทันที
        mock_train = _generate_mock_transport_data(origin_iata, destination_iata, "train")
        mock_bus = _generate_mock_transport_data(origin_iata, destination_iata, "bus")
        mock_ferry = _generate_mock_transport_data(origin_iata, destination_iata, "ferry")
        
        segment_transport["train"]["available"] = True
        segment_transport["train"]["data"] = [mock_train]
        segment_transport["train"]["reason"] = "ข้อมูลจำลอง - ไม่มีราคาจริง"
        
        segment_transport["bus"]["available"] = True
        segment_transport["bus"]["data"] = [mock_bus]
        segment_transport["bus"]["reason"] = "ข้อมูลจำลอง - ไม่มีราคาจริง"
        
        segment_transport["ferry"]["available"] = True
        segment_transport["ferry"]["data"] = [mock_ferry]
        segment_transport["ferry"]["reason"] = "ข้อมูลจำลอง - ไม่มีราคาจริง"
        
        transport_segments.append(segment_transport)
    
    # ✅ ถ้ามี client ให้ลองดึงข้อมูลจริงแบบ parallel (ทุก segments และทุก transport types พร้อมกัน)
    if client and start_date:
        async def fetch_transport_for_segment(seg_idx: int, origin_iata: str, destination_iata: str) -> Dict[str, Any]:
            """Fetch transport data for a single segment (train, bus, ferry in parallel)"""
            segment_transport = transport_segments[seg_idx]
            
            # ✅ ค้นหา train, bus, ferry แบบ parallel
            train_task = asyncio.to_thread(_search_trains, client, origin_iata, destination_iata, start_date)
            bus_task = asyncio.to_thread(_search_buses, client, origin_iata, destination_iata, start_date)
            ferry_task = asyncio.to_thread(_search_ferries, client, origin_iata, destination_iata, start_date)
            
            # ✅ รอผลลัพธ์ทั้ง 3 อย่างพร้อมกัน (parallel)
            train_result, bus_result, ferry_result = await asyncio.gather(
                train_task, bus_task, ferry_task, return_exceptions=True
            )
            
            # อัปเดตผลลัพธ์
            if not isinstance(train_result, Exception) and train_result.get("available"):
                segment_transport["train"] = {
                    "available": True,
                    "data": train_result.get("data", []),
                    "reason": "พบข้อมูลรถไฟจาก Amadeus API",
                }
            
            if not isinstance(bus_result, Exception) and bus_result.get("available"):
                segment_transport["bus"] = {
                    "available": True,
                    "data": bus_result.get("data", []),
                    "reason": "พบข้อมูลรถโดยสารจาก Amadeus API",
                }
            
            if not isinstance(ferry_result, Exception) and ferry_result.get("available"):
                segment_transport["ferry"] = {
                    "available": True,
                    "data": ferry_result.get("data", []),
                    "reason": "พบข้อมูลเรือจาก Amadeus API",
                }
            
            return segment_transport
        
        # ✅ ค้นหา transport สำหรับทุก segments แบบ parallel
        tasks = []
        for seg_idx, flight_seg in enumerate(flight_segments):
            origin_iata = flight_seg.get("from")
            destination_iata = flight_seg.get("to")
            if origin_iata and destination_iata:
                tasks.append(fetch_transport_for_segment(seg_idx, origin_iata, destination_iata))
        
        # ✅ รอผลลัพธ์จากทุก segments พร้อมกัน (parallel)
        if tasks:
            try:
                await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass  # ถ้าเกิด error ไม่เป็นไร ใช้ข้อมูลจำลอง
    
    return transport_segments


def build_persona_choices(
    choices: List[Dict[str, Any]],
    processed_flights: List[Dict[str, Any]],
    processed_hotels: List[Dict[str, Any]],
    processed_cars: List[Dict[str, Any]],
    transport_segments_data: List[Dict[str, Any]],
    nights: int,
) -> List[Dict[str, Any]]:
    """
    สร้าง 10 plan choices ตาม persona ที่กำหนด:
    1. ถูกสุด (Cheapest) - ราคาต่ำสุด
    2. เร็วสุด (Fastest) - เวลารวมเดินทางสั้นที่สุด
    3. สมดุล (Balanced) - ราคาและคุณภาพสมดุล (แนะนำ)
    4. สบาย (Comfort) - บินช่วงเวลาสบาย โรงแรม 4⭐
    5. พรีเมียม (Premium) - Business/Premium Economy โรงแรม 4-5⭐
    6. เช้าไว (Early Bird) - บินเช้ามาก
    7. ชิล ๆ (Late & Chill) - บินสาย/บ่าย
    8. ครอบครัว (Family Friendly) - บินตรง โรงแรมห้องใหญ่
    9. โลเคชันเทพ (Best Location) - โรงแรม prime location
    10. ยืดหยุ่นสูง (Flexible) - ไฟลต์เปลี่ยนวันได้
    """
    if not choices:
        return []
    
    persona_results: List[Tuple[str, Dict[str, Any], float]] = []  # (persona, choice, score)
    
    # 1. ถูกสุด (Cheapest) - ราคาต่ำสุด
    cheapest = min(choices, key=lambda x: x.get("total_price") or float('inf'))
    persona_results.append(("cheapest", cheapest, cheapest.get("total_price") or 0))
    
    # 2. เร็วสุด (Fastest) - เวลารวมเดินทางสั้นที่สุด (non-stop หรือ layover สั้น)
    fastest = min(
        [c for c in choices if c.get("is_non_stop") or c.get("total_duration_sec", float('inf')) < 36000],  # < 10 hours
        key=lambda x: x.get("total_duration_sec") or float('inf'),
        default=min(choices, key=lambda x: x.get("total_duration_sec") or float('inf'))
    )
    persona_results.append(("fastest", fastest, fastest.get("total_duration_sec") or 0))
    
    # 3. สมดุล (Balanced) - ราคาและคุณภาพสมดุล (แนะนำ)
    # เลือก choice ที่ราคาอยู่ใน middle range และมี non-stop หรือ layover น้อย
    sorted_by_price = sorted(choices, key=lambda x: x.get("total_price") or float('inf'))
    mid_index = len(sorted_by_price) // 2
    balanced_candidates = sorted_by_price[max(0, mid_index-2):min(len(sorted_by_price), mid_index+3)]
    balanced = max(
        balanced_candidates,
        key=lambda x: (1 if x.get("is_non_stop") else 0) * 1000 - (x.get("total_duration_sec") or 0) / 100
    )
    persona_results.append(("balanced", balanced, balanced.get("total_price") or 0))
    
    # 4. สบาย (Comfort) - บินช่วงเวลาสบาย (ไม่ดึก) โรงแรม 4⭐
    # เลือก choice ที่มี flight departure time ระหว่าง 8:00-18:00
    comfort_candidates = [c for c in choices if _is_comfortable_time(c)]
    if comfort_candidates:
        comfort = min(comfort_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        comfort = sorted_by_price[min(2, len(sorted_by_price)-1)]  # 3rd cheapest
    persona_results.append(("comfort", comfort, comfort.get("total_price") or 0))
    
    # 5. พรีเมียม (Premium) - Business/Premium Economy โรงแรม 4-5⭐
    # เลือก choice ที่มีราคาสูงกว่า (top 30% ของราคา)
    premium_threshold = sorted_by_price[int(len(sorted_by_price) * 0.7)].get("total_price") if sorted_by_price else float('inf')
    premium_candidates = [c for c in choices if (c.get("total_price") or 0) >= premium_threshold]
    if premium_candidates:
        premium = min(premium_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        premium = sorted_by_price[-1] if sorted_by_price else choices[0]  # Most expensive
    persona_results.append(("premium", premium, premium.get("total_price") or 0))
    
    # 6. เช้าไว (Early Bird) - บินเช้ามาก (departure time < 10:00)
    early_candidates = [c for c in choices if _is_early_morning(c)]
    if early_candidates:
        early_bird = min(early_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        early_bird = fastest  # Fallback to fastest
    persona_results.append(("early_bird", early_bird, early_bird.get("total_price") or 0))
    
    # 7. ชิล ๆ (Late & Chill) - บินสาย/บ่าย (departure time > 12:00)
    late_candidates = [c for c in choices if _is_late_morning_or_afternoon(c)]
    if late_candidates:
        chill = min(late_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        chill = balanced  # Fallback to balanced
    persona_results.append(("chill", chill, chill.get("total_price") or 0))
    
    # 8. ครอบครัว (Family Friendly) - บินตรง โรงแรมห้องใหญ่
    family_candidates = [c for c in choices if c.get("is_non_stop")]
    if family_candidates:
        family = min(family_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        family = fastest  # Fallback to fastest
    persona_results.append(("family", family, family.get("total_price") or 0))
    
    # 9. โลเคชันเทพ (Best Location) - โรงแรม prime location (ราคาสูงกว่าเล็กน้อย)
    # เลือก choice ที่มี hotel price สูงกว่าเล็กน้อย (อาจเป็น prime location)
    location_threshold = sorted_by_price[int(len(sorted_by_price) * 0.4)].get("total_price") if sorted_by_price else float('inf')
    location_candidates = [c for c in choices if (c.get("total_price") or 0) >= location_threshold]
    if location_candidates:
        best_location = min(location_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        best_location = balanced  # Fallback to balanced
    persona_results.append(("best_location", best_location, best_location.get("total_price") or 0))
    
    # 10. ยืดหยุ่นสูง (Flexible) - ไฟลต์เปลี่ยนวันได้ (เลือก choice ที่มี non-stop หรือราคาไม่สูงมาก)
    flexible_candidates = [c for c in choices if c.get("is_non_stop") or (c.get("total_price") or 0) <= (cheapest.get("total_price") or 0) * 1.2]
    if flexible_candidates:
        flexible = min(flexible_candidates, key=lambda x: x.get("total_price") or float('inf'))
    else:
        flexible = cheapest  # Fallback to cheapest
    persona_results.append(("flexible", flexible, flexible.get("total_price") or 0))
    
    # สร้าง final choices โดยใช้ persona ที่เลือก
    final_choices = []
    for persona, choice, score in persona_results:
        # เพิ่ม persona metadata
        choice_with_persona = dict(choice)
        choice_with_persona["persona"] = persona
        final_choices.append(choice_with_persona)
    
    return final_choices


def _is_comfortable_time(choice: Dict[str, Any]) -> bool:
    """ตรวจสอบว่า flight departure time อยู่ในช่วงสบาย (8:00-18:00)"""
    flight = choice.get("flight", {})
    segments = flight.get("segments", [])
    if not segments:
        return False
    first_seg = segments[0]
    dep_time = first_seg.get("depart_time", "")
    if not dep_time:
        return False
    try:
        hour = int(dep_time.split(":")[0])
        return 8 <= hour <= 18
    except:
        return False


def _is_early_morning(choice: Dict[str, Any]) -> bool:
    """ตรวจสอบว่า flight departure time เป็นเช้ามาก (< 10:00)"""
    flight = choice.get("flight", {})
    segments = flight.get("segments", [])
    if not segments:
        return False
    first_seg = segments[0]
    dep_time = first_seg.get("depart_time", "")
    if not dep_time:
        return False
    try:
        hour = int(dep_time.split(":")[0])
        return hour < 10
    except:
        return False


def _generate_persona_tags(persona: str, choice_data: Dict[str, Any]) -> List[str]:
    """Generate tags based on persona"""
    tags = []
    if persona == "cheapest":
        tags.append("ถูกสุด")
    elif persona == "fastest":
        tags.append("เร็วสุด")
        if choice_data.get("is_non_stop"):
            tags.append("บินตรง")
    elif persona == "balanced":
        tags.append("แนะนำ")
        tags.append("สมดุล")
    elif persona == "comfort":
        tags.append("สบาย")
    elif persona == "premium":
        tags.append("พรีเมียม")
    elif persona == "early_bird":
        tags.append("เช้าไว")
    elif persona == "chill":
        tags.append("ชิล")
    elif persona == "family":
        tags.append("ครอบครัว")
        if choice_data.get("is_non_stop"):
            tags.append("บินตรง")
    elif persona == "best_location":
        tags.append("โลเคชันดี")
    elif persona == "flexible":
        tags.append("ยืดหยุ่น")
    
    return tags


def _is_late_morning_or_afternoon(choice: Dict[str, Any]) -> bool:
    """ตรวจสอบว่า flight departure time เป็นสาย/บ่าย (> 12:00)"""
    flight = choice.get("flight", {})
    segments = flight.get("segments", [])
    if not segments:
        return False
    first_seg = segments[0]
    dep_time = first_seg.get("depart_time", "")
    if not dep_time:
        return False
    try:
        hour = int(dep_time.split(":")[0])
        return hour >= 12
    except:
        return False


async def build_plan_choices_3(search_results: Dict[str, Any], travel_slots: Dict[str, Any], debug: Dict[str, Any]) -> List[Dict[str, Any]]:
    flights = (search_results or {}).get("flights", {}).get("data") or []
    hotels = (search_results or {}).get("hotels", {}).get("data") or []
    cars = (search_results or {}).get("cars", {}).get("data") or []

    nights = int(travel_slots.get("nights") or 3)
    dest_label = str(travel_slots.get("destination") or "").strip() or "ปลายทาง"
    
    # Get origin and destination IATA codes from debug for transport attempts
    origin_iata = (debug or {}).get("origin_air")
    dest_iata = (debug or {}).get("dest_air")
    start_date = str(travel_slots.get("start_date") or "").strip()
    
    # ✅ Get Amadeus client to attempt fetching other transport types
    client = None
    try:
        from core.config import get_amadeus_search_client
        client = get_amadeus_search_client()
    except Exception:
        pass

    hotel_note = ""
    picked = (debug or {}).get("hotel_pack")
    if isinstance(picked, dict) and picked.get("cityCode") and picked.get("checkInDate"):
        if picked.get("cityCode") != (debug or {}).get("dest_air"):
            hotel_note = f"หมายเหตุ: โรงแรมเป็นเมือง {picked.get('cityCode')} (fallback) เพราะปลายทางใน sandbox ไม่พบราคาในช่วงวันนั้น"

    choices: List[Dict[str, Any]] = []

    # Process all flights and hotels
    processed_flights: List[Dict[str, Any]] = []
    processed_hotels: List[Dict[str, Any]] = []

    # ✅ Process flights (limit to top 10 for performance - เพื่อความเร็ว)
    for flight_offer in flights[:10]:
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
                "flight_details": f.get("details", {}),  # ✅ เพิ่มข้อมูลรายละเอียด
            })

    # ✅ Process hotels (limit to top 10 for performance - เพื่อความเร็ว)
    for hotel_item in hotels[:10]:
        h = pick_hotel_fields(hotel_item, nights=nights)
        hotel_price_thb = None
        if h.get("price_total") and h.get("currency"):
            hotel_price_thb, _ = convert_to_thb(float(h["price_total"]), h["currency"])
        if hotel_price_thb is not None:
            processed_hotels.append({
            "hotel": h,
                "hotel_price_thb": hotel_price_thb,
            })

    # ✅ Process cars (รถเช่า)
    processed_cars: List[Dict[str, Any]] = []
    for car_item in cars[:10]:  # Limit to top 10 cars
        try:
            # Extract car data from Amadeus structure
            car_price = None
            car_currency = None
            if isinstance(car_item, dict):
                # Amadeus car structure may vary, try common fields
                price_info = car_item.get("estimatedTotal", {}) or car_item.get("price", {}) or {}
                if isinstance(price_info, dict):
                    car_price = price_info.get("amount") or price_info.get("total")
                    car_currency = price_info.get("currency") or "EUR"
                elif isinstance(price_info, (int, float)):
                    car_price = price_info
                    car_currency = "EUR"
            
            if car_price:
                car_price_thb, _ = convert_to_thb(float(car_price), car_currency or "EUR")
                processed_cars.append({
                    "car": car_item,
                    "car_price_thb": car_price_thb,
                })
        except Exception:
            pass

    # ✅ ดึงข้อมูลการขนส่งแบบ parallel (ครั้งเดียวสำหรับทุก flight segments)
    # ใช้ flight segments จาก flight แรก (หรือใช้ origin/dest ถ้าไม่มี flights)
    transport_segments_data = []
    if processed_flights:
        # ใช้ flight segments จาก flight แรก
        first_flight = processed_flights[0]["flight"]
        flight_segments_for_transport = first_flight.get("segments") or []
        
        if flight_segments_for_transport:
            # ✅ ค้นหา transport แบบ parallel (ครั้งเดียว)
            transport_segments_data = await attempt_fetch_other_transport_async(
                client=client,
                flight_segments=flight_segments_for_transport,
                start_date=start_date,
            )
    elif origin_iata and dest_iata:
        # ถ้าไม่มี flights ให้ใช้ origin/dest
        transport_segments_data = await attempt_fetch_other_transport_async(
            client=client,
            flight_segments=[{"from": origin_iata, "to": dest_iata}],
            start_date=start_date,
        )

    # ✅ Create combinations: Slot 1 (Flight) + Slot 2 (Hotel) + Slot 3 (Transport: Car/Bus/Train/Ferry)
    # แต่ละ choice ต้องมีทั้ง 3 slots (ถ้ามีข้อมูล)
    for flight_data in processed_flights:
        flight_obj = flight_data["flight"]
        flight_segments = flight_obj.get("segments") or []
        
        for hotel_data in processed_hotels:
            # ✅ สร้าง hotel segments ตาม flight segments
            hotel_segments = []
            hotel_price_total_thb = 0
            
            if len(flight_segments) > 1:
                # Multiple flight segments -> สร้าง hotel segments ตามแต่ละ destination
                # แบ่ง nights ตามจำนวน segments
                nights_per_segment = max(1, nights // len(flight_segments))
                remaining_nights = nights - (nights_per_segment * (len(flight_segments) - 1))
                
                for i, flight_seg in enumerate(flight_segments):
                    destination_city = flight_seg.get("to")
                    segment_nights = remaining_nights if i == len(flight_segments) - 1 else nights_per_segment
                    
                    # สร้าง hotel segment สำหรับแต่ละ destination
                    hotel_seg = {
                        "hotelName": hotel_data["hotel"].get("hotelName"),
                        "hotelId": hotel_data["hotel"].get("hotelId"),
                        "cityCode": destination_city,  # ใช้ destination ของ flight segment
                        "nights": segment_nights,
                        "boardType": hotel_data["hotel"].get("boardType"),
                        "price_total": hotel_data["hotel"].get("price_total") / len(flight_segments) if hotel_data["hotel"].get("price_total") else None,
                        "currency": hotel_data["hotel"].get("currency"),
                        "latitude": hotel_data["hotel"].get("latitude"),
                        "longitude": hotel_data["hotel"].get("longitude"),
                        "address": hotel_data["hotel"].get("address"),
                    }
                    hotel_segments.append(hotel_seg)
                    
                    # คำนวณราคา
                    if hotel_seg.get("price_total") and hotel_seg.get("currency"):
                        seg_price_thb, _ = convert_to_thb(float(hotel_seg["price_total"]), hotel_seg["currency"])
                        hotel_price_total_thb += seg_price_thb
            else:
                # Single flight segment -> ใช้ hotel เดียว (backward compatibility)
                hotel_segments = None
                hotel_price_total_thb = hotel_data["hotel_price_thb"]
            
            # สร้าง hotel object (รองรับทั้ง single และ multiple segments)
            if hotel_segments:
                hotel_obj = {
                    "segments": hotel_segments,
                    "price_total": hotel_data["hotel"].get("price_total"),
                    "currency": hotel_data["hotel"].get("currency"),
                }
            else:
                # Single hotel (backward compatibility)
                hotel_obj = hotel_data["hotel"]
            
            base_price = round(flight_data["flight_price_thb"] + hotel_price_total_thb, 2)
            
            # ✅ Slot 3: Transport (รถและเรือ)
            # รวม cars และ transport types อื่นๆ เป็น transport options
            transport_options = []
            transport_price_total = 0
            
            # เพิ่ม cars เป็น transport option
            for car_data in processed_cars[:3]:  # Limit to 3 car options
                transport_options.append({
                    "type": "car_rental",  # รถเช่า
                    "data": car_data["car"],
                    "price_thb": car_data["car_price_thb"],
                    "available": True,
                })
            
            # ✅ ใช้ transport_segments_data ที่ดึงมาแล้ว (ไม่ต้องดึงซ้ำ)
            # สร้าง choices: 1 choice ต่อ 1 transport option (ถ้ามี)
            if transport_options:
                for transport_option in transport_options:
                    # ✅ รวม transport_segments_data เข้าไปใน transport structure
                    transport_with_segments = {
                        **transport_option,
                        "segments": transport_segments_data,  # ✅ ข้อมูลการขนส่งตาม segments
                    }
                    total_thb = round(base_price + transport_option["price_thb"], 2)
                    choices.append({
                        # Slot 1: ไฟลต์บิน
                        "flight": flight_data["flight"],
                        "flight_price_thb": flight_data["flight_price_thb"],
                        "is_non_stop": flight_data.get("is_non_stop", False),
                        "total_duration_sec": flight_data.get("total_duration_sec", 0),  # ✅ เพิ่ม total_duration_sec
                        # Slot 2: ที่พัก (รองรับหลาย segments)
                        "hotel": hotel_obj,
                        "hotel_price_thb": hotel_price_total_thb,
                        # Slot 3: รถและเรือ (รวม segments)
                        "transport": transport_with_segments,
                        "transport_price_thb": transport_option["price_thb"],
                        "total_price": total_thb,
                    })
            else:
                # ถ้าไม่มี transport options ให้สร้าง choice โดยไม่มี transport แต่ยังเก็บ segments
                transport_with_segments = {
                    "type": None,
                    "data": None,
                    "price_thb": None,
                    "available": False,
                    "segments": transport_segments_data,  # ✅ ข้อมูลการขนส่งตาม segments
                }
                choices.append({
                    # Slot 1: ไฟลต์บิน
                    "flight": flight_data["flight"],
                    "flight_price_thb": flight_data["flight_price_thb"],
                    "is_non_stop": flight_data.get("is_non_stop", False),
                    "total_duration_sec": flight_data.get("total_duration_sec", 0),  # ✅ เพิ่ม total_duration_sec
                    "flight_details": flight_data.get("flight_details", {}),  # ✅ เพิ่มข้อมูลรายละเอียด
                    # Slot 2: ที่พัก (รองรับหลาย segments)
                    "hotel": hotel_obj,
                    "hotel_price_thb": hotel_price_total_thb,
                    # Slot 3: รถและเรือ (ไม่มี แต่เก็บ segments)
                    "transport": transport_with_segments,
                    "transport_price_thb": None,
                    "total_price": base_price,
                })

    # ✅ ไม่สร้าง flight-only choices อีกต่อไป - ทุก choice ต้องมีทั้ง 3 slots (Flight + Hotel + Transport)

    # ✅ 10 Personas: ถูกสุด, เร็วสุด, สมดุล, สบาย, พรีเมียม, เช้าไว, ชิล, ครอบครัว, โลเคชันเทพ, ยืดหยุ่น
    persona_configs = [
        {"label": "ถูกสุด", "emoji": "💰", "persona": "cheapest", "recommended": False},
        {"label": "เร็วสุด", "emoji": "⚡", "persona": "fastest", "recommended": False},
        {"label": "สมดุล", "emoji": "⭐", "persona": "balanced", "recommended": True},  # Default recommended
        {"label": "สบาย", "emoji": "✨", "persona": "comfort", "recommended": False},
        {"label": "พรีเมียม", "emoji": "💎", "persona": "premium", "recommended": False},
        {"label": "เช้าไว", "emoji": "🌅", "persona": "early_bird", "recommended": False},
        {"label": "ชิล ๆ", "emoji": "🌴", "persona": "chill", "recommended": False},
        {"label": "ครอบครัว", "emoji": "👨‍👩‍👧‍👦", "persona": "family", "recommended": False},
        {"label": "โลเคชันเทพ", "emoji": "📍", "persona": "best_location", "recommended": False},
        {"label": "ยืดหยุ่นสูง", "emoji": "🔄", "persona": "flexible", "recommended": False},
    ]

    # ✅ สร้าง 10 choices ตาม persona ที่กำหนด
    persona_choices = build_persona_choices(
        choices=choices,
        processed_flights=processed_flights,
        processed_hotels=processed_hotels,
        processed_cars=processed_cars,
        transport_segments_data=transport_segments_data,
        nights=nights,
    )
    
    # Use persona choices if we have enough, otherwise fallback to sorted choices
    if len(persona_choices) >= 10:
        choices = persona_choices[:10]
    else:
        # Fallback: sort by price and take top 10
        choices.sort(key=lambda x: x.get("total_price") or float('inf'))
        choices = choices[:10]

    # Build final choice objects with labels and titles

    final_choices: List[Dict[str, Any]] = []
    for idx, choice_data in enumerate(choices):
        choice_id = idx + 1
        
        # ✅ ใช้ persona config ถ้ามี persona metadata
        persona = choice_data.get("persona")
        config = None
        if persona:
            # หา config ที่ตรงกับ persona
            for pc in persona_configs:
                if pc["persona"] == persona:
                    config = pc
                    break
        
        # Fallback: ใช้ config ตามลำดับ
        if not config:
            config = persona_configs[min(idx, len(persona_configs) - 1)]
        
        label = config["label"]
        emoji = config["emoji"]
        is_recommended = config.get("recommended", False)
        
        # ✅ Generate tags using Gemini
        tags = []
        try:
            from services.gemini_service import generate_choice_tags
            # Prepare choice data for tag generation
            choice_for_tags = {
                "id": choice_id,
                "is_non_stop": choice_data.get("is_non_stop", False),
                "total_price": choice_data.get("total_price"),
            }
            tags = generate_choice_tags(choice_for_tags, choices)
        except Exception:
            # Fallback: simple tags
            if choice_data.get("is_non_stop", False):
                tags.append("บินตรง")
            if choice_id == 1:
                tags.append("แนะนำ")
        
        # Determine title based on what's included (3 slots structure: Flight + Hotel + Transport)
        has_transport = bool(choice_data.get("transport"))
        transport_obj = choice_data.get("transport")
        transport_type = transport_obj.get("type") if isinstance(transport_obj, dict) else None
        
        # ✅ ทุก choice ต้องมีทั้ง Flight + Hotel (3 slots structure)
        if has_transport and transport_type:
            transport_label = "รถเช่า" if transport_type == "car_rental" else "ขนส่ง"
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (ไฟลต์ + ที่พัก + {transport_label})"
        else:
            title = f"{emoji} ช้อยส์ {choice_id} – {label} (ไฟลต์ + ที่พัก)"

        # Build ground transport message (Slot 3 info)
        # ✅ แสดงข้อมูลการขนส่งตาม segments
        transport_parts = []
        
        # ✅ แสดง transport ที่มีข้อมูล
        if has_transport and transport_type:
            if transport_type == "car_rental":
                transport_parts.append("🚗 มีรถเช่า (จาก Amadeus)")
            else:
                transport_parts.append(f"🚗 มี{transport_type}")
        
        # ✅ ดึงข้อมูล transport segments
        transport_segments = transport_obj.get("segments", []) if isinstance(transport_obj, dict) else []
        
        if transport_segments:
            transport_parts.append("")
            transport_parts.append("📋 ข้อมูลการขนส่งระหว่างเมือง:")
            
            # ✅ แสดงข้อมูลการขนส่งในแต่ละ segment
            for seg_data in transport_segments:
                seg_num = seg_data.get("segment", 1)
                from_city = seg_data.get("from", "N/A")
                to_city = seg_data.get("to", "N/A")
                
                transport_parts.append("")
                transport_parts.append(f"📍 Segment {seg_num}: {from_city} → {to_city}")
                
                # รถไฟ (Train)
                train_status = seg_data.get("train", {})
                if train_status.get("available"):
                    train_data = train_status.get("data", [])
                    if train_data:
                        train_info = train_data[0] if train_data else {}
                        operator = train_info.get("operator", "รถไฟท้องถิ่น")
                        duration = train_info.get("duration", "2-4 ชั่วโมง")
                        note = train_info.get("note", "")
                        transport_parts.append(f"  ✅ 🚂 รถไฟ: {operator} (ระยะเวลา: {duration})")
                        if note:
                            transport_parts.append(f"     {note}")
                    else:
                        transport_parts.append(f"  ✅ 🚂 รถไฟ: {train_status.get('reason', 'พบข้อมูล')}")
                else:
                    transport_parts.append(f"  ❌ 🚂 รถไฟ: {train_status.get('reason', 'ไม่พบข้อมูล')}")
                
                # รถโดยสาร (Bus)
                bus_status = seg_data.get("bus", {})
                if bus_status.get("available"):
                    bus_data = bus_status.get("data", [])
                    if bus_data:
                        bus_info = bus_data[0] if bus_data else {}
                        operator = bus_info.get("operator", "รถโดยสารประจำทาง")
                        duration = bus_info.get("duration", "3-6 ชั่วโมง")
                        note = bus_info.get("note", "")
                        transport_parts.append(f"  ✅ 🚌 รถโดยสาร: {operator} (ระยะเวลา: {duration})")
                        if note:
                            transport_parts.append(f"     {note}")
                    else:
                        transport_parts.append(f"  ✅ 🚌 รถโดยสาร: {bus_status.get('reason', 'พบข้อมูล')}")
                else:
                    transport_parts.append(f"  ❌ 🚌 รถโดยสาร: {bus_status.get('reason', 'ไม่พบข้อมูล')}")
                
                # เรือ (Ferry)
                ferry_status = seg_data.get("ferry", {})
                if ferry_status.get("available"):
                    ferry_data = ferry_status.get("data", [])
                    if ferry_data:
                        ferry_info = ferry_data[0] if ferry_data else {}
                        operator = ferry_info.get("operator", "เรือข้ามฟาก")
                        duration = ferry_info.get("duration", "1-3 ชั่วโมง")
                        note = ferry_info.get("note", "")
                        transport_parts.append(f"  ✅ ⛴️ เรือ: {operator} (ระยะเวลา: {duration})")
                        if note:
                            transport_parts.append(f"     {note}")
                    else:
                        transport_parts.append(f"  ✅ ⛴️ เรือ: {ferry_status.get('reason', 'พบข้อมูล')}")
                else:
                    transport_parts.append(f"  ❌ ⛴️ เรือ: {ferry_status.get('reason', 'ไม่พบข้อมูล')}")
                
                # รถไฟฟ้า (Metro) - ไม่มี API
                metro_status = seg_data.get("metro", {})
                transport_parts.append(f"  ❌ 🚇 รถไฟฟ้า: {metro_status.get('reason', 'Amadeus API ไม่มี endpoint สำหรับรถไฟฟ้า')}")
        else:
            # Fallback: แสดงสถานะแบบเดิม (backward compatibility)
            transport_parts.append("")
            transport_parts.append("📋 สถานะการค้นหาข้อมูลการขนส่ง:")
            transport_parts.append("❌ ไม่พบข้อมูลการขนส่ง")
        
        if hotel_note:
            transport_parts.append("")
            transport_parts.append(hotel_note)
        
        ground_transport = "\n".join(transport_parts).strip()

        # Build itinerary (ทุก choice ต้องมีทั้ง Flight + Hotel)
        # ✅ ใช้ fallback itinerary เพื่อความเร็ว (ไม่ใช้ Gemini เพื่อหลีกเลี่ยง timeout)
        # Note: Gemini itinerary generation ใช้เวลานานและอาจทำให้ timeout
        # ใช้ fallback แทนเพื่อให้เสร็จภายใน 1 นาที
        
        # ใช้ fallback itinerary เพื่อความเร็ว
        itinerary_text = build_day_by_day(nights=nights, dest_label=dest_label)
        
        # Check if this is a non-stop flight
        flight_obj = choice_data.get("flight")
        is_non_stop_choice = choice_data.get("is_non_stop", False)
        if not is_non_stop_choice and flight_obj:
            segments = flight_obj.get("segments") or []
            is_non_stop_choice = len(segments) == 1
        
        # Extract transport info
        transport_price = choice_data.get("transport_price_thb")
        
        # Generate persona-specific tags
        persona_name = persona or config["persona"]
        persona_tags = _generate_persona_tags(persona_name, choice_data)
        tags.extend(persona_tags)
        
        final_choice = {
            "id": choice_id,
            "label": label,
            "title": title,
            "recommended": is_recommended,  # ✅ ใช้ recommended จาก persona config
            "persona": persona_name,  # ✅ เพิ่ม persona metadata
            "tags": tags,  # ✅ เพิ่ม tags จาก Gemini + persona
            # Slot 1: ไฟลต์บิน
            "flight": choice_data.get("flight"),
            # Slot 2: ที่พัก
            "hotel": choice_data.get("hotel"),
            # Slot 3: รถและเรือ
            "transport": transport_obj,
            "ground_transport": ground_transport,
            "itinerary": itinerary_text,
            "currency": "THB",
            "total_price": choice_data.get("total_price"),
            "price_breakdown": {
                "flight_total": choice_data.get("flight_price_thb"),
                "hotel_total": choice_data.get("hotel_price_thb"),
                "transport_total": transport_price,  # ✅ รวม transport price
                "currency": "THB",
            },
            "is_non_stop": is_non_stop_choice,  # ✅ เพิ่ม flag สำหรับ non-stop
        }
        final_choice["display_text"] = render_choice_text(final_choice)
        final_choices.append(final_choice)

    return final_choices
