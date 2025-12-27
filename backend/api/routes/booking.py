from __future__ import annotations

from typing import Any, Dict, Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.config import get_amadeus_booking_client
from core.context import get_user_ctx
from core.safety import ensure_booking_is_sandbox

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


@router.post("/confirm")
def confirm_current_plan_booking(payload: ConfirmBookingRequest):
    """High-level booking: use the currently selected plan in server memory and book in TEST env."""
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
