from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.config import get_amadeus_booking_client
from core.context import get_user_ctx
from core.safety import ensure_booking_is_sandbox
from db import get_db
from db.mongo.repos.bookings_repo import BookingsRepo
from core.auth import get_current_user
from fastapi import Depends
from bson import ObjectId

router = APIRouter(prefix="/api/booking", tags=["booking"])


class Traveler(BaseModel):
    id: str = "1"
    dateOfBirth: Optional[str] = None
    name: Dict[str, str] = Field(default_factory=dict)  # {"firstName": "...", "lastName": "..."}
    gender: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None  # {"emailAddress": "...", "phones":[...]}

class ConfirmBookingRequest(BaseModel):
    user_id: str = Field(..., description="Your app user id")
    trip_id: Optional[str] = Field(None, description="Client trip id (optional)")
    user_profile: Optional[Dict[str, Any]] = Field(None, description="Profile fields from frontend for travelers/contact")
    client_ref: Optional[str] = Field(None, description="Optional idempotency hint")


class FlightOrderRequest(BaseModel):
    flight_order: Dict[str, Any] = Field(..., description="Amadeus flight order request body")
    client_ref: Optional[str] = Field(None, description="Optional idempotency hint")


def _build_travelers(user_profile: Optional[Dict[str, Any]], adults: int, children: int) -> List[Dict[str, Any]]:
    up = user_profile or {}
    first = (up.get("first_name") or up.get("firstName") or "").strip() or "TEST"
    last = (up.get("last_name") or up.get("lastName") or "").strip() or "USER"
    email = (up.get("email") or "").strip() or "test@example.com"
    phone = (up.get("phone") or "").strip()

    base_trav = {
        "name": {"firstName": first, "lastName": last},
        "contact": {"emailAddress": email, "phones": ([{"deviceType": "MOBILE", "countryCallingCode": "66", "number": phone}] if phone else [])},
    }
    # Sandbox often accepts minimal travelers; keep DOB/gender if provided
    if up.get("dob"):
        base_trav["dateOfBirth"] = up.get("dob")
    if up.get("gender"):
        base_trav["gender"] = up.get("gender")

    travelers: List[Dict[str, Any]] = []
    tid = 1
    for _ in range(max(0, adults)):
        t = dict(base_trav)
        t["id"] = str(tid)
        travelers.append(t)
        tid += 1

    for _ in range(max(0, children)):
        t = dict(base_trav)
        t["id"] = str(tid)
        travelers.append(t)
        tid += 1

    if not travelers:
        base_trav["id"] = "1"
        travelers = [base_trav]

    return travelers


@router.post("/flight-order")
def create_flight_order(payload: FlightOrderRequest):
    """Low-level passthrough: frontend sends full flight-order body."""
    client = get_amadeus_booking_client()
    if not client:
        raise HTTPException(status_code=400, detail="Amadeus booking client not configured")

    try:
        ensure_booking_is_sandbox(client)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    try:
        resp = client.booking.flight_orders.post(payload.flight_order)
        data = getattr(resp, "data", None) if hasattr(resp, "data") else resp
        return {"ok": True, "sandbox": True, "data": data}
    except Exception as e:
        detail: Any = str(e)
        response = getattr(e, "response", None)
        if response is not None:
            body = getattr(response, "body", None) or getattr(response, "data", None)
            if body is not None:
                detail = body
        raise HTTPException(status_code=400, detail=detail)


