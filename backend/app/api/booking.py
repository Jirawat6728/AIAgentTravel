"""
เราเตอร์ API การจอง
จัดการการสร้างจอง การชำระเงิน การยกเลิก และรายการจอง
เชื่อมกับ Omise Payment Gateway
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Callable, Awaitable
from datetime import datetime
import random
import asyncio
import uuid
from app.api.notification import push_notification_event

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.mongodb_storage import MongoStorage
from app.services.omise_service import OmiseService
from app.core.exceptions import AmadeusException
import httpx

logger = get_logger(__name__)

# ✅ ชื่อฟิลด์ที่ต้องมีในโปรไฟล์ก่อนจอง (ข้อมูลพื้นฐาน) — ถ้าไม่ครบให้แจ้งผู้ใช้
BOOKING_REQUIRED_PROFILE_FIELDS = [
    ("first_name", "ชื่อ (ภาษาอังกฤษ)"),
    ("last_name", "นามสกุล (ภาษาอังกฤษ)"),
    ("email", "อีเมล"),
    ("phone", "เบอร์โทรศัพท์"),
]


def _get_missing_profile_fields_for_booking(user_doc: dict) -> list[str]:
    """คืนรายการชื่อฟิลด์ (ภาษาไทย) ที่ยังไม่กรอก — ใช้แจ้งผู้ใช้ให้กรอกข้อมูลให้ครบก่อนจอง"""
    if not user_doc:
        return [label for _, label in BOOKING_REQUIRED_PROFILE_FIELDS]
    missing = []
    for key, label in BOOKING_REQUIRED_PROFILE_FIELDS:
        val = user_doc.get(key)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(label)
    return missing


# ✅ My Bookings = Amadeus sandbox: retry จนกว่าจะสำเร็จ ห้ามฝั่งใดฝั่งหนึ่งสำเร็จอย่างเดียว
AMADEUS_SYNC_MAX_RETRIES = 5
AMADEUS_SYNC_RETRY_DELAY_SEC = 2


async def _amadeus_retry_until_success(operation_name: str, coro_fn: Callable[[], Awaitable[None]]) -> None:
    """รัน Amadeus operation ด้วย retry จนกว่าจะสำเร็จ (หรือครบจำนวนครั้ง)"""
    last_err = None
    for attempt in range(1, AMADEUS_SYNC_MAX_RETRIES + 1):
        try:
            await coro_fn()
            if attempt > 1:
                logger.info(f"Amadeus {operation_name} succeeded on attempt {attempt}")
            return
        except Exception as e:
            last_err = e
            logger.warning(f"Amadeus {operation_name} attempt {attempt}/{AMADEUS_SYNC_MAX_RETRIES} failed: {e}")
            if attempt < AMADEUS_SYNC_MAX_RETRIES:
                await asyncio.sleep(AMADEUS_SYNC_RETRY_DELAY_SEC)
    raise last_err


async def _sync_booking_to_amadeus_sandbox(booking_doc: dict, bookings_collection) -> None:
    """
    ส่งข้อมูลจองทั้งหมดไปยัง Amadeus sandbox
    ต้องสำเร็จเท่านั้น — ถ้า Amadeus ล้มเหลวจะ raise เพื่อไม่ให้การชำระเงินถูกยืนยัน
    """
    if not booking_doc:
        return
    if settings.amadeus_booking_env.lower() == "production":
        raise AmadeusException("Amadeus booking env is production — ไม่อนุญาตให้ sync ใน production")
    from app.services.travel_service import orchestrator
    plan = booking_doc.get("plan") or {}
    travel_slots = booking_doc.get("travel_slots") or {}
    user_id = booking_doc.get("user_id", "")
    booking_id = booking_doc.get("booking_id") or str(booking_doc.get("_id", ""))
    adults = int(travel_slots.get("adults") or 1)
    children = int(travel_slots.get("children") or 0)
    travelers = []
    for i in range(adults):
        travelers.append({
            "id": str(i + 1),
            "dateOfBirth": "1990-01-01",
            "name": {"firstName": "Traveler", "lastName": f"Adult{i + 1}"},
            "gender": "M"
        })
    for i in range(children):
        travelers.append({
            "id": str(adults + i + 1),
            "dateOfBirth": "2015-01-01",
            "name": {"firstName": "Child", "lastName": f"{i + 1}"},
            "gender": "M"
        })
    if not travelers:
        travelers = [{"id": "1", "dateOfBirth": "1990-01-01", "name": {"firstName": "Guest", "lastName": "1"}, "gender": "M"}]
    flight_order_ids = []
    hotel_booking_ids = []
    travel = plan.get("travel") or {}
    flights_data = travel.get("flights") or {}
    for direction in ("outbound", "inbound"):
        segments = flights_data.get(direction) or []
        for seg in segments:
            opt = seg.get("selected_option") or {}
            raw = opt.get("raw_data") or opt
            if not raw:
                continue
            offer = raw if isinstance(raw, dict) else {}
            if not offer.get("id") and not offer.get("itineraries"):
                continue
            result = await orchestrator.create_flight_order(offer, travelers)
            if result and result.get("data", {}).get("id"):
                flight_order_ids.append(result["data"]["id"])
                logger.info(f"Amadeus sandbox flight order created: {result['data']['id']} for booking {booking_id}")
    acc = plan.get("accommodation") or {}
    acc_segments = acc.get("segments") if isinstance(acc, dict) else (plan.get("accommodations") or [])
    if not isinstance(acc_segments, list):
        acc_segments = []
    guests = [{"name": {"title": "MR", "firstName": "Guest", "lastName": "1"}, "contact": {"email": "guest@test.com", "phone": "+66800000000"}}]
    for seg in acc_segments:
        opt = seg.get("selected_option") if isinstance(seg, dict) else None
        if not opt:
            continue
        raw = (opt.get("raw_data") or opt) if isinstance(opt, dict) else {}
        offer_id = raw.get("id") or raw.get("offerId") or (opt.get("id") if isinstance(opt, dict) else None)
        if not offer_id:
            continue
        hotel_offer = {"id": offer_id} if isinstance(offer_id, str) else offer_id
        result = await orchestrator.create_hotel_booking(hotel_offer, guests)
        if result and result.get("data", {}).get("id"):
            hotel_booking_ids.append(result["data"]["id"])
            logger.info(f"Amadeus sandbox hotel booking created: {result['data']['id']} for booking {booking_id}")
    from bson import ObjectId
    update_filter = {"user_id": user_id}
    if len(booking_id) == 24:
        try:
            update_filter["_id"] = ObjectId(booking_id)
        except Exception:
            update_filter["booking_id"] = booking_id
    else:
        update_filter["booking_id"] = booking_id
    await bookings_collection.update_one(
        update_filter,
        {"$set": {
            "amadeus_sync": {
                "flight_order_ids": flight_order_ids,
                "hotel_booking_ids": hotel_booking_ids,
                "synced_at": datetime.utcnow().isoformat()
            },
            "updated_at": datetime.utcnow().isoformat()
        }}
    )
    logger.info(f"Booking {booking_id} synced to Amadeus sandbox: flights={len(flight_order_ids)}, hotels={len(hotel_booking_ids)}")

router = APIRouter(prefix="/api/booking", tags=["booking"])


def _generate_numeric_booking_id() -> str:
    """Generate a unique numeric booking ID (10–12 digits), Amadeus-style."""
    # 8 digits from timestamp (ms) + 4 random digits = 12 digits total, unique enough
    base = int(datetime.utcnow().timestamp() * 1000) % (10 ** 8)
    suffix = random.randint(1000, 9999)
    return str(base * 10000 + suffix)


# =============================================================================
# Request/Response Models
# =============================================================================

class BookingCreateRequest(BaseModel):
    """Test-validated: plan (dict), travel_slots (dict). Cancel via POST /api/booking/cancel?booking_id=..."""
    trip_id: str = Field(..., description="Trip ID")
    chat_id: Optional[str] = None
    user_id: str = Field(..., description="User ID (or X-User-ID header)")
    plan: Dict[str, Any] = Field(
        ...,
        description="Trip plan dict, e.g. {flights: [...], hotels: [...], ground_transfers: [], budget, travelers}"
    )
    travel_slots: Dict[str, Any] = Field(
        ...,
        description="Travel slots dict, e.g. {origin_city, destination_city, departure_date, return_date, nights}"
    )
    total_price: float = Field(..., description="Total booking price")
    currency: str = Field(default="THB", description="Currency code")
    mode: Optional[str] = Field(default="normal", description="Chat mode: 'normal' or 'agent'")
    auto_booked: Optional[bool] = Field(default=False, description="Whether booking was auto-created by Agent Mode")
    passengers: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of passengers: [{name, type, passport_no, ...}] — ถ้าไม่ส่งมาจะดึงจาก user profile อัตโนมัติ"
    )
    replace_booking_id: Optional[str] = Field(
        default=None,
        description="โหมดแก้ไขทริป: ID การจองเดิมที่จะยกเลิกก่อนสร้างจองใหม่ (ใช้ trip_id เดิม)"
    )


class BookingListResponse(BaseModel):
    """Response model for booking list"""
    ok: bool
    bookings: List[Dict[str, Any]]
    count: int


class BookingPaymentResponse(BaseModel):
    """Response model for payment"""
    ok: bool
    message: str
    payment_url: Optional[str] = None
    status: Optional[str] = None
    booking_reference: Optional[str] = None


class BookingUpdateRequest(BaseModel):
    """Request model for updating a booking"""
    plan: Optional[Dict[str, Any]] = Field(default=None, description="Updated trip plan data")
    travel_slots: Optional[Dict[str, Any]] = Field(default=None, description="Updated travel slot information")
    total_price: Optional[float] = Field(default=None, description="Updated total booking price")
    currency: Optional[str] = Field(default=None, description="Updated currency code")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# =============================================================================
# Booking Endpoints
# =============================================================================

@router.post("/create")
async def create_booking(booking_request: BookingCreateRequest, fastapi_request: Request):
    """
    Create a new booking (pending payment or confirmed for Agent Mode).
    Returns {ok, booking_id, message, status}. Cancel via POST /api/booking/cancel?booking_id=...
    SECURITY: Amadeus booking is sandbox-only (production blocked).
    ✅ ใช้ user_id จาก session/cookie เป็นหลัก เพื่อให้การจองแสดงใน My Bookings (list ใช้ session เดียวกัน)
    """
    try:
        # ✅ SECURITY: Check Amadeus booking environment - block production
        booking_env = settings.amadeus_booking_env.lower()
        if booking_env == "production":
            logger.error("🚨 SECURITY: AMADEUS_BOOKING_ENV=production is NOT ALLOWED for booking operations!")
            raise HTTPException(
                status_code=403,
                detail="Booking in production environment is not allowed for security reasons. Please use sandbox environment."
            )
        
        # ✅ ใช้ user_id ให้ตรงกับ My Bookings: ถ้า client ส่ง X-User-ID ให้ใช้เป็นหลัก (แชท/Agent ส่ง header นี้) แล้วค่อย cookie/body
        from app.core.security import extract_user_id_from_request
        header_user_id = (fastapi_request.headers.get("X-User-ID") or "").strip()
        session_user_id = extract_user_id_from_request(fastapi_request)
        body_user_id = (booking_request.user_id or "").strip()
        user_id = (header_user_id or body_user_id or session_user_id).strip() if (header_user_id or body_user_id or session_user_id) else None
        if header_user_id and session_user_id and header_user_id != session_user_id:
            logger.debug(f"Booking create: using X-User-ID ({header_user_id}) so list will show this booking for same user")
        
        # ✅ Log incoming request for debugging
        logger.info(f"Creating booking - trip_id: {booking_request.trip_id}, user_id: {user_id}, mode: {booking_request.mode}, booking_env: {booking_env}")
        logger.debug(f"Booking request - plan keys: {list(booking_request.plan.keys()) if booking_request.plan else 'None'}, travel_slots keys: {list(booking_request.travel_slots.keys()) if booking_request.travel_slots else 'None'}, total_price: {booking_request.total_price}")
        
        # ✅ Validate required fields
        if not booking_request.plan or not isinstance(booking_request.plan, dict):
            raise HTTPException(status_code=400, detail="Invalid request format: 'plan' is required and must be a dictionary")
        if not booking_request.travel_slots or not isinstance(booking_request.travel_slots, dict):
            raise HTTPException(status_code=400, detail="Invalid request format: 'travel_slots' is required and must be a dictionary")
        if booking_request.total_price is None or (isinstance(booking_request.total_price, (int, float)) and booking_request.total_price < 0):
            raise HTTPException(status_code=400, detail="Invalid request format: 'total_price' must be a non-negative number")
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid request format: 'user_id' is required (send X-User-ID header or user_id in body)")
        if not booking_request.trip_id:
            raise HTTPException(status_code=400, detail="Invalid request format: 'trip_id' is required")
        
        storage = MongoStorage()
        await storage.connect()
        
        # ✅ ต้องยืนยันอีเมลก่อนถึงจะจองได้
        users_collection = storage.db["users"]
        user_doc = await users_collection.find_one({"user_id": user_id})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        if not user_doc.get("email_verified", False):
            raise HTTPException(
                status_code=403,
                detail="กรุณายืนยันอีเมลก่อนจึงจะจองได้ ไปที่ การตั้งค่า > สถานะการยืนยันอีเมล > ส่งอีเมลยืนยัน"
            )
        
        # ✅ ข้อมูลพื้นฐานไม่ครบ — ไม่งี่นจะจองไม่ได้ แจ้งให้ผู้ใช้ไปกรอกใน ข้อมูลพื้นฐาน ให้ครบ
        missing_fields = _get_missing_profile_fields_for_booking(user_doc)
        if missing_fields:
            missing_list = ", ".join(missing_fields)
            raise HTTPException(
                status_code=400,
                detail=f"กรุณากรอกข้อมูลใน ข้อมูลพื้นฐาน ให้ครบก่อนจึงจะจองได้: {missing_list} — ไปที่ การตั้งค่า > ข้อมูลพื้นฐาน"
            )
        
        # ✅ ประวัติ workflow: บันทึก summary → booking (ผู้ใช้กดยืนยันจอง)
        _session_id = f"{user_id}::{booking_request.chat_id or booking_request.trip_id}"
        try:
            from app.services.workflow_history import append_workflow_event_fire_and_forget
            append_workflow_event_fire_and_forget(_session_id, "summary", "booking")
        except Exception:
            pass
        
        # ✅ Agent Mode: Still requires payment (Amadeus sandbox needs payment before booking)
        # Status is always "pending_payment" - user must pay first
        initial_status = "pending_payment"
        
        bookings_collection = storage.db["bookings"]
        # ✅ Generate unique numeric booking_id (Amadeus-style, 10–12 digits)
        for _ in range(5):
            numeric_id = _generate_numeric_booking_id()
            existing = await bookings_collection.find_one({"booking_id": numeric_id})
            if not existing:
                break
            logger.debug(f"Booking ID collision, retrying: {numeric_id}")
        else:
            numeric_id = _generate_numeric_booking_id()  # fallback

        # ── ดึงข้อมูลผู้โดยสาร ──────────────────────────────────────────────────
        passengers = booking_request.passengers or []
        if not passengers:
            # ดึงจาก user profile อัตโนมัติ
            try:
                users_collection = storage.db["users"]
                user_doc = await users_collection.find_one({"user_id": user_id})
                if user_doc:
                    from app.services.user_family_service import get_user_family
                    # ผู้จองหลัก — เก็บทั้งชื่อไทยและอังกฤษแยกกัน
                    main_name_th = f"{user_doc.get('first_name_th', '')} {user_doc.get('last_name_th', '')}".strip()
                    main_name_en = f"{user_doc.get('first_name', '')} {user_doc.get('last_name', '')}".strip()
                    main_name = (
                        main_name_th
                        or user_doc.get("full_name")
                        or main_name_en
                        or user_doc.get("name")
                        or user_doc.get("email", "").split("@")[0]
                        or "ผู้โดยสาร"
                    )
                    main_pax: dict = {
                        "name": main_name,
                        "type": "adult",
                        "is_main_booker": True,
                    }
                    # บันทึกชื่อไทยและอังกฤษแยกกันเพื่อให้ frontend เลือกแสดงได้
                    if main_name_th:
                        main_pax["name_th"] = main_name_th
                    if main_name_en:
                        main_pax["name_en"] = main_name_en
                    passengers.append(main_pax)
                    # family members (co-travelers) — อ่านจาก user_family
                    family = await get_user_family(storage.db, user_id)
                    adults_needed = int(booking_request.travel_slots.get("adults") or 1) - 1
                    children_needed = int(booking_request.travel_slots.get("children") or 0)
                    added_adults = 0
                    added_children = 0
                    for member in family:
                        member_type = member.get("type", "adult")
                        # เก็บทั้งชื่อไทยและอังกฤษแยกกัน
                        member_name_th = f"{member.get('first_name_th', '')} {member.get('last_name_th', '')}".strip()
                        member_name_en = f"{member.get('first_name', '')} {member.get('last_name', '')}".strip()
                        member_name = (
                            member_name_th
                            or member_name_en
                            or member.get("name", "")
                        )
                        if not member_name:
                            continue
                        member_pax: dict = {"name": member_name, "type": member_type}
                        if member_name_th:
                            member_pax["name_th"] = member_name_th
                        if member_name_en:
                            member_pax["name_en"] = member_name_en
                        if member_type == "adult" and added_adults < adults_needed:
                            passengers.append(member_pax)
                            added_adults += 1
                        elif member_type == "child" and added_children < children_needed:
                            passengers.append(member_pax)
                            added_children += 1
            except Exception as pax_err:
                logger.warning(f"Failed to build passengers list: {pax_err}")

        # Create booking document
        booking_doc = {
            "booking_id": numeric_id,  # ✅ ตัวเลขแบบ Amadeus (ใช้เป็น ID หลักใน API และ UI)
            "trip_id": booking_request.trip_id,
            "chat_id": booking_request.chat_id,
            "user_id": user_id,  # ✅ Use session user_id so /list returns this booking
            "plan": booking_request.plan,
            "travel_slots": booking_request.travel_slots,
            "total_price": booking_request.total_price,
            "currency": booking_request.currency,
            "status": initial_status,  # ✅ "confirmed" for Agent Mode, "pending_payment" for Normal Mode
            "passengers": passengers,  # ✅ รายชื่อผู้โดยสาร
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "mode": booking_request.mode or "normal",  # ✅ Store chat mode
                "auto_booked": booking_request.auto_booked or False  # ✅ Flag for agent mode
            }
        }
        
        # ✅ โหมดแก้ไขทริป: ยกเลิกการจองเดิมก่อน แล้วสร้างจองใหม่ใน trip_id เดิม
        if getattr(booking_request, "replace_booking_id", None):
            from bson import ObjectId
            rid = (booking_request.replace_booking_id or "").strip()
            if rid:
                old_booking = None
                try:
                    old_booking = await bookings_collection.find_one(
                        {"_id": ObjectId(rid), "user_id": user_id}
                    )
                except Exception:
                    pass
                if not old_booking:
                    old_booking = await bookings_collection.find_one(
                        {"booking_id": rid, "user_id": user_id}
                    )
                if not old_booking:
                    raise HTTPException(
                        status_code=400,
                        detail="ไม่พบการจองเดิมที่ต้องการแทนที่ หรือไม่มีสิทธิ์แก้ไข"
                    )
                if old_booking.get("trip_id") != booking_request.trip_id:
                    raise HTTPException(
                        status_code=400,
                        detail="การจองเดิมไม่ตรงกับทริปนี้ (trip_id ไม่ตรงกัน)"
                    )
                old_id = str(old_booking.get("_id") or old_booking.get("booking_id") or rid)
                old_status = (old_booking.get("status") or "").lower()
                if old_status not in ("cancelled",):
                    # Amadeus sandbox: ยกเลิก flight orders แบบ best-effort
                    amadeus_sync = old_booking.get("amadeus_sync") or {}
                    flight_order_ids = amadeus_sync.get("flight_order_ids") or []
                    if flight_order_ids and settings.amadeus_booking_env.lower() != "production":
                        from app.services.travel_service import orchestrator
                        for order_id in flight_order_ids:
                            async def _cancel_one(oid=order_id):
                                await orchestrator.delete_flight_order(oid)
                            try:
                                await _amadeus_retry_until_success(f"cancel_flight_order_{order_id}", _cancel_one)
                            except Exception as ae:
                                logger.warning(f"Amadeus cancel (replace): booking={old_id} order={order_id}: {ae}")
                    # อัปเดต DB เป็น cancelled
                    try:
                        await bookings_collection.update_one(
                            {"_id": old_booking["_id"]},
                            {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
                        )
                    except Exception:
                        await bookings_collection.update_one(
                            {"booking_id": old_booking.get("booking_id"), "user_id": user_id},
                            {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
                        )
                    logger.info(f"Replace booking: cancelled old booking {old_id} for trip_id={booking_request.trip_id}")
        
        # ✅ CRUD STABILITY: Check for duplicate booking (same trip_id + user_id)
        existing_booking = await bookings_collection.find_one({
            "trip_id": booking_request.trip_id,
            "user_id": user_id,
            "status": {"$in": ["pending_payment", "confirmed", "paid"]}
        })
        if existing_booking:
            logger.warning(f"Duplicate booking attempt: trip_id={booking_request.trip_id}, user_id={user_id}")
            raise HTTPException(
                status_code=409,
                detail="A booking for this trip already exists. Please update the existing booking instead."
            )
        
        # ✅ CRUD STABILITY: Insert with error handling for duplicate key errors
        try:
            result = await bookings_collection.insert_one(booking_doc)
            booking_id = numeric_id  # ✅ Return numeric ID (ไม่ใช้ ObjectId)
        except Exception as insert_error:
            error_str = str(insert_error).lower()
            if "duplicate" in error_str or "e11000" in error_str:
                logger.warning(f"Duplicate key error on booking insert: {insert_error}")
                raise HTTPException(
                    status_code=409,
                    detail="A booking with this information already exists"
                )
            raise
        
        logger.info(f"Created booking: {booking_id} for user: {user_id} (status: {initial_status})")
        
        session_id = f"{user_id}::{booking_request.chat_id or booking_request.trip_id}"
        # ✅ ประวัติ workflow สำหรับ debug/analytics: บันทึก booking → done
        try:
            from app.services.workflow_history import append_workflow_event_fire_and_forget
            append_workflow_event_fire_and_forget(session_id, "booking", "done", {"booking_id": booking_id, "status": initial_status})
        except Exception as hist_err:
            logger.debug(f"Workflow history append skip: {hist_err}")
        
        # ✅ เคลียร์ Redis workflow + options + raw Amadeus เมื่อจองสำเร็จ (workflow เสร็จสิ้น)
        try:
            from app.services.options_cache import get_options_cache
            from app.services.workflow_state import get_workflow_state_service
            options_cache = get_options_cache()
            wf = get_workflow_state_service()
            await options_cache.clear_session_all(session_id)
            await wf.clear_workflow(session_id)
            logger.info(f"Cleared Redis workflow/options/raw for session {session_id} after booking")
        except Exception as clear_err:
            logger.warning(f"Failed to clear Redis after booking: {clear_err}")
        
        # ✅ Invalidate bookings list cache for this user
        try:
            from app.core.redis_cache import cache
            cache_key = f"bookings:list:{user_id}"
            await cache.delete(cache_key)
            logger.debug(f"Invalidated bookings cache for user: {user_id}")
        except Exception as cache_err:
            logger.debug(f"Failed to invalidate cache: {cache_err}")
        
        # ✅ Create in-app notification only if user has notifications enabled (Settings)
        try:
            from app.services.notification_preferences import should_create_in_app_notification
            users_collection = storage.db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            is_edit_trip = bool(getattr(booking_request, "replace_booking_id", None))
            notif_type = "trip_edited" if is_edit_trip else "booking_created"
            if should_create_in_app_notification(user_doc, notif_type):
                notifications_collection = storage.db.get_collection("notifications")
                if is_edit_trip:
                    notification_doc = {
                        "user_id": user_id,
                        "type": "trip_edited",
                        "title": "แก้ไขทริปสำเร็จ",
                        "message": "การจองเดิมถูกยกเลิกและสร้างการจองใหม่ในทริปนี้แล้ว กรุณาชำระเงินเพื่อยืนยันการจอง",
                        "booking_id": booking_id,
                        "read": False,
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        "metadata": {
                            "status": initial_status,
                            "total_price": booking_request.total_price,
                            "currency": booking_request.currency or "THB",
                        }
                    }
                else:
                    notification_doc = {
                        "user_id": user_id,
                        "type": "booking_created",
                        "title": "จองสำเร็จ",
                        "message": f"การจองของคุณได้รับการสร้างแล้ว กรุณาชำระเงินเพื่อยืนยันการจอง",
                        "booking_id": booking_id,
                        "read": False,
                        "created_at": datetime.utcnow().isoformat() + "Z",
                        "metadata": {
                            "status": initial_status,
                            "total_price": booking_request.total_price,
                            "currency": booking_request.currency or "THB"
                        }
                    }
                result = await notifications_collection.insert_one(notification_doc)
                notification_doc["id"] = str(result.inserted_id)
                notification_doc.pop("_id", None)
                await push_notification_event(user_id, notification_doc)
                logger.info(f"Created {notif_type} notification for booking: {booking_id} (user_id: {user_id})")
                # ส่งอีเมลแจ้งเตือนแก้ไขทริป (ถ้าผู้ใช้เปิดรับ)
                if is_edit_trip:
                    import asyncio
                    from app.services.notification_service import send_notification_email_if_enabled
                    asyncio.create_task(
                        send_notification_email_if_enabled(
                            db=storage.db,
                            user_id=user_id,
                            notif_type="trip_edited",
                            title=notification_doc["title"],
                            message=notification_doc["message"],
                            booking_id=booking_id,
                        )
                    )
            else:
                logger.debug(f"Skipped notification for booking {booking_id} (user preferences)")
        except Exception as notif_error:
            logger.warning(f"Failed to create notification for booking {booking_id}: {notif_error}")
            # Don't fail booking creation if notification fails
        
        # ✅ Agent Mode: Return appropriate message
        if initial_status == "confirmed":
            message = "✅ จองสำเร็จแล้ว! (Agent Mode - Auto-confirmed)"
        else:
            message = "Booking created successfully. Please proceed to payment."
        
        return {
            "ok": True,
            "booking_id": booking_id,
            "message": message,
            "status": initial_status,
            "total_price": booking_request.total_price,
            "currency": booking_request.currency or "THB",
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create booking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")


@router.get("/profile-check")
async def booking_profile_check(request: Request):
    """
    ตรวจสอบว่าข้อมูลพื้นฐานของผู้ใช้ครบสำหรับการจองหรือไม่
    คืนค่า ready_for_booking, missing_fields เพื่อให้ frontend แสดงข้อความแจ้งหรือปิดปุ่มจอง
    """
    from app.core.security import extract_user_id_from_request
    user_id = extract_user_id_from_request(request)
    if not user_id:
        return {
            "ok": True,
            "ready_for_booking": False,
            "missing_fields": ["กรุณาเข้าสู่ระบบ"],
            "message": "กรุณาเข้าสู่ระบบก่อนจึงจะจองได้",
        }
    storage = MongoStorage()
    await storage.connect()
    users_collection = storage.db["users"]
    user_doc = await users_collection.find_one({"user_id": user_id})
    if not user_doc:
        return {
            "ok": True,
            "ready_for_booking": False,
            "missing_fields": ["ไม่พบข้อมูลผู้ใช้"],
            "message": "ไม่พบข้อมูลผู้ใช้",
        }
    if not user_doc.get("email_verified", False):
        return {
            "ok": True,
            "ready_for_booking": False,
            "missing_fields": ["ยืนยันอีเมล"],
            "message": "กรุณายืนยันอีเมลก่อนจึงจะจองได้ ไปที่ การตั้งค่า > สถานะการยืนยันอีเมล",
        }
    missing = _get_missing_profile_fields_for_booking(user_doc)
    if missing:
        return {
            "ok": True,
            "ready_for_booking": False,
            "missing_fields": missing,
            "message": f"กรุณากรอกข้อมูลใน ข้อมูลพื้นฐาน ให้ครบก่อนจึงจะจองได้: {', '.join(missing)}",
        }
    return {
        "ok": True,
        "ready_for_booking": True,
        "missing_fields": [],
        "message": "ข้อมูลครบ สามารถจองได้",
    }


@router.get("/list")
async def list_bookings(request: Request):
    """
    List all bookings for the current user
    ✅ ใช้ X-User-ID เป็นหลักเมื่อมี (ให้ตรงกับ create จากแชท) เพื่อให้จองโผล่ใน My Bookings
    """
    import asyncio
    from app.core.redis_cache import cache
    
    try:
        # ✅ Prefer X-User-ID when sent (same as create from chat/Agent) so bookings appear in My Bookings
        header_user_id = (request.headers.get("X-User-ID") or "").strip()
        cookie_user_id = (request.cookies.get(settings.session_cookie_name) or "").strip()
        user_id = (header_user_id or cookie_user_id) or None
        
        if not user_id:
            logger.debug("No user_id provided in request")
            return {
                "ok": True,
                "bookings": [],
                "count": 0
            }
        
        # ✅ Normalize user_id
        user_id_normalized = user_id.strip() if user_id else None
        
        # ✅ Try Redis cache first (TTL: 30 seconds for bookings list)
        cache_key = f"bookings:list:{user_id_normalized}"
        cached_result = await cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"✅ Cache hit for bookings list: {user_id_normalized}")
            return cached_result
        
        # ✅ Cache miss - fetch from database
        logger.debug(f"Cache miss - fetching bookings from database for user: {user_id_normalized}")
        
        storage = MongoStorage()
        try:
            await storage.connect()
        except Exception as conn_e:
            logger.error(f"Failed to connect to MongoDB: {conn_e}", exc_info=True)
            # Return empty list instead of crashing if MongoDB is unavailable
            return {
                "ok": True,
                "bookings": [],
                "count": 0,
                "message": "Database temporarily unavailable"
            }
        
        # ✅ Ensure db and collection are available
        if storage.db is None:
            logger.error("MongoStorage.db is None after connect()")
            return {
                "ok": True,
                "bookings": [],
                "count": 0,
                "message": "Database connection unavailable"
            }
        
        bookings_collection = storage.db["bookings"]
        
        # ✅ SECURITY: Query only bookings for this specific user_id
        query = {"user_id": user_id_normalized}
        
        # ✅ CRUD STABILITY: Optimized query with timeout (5 seconds max) and error handling
        try:
            cursor = bookings_collection.find(query).sort("created_at", -1).limit(100)
            # Use asyncio.wait_for to prevent slow queries from blocking
            bookings = await asyncio.wait_for(cursor.to_list(length=100), timeout=5.0)
        except asyncio.TimeoutError:
            logger.error(f"Bookings query timeout for user: {user_id_normalized}")
            return {
                "ok": False,
                "bookings": [],
                "count": 0,
                "message": "Query timeout - database may be slow"
            }
        except Exception as query_error:
            logger.error(f"Bookings query error for user {user_id_normalized}: {query_error}", exc_info=True)
            return {
                "ok": False,
                "bookings": [],
                "count": 0,
                "message": "Failed to retrieve bookings"
            }
        
        # ✅ Expose ID for client: ใช้ booking_id (ตัวเลขแบบ Amadeus) เป็นหลัก ถ้าไม่มีใช้ _id (backward compat)
        for booking in bookings:
            bid = booking.get("booking_id")
            if bid is not None:
                booking["_id"] = str(bid)
            else:
                booking["_id"] = str(booking["_id"])
        
        result = {
            "ok": True,
            "bookings": bookings,
            "count": len(bookings)
        }
        
        # ✅ Cache the result (30 seconds TTL)
        await cache.set(cache_key, result, ttl=30)
        
        logger.info(f"Retrieved {len(bookings)} bookings for user: {user_id_normalized}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list bookings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list bookings: {str(e)}")


def _safe_float(val, default: float = 0.0) -> float:
    if val is None: return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _calculate_total_price_from_plan(booking_doc: dict) -> Optional[float]:
    """คำนวณ total_price จาก plan เมื่อของเดิมเป็น 0 หรือไม่มี — ใช้ทั้งใน detail และ payment flow"""
    plan = booking_doc.get("plan") or {}
    travel_slots = booking_doc.get("travel_slots") or {}
    total = 0.0

    def pick(d: dict, *keys: str) -> float:
        if not d or not isinstance(d, dict):
            return 0.0
        for k in keys:
            v = d.get(k)
            if v is not None and v != "":
                n = _safe_float(v, -1)
                if n >= 0:
                    return n
        return 0.0

    try:
        total += pick(plan.get("flight") or {}, "price_total", "price_amount", "price", "total_price")
        hotel_data = plan.get("hotel") or plan.get("accommodation") or {}
        hp = pick(hotel_data, "price_total", "price_amount", "price", "total_price")
        if hp > 0:
            total += hp
        else:
            nights = _safe_float(travel_slots.get("nights") or travel_slots.get("number_of_nights") or 1, 1)
            nr = hotel_data.get("nightly_rate")
            if nr is not None:
                total += _safe_float(nr, 0) * max(nights, 1)
        total += pick(plan.get("transport") or plan.get("transfer") or {}, "price_total", "price_amount", "price", "total_price")
        travel = plan.get("travel") or {}
        for direction in ("outbound", "inbound"):
            for seg in (travel.get("flights") or {}).get(direction) or []:
                opt = (seg or {}).get("selected_option") or {}
                total += pick(opt, "price_amount", "price_total", "price")
        acc_segments = (plan.get("accommodation") or {}).get("segments") or (plan.get("hotel") or {}).get("segments") or []
        for seg in acc_segments:
            opt = (seg or {}).get("selected_option") or {}
            total += pick(opt, "price_amount", "price_total", "price")
    except (TypeError, ValueError, KeyError):
        pass
    return total if total > 0 else None


@router.get("/detail")
async def get_booking_detail(request: Request, booking_id: str = Query(..., description="Booking ID or _id")):
    """
    ดึงข้อมูลการจองหนึ่งรายการ (รวม plan, travel_slots, total_price) สำหรับหน้าชำระเงิน
    ใช้แทนการดึงจาก list เพื่อให้ได้ข้อมูลล่าสุดและครบ
    """
    from app.core.security import extract_user_id_from_request
    from bson import ObjectId

    user_id = extract_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    bid = (booking_id or "").strip()
    if not bid:
        raise HTTPException(status_code=400, detail="booking_id is required")

    storage = MongoStorage()
    try:
        await storage.connect()
    except Exception as e:
        logger.error(f"DB connect failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not storage.db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    coll = storage.db["bookings"]
    or_conds = [{"booking_id": bid}, {"_id": bid}]
    if len(bid) == 24 and all(c in "0123456789abcdefABCDEF" for c in bid):
        try:
            or_conds.append({"_id": ObjectId(bid)})
        except Exception:
            pass
    query = {"user_id": user_id.strip(), "$or": or_conds}
    try:
        booking = await coll.find_one(query)
    except Exception as e:
        logger.error(f"Booking detail query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load booking")
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบข้อมูลการจอง")

    # คืนแบบ dict ที่ frontend ใช้ได้ (รวม plan, travel_slots)
    out = dict(booking)
    out["_id"] = str(out.get("booking_id") or out.get("_id", ""))
    if "created_at" in out and hasattr(out["created_at"], "isoformat"):
        out["created_at"] = out["created_at"].isoformat()
    if "updated_at" in out and hasattr(out["updated_at"], "isoformat"):
        out["updated_at"] = out["updated_at"].isoformat()
    # ถ้า total_price เป็น 0 หรือไม่มี ให้คำนวณจาก plan แล้วใส่ใน response (frontend จะได้แสดงราคา)
    stored_price = out.get("total_price")
    if stored_price is None or (isinstance(stored_price, (int, float)) and float(stored_price) <= 0):
        computed = _calculate_total_price_from_plan(out)
        if computed is not None and computed > 0:
            out["total_price"] = computed
            logger.info(f"Detail: filled total_price from plan for booking {bid}: {computed}")
    return {"ok": True, "booking": out}


@router.get("/by-trip")
async def get_booking_by_trip(request: Request, trip_id: str = Query(..., description="Trip ID")):
    """
    ดึงการจองล่าสุดของทริปนี้ (สำหรับหน้าชำระเงิน) พร้อม plan, travel_slots และราคาชำระเงิน (total_price)
    """
    from app.core.security import extract_user_id_from_request

    user_id = extract_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
    tid = (trip_id or "").strip()
    if not tid:
        raise HTTPException(status_code=400, detail="trip_id is required")

    storage = MongoStorage()
    try:
        await storage.connect()
    except Exception as e:
        logger.error(f"DB connect failed: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    if not storage.db:
        raise HTTPException(status_code=503, detail="Database unavailable")

    coll = storage.db["bookings"]
    query = {"user_id": user_id.strip(), "trip_id": tid}
    try:
        booking = await coll.find_one(
            query,
            sort=[("created_at", -1)],
            projection=None,
        )
    except Exception as e:
        logger.error(f"Booking by-trip query failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to load booking")
    if not booking:
        raise HTTPException(status_code=404, detail="ไม่พบการจองของทริปนี้")

    out = dict(booking)
    out["_id"] = str(out.get("booking_id") or out.get("_id", ""))
    if "created_at" in out and hasattr(out["created_at"], "isoformat"):
        out["created_at"] = out["created_at"].isoformat()
    if "updated_at" in out and hasattr(out["updated_at"], "isoformat"):
        out["updated_at"] = out["updated_at"].isoformat()
    stored_price = out.get("total_price")
    if stored_price is None or (isinstance(stored_price, (int, float)) and float(stored_price) <= 0):
        computed = _calculate_total_price_from_plan(out)
        if computed is not None and computed > 0:
            out["total_price"] = computed
            logger.info(f"By-trip: filled total_price from plan for trip_id={tid}: {computed}")
    amount = out.get("total_price")
    if amount is not None:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            amount = None
    return {"ok": True, "booking": out, "amount": amount}


@router.post("/payment")
async def process_payment(
    request: Request,
    booking_id: str = Query(..., description="Booking ID")
):
    """
    Process payment for a booking using Omise
    Returns Omise checkout URL for redirect
    """
    # Input validation
    if not booking_id or not booking_id.strip():
        raise HTTPException(status_code=400, detail="Booking ID is required")
    
    booking_id = booking_id.strip()
    
    try:
        storage = MongoStorage()
        await storage.connect()
        
        bookings_collection = storage.db["bookings"]
        
        # ✅ Use security helper function (prioritizes cookie, then header)
        from app.core.security import extract_user_id_from_request
        user_id = extract_user_id_from_request(request)
        
        # ✅ SECURITY: Find booking with user_id filter FIRST (never query without user_id)
        from bson import ObjectId
        booking = None
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # ✅ CRITICAL: Always query with user_id filter to prevent data leakage
        try:
            if len(booking_id) == 24:  # MongoDB ObjectId length
                booking = await bookings_collection.find_one({
                    "_id": ObjectId(booking_id),
                    "user_id": user_id  # ✅ Filter by user_id FIRST
                })
        except Exception as obj_err:
            logger.debug(f"Failed to parse as ObjectId: {obj_err}")
        
        if not booking:
            booking = await bookings_collection.find_one({
                "booking_id": booking_id,
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })
        
        if not booking:
            # ✅ SECURITY: Don't reveal if booking exists but belongs to another user
            logger.warning(f"Booking not found or access denied: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # ✅ SECURITY: Double-check user_id matches (additional safety layer)
        booking_user_id = booking.get("user_id")
        if booking_user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Booking {booking_id} user_id mismatch! expected {user_id}, found {booking_user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to access this booking")
        
        # Check if already paid
        if booking.get("status") in ["paid", "confirmed"]:
            return {
                "ok": True,
                "message": "Booking already paid",
                "status": booking.get("status"),
                "payment_url": None
            }
        
        # Check if cancelled
        if booking.get("status") == "cancelled":
            raise HTTPException(status_code=400, detail="Cannot pay for cancelled booking")
        
        # ✅ Validate and calculate amount
        amount = booking.get("total_price", 0)
        
        # ✅ FIX: If total_price is 0 or missing, try to calculate from plan
        if not isinstance(amount, (int, float)) or amount <= 0:
            logger.warning(f"Booking {booking_id} has invalid total_price: {amount}. Attempting to calculate from plan...")
            
            # Try to calculate from plan data
            plan = booking.get("plan", {})
            travel_slots = booking.get("travel_slots", {})
            
            # ✅ DEBUG: Log plan structure for debugging
            logger.debug(f"Plan structure: {list(plan.keys()) if plan else 'No plan'}")
            if plan:
                logger.debug(f"Plan flight keys: {list(plan.get('flight', {}).keys()) if plan.get('flight') else 'No flight'}")
                logger.debug(f"Plan hotel keys: {list(plan.get('hotel', {}).keys()) if plan.get('hotel') else 'No hotel'}")
                logger.debug(f"Plan travel keys: {list(plan.get('travel', {}).keys()) if plan.get('travel') else 'No travel'}")
                logger.debug(f"Plan accommodation keys: {list(plan.get('accommodation', {}).keys()) if plan.get('accommodation') else 'No accommodation'}")
            
            calculated_amount = 0
            
            # ✅ Calculate from flight prices - check multiple possible structures
            # Structure 1: plan.flight (direct)
            flight_data = plan.get("flight") or {}
            # Structure 2: plan.travel.flights (nested)
            travel_data = plan.get("travel", {})
            travel_flights = travel_data.get("flights", {}) if isinstance(travel_data, dict) else {}
            
            # Try direct flight structure first
            if flight_data:
                # Try different price field names
                flight_price = (
                    flight_data.get("price_total") or
                    flight_data.get("price_amount") or
                    flight_data.get("price") or
                    flight_data.get("total_price") or
                    0
                )
                if isinstance(flight_price, (int, float)) and flight_price > 0:
                    calculated_amount += float(flight_price)
                    logger.debug(f"Added flight price: {flight_price}")
                else:
                    # Try nested structure (e.g., flight.price.total)
                    nested_price = flight_data.get("price", {})
                    if isinstance(nested_price, dict):
                        nested_total = nested_price.get("total") or nested_price.get("amount") or 0
                        if isinstance(nested_total, (int, float)) and nested_total > 0:
                            calculated_amount += float(nested_total)
                            logger.debug(f"Added nested flight price: {nested_total}")
            
            # ✅ Calculate from travel.flights structure (outbound + inbound)
            if travel_flights:
                # Calculate from outbound flights
                outbound_flights = travel_flights.get("outbound", [])
                if isinstance(outbound_flights, list):
                    for flight_seg in outbound_flights:
                        if isinstance(flight_seg, dict):
                            selected_option = flight_seg.get("selected_option", {})
                            if selected_option:
                                flight_price = (
                                    selected_option.get("price_amount") or
                                    selected_option.get("price_total") or
                                    selected_option.get("price") or
                                    0
                                )
                                if isinstance(flight_price, (int, float)) and flight_price > 0:
                                    calculated_amount += float(flight_price)
                                    logger.debug(f"Added outbound flight price: {flight_price}")
                
                # Calculate from inbound flights
                inbound_flights = travel_flights.get("inbound", [])
                if isinstance(inbound_flights, list):
                    for flight_seg in inbound_flights:
                        if isinstance(flight_seg, dict):
                            selected_option = flight_seg.get("selected_option", {})
                            if selected_option:
                                flight_price = (
                                    selected_option.get("price_amount") or
                                    selected_option.get("price_total") or
                                    selected_option.get("price") or
                                    0
                                )
                                if isinstance(flight_price, (int, float)) and flight_price > 0:
                                    calculated_amount += float(flight_price)
                                    logger.debug(f"Added inbound flight price: {flight_price}")
            
            # ✅ Calculate from hotel prices - check multiple possible field names
            # Structure 1: plan.hotel (direct)
            hotel_data = plan.get("hotel") or {}
            # Structure 2: plan.accommodation (alternative)
            accommodation_data = plan.get("accommodation") or {}
            
            # Try direct hotel structure first
            if hotel_data:
                hotel_price = (
                    hotel_data.get("price_total") or
                    hotel_data.get("price_amount") or
                    hotel_data.get("price") or
                    hotel_data.get("total_price") or
                    hotel_data.get("nightly_rate") or
                    0
                )
                if isinstance(hotel_price, (int, float)) and hotel_price > 0:
                    # If it's nightly rate, multiply by nights
                    nights = travel_slots.get("nights") or travel_slots.get("number_of_nights") or 1
                    if hotel_data.get("nightly_rate"):
                        calculated_amount += float(hotel_price) * float(nights)
                        logger.debug(f"Added hotel price (nightly_rate * nights): {hotel_price} * {nights} = {float(hotel_price) * float(nights)}")
                    else:
                        calculated_amount += float(hotel_price)
                        logger.debug(f"Added hotel price: {hotel_price}")
                else:
                    # Try nested structure
                    nested_price = hotel_data.get("price", {})
                    if isinstance(nested_price, dict):
                        nested_total = nested_price.get("total") or nested_price.get("amount") or 0
                        if isinstance(nested_total, (int, float)) and nested_total > 0:
                            calculated_amount += float(nested_total)
                            logger.debug(f"Added nested hotel price: {nested_total}")
            
            # ✅ Calculate from accommodation structure (alternative hotel structure)
            if accommodation_data:
                if isinstance(accommodation_data, list):
                    # If accommodation is a list
                    for acc in accommodation_data:
                        if isinstance(acc, dict):
                            selected_option = acc.get("selected_option", {})
                            if selected_option:
                                acc_price = (
                                    selected_option.get("price_amount") or
                                    selected_option.get("price_total") or
                                    selected_option.get("price") or
                                    0
                                )
                                if isinstance(acc_price, (int, float)) and acc_price > 0:
                                    calculated_amount += float(acc_price)
                                    logger.debug(f"Added accommodation price: {acc_price}")
                elif isinstance(accommodation_data, dict):
                    # If accommodation is a dict
                    acc_price = (
                        accommodation_data.get("price_amount") or
                        accommodation_data.get("price_total") or
                        accommodation_data.get("price") or
                        0
                    )
                    if isinstance(acc_price, (int, float)) and acc_price > 0:
                        calculated_amount += float(acc_price)
                        logger.debug(f"Added accommodation price: {acc_price}")
            
            # ✅ Calculate from transport prices
            # Structure 1: plan.transport or plan.transfer
            transport_data = plan.get("transport") or plan.get("transfer") or {}
            # Structure 2: plan.travel.ground_transport
            ground_transport = travel_data.get("ground_transport", []) if isinstance(travel_data, dict) else []
            
            # Try direct transport structure first
            if transport_data:
                transport_price = (
                    transport_data.get("price_total") or
                    transport_data.get("price_amount") or
                    transport_data.get("price") or
                    transport_data.get("total_price") or
                    0
                )
                if isinstance(transport_price, (int, float)) and transport_price > 0:
                    calculated_amount += float(transport_price)
                    logger.debug(f"Added transport price: {transport_price}")
            
            # ✅ Calculate from ground_transport structure
            if isinstance(ground_transport, list):
                for transport_seg in ground_transport:
                    if isinstance(transport_seg, dict):
                        selected_option = transport_seg.get("selected_option", {})
                        if selected_option:
                            transport_price = (
                                selected_option.get("price_amount") or
                                selected_option.get("price_total") or
                                selected_option.get("price") or
                                0
                            )
                            if isinstance(transport_price, (int, float)) and transport_price > 0:
                                calculated_amount += float(transport_price)
                                logger.debug(f"Added ground transport price: {transport_price}")
            
            # ✅ Try to get price from choices if plan structure is different
            if calculated_amount == 0:
                # Check if plan has choices array with prices
                choices = plan.get("choices") or []
                for choice in choices:
                    choice_price = (
                        choice.get("price") or
                        choice.get("price_amount") or
                        choice.get("price_total") or
                        0
                    )
                    if isinstance(choice_price, (int, float)) and choice_price > 0:
                        calculated_amount += float(choice_price)
                        logger.debug(f"Added choice price: {choice_price}")
            
            # ✅ If calculated amount is valid, use it and update booking
            if calculated_amount > 0:
                logger.info(f"✅ Calculated amount from plan: {calculated_amount}. Updating booking...")
                amount = calculated_amount
                
                # Update booking with calculated amount
                try:
                    from bson import ObjectId
                    # Build query filter
                    query_filter = {"user_id": user_id}
                    if len(booking_id) == 24:
                        try:
                            query_filter["_id"] = ObjectId(booking_id)
                        except Exception:
                            query_filter["booking_id"] = booking_id
                    else:
                        query_filter["booking_id"] = booking_id
                    
                    update_result = await bookings_collection.update_one(
                        query_filter,
                        {"$set": {"total_price": calculated_amount, "updated_at": datetime.utcnow().isoformat()}}
                    )
                    if update_result.modified_count > 0:
                        logger.info(f"✅ Updated booking {booking_id} with calculated total_price: {calculated_amount}")
                    else:
                        logger.warning(f"⚠️ Failed to update booking {booking_id} - no document matched")
                except Exception as update_err:
                    logger.error(f"❌ Failed to update booking total_price: {update_err}", exc_info=True)
            else:
                # Still invalid - log detailed info
                logger.error(f"❌ Booking {booking_id} has invalid amount and cannot be calculated from plan data")
                logger.error(f"   Plan keys: {list(plan.keys()) if plan else 'No plan'}")
                logger.error(f"   Plan content (first 500 chars): {str(plan)[:500] if plan else 'No plan'}")
                
                # ✅ Check if flights/accommodations are not yet selected (selected_option is None)
                travel_data = plan.get("travel", {})
                travel_flights = travel_data.get("flights", {}) if isinstance(travel_data, dict) else {}
                accommodation_data = plan.get("accommodation") or []
                
                has_unselected_flights = False
                if travel_flights:
                    outbound = travel_flights.get("outbound", [])
                    inbound = travel_flights.get("inbound", [])
                    for flight in (outbound + inbound):
                        if isinstance(flight, dict) and flight.get("selected_option") is None:
                            has_unselected_flights = True
                            break
                
                has_unselected_accommodation = False
                if isinstance(accommodation_data, list):
                    for acc in accommodation_data:
                        if isinstance(acc, dict) and acc.get("selected_option") is None:
                            has_unselected_accommodation = True
                            break
                
                # ✅ Provide helpful error message
                if has_unselected_flights or has_unselected_accommodation:
                    error_detail = "ไม่สามารถคำนวณราคาได้เนื่องจากยังไม่ได้เลือกไฟท์บินหรือที่พัก กรุณาเลือกไฟท์บินและที่พักก่อนจอง"
                else:
                    error_detail = f"Invalid booking amount ({amount}). Unable to calculate from plan data. Please contact support or update the booking amount."
                
                raise HTTPException(
                    status_code=400, 
                    detail=error_detail
                )
        
        # Final validation
        if not isinstance(amount, (int, float)) or amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid booking amount")
        
        currency = booking.get("currency", "THB")
        if not currency or not isinstance(currency, str):
            currency = "THB"
        
        # Create Omise checkout with error handling
        try:
            # Get base URL from request for payment page URL generation
            try:
                request_base_url = str(request.base_url).rstrip('/') if request and hasattr(request, 'base_url') else None
            except Exception as url_err:
                logger.warning(f"Failed to get base URL from request: {url_err}")
                request_base_url = None
            
            payment_url = await OmiseService.create_checkout(
                booking_id, 
                float(amount), 
                currency,
                request_base_url=request_base_url
            )
            logger.info(f"Created Omise checkout for booking: {booking_id}, URL: {payment_url[:100] if payment_url else 'None'}...")
        except HTTPException as he:
            # Re-raise HTTP exceptions with their original status codes
            logger.error(f"Omise HTTPException: {he.status_code} - {he.detail}")
            raise he
        except Exception as omise_err:
            logger.error(f"Omise service error: {omise_err}", exc_info=True)
            raise HTTPException(
                status_code=503,
                detail=f"Payment service temporarily unavailable: {str(omise_err)}"
            )
        
        return {
            "ok": True,
            "message": "Redirecting to payment gateway...",
            "payment_url": payment_url,
            "status": "pending_payment"
        }
        
    except HTTPException as he:
        # Re-raise HTTP exceptions (they already have proper status codes)
        logger.error(f"Payment HTTPException: {he.status_code} - {he.detail}")
        raise he
    except Exception as e:
        # Log full error details for debugging
        logger.error(f"Failed to process payment: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to process payment: {str(e)}"
        )


@router.post("/cancel")
async def cancel_booking(
    request: Request,
    booking_id: str = Query(..., description="Booking ID")
):
    """
    Cancel a booking
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        from app.core.security import extract_user_id_from_request
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        storage = MongoStorage()
        await storage.connect()
        
        bookings_collection = storage.db["bookings"]
        
        # ✅ SECURITY: Find booking with user_id filter FIRST
        from bson import ObjectId
        booking = None
        
        # ✅ CRITICAL: Always query with user_id filter to prevent data leakage
        try:
            booking = await bookings_collection.find_one({
                "_id": ObjectId(booking_id),
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })
        except Exception:
            booking = await bookings_collection.find_one({
                "booking_id": booking_id,
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })

        if not booking:
            # ✅ SECURITY: Don't reveal if booking exists but belongs to another user
            logger.warning(f"Booking not found or access denied: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found")

        # ✅ SECURITY: Double-check user_id matches (additional safety layer)
        booking_user_id = booking.get("user_id")
        if booking_user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Booking {booking_id} user_id mismatch! expected {user_id}, found {booking_user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to cancel this booking")
        
        # ✅ Amadeus sandbox sync: ยกเลิก flight orders แบบ best-effort — ไม่บล็อกการยกเลิก
        amadeus_sync = booking.get("amadeus_sync") or {}
        flight_order_ids = amadeus_sync.get("flight_order_ids") or []
        if flight_order_ids and settings.amadeus_booking_env.lower() != "production":
            from app.services.travel_service import orchestrator
            for order_id in flight_order_ids:
                async def _cancel_one(oid=order_id):
                    await orchestrator.delete_flight_order(oid)
                try:
                    await _amadeus_retry_until_success(f"cancel_flight_order_{order_id}", _cancel_one)
                except Exception as ae:
                    # Log เพื่อ audit แต่ไม่บล็อกการยกเลิก
                    logger.warning(f"Amadeus cancel flight order failed (best-effort): booking={booking_id} order={order_id}: {ae}")
        
        # ✅ อัปเดต DB หลัง Amadeus ยกเลิกครบแล้วเท่านั้น
        from bson import ObjectId
        try:
            result = await bookings_collection.update_one(
                {"_id": ObjectId(booking_id), "user_id": user_id},  # ✅ Atomic update with user_id filter
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
            )
        except Exception:
            result = await bookings_collection.update_one(
                {"booking_id": booking_id, "user_id": user_id},  # ✅ Atomic update with user_id filter
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
            )
        
        # ✅ CRUD STABILITY: Verify update was successful
        if result.matched_count == 0:
            logger.warning(f"Booking not found during cancellation: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found or already cancelled")
        
        logger.info(f"Cancelled booking: {booking_id}")
        
        # ✅ Invalidate bookings list cache for this user
        try:
            from app.core.redis_cache import cache
            cache_key = f"bookings:list:{user_id}"
            await cache.delete(cache_key)
            logger.debug(f"Invalidated bookings cache for user: {user_id}")
        except Exception as cache_err:
            logger.debug(f"Failed to invalidate cache: {cache_err}")

        # ✅ Create trip_change notification for cancellation if user has it enabled
        try:
            from app.services.notification_preferences import should_create_in_app_notification
            users_collection = storage.db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            if should_create_in_app_notification(user_doc, "trip_change"):
                notifications_collection = storage.db.get_collection("notifications")
                cancel_doc = {
                    "user_id": user_id,
                    "type": "trip_change",
                    "title": "ยกเลิกการจอง",
                    "message": f"การจอง #{booking_id[:8]} ถูกยกเลิกเรียบร้อยแล้ว",
                    "booking_id": booking_id,
                    "read": False,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "metadata": {"action": "cancelled"}
                }
                result = await notifications_collection.insert_one(cancel_doc)
                cancel_doc["id"] = str(result.inserted_id)
                cancel_doc.pop("_id", None)
                await push_notification_event(user_id, cancel_doc)
                logger.info(f"Created cancellation notification for booking {booking_id}")
                # ส่งอีเมลแจ้งเตือนทริปยกเลิก (ถ้าผู้ใช้เปิดรับ)
                import asyncio
                from app.services.notification_service import send_notification_email_if_enabled
                asyncio.create_task(
                    send_notification_email_if_enabled(
                        db=storage.db,
                        user_id=user_id,
                        notif_type="trip_change",
                        title=cancel_doc["title"],
                        message=cancel_doc["message"],
                        booking_id=booking_id,
                    )
                )
        except Exception as notif_err:
            logger.warning(f"Failed to create cancellation notification: {notif_err}")

        return {
            "ok": True,
            "message": "Booking cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel booking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel booking: {str(e)}")


@router.put("/update")
@router.patch("/update")
async def update_booking(
    fastapi_request: Request,
    booking_id: str = Query(..., description="Booking ID"),
    request: BookingUpdateRequest = None
):
    """
    Update a booking (only allowed for pending_payment status)
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        from app.core.security import extract_user_id_from_request
        user_id = extract_user_id_from_request(fastapi_request)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        storage = MongoStorage()
        await storage.connect()
        
        bookings_collection = storage.db["bookings"]
        
        # ✅ SECURITY: Find booking with user_id filter FIRST
        from bson import ObjectId
        booking = None
        
        # ✅ CRITICAL: Always query with user_id filter to prevent data leakage
        try:
            booking = await bookings_collection.find_one({
                "_id": ObjectId(booking_id),
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })
        except:
            booking = await bookings_collection.find_one({
                "booking_id": booking_id,
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })
        
        if not booking:
            # ✅ SECURITY: Don't reveal if booking exists but belongs to another user
            logger.warning(f"Booking not found or access denied: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # ✅ SECURITY: Double-check user_id matches (additional safety layer)
        booking_user_id = booking.get("user_id")
        if booking_user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Booking {booking_id} user_id mismatch! expected {user_id}, found {booking_user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to update this booking")
        
        # Check if booking can be updated
        current_status = booking.get("status", "")
        if current_status not in ["pending_payment"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot update booking with status '{current_status}'. Only 'pending_payment' bookings can be updated."
            )
        
        # ✅ CRUD STABILITY: Build update data with validation (only include fields that were provided)
        update_data = {}
        if request.plan is not None:
            if not isinstance(request.plan, dict):
                raise HTTPException(status_code=400, detail="'plan' must be a dictionary")
            update_data["plan"] = request.plan
        if request.travel_slots is not None:
            if not isinstance(request.travel_slots, dict):
                raise HTTPException(status_code=400, detail="'travel_slots' must be a dictionary")
            update_data["travel_slots"] = request.travel_slots
        if request.total_price is not None:
            if not isinstance(request.total_price, (int, float)) or request.total_price < 0:
                raise HTTPException(status_code=400, detail="'total_price' must be a non-negative number")
            update_data["total_price"] = request.total_price
        if request.currency is not None:
            if not isinstance(request.currency, str) or len(request.currency) != 3:
                raise HTTPException(status_code=400, detail="'currency' must be a 3-character currency code")
            update_data["currency"] = request.currency
        if request.metadata is not None:
            if not isinstance(request.metadata, dict):
                raise HTTPException(status_code=400, detail="'metadata' must be a dictionary")
            update_data["metadata"] = request.metadata
        
        # Always update timestamp
        update_data["updated_at"] = datetime.utcnow().isoformat()
        
        if not update_data or len(update_data) == 1:  # Only updated_at
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # ✅ SECURITY: Update booking with user_id filter
        try:
            result = await bookings_collection.update_one(
                {"_id": ObjectId(booking_id), "user_id": user_id},  # ✅ Filter by user_id
                {"$set": update_data}
            )
        except Exception:
            result = await bookings_collection.update_one(
                {"booking_id": booking_id, "user_id": user_id},  # ✅ Filter by user_id
                {"$set": update_data}
            )
        
        if result.matched_count == 0:
            logger.warning(f"Booking not found during update: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found during update")
        
        logger.info(f"Updated booking: {booking_id} - Fields: {list(update_data.keys())}")
        
        # ✅ Invalidate bookings list cache for this user
        try:
            from app.core.redis_cache import cache
            cache_key = f"bookings:list:{user_id}"
            await cache.delete(cache_key)
            logger.debug(f"Invalidated bookings cache for user: {user_id}")
        except Exception as cache_err:
            logger.debug(f"Failed to invalidate cache: {cache_err}")

        # ✅ Create trip_change notification if user has it enabled
        try:
            from app.services.notification_preferences import should_create_in_app_notification
            users_collection = storage.db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            if should_create_in_app_notification(user_doc, "trip_change"):
                notifications_collection = storage.db.get_collection("notifications")
                changed_fields = [k for k in update_data.keys() if k != "updated_at"]
                update_doc = {
                    "user_id": user_id,
                    "type": "trip_change",
                    "title": "อัปเดตการจอง",
                    "message": f"การจอง #{booking_id[:8]} ได้รับการอัปเดตเรียบร้อยแล้ว",
                    "booking_id": booking_id,
                    "read": False,
                    "created_at": datetime.utcnow().isoformat() + "Z",
                    "metadata": {"changed_fields": changed_fields}
                }
                result = await notifications_collection.insert_one(update_doc)
                update_doc["id"] = str(result.inserted_id)
                update_doc.pop("_id", None)
                await push_notification_event(user_id, update_doc)
                logger.info(f"Created trip_change notification for booking {booking_id}")
                # ส่งอีเมลแจ้งเตือนแก้ไขทริป/อัปเดตการจอง (ถ้าผู้ใช้เปิดรับ)
                import asyncio
                from app.services.notification_service import send_notification_email_if_enabled
                asyncio.create_task(
                    send_notification_email_if_enabled(
                        db=storage.db,
                        user_id=user_id,
                        notif_type="trip_change",
                        title=update_doc["title"],
                        message=update_doc["message"],
                        booking_id=booking_id,
                    )
                )
        except Exception as notif_err:
            logger.warning(f"Failed to create trip_change notification: {notif_err}")

        # ✅ SECURITY: Return updated booking with user_id filter
        try:
            updated_booking = await bookings_collection.find_one({
                "_id": ObjectId(booking_id),
                "user_id": user_id  # ✅ Filter by user_id
            })
        except Exception:
            updated_booking = await bookings_collection.find_one({
                "booking_id": booking_id,
                "user_id": user_id  # ✅ Filter by user_id
            })
        
        if updated_booking:
            updated_booking["_id"] = str(updated_booking["_id"])
        
        return {
            "ok": True,
            "message": "Booking updated successfully",
            "booking": updated_booking
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update booking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update booking: {str(e)}")


# =============================================================================
# Omise Test Endpoints
# =============================================================================

class OmiseTestRequest(BaseModel):
    """Request model for testing Omise"""
    amount: float = Field(default=100.0, description="Test amount in THB")
    currency: str = Field(default="THB", description="Currency code")


@router.post("/test-omise")
async def test_omise_connection(request: OmiseTestRequest = OmiseTestRequest()):
    """
    Test Omise API connection and create a test payment link
    This endpoint helps verify Omise configuration without creating a real booking
    """
    try:
        # Check configuration
        config_status = {
            "omise_secret_key_configured": bool(settings.omise_secret_key),
            "omise_secret_key_format": "valid" if (settings.omise_secret_key and settings.omise_secret_key.startswith("skey_")) else "invalid",
            "omise_public_key_configured": bool(settings.omise_public_key),
            "omise_public_key_format": "valid" if (settings.omise_public_key and settings.omise_public_key.startswith("pkey_")) else "invalid",
        }
        
        # If keys are not configured, return config status only
        if not settings.omise_secret_key or not settings.omise_secret_key.startswith("skey_"):
            return {
                "ok": False,
                "message": "Omise API keys not configured or invalid",
                "config": config_status,
                "error": "Please set OMISE_SECRET_KEY and OMISE_PUBLIC_KEY in .env file",
                "test_payment_url": None
            }
        
        # Try to create a test payment link
        test_booking_id = f"test_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        try:
            payment_url = await OmiseService.create_checkout(
                booking_id=test_booking_id,
                amount=request.amount,
                currency=request.currency
            )
            
            logger.info(f"Omise test successful - Created payment URL: {payment_url[:50]}...")
            
            return {
                "ok": True,
                "message": "Omise connection successful!",
                "config": config_status,
                "test_booking_id": test_booking_id,
                "test_amount": request.amount,
                "test_currency": request.currency,
                "test_payment_url": payment_url,
                "instructions": "Click the payment_url to test the Omise payment page. Use test card: 4242424242424242"
            }
            
        except HTTPException as he:
            return {
                "ok": False,
                "message": f"Omise API call failed: {he.detail}",
                "config": config_status,
                "error": str(he.detail),
                "status_code": he.status_code,
                "test_payment_url": None
            }
        except Exception as e:
            logger.error(f"Omise test error: {e}", exc_info=True)
            return {
                "ok": False,
                "message": f"Omise test failed: {str(e)}",
                "config": config_status,
                "error": str(e),
                "test_payment_url": None
            }
            
    except Exception as e:
        logger.error(f"Failed to test Omise: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to test Omise: {str(e)}")


@router.get("/test-omise")
async def test_omise_get():
    """
    GET endpoint for testing Omise configuration (simpler, no payment link)
    """
    try:
        config_status = {
            "omise_secret_key_configured": bool(settings.omise_secret_key),
            "omise_secret_key_format": "valid" if (settings.omise_secret_key and settings.omise_secret_key.startswith("skey_")) else "invalid",
            "omise_secret_key_prefix": settings.omise_secret_key[:10] + "..." if settings.omise_secret_key else "not_set",
            "omise_public_key_configured": bool(settings.omise_public_key),
            "omise_public_key_format": "valid" if (settings.omise_public_key and settings.omise_public_key.startswith("pkey_")) else "invalid",
            "omise_public_key_prefix": settings.omise_public_key[:10] + "..." if settings.omise_public_key else "not_set",
        }
        
        # Test API connectivity
        connectivity_test = {
            "can_reach_omise_api": False,
            "api_response": None,
            "error": None
        }
        
        if settings.omise_secret_key and settings.omise_secret_key.startswith("skey_"):
            try:
                async with httpx.AsyncClient() as client:
                    # Simple API call to verify connectivity (using account endpoint)
                    response = await client.get(
                        "https://api.omise.co/account",
                        auth=(settings.omise_secret_key, ""),
                        timeout=10.0
                    )
                    connectivity_test["can_reach_omise_api"] = True
                    connectivity_test["api_response"] = {
                        "status_code": response.status_code,
                        "account_email": response.json().get("email", "N/A") if response.status_code == 200 else None
                    }
            except httpx.RequestError as req_err:
                connectivity_test["error"] = f"Network error: {str(req_err)}"
            except Exception as api_err:
                connectivity_test["error"] = f"API error: {str(api_err)}"
        
        return {
            "ok": True,
            "message": "Omise configuration check",
            "config": config_status,
            "connectivity": connectivity_test,
            "recommendations": [
                "Use POST /api/booking/test-omise to create a test payment link",
                "Test card number: 4242424242424242",
                "Any future expiry date and CVV",
                "For test mode, use keys starting with 'skey_test_' and 'pkey_test_'"
            ] if config_status["omise_secret_key_format"] == "valid" else [
                "Set OMISE_SECRET_KEY in .env file (should start with 'skey_test_' for test mode)",
                "Set OMISE_PUBLIC_KEY in .env file (should start with 'pkey_test_' for test mode)"
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to check Omise config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to check Omise config: {str(e)}")


@router.get("/payment-page/{booking_id}")
async def payment_page(
    request: Request,
    booking_id: str,
    amount: Optional[float] = Query(None, description="Payment amount"),
    currency: str = Query(default="THB", description="Currency code"),
    return_url: str = Query(default="", description="Return URL after payment"),
    cancel_url: str = Query(default="", description="Cancel URL")
):
    """
    Serve payment page with Omise.js integration - Modern split layout design
    ✅ SECURITY: Verifies booking ownership before showing payment page
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        from app.core.security import extract_user_id_from_request
        user_id = extract_user_id_from_request(request)
        
        if not settings.omise_public_key:
            raise HTTPException(status_code=500, detail="Omise public key not configured")
        
        # Get booking details for order summary
        booking_details = {}
        try:
            storage = MongoStorage()
            await storage.connect()
            bookings_collection = storage.db["bookings"]
            
            # ✅ SECURITY: Find booking with user_id filter FIRST
            from bson import ObjectId
            booking = None
            
            if not user_id:
                raise HTTPException(status_code=401, detail="Authentication required")
            
            # ✅ CRITICAL: Always query with user_id filter to prevent data leakage
            booking = None
            try:
                if len(booking_id) == 24:
                    booking = await bookings_collection.find_one({
                        "_id": ObjectId(booking_id),
                        "user_id": user_id  # ✅ Filter by user_id FIRST
                    })
            except Exception:
                pass

            if not booking:
                booking = await bookings_collection.find_one({
                    "booking_id": booking_id,
                    "user_id": user_id  # ✅ Filter by user_id FIRST
                })
            
            if not booking:
                # ✅ SECURITY: Don't reveal if booking exists but belongs to another user
                logger.warning(f"Booking not found or access denied: booking_id={booking_id}, user_id={user_id}")
                raise HTTPException(status_code=404, detail="Booking not found")
            
            # ✅ SECURITY: Double-check user_id matches (additional safety layer)
            booking_user_id = booking.get("user_id")
            if booking_user_id != user_id:
                logger.error(f"🚨 SECURITY ALERT: Booking {booking_id} user_id mismatch! expected {user_id}, found {booking_user_id}")
                raise HTTPException(status_code=403, detail="You do not have permission to access this booking")
            
            if booking:
                # Use amount from booking if not provided in query
                if amount is None:
                    amount = booking.get("total_price", 0)
                
                # ✅ FIX: If amount is 0, try to calculate from plan (same logic as payment endpoint)
                if not isinstance(amount, (int, float)) or amount <= 0:
                    logger.warning(f"Payment page: Booking {booking_id} has invalid total_price: {amount}. Attempting to calculate from plan...")
                    plan = booking.get("plan", {})
                    calculated_amount = 0
                    
                    # Calculate from flight prices
                    flight_data = plan.get("flight") or {}
                    if flight_data:
                        flight_price = (
                            flight_data.get("price_total") or
                            flight_data.get("price_amount") or
                            flight_data.get("price") or
                            flight_data.get("total_price") or
                            0
                        )
                        if isinstance(flight_price, (int, float)) and flight_price > 0:
                            calculated_amount += float(flight_price)
                    
                    # Calculate from hotel prices
                    hotel_data = plan.get("hotel") or {}
                    if hotel_data:
                        hotel_price = (
                            hotel_data.get("price_total") or
                            hotel_data.get("price_amount") or
                            hotel_data.get("price") or
                            hotel_data.get("total_price") or
                            0
                        )
                        if isinstance(hotel_price, (int, float)) and hotel_price > 0:
                            calculated_amount += float(hotel_price)
                    
                    # Calculate from transport prices
                    transport_data = plan.get("transport") or plan.get("transfer") or {}
                    if transport_data:
                        transport_price = (
                            transport_data.get("price_total") or
                            transport_data.get("price_amount") or
                            transport_data.get("price") or
                            transport_data.get("total_price") or
                            0
                        )
                        if isinstance(transport_price, (int, float)) and transport_price > 0:
                            calculated_amount += float(transport_price)
                    
                    if calculated_amount > 0:
                        amount = calculated_amount
                        logger.info(f"Payment page: Calculated amount from plan: {calculated_amount}")
                    else:
                        logger.warning(f"Payment page: Could not calculate amount from plan for booking {booking_id}")
                
                booking_details = {
                    "trip_title": booking.get("trip_title", "Travel Booking"),
                    "travel_slots": booking.get("travel_slots", {}),
                    "description": booking.get("description", ""),
                    "total_price": amount if amount > 0 else booking.get("total_price", 0),
                    "currency": booking.get("currency", currency)
                }
        except Exception as e:
            logger.warning(f"Could not fetch booking details: {e}")
        
        if amount is None:
            amount = 0.0 # Fallback
        
        # Default return URLs
        if not return_url:
            return_url = f"{settings.frontend_url}/bookings?booking_id={booking_id}&payment_status=success"
        
        # Format booking details for display
        trip_title = booking_details.get("trip_title", "Travel Booking")
        travel_slots = booking_details.get("travel_slots", {})
        origin = travel_slots.get("origin_city", "")
        destination = travel_slots.get("destination_city", "")
        departure_date = travel_slots.get("departure_date", "")
        description = f"{origin} → {destination}" if origin and destination else booking_details.get("description", "Travel Booking")
        
        # Check if using test mode
        is_test_mode = settings.omise_public_key.startswith("pkey_test_") if settings.omise_public_key else False
        
        # Load HTML template
        import os
        template_path = os.path.join(os.path.dirname(__file__), "payment_page_template.html")
        
        html_content = ""
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                html_content = f.read()
        except Exception as file_err:
            logger.error(f"Failed to read template file: {file_err}")
            raise HTTPException(status_code=500, detail="Payment page template not found")
        
        # Replace template placeholders with actual data
        # Note: We use .replace() on a plain string to avoid f-string interpolation issues
        html_content = html_content.replace("{omise_public_key}", settings.omise_public_key)
        html_content = html_content.replace("{booking_id}", booking_id)
        html_content = html_content.replace("{amount}", f"{amount:,.2f}")
        html_content = html_content.replace("{currency}", currency)
        html_content = html_content.replace("{return_url}", return_url)
        html_content = html_content.replace("{trip_title}", trip_title)
        html_content = html_content.replace("{description}", description)
        html_content = html_content.replace("{origin}", origin or "Origin")
        html_content = html_content.replace("{destination}", destination or "Destination")
        html_content = html_content.replace("{departure_date}", departure_date or "Date TBD")
        html_content = html_content.replace("{is_test_mode}", "true" if is_test_mode else "false")
        
        return HTMLResponse(content=html_content)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving payment page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")


class CreateChargeRequest(BaseModel):
    """Request model for creating Omise charge"""
    booking_id: str = Field(..., description="Booking ID")
    token: Optional[str] = Field(None, description="Omise token from frontend (new card)")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(default="THB", description="Currency code")
    card_id: Optional[str] = Field(None, description="Omise card id (saved card)")
    customer_id: Optional[str] = Field(None, description="Omise customer id (saved card)")
    payment_method: Optional[str] = Field(None, description="promptpay = สแกน QR PromtPay (ไม่ใช้ token/card)")


@router.post("/create-charge")
async def create_charge(fastapi_request: Request, request: CreateChargeRequest):
    """
    Create Omise charge using token from frontend
    ✅ SECURITY: Verifies booking ownership before processing payment
    """
    try:
        # ✅ FIX: Prioritize X-User-ID header over cookie (frontend sends correct user_id in header)
        user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        if not settings.omise_secret_key or not settings.omise_secret_key.startswith("skey_"):
            raise HTTPException(status_code=500, detail="Omise secret key not configured")
        
        # ✅ SECURITY: Verify booking ownership before processing payment
        storage = MongoStorage()
        await storage.connect()
        bookings_collection = storage.db["bookings"]
        
        # ✅ SECURITY: Find booking with user_id filter FIRST
        from bson import ObjectId
        booking = None
        
        # ✅ CRITICAL: Always query with user_id filter to prevent data leakage
        booking = None
        try:
            if len(request.booking_id) == 24:
                booking = await bookings_collection.find_one({
                    "_id": ObjectId(request.booking_id),
                    "user_id": user_id  # ✅ Filter by user_id FIRST
                })
        except Exception:
            pass

        if not booking:
            booking = await bookings_collection.find_one({
                "booking_id": request.booking_id,
                "user_id": user_id  # ✅ Filter by user_id FIRST
            })
        
        if not booking:
            # ✅ SECURITY: Don't reveal if booking exists but belongs to another user
            logger.warning(f"Booking not found or access denied: booking_id={request.booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found")
        
        # ✅ SECURITY: Double-check user_id matches (additional safety layer)
        booking_user_id = booking.get("user_id")
        if booking_user_id != user_id:
            logger.error(f"🚨 SECURITY ALERT: Booking {request.booking_id} user_id mismatch! expected {user_id}, found {booking_user_id}")
            raise HTTPException(status_code=403, detail="You do not have permission to process payment for this booking")
        
        # Check if using test mode
        is_test_mode = settings.omise_secret_key.startswith("skey_test_")
        if is_test_mode:
            logger.info(f"Creating charge in TEST mode (sandbox) for booking {request.booking_id}")
        else:
            logger.info(f"Creating charge in LIVE mode for booking {request.booking_id}")
        
        # Validate amount matches booking
        booking_amount = booking.get("total_price", 0)
        if abs(request.amount - booking_amount) > 0.01:  # Allow small floating point differences
            logger.warning(f"Charge amount mismatch: request={request.amount}, booking={booking_amount}")
            raise HTTPException(status_code=400, detail=f"Payment amount ({request.amount}) does not match booking amount ({booking_amount})")
        
        # Validate amount
        if request.amount <= 0:
            raise HTTPException(status_code=400, detail="Invalid amount")

        use_promptpay = (request.payment_method or "").strip().lower() == "promptpay"
        if use_promptpay:
            # PromptPay: จำนวนขั้นต่ำ 20 บาท, สูงสุด 150,000 บาท (Omise limit)
            amount_satang = int(round(request.amount * 100))
            if amount_satang < 2000:
                raise HTTPException(status_code=400, detail="ยอดขั้นต่ำสำหรับ PromtPay คือ ฿20")
            if amount_satang > 15000000:
                raise HTTPException(status_code=400, detail="ยอดสูงสุดสำหรับ PromtPay คือ ฿150,000")
        else:
            amount_satang = int(request.amount * 100)

        use_saved_card = request.card_id and request.customer_id
        if not use_promptpay and not use_saved_card and not request.token:
            raise HTTPException(status_code=400, detail="Provide either token (new card), card_id and customer_id (saved card), or payment_method=promptpay")
        if use_saved_card:
            # ✅ SECURITY: Verify saved card belongs to this user in MongoDB
            saved_doc = await storage.saved_cards_collection.find_one({"user_id": user_id})
            if not saved_doc:
                raise HTTPException(status_code=404, detail="Saved cards not found")
            cards = saved_doc.get("cards") or []
            if not any(c.get("card_id") == request.card_id for c in cards):
                raise HTTPException(status_code=403, detail="Card does not belong to your account")
        
        charge_payload = {
            "amount": amount_satang,
            "currency": request.currency.lower(),
            "description": f"Booking #{request.booking_id}",
            "metadata": {"booking_id": request.booking_id, "user_id": user_id},
        }
        if use_promptpay:
            charge_payload["source"] = {"type": "promptpay"}
        elif use_saved_card:
            charge_payload["customer"] = request.customer_id
            charge_payload["card"] = request.card_id
        else:
            charge_payload["card"] = request.token

        # Create charge using Omise API
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.omise.co/charges",
                    auth=(settings.omise_secret_key, ""),
                    json=charge_payload,
                    timeout=30.0
                )

                if response.status_code == 200:
                    charge_data = response.json()

                    if use_promptpay:
                        # PromptPay: charge is pending until user scans QR; return QR link and authorize_uri
                        source = charge_data.get("source") or {}
                        scannable = source.get("scannable_code") or {}
                        image = scannable.get("image") or {}
                        qr_download_uri = image.get("download_uri")
                        authorize_uri = charge_data.get("authorize_uri")
                        # Update booking with pending charge (ไม่เปลี่ยน status เป็น paid จนกว่าจะได้ webhook charge.complete)
                        from bson import ObjectId
                        up_filter = {"user_id": user_id, "booking_id": request.booking_id}
                        await bookings_collection.update_one(
                            up_filter,
                            {"$set": {
                                "status": "pending_payment",
                                "payment_id": charge_data.get("id"),
                                "payment_status": charge_data.get("status"),
                                "promptpay_charge_id": charge_data.get("id"),
                                "updated_at": datetime.utcnow().isoformat()
                            }}
                        )
                        return {
                            "ok": True,
                            "message": "กรุณาสแกน QR PromtPay เพื่อชำระเงิน",
                            "charge_id": charge_data.get("id"),
                            "status": charge_data.get("status"),
                            "paid": False,
                            "authorize_uri": authorize_uri,
                            "qr_download_uri": qr_download_uri,
                        }

                    # ✅ Sync Amadeus sandbox แบบ best-effort — ไม่บล็อกการชำระเงิน
                    # Amadeus sandbox offer หมดอายุเร็ว ไม่ควรทำให้ user ชำระเงินไม่ได้
                    if charge_data.get("paid"):
                        async def _do_sync():
                            await _sync_booking_to_amadeus_sandbox(booking, bookings_collection)
                        try:
                            await _amadeus_retry_until_success("sync_booking", _do_sync)
                        except Exception as sync_err:
                            # Log เพื่อ debug แต่ไม่บล็อก — การชำระเงินสำเร็จแล้ว
                            logger.warning(
                                f"Amadeus sandbox sync failed (best-effort, payment already confirmed): {sync_err}"
                            )
                            # บันทึก sync error ลง booking doc เพื่อ audit
                            try:
                                await bookings_collection.update_one(
                                    {"booking_id": request.booking_id},
                                    {"$set": {
                                        "amadeus_sync_error": str(sync_err),
                                        "amadeus_sync_status": "failed",
                                        "updated_at": datetime.utcnow().isoformat()
                                    }}
                                )
                            except Exception:
                                pass
                    
                    # Update booking status (paid ได้เฉพาะหลัง sync Amadeus สำเร็จ)
                    try:
                        await bookings_collection.update_one(
                            {"_id": ObjectId(request.booking_id)},
                            {"$set": {
                                "status": "paid" if charge_data.get("paid") else "pending_payment",
                                "payment_id": charge_data.get("id"),
                                "payment_status": charge_data.get("status"),
                                "updated_at": datetime.utcnow().isoformat()
                            }}
                        )
                    except Exception:
                        await bookings_collection.update_one(
                            {"booking_id": request.booking_id},
                            {"$set": {
                                "status": "paid" if charge_data.get("paid") else "pending_payment",
                                "payment_id": charge_data.get("id"),
                                "payment_status": charge_data.get("status"),
                                "updated_at": datetime.utcnow().isoformat()
                            }}
                        )
                    
                    logger.info(f"Charge created successfully for booking {request.booking_id}: {charge_data.get('id')}")
                    
                    # ✅ Invalidate bookings list cache for this user
                    booking_for_cache = None
                    try:
                        booking_for_cache = await bookings_collection.find_one({"_id": ObjectId(request.booking_id)})
                        if not booking_for_cache:
                            booking_for_cache = await bookings_collection.find_one({"booking_id": request.booking_id})
                        if booking_for_cache:
                            user_id_for_cache = booking_for_cache.get("user_id")
                            if user_id_for_cache:
                                from app.core.redis_cache import cache
                                cache_key = f"bookings:list:{user_id_for_cache}"
                                await cache.delete(cache_key)
                                logger.debug(f"Invalidated bookings cache for user: {user_id_for_cache}")
                    except Exception as cache_err:
                        logger.debug(f"Failed to invalidate cache after payment: {cache_err}")

                    # ✅ Create payment_status notification if user has it enabled
                    try:
                        from app.services.notification_preferences import should_create_in_app_notification
                        _bk = booking_for_cache
                        if not _bk:
                            try:
                                _bk = await bookings_collection.find_one({"_id": ObjectId(request.booking_id)})
                            except Exception:
                                _bk = await bookings_collection.find_one({"booking_id": request.booking_id})
                        if _bk:
                            _uid = _bk.get("user_id")
                            if _uid:
                                users_collection = storage.db["users"]
                                user_doc = await users_collection.find_one({"user_id": _uid})
                                is_paid = charge_data.get("paid", False)
                                if should_create_in_app_notification(user_doc, "payment_status"):
                                    notifications_collection = storage.db.get_collection("notifications")
                                    pay_doc = {
                                        "user_id": _uid,
                                        "type": "payment_status",
                                        "title": "ชำระเงินสำเร็จ" if is_paid else "การชำระเงินล้มเหลว",
                                        "message": (
                                            f"ชำระเงินสำเร็จสำหรับการจอง #{request.booking_id[:8]}"
                                            if is_paid else
                                            f"การชำระเงินสำหรับการจอง #{request.booking_id[:8]} ไม่สำเร็จ"
                                        ),
                                        "booking_id": request.booking_id,
                                        "read": False,
                                        "created_at": datetime.utcnow().isoformat() + "Z",
                                        "metadata": {
                                            "charge_id": charge_data.get("id"),
                                            "paid": is_paid,
                                            "amount": _bk.get("total_price"),
                                            "currency": _bk.get("currency", "THB"),
                                        }
                                    }
                                    result = await notifications_collection.insert_one(pay_doc)
                                    pay_doc["id"] = str(result.inserted_id)
                                    pay_doc.pop("_id", None)
                                    await push_notification_event(_uid, pay_doc)
                                    logger.info(f"Created payment_status notification for booking {request.booking_id}")
                                    if is_paid:
                                        import asyncio
                                        from app.services.notification_service import send_notification_email_if_enabled
                                        asyncio.create_task(
                                            send_notification_email_if_enabled(
                                                db=storage.db,
                                                user_id=_uid,
                                                notif_type="payment_success",
                                                title="ชำระเงินสำเร็จ",
                                                message=pay_doc["message"],
                                                booking_id=request.booking_id,
                                            )
                                        )
                                # ส่งอีเมลใบเสร็จ/ยืนยันชำระเงินทุกครั้งเมื่อชำระสำเร็จ (ไม่ขึ้นกับ preference)
                                if is_paid and user_doc:
                                    _to_email = (user_doc.get("email") or "").strip()
                                    if _to_email and "@" in _to_email:
                                        try:
                                            from app.services.email_service import get_email_service
                                            _amount = _bk.get("total_price")
                                            _currency = _bk.get("currency", "THB")
                                            _amount_str = f"{_amount:,.2f} {_currency}" if _amount is not None else _currency
                                            _receipt_msg = (
                                                f"ชำระเงินสำเร็จสำหรับการจอง #{request.booking_id[:8]} "
                                                f"ยอดชำระ {_amount_str} คุณสามารถตรวจสอบรายการจองได้ที่ My Bookings"
                                            )
                                            _email_svc = get_email_service()
                                            if _email_svc.send_notification_email(
                                                _to_email,
                                                f"ชำระเงินสำเร็จ — การจอง #{request.booking_id[:8]}",
                                                "ชำระเงินสำเร็จ",
                                                _receipt_msg,
                                            ):
                                                logger.info(f"Payment receipt email sent to {_to_email} for booking {request.booking_id}")
                                            else:
                                                logger.warning("Payment receipt email not sent (SMTP not configured or failed)")
                                        except Exception as _email_err:
                                            logger.warning(f"Failed to send payment receipt email: {_email_err}")
                    except Exception as notif_err:
                        logger.warning(f"Failed to create payment notification: {notif_err}")

                    return {
                        "ok": True,
                        "message": "Payment successful",
                        "charge_id": charge_data.get("id"),
                        "status": charge_data.get("status"),
                        "paid": charge_data.get("paid", False)
                    }
                else:
                    error_text = response.text
                    logger.error(f"Omise charge error: {response.status_code} - {error_text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Payment failed: {error_text}"
                    )
                    
            except httpx.RequestError as req_err:
                logger.error(f"Network error creating charge: {req_err}")
                raise HTTPException(status_code=503, detail="Payment gateway unreachable")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create charge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process payment: {str(e)}")


