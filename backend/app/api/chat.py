"""
เราเตอร์ API แชท
Endpoint ระดับ production พร้อมจัดการข้อผิดพลาดและงานพื้นหลัง
"""

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import json
import asyncio
import os
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any, Dict, Tuple
from app.models import UserSession, TripPlan
from app.models.trip_plan import SegmentStatus
from app.engine.agent import TravelAgent
from app.core.constants import FALLBACK_RESPONSE_EMPTY
from app.services.llm import LLMServiceWithMCP
from app.services.llm import IntentBasedLLM
from app.services.title import generate_chat_title
from app.storage.mongodb_storage import MongoStorage
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.exceptions import AgentException, StorageException, LLMException
from app.core.config import settings
from app.services.options_cache import get_options_cache
from app.services.tts_service import TTSService
from app.services.live_audio_service import LiveAudioService
from fastapi.responses import Response
import base64
import httpx

logger = get_logger(__name__)


async def _fetch_image_as_base64_data_url(url: str, timeout: float = 6.0) -> Optional[str]:
    """Fetch image from URL and return as data URL (base64). Returns None on failure."""
    if not url or not isinstance(url, str) or url.startswith("data:"):
        return url if (url and url.startswith("data:")) else None
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            r = await client.get(url)
            r.raise_for_status()
            ct = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            if "image" not in ct:
                ct = "image/jpeg"
            b64 = base64.b64encode(r.content).decode("ascii")
            return f"data:{ct};base64,{b64}"
    except Exception as e:
        logger.debug(f"Failed to fetch image as base64: {e}")
        return None


async def _convert_hotel_image_urls_to_base64(slot_choices: List[Dict]) -> None:
    """In-place: replace hotel.visuals.image_urls (HTTP URLs) with base64 data URLs (max 3 per hotel)."""
    for choice in slot_choices:
        if choice.get("category") != "hotel":
            continue
        hotel = choice.get("hotel") or {}
        visuals = hotel.get("visuals") or {}
        urls = visuals.get("image_urls") or []
        if not urls or not isinstance(urls, list):
            continue
        data_urls = []
        for url in urls[:3]:
            if not url or not isinstance(url, str):
                continue
            if url.startswith("data:"):
                data_urls.append(url)
                continue
            data_url = await _fetch_image_as_base64_data_url(url)
            if data_url:
                data_urls.append(data_url)
        if data_urls:
            if "visuals" not in choice["hotel"]:
                choice["hotel"]["visuals"] = {}
            choice["hotel"]["visuals"]["image_urls"] = data_urls

router = APIRouter(prefix="/api/chat", tags=["chat"])

# ✅ Helper function to safely write debug logs
def _calc_nights(check_in: Optional[str], check_out: Optional[str]) -> Optional[int]:
    """คำนวณจำนวนคืนจาก check_in/check_out ISO string — คืน None ถ้าข้อมูลไม่ครบหรือ parse ไม่ได้"""
    if not check_in or not check_out:
        return None
    try:
        ci = datetime.fromisoformat(check_in.replace("Z", "+00:00"))
        co = datetime.fromisoformat(check_out.replace("Z", "+00:00"))
        nights = (co - ci).days
        return nights if nights > 0 else None
    except (ValueError, AttributeError):
        return None


_DEBUG_LOG_ENABLED = os.getenv("DEBUG_LOG_ENABLED", "false").lower() == "true"
_DEBUG_LOG_MAX_BYTES = int(os.getenv("DEBUG_LOG_MAX_BYTES", str(10 * 1024 * 1024)))  # 10 MB default

def _write_debug_log(data: dict):
    """Write debug log only when DEBUG_LOG_ENABLED=true, with size-based rotation."""
    if not _DEBUG_LOG_ENABLED:
        return
    try:
        from pathlib import Path
        import logging.handlers as _lh
        debug_log_dir = Path(__file__).parent.parent.parent / 'data' / 'logs' / 'debug'
        debug_log_dir.mkdir(parents=True, exist_ok=True)
        debug_log_path = debug_log_dir / 'chat_debug.log'
        # Rotate if file exceeds max size
        if debug_log_path.exists() and debug_log_path.stat().st_size > _DEBUG_LOG_MAX_BYTES:
            backup = debug_log_path.with_suffix('.log.1')
            backup.unlink(missing_ok=True)
            debug_log_path.rename(backup)
        with open(debug_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception as e:
        logger.debug(f"Failed to write debug log: {e}")

async def _is_admin_user(user_id: str, storage) -> bool:
    """ตรวจสอบว่า user_id เป็น admin หรือไม่ (เช็กจาก DB เท่านั้น ไม่ hardcode)"""
    if not user_id or user_id == "anonymous":
        return False
    try:
        if hasattr(storage, 'mongo') and storage.mongo and hasattr(storage.mongo, 'db') and storage.mongo.db:
            user_data = await storage.mongo.db["users"].find_one({"user_id": user_id})
        elif hasattr(storage, 'db') and storage.db:
            user_data = await storage.db["users"].find_one({"user_id": user_id})
        elif hasattr(storage, 'users_collection') and storage.users_collection:
            user_data = await storage.users_collection.find_one({"user_id": user_id})
        else:
            return False
        return bool(user_data and user_data.get("is_admin"))
    except Exception as e:
        logger.warning(f"Failed to check admin status for user {user_id}: {e}")
        return False


# Initialize TTS service
_tts_service = None

def get_tts_service() -> TTSService:
    """Get or create TTS service instance"""
    global _tts_service
    if _tts_service is None:
        try:
            _tts_service = TTSService()
        except Exception as e:
            logger.warning(f"Failed to initialize TTS service: {e}")
            return None
    return _tts_service


class ChatRequest(BaseModel):
    """Request model for chat endpoint matching frontend"""
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")
    user_id: Optional[str] = None
    client_trip_id: Optional[str] = None  # ✅ Backward compatibility
    trip_id: Optional[str] = None  # ✅ trip_id: สำหรับ 1 ทริป (1 trip = หลาย chat ได้)
    chat_id: Optional[str] = None  # ✅ chat_id: สำหรับแต่ละแชท (1 chat = 1 chat_id)
    trigger: Optional[str] = "user_message"
    mode: Optional[str] = "normal"  # ✅ 'normal' = ผู้ใช้เลือกช้อยส์เอง, 'agent' = AI ดำเนินการเอง

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"normal", "agent", None}
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed - {None}}")
        return v


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Agent's response in Thai")
    session_id: str = Field(..., description="Session identifier")
    # Add other fields the frontend might expect from agent state
    agent_state: Optional[dict] = None
    plan_choices: Optional[list] = None
    slot_choices: Optional[list] = None
    slot_intent: Optional[str] = None
    current_plan: Optional[dict] = None
    travel_slots: Optional[dict] = None
    trip_title: Optional[str] = None