@router.post("/create")
async def create_booking(
    payload: ConfirmBookingRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Create a booking record (pending payment). Does not book in Amadeus yet."""
    ctx = get_user_ctx(payload.user_id)
    current_plan = ctx.get("current_plan")
    if not current_plan:
        raise HTTPException(status_code=400, detail="No current_plan selected. Please select a choice first.")

    slots = ctx.get("last_travel_slots") or {}
    
    # Get trip title from context
    trip_title = ctx.get("trip_title") or slots.get("trip_title") or None
    
    # Calculate total price
    total_price = 0.0
    currency = "THB"
    if isinstance(current_plan, dict):
        total_price = float(current_plan.get("total_price") or current_plan.get("price") or 0)
        currency = current_plan.get("currency") or "THB"
        # ✅ Add trip_title to plan if not already present
        if trip_title and not current_plan.get("trip_title"):
            current_plan["trip_title"] = trip_title

    # Create booking record in database
    db = get_db()
    bookings = BookingsRepo(db)
    await bookings.ensure_indexes()

    booking = await bookings.create(
        user_id=user["_id"],
        trip_id=payload.trip_id,
        plan=current_plan,
        travel_slots=slots,
        user_profile=payload.user_profile or {},
        total_price=total_price,
        currency=currency,
        status="pending_payment",
        trip_title=trip_title,  # ✅ Store trip_title in booking
    )

    return {
        "ok": True,
        "booking_id": str(booking["_id"]),
        "status": "pending_payment",
        "message": "✅ สร้างการจองสำเร็จ กรุณาชำระเงินเพื่อยืนยันการจอง",
        "total_price": total_price,
        "currency": currency,
    }


@router.post("/confirm")
async def confirm_current_plan_booking(
    payload: ConfirmBookingRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """High-level booking: use the currently selected plan in server memory and book in TEST env.
    This is now used for payment confirmation - it will actually book in Amadeus Sandbox."""
    client = get_amadeus_booking_client()
    if not client:
        raise HTTPException(status_code=400, detail="Amadeus booking client not configured")

    try:
        ensure_booking_is_sandbox(client)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    ctx = get_user_ctx(payload.user_id)
    current_plan = ctx.get("current_plan")
    if not current_plan:
        raise HTTPException(status_code=400, detail="No current_plan selected. Please select a choice first.")

    flight_raw = (((current_plan.get("flight") or {}).get("raw")) if isinstance(current_plan, dict) else None)
    if not flight_raw:
        raise HTTPException(status_code=400, detail="Current plan has no flight offer to book.")

    slots = ctx.get("last_travel_slots") or {}
    adults = int(slots.get("adults") or 1)
    children = int(slots.get("children") or 0)

    travelers = _build_travelers(payload.user_profile, adults=adults, children=children)

    flight_order = {
        "data": {
            "type": "flight-order",
            "flightOffers": [flight_raw],
            "travelers": travelers,
        }
    }

    try:
        resp = client.booking.flight_orders.post(flight_order)
        data = getattr(resp, "data", None) if hasattr(resp, "data") else resp
        
        # Extract booking reference if available
        booking_ref = None
        if isinstance(data, dict):
            booking_ref = data.get("associatedRecords", [{}])[0].get("reference") if data.get("associatedRecords") else None
            if not booking_ref:
                booking_ref = data.get("id") or data.get("bookingReferenceId")
        
        message = "✅ จองสำเร็จ"
        if booking_ref:
            message += f"\n📋 หมายเลขการจอง: {booking_ref}"
        message += "\n(จองใน Amadeus Sandbox - สำหรับทดสอบเท่านั้น)"
        
        # ✅ Create Google Calendar event for confirmed booking
        try:
            from services.google_calendar_service import create_trip_calendar_event
            slots = ctx.get("last_travel_slots", {})
            trip_title = ctx.get("trip_title") or f"ทริปไป {slots.get('destination', 'Unknown')}"
            destination = slots.get("destination", "Unknown")
            start_date = slots.get("start_date")
            nights = slots.get("nights", 1)
            
            if start_date:
                calendar_event = await create_trip_calendar_event(
                    trip_title=trip_title,
                    destination=destination,
                    start_date=start_date,
                    nights=nights,
                    reminders_days_before=[7, 3, 1]
                )
                if calendar_event.get("ok"):
                    import logging
                    logging.info(f"Created calendar event for booking confirmation: {trip_title}")
        except Exception as e:
            import logging
            logging.warning(f"Failed to create calendar event for booking confirmation: {e}")
        
        return {
            "ok": True,
            "sandbox": True,
            "message": message,
            "data": data,
            "booking_reference": booking_ref,
        }
    except Exception as e:
        detail: Any = str(e)
        response = getattr(e, "response", None)
        if response is not None:
            body = getattr(response, "body", None) or getattr(response, "data", None)
            if body is not None:
                detail = body
        # Even if booking fails, return a helpful error
        raise HTTPException(status_code=400, detail={"message": "Booking failed", "detail": detail, "sandbox": True})


@router.post("/payment")
async def process_payment(
    booking_id: str = Query(..., description="Booking ID to process payment for"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Process payment for a booking. After payment, actually book in Amadeus Sandbox."""
    db = get_db()
    bookings = BookingsRepo(db)
    
    booking = await bookings.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if str(booking["user_id"]) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    if booking["status"] != "pending_payment":
        raise HTTPException(status_code=400, detail=f"Booking is not pending payment. Current status: {booking['status']}")

    # Mock payment processing (in real app, integrate with payment gateway)
    # For now, just simulate successful payment
    payment_result = {"ok": True, "paid": True, "charge_id": f"MOCK-{booking_id}"}
    
    # Now actually book in Amadeus Sandbox
    client = get_amadeus_booking_client()
    if not client:
        raise HTTPException(status_code=400, detail="Amadeus booking client not configured")

    try:
        ensure_booking_is_sandbox(client)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))

    plan = booking.get("plan", {})
    flight_raw = (((plan.get("flight") or {}).get("raw")) if isinstance(plan, dict) else None)
    hotel = plan.get("hotel") if isinstance(plan, dict) else None
    
    # Handle flight booking
    if flight_raw:
        travel_slots = booking.get("travel_slots", {})
        adults = int(travel_slots.get("adults") or 1)
        children = int(travel_slots.get("children") or 0)
        user_profile = booking.get("user_profile", {})

        travelers = _build_travelers(user_profile, adults=adults, children=children)

        flight_order = {
            "data": {
                "type": "flight-order",
                "flightOffers": [flight_raw],
                "travelers": travelers,
            }
        }

        try:
            resp = client.booking.flight_orders.post(flight_order)
            data = getattr(resp, "data", None) if hasattr(resp, "data") else resp
            
            # Extract booking reference
            booking_ref = None
            if isinstance(data, dict):
                booking_ref = data.get("associatedRecords", [{}])[0].get("reference") if data.get("associatedRecords") else None
                if not booking_ref:
                    booking_ref = data.get("id") or data.get("bookingReferenceId")
            
            # Update booking status
            await bookings.update_status(
                booking_id,
                status="confirmed",
                payment_status="paid",
                amadeus_booking_reference=booking_ref,
            )
            
            # ✅ Create Google Calendar event for confirmed booking
            try:
                from services.google_calendar_service import create_trip_calendar_event
                travel_slots = booking.get("travel_slots", {})
                trip_title = booking.get("plan", {}).get("trip_title") or f"ทริปไป {travel_slots.get('destination', 'Unknown')}"
                destination = travel_slots.get("destination", "Unknown")
                start_date = travel_slots.get("start_date")
                nights = travel_slots.get("nights", 1)
                
                if start_date:
                    calendar_event = await create_trip_calendar_event(
                        trip_title=trip_title,
                        destination=destination,
                        start_date=start_date,
                        nights=nights,
                        reminders_days_before=[7, 3, 1]  # Remind 7 days, 3 days, and 1 day before
                    )
                    # Store calendar event data in booking (for future Google Calendar API integration)
                    if calendar_event.get("ok"):
                        import logging
                        logging.info(f"Created calendar event for booking {booking_id}")
            except Exception as e:
                import logging
                logging.warning(f"Failed to create calendar event: {e}")
                # Continue without calendar event
            
            return {
                "ok": True,
                "sandbox": True,
                "message": "✅ ชำระเงินและจองสำเร็จ",
                "booking_reference": booking_ref,
                "status": "confirmed",
            }
        except Exception as e:
            # Payment succeeded but booking failed - mark payment as paid but booking as failed
            await bookings.update_status(
                booking_id,
                status="payment_failed",
                payment_status="paid",
            )
            detail: Any = str(e)
            response = getattr(e, "response", None)
            if response is not None:
                body = getattr(response, "body", None) or getattr(response, "data", None)
                if body is not None:
                    detail = body
            raise HTTPException(status_code=400, detail={"message": "Payment succeeded but booking failed", "detail": detail})
    
    # Handle hotel-only booking (for now, just mark as confirmed without actual Amadeus booking)
    # Note: Amadeus hotel booking API might require different handling
    elif hotel:
        # For hotel-only bookings, we'll just mark as confirmed
        # In the future, you might want to integrate with Amadeus hotel booking API
        booking_ref = f"HOTEL-{booking_id[:8].upper()}"
        
        await bookings.update_status(
            booking_id,
            status="confirmed",
            payment_status="paid",
            amadeus_booking_reference=booking_ref,
        )
        
        # ✅ Create Google Calendar event for confirmed hotel booking
        try:
            from services.google_calendar_service import create_trip_calendar_event
            travel_slots = booking.get("travel_slots", {})
            trip_title = booking.get("plan", {}).get("trip_title") or f"ทริปไป {travel_slots.get('destination', 'Unknown')}"
            destination = travel_slots.get("destination", "Unknown")
            start_date = travel_slots.get("start_date")
            nights = travel_slots.get("nights", 1)
            
            if start_date:
                calendar_event = await create_trip_calendar_event(
                    trip_title=trip_title,
                    destination=destination,
                    start_date=start_date,
                    nights=nights,
                    reminders_days_before=[7, 3, 1]
                )
                if calendar_event.get("ok"):
                    import logging
                    logging.info(f"Created calendar event for hotel booking {booking_id}: {trip_title}")
        except Exception as e:
            import logging
            logging.warning(f"Failed to create calendar event for hotel booking {booking_id}: {e}")
        
        return {
            "ok": True,
            "sandbox": True,
            "message": "✅ ชำระเงินและจองสำเร็จ (ที่พัก)",
            "booking_reference": booking_ref,
            "status": "confirmed",
        }
    
    else:
        raise HTTPException(status_code=400, detail="Booking has no flight or hotel offer to book.")