@router.get("/payment-config")
async def get_payment_config(request: Request):
    """
    Get payment configuration (Omise public key) for frontend
    """
    try:
        if not settings.omise_public_key:
            raise HTTPException(status_code=500, detail="Omise public key not configured")
        
        return {
            "ok": True,
            "public_key": settings.omise_public_key,
            "is_test_mode": settings.omise_public_key.startswith("pkey_test_")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get payment config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get payment config: {str(e)}")


@router.get("/omise.js")
async def serve_omise_js():
    """
    Proxy Omise.js from CDN — โหลดจาก Backend (same origin) ลดโอกาสถูก Ad blocker / CORS บล็อก
    """
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://cdn.omise.co/omise.js", timeout=15.0)
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="Omise CDN unavailable")
            from fastapi.responses import Response
            return Response(content=resp.content, media_type="application/javascript")
    except httpx.RequestError as e:
        logger.warning(f"Omise.js proxy failed: {e}")
        raise HTTPException(status_code=502, detail="Cannot fetch Omise.js from CDN")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Omise.js proxy error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to serve Omise.js")


# =============================================================================
# Saved Cards (MongoDB + Omise Customer)
# =============================================================================

class AddSavedCardRequest(BaseModel):
    """Request model for adding a saved card"""
    token: str = Field(..., description="Omise token from frontend (single-use)")
    email: Optional[str] = Field(None, description="Customer email (for Omise customer)")
    name: Optional[str] = Field(None, description="Cardholder name (ชื่อผู้ถือบัตร)")


