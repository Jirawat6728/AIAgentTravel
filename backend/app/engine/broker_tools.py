"""
Broker Tool Definitions — Pydantic models for the Travel Broker Agent's tool interface.

These are semantic wrappers over the underlying Amadeus/Google Maps MCP tools.
They are used in:
  - System prompt tool descriptions (so the LLM knows what tools exist)
  - Action log serialization for tool_call / tool_output messages
  - Type-safe parameter passing when tools are invoked

No changes are made to the underlying MCPToolExecutor or Amadeus connectors.
"""

from __future__ import annotations
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input schemas (what the broker sends TO the tool)
# ---------------------------------------------------------------------------

class SearchFlightsTool(BaseModel):
    """Search for available flights between two airports."""
    destination: str = Field(..., description="Destination city or IATA airport code (e.g. 'Phuket' or 'HKT')")
    origin: str = Field(default="Bangkok", description="Origin city or IATA airport code (e.g. 'Bangkok' or 'BKK')")
    date: str = Field(..., description="Departure date in YYYY-MM-DD format")
    return_date: Optional[str] = Field(default=None, description="Return date for round trips (YYYY-MM-DD). None for one-way.")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of adult passengers")
    cabin_class: Literal["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"] = Field(
        default="ECONOMY",
        description="Preferred cabin class"
    )
    direct_only: bool = Field(default=False, description="If True, search non-stop flights only")


class SearchHotelsTool(BaseModel):
    """Search for available hotels at the destination."""
    location: str = Field(..., description="City name or area (e.g. 'Phuket', 'Myeongdong Seoul')")
    check_in: str = Field(..., description="Check-in date in YYYY-MM-DD format")
    check_out: str = Field(..., description="Check-out date in YYYY-MM-DD format")
    guests: int = Field(default=1, ge=1, description="Number of guests")
    preferences: Dict[str, Any] = Field(
        default_factory=dict,
        description="Broker-curated filters derived from user's travel_preferences: e.g. {'family_friendly': True, 'near_attractions': ['MBK', 'Siam'], 'budget_level': 'mid'}"
    )


class SearchTransfersTool(BaseModel):
    """Search for airport-to-hotel ground transfers."""
    origin: str = Field(..., description="Pickup location (e.g. 'Suvarnabhumi Airport')")
    destination: str = Field(..., description="Drop-off location (e.g. 'hotel name or area')")
    date: str = Field(..., description="Transfer date in YYYY-MM-DD format")
    passengers: int = Field(default=1, ge=1)


class ConfirmBookingTool(BaseModel):
    """Confirm and lock a selected option for booking."""
    item_id: str = Field(..., description="ID of the selected option (from options_pool)")
    slot: Literal["flights_outbound", "flights_inbound", "accommodation", "ground_transport"] = Field(
        ..., description="Which segment this booking confirmation applies to"
    )
    user_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Booker details: name, passport, contact, payment_method_id, etc."
    )


# ---------------------------------------------------------------------------
# Output schemas (what the tool returns TO the broker)
# ---------------------------------------------------------------------------

class FlightSearchResult(BaseModel):
    """Summary of a flight search result (used in tool_output messages)."""
    tool: str = "search_flights"
    result_count: int
    cheapest_price: Optional[float] = None
    cheapest_currency: Optional[str] = None
    fastest_duration_minutes: Optional[int] = None
    has_direct_option: bool = False
    segments: List[Dict[str, Any]] = Field(default_factory=list)


class HotelSearchResult(BaseModel):
    """Summary of a hotel search result."""
    tool: str = "search_hotels"
    result_count: int
    cheapest_price_per_night: Optional[float] = None
    currency: Optional[str] = None
    location: Optional[str] = None
    segments: List[Dict[str, Any]] = Field(default_factory=list)


class BookingConfirmationResult(BaseModel):
    """Result of confirming a booking."""
    tool: str = "confirm_booking"
    success: bool
    booking_reference: Optional[str] = None
    slot: Optional[str] = None
    message: Optional[str] = None


# ---------------------------------------------------------------------------
# Tool registry — used in system prompt descriptions
# ---------------------------------------------------------------------------

BROKER_TOOLS_DESCRIPTION = """
Available Broker Tools (call these when user expresses travel intent):

1. search_flights(destination, origin, date, return_date, passengers, cabin_class, direct_only)
   → Searches Amadeus for available flights. Always confirm parameters with user before calling.

2. search_hotels(location, check_in, check_out, guests, preferences)
   → Searches for hotels near attractions based on user preferences. Apply travel_preferences filters.

3. search_transfers(origin, destination, date, passengers)
   → Finds airport-to-hotel ground transfer options.

4. confirm_booking(item_id, slot, user_details)
   → Locks the user's selected option and creates the booking record.
   → ALWAYS ask user to confirm all details before calling this tool.
"""


def summarize_flight_results(options_pool: List[Dict[str, Any]]) -> FlightSearchResult:
    """Create a summary FlightSearchResult from an options_pool list."""
    if not options_pool:
        return FlightSearchResult(result_count=0)
    prices = [o.get("price", {}).get("total") for o in options_pool if o.get("price", {}).get("total")]
    durations = [o.get("duration_minutes") for o in options_pool if o.get("duration_minutes")]
    has_direct = any(o.get("non_stop") or o.get("direct_flight") for o in options_pool)
    return FlightSearchResult(
        result_count=len(options_pool),
        cheapest_price=min(float(p) for p in prices) if prices else None,
        cheapest_currency=options_pool[0].get("price", {}).get("currency") if options_pool else None,
        fastest_duration_minutes=min(durations) if durations else None,
        has_direct_option=has_direct,
    )


def summarize_hotel_results(options_pool: List[Dict[str, Any]]) -> HotelSearchResult:
    """Create a summary HotelSearchResult from an options_pool list."""
    if not options_pool:
        return HotelSearchResult(result_count=0)
    prices = [o.get("price_per_night") or o.get("price", {}).get("total") for o in options_pool]
    prices = [float(p) for p in prices if p]
    return HotelSearchResult(
        result_count=len(options_pool),
        cheapest_price_per_night=min(prices) if prices else None,
        currency=options_pool[0].get("currency") or options_pool[0].get("price", {}).get("currency") if options_pool else None,
    )
