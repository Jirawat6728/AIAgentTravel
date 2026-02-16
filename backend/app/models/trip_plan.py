"""
โมเดลแผนการเดินทาง (Trip Plan) ตรวจสอบด้วย Pydantic V2
โครงสร้างลำดับชั้น: การเดินทาง (เครื่องบิน/รถ/ทั้งสอง) และที่พัก
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field, field_validator, model_validator


class SegmentStatus(str, Enum):
    """Strict status enum for segments"""
    PENDING = "pending"
    SEARCHING = "searching"
    SELECTING = "selecting"
    CONFIRMED = "confirmed"


class TravelMode(str, Enum):
    """Modes of travel"""
    FLIGHT_ONLY = "flight_only"
    CAR_ONLY = "car_only"
    BOTH = "both"


class Segment(BaseModel):
    """
    Single segment in a trip plan slot
    Strict validation with Pydantic V2
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    status: SegmentStatus = Field(
        default=SegmentStatus.PENDING,
        description="Current status of the segment"
    )
    requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Requirements needed to search for this segment"
    )
    options_pool: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of search results waiting for user selection"
    )
    selected_option: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The option that user has selected"
    )
    
    @field_validator('status', mode='before')
    @classmethod
    def validate_status(cls, v: Any) -> SegmentStatus:
        """Validate and convert status to enum"""
        if isinstance(v, SegmentStatus):
            return v
        if isinstance(v, str):
            try:
                return SegmentStatus(v.lower())
            except ValueError:
                raise ValueError(f"status must be one of {[s.value for s in SegmentStatus]}")
        raise ValueError(f"Invalid status type: {type(v)}")
    
    @model_validator(mode='after')
    def validate_state(self) -> 'Segment':
        """Validate segment state consistency"""
        if self.status == SegmentStatus.CONFIRMED and self.selected_option is None:
            raise ValueError("Segment with status 'confirmed' must have selected_option")
        if self.status == SegmentStatus.SELECTING and len(self.options_pool) == 0:
            raise ValueError("Segment with status 'selecting' must have options in options_pool")
        return self
    
    def is_complete(self) -> bool:
        """Check if segment is completed"""
        return self.status == SegmentStatus.CONFIRMED and self.selected_option is not None
    
    def needs_search(self) -> bool:
        """Check if segment needs to be searched"""
        if self.status == SegmentStatus.CONFIRMED:
            return False
        if len(self.options_pool) > 0:
            return False
        # Check if requirements are complete
        req = self.requirements
        
        # For Flights/Transport: origin, destination, date/departure_date
        has_origin = bool(req.get('origin'))
        has_dest = bool(req.get('destination'))
        has_date = bool(req.get('date') or req.get('departure_date'))
        
        if has_origin and has_dest and has_date:
            return True
            
        # For Accommodation: location, check_in, check_out
        has_loc = bool(req.get('location'))
        has_check_in = bool(req.get('check_in'))
        has_check_out = bool(req.get('check_out'))
        
        if has_loc and has_check_in and has_check_out:
            return True
            
        return False


class FlightGroup(BaseModel):
    """
    Grouping for flight segments: Outbound (Departure) and Inbound (Return)
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    outbound: List[Segment] = Field(default_factory=list, description="Outbound flight segments")
    inbound: List[Segment] = Field(default_factory=list, description="Inbound/Return flight segments")
    
    @model_validator(mode='before')
    @classmethod
    def migrate_legacy_flights(cls, v: Any) -> Any:
        """
        Migrate legacy List[Segment] to FlightGroup(outbound=..., inbound=[])
        This handles the Validation Error when loading old sessions.
        """
        if isinstance(v, list):
            # Assume all legacy segments are outbound
            return {'outbound': v, 'inbound': []}
        return v

    @property
    def all_segments(self) -> List[Segment]:
        """Get all segments as a flat list"""
        return self.outbound + self.inbound

    def is_complete(self) -> bool:
        outbound_ok = all(s.is_complete() for s in self.outbound)
        inbound_ok = all(s.is_complete() for s in self.inbound)
        # If list is empty, it's considered complete (not needed) unless we want to enforce presence
        # But usually CreateItinerary populates them.
        return outbound_ok and inbound_ok


class TravelSlot(BaseModel):
    """
    Grouping for travel-related segments
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    mode: TravelMode = Field(default=TravelMode.BOTH, description="Preferred mode of travel")
    trip_type: str = Field(default="round_trip", description="Trip type: 'one_way' or 'round_trip'")
    flights: FlightGroup = Field(default_factory=FlightGroup, description="Flight segments group")
    ground_transport: List[Segment] = Field(default_factory=list, description="Ground transport segments (Car)")

    def is_complete(self) -> bool:
        # Check based on mode
        if self.mode == TravelMode.FLIGHT_ONLY:
            return self.flights.is_complete() and (len(self.flights.outbound) > 0)
        elif self.mode == TravelMode.CAR_ONLY:
            return all(s.is_complete() for s in self.ground_transport) and len(self.ground_transport) > 0
        else: # BOTH
            flights_ok = self.flights.is_complete() and (len(self.flights.outbound) > 0)
            ground_ok = all(s.is_complete() for s in self.ground_transport) and len(self.ground_transport) > 0
            return flights_ok and ground_ok