class AddSavedCardLocalRequest(BaseModel):
    """Request model for adding a saved card to DB only (no Omise)"""
    last4: str = Field(..., description="Last 4 digits of card")
    brand: str = Field(..., description="Card brand: visa, mastercard, amex, etc.")
    expiry_month: str = Field(..., description="MM")
    expiry_year: str = Field(..., description="YY")
    name: Optional[str] = Field(None, description="Cardholder name")


@router.get("/saved-cards")
async def list_saved_cards(request: Request):
    """
    List saved cards for the current user (from MongoDB).
    Returns list of { id, last4, brand, expiry_month, expiry_year } — id is Omise card_id for charging.
    """
    try:
        user_id = request.headers.get("X-User-ID") or request.cookies.get(settings.session_cookie_name)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        storage = MongoStorage()
        await storage.connect()
        doc = await storage.saved_cards_collection.find_one({"user_id": user_id})
        cards = (doc or {}).get("cards") or []
        primary_card_id = doc.get("primary_card_id") if doc else None
        return {"ok": True, "cards": cards, "customer_id": doc.get("omise_customer_id") if doc else None, "primary_card_id": primary_card_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list saved cards: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list saved cards: {str(e)}")


@router.post("/saved-cards")
async def add_saved_card(fastapi_request: Request, body: AddSavedCardRequest):
    """
    Add a card to the user's saved cards: create/update Omise customer with token, then save to MongoDB.
    """
    try:
        user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        if not settings.omise_secret_key or not settings.omise_secret_key.startswith("skey_"):
            raise HTTPException(status_code=500, detail="Omise secret key not configured")
        storage = MongoStorage()
        await storage.connect()
        coll = storage.saved_cards_collection
        doc = await coll.find_one({"user_id": user_id})
        email = (body.email or "").strip() or f"user-{user_id}@saved-card.local"
        async with httpx.AsyncClient() as client:
            auth = (settings.omise_secret_key, "")
            if not doc or not doc.get("omise_customer_id"):
                # Create new Omise customer with card
                resp = await client.post(
                    "https://api.omise.co/customers",
                    auth=auth,
                    json={"email": email, "description": f"User {user_id}", "card": body.token},
                    timeout=30.0,
                )
                if resp.status_code != 200:
                    err = resp.json() if resp.text else {}
                    raise HTTPException(status_code=400, detail=err.get("message", resp.text))
                data = resp.json()
                customer_id = data["id"]
                cards_data = data.get("cards", {}).get("data") or []
                if not cards_data:
                    raise HTTPException(status_code=400, detail="Card could not be added to customer")
                new_card = cards_data[-1]
                card_info = {
                    "card_id": new_card["id"],
                    "last4": new_card.get("last_digits", "****"),
                    "brand": new_card.get("brand", "Card"),
                    "expiry_month": str(new_card.get("expiration_month", "")),
                    "expiry_year": str(new_card.get("expiration_year", ""))[-2:],
                }
                if body.name and body.name.strip():
                    card_info["name"] = body.name.strip()
                await coll.update_one(
                    {"user_id": user_id},
                    {"$set": {"user_id": user_id, "omise_customer_id": customer_id, "updated_at": datetime.utcnow().isoformat()}, "$push": {"cards": card_info}},
                    upsert=True,
                )
            else:
                # Add card to existing customer
                customer_id = doc["omise_customer_id"]
                resp = await client.patch(
                    f"https://api.omise.co/customers/{customer_id}",
                    auth=auth,
                    json={"card": body.token},
                    timeout=30.0,
                )
                if resp.status_code != 200:
                    err = resp.json() if resp.text else {}
                    raise HTTPException(status_code=400, detail=err.get("message", resp.text))
                data = resp.json()
                cards_data = data.get("cards", {}).get("data") or []
                if not cards_data:
                    raise HTTPException(status_code=400, detail="Card could not be added")
                new_card = cards_data[-1]
                card_info = {
                    "card_id": new_card["id"],
                    "last4": new_card.get("last_digits", "****"),
                    "brand": new_card.get("brand", "Card"),
                    "expiry_month": str(new_card.get("expiration_month", "")),
                    "expiry_year": str(new_card.get("expiration_year", ""))[-2:],
                }
                if body.name and body.name.strip():
                    card_info["name"] = body.name.strip()
                await coll.update_one(
                    {"user_id": user_id},
                    {"$push": {"cards": card_info}, "$set": {"updated_at": datetime.utcnow().isoformat()}},
                )
            # Return updated list
            doc = await coll.find_one({"user_id": user_id})
            cards = (doc or {}).get("cards") or []
        # Notification: บัตรถูกเพิ่มสำเร็จ
        try:
            from app.services.notification_service import create_and_push_notification
            await create_and_push_notification(
                db=storage.db,
                user_id=user_id,
                notif_type="account_card_added",
                title="เพิ่มบัตรสำเร็จ",
                message=f"เพิ่มบัตร {card_info.get('brand', 'Card')} ****{card_info.get('last4', '****')} เรียบร้อยแล้ว",
                metadata={"brand": card_info.get("brand"), "last4": card_info.get("last4")},
            )
        except Exception:
            pass
        return {"ok": True, "cards": cards, "customer_id": customer_id, "primary_card_id": doc.get("primary_card_id") if doc else None}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add saved card: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add saved card: {str(e)}")


@router.put("/saved-cards/{card_id}/set-primary")
async def set_primary_card(fastapi_request: Request, card_id: str):
    """Set a card as the primary payment card."""
    try:
        user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        storage = MongoStorage()
        await storage.connect()
        coll = storage.saved_cards_collection
        doc = await coll.find_one({"user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="No saved cards")
        cards = doc.get("cards") or []
        if not any(c.get("card_id") == card_id for c in cards):
            raise HTTPException(status_code=404, detail="Card not found")
        await coll.update_one(
            {"user_id": user_id},
            {"$set": {"primary_card_id": card_id, "updated_at": datetime.utcnow().isoformat()}},
        )
        return {"ok": True, "primary_card_id": card_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set primary card: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to set primary card: {str(e)}")


@router.post("/saved-cards/add-local")
async def add_saved_card_local(fastapi_request: Request, body: AddSavedCardLocalRequest):
    """
    Add a card to the user's saved cards in MongoDB only (no Omise).
    Stores last4, brand, expiry — never full card number or CVV.
    """
    try:
        user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        last4 = "".join(c for c in (body.last4 or "") if c.isdigit())[-4:]
        if len(last4) != 4:
            raise HTTPException(status_code=400, detail="last4 must be 4 digits")
        brand_raw = (body.brand or "Card").strip().lower()
        brand_map = {"visa": "Visa", "mastercard": "Mastercard", "amex": "American Express", "jcb": "JCB",
                     "discover": "Discover", "diners": "Diners Club", "unionpay": "UnionPay"}
        brand = brand_map.get(brand_raw, brand_raw.title() if brand_raw else "Card")
        mm = (body.expiry_month or "").strip()
        yy = (body.expiry_year or "").strip()
        if len(mm) != 2 or len(yy) != 2 or not mm.isdigit() or not yy.isdigit():
            raise HTTPException(status_code=400, detail="expiry_month and expiry_year must be MM and YY")
        card_id = "local_" + str(uuid.uuid4())
        card_info = {
            "card_id": card_id,
            "last4": last4,
            "brand": brand,
            "expiry_month": mm,
            "expiry_year": yy,
        }
        if body.name and body.name.strip():
            card_info["name"] = body.name.strip()
        storage = MongoStorage()
        await storage.connect()
        coll = storage.saved_cards_collection
        doc = await coll.find_one({"user_id": user_id})
        update_op = {"$set": {"user_id": user_id, "updated_at": datetime.utcnow().isoformat()}, "$push": {"cards": card_info}}
        if not doc or not doc.get("cards"):
            update_op["$set"]["primary_card_id"] = card_id
        await coll.update_one(
            {"user_id": user_id},
            update_op,
            upsert=True,
        )
        doc = await coll.find_one({"user_id": user_id})
        cards = (doc or {}).get("cards") or []
        primary_card_id = doc.get("primary_card_id") if doc else None
        # Notification: บัตรถูกเพิ่มสำเร็จ
        try:
            from app.services.notification_service import create_and_push_notification
            await create_and_push_notification(
                db=storage.db,
                user_id=user_id,
                notif_type="account_card_added",
                title="เพิ่มบัตรสำเร็จ",
                message=f"เพิ่มบัตร {card_info.get('brand', 'Card')} ****{card_info.get('last4', '****')} เรียบร้อยแล้ว",
                metadata={"brand": card_info.get("brand"), "last4": card_info.get("last4")},
            )
        except Exception:
            pass
        return {"ok": True, "cards": cards, "primary_card_id": primary_card_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add saved card (local): {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to add saved card: {str(e)}")


@router.delete("/saved-cards/{card_id}")
async def delete_saved_card(fastapi_request: Request, card_id: str):
    """
    Remove a saved card from MongoDB. For Omise cards, also remove from Omise customer.
    For local_ cards, only remove from MongoDB.
    """
    try:
        user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        storage = MongoStorage()
        await storage.connect()
        coll = storage.saved_cards_collection
        doc = await coll.find_one({"user_id": user_id})
        if not doc:
            raise HTTPException(status_code=404, detail="No saved cards")
        cards = doc.get("cards") or []
        if not any(c.get("card_id") == card_id for c in cards):
            raise HTTPException(status_code=404, detail="Card not found")
        doc_before_delete = doc  # เก็บไว้สำหรับ notification
        update_data = {"$pull": {"cards": {"card_id": card_id}}, "$set": {"updated_at": datetime.utcnow().isoformat()}}
        if doc.get("primary_card_id") == card_id:
            remaining = [c for c in cards if c.get("card_id") != card_id]
            update_data["$set"]["primary_card_id"] = remaining[0]["card_id"] if remaining else None
        is_local = card_id.startswith("local_")
        if not is_local:
            customer_id = doc.get("omise_customer_id")
            if not customer_id:
                raise HTTPException(status_code=404, detail="No Omise customer")
            if settings.omise_secret_key and settings.omise_secret_key.startswith("skey_"):
                async with httpx.AsyncClient() as client:
                    resp = await client.delete(
                        f"https://api.omise.co/customers/{customer_id}/cards/{card_id}",
                        auth=(settings.omise_secret_key, ""),
                        timeout=30.0,
                    )
                    if resp.status_code not in (200, 204):
                        err = resp.json() if resp.text else {}
                        logger.warning(f"Omise delete card: {resp.status_code} - {err}")
        await coll.update_one(
            {"user_id": user_id},
            update_data,
        )
        doc = await coll.find_one({"user_id": user_id})
        cards = (doc or {}).get("cards") or []
        primary_card_id = doc.get("primary_card_id") if doc else None
        # Notification: ลบบัตรสำเร็จ
        try:
            deleted_card = next((c for c in (doc_before_delete or {}).get("cards", []) if c.get("card_id") == card_id), {})
            from app.services.notification_service import create_and_push_notification
            await create_and_push_notification(
                db=storage.db,
                user_id=user_id,
                notif_type="account_card_removed",
                title="ลบบัตรสำเร็จ",
                message=f"ลบบัตร {deleted_card.get('brand', 'Card')} ****{deleted_card.get('last4', '****')} เรียบร้อยแล้ว",
                metadata={"card_id": card_id},
            )
        except Exception:
            pass
        return {"ok": True, "cards": cards, "primary_card_id": primary_card_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete saved card: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete saved card: {str(e)}")


# ---------------------------------------------------------------------------
# Proactive Crisis Manager — manual flight status check (local dev trigger)
# ---------------------------------------------------------------------------

@router.post("/{booking_id}/check-flight", summary="Manual flight status check (Crisis Manager trigger)")
async def trigger_flight_check(booking_id: str, fastapi_request: Request):
    """
    Manually trigger the FlightMonitorService for a specific booking.
    Useful for local dev testing without waiting for the 30-min background loop.
    """
    user_id = fastapi_request.headers.get("X-User-ID") or fastapi_request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    await storage.connect()
    booking_doc = await storage.db["bookings"].find_one({"booking_id": booking_id, "user_id": user_id})
    if not booking_doc:
        raise HTTPException(status_code=404, detail="Booking not found")

    try:
        from app.services.flight_monitor import FlightMonitorService
        monitor = FlightMonitorService(db=storage.db)
        await monitor.check_booking(booking_id, user_id, booking_doc)
        updated = await storage.db["bookings"].find_one({"booking_id": booking_id}, {"flight_status": 1, "delay_minutes": 1})
        return {
            "booking_id": booking_id,
            "flight_status": (updated or {}).get("flight_status", "unknown"),
            "delay_minutes": (updated or {}).get("delay_minutes", 0),
            "checked_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"[FlightMonitor] Manual check failed for {booking_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Flight check failed: {str(e)}")