def _map_option_for_frontend(option: Dict[str, Any], index: int = 0, slot_context: str = None, user_visa_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Map internal StandardizedItem fields to Frontend-friendly UI Card props.
    Ensures that cards display Title, Price, and Details correctly (~90% accuracy).
    user_visa_profile: Optional dict with has_visa, visa_type, visa_expiry_date, etc. for visa_warning personalization.
    """
    # ✅ Defensive: ensure option is dict and required keys have safe defaults
    if not isinstance(option, dict):
        option = {}
    raw_data = option.get("raw_data")
    if raw_data is not None and not isinstance(raw_data, dict):
        raw_data = {}
    option = dict(option)
    if raw_data is not None:
        option["raw_data"] = raw_data
    # 1. Base props
    tags = option.get("tags")
    if not isinstance(tags, list):
        tags = []
    # กรองแท็กที่ไม่ต้องการ (Amadeus, ราคาจริง, จองได้ทันที)
    _HIDDEN_TAGS = {"Amadeus", "ราคาจริง", "จองได้ทันที"}
    tags = [t for t in tags if t not in _HIDDEN_TAGS]
    recommended = bool(option.get("recommended", False))
    category = option.get("category")
    
    # Smart Label based on category
    type_label = "ช้อยส์"
    if category == "flight": type_label = "เที่ยวบิน"
    elif category == "hotel": type_label = "ที่พัก"
    elif category == "transfer" or category == "transport": type_label = "การเดินทาง"
    
    # Construct a rich title (ไม่ append tags ใน title — แสดงแยกในแท็ก pills บนการ์ด)
    tags_suffix = ""
    display_name = option.get("display_name", "Unknown Option")
    long_desc = option.get("description")
    
    final_description = display_name
    if long_desc and long_desc != display_name:
        final_description = f"{display_name}\n{long_desc}"
    
    # ✅ Use numeric index (1-based) instead of ID (place_id, etc.) for user-friendly selection
    # Store original ID in raw_data for backend processing
    original_id = option.get("id")
    numeric_id = str(index + 1)  # 1-based index for display
    
    # ✅ Defensive: price/currency always valid for display
    try:
        price_val = float(option.get("price_amount", 0) or 0)
    except (TypeError, ValueError):
        price_val = 0.0
    currency_val = option.get("currency") or "THB"
    if not isinstance(currency_val, str):
        currency_val = "THB"
    ui_option = {
        "id": numeric_id,
        "title": f"{type_label} {index + 1}{tags_suffix}",
        "subtitle": str(option.get("provider") or ""),
        "price": price_val,
        "total_price": price_val if price_val > 0 else None,
        "currency": currency_val,
        "description": final_description if category != "flight" else None,
        "details": [],
        "image": option.get("image_url"),
        "tags": tags,
        "recommended": recommended,
        "raw": option,
        "category": category,
        "_original_id": original_id,
    }
    raw_data = option.get("raw_data") or {}

    # 2. Category-specific mapping for rich UI (PlanChoiceCard.jsx)
    if category == "flight":
        itineraries = raw_data.get("itineraries", [])
        if itineraries:
            mapped_segments = []

            # Helper to process an itinerary
            def process_itinerary(itinerary, direction_label):
                segs = itinerary.get("segments", [])
                for i, seg in enumerate(segs):
                    # Smart label for connecting flights: "BKK->HKG (Leg 1)"
                    if len(segs) > 1:
                        leg_label = f"{direction_label} (ต่อเครื่อง {i+1})"
                    else:
                        leg_label = direction_label

                    dep = seg.get("departure") or {}
                    arr = seg.get("arrival") or {}
                    at_dep = dep.get("at") or ""
                    at_arr = arr.get("at") or ""
                    depart_time = at_dep.split("T")[-1][:5] if isinstance(at_dep, str) and "T" in at_dep else (at_dep[:5] if isinstance(at_dep, str) and len(at_dep) >= 5 else "")
                    arrive_time = at_arr.split("T")[-1][:5] if isinstance(at_arr, str) and "T" in at_arr else (at_arr[:5] if isinstance(at_arr, str) and len(at_arr) >= 5 else "")
                    mapped_seg = {
                        "from": dep.get("iataCode"),
                        "to": arr.get("iataCode"),
                        "depart_time": depart_time,
                        "arrive_time": arrive_time,
                        "depart_at": at_dep if at_dep else None,
                        "arrive_at": at_arr if at_arr else None,
                        "duration": seg.get("duration"),
                        "carrier": seg.get("carrierCode"),
                        "flight_number": seg.get("number"),
                        "aircraft_code": (seg.get("aircraft") or {}).get("code"),
                        "direction": leg_label
                    }
                    mapped_segments.append(mapped_seg)

            # Determine direction label based on Slot Context
            default_label = "เที่ยวบิน"
            if slot_context == "flights_outbound":
                default_label = "ขาไป"
            elif slot_context == "flights_inbound":
                default_label = "ขากลับ"

            if len(itineraries) == 1:
                # One Way or Split Search: Use context to label
                process_itinerary(itineraries[0], default_label)
            elif len(itineraries) >= 2:
                # Round Trip (Bundled): First is Outbound, Second is Return
                process_itinerary(itineraries[0], "ขาไป")
                process_itinerary(itineraries[1], "ขากลับ")
                # Handle extra itineraries
                for i in range(2, len(itineraries)):
                     process_itinerary(itineraries[i], f"Flight {i+1}")

            flight_price = option.get("price_amount")
            if flight_price is None and raw_data:
                price_dict = raw_data.get("price", {})
                flight_price = price_dict.get("total") or price_dict.get("grandTotal")
                if flight_price is not None:
                    try:
                        flight_price = float(flight_price)
                    except (TypeError, ValueError):
                        flight_price = None
            ui_option["flight"] = {
                "price_total": flight_price,
                "currency": option.get("currency") or (raw_data.get("price", {}) or {}).get("currency") or "THB",
                "segments": mapped_segments
            }
            # ชื่อการ์ดชัดเจน: เที่ยวบิน 1: BKK → NRT
            if mapped_segments:
                first_from = mapped_segments[0].get("from") or ""
                last_to = mapped_segments[-1].get("to") or ""
                if first_from and last_to:
                    ui_option["title"] = f"{type_label} {index + 1}: {first_from} → {last_to}{tags_suffix}"
                # ส่ง direction ให้ frontend แสดงแท็ก ขาไป/ขากลับ
                first_dir = mapped_segments[0].get("direction") or ""
                if "ขาไป" in first_dir:
                    ui_option["flight_direction"] = "outbound"
                elif "ขากลับ" in first_dir:
                    ui_option["flight_direction"] = "inbound"
            
            # Enhanced Info from Data Aggregator
            enhanced_info = raw_data.get("enhanced_info", {})
            
            # Add Cabin info if available in travelerPricings (or enhanced_info)
            traveler_pricings = raw_data.get("travelerPricings", [{}])
            if traveler_pricings:
                fare_details = traveler_pricings[0].get("fareDetailsBySegment", [{}])
                if fare_details:
                    ui_option["flight"]["cabin"] = enhanced_info.get("cabin") or fare_details[0].get("cabin", "ECONOMY")
            
            # Add Baggage info
            if enhanced_info.get("baggage"):
                ui_option["flight"]["baggage"] = enhanced_info.get("baggage")
            
            # Pass refund/change info to flight_details (separate key)
            ui_option["flight_details"] = {
                "price_per_person": option.get("price_amount"),  # Simplified
                "changeable": enhanced_info.get("changeable"),
                "refundable": enhanced_info.get("refundable"),
                "change_fee": enhanced_info.get("change_fee") or ("ค่าธรรมเนียมตามเงื่อนไขสายการบิน" if enhanced_info.get("changeable") else None),
                "hand_baggage": enhanced_info.get("hand_baggage") or "1 กระเป๋าถือ (7 kg)",
                "checked_baggage": enhanced_info.get("baggage"),
                "meals": enhanced_info.get("meals") or ("รวมอาหาร" if "BUSINESS" in str(enhanced_info.get("cabin")) else "อาหารว่าง/ซื้อเพิ่ม"),
                "seat_selection": enhanced_info.get("seat_selection") or "อาจมีค่าธรรมเนียม",
                "seat_width": enhanced_info.get("seat_width"),
                "wifi": enhanced_info.get("wifi") or "ตรวจสอบบนเครื่อง",
                "power_outlet": enhanced_info.get("power_outlet") or "ตรวจสอบบนเครื่อง",
                "co2_emissions_kg": enhanced_info.get("co2_emissions_kg"),  # from data_aggregator
                "on_time_performance": enhanced_info.get("on_time_performance"),
                "promotions": enhanced_info.get("promotions") or []
            }

            # Transit Visa Warning Logic + 🛂 Profile-based visa hint for search/planning
            # If flight has legs with stops in different countries than Origin/Dest, warn about visa.
            base_warning = None
            if len(mapped_segments) > 1:
                 if enhanced_info.get("transit_warning"):
                     base_warning = enhanced_info.get("transit_warning")
                 else:
                     base_warning = "ตรวจสอบวีซ่า Transit"
            if "Self-Transfer" in tags:
                 base_warning = "⚠️ Self-Transfer: ต้องใช้วีซ่า / รับกระเป๋าเอง"
            if base_warning:
                 # Personalize using user profile (visa transfer section) for filtering/planning
                 profile = user_visa_profile or {}
                 if profile.get("has_visa"):
                     expiry = profile.get("visa_expiry_date") or ""
                     hint = f"คุณมีวีซ่าในโปรไฟล์" + (f" (หมดอายุ {expiry})" if expiry else "") + " - ตรวจสอบประเทศปลายทาง/Transit ว่าครอบคลุมหรือไม่"
                     ui_option["flight"]["visa_warning"] = f"{base_warning}\n💡 {hint}"
                 else:
                     ui_option["flight"]["visa_warning"] = f"{base_warning}\n💡 คุณยังไม่มีวีซ่าในโปรไฟล์ - อัพเดทได้ที่ Profile เพื่อช่วยกรองเที่ยวบิน"

    elif category == "hotel":
        # Support for: 1. MergedHotelOption, 2. Google discovery, 3. Basic Amadeus
        
        if raw_data.get("source") == "amadeus_google_merged":
            # รวม Amadeus + Google — ตรงที่ Amadeus ไม่มี (รูป, รีวิว, ระดับดาว, ชื่อไทย) ใช้จาก Google แล้ว
            booking = raw_data.get("booking", {})
            pricing = booking.get("pricing", {})
            visuals = raw_data.get("visuals", {})
            loc = raw_data.get("location", {})
            
            addr = loc.get("address") or ""
            star = raw_data.get("star_rating") or visuals.get("review_score")
            hotel_total = pricing.get("total_amount") or option.get("price_amount")
            if hotel_total is not None:
                try:
                    hotel_total = float(hotel_total)
                except (TypeError, ValueError):
                    hotel_total = pricing.get("total_amount")
            hotel_name_merged = raw_data.get("hotel_name") or option.get("display_name") or ""
            # Amenities + nights for frontend (ภาพ, ดาว, รูปแบบห้อง, จำนวนคืน, ส่วนกลาง, เช็คอิน/เอาท์, ราคาแยก/รวม)
            amenities_raw = raw_data.get("amenities") or {}
            if hasattr(amenities_raw, "model_dump"):
                amenities_raw = amenities_raw.model_dump()
            nights = None
            if booking.get("check_in_date") and booking.get("check_out_date"):
                try:
                    from datetime import datetime
                    d1 = datetime.strptime(booking["check_in_date"][:10], "%Y-%m-%d")
                    d2 = datetime.strptime(booking["check_out_date"][:10], "%Y-%m-%d")
                    nights = max(1, (d2 - d1).days)
                except Exception:
                    pass
            ui_option["hotel"] = {
                "hotelName": hotel_name_merged or None,
                "address": addr,
                "location": {"address": addr},
                "price_total": hotel_total,
                "currency": pricing.get("currency") or option.get("currency") or "THB",
                "rating": visuals.get("review_score") or star,
                "star_rating": star,
                "visuals": visuals,
                "amenities": amenities_raw,
                "nights": nights,
                "booking": {
                    "check_in_date": booking.get("check_in_date"),
                    "check_out_date": booking.get("check_out_date"),
                    "guests": booking.get("guests"),
                    "room": booking.get("room", {}),
                    "policies": {
                        "meal_plan": booking.get("policies", {}).get("meal_plan"),
                        "is_refundable": booking.get("policies", {}).get("is_refundable"),
                    },
                    "pricing": {
                        "price_per_night": pricing.get("price_per_night"),
                        "taxes_and_fees": pricing.get("taxes_and_fees"),
                        "total_amount": pricing.get("total_amount"),
                        "currency": pricing.get("currency"),
                    },
                },
            }
            ui_option["price"] = pricing.get("total_amount")
            ui_option["currency"] = pricing.get("currency")
            if visuals.get("image_urls"):
                ui_option["image"] = visuals["image_urls"][0]
            ui_option["subtitle"] = "จองผ่าน Amadeus – ข้อมูลโดย Google"
            details = []
            if pricing.get("price_per_night"):
                details.append(f"฿{pricing['price_per_night']:,}/คืน")
            if visuals.get("review_score"):
                details.append(f"⭐ {visuals['review_score']} ({visuals.get('review_count', 0)} รีวิว)")
            if booking.get("policies", {}).get("meal_plan"):
                details.append(f"🍴 {booking['policies']['meal_plan']}")
            ui_option["details"] = details
            hotel_name_short = (hotel_name_merged or "")[:36]
            if hotel_name_short:
                ui_option["title"] = f"{type_label} {index + 1}: {hotel_name_short}{tags_suffix}"

        elif raw_data.get("google_place"):
            # ข้อมูลจาก Google Places เท่านั้น (ไม่มี Amadeus)
            place = raw_data.get("google_place", {})
            addr = place.get("formatted_address") or ""
            # Build image_urls from Google Place photos (Nearby/Text Search include photos)
            image_urls = []
            if settings.google_maps_api_key and place.get("photos"):
                for p in place["photos"][:5]:
                    ref = p.get("photo_reference")
                    if ref:
                        image_urls.append(
                            f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={ref}&key={settings.google_maps_api_key}"
                        )
            ui_option["hotel"] = {
                "hotelName": place.get("name") or ui_option["title"],
                "cityCode": place.get("_resolved_city"),
                "address": addr,
                "location": {"address": addr},
                "price_total": None,
                "currency": ui_option["currency"],
                "rating": place.get("rating"),
                "visuals": {
                    "review_score": place.get("rating"),
                    "review_count": place.get("user_ratings_total"),
                    "image_urls": image_urls,
                },
            }
            ui_option["subtitle"] = "Google Places (ไม่ใช่ราคาจองจริง)"
            name_short = (place.get("name") or "")[:36]
            if name_short:
                ui_option["title"] = f"{type_label} {index + 1}: {name_short}{tags_suffix}"
        else:
            # Raw Amadeus เท่านั้น (ไม่มี Google merge — ภาพ/รีวิว/ระดับดาวจะไม่มี; ใช้ได้จาก merge ใน data_aggregator)
            hotel_data = raw_data.get("hotel", {})
            offers = raw_data.get("offers", [])
            first_offer = offers[0] if offers else {}
            price_from_offer = first_offer.get("price", {}) if first_offer else {}
            total_val = price_from_offer.get("total") or price_from_offer.get("total_amount") or option.get("price_amount") or ui_option["price"]
            if total_val is not None:
                try:
                    hotel_price_real = float(total_val)
                except (TypeError, ValueError):
                    hotel_price_real = ui_option["price"]
            else:
                hotel_price_real = ui_option["price"]
            base_val = price_from_offer.get("base")
            taxes_val = 0.0
            if "taxes" in price_from_offer:
                for t in price_from_offer.get("taxes", []):
                    taxes_val += float(t.get("amount", 0))
            elif base_val is not None and hotel_price_real is not None:
                taxes_val = hotel_price_real - float(base_val)
            check_in = first_offer.get("checkInDate") or first_offer.get("check_in_date") or raw_data.get("check_in_date")
            check_out = first_offer.get("checkOutDate") or first_offer.get("check_out_date") or raw_data.get("check_out_date")
            nights = None
            if check_in and check_out:
                try:
                    from datetime import datetime
                    d1 = datetime.strptime(str(check_in)[:10], "%Y-%m-%d")
                    d2 = datetime.strptime(str(check_out)[:10], "%Y-%m-%d")
                    nights = max(1, (d2 - d1).days)
                except Exception:
                    pass
            room_est = first_offer.get("room", {}).get("typeEstimated", {}) or {}
            room_type = room_est.get("category") or first_offer.get("room", {}).get("description", {}).get("text") or "Standard"
            price_per_night = (hotel_price_real / nights) if (nights and nights > 0 and hotel_price_real is not None) else hotel_price_real
            booking_obj = {
                "check_in_date": check_in,
                "check_out_date": check_out,
                "guests": first_offer.get("guests", {}).get("adults", 1),
                "room": {
                    "room_type": room_type,
                    "description": first_offer.get("room", {}).get("description", {}).get("text"),
                    "bed_type": room_est.get("bedType"),
                    "bed_quantity": room_est.get("beds", 1),
                },
                "policies": {"meal_plan": "Room Only", "is_refundable": False},
                "pricing": {
                    "price_per_night": round(price_per_night, 2) if price_per_night is not None else None,
                    "taxes_and_fees": round(taxes_val, 2) if taxes_val else 0,
                    "total_amount": hotel_price_real,
                    "currency": price_from_offer.get("currency") or ui_option["currency"],
                },
            }
            addr = ", ".join(hotel_data.get("address", {}).get("lines", []))
            name_from_raw = hotel_data.get("name") or raw_data.get("name") or option.get("display_name") or ""
            raw_amenities = hotel_data.get("amenities", []) or []
            tags_upper = [str(a).upper() for a in raw_amenities]
            amenities_obj = {
                "has_wifi": any("WIFI" in t for t in tags_upper),
                "has_pool": any("POOL" in t or "SWIM" in t for t in tags_upper),
                "has_fitness": any("GYM" in t or "FITNESS" in t for t in tags_upper),
                "has_parking": any("PARKING" in t for t in tags_upper),
                "has_spa": any("SPA" in t for t in tags_upper),
                "has_air_conditioning": any("AIR" in t and "CONDITION" in t for t in tags_upper),
                "original_list": raw_amenities[:15],
            }
            ui_option["hotel"] = {
                "hotelName": name_from_raw or ui_option["title"],
                "cityCode": hotel_data.get("cityCode"),
                "address": addr,
                "location": {"address": addr},
                "price_total": hotel_price_real,
                "currency": ui_option["currency"],
                "rating": hotel_data.get("rating"),
                "star_rating": hotel_data.get("rating"),
                "nights": nights,
                "amenities": amenities_obj,
                "booking": booking_obj,
            }
            name_short = (name_from_raw or "")[:36]
            if name_short:
                ui_option["title"] = f"{type_label} {index + 1}: {name_short}{tags_suffix}"

    # ✅ Hotel: fallback ชื่อโรงแรมจาก display_name ถ้า hotelName ยังเป็น generic (ที่พัก 1, ที่พัก 2, Unknown Hotel)
    if category == "hotel" and ui_option.get("hotel"):
        h = ui_option["hotel"]
        name = (h.get("hotelName") or "").strip()
        fallback = option.get("display_name") or raw_data.get("name") or raw_data.get("hotel_name")
        use_fallback = fallback and str(fallback).strip() and (
            not name or name == "Unknown Hotel" or (type_label and name.startswith(type_label))
        )
        if use_fallback:
            h["hotelName"] = str(fallback).strip()
            short = (str(fallback).strip())[:36]
            if short:
                ui_option["title"] = f"{type_label} {index + 1}: {short}{tags_suffix}"

    if category in ("transfer", "transport"):
        raw_data = option.get("raw_data", {}) or option
        route_parts = []
        if option.get("display_name"):
            route_parts.append(option["display_name"])
        origin = raw_data.get("origin") or option.get("origin")
        dest = raw_data.get("destination") or option.get("destination")
        if origin and dest:
            route_parts.append(f"{origin} → {dest}")
        route = " | ".join(route_parts) if route_parts else (raw_data.get("route") or (option.get("description") or "")[:80])
        ui_option["transport"] = {
            "type": raw_data.get("type") or option.get("category") or "transfer",
            "route": route or (option.get("description") or "")[:80],
            "price": option.get("price_amount") or raw_data.get("price") or option.get("price"),
            "price_amount": option.get("price_amount") or raw_data.get("price"),
            "currency": option.get("currency") or raw_data.get("currency") or "THB",
            "duration": raw_data.get("duration") or option.get("duration"),
            "distance": raw_data.get("distance") or option.get("distance"),
            "provider": raw_data.get("provider") or option.get("provider") or raw_data.get("company"),
            "company": raw_data.get("company") or option.get("company"),
            "vehicle_type": raw_data.get("vehicle_type") or option.get("vehicle_type") or raw_data.get("car_type"),
            "car_type": raw_data.get("car_type") or option.get("car_type"),
            "seats": raw_data.get("seats") or option.get("seats") or raw_data.get("capacity"),
            "capacity": raw_data.get("capacity") or option.get("capacity"),
            "price_per_day": raw_data.get("price_per_day") or option.get("price_per_day"),
            "details": raw_data.get("details") or option.get("details"),
            "features": raw_data.get("features") or raw_data.get("amenities") or option.get("amenities"),
            "amenities": raw_data.get("amenities") or raw_data.get("features"),
            "note": raw_data.get("note") or option.get("note"),
            "description": option.get("description") or raw_data.get("description") or option.get("display_name"),
        }
        if option.get("description") and not ui_option["transport"]["route"]:
            ui_option["transport"]["route"] = (option["description"] or "")[:120]
        ui_option["price"] = ui_option["transport"].get("price") or ui_option["transport"].get("price_amount") or ui_option["price"]
        route_short = (ui_option["transport"].get("route") or "")[:40]
        if route_short:
            ui_option["title"] = f"{type_label} {index + 1}: {route_short}{tags_suffix}"

    # 3. Build Details tags for generic display (do not overwrite category-specific details)
    existing_details = ui_option.get("details", [])
    if not (category == "hotel" and len(existing_details) > 0):
        details = []
        if option.get("duration"):
            details.append(f"⏱ {option['duration']}")
        if option.get("rating"):
            details.append(f"⭐ {option['rating']}")
        if option.get("start_time"):
            time_str = option['start_time'].split('T')[-1][:5] if 'T' in str(option.get('start_time', '')) else str(option.get("start_time", ""))
            details.append(f"🕒 {time_str}")
        ui_option["details"] = details if details else existing_details

    return ui_option


async def _get_user_visa_profile(storage, user_id: str) -> Dict[str, Any]:
    """Fetch user visa section from profile for flight/transfer visa filtering and warnings.
    Uses visa_records when present; falls back to legacy visa_type/visa_number. Includes
    active_visas and visa_warnings (linked_passport) for agent/UI."""
    if not user_id or user_id == "anonymous" or not storage:
        return {}
    try:
        if hasattr(storage, "db") and storage.db:
            users_collection = storage.db["users"]
        elif hasattr(storage, "users_collection") and storage.users_collection:
            users_collection = storage.users_collection
        else:
            return {}
        user_doc = await users_collection.find_one({"user_id": user_id})
        if not user_doc:
            return {}
        from app.models.visa import (
            ensure_visa_records_from_doc,
            get_active_visas,
            compute_visa_status,
            get_linked_passport_warning,
        )
        visa_records = ensure_visa_records_from_doc(user_doc)
        for v in visa_records:
            v["status"] = compute_visa_status(v)
        active_visas = get_active_visas(visa_records)
        passport_numbers = [
            p.get("passport_no") for p in (user_doc.get("passports") or [])
            if p.get("passport_no")
        ]
        visa_warnings = []
        for v in active_visas:
            msg = get_linked_passport_warning(v, passport_numbers)
            if msg:
                visa_warnings.append({
                    "country_code": v.get("country_code"),
                    "linked_passport": v.get("linked_passport"),
                    "message": msg,
                })
        # Legacy-style fields for backward compat (from first active or legacy)
        first_active = active_visas[0] if active_visas else None
        if first_active:
            has_visa = True
            visa_type = first_active.get("visa_type") or ""
            visa_number = first_active.get("visa_number") or ""
            visa_issuing_country = first_active.get("country_code") or ""
            visa_expiry_date = first_active.get("expiry_date") or ""
            visa_entry_type = "M" if (first_active.get("entries") or "").strip() == "Multiple" else "S"
            visa_purpose = first_active.get("purpose") or "T"
        else:
            has_visa = bool(user_doc.get("visa_type") or user_doc.get("visa_number"))
            visa_type = user_doc.get("visa_type") or ""
            visa_number = user_doc.get("visa_number") or ""
            visa_issuing_country = user_doc.get("visa_issuing_country") or ""
            visa_expiry_date = user_doc.get("visa_expiry_date") or ""
            visa_entry_type = user_doc.get("visa_entry_type") or "S"
            visa_purpose = user_doc.get("visa_purpose") or "T"
        return {
            "has_visa": has_visa,
            "visa_type": visa_type,
            "visa_number": visa_number,
            "visa_issuing_country": visa_issuing_country,
            "visa_expiry_date": visa_expiry_date,
            "visa_entry_type": visa_entry_type,
            "visa_purpose": visa_purpose,
            "visa_records": visa_records,
            "active_visas": active_visas,
            "visa_warnings": visa_warnings,
        }
    except Exception as e:
        logger.debug(f"Failed to get user visa profile for {user_id}: {e}")
        return {}


def _extract_broker_profile_from_user(user_data: dict) -> dict:
    """
    Personal Tailor: Extract structured travel_preferences from the user's profile document.
    Merges family composition, dietary restrictions (from memory_summaries), and trip style.
    """
    if not user_data:
        return {}
    profile: dict = {}

    # Family composition from FamilyMember array
    family = user_data.get("family") or []
    if family:
        children = [m for m in family if (m.get("type") or "").lower() == "child"]
        profile["family_friendly"] = True
        profile["family_size"] = 1 + len(family)
        profile["has_children"] = len(children) > 0
        profile["children_count"] = len(children)
        # Format for broker display
        adults = len(family) - len(children)
        profile["family_summary"] = f"{1 + adults} ผู้ใหญ่{f' + {len(children)} เด็ก' if children else ''}"

    # Dietary / lifestyle from learned memory_summaries
    memory_summaries: list = user_data.get("preferences", {}).get("memory_summaries", [])
    dietary_keywords = ["ไม่เผ็ด", "มังสวิรัติ", "vegan", "halal", "ฮาลาล", "non-spicy", "vegetarian", "gluten"]
    dietary_hints = [s for s in memory_summaries if any(k.lower() in s.lower() for k in dietary_keywords)]
    if dietary_hints:
        profile["dietary_restrictions"] = dietary_hints[-1]  # most recent

    # Budget level hint from memories
    budget_keywords_high = ["บิสซิเนส", "business class", "ชั้นธุรกิจ", "โรงแรม 5 ดาว", "luxury"]
    budget_keywords_low = ["ประหยัด", "budget", "ราคาถูก", "low cost"]
    all_mem = " ".join(memory_summaries).lower()
    if any(k.lower() in all_mem for k in budget_keywords_high):
        profile["budget_level"] = "high"
    elif any(k.lower() in all_mem for k in budget_keywords_low):
        profile["budget_level"] = "low"
    else:
        profile.setdefault("budget_level", "mid")

    # Travel style hints
    style_keywords = {"adventure": ["ผจญภัย", "trekking", "เดินป่า"], "relaxation": ["พักผ่อน", "spa", "ชายหาด", "beach"]}
    for style, keywords in style_keywords.items():
        if any(k.lower() in all_mem for k in keywords):
            profile["travel_style"] = style
            break

    return profile


async def _load_user_agent_preferences(storage, user_id: str) -> dict:
    """Load all AI Agent preferences for a user from MongoDB. Returns defaults if not found.
    Personal Tailor: Also auto-populates travelPreferences from family, memories, and profile.
    """
    defaults = {
        "agentPersonality": "agency",
        "responseStyle": "balanced",
        "detailLevel": "medium",
        "chatLanguage": "th",
        "reinforcementLearning": True,
        "learnFromMyChoices": True,
        "travelPreferences": {},
    }
    try:
        if hasattr(storage, 'db') and storage.db:
            from app.services.user_family_service import get_user_with_family
            user_data = await get_user_with_family(storage.db, user_id)
            if user_data:
                prefs = user_data.get("preferences") or {}
                # Personal Tailor: derive broker profile from user document
                broker_profile = _extract_broker_profile_from_user(user_data)
                # Explicit user-saved travelPreferences take precedence over auto-derived
                explicit_prefs = prefs.get("travelPreferences") or {}
                merged_travel_prefs = {**broker_profile, **explicit_prefs}
                return {
                    "agentPersonality": prefs.get("agentPersonality", defaults["agentPersonality"]),
                    "responseStyle": prefs.get("responseStyle", defaults["responseStyle"]),
                    "detailLevel": prefs.get("detailLevel", defaults["detailLevel"]),
                    "chatLanguage": prefs.get("chatLanguage", defaults["chatLanguage"]),
                    "reinforcementLearning": prefs.get("reinforcementLearning", defaults["reinforcementLearning"]),
                    "learnFromMyChoices": prefs.get("learnFromMyChoices", defaults["learnFromMyChoices"]),
                    "travelPreferences": merged_travel_prefs,
                }
        elif hasattr(storage, 'users_collection') and storage.users_collection:
            from app.services.user_family_service import get_user_with_family
            db = storage.db if hasattr(storage, 'db') and storage.db else None
            if db:
                user_data = await get_user_with_family(db, user_id)
                if user_data:
                    prefs = user_data.get("preferences") or {}
                    broker_profile = _extract_broker_profile_from_user(user_data)
                    explicit_prefs = prefs.get("travelPreferences") or {}
                    merged_travel_prefs = {**broker_profile, **explicit_prefs}
                    return {
                        "agentPersonality": prefs.get("agentPersonality", defaults["agentPersonality"]),
                        "responseStyle": prefs.get("responseStyle", defaults["responseStyle"]),
                        "detailLevel": prefs.get("detailLevel", defaults["detailLevel"]),
                        "chatLanguage": prefs.get("chatLanguage", defaults["chatLanguage"]),
                        "reinforcementLearning": prefs.get("reinforcementLearning", defaults["reinforcementLearning"]),
                        "learnFromMyChoices": prefs.get("learnFromMyChoices", defaults["learnFromMyChoices"]),
                        "travelPreferences": merged_travel_prefs,
                    }
    except Exception as e:
        logger.warning(f"Failed to load agent preferences for user {user_id}: {e}")
    return defaults


async def get_agent_metadata(session: Optional[UserSession], is_admin: bool = False, mode: str = "normal"):
    """Helper to extract metadata for frontend from session using Slot & Segment logic
    
    Args:
        session: UserSession object
        is_admin: If True, Admin user (for Amadeus Viewer access)
        mode: Chat mode - 'normal' (user selects) or 'agent' (AI auto-selects and books)
    """
    if not session:
        return {
            "agent_state": {"mode": mode},
            "travel_slots": {"flights": [], "accommodations": [], "ground_transport": []}
        }
    
    plan = session.trip_plan
    # 🛂 Fetch user visa profile for flight/transfer visa_warning personalization
    user_id = (session.session_id or "").split("::")[0] if getattr(session, "session_id", None) else ""
    storage = MongoStorage()
    user_visa_profile = await _get_user_visa_profile(storage, user_id) if user_id else {}
    
    # 1. Map Current Status of all Slots
    # Access new hierarchical structure
    all_flights = plan.travel.flights.all_segments
    all_accommodations = plan.accommodation.segments
    all_ground = plan.travel.ground_transport
    
    # #region agent log
    import json
    _write_debug_log({
        "sessionId": "debug-session",
        "runId": "run1",
        "hypothesisId": "A",
        "location": "chat.py:303",
        "message": "all_ground segments status check",
        "data": {
            "all_ground_count": len(all_ground),
            "all_ground_statuses": [{"status": str(seg.status), "has_selected_option": bool(seg.selected_option)} for seg in all_ground],
            "confirmed_count": sum(1 for seg in all_ground if seg.status == SegmentStatus.CONFIRMED)
        },
        "timestamp": int(datetime.now().timestamp() * 1000)
    })
    # #endregion

    # ✅ Build travel_slots with formatted data for frontend SlotCards
    # Frontend expects: flight, hotel, transport objects (not just segments)
    travel_slots = {
        "flights": [s.model_dump() for s in all_flights],
        "accommodations": [s.model_dump() for s in all_accommodations],
        "ground_transport": [s.model_dump() for s in all_ground]
    }
    
    # ✅ Extract selected options and format for SlotCards
    # Flight: Extract from segments with selected_option (CONFIRMED หรือ Agent Mode ที่มี selected_option)
    agent_mode = (mode == "agent")
    confirmed_outbound = [s for s in plan.travel.flights.outbound if s.selected_option and (s.status == SegmentStatus.CONFIRMED or agent_mode)]
    confirmed_inbound = [s for s in plan.travel.flights.inbound if s.selected_option and (s.status == SegmentStatus.CONFIRMED or agent_mode)]
    flight_data = None
    
    outbound_segments = []
    inbound_segments = []
    total_price = 0.0
    currency = "THB"
    
    # ✅ Process outbound flights
    for flight_seg in confirmed_outbound:
        selected_flight = flight_seg.selected_option
        raw_data = selected_flight.get("raw_data", {})
        itineraries = raw_data.get("itineraries", [])
        
        for itin in itineraries:
            for seg in itin.get("segments", []):
                outbound_segments.append({
                    "from": seg.get("departure", {}).get("iataCode"),
                    "to": seg.get("arrival", {}).get("iataCode"),
                    "departure": seg.get("departure", {}).get("at"),
                    "arrival": seg.get("arrival", {}).get("at"),
                    "carrier": seg.get("carrierCode"),
                    "number": seg.get("number"),
                    "duration": seg.get("duration")
                })
        
        # Add price
        price = selected_flight.get("price_amount") or selected_flight.get("price_total") or 0
        if isinstance(price, (int, float)):
            total_price += float(price)
        if selected_flight.get("currency"):
            currency = selected_flight.get("currency")
    
    # ✅ Process inbound flights
    for flight_seg in confirmed_inbound:
        selected_flight = flight_seg.selected_option
        raw_data = selected_flight.get("raw_data", {})
        itineraries = raw_data.get("itineraries", [])
        
        for itin in itineraries:
            for seg in itin.get("segments", []):
                inbound_segments.append({
                    "from": seg.get("departure", {}).get("iataCode"),
                    "to": seg.get("arrival", {}).get("iataCode"),
                    "departure": seg.get("departure", {}).get("at"),
                    "arrival": seg.get("arrival", {}).get("at"),
                    "carrier": seg.get("carrierCode"),
                    "number": seg.get("number"),
                    "duration": seg.get("duration")
                })
        
        # Add price
        price = selected_flight.get("price_amount") or selected_flight.get("price_total") or 0
        if isinstance(price, (int, float)):
            total_price += float(price)
        if selected_flight.get("currency"):
            currency = selected_flight.get("currency")
    
    # ✅ Combine all segments
    all_flight_segments = outbound_segments + inbound_segments
    
    if all_flight_segments:
        flight_data = {
            "segments": all_flight_segments,  # All segments (outbound + inbound)
            "outbound": outbound_segments,  # ✅ Outbound segments only
            "inbound": inbound_segments,  # ✅ Inbound segments only
            "total_price": total_price if total_price > 0 else None,
            "currency": currency,
            "total_duration": None,  # Will be calculated if needed
            "is_non_stop": len(outbound_segments) == 1 and len(inbound_segments) == 0,  # Only for outbound
            "num_stops": max(0, len(outbound_segments) - 1) if outbound_segments else 0
        }
    
    # Hotel: Extract from segments with selected_option (CONFIRMED หรือ Agent Mode)
    hotel_data = None
    confirmed_hotel_segments = [s for s in all_accommodations if s.selected_option and (s.status == SegmentStatus.CONFIRMED or agent_mode)]
    if confirmed_hotel_segments:
        # Get first confirmed hotel segment
        first_hotel_seg = confirmed_hotel_segments[0]
        selected_hotel = first_hotel_seg.selected_option
        
        raw_data = selected_hotel.get("raw_data", {})
        pricing = raw_data.get("pricing", {})
        visuals = raw_data.get("visuals", {})
        loc = raw_data.get("location", {})
        
        hotel_data = {
            "hotelName": raw_data.get("hotel_name") or selected_hotel.get("display_name"),
            "city": first_hotel_seg.requirements.get("location"),
            "address": loc.get("address"),
            "total_price": pricing.get("total_amount") or selected_hotel.get("price_amount"),
            "currency": pricing.get("currency") or selected_hotel.get("currency", "THB"),
            "rating": visuals.get("review_score") or raw_data.get("star_rating"),
            "nights": _calc_nights(
                first_hotel_seg.requirements.get("check_in"),
                first_hotel_seg.requirements.get("check_out"),
            )
        }
    
    # Transport: Extract from segments with selected_option (CONFIRMED หรือ Agent Mode)
    transport_data = None
    confirmed_transport_segments = [s for s in all_ground if s.selected_option and (s.status == SegmentStatus.CONFIRMED or agent_mode)]
    if confirmed_transport_segments:
        first_transport_seg = confirmed_transport_segments[0]
        selected_transport = first_transport_seg.selected_option
        raw_data = selected_transport.get("raw_data", {})
        
        # ✅ Extract comprehensive transport information
        transport_data = {
            "type": selected_transport.get("category") or "transfer",
            "route": f"{first_transport_seg.requirements.get('origin', '')} → {first_transport_seg.requirements.get('destination', '')}",
            "price": selected_transport.get("price_amount") or selected_transport.get("price_total"),
            "currency": selected_transport.get("currency", "THB"),
            "duration": selected_transport.get("duration"),
            # ✅ Additional details
            "distance": raw_data.get("distance") or selected_transport.get("distance"),
            "provider": selected_transport.get("provider") or raw_data.get("provider") or selected_transport.get("company"),
            "company": selected_transport.get("company") or raw_data.get("company"),
            "vehicle_type": raw_data.get("vehicle_type") or selected_transport.get("vehicle_type") or selected_transport.get("car_type"),
            "car_type": selected_transport.get("car_type") or raw_data.get("car_type"),
            "seats": raw_data.get("seats") or selected_transport.get("seats") or raw_data.get("capacity") or selected_transport.get("capacity"),
            "capacity": raw_data.get("capacity") or selected_transport.get("capacity"),
            "price_per_day": raw_data.get("price_per_day") or selected_transport.get("price_per_day"),
            "details": raw_data.get("details") or selected_transport.get("details"),
            "features": raw_data.get("features") or selected_transport.get("features") or raw_data.get("amenities") or selected_transport.get("amenities"),
            "amenities": raw_data.get("amenities") or selected_transport.get("amenities"),
            "note": raw_data.get("note") or selected_transport.get("note"),
            "description": selected_transport.get("description") or raw_data.get("description") or selected_transport.get("display_name")
        }
    
    # ✅ Extract basic trip information from segments for TripSummaryCard
    # Origin/Destination from flight segments
    origin_city = None
    destination_city = None
    departure_date = None
    return_date = None
    adults = 1
    children = 0
    infants = 0
    
    # Get from outbound flight segment (priority)
    if plan.travel.flights.outbound:
        outbound_seg = plan.travel.flights.outbound[0]
        origin_city = outbound_seg.requirements.get("origin")
        destination_city = outbound_seg.requirements.get("destination")
        departure_date = outbound_seg.requirements.get("departure_date")
        adults = outbound_seg.requirements.get("adults", 1)
        children = outbound_seg.requirements.get("children", 0) or outbound_seg.requirements.get("children_2_11", 0)
        infants = outbound_seg.requirements.get("infants", 0) or (outbound_seg.requirements.get("infants_with_seat", 0) + outbound_seg.requirements.get("infants_on_lap", 0))
        # Also try to get from selected_option if available
        if outbound_seg.selected_option:
            raw_data = outbound_seg.selected_option.get("raw_data", {})
            itineraries = raw_data.get("itineraries", [])
            if itineraries and itineraries[0].get("segments"):
                first_seg = itineraries[0]["segments"][0]
                if not origin_city:
                    origin_city = first_seg.get("departure", {}).get("iataCode")
                if not destination_city and len(itineraries[0]["segments"]) > 0:
                    last_seg = itineraries[0]["segments"][-1]
                    destination_city = last_seg.get("arrival", {}).get("iataCode")
    
    # Get return date from inbound flight segment
    if plan.travel.flights.inbound:
        inbound_seg = plan.travel.flights.inbound[0]
        return_date = inbound_seg.requirements.get("departure_date")
        if not adults:
            adults = inbound_seg.requirements.get("adults", 1)
        if children == 0:
            children = inbound_seg.requirements.get("children", 0) or inbound_seg.requirements.get("children_2_11", 0)
        if infants == 0:
            infants = inbound_seg.requirements.get("infants", 0) or (inbound_seg.requirements.get("infants_with_seat", 0) + inbound_seg.requirements.get("infants_on_lap", 0))
    
    # Get from accommodation segments if flights don't have it (fallback)
    if not departure_date and all_accommodations:
        first_acc = all_accommodations[0]
        departure_date = first_acc.requirements.get("check_in")
        if not destination_city:
            destination_city = first_acc.requirements.get("location")
        if not adults:
            adults = first_acc.requirements.get("guests", 1)
        if children == 0:
            children = first_acc.requirements.get("children", 0)
    
    # Get return date from accommodation check_out if no inbound flight (fallback)
    if not return_date and all_accommodations:
        first_acc = all_accommodations[0]
        return_date = first_acc.requirements.get("check_out")
    
    # Calculate nights if we have check_in and check_out
    nights = None
    if departure_date and return_date:
        try:
            start_dt = datetime.strptime(departure_date, "%Y-%m-%d")
            end_dt = datetime.strptime(return_date, "%Y-%m-%d")
            nights = (end_dt - start_dt).days
        except (ValueError, TypeError):
            pass
    
    # ✅ Add basic trip info to travel_slots
    travel_slots["origin_city"] = origin_city
    travel_slots["destination_city"] = destination_city
    travel_slots["origin"] = origin_city  # Alias
    travel_slots["destination"] = destination_city  # Alias
    travel_slots["departure_date"] = departure_date
    travel_slots["start_date"] = departure_date  # Alias
    travel_slots["return_date"] = return_date
    travel_slots["end_date"] = return_date  # Alias
    travel_slots["adults"] = adults
    travel_slots["guests"] = adults + children  # Total (alias for backward compat; frontend may use adults+children)
    travel_slots["children"] = children
    travel_slots["children_2_11"] = children  # Alias for 4-type UI
    travel_slots["infants"] = infants
    # ผู้โดยสาร 4 ประเภท: จาก segment requirements ถ้ามี
    infants_ws = 0
    infants_ol = 0
    if plan.travel.flights.outbound and plan.travel.flights.outbound[0].requirements:
        req = plan.travel.flights.outbound[0].requirements
        infants_ws = req.get("infants_with_seat", 0) or 0
        infants_ol = req.get("infants_on_lap", 0) or 0
        if infants_ws == 0 and infants_ol == 0 and infants:
            infants_ol = infants  # legacy: only total infants → assume on lap
    travel_slots["infants_with_seat"] = infants_ws
    travel_slots["infants_on_lap"] = infants_ol
    travel_slots["nights"] = nights
    
    # ✅ Add formatted data to travel_slots for SlotCards
    if flight_data:
        travel_slots["flight"] = flight_data
    if hotel_data:
        travel_slots["hotel"] = hotel_data
    if transport_data:
        travel_slots["transport"] = transport_data
    
    # 2. Build plan_choices/slot_choices จาก segment.options_pool — รวมทุก segment ที่มีตัวเลือก (ที่พัก + รถรับส่ง) เพื่อให้แสดง choice ได้
    slot_choices = []
    slot_intent = None
    def iter_all_segments():
        for s in plan.travel.flights.outbound:
            yield "flights_outbound", s
        for s in plan.travel.flights.inbound:
            yield "flights_inbound", s
        for s in all_accommodations:
            yield "accommodations", s
        for s in all_ground:
            yield "ground_transport", s

    def intent_for_slot(slot_name: str) -> str:
        if slot_name == "flights_outbound" or slot_name == "flights_inbound":
            return "flight"
        if "accommodation" in slot_name:
            return "hotel"
        if "ground" in slot_name:
            return "transfer"
        return "flight"

    # รวบรวมตัวเลือกจากทุก segment ที่มี status SELECTING และ options_pool (ไม่ break แค่ slot แรก)
    collected: List[Tuple[str, str, List[Dict]]] = []  # (slot_name, intent, mapped)
    for slot_name, segment in iter_all_segments():
        if segment.status != SegmentStatus.SELECTING or not (segment.options_pool and len(segment.options_pool) > 0):
            continue
        raw_choices = segment.options_pool
        mapped = [_map_option_for_frontend(opt, i, slot_context=slot_name, user_visa_profile=user_visa_profile) for i, opt in enumerate(raw_choices)]
        if not mapped:
            continue
        intent = intent_for_slot(slot_name)
        # เที่ยวบินขากลับ: แสดงเฉพาะเมื่อ outbound confirmed แล้ว (round_trip)
        if slot_name == "flights_inbound":
            if not (getattr(plan.travel, "trip_type", "round_trip") == "round_trip" and all(s.status == SegmentStatus.CONFIRMED for s in plan.travel.flights.outbound)):
                continue
        collected.append((slot_name, intent, mapped))

    # ตามลำดับความสำคัญ: เที่ยวบินขาไป → ขากลับ → ที่พัก → รถรับส่ง
    order = ["flights_outbound", "flights_inbound", "accommodations", "ground_transport"]
    for slot_name in order:
        for sn, intent, mapped in collected:
            if sn == slot_name:
                slot_choices.extend(mapped)
                if slot_intent is None:
                    slot_intent = intent
                elif slot_intent != intent:
                    slot_intent = "multi"  # หลายประเภท → frontend แสดงทั้งหมด
                break

    # Fallback: ถ้ายังไม่มี (กรณี state ยังไม่ sync) ใช้ segment แรกที่เจอ
    if not slot_choices:
        for slot_name, segment in iter_all_segments():
            if segment.options_pool and len(segment.options_pool) > 0 and segment.status == SegmentStatus.SELECTING:
                raw_choices = segment.options_pool
                slot_choices = [_map_option_for_frontend(opt, i, slot_context=slot_name, user_visa_profile=user_visa_profile) for i, opt in enumerate(raw_choices)]
                slot_intent = intent_for_slot(slot_name)
                break

    # 3. Determine if trip is ready for summary
    # ✅ แสดง Summary ได้เมื่อ: มี Core Segments (Flight OR Hotel) ที่ Confirmed แล้ว
    # ไม่จำเป็นต้องรอให้ Transfer confirmed (เพราะบางทริปอาจไม่ต้องการ Transfer)
    # Only check list/sequence values, not scalar values like adults, nights, etc.
    segment_keys = ["flights", "accommodations", "ground_transport"]
    has_any_segments = any(
        travel_slots.get(key) is not None and len(travel_slots.get(key, [])) > 0 
        for key in segment_keys
    )
    is_fully_complete = has_any_segments and plan.is_complete() # ทุกอย่างเสร็จ 100%
    
    # Check Core Segments (Flights + Hotels) - ถือว่า "พร้อมแสดง Summary" แล้ว
    agent_mode_active = (mode == "agent")
    has_confirmed_flights = any(seg.status == SegmentStatus.CONFIRMED for seg in all_flights)
    has_confirmed_hotels = any(seg.status == SegmentStatus.CONFIRMED for seg in all_accommodations)
    has_selected_flights = any(getattr(s, "selected_option", None) for s in all_flights)
    has_selected_hotels = any(getattr(s, "selected_option", None) for s in all_accommodations)
    has_core_segments_ready = (
        has_confirmed_flights or has_confirmed_hotels
        or (agent_mode_active and (has_selected_flights or has_selected_hotels))
    )
    # แสดง Summary ได้เมื่อ:
    # - Normal Mode: ทั้งหมดเสร็จ หรือ มี Core Segments พร้อมแล้ว (ผู้ใช้เลือกแล้ว)
    # - Agent Mode: ทั้งหมดเสร็จ หรือ มี Core Segments พร้อมแล้ว หรือ Agent เลือกแล้ว (มี selected_option)
    should_show_summary = is_fully_complete or has_core_segments_ready
    
    # ✅ Build current_plan with formatted data for TripSummaryCard
    current_plan = None
    if should_show_summary:
        plan_dict = plan.model_dump()
        
        # ✅ Add formatted flight/hotel/transport data to plan
        if flight_data:
            plan_dict["flight"] = flight_data
        if hotel_data:
            plan_dict["hotel"] = hotel_data
        if transport_data:
            plan_dict["transport"] = transport_data
        
        # ✅ Calculate total price
        total_price = 0.0
        currency = "THB"
        if flight_data and flight_data.get("total_price"):
            total_price += float(flight_data.get("total_price", 0))
            currency = flight_data.get("currency", currency)
        if hotel_data and hotel_data.get("total_price"):
            total_price += float(hotel_data.get("total_price", 0))
            currency = hotel_data.get("currency", currency)
        if transport_data and transport_data.get("price"):
            total_price += float(transport_data.get("price", 0))
            currency = transport_data.get("currency", currency)
        
        if total_price > 0:
            plan_dict["total_price"] = total_price
            plan_dict["currency"] = currency
        
        current_plan = plan_dict

    # ✅ Get trip_type from travel slot (may be stored in requirements or as attribute)
    trip_type = "round_trip"  # Default
    if hasattr(plan.travel, 'trip_type'):
        trip_type = plan.travel.trip_type
    elif hasattr(plan.travel, 'flights') and plan.travel.flights.outbound:
        # Check if inbound flights exist - if not, it's likely one_way
        if not plan.travel.flights.inbound or len(plan.travel.flights.inbound) == 0:
            trip_type = "one_way"
    
    # ✅ Workflow state (Redis) + schema สำหรับ frontend (current_step, is_complete, completeness_issues)
    workflow_validation = None
    workflow_step = "planning"
    if session:
        try:
            from app.services.workflow_state import get_workflow_state_service, WorkflowStep as WfStep
            wf = get_workflow_state_service()
            if should_show_summary:
                await wf.set_workflow_state(session.session_id, WfStep.SUMMARY)
            workflow_validation = await wf.get_workflow_validation(
                session.session_id,
                trip_plan=plan,
            )
            workflow_step = workflow_validation.get("current_step") or workflow_validation.get("step", "planning")
            if should_show_summary:
                workflow_validation["step"] = WfStep.SUMMARY
                workflow_validation["current_step"] = WfStep.SUMMARY
                workflow_validation["is_complete"] = True
                workflow_validation["completeness_issues"] = []
        except Exception as wf_err:
            logger.warning(f"Workflow state: {wf_err}")
    
    # ✅ ดึงข้อมูลจาก cache (options + raw Amadeus อยู่ที่ Redis)
    cached_options = None
    cache_validation = None
    if session:
        try:
            options_cache = get_options_cache()
            cached_options = await options_cache.get_all_session_options(session.session_id)
            cache_validation = await options_cache.validate_cache_data(session.session_id)
            logger.info(f"Retrieved cached options for session {session.session_id}: {cache_validation.get('summary', {})}")
        except Exception as cache_error:
            logger.warning(f"Failed to get cached options: {cache_error}")
    
    # ✅ แปลงภาพโรงแรมจาก URL เป็น base64 data URL เพื่อให้ frontend แสดงได้โดยไม่ติด CORS
    await _convert_hotel_image_urls_to_base64(slot_choices)
    
    return {
        "trip_type": trip_type,
        "plan_choices": slot_choices,
        "slot_choices": slot_choices,
        "slot_intent": slot_intent,
        "agent_state": {
            "agent_mode": agent_mode_active,
            "mode": mode,
            "step": workflow_step,
            "slot_workflow": {"current_slot": slot_intent or ("summary" if should_show_summary else None)},
            "booking_funnel_state": getattr(session, "booking_funnel_state", "idle") or "idle",
        },
        "travel_slots": travel_slots,
        "current_plan": current_plan,
        "flight": flight_data,
        "hotel": hotel_data,
        "transport": transport_data,
        "cached_options": cached_options,
        "cache_validation": cache_validation,
        "workflow_validation": workflow_validation,
        "popular_destinations": getattr(session, "popular_destinations", None)
    }


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID", description="Conversation identifier"),
):
    """
    SSE stream endpoint for chat
    """
    # ✅ SECURITY: Use security helper to extract user_id (prioritizes cookie, then header)
    from app.core.security import extract_user_id_from_request
    user_id = extract_user_id_from_request(fastapi_request) or request.user_id or "anonymous"
    
    # ✅ SECURITY: Validate user_id is not empty
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # ✅ ใช้ chat_id เป็นหลัก (fallback ไป client_trip_id หรือ x_conversation_id สำหรับ backward compatibility)
    chat_id = request.chat_id or x_conversation_id or request.client_trip_id
    trip_id = request.trip_id or request.client_trip_id  # ✅ trip_id สำหรับ metadata
    
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id (or X-Conversation-ID header or client_trip_id) is required")
    
    # ✅ session_id ใช้ chat_id (แต่ละ chat = 1 session)
    session_id = f"{user_id}::{chat_id}"

    async def event_generator():
        # #region agent log (Hypothesis: No Response)
        import json
        import time
        import os
        try:
            from pathlib import Path
            debug_log_dir = Path(__file__).parent.parent.parent / 'data' / 'logs' / 'debug'
            debug_log_dir.mkdir(parents=True, exist_ok=True)
            debug_log_path = debug_log_dir / 'chat_stream_debug.log'
            with open(debug_log_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "id": f"log_{int(time.time() * 1000)}_event_generator_start",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:982",
                    "message": "event_generator started",
                    "data": {"session_id": session_id, "user_id": user_id, "message": request.message[:50] if request.message else ""},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                }, ensure_ascii=False) + '\n')
        except Exception as e:
            pass  # Silently ignore debug log errors
        # #endregion
        
        set_logging_context(session_id=session_id, user_id=user_id)
        try:
            storage = MongoStorage()
            
            # ✅ SECURITY: Verify session belongs to this user before processing
            # ✅ CRITICAL: Validate session_id format matches user_id
            from app.core.security import validate_session_user_id
            validate_session_user_id(session_id, user_id)
            
            existing_session = await storage.get_session(session_id)
            
            # #region agent log (Hypothesis: No Response)
            try:
                from pathlib import Path
                debug_log_dir = Path(__file__).parent.parent.parent / 'data' / 'logs' / 'debug'
                debug_log_dir.mkdir(parents=True, exist_ok=True)
                debug_log_path = debug_log_dir / 'chat_session_debug.log'
                with open(debug_log_path, 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "id": f"log_{int(time.time() * 1000)}_got_existing_session",
                        "timestamp": int(time.time() * 1000),
                        "location": "chat.py:990",
                        "message": "Got existing session",
                        "data": {"has_session": existing_session is not None},
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "A"
                    }, ensure_ascii=False) + '\n')
            except Exception as e:
                pass  # Silently ignore debug log errors
            # #endregion
            
            # ✅ SECURITY: Double-check session ownership (additional safety layer)
            if existing_session and existing_session.user_id != user_id:
                logger.error(f"🚨 SECURITY ALERT: Unauthorized chat stream attempt: user {user_id} tried to access session {session_id} owned by {existing_session.user_id}")
                yield f"data: {json.dumps({'status': 'error', 'error': 'You do not have permission to access this session'})}\n\n"
                return
            
            # ✅ CRITICAL: Check GEMINI_API_KEY before initializing LLM
            if not settings.gemini_api_key or not settings.gemini_api_key.strip():
                logger.error(f"GEMINI_API_KEY is missing or empty for session {session_id}")
                yield f"data: {json.dumps({'status': 'error', 'message': 'GEMINI_API_KEY is not configured. Please set it in .env file.'}, ensure_ascii=False)}\n\n"
                return
            
            # #region agent log (Hypothesis: No Response)
            _write_debug_log({
                "id": f"log_{int(time.time() * 1000)}_before_llm_init",
                "timestamp": int(time.time() * 1000),
                "location": "chat.py:1000",
                "message": "Before LLM initialization",
                "data": {"has_gemini_key": bool(settings.gemini_api_key)},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            
            try:
                llm_with_mcp = LLMServiceWithMCP()
                
                # ✅ Get user preferences for agent (personality, style, language, RL)
                _prefs = await _load_user_agent_preferences(storage, user_id)
                agent = TravelAgent(
                    storage,
                    llm_service=llm_with_mcp,
                    agent_personality=_prefs["agentPersonality"],
                    response_style=_prefs["responseStyle"],
                    detail_level=_prefs["detailLevel"],
                    chat_language=_prefs["chatLanguage"],
                    reinforcement_learning=_prefs["reinforcementLearning"],
                )
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_agent_initialized",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1005",
                    "message": "Agent initialized successfully",
                    "data": {},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
            except LLMException as llm_error:
                logger.error(f"LLM initialization failed for session {session_id}: {llm_error}")
                yield f"data: {json.dumps({'status': 'error', 'message': f'LLM service initialization failed: {str(llm_error)}'}, ensure_ascii=False)}\n\n"
                return
            except Exception as init_error:
                logger.error(f"Agent initialization failed for session {session_id}: {init_error}", exc_info=True)
                yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to initialize chat service. Please check server logs.'}, ensure_ascii=False)}\n\n"
                return
            
            # Queue for bridging status updates from agent to SSE
            status_queue = asyncio.Queue()
            
            async def status_callback(status: str, message: str, step: str):
                await status_queue.put({
                    "status": status,
                    "message": message,
                    "step": step
                })

            # ✅ Get mode from request (default to 'normal')
            mode = request.mode or "normal"
            logger.info(f"Chat mode: {mode} for session {session_id}")
            
            # ✅ REALTIME: Save user message to DB IMMEDIATELY before processing starts
            try:
                _user_msg_realtime = {
                    "role": "user",
                    "content": request.message,
                    "timestamp": datetime.utcnow()
                }
                await storage.save_message(session_id, _user_msg_realtime)
                logger.info(f"[Realtime] User message saved to DB before processing: session={session_id}")
            except Exception as _save_err:
                logger.warning(f"[Realtime] Failed to save user message before processing (will not retry): {_save_err}")
            
            # Start agent in background task
            try:
                logger.info(f"Creating agent task: session={session_id}, message_length={len(request.message)}, mode={mode}")
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_creating_task",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1029",
                    "message": "Creating agent task",
                    "data": {"message_length": len(request.message), "mode": mode},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                run_turn_error_hint = None  # ตั้งค่าเริ่มต้น (จะถูกเซ็ตเมื่อ run_turn return tuple หลัง exception)
                task = asyncio.create_task(agent.run_turn(
                    session_id=session_id,
                    user_input=request.message,
                    status_callback=status_callback,
                    mode=mode,
                    travel_preferences=_prefs.get("travelPreferences") or {},
                ))
                logger.info(f"Agent task created successfully for session {session_id}")
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_task_created",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1038",
                    "message": "Agent task created",
                    "data": {"task_done": task.done()},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
            except Exception as task_error:
                logger.error(f"Failed to create agent task: {task_error}", exc_info=True)
                yield f"data: {json.dumps({'status': 'error', 'message': 'Failed to start chat processing. Please try again.'}, ensure_ascii=False)}\n\n"
                return
            
            # 1. Send initial status
            yield f"data: {json.dumps({'status': 'processing', 'message': 'กำลังเริ่มประมวลผล...', 'step': 'start'}, ensure_ascii=False)}\n\n"
            
            # ✅ VISIBLE HEARTBEAT: Send "ping" or "processing" event every 2 seconds
            last_heartbeat = asyncio.get_event_loop().time()
            heartbeat_interval = 2.0  # 2 seconds
            
            # 2. Bridge status updates from queue to SSE until task is done
            _stream_timeout = float(settings.chat_timeout_agent if mode == "agent" else settings.chat_timeout_normal)
            start_time = asyncio.get_event_loop().time()
            
            while not task.done() or not status_queue.empty():
                try:
                    # Check timeout
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > _stream_timeout:
                        logger.warning(f"Task timeout exceeded ({elapsed:.1f}s > {_stream_timeout}s) for session {session_id}")
                        task.cancel()
                        break
                    
                    # Try to get from queue with short timeout
                    try:
                        status_data = await asyncio.wait_for(status_queue.get(), timeout=0.1)
                        yield f"data: {json.dumps(status_data, ensure_ascii=False)}\n\n"
                        # ✅ Agent Mode: เมื่อได้ step agent_show_summary ให้ส่ง summary_ready พร้อม current_plan เพื่อให้ frontend แสดง Trip Summary ก่อนจอง
                        if status_data.get("step") == "agent_show_summary":
                            try:
                                updated_session = await storage.get_session(session_id)
                                if updated_session:
                                    metadata = await get_agent_metadata(updated_session, is_admin=False, mode=mode)
                                    summary_event = {
                                        "status": "summary_ready",
                                        "current_plan": metadata.get("current_plan"),
                                        "travel_slots": metadata.get("travel_slots"),
                                        "workflow_validation": metadata.get("workflow_validation"),
                                        "agent_state": metadata.get("agent_state"),
                                    }
                                    yield f"data: {json.dumps(summary_event, ensure_ascii=False)}\n\n"
                            except Exception as summary_err:
                                logger.warning(f"Agent show summary: failed to build summary_ready event: {summary_err}")
                    except asyncio.TimeoutError:
                        # ✅ HEARTBEAT: Send ping every 2 seconds while waiting
                        current_time = asyncio.get_event_loop().time()
                        if current_time - last_heartbeat >= heartbeat_interval:
                            yield f"data: {json.dumps({'status': 'processing', 'message': 'กำลังประมวลผล...', 'step': 'heartbeat'}, ensure_ascii=False)}\n\n"
                            last_heartbeat = current_time
                        
                        # Check for disconnect while waiting
                        if await fastapi_request.is_disconnected():
                            logger.info(f"Client disconnected during stream: session={session_id}")
                            task.cancel()
                            return
                        if task.done() and status_queue.empty():
                            break
                        continue
                except Exception as e:
                    logger.error(f"Queue error in stream: {e}")
                    # ✅ HEARTBEAT: Even on error, send heartbeat to keep connection alive
                    current_time = asyncio.get_event_loop().time()
                    if current_time - last_heartbeat >= heartbeat_interval:
                        yield f"data: {json.dumps({'status': 'processing', 'message': 'กำลังประมวลผล...', 'step': 'heartbeat'}, ensure_ascii=False)}\n\n"
                        last_heartbeat = current_time
                    continue
            
            # 3. Get the final response from agent (task is already done)
            response_text = None
            auto_booked = False
            try:
                # ✅ Timeout อ่านจาก settings เพื่อให้ตรงกับ middleware (ไม่ถูกตัดก่อน)
                timeout_seconds = float(settings.chat_timeout_agent if mode == "agent" else settings.chat_timeout_normal)
                logger.info(f"Waiting for agent task to complete: session={session_id}, timeout={timeout_seconds}s")
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_waiting_for_task",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1094",
                    "message": "Waiting for agent task",
                    "data": {"task_done": task.done()},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                result = await asyncio.wait_for(task, timeout=timeout_seconds)
                # run_turn returns str หรือ (str, error_hint) เมื่อเกิด exception
                if isinstance(result, tuple) and len(result) >= 2:
                    response_text = result[0]
                    run_turn_error_hint = result[1]
                else:
                    response_text = result if isinstance(result, str) else str(result)
                    run_turn_error_hint = None
                # Read auto_booked from session after run_turn completes
                _session_after = await storage.get_session(session_id)
                auto_booked = bool(getattr(_session_after, "_agent_auto_booked", False)) if _session_after else False
                
                # ✅ CRITICAL: Log detailed response info
                if response_text is None:
                    logger.error(f"⚠️ Agent task returned None for session {session_id}")
                    # Check if task has exception
                    if task.done() and task.exception():
                        logger.error(f"Task has exception: {task.exception()}", exc_info=True)
                elif not response_text.strip():
                    logger.error(f"⚠️ Agent task returned empty string for session {session_id}")
                else:
                    logger.info(f"✅ Agent task completed: session={session_id}, response_length={len(response_text)}")
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_task_completed",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1100",
                    "message": "Agent task completed",
                    "data": {"response_length": len(response_text) if response_text else 0, "response_preview": response_text[:100] if response_text else ""},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                # ✅ CRITICAL: Check if response_text is None or empty
                if not response_text or not response_text.strip():
                    logger.error(
                        "Agent returned empty response, using fallback",
                        extra={"session_id": session_id, "fallback_reason": "stream_agent_empty"},
                    )
                    response_text = FALLBACK_RESPONSE_EMPTY
                else:
                    logger.info(f"Agent response received: {response_text[:100]}...")
            except asyncio.TimeoutError:
                logger.error(f"Agent execution timed out: session={session_id}")
                response_text = "ระบบใช้เวลาประมวลผลนานเกินไป กรุณาลองใหม่อีกครั้ง"
                yield f"data: {json.dumps({'status': 'error', 'message': response_text}, ensure_ascii=False)}\n\n"
                return
            except Exception as e:
                logger.error(f"Error getting response from agent: {e}", exc_info=True)
                # ✅ Check if task has exception
                if task.done() and task.exception():
                    task_exception = task.exception()
                    logger.error(f"Task exception: {task_exception}", exc_info=True)
                    # If it's an LLM error, provide more specific message
                    error_str = str(task_exception).lower()
                    if "api" in error_str and "key" in error_str:
                        response_text = "ขออภัยค่ะ ระบบไม่สามารถเชื่อมต่อกับ AI service ได้ กรุณาตรวจสอบ GEMINI_API_KEY ในไฟล์ .env"
                    elif "timeout" in error_str or "timed out" in error_str:
                        response_text = "ระบบใช้เวลาประมวลผลนานเกินไป กรุณาลองใหม่อีกครั้ง"
                    elif "connection aborted" in error_str or "remotedisconnected" in error_str or "remote end closed" in error_str:
                        response_text = "การเชื่อมต่อหลุดระหว่างประมวลผล (อาจใช้เวลานาน) กรุณากดรีเฟรชแล้วลองจองอีกครั้ง หรือส่งข้อความใหม่ค่ะ"
                    else:
                        response_text = f"ขออภัยค่ะ เกิดข้อผิดพลาดในการประมวลผล: {str(task_exception)[:100]}"
                else:
                    response_text = "ขออภัยค่ะ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่อีกครั้ง"
            
            # ✅ CRITICAL: Ensure response_text is set
            if response_text is None:
                logger.error(f"Response text is None after all error handling: session={session_id}")
                response_text = "ขออภัยค่ะ ระบบไม่สามารถสร้างคำตอบได้ กรุณาลองใหม่อีกครั้ง"
            
            # 4. Get updated session for metadata
            updated_session = await storage.get_session(session_id)
            
            # ✅ Check if user is admin (for Test Mode)
            is_admin_user = await _is_admin_user(user_id, storage)
            
            # ✅ CRITICAL: Save session after agent run to persist trip_plan with all plan choices, selected options, and raw data
            if updated_session:
                if trip_id and (not updated_session.trip_id or updated_session.trip_id != trip_id):
                    updated_session.trip_id = trip_id
                if chat_id and (not updated_session.chat_id or updated_session.chat_id != chat_id):
                    updated_session.chat_id = chat_id
                
                # Always save session to ensure trip_plan (with selected_option and options_pool) is persisted
                session_saved = await storage.save_session(updated_session)
                if not session_saved:
                    logger.error(f"Failed to save session to database after agent run: session_id={session_id}")
                else:
                    # Log trip_plan data for debugging
                    trip_plan = updated_session.trip_plan
                    total_options = 0
                    confirmed_selections = 0
                    for seg in (trip_plan.travel.flights.outbound + 
                               trip_plan.travel.flights.inbound +
                               trip_plan.accommodation.segments +
                               trip_plan.travel.ground_transport):
                        if seg.options_pool:
                            total_options += len(seg.options_pool)
                        if seg.status.value == "confirmed" and seg.selected_option:
                            confirmed_selections += 1
                    
                    logger.info(f"Session saved with trip_plan: session_id={session_id}, {confirmed_selections} confirmed selections, {total_options} total options in pools (raw data preserved)")
            
            metadata = await get_agent_metadata(updated_session, is_admin=is_admin_user, mode=mode) if updated_session else {
                "plan_choices": [],
                "slot_choices": [],
                "slot_intent": None,
                "agent_state": {"mode": mode, "step": "planning"},
                "travel_slots": {"flights": [], "accommodations": [], "ground_transport": []},
                "current_plan": None,
                "workflow_validation": None
            }
            
            # ✅ REALTIME: Save bot message to DB IMMEDIATELY after response is available (with metadata)
            try:
                _bot_msg_realtime = {
                    "role": "assistant",
                    "content": response_text,
                    "timestamp": datetime.utcnow(),
                    "metadata": metadata
                }
                await storage.save_message(session_id, _bot_msg_realtime)
                logger.info(f"[Realtime] Bot message saved to DB after response: session={session_id}, length={len(response_text)}")
            except Exception as _save_err:
                logger.warning(f"[Realtime] Failed to save bot message realtime: {_save_err}")
            
            # 5. Send completion data
            # ✅ CRITICAL: Ensure response_text is never None or empty
            if not response_text or not response_text.strip():
                logger.error(
                    "Response text empty before send, using fallback",
                    extra={"session_id": session_id, "fallback_reason": "stream_final_empty"},
                )
                response_text = FALLBACK_RESPONSE_EMPTY
            
            final_data = {
                "response": response_text,
                "session_id": session_id,
                "trip_title": updated_session.title if updated_session else None,
                **metadata
            }
            if run_turn_error_hint:
                final_data["error_hint"] = run_turn_error_hint
            if mode == "agent":
                final_data["auto_booked"] = auto_booked
                if auto_booked:
                    final_data["agent_booking_success_message"] = (
                        "✅ จองอัตโนมัติสำเร็จ! กรุณาชำระเงินที่ My Bookings เพื่อยืนยันการจอง"
                    )
            
            _write_debug_log({"id": f"log_{int(datetime.utcnow().timestamp()*1000)}_final_data", "timestamp": int(datetime.utcnow().timestamp()*1000), "location": "chat.py:stream", "message": "Completion final_data built", "data": {"mode": mode, "has_current_plan": bool(metadata.get("current_plan")), "auto_booked": auto_booked if mode == "agent" else None}, "runId": "run1", "hypothesisId": "H3"})
            
            # ✅ CRITICAL: Log before sending to ensure we have response
            logger.info(f"Sending completion event: session={session_id}, response_length={len(response_text)}, has_metadata={bool(metadata)}")
            
            # #region agent log (Hypothesis: No Response)
            _write_debug_log({
                "id": f"log_{int(time.time() * 1000)}_before_send_completion",
                "timestamp": int(time.time() * 1000),
                "location": "chat.py:1195",
                "message": "Before sending completion event",
                "data": {"response_length": len(response_text) if response_text else 0, "final_data_keys": list(final_data.keys())},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            
            try:
                completion_event = json.dumps({'status': 'completed', 'data': final_data}, ensure_ascii=False)
                yield f"data: {completion_event}\n\n"
                logger.info(f"Completion event sent successfully for session {session_id}")
                
                # #region agent log (Hypothesis: No Response)
                _write_debug_log({
                    "id": f"log_{int(time.time() * 1000)}_completion_sent",
                    "timestamp": int(time.time() * 1000),
                    "location": "chat.py:1200",
                    "message": "Completion event sent",
                    "data": {"event_length": len(completion_event)},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
            except Exception as send_error:
                logger.error(f"Failed to send completion event: {send_error}", exc_info=True)
                # Try to send minimal response
                try:
                    yield f"data: {json.dumps({'status': 'completed', 'data': {'response': response_text}}, ensure_ascii=False)}\n\n"
                except Exception:
                    logger.error(f"Failed to send minimal response for session {session_id}")
            
            # ✅ CRITICAL: Save session to database to persist trip_plan with all plan choices and raw data
            if updated_session:
                session_saved = await storage.save_session(updated_session)
                if not session_saved:
                    logger.error(f"Failed to save session to database after SSE stream: session_id={session_id}")
                else:
                    logger.info(f"Session saved with trip_plan after SSE stream: session_id={session_id}")
            
            # ✅ Messages were already saved REALTIME above:
            # - User message: saved BEFORE agent task creation
            # - Bot message: saved AFTER response + metadata were ready, BEFORE completion event
            logger.info(f"[Realtime] Both messages already saved to DB for session {session_id}")
            
            # 6. Background tasks (Title generation)
            if updated_session and updated_session.title is None:
                background_tasks.add_task(run_title_generator, session_id, request.message, response_text)
                
        except Exception as e:
            # #region agent log (Hypothesis: No Response)
            _write_debug_log({
                "id": f"log_{int(time.time() * 1000)}_sse_error",
                "timestamp": int(time.time() * 1000),
                "location": "chat.py:1245",
                "message": "SSE Stream error",
                "data": {"error": str(e), "error_type": type(e).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            
            logger.error(f"SSE Stream error for session {session_id}: {e}", exc_info=True)
            # ✅ CRITICAL: Always send error response to frontend
            try:
                error_message = str(e)[:200] if str(e) else "Unknown error occurred"
                yield f"data: {json.dumps({'status': 'error', 'message': error_message}, ensure_ascii=False)}\n\n"
            except Exception as yield_error:
                logger.error(f"Failed to send error response: {yield_error}")
                # Last resort - send minimal error
                try:
                    yield f"data: {json.dumps({'status': 'error', 'message': 'Chat service error'}, ensure_ascii=False)}\n\n"
                except Exception:
                    pass  # Connection may be closed
        finally:
            clear_logging_context()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID", description="Conversation identifier"),
):
    """
    Chat endpoint - Main entry point for Travel Agent
    Supports both Session Cookie and Headers for auth
    """
    # ✅ SECURITY: Use security helper to extract user_id (prioritizes cookie, then header)
    from app.core.security import extract_user_id_from_request
    user_id = extract_user_id_from_request(fastapi_request) or request.user_id or "anonymous"
    
    # ✅ SECURITY: Validate user_id is not empty
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # 2. Get chat_id and trip_id (ใช้ chat_id เป็นหลัก)
    chat_id = request.chat_id or x_conversation_id or request.client_trip_id
    trip_id = request.trip_id or request.client_trip_id  # ✅ trip_id สำหรับ metadata
    
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id (or X-Conversation-ID header or client_trip_id) is required")
    
    # ✅ session_id ใช้ chat_id (แต่ละ chat = 1 session)
    session_id = f"{user_id}::{chat_id}"
    set_logging_context(session_id=session_id, user_id=user_id)
    
    try:
        # Validate input
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="message is empty")
        
        logger.info(f"Processing chat request: message_length={len(request.message)}")
        
        # Instantiate storage and agent (with MCP support)
        storage = MongoStorage()
        llm_with_mcp = LLMServiceWithMCP()
        
        # ✅ Get user preferences for agent (personality, style, language, RL)
        _prefs = await _load_user_agent_preferences(storage, user_id)
        agent = TravelAgent(
            storage,
            llm_service=llm_with_mcp,
            agent_personality=_prefs["agentPersonality"],
            response_style=_prefs["responseStyle"],
            detail_level=_prefs["detailLevel"],
            chat_language=_prefs["chatLanguage"],
            reinforcement_learning=_prefs["reinforcementLearning"],
        )

        # ✅ SECURITY: CRITICAL - Validate session_id format matches user_id BEFORE loading session
        from app.core.security import validate_session_user_id
        validate_session_user_id(session_id, user_id)
        
        # ✅ SECURITY: Verify session belongs to this user before processing
        session = await storage.get_session(session_id)
        
        # ✅ SECURITY: Double-check session ownership (additional safety layer)
        if session and session.user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Unauthorized chat attempt: user {user_id} tried to access session {session_id} owned by {session.user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to access this session")

        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # ✅ Update trip_id and chat_id if provided (for new sessions or migration)
        if trip_id and (not session.trip_id or session.trip_id != trip_id):
            session.trip_id = trip_id
        if chat_id and (not session.chat_id or session.chat_id != chat_id):
            session.chat_id = chat_id
        if trip_id or chat_id:
            await storage.save_session(session)
        
        needs_title = session.title is None
        
        # ✅ Get mode from request (default to 'normal')
        mode = request.mode or "normal"
        logger.info(f"Chat mode: {mode} for session {session_id}")
        
        # ✅ REALTIME: Save user message to DB IMMEDIATELY before processing starts
        try:
            _user_msg_now = {
                "role": "user",
                "content": request.message,
                "timestamp": datetime.utcnow()
            }
            await storage.save_message(session_id, _user_msg_now)
            logger.info(f"[Realtime] User message saved to DB before agent run: session={session_id}")
        except Exception as _save_err:
            logger.warning(f"[Realtime] Failed to save user message realtime: {_save_err}")
        
        # Run agent turn (this returns the response text)
        # Note: TravelAgent.run_turn should handle internal state updates
        result = await agent.run_turn(session_id, request.message, mode=mode)
        # run_turn always returns str; auto_booked flag is stored on the session object
        response_text = result if isinstance(result, str) else (result[0] if isinstance(result, tuple) else str(result))
        # Read auto_booked from session after run_turn completes
        _session_after = await storage.get_session(session_id)
        auto_booked = bool(getattr(_session_after, "_agent_auto_booked", False)) if _session_after else False
        
        # Get the updated session for additional metadata
        updated_session = await storage.get_session(session_id)
        
        # #region agent log (Hypothesis: No Response)
        import json
        import time
        _write_debug_log({
            "id": f"log_{int(time.time() * 1000)}_got_updated_session",
            "timestamp": int(time.time() * 1000),
            "location": "chat.py:1483",
            "message": "Got updated session",
            "data": {"has_session": updated_session is not None},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        })
        # #endregion
        
        # ✅ Check if user is admin (for Test Mode)
        is_admin_user = await _is_admin_user(user_id, storage)
        
        # Extract metadata for frontend
        metadata = await get_agent_metadata(updated_session, is_admin=is_admin_user, mode=mode)
        
        # Schedule background title generation if needed (first turn only)
        if needs_title:
            logger.info(f"Scheduling background title generation for session {session_id}")
            background_tasks.add_task(
                run_title_generator,
                session_id,
                request.message,
                response_text
            )
        
        # ✅ User message was already saved REALTIME before agent run above
        # ✅ Save bot response to database (MongoDB) - REALTIME after response
        bot_msg = {
            "role": "assistant",
            "content": response_text,
            "timestamp": datetime.utcnow(),
            "metadata": metadata
        }
        bot_msg_saved = await storage.save_message(session_id, bot_msg)
        if not bot_msg_saved:
            logger.error(f"Failed to save bot message to database for session {session_id}")
        else:
            logger.info(f"[Realtime] Bot message saved to DB after agent run: session={session_id}")
        
        logger.info("Chat request completed successfully")
        
        # Build response with metadata from state
        current_plan_data = None
        if updated_session and hasattr(updated_session, 'trip_plan') and updated_session.trip_plan:
            try:
                current_plan_data = updated_session.trip_plan.model_dump()
            except Exception as e:
                logger.error(f"Error serializing trip_plan: {e}", exc_info=True)
                current_plan_data = None
        
        # #region agent log (Hypothesis: No Response)
        import json
        import time
        _write_debug_log({
            "id": f"log_{int(time.time() * 1000)}_before_send_completed",
            "timestamp": int(time.time() * 1000),
            "location": "chat.py:1575",
            "message": "Before sending completed status",
            "data": {"response_text_length": len(response_text) if response_text else 0, "has_metadata": bool(metadata)},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        })
        # #endregion
        
        # ✅ FIX: metadata already contains current_plan from get_agent_metadata()
        # Use current_plan_data as fallback if metadata doesn't have it
        if current_plan_data and not metadata.get("current_plan"):
            metadata["current_plan"] = current_plan_data
        
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            trip_title=updated_session.title if updated_session else None,
            **metadata
        )
    
    except HTTPException:
        raise
    except (AgentException, StorageException) as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        clear_logging_context()


@router.get("/history/{client_trip_id}")
async def get_history(
    client_trip_id: str,
    fastapi_request: Request,
    limit: int = 50,
    x_trip_id: Optional[str] = Header(None, alias="X-Trip-ID", description="Trip ID for session lookup"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID", description="User ID for session lookup (ต้องตรงกับตอนส่งข้อความ)"),
):
    """
    Get chat history for ONE chat/trip (แบบ GPT/Gemini — โหลดทีละแชท).
    เฉพาะ user ที่ login (X-User-ID หรือ cookie) — ลด 429 จากการยิงหลาย request พร้อมกัน
    """
    from app.core.security import extract_user_id_from_request
    # ✅ ใช้ X-User-ID จาก frontend ก่อน เพื่อให้ตรงกับ user ที่แสดงในรายการแชท (ป้องกัน no history เมื่อ cookie กับ list ไม่ตรง)
    user_id = x_user_id or extract_user_id_from_request(fastapi_request) or "guest"
    
    # ✅ ใช้ client_trip_id เป็น chat_id (frontend ส่ง chatId มา)
    chat_id = client_trip_id
    trip_id = x_trip_id
    
    # ✅ session_id ใช้รูปแบบเดียวกับ chat endpoint: user_id::chat_id
    session_id = f"{user_id}::{chat_id}"
    
    logger.info(f"Fetching history for session_id={session_id}, chat_id={chat_id}, trip_id={trip_id}, user_id={user_id}")
    
    storage = MongoStorage()
    
    # Try to get history using session_id (user_id::chat_id)
    history = await storage.get_chat_history(session_id, limit)
    
    # ✅ Fallback 1: ลองใช้ trip_id เป็น session_id (กรณี frontend ใช้ tripId แทน chatId)
    if not history and trip_id and trip_id != chat_id:
        fallback_session_id = f"{user_id}::{trip_id}"
        logger.info(f"No history with chat_id, trying trip_id: {fallback_session_id}")
        history = await storage.get_chat_history(fallback_session_id, limit)
    
    # ✅ Fallback 2: รูปแบบเก่าใน Mongo ที่ session_id เก็บแค่ chat_id (ไม่มี user_id::)
    if not history:
        history = await storage.get_chat_history_by_chat_id(chat_id, user_id, limit)
    
    # ✅ SECURITY: Do NOT try alternative user_ids - this could cause data leakage
    # Each user should only access their own data based on their session cookie
    
    # Map to frontend format
    mapped_history = []
    for msg in history:
        mapped_history.append({
            "id": str(msg.get("_id") or datetime.utcnow().timestamp()), # Fallback ID
            "type": "bot" if msg.get("role") == "assistant" else "user",
            "text": msg.get("content"),
            "timestamp": msg.get("timestamp"),
            # Restore rich data if available
            **msg.get("metadata", {}) 
        })
    
    logger.info(f"Returning {len(mapped_history)} messages for session_id={session_id}")
    return {"history": mapped_history}


@router.get("/histories")
async def get_all_histories_deprecated(fastapi_request: Request):
    """
    Deprecated: Bulk fetch ถูกลบแล้ว — ใช้ GET /history/{chat_id} โหลดทีละแชท (เฉพาะ user ที่ login) เพื่อหลีกเลี่ยง 429.
    """
    raise HTTPException(
        status_code=410,
        detail="Bulk histories removed. Use GET /api/chat/history/{chat_id} to load one chat at a time (per logged-in user).",
    )


@router.get("/sessions")
async def get_user_sessions(
    fastapi_request: Request,
    limit: int = 50,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID", description="User ID (ให้ตรงกับตอนส่งข้อความ)"),
):
    """
    Get all sessions/chats for the current user
    ใช้ X-User-ID (ถ้ามี) ก่อน cookie เพื่อให้ตรงกับ frontend
    """
    from app.core.security import extract_user_id_from_request
    user_id = x_user_id or extract_user_id_from_request(fastapi_request)
    
    cookie_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    header_user_id = fastapi_request.headers.get("X-User-ID")
    logger.info(f"🔍 /api/chat/sessions - Cookie: {cookie_user_id}, Header: {header_user_id}, Final user_id: {user_id}")
    
    # ✅ ไม่บังคับ login — ถ้าไม่มี user_id คืนรายการว่าง เพื่อให้หน้าแชทโหลดได้ (แสดง "กรุณาเข้าสู่ระบบ" ได้)
    if not user_id:
        logger.warning("No user_id in request, returning empty sessions so chat page can load")
        return {"sessions": [], "require_login": True}
    
    logger.info(f"Fetching all sessions for user_id={user_id}, limit={limit}")
    
    storage = MongoStorage()
    
    try:
        # Get MongoDB database
        from app.storage.connection_manager import ConnectionManager
        conn_mgr = ConnectionManager.get_instance()
        db = conn_mgr.get_database()
        sessions_collection = db["sessions"]
        conversations_collection = db["conversations"]
        
        # ✅ SECURITY: Only query sessions for the exact user_id from session cookie
        # Do NOT try multiple user_ids as this could cause data leakage
        all_sessions = []
        seen_chat_ids = set()
        
        # ✅ SECURITY: Find sessions by user_id ONLY (exact match, no fallback)
        # This ensures users can ONLY see their own sessions
        query = {"user_id": user_id}
        logger.debug(f"🔍 Querying sessions with filter: {query}")
        
        cursor = sessions_collection.find(query).sort("last_updated", -1).limit(limit)
            
        async for doc in cursor:
            session_id = doc.get("session_id", "")
            chat_id = doc.get("chat_id") or session_id.split("::")[-1] if "::" in session_id else session_id
            
            # ✅ SECURITY: Double-check that session belongs to this user
            session_user_id = session_id.split("::")[0] if "::" in session_id else doc.get("user_id")
            if session_user_id != user_id:
                logger.warning(f"Session {session_id} has mismatched user_id: expected {user_id}, found {session_user_id}")
                continue
            
            # Skip duplicates
            if chat_id in seen_chat_ids:
                continue
            seen_chat_ids.add(chat_id)
            
            # ✅ SECURITY: Check if conversation has messages and verify user_id
            # Query conversation with BOTH session_id AND user_id to prevent data leakage
            conv_query = {"session_id": session_id, "user_id": user_id}
            conv_doc = await conversations_collection.find_one(conv_query)
            if conv_doc:
                conv_user_id = conv_doc.get("user_id")
                # Double-check user_id match (additional safety layer)
                if conv_user_id and conv_user_id != user_id:
                    logger.error(f"🚨 SECURITY ALERT: Session {session_id} conversation has mismatched user_id! expected {user_id}, found {conv_user_id}")
                    continue  # Skip this session to prevent data leakage
            elif conv_doc is None and session_id:
                # ✅ If no conversation found, that's OK (new session) - don't skip the session
                pass
            has_messages = conv_doc and conv_doc.get("messages") and len(conv_doc["messages"]) > 0
            msg_count = len(conv_doc.get("messages", [])) if conv_doc else 0

            # ✅ Title: แบบ Gemini — จาก session.title หรือข้อความแรกของ user (ตัดสั้น) หรือ "การสนทนาใหม่"
            title = (doc.get("title") or "").strip()
            if not title and conv_doc:
                messages = conv_doc.get("messages") or []
                for m in messages:
                    if (m.get("role") or "").lower() == "user":
                        raw = (m.get("content") or m.get("text") or "").strip()
                        if raw:
                            title = raw[:50] + ("…" if len(raw) > 50 else "")
                            break
            if not title:
                title = "การสนทนาใหม่"

            last_ts = doc.get("last_updated") or doc.get("created_at")
            last_updated_str = last_ts.isoformat() if last_ts else None
            created_str = doc.get("created_at").isoformat() if doc.get("created_at") else None

            # ✅ SECURITY: Include user_id in response for frontend validation
            all_sessions.append({
                "session_id": session_id,
                "chat_id": chat_id,
                "trip_id": doc.get("trip_id"),
                "user_id": user_id,  # ✅ Include user_id for frontend validation
                "title": title,
                "last_updated": last_updated_str,
                "created_at": created_str,
                "has_messages": has_messages,
                "message_count": msg_count,
            })
        
        # Sort by last_updated descending
        all_sessions.sort(key=lambda x: x.get("last_updated") or "", reverse=True)
        
        logger.info(f"✅ Returning {len(all_sessions)} sessions for user_id={user_id} (email: {user_id})")
        
        # ✅ SECURITY: Log session user_ids for debugging
        if all_sessions:
            session_user_ids = [s.get("user_id") for s in all_sessions[:3]]
            logger.debug(f"First 3 session user_ids: {session_user_ids}")
        
        return {"sessions": all_sessions[:limit]}
        
    except Exception as e:
        logger.error(f"Error fetching user sessions: {e}", exc_info=True)
        return {"sessions": [], "error": str(e)}


@router.post("/select_choice")
async def select_choice(request: dict, fastapi_request: Request):
    """
    Select a choice from the agent's proposed plan_choices or slot_choices
    ✅ SECURITY: Only allows selection for authenticated user's own session
    """
    # ✅ SECURITY: Use security helper to extract user_id (prioritizes cookie, then header)
    from app.core.security import extract_user_id_from_request, validate_session_user_id
    user_id = extract_user_id_from_request(fastapi_request) or request.get("user_id")
    
    # ✅ SECURITY: Validate user_id is not empty
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # ✅ ใช้ chat_id เป็นหลัก (fallback ไป trip_id หรือ client_trip_id สำหรับ backward compatibility)
    chat_id = request.get("chat_id") or request.get("trip_id") or request.get("client_trip_id")
    trip_id = request.get("trip_id") or request.get("client_trip_id")  # ✅ trip_id สำหรับ metadata
    choice_id = request.get("choice_id")
    choice_data = request.get("choice_data")  # ✅ ข้อมูล choice ทั้งหมด
    slot_type = request.get("slot_type")  # ✅ slot type (flight, hotel, etc.)
    
    if not chat_id or not choice_id:
        raise HTTPException(status_code=400, detail="chat_id (or trip_id) and choice_id required")
        
    # ✅ session_id ใช้ chat_id (แต่ละ chat = 1 session)
    session_id = f"{user_id}::{chat_id}"
    
    # ✅ SECURITY: CRITICAL - Validate session_id format matches user_id
    validate_session_user_id(session_id, user_id)
    set_logging_context(session_id=session_id, user_id=user_id)
    
    try:
        storage = MongoStorage()
        
        # ✅ SECURITY: Verify session belongs to this user before proceeding
        existing_session = await storage.get_session(session_id)
        if existing_session and existing_session.user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Unauthorized choose attempt: user {user_id} tried to access session {session_id} owned by {existing_session.user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to access this session")
        
        llm_with_mcp = LLMServiceWithMCP()
        
        # ✅ Get user preferences for agent (personality, style, language, RL)
        _prefs = await _load_user_agent_preferences(storage, user_id)
        agent = TravelAgent(
            storage,
            llm_service=llm_with_mcp,
            agent_personality=_prefs["agentPersonality"],
            response_style=_prefs["responseStyle"],
            detail_level=_prefs["detailLevel"],
            chat_language=_prefs["chatLanguage"],
            reinforcement_learning=_prefs["reinforcementLearning"],
        )

        # ✅ สร้างข้อความที่รวมข้อมูล choice ทั้งหมดเพื่อให้ AI รู้ว่าผู้ใช้เลือกข้อมูลอะไร
        if choice_data:
            # สรุปข้อมูล choice เพื่อให้ AI เข้าใจ
            choice_summary = f"เลือกช้อยส์ {choice_id}"
            if isinstance(choice_data, dict):
                # เพิ่มข้อมูลสำคัญจาก choice
                if choice_data.get("flight"):
                    flight = choice_data.get("flight")
                    segments = flight.get("segments", [])
                    if segments:
                        first_seg = segments[0]
                        last_seg = segments[-1]
                        route = f"{first_seg.get('from', '')} → {last_seg.get('to', '')}"
                        price = flight.get("price_total") or flight.get("price")
                        choice_summary += f" - เที่ยวบิน: {route}, ราคา: {price}"
                elif choice_data.get("hotel"):
                    hotel = choice_data.get("hotel")
                    hotel_name = hotel.get("hotelName") or hotel.get("name")
                    price = hotel.get("price_total") or hotel.get("price")
                    choice_summary += f" - ที่พัก: {hotel_name}, ราคา: {price}"
                elif choice_data.get("transport"):
                    transport = choice_data.get("transport")
                    transport_type = transport.get("type") or transport.get("mode")
                    choice_summary += f" - การเดินทาง: {transport_type}"
                
                # ✅ ส่งข้อมูล choice ทั้งหมดในรูปแบบ JSON string เพื่อให้ AI เข้าใจ
                import json
                choice_summary += f"\n\nข้อมูล choice ที่เลือก:\n{json.dumps(choice_data, ensure_ascii=False, indent=2)}"
            
            user_message = f"{choice_summary}"
        else:
            # Fallback: ถ้าไม่มี choice_data ใช้แบบเดิม
            user_message = f"I choose option {choice_id}"
        
        # ✅ ส่งข้อความที่มีข้อมูล choice ทั้งหมดไปยัง agent
        response_text = await agent.run_turn(session_id, user_message)
        
        # ✅ CRITICAL: Get updated session and save to database immediately
        # This ensures selected_option and trip_plan (with raw data) are persisted
        updated_session = await storage.get_session(session_id)
        
        # ✅ Update trip_id and chat_id if provided
        if trip_id and (not updated_session.trip_id or updated_session.trip_id != trip_id):
            updated_session.trip_id = trip_id
        if chat_id and (not updated_session.chat_id or updated_session.chat_id != chat_id):
            updated_session.chat_id = chat_id
        
        # ✅ CRITICAL: Always save session after choice selection to persist trip_plan with selected_option and options_pool
        session_saved = await storage.save_session(updated_session)
        if not session_saved:
            logger.error(f"Failed to save session to database after choice selection: session_id={session_id}")
        else:
            logger.info(f"Session saved successfully with trip_plan data: session_id={session_id}")
            # 🎯 Selection preferences: บันทึก choice history (ใช้ร่วมกับ RL/ML)
            if choice_data and isinstance(choice_data, dict):
                try:
                    from app.services.selection_preferences import record_choice
                    slot_for_history = slot_type or "unknown"
                    await record_choice(user_id, slot_for_history, choice_data, slot_type=slot_type)
                except Exception as rec_err:
                    logger.debug(f"Record choice for preferences (non-critical): {rec_err}")
            # Log what was saved for debugging
            confirmed_with_selection = []
            segments_with_options = []
            all_segments = (
                updated_session.trip_plan.travel.flights.outbound + 
                updated_session.trip_plan.travel.flights.inbound +
                updated_session.trip_plan.accommodation.segments +
                updated_session.trip_plan.travel.ground_transport
            )
            for seg in all_segments:
                if seg.status.value == "confirmed" and seg.selected_option:
                    confirmed_with_selection.append("confirmed_with_option")
                if seg.options_pool and len(seg.options_pool) > 0:
                    segments_with_options.append(f"{len(seg.options_pool)}_options")
            
            if confirmed_with_selection or segments_with_options:
                logger.info(f"Saved session: {len(confirmed_with_selection)} confirmed segments with selected_option, {len(segments_with_options)} segments with options_pool (raw data preserved)")
        
        return {
            "ok": True,
            "response": response_text,
            "session_id": session_id,
            "trip_id": updated_session.trip_id,
            "chat_id": updated_session.chat_id,
            "trip_title": updated_session.title
        }
    except Exception as e:
        logger.error(f"Select choice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        clear_logging_context()


@router.post("/tts")
async def generate_tts(request: dict, fastapi_request: Request):
    """
    Generate speech audio from text using Gemini TTS
    """
    try:
        text = request.get("text", "").strip()
        if not text:
            raise HTTPException(status_code=400, detail="Text is required")
        
        voice_name = request.get("voice_name", "Kore")  # Kore, Aoede, Callirrhoe
        audio_format = request.get("audio_format", "MP3")  # MP3, LINEAR16, OGG_OPUS
        
        tts_service = get_tts_service()
        if not tts_service:
            raise HTTPException(status_code=503, detail="TTS service not available")
        
        audio_data = await tts_service.generate_speech(
            text=text,
            voice_name=voice_name,
            language="th",
            audio_format=audio_format
        )
        
        # TTS ส่งคืน WAV (เบราว์เซอร์เล่นได้ทั้ง WAV/MP3)
        content_type = "audio/wav"
        return Response(
            content=audio_data,
            media_type=content_type,
            headers={
                "Content-Disposition": 'inline; filename="tts.wav"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS generation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate speech: {str(e)}")


@router.websocket("/live-audio")
async def live_audio_conversation(websocket: WebSocket):
    """
    WebSocket endpoint for real-time voice conversation using Gemini Live API
    Provides human-like voice interaction with native audio processing
    """
    await websocket.accept()
    logger.info("Live audio WebSocket connection established")
    
    live_service = None
    session = None
    
    try:
        # Initialize Live Audio Service
        live_service = LiveAudioService()
        
        # ✅ SECURITY: Get user_id from query params (WebSocket cannot use cookies easily)
        # Note: Frontend should send user_id in query params for WebSocket connections
        user_id = websocket.query_params.get("user_id")
        
        # ✅ SECURITY: Validate user_id is not empty
        if not user_id or user_id == "anonymous":
            await websocket.close(code=1008, reason="Authentication required")
            logger.warning("WebSocket connection rejected: No user_id provided")
            return
        
        chat_id = websocket.query_params.get("chat_id")
        
        # Build system instruction for travel agent
        system_instruction = """คุณเป็น Travel Agent AI ที่พูดคุยด้วยเสียงแบบธรรมชาติ
- ใช้ภาษาไทยในการสนทนา
- พูดคุยแบบเป็นมิตร เป็นธรรมชาติ เหมือนมนุษย์จริงๆ
- ฟังน้ำเสียงและอารมณ์ของผู้ใช้ และตอบสนองด้วยอารมณ์ที่เหมาะสม
- สามารถขัดจังหวะได้เมื่อผู้ใช้ต้องการพูด
- ช่วยวางแผนการเดินทาง หาเที่ยวบิน ที่พัก และการขนส่ง
- ตอบคำถามเกี่ยวกับการท่องเที่ยวอย่างเป็นมิตรและเป็นประโยชน์"""
        
        # #region agent log (Hypothesis A)
        import json
        _write_debug_log({
            "id": f"log_{int(__import__('time').time() * 1000)}_websocket_before_create",
            "timestamp": int(__import__('time').time() * 1000),
            "location": "chat.py:1710",
            "message": "WebSocket: Before create_session",
            "data": {"user_id": user_id},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        })
        # #endregion
        
        # Create Live API session
        try:
            session = await live_service.create_session(
                system_instruction=system_instruction
            )
            logger.info(f"Live API session created for user: {user_id}")
            
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_websocket_session_created",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "chat.py:1720",
                "message": "WebSocket: Session created successfully",
                "data": {"session_type": type(session).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
        except Exception as create_error:
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_websocket_create_failed",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "chat.py:1730",
                "message": "WebSocket: create_session failed",
                "data": {"error": str(create_error), "error_type": type(create_error).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            raise
        
        # Send initial confirmation
        await websocket.send_json({
            "type": "connected",
            "message": "พร้อมสนทนาด้วยเสียงแล้ว"
        })
        
        # ── callbacks ──────────────────────────────────────────────────
        async def send_audio_to_client(audio_bytes: bytes):
            """ส่ง PCM audio เป็น binary frame (เร็วกว่า base64)"""
            try:
                await websocket.send_bytes(audio_bytes)
            except Exception as e:
                logger.error(f"Error sending audio to client: {e}")

        async def send_text_to_client(text: str):
            try:
                await websocket.send_json({"type": "text", "data": text})
            except Exception as e:
                logger.error(f"Error sending text to client: {e}")

        async def send_turn_complete():
            try:
                await websocket.send_json({"type": "turn_complete"})
            except Exception as e:
                logger.error(f"Error sending turn_complete: {e}")

        # ── background task: รับ audio/text จาก Gemini Live ──────────
        async def receive_from_session():
            try:
                async for message in live_service.receive_audio_stream(
                    session,
                    on_audio_chunk=send_audio_to_client,
                    on_text_chunk=send_text_to_client
                ):
                    # ตรวจ turn_complete จาก server_content
                    if message.get("type") == "turn_complete":
                        await send_turn_complete()
                    elif message.get("type") == "interruption":
                        await websocket.send_json({"type": "interruption"})
            except Exception as e:
                logger.error(f"Error receiving from session: {e}", exc_info=True)
                try:
                    await websocket.send_json({"type": "error", "message": f"Session error: {str(e)}"})
                except Exception:
                    pass

        receive_task = asyncio.create_task(receive_from_session())

        # ── main loop: รับ PCM binary จาก browser ────────────────────
        while True:
            try:
                data = await websocket.receive()

                if "bytes" in data:
                    # ✅ binary frame = raw PCM 16-bit LE 16kHz mono จาก ScriptProcessor
                    audio_bytes = data["bytes"]
                    if audio_bytes:
                        await live_service.send_audio_chunk(session, audio_bytes)

                elif "text" in data:
                    message_data = json.loads(data["text"])
                    message_type = message_data.get("type")

                    if message_type == "text":
                        text = message_data.get("data", "")
                        if text:
                            await live_service.send_text_message(session, text, turn_complete=True)
                    elif message_type == "end_turn":
                        await live_service.send_text_message(session, "", turn_complete=True)
                    elif message_type == "audio":
                        # base64 fallback (legacy)
                        audio_base64 = message_data.get("data", "")
                        if audio_base64:
                            audio_bytes = base64.b64decode(audio_base64)
                            await live_service.send_audio_chunk(session, audio_bytes)

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected")
                break
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}", exc_info=True)
                try:
                    await websocket.send_json({"type": "error", "message": f"Processing error: {str(e)}"})
                except Exception:
                    pass
        
        # Cancel receive task
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass
            
    except Exception as e:
        logger.error(f"Live audio WebSocket error: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Connection error: {str(e)}"
            })
        except Exception:
            pass
    finally:
        # Cleanup
        if session:
            try:
                await live_service.close_session(session)
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("Live audio WebSocket connection closed")


@router.delete("/sessions/{chat_id}")
async def delete_chat_session(
    chat_id: str,
    fastapi_request: Request,
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
):
    """
    Delete a chat session and its conversation history permanently.
    Removes both the session document and conversation messages from MongoDB.
    ✅ SECURITY: Only allows deletion for authenticated user's own session.
    ใช้ X-User-ID (ถ้ามี) ก่อน cookie เพื่อให้ตรงกับ frontend
    """
    from app.core.security import extract_user_id_from_request
    user_id = x_user_id or extract_user_id_from_request(fastapi_request)

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    session_id = f"{user_id}::{chat_id}"
    logger.info(f"Deleting chat session: session_id={session_id}, user_id={user_id}")

    try:
        from app.storage.connection_manager import ConnectionManager
        conn_mgr = ConnectionManager.get_instance()
        db = conn_mgr.get_database()

        sessions_collection = db["sessions"]
        conversations_collection = db["conversations"]

        # ✅ SECURITY: Verify session belongs to this user before deleting
        session_doc = await sessions_collection.find_one({"session_id": session_id})
        if session_doc:
            session_user_id = session_doc.get("user_id") or (session_id.split("::")[0] if "::" in session_id else None)
            if session_user_id and session_user_id != user_id:
                logger.error(f"🚨 SECURITY: Unauthorized delete attempt: user {user_id} tried to delete session owned by {session_user_id}")
                raise HTTPException(status_code=403, detail="You do not have permission to delete this session")

        # Delete session document
        session_result = await sessions_collection.delete_one({"session_id": session_id, "user_id": user_id})

        # Delete conversation/messages document
        conv_result = await conversations_collection.delete_one({"session_id": session_id, "user_id": user_id})

        # Redis removed — MongoDB is the only storage

        logger.info(f"Deleted session {session_id}: sessions={session_result.deleted_count}, conversations={conv_result.deleted_count}")
        return {"ok": True, "session_id": session_id, "deleted_sessions": session_result.deleted_count, "deleted_conversations": conv_result.deleted_count}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete session error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset")
async def reset_chat(request: dict, fastapi_request: Request):
    """
    Reset chat context for a chat (ใช้ chat_id)
    """
    session_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    user_id = session_user_id or request.get("user_id") or "anonymous"
    
    # ✅ ใช้ chat_id เป็นหลัก (fallback ไป client_trip_id สำหรับ backward compatibility)
    chat_id = request.get("chat_id") or request.get("client_trip_id")
    
    if not chat_id:
        return {"ok": False, "error": "chat_id (or client_trip_id) required"}
        
    # ✅ session_id ใช้ chat_id (แต่ละ chat = 1 session)
    session_id = f"{user_id}::{chat_id}"
    
    try:
        storage = MongoStorage()
        
        # ✅ SECURITY: Verify session belongs to this user before clearing
        existing_session = await storage.get_session(session_id)
        if existing_session and existing_session.user_id != user_id:
            logger.warning(f"Unauthorized reset attempt: user {user_id} tried to reset session {session_id} owned by {existing_session.user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to reset this session")
        
        # Actually clear the session data in MongoDB
        success = await storage.clear_session_data(session_id)
        return {"ok": success}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def run_title_generator(session_id: str, user_input: str, bot_response: str):
    """
    Background worker function for title generation
    Runs asynchronously after response is sent to user
    
    Args:
        session_id: Session identifier
        user_input: User's message
        bot_response: Bot's response
    """
    try:
        # Set logging context for background task
        set_logging_context(session_id=session_id, user_id=session_id.split("::")[0])
        
        logger.info(f"Starting background title generation for session {session_id}")
        
        # Generate title
        title = await generate_chat_title(user_input, bot_response)
        
        # Update session title
        storage = MongoStorage()
        await storage.update_title(session_id, title)
        
        logger.info(f"Title generated and saved for session {session_id}: {title}")
    
    except Exception as e:
        logger.error(f"Error in background title generation for session {session_id}: {e}", exc_info=True)
        # Don't raise - background task failures shouldn't affect user experience
    finally:
        clear_logging_context()


class AutoDeleteRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1, le=365)


@router.post("/auto-delete-old")
async def auto_delete_old_conversations(request: AutoDeleteRequest, fastapi_request: Request):
    """
    Delete all sessions and conversations older than N days for the authenticated user.
    Respects user privacy preference: autoDeleteConversations + autoDeleteDays.
    """
    from app.core.security import extract_user_id_from_request
    user_id = extract_user_id_from_request(fastapi_request)

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    days = request.older_than_days
    logger.info(f"Auto-delete conversations older than {days} days for user: {user_id}")

    try:
        from app.storage.connection_manager import ConnectionManager
        from datetime import timedelta
        conn_mgr = ConnectionManager.get_instance()
        db = conn_mgr.get_database()

        sessions_collection = db["sessions"]
        conversations_collection = db["conversations"]

        cutoff_dt = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_dt.isoformat()

        # Find sessions older than cutoff for this user
        old_sessions = await sessions_collection.find(
            {
                "user_id": user_id,
                "last_updated": {"$lt": cutoff_iso}
            },
            {"session_id": 1}
        ).to_list(length=500)

        old_session_ids = [s["session_id"] for s in old_sessions if s.get("session_id")]

        if not old_session_ids:
            return {"ok": True, "deleted_sessions": 0, "deleted_conversations": 0, "message": "No old conversations to delete"}

        # Delete sessions
        s_result = await sessions_collection.delete_many({
            "user_id": user_id,
            "session_id": {"$in": old_session_ids}
        })

        # Delete conversation documents
        c_result = await conversations_collection.delete_many({
            "user_id": user_id,
            "session_id": {"$in": old_session_ids}
        })

        # Redis removed — MongoDB is the only storage

        logger.info(
            f"Auto-deleted {s_result.deleted_count} sessions and {c_result.deleted_count} conversations "
            f"older than {days} days for user: {user_id}"
        )

        return {
            "ok": True,
            "deleted_sessions": s_result.deleted_count,
            "deleted_conversations": c_result.deleted_count,
            "message": f"Deleted {s_result.deleted_count} old conversation(s)"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Auto-delete conversations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Auto-delete failed: {str(e)}")


class FlushSessionRequest(BaseModel):
    session_id: Optional[str] = None  # flush specific session; if None, flush all user sessions


@router.post("/flush-session")
async def flush_session_to_mongodb(request: FlushSessionRequest, fastapi_request: Request):
    """
    No-op endpoint kept for frontend compatibility.
    Redis removed — all data is already persisted directly to MongoDB in real-time.
    """
    return {"ok": True, "flushed": 0, "message": "MongoDB-only mode: data already persisted"}