class AccommodationSlot(BaseModel):
    """
    Grouping for accommodation-related segments
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    segments: List[Segment] = Field(default_factory=list, description="Accommodation segments")

    def is_complete(self) -> bool:
        return all(s.is_complete() for s in self.segments) and len(self.segments) > 0


# =============================================================================
# Production-Grade Hotel Data Models
# =============================================================================

class HotelPricing(BaseModel):
    """Detailed pricing breakdown - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    total_amount: float
    base_amount: Optional[float] = None
    taxes_and_fees: float = 0.0
    currency: str
    price_per_night: float

class HotelPolicy(BaseModel):
    """Policies and Terms - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    is_refundable: bool = False
    cancellation_deadline: Optional[str] = None
    penalty_amount: Optional[str] = None
    check_in_time: Optional[str] = None
    check_out_time: Optional[str] = None
    meal_plan: str = "Room Only"

class HotelRoom(BaseModel):
    """Room specifications - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    room_type: str = "Standard"
    description: Optional[str] = None
    bed_type: Optional[str] = None
    bed_quantity: int = 0
    occupancy: int = 2

class HotelBookingDetails(BaseModel):
    """Core booking information used for creating reservations - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    offer_id: str
    check_in_date: str
    check_out_date: str
    guests: int
    pricing: HotelPricing
    room: HotelRoom
    policies: HotelPolicy

class HotelAmenities(BaseModel):
    """Structured amenities for filtering - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    # Core
    has_wifi: bool = False
    has_parking: bool = False
    has_air_conditioning: bool = False
    # Wellness & Leisure
    has_fitness: bool = False
    has_pool: bool = False
    has_spa: bool = False
    # Full list for display
    original_list: List[str] = Field(default_factory=list)

class HotelLocation(BaseModel):
    """Geo and Contextual location data - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    place_id: Optional[str] = None
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_to_airport: Optional[str] = None
    nearby_transport: Optional[str] = None

class HotelVisuals(BaseModel):
    """Images and Reviews - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    image_urls: List[str] = Field(default_factory=list)
    review_score: Optional[float] = None
    review_count: Optional[int] = None

class AIPerspective(BaseModel):
    """AI Generated Insights - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    vibe_check: Optional[str] = None
    value_reasoning: Optional[str] = None

class MergedHotelOption(BaseModel):
    """
    Production-Grade Merged Hotel Object
    Combines Amadeus (Booking) + Google (Content) + AI (Insight)
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    # Identity
    hotel_id: str
    hotel_name: str
    chain_code: Optional[str] = None
    star_rating: Optional[int] = None
    
    # Groups
    booking: HotelBookingDetails
    amenities: HotelAmenities
    location: HotelLocation
    visuals: HotelVisuals
    ai: Optional[AIPerspective] = None
    
    source: str = "amadeus_google_merged"
    tags: List[str] = Field(default_factory=list)
    is_recommended: bool = False



class TripPlan(BaseModel):
    """
    Complete trip plan with Hierarchical Structure
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    travel: TravelSlot = Field(default_factory=TravelSlot, description="Travel arrangements")
    accommodation: AccommodationSlot = Field(default_factory=AccommodationSlot, description="Accommodation arrangements")
    
    def is_complete(self) -> bool:
        """Check if all parts of the plan are complete"""
        return self.travel.is_complete() and self.accommodation.is_complete()