@router.get("/list")
async def list_bookings(
    user: Dict[str, Any] = Depends(get_current_user),
    status: Optional[str] = None,
):
    """Get all bookings for the current user."""
    db = get_db()
    bookings = BookingsRepo(db)
    
    booking_list = await bookings.get_by_user(user["_id"], status=status)
    
    # Convert ObjectId to string for JSON serialization
    for booking in booking_list:
        booking["_id"] = str(booking["_id"])
        if isinstance(booking.get("user_id"), ObjectId):
            booking["user_id"] = str(booking["user_id"])
    
    return {
        "ok": True,
        "bookings": booking_list,
        "count": len(booking_list),
    }


@router.post("/cancel")
async def cancel_booking(
    booking_id: str = Query(..., description="Booking ID to cancel"),
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Cancel a booking."""
    db = get_db()
    bookings = BookingsRepo(db)
    
    booking = await bookings.get_by_id(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if str(booking["user_id"]) != str(user["_id"]):
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Only allow cancellation if booking is pending_payment or confirmed
    current_status = booking.get("status")
    if current_status not in ["pending_payment", "confirmed"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot cancel booking with status: {current_status}. Only pending_payment or confirmed bookings can be cancelled."
        )
    
    # Update booking status to cancelled
    success = await bookings.update_status(
        booking_id,
        status="cancelled",
        notes="Cancelled by user"
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel booking")
    
    return {
        "ok": True,
        "message": "✅ ยกเลิกการจองสำเร็จ",
        "booking_id": booking_id,
        "status": "cancelled",
    }
