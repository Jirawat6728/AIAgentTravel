"""
Booking API Router
Handles booking creation, payment, cancellation, and listing
Integrates with Omise Payment Gateway
"""

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.mongodb_storage import MongoStorage
from app.services.omise_service import OmiseService
import httpx

logger = get_logger(__name__)

router = APIRouter(prefix="/api/booking", tags=["booking"])


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
async def create_booking(request: BookingCreateRequest):
    """
    Create a new booking (pending payment or confirmed for Agent Mode).
    Returns {ok, booking_id, message, status}. Cancel via POST /api/booking/cancel?booking_id=...
    SECURITY: Amadeus booking is sandbox-only (production blocked).
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
        
        # ✅ Log incoming request for debugging
        logger.info(f"Creating booking - trip_id: {request.trip_id}, user_id: {request.user_id}, mode: {request.mode}, booking_env: {booking_env}")
        logger.debug(f"Booking request - plan keys: {list(request.plan.keys()) if request.plan else 'None'}, travel_slots keys: {list(request.travel_slots.keys()) if request.travel_slots else 'None'}, total_price: {request.total_price}")
        
        # ✅ Validate required fields
        if not request.plan or not isinstance(request.plan, dict):
            raise HTTPException(status_code=400, detail="Invalid request format: 'plan' is required and must be a dictionary")
        if not request.travel_slots or not isinstance(request.travel_slots, dict):
            raise HTTPException(status_code=400, detail="Invalid request format: 'travel_slots' is required and must be a dictionary")
        if request.total_price is None or (isinstance(request.total_price, (int, float)) and request.total_price < 0):
            raise HTTPException(status_code=400, detail="Invalid request format: 'total_price' must be a non-negative number")
        if not request.user_id:
            raise HTTPException(status_code=400, detail="Invalid request format: 'user_id' is required")
        if not request.trip_id:
            raise HTTPException(status_code=400, detail="Invalid request format: 'trip_id' is required")
        
        storage = MongoStorage()
        await storage.connect()
        
        # ✅ Agent Mode: Still requires payment (Amadeus sandbox needs payment before booking)
        # Status is always "pending_payment" - user must pay first
        initial_status = "pending_payment"
        
        # ✅ SECURITY: Validate and normalize user_id
        user_id = request.user_id.strip() if request.user_id else None
        if not user_id:
            raise HTTPException(status_code=400, detail="Invalid request format: 'user_id' is required and cannot be empty")
        
        # Create booking document
        booking_doc = {
            "trip_id": request.trip_id,
            "chat_id": request.chat_id,
            "user_id": user_id,  # ✅ Use normalized user_id
            "plan": request.plan,
            "travel_slots": request.travel_slots,
            "total_price": request.total_price,
            "currency": request.currency,
            "status": initial_status,  # ✅ "confirmed" for Agent Mode, "pending_payment" for Normal Mode
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "metadata": {
                "mode": request.mode or "normal",  # ✅ Store chat mode
                "auto_booked": request.auto_booked or False  # ✅ Flag for agent mode
            }
        }
        
        # Insert into bookings collection
        bookings_collection = storage.db["bookings"]
        result = await bookings_collection.insert_one(booking_doc)
        booking_id = str(result.inserted_id)
        
        logger.info(f"Created booking: {booking_id} for user: {user_id} (status: {initial_status})")
        
        # ✅ Create notification for the user
        try:
            notifications_collection = storage.db.get_collection("notifications")
            notification_doc = {
                "user_id": user_id,  # ✅ Use normalized user_id
                "type": "booking_created",
                "title": "จองสำเร็จ",
                "message": f"การจองของคุณได้รับการสร้างแล้ว กรุณาชำระเงินเพื่อยืนยันการจอง",
                "booking_id": booking_id,
                "read": False,
                "created_at": datetime.utcnow().isoformat(),
                "metadata": {
                    "status": initial_status,
                    "total_price": request.total_price,
                    "currency": request.currency
                }
            }
            await notifications_collection.insert_one(notification_doc)
            logger.info(f"Created notification for booking: {booking_id} (user_id: {user_id})")
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
            "status": initial_status
        }
        
    except Exception as e:
        logger.error(f"Failed to create booking: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create booking: {str(e)}")


@router.get("/list")
async def list_bookings(request: Request):
    """
    List all bookings for the current user
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        from app.core.security import extract_user_id_from_request
        user_id = extract_user_id_from_request(request)
        
        # ✅ Log mismatch warning if both exist and differ (for debugging)
        # Check log level instead of debug_mode (debug_mode doesn't exist in Settings)
        cookie_user_id = request.cookies.get(settings.session_cookie_name)
        header_user_id = request.headers.get("X-User-ID")
        if cookie_user_id and header_user_id and cookie_user_id.strip() != header_user_id.strip():
            logger.warning(f"⚠️ User ID mismatch - Cookie: {cookie_user_id}, Header: {header_user_id}. Using cookie (priority): {cookie_user_id}")
        
        # ✅ Log extracted user_id for debugging
        logger.info(f"Extracted user_id from request: '{user_id}' (cookie: '{cookie_user_id}', header: '{header_user_id}')")
        
        if not user_id:
            # Return empty list if no user_id
            logger.warning("No user_id provided in request")
            return {
                "ok": True,
                "bookings": [],
                "count": 0
            }
        
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
        # ✅ Normalize user_id (strip whitespace, ensure string)
        user_id_normalized = user_id.strip() if user_id else None
        query = {"user_id": user_id_normalized}
        
        # ✅ DEBUG: Log query details
        logger.info(f"Querying bookings with user_id: '{user_id_normalized}' (original: '{user_id}')")
        
        # ✅ DEBUG: Check if collection exists and has any documents
        total_count = await bookings_collection.count_documents({})
        logger.info(f"Total bookings in database: {total_count}")
        
        # ✅ DEBUG: Check if any bookings exist for this user_id
        user_count = await bookings_collection.count_documents(query)
        logger.info(f"Bookings found for user_id '{user_id_normalized}': {user_count}")
        
        # ✅ DEBUG: Sample a few bookings to check user_id format
        if total_count > 0:
            sample_bookings = await bookings_collection.find({}).limit(5).to_list(length=5)
            sample_user_ids = [b.get('user_id') for b in sample_bookings]
            logger.info(f"Sample booking user_ids (first 5): {sample_user_ids}")
            logger.info(f"Sample booking user_id types: {[type(b.get('user_id')).__name__ for b in sample_bookings]}")
            
            # ✅ Check if any sample user_id matches (for debugging)
            if user_id_normalized:
                matches = [uid for uid in sample_user_ids if uid and str(uid).strip() == user_id_normalized]
                if matches:
                    logger.info(f"✅ Found matching user_id in samples: {matches}")
                else:
                    logger.warning(f"⚠️ No matching user_id found in samples. Querying user_id: '{user_id_normalized}'")
        
        cursor = bookings_collection.find(query).sort("created_at", -1)
        bookings = await cursor.to_list(length=100)
        
        # Convert ObjectId to string
        for booking in bookings:
            booking["_id"] = str(booking["_id"])
        
        logger.info(f"Retrieved {len(bookings)} bookings for user: {user_id}")
        
        # ✅ DEBUG: Log response structure
        logger.debug(f"Response structure - ok: True, bookings count: {len(bookings)}, count field: {len(bookings)}")
        if len(bookings) > 0:
            logger.debug(f"First booking sample - _id: {bookings[0].get('_id')}, user_id: {bookings[0].get('user_id')}, status: {bookings[0].get('status')}")
        
        # ✅ DEBUG: If no bookings found, try alternative queries
        if len(bookings) == 0 and user_count == 0:
            # Try case-insensitive search
            case_insensitive_query = {"user_id": {"$regex": f"^{user_id_normalized}$", "$options": "i"}}
            case_insensitive_count = await bookings_collection.count_documents(case_insensitive_query)
            if case_insensitive_count > 0:
                logger.warning(f"Found {case_insensitive_count} bookings with case-insensitive match for user_id: {user_id_normalized}")
            
            # Try to find bookings with similar user_id (for debugging)
            all_user_ids = await bookings_collection.distinct("user_id")
            logger.info(f"All unique user_ids in database (first 20): {all_user_ids[:20]}")
            
            # ✅ Check if user_id from cookie/header matches any booking user_id
            if user_id_normalized:
                # Try exact match with different formats
                exact_matches = [uid for uid in all_user_ids if uid and str(uid).strip() == user_id_normalized]
                if exact_matches:
                    logger.info(f"✅ Found exact match in distinct user_ids: {exact_matches}")
                else:
                    logger.warning(f"⚠️ No exact match found. Query user_id: '{user_id_normalized}', Available user_ids: {all_user_ids[:10]}")
        
        return {
            "ok": True,
            "bookings": bookings,
            "count": len(bookings)
        }
        
    except Exception as e:
        logger.error(f"Failed to list bookings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list bookings: {str(e)}")


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
                        except:
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
            raise HTTPException(status_code=403, detail="You do not have permission to cancel this booking")
        
        # Update status
        from bson import ObjectId
        try:
            await bookings_collection.update_one(
                {"_id": ObjectId(booking_id)},
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
            )
        except:
            await bookings_collection.update_one(
                {"booking_id": booking_id},
                {"$set": {"status": "cancelled", "updated_at": datetime.utcnow().isoformat()}}
            )
        
        logger.info(f"Cancelled booking: {booking_id}")
        
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
        
        # Build update data (only include fields that were provided)
        update_data = {}
        if request.plan is not None:
            update_data["plan"] = request.plan
        if request.travel_slots is not None:
            update_data["travel_slots"] = request.travel_slots
        if request.total_price is not None:
            update_data["total_price"] = request.total_price
        if request.currency is not None:
            update_data["currency"] = request.currency
        if request.metadata is not None:
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
        except:
            result = await bookings_collection.update_one(
                {"booking_id": booking_id, "user_id": user_id},  # ✅ Filter by user_id
                {"$set": update_data}
            )
        
        if result.matched_count == 0:
            logger.warning(f"Booking not found during update: booking_id={booking_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Booking not found during update")
        
        logger.info(f"Updated booking: {booking_id} - Fields: {list(update_data.keys())}")
        
        # ✅ SECURITY: Return updated booking with user_id filter
        try:
            updated_booking = await bookings_collection.find_one({
                "_id": ObjectId(booking_id),
                "user_id": user_id  # ✅ Filter by user_id
            })
        except:
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
            try:
                if len(booking_id) == 24:
                    booking = await bookings_collection.find_one({
                        "_id": ObjectId(booking_id),
                        "user_id": user_id  # ✅ Filter by user_id FIRST
                    })
            except:
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
    token: str = Field(..., description="Omise token from frontend")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(default="THB", description="Currency code")


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
        try:
            if len(request.booking_id) == 24:
                booking = await bookings_collection.find_one({
                    "_id": ObjectId(request.booking_id),
                    "user_id": user_id  # ✅ Filter by user_id FIRST
                })
        except:
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
        
        # Create charge using Omise API
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.omise.co/charges",
                    auth=(settings.omise_secret_key, ""),
                    json={
                        "amount": int(request.amount * 100),  # Convert to satang
                        "currency": request.currency.lower(),
                        "card": request.token,
                        "description": f"Booking #{request.booking_id}",
                        "metadata": {
                            "booking_id": request.booking_id,
                            "user_id": user_id  # ✅ Store user_id in charge metadata
                        }
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    charge_data = response.json()
                    
                    # Update booking status
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
                    except:
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
