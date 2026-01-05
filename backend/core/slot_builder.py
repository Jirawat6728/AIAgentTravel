"""
Slot-based choice builder for step-by-step trip planning.
Separates flight and hotel choices instead of combining them.
"""
from __future__ import annotations

from typing import Any, Dict, List

from core.plan_builder import (
    flight_offer_to_detailed,
    pick_hotel_fields,
    convert_to_thb,
)


def build_flight_choices(
    search_results: Dict[str, Any],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Build flight choices only (Slot 1) - 10 personas based on user requirements.
    Creates structured choices: Best Overall, Cheapest, Fastest, Non-stop, Prime Time,
    Night Flight, Baggage Friendly, Premium, Flexible, Promotional.
    """
    flights = (search_results or {}).get("flights", {}).get("data") or []
    raw_choices: List[Dict[str, Any]] = []
    
    # Step 1: Process all flights into raw choices with metadata
    for flight_offer in flights[:50]:  # Process more to have enough options
        f = flight_offer_to_detailed(flight_offer)
        flight_price_thb = None
        if f.get("price_total") and f.get("currency"):
            flight_price_thb, _ = convert_to_thb(float(f["price_total"]), f["currency"])
        
        if flight_price_thb is None:
            continue
        
        segments = f.get("segments") or []
        if not segments:
            continue
            
        first_seg = segments[0]
        last_seg = segments[-1]
        
        # Calculate total duration
        total_duration_sec = 0
        num_stops = len(segments) - 1
        is_non_stop = len(segments) == 1
        
        for seg in segments:
            duration_str = seg.get("duration") or ""
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
        
        # Extract departure/arrival times
        dep_time_str = first_seg.get("depart_time") or first_seg.get("departure_time") or ""
        arr_time_str = last_seg.get("arrive_time") or last_seg.get("arrival_time") or ""
        
        # Parse departure hour for time-based personas
        dep_hour = None
        if dep_time_str:
            try:
                # Handle ISO format "2024-12-31T08:30:00" or "08:30:00"
                time_part = dep_time_str.split("T")[-1] if "T" in dep_time_str else dep_time_str
                dep_hour = int(time_part.split(":")[0])
            except:
                pass
        
        # Extract cabin class from segments
        cabin_class = "ECONOMY"  # Default
        for seg in segments:
            cabin = seg.get("cabin") or seg.get("bookingClass") or seg.get("cabinCode") or ""
            if cabin:
                cabin_upper = cabin.upper()
                if "FIRST" in cabin_upper:
                    cabin_class = "FIRST"
                    break
                elif "BUSINESS" in cabin_upper or "J" in cabin_upper or "C" in cabin_upper:
                    cabin_class = "BUSINESS"
                elif "PREMIUM" in cabin_upper or "W" in cabin_upper:
                    cabin_class = "PREMIUM_ECONOMY"
                elif cabin_class == "ECONOMY":
                    cabin_class = "ECONOMY"
        
        # Extract flight details for baggage, flexibility info
        flight_details = f.get("details", {}) or {}
        
        # Check for baggage info
        has_baggage = True  # Default
        baggage_quantity = 0
        if flight_details and flight_details.get("checked_baggage"):
            has_baggage = True
            baggage_str = flight_details.get("checked_baggage", "")
            try:
                # Extract quantity from string like "2 piece(s)" or "1 piece(s)"
                baggage_quantity = int(baggage_str.split()[0]) if baggage_str.split() else 0
            except:
                pass
        
        # Check for changeable/refundable (flexibility)
        is_changeable = flight_details.get("changeable") if flight_details else None
        is_refundable = flight_details.get("refundable") if flight_details else None
        is_flexible = bool(is_changeable or is_refundable)
        
        raw_choices.append({
            "flight": f,
            "total_price": flight_price_thb,
            "currency": "THB",
            "total_duration_sec": total_duration_sec,
            "num_stops": num_stops,
            "is_non_stop": is_non_stop,
            "dep_hour": dep_hour,
            "dep_time_str": dep_time_str,
            "arr_time_str": arr_time_str,
            "cabin_class": cabin_class,
            "has_baggage": has_baggage,
            "baggage_quantity": baggage_quantity,
            "is_flexible": is_flexible,
            "is_changeable": is_changeable,
            "is_refundable": is_refundable,
            "origin": first_seg.get("from") or "",
            "dest": last_seg.get("to") or "",
            "segments": segments,
            "flight_details": flight_details,
        })
    
    if not raw_choices:
        return []
    
    # Step 2: Build 10 persona-based choices
    persona_choices = []
    
    # 1. 🥇 Best Overall (แนะนำ) - Balanced: price, time, stops
    # เลือกที่ราคาอยู่กลางๆ (30-70 percentile), non-stop หรือ stops น้อย, เวลาดี
    sorted_by_price = sorted(raw_choices, key=lambda x: x["total_price"])
    price_range = [sorted_by_price[int(len(sorted_by_price) * 0.3)], sorted_by_price[int(len(sorted_by_price) * 0.7) - 1] if len(sorted_by_price) > 1 else sorted_by_price[0]]
    best_overall_candidates = [
        c for c in raw_choices 
        if price_range[0]["total_price"] <= c["total_price"] <= price_range[1]["total_price"]
        and (c["is_non_stop"] or c["num_stops"] <= 1)
        and (c["dep_hour"] is None or 6 <= c["dep_hour"] <= 22)
    ]
    if best_overall_candidates:
        best_overall = max(best_overall_candidates, key=lambda x: (1 if x["is_non_stop"] else 0) * 10 - x["total_duration_sec"] / 3600)
    else:
        best_overall = sorted_by_price[len(sorted_by_price) // 2] if sorted_by_price else raw_choices[0]
    
    # 2. 💰 ถูกที่สุด
    cheapest = sorted_by_price[0]
    
    # 3. ⚡ เร็วที่สุด - Shortest duration
    fastest = min(raw_choices, key=lambda x: x["total_duration_sec"])
    
    # 4. 🛫 บินตรง - Non-stop only (strict: must be non-stop, otherwise skip this choice)
    non_stop_candidates = [c for c in raw_choices if c["is_non_stop"]]
    non_stop = min(non_stop_candidates, key=lambda x: x["total_price"]) if non_stop_candidates else None  # None if no non-stop flights
    
    # 5. 🕘 เวลาออกดี (Prime Time) - 6:00-10:00 AM
    prime_time_candidates = [c for c in raw_choices if c["dep_hour"] and 6 <= c["dep_hour"] <= 10]
    prime_time = min(prime_time_candidates, key=lambda x: x["total_price"]) if prime_time_candidates else best_overall
    
    # 6. 🌙 ไฟท์กลางคืน - 22:00-6:00
    night_candidates = [c for c in raw_choices if c["dep_hour"] and (c["dep_hour"] >= 22 or c["dep_hour"] < 6)]
    night_flight = min(night_candidates, key=lambda x: x["total_price"]) if night_candidates else cheapest
    
    # 7. 🎒 กระเป๋าคุ้ม - Flights with good baggage allowance
    baggage_candidates = [c for c in raw_choices if c.get("baggage_quantity", 0) >= 2 or c.get("has_baggage")]
    if baggage_candidates:
        baggage_friendly = min(baggage_candidates, key=lambda x: x["total_price"])
                else:
        baggage_friendly = sorted_by_price[min(3, len(sorted_by_price) - 1)]  # 4th cheapest (usually has baggage)
    
    # 8. 🛋️ สบายกว่า (Premium) - Business/Premium Economy or higher price range
    premium_candidates = [c for c in raw_choices if c["cabin_class"] in ["BUSINESS", "PREMIUM_ECONOMY", "FIRST"]]
    if not premium_candidates:
        # Fallback: top 20% by price
        premium_candidates = sorted_by_price[int(len(sorted_by_price) * 0.8):]
    premium = min(premium_candidates, key=lambda x: x["total_price"]) if premium_candidates else sorted_by_price[-1] if sorted_by_price else raw_choices[0]
    
    # 9. 🔁 เปลี่ยน/คืนง่าย - Flights with flexible conditions
    flexible_candidates = [c for c in raw_choices if c.get("is_flexible") or c.get("is_changeable") or c.get("is_refundable")]
    if not flexible_candidates:
        # Fallback: non-stop or cheaper flights (usually more flexible)
        flexible_candidates = [c for c in raw_choices if c["is_non_stop"] or c["total_price"] <= cheapest["total_price"] * 1.15]
    flexible = min(flexible_candidates, key=lambda x: x["total_price"]) if flexible_candidates else cheapest
    
    # 10. 🎁 มีโปรโมชั่น - Usually cheapest or those with special pricing
    promotional = cheapest  # Could be enhanced to detect actual promotions
    
    # Step 3: Build final choices with persona metadata
    persona_configs = [
        {"id": 1, "emoji": "🥇", "label": "แนะนำ", "persona": "best_overall", "recommended": True, "choice": best_overall, "required": True},
        {"id": 2, "emoji": "💰", "label": "ถูกที่สุด", "persona": "cheapest", "recommended": False, "choice": cheapest, "required": True},
        {"id": 3, "emoji": "⚡", "label": "เร็วที่สุด", "persona": "fastest", "recommended": False, "choice": fastest, "required": True},
        {"id": 4, "emoji": "🛫", "label": "บินตรง", "persona": "non_stop", "recommended": False, "choice": non_stop, "required": False},  # Optional: only show if non-stop exists
        {"id": 5, "emoji": "🕘", "label": "เวลาออกดี", "persona": "prime_time", "recommended": False, "choice": prime_time, "required": True},
        {"id": 6, "emoji": "🌙", "label": "ไฟท์กลางคืน", "persona": "night_flight", "recommended": False, "choice": night_flight, "required": True},
        {"id": 7, "emoji": "🎒", "label": "กระเป๋าคุ้ม", "persona": "baggage_friendly", "recommended": False, "choice": baggage_friendly, "required": True},
        {"id": 8, "emoji": "🛋️", "label": "สบายกว่า", "persona": "premium", "recommended": False, "choice": premium, "required": True},
        {"id": 9, "emoji": "🔁", "label": "เปลี่ยน/คืนง่าย", "persona": "flexible", "recommended": False, "choice": flexible, "required": True},
        {"id": 10, "emoji": "🎁", "label": "มีโปรโมชั่น", "persona": "promotional", "recommended": False, "choice": promotional, "required": True},
    ]
    
    final_choices = []
    for config in persona_configs:
        # Skip choice if it's optional and choice is None (e.g., no non-stop flights)
        if not config.get("required", True) and config["choice"] is None:
            continue
        
        # Also skip if choice is None for any reason
        if config["choice"] is None:
            continue
        
        choice_data = config["choice"]
        
        # Additional validation: For non-stop persona, must be truly non-stop
        if config["persona"] == "non_stop" and not choice_data.get("is_non_stop", False):
            continue  # Skip if somehow assigned a non-non-stop flight
        
        flight_obj = choice_data["flight"]
        segments = choice_data["segments"]
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}
        
        # Format duration
        hours = choice_data["total_duration_sec"] // 3600
        minutes = (choice_data["total_duration_sec"] % 3600) // 60
        duration_str = f"{hours}ชม{minutes}นาที" if hours > 0 else f"{minutes}นาที"
        
        origin = choice_data["origin"]
        dest = choice_data["dest"]
        dep_time = choice_data["dep_time_str"]
        arr_time = choice_data["arr_time_str"]
        
        # Build tags based on persona and flight characteristics
        tags = []
        if config.get("recommended", False):
            tags.append("แนะนำ")
        if choice_data["is_non_stop"]:
            tags.append("บินตรง")
        if config["persona"] == "cheapest":
            tags.append("ถูกสุด")
        if config["persona"] == "fastest":
            tags.append("เร็วสุด")
        if config["persona"] == "prime_time":
            tags.append("เวลาออกดี")
        if config["persona"] == "night_flight":
            tags.append("ไฟท์กลางคืน")
        if config["persona"] == "baggage_friendly":
            tags.append("กระเป๋าคุ้ม")
        if config["persona"] == "flexible":
            tags.append("ยืดหยุ่น")
        if config["persona"] == "promotional":
            tags.append("โปรโมชั่น")
        
        # Add cabin class tag
        cabin_class = choice_data["cabin_class"]
        if cabin_class == "BUSINESS":
            tags.append("Business")
        elif cabin_class == "PREMIUM_ECONOMY":
            tags.append("Premium Economy")
        elif cabin_class == "FIRST":
            tags.append("First Class")
        else:
            tags.append("Economy")  # Default to Economy
        
        # Build title (will be updated after re-numbering)
        title = f"{config['emoji']} ช้อยส์ที่ {config['id']} — {config['label']}"
        
        final_choices.append({
            "id": config["id"],  # Will be re-numbered later
            "original_id": config["id"],  # Keep original for reference
            "type": "flight",
            "slot": "flight",
            "flight": flight_obj,
            "total_price": choice_data["total_price"],
            "currency": "THB",
            "label": f"{origin} → {dest}",
            "title": title,
            "recommended": config.get("recommended", False),
            "tags": tags,
            "persona": config["persona"],
            "cabin_class": choice_data["cabin_class"],
            "display_text": (  # Will be updated with correct ID after re-numbering
                f"{title}\n"
                f"เวลา: {dep_time} - {arr_time} ({duration_str})\n"
                f"{'บินตรง' if choice_data['is_non_stop'] else str(choice_data['num_stops']) + ' ต่อเครื่อง'}\n"
                f"ชั้นที่นั่ง: {choice_data['cabin_class'].replace('_', ' ').title()}\n"
                f"{'กระเป๋า: ' + str(choice_data.get('baggage_quantity', 0)) + ' ใบ' if choice_data.get('baggage_quantity', 0) > 0 else 'ไม่มีกระเป๋าโหลด'}\n"
                f"ราคา: {choice_data['total_price']:,.0f} THB"
            ),
            "dep_time_str": dep_time,  # Store for later use in re-numbering
            "arr_time_str": arr_time,  # Store for later use in re-numbering
            "flight_price_thb": choice_data["total_price"],
            "total_duration_sec": choice_data["total_duration_sec"],
            "num_stops": choice_data["num_stops"],
            "is_non_stop": choice_data["is_non_stop"],
        })
    
    # Re-number IDs to be sequential (1, 2, 3, ...) after filtering
    # Also update titles and display_text to reflect new IDs
    for idx, choice in enumerate(final_choices):
        choice["id"] = idx + 1
        # Update title with new ID
        original_title_parts = choice.get("title", "").split(" — ")
        if len(original_title_parts) >= 2:
            emoji_and_label = original_title_parts[0].split(" ช้อยส์ที่ ")[0]  # Get emoji
            label = " — ".join(original_title_parts[1:])  # Get label (everything after first " — ")
            new_title = f"{emoji_and_label} ช้อยส์ที่ {idx + 1} — {label}"
            choice["title"] = new_title
            
            # Update display_text with new title
            # ใช้ dep_time_str และ arr_time_str ที่เก็บไว้แล้วใน choice
            dep_time = choice.get("dep_time_str", "")
            arr_time = choice.get("arr_time_str", "")
            
            # Fallback: ถ้ายังไม่มี ให้ดึงจาก flight segments
            if not dep_time or not arr_time:
                segments = choice.get("flight", {}).get("segments", [])
                if segments:
                    if not dep_time:
                        dep_time = segments[0].get("depart_time", "")
                    if not arr_time and len(segments) > 0:
                        arr_time = segments[-1].get("arrive_time", "")
            total_duration_sec = choice.get("total_duration_sec", 0)
            hours = total_duration_sec // 3600
            minutes = (total_duration_sec % 3600) // 60
            duration_str = f"{hours}ชม{minutes}นาที" if hours > 0 else f"{minutes}นาที"
            is_non_stop = choice.get("is_non_stop", False)
            num_stops = choice.get("num_stops", 0)
            cabin_class = choice.get("cabin_class", "ECONOMY")
            baggage_quantity = choice.get("flight", {}).get("details", {}).get("checked_baggage", "")
            baggage_qty = 0
            if baggage_quantity and isinstance(baggage_quantity, str):
                try:
                    baggage_qty = int(baggage_quantity.split()[0])
                except:
                    pass
            
            choice["display_text"] = (
                f"{new_title}\n"
                f"เวลา: {dep_time} - {arr_time} ({duration_str})\n"
                f"{'บินตรง' if is_non_stop else str(num_stops) + ' ต่อเครื่อง'}\n"
                f"ชั้นที่นั่ง: {cabin_class.replace('_', ' ').title()}\n"
                f"{'กระเป๋า: ' + str(baggage_qty) + ' ใบ' if baggage_qty > 0 else 'ไม่มีกระเป๋าโหลด'}\n"
                f"ราคา: {choice.get('total_price', 0):,.0f} THB"
            )
    
    return final_choices


def build_hotel_choices(
    search_results: Dict[str, Any],
    travel_slots: Dict[str, Any],
    selected_flight: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Build hotel choices only (Slot 2).
    Can filter based on selected flight if provided.
    """
    hotels = (search_results or {}).get("hotels", {}).get("data") or []
    nights = int(travel_slots.get("nights") or 3)
    choices: List[Dict[str, Any]] = []
    
    # If flight is selected, we can filter hotels by destination
    # (For now, just use all hotels - can add filtering later)
    
    for idx, hotel_item in enumerate(hotels[:limit]):
        h = pick_hotel_fields(hotel_item, nights=nights)
        hotel_price_thb = None
        if h.get("price_total") and h.get("currency"):
            hotel_price_thb, _ = convert_to_thb(float(h["price_total"]), h["currency"])
        
        if hotel_price_thb is not None:
            hotel_name = h.get("hotelName") or h.get("name") or "โรงแรม"
            stars = h.get("stars") or 0
            area = h.get("area") or h.get("city") or ""
            
            choices.append({
                "id": idx + 1,
                "type": "hotel",
                "slot": "hotel",  # Slot identifier
                "hotel": h,
                "total_price": hotel_price_thb,
                "currency": "THB",
                "label": hotel_name,
            "display_text": (
                    f"ที่พัก {idx + 1}: {hotel_name}\n"
                    f"{'⭐' * stars if stars else ''} {area}\n"
                    f"{nights} คืน ราคา: {hotel_price_thb:,.0f} THB"
                ),
                "hotel_price_thb": hotel_price_thb,
                "nights": nights,
            })
    
    return choices


def build_car_choices(
    search_results: Dict[str, Any],
    travel_slots: Dict[str, Any],
    selected_flight: Dict[str, Any] = None,
    selected_hotel: Dict[str, Any] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Build car rental choices (Slot 3).
    Returns empty list if no cars available (user can skip).
    """
    cars = (search_results or {}).get("cars", {}).get("data") or []
    choices = []
    
    for idx, car_offer in enumerate(cars[:limit]):
        # Extract car information
        car_name = car_offer.get("vehicle", {}).get("vehicleInfo", {}).get("category") or "รถเช่า"
        car_type = car_offer.get("vehicle", {}).get("vehicleInfo", {}).get("acrissCode") or ""
        price_info = car_offer.get("price", {})
        total_price = price_info.get("total") or 0
        currency = price_info.get("currencyCode") or "THB"
        
        # Convert to THB
        car_price_thb = total_price
        if currency != "THB":
            car_price_thb, _ = convert_to_thb(float(total_price), currency)
        
        if car_price_thb is None:
            continue
        
        choices.append({
            "id": idx + 1,
            "type": "car",
            "slot": "car",
            "car": car_offer,
            "total_price": car_price_thb,
            "currency": "THB",
            "label": f"{car_name} ({car_type})" if car_type else car_name,
            "display_text": (
                f"รถเช่า {idx + 1}: {car_name}\n"
                f"{'ประเภท: ' + car_type if car_type else ''}\n"
                f"ราคา: {car_price_thb:,.0f} THB"
            ),
            "car_price_thb": car_price_thb,
        })
    
    return choices


def build_trip_summary(
    slot_selections: Dict[str, Any],
    travel_slots: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Build trip summary from selected slots.
    slot_selections should contain: {"flight": {...}, "hotel": {...}}
    """
    selected_flight = slot_selections.get("flight")
    selected_hotel = slot_selections.get("hotel")
    
    total_price = 0
    summary_parts = []
    
    if selected_flight:
        f = selected_flight.get("flight") or selected_flight
        segments = f.get("segments") or []
        first_seg = segments[0] if segments else {}
        last_seg = segments[-1] if segments else {}
        origin = first_seg.get("from") or ""
        dest = last_seg.get("to") or ""
        flight_price = selected_flight.get("total_price") or selected_flight.get("flight_price_thb") or 0
        total_price += flight_price
        summary_parts.append(f"✈️ ไฟลต์: {origin} → {dest} ({flight_price:,.0f} THB)")
    
    if selected_hotel:
        h = selected_hotel.get("hotel") or selected_hotel
        hotel_name = h.get("hotelName") or h.get("name") or "โรงแรม"
        nights = selected_hotel.get("nights") or travel_slots.get("nights") or 3
        hotel_price = selected_hotel.get("total_price") or selected_hotel.get("hotel_price_thb") or 0
        total_price += hotel_price
        summary_parts.append(f"🏨 ที่พัก: {hotel_name} ({nights} คืน, {hotel_price:,.0f} THB)")
    
    summary_text = "\n".join(summary_parts) if summary_parts else "ยังไม่ได้เลือก"
    
    return {
        "summary_text": summary_text,
        "total_price": total_price,
        "currency": "THB",
        "selected_flight": selected_flight,
        "selected_hotel": selected_hotel,
    }

