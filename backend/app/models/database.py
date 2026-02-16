"""
โมเดลและสคีมาฐานข้อมูล MongoDB
ออกแบบสำหรับ AI Travel Agent ระดับ production
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from bson import ObjectId
from pymongo import IndexModel

from app.models.trip_plan import TripPlan, Segment, SegmentStatus


class PyObjectId(ObjectId):
    """Custom ObjectId for Pydantic V2"""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        from pydantic_core import core_schema
        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(cls.validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x)
            ),
        )
    
    @classmethod
    def validate(cls, v):
        if isinstance(v, ObjectId):
            return v
        if isinstance(v, str):
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)
        raise ValueError("Invalid ObjectId type")


# =============================================================================
# Family member (for co-travelers / booking)
# =============================================================================
class FamilyMember(BaseModel):
    """Family member for co-traveler selection when booking (adult or child). Same detail as main booker."""
    id: Optional[str] = Field(default=None, description="Unique id for frontend (e.g. uuid)")
    type: str = Field(..., description="adult or child")
    first_name: str = Field(..., description="First name")
    last_name: str = Field(..., description="Last name")
    first_name_th: Optional[str] = Field(default=None, description="First name in Thai")
    last_name_th: Optional[str] = Field(default=None, description="Last name in Thai")
    date_of_birth: Optional[str] = Field(default=None, description="YYYY-MM-DD (recommended for child)")
    gender: Optional[str] = Field(default=None, description="Gender: M, F, O")
    national_id: Optional[str] = Field(default=None, description="National ID (13 digits)")
    passport_no: Optional[str] = Field(default=None, description="Passport number (for international)")
    passport_expiry: Optional[str] = Field(default=None, description="Passport expiry YYYY-MM-DD")
    passport_issue_date: Optional[str] = Field(default=None, description="Passport issue date YYYY-MM-DD")
    passport_issuing_country: Optional[str] = Field(default=None, description="Passport issuing country (e.g. TH)")
    passport_given_names: Optional[str] = Field(default=None, description="Given names as on passport (English)")
    passport_surname: Optional[str] = Field(default=None, description="Surname as on passport (English)")
    place_of_birth: Optional[str] = Field(default=None, description="Place of birth (city, country)")
    passport_type: Optional[str] = Field(default="N", description="Passport type: N, D, O, S")
    nationality: Optional[str] = Field(default=None, description="Nationality code (e.g. TH)")

    model_config = {"extra": "allow"}


# =============================================================================
# User Collection
# =============================================================================
class User(BaseModel):
    """
    User model for MongoDB with Brain/Memory support
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(default=None, description="User email")
    name: Optional[str] = Field(default=None, description="User name")
    full_name: Optional[str] = Field(default=None, description="Full name")
    first_name: Optional[str] = Field(default=None, description="First name")
    last_name: Optional[str] = Field(default=None, description="Last name")
    first_name_th: Optional[str] = Field(default=None, description="First name in Thai")
    last_name_th: Optional[str] = Field(default=None, description="Last name in Thai")
    phone: Optional[str] = Field(default=None, description="Phone number")
    dob: Optional[str] = Field(default=None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(default=None, description="Gender: M, F, OTHER, or custom value")
    national_id: Optional[str] = Field(default=None, description="National ID Card number")
    profile_image: Optional[str] = Field(default=None, description="Profile image URL")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences (auto-learned)")
    # Authentication fields
    auth_provider: Optional[str] = Field(default=None, description="Authentication provider: 'firebase', 'google', 'email'")
    email_verified: Optional[bool] = Field(default=False, description="Email verification status")
    email_verification_token: Optional[str] = Field(default=None, description="Email verification token")
    email_verification_sent_at: Optional[datetime] = Field(default=None, description="When verification email was sent")
    # Phone OTP (for change phone)
    phone_pending: Optional[str] = Field(default=None, description="New phone number pending OTP verification")
    phone_verification_otp: Optional[str] = Field(default=None, description="OTP sent to phone")
    phone_verification_sent_at: Optional[datetime] = Field(default=None, description="When OTP was sent")
    is_admin: Optional[bool] = Field(default=False, description="Admin user flag")
    # Passport information (for international flights)
    passport_no: Optional[str] = Field(default=None, description="Passport number")
    passport_expiry: Optional[str] = Field(default=None, description="Passport expiry date (YYYY-MM-DD)")
    passport_issue_date: Optional[str] = Field(default=None, description="Passport issue date (YYYY-MM-DD)")
    passport_issuing_country: Optional[str] = Field(default=None, description="Country that issued the passport (ISO country code)")
    passport_given_names: Optional[str] = Field(default=None, description="Given names as shown on passport (English)")
    passport_surname: Optional[str] = Field(default=None, description="Surname as shown on passport (English)")
    place_of_birth: Optional[str] = Field(default=None, description="Place of birth (city, country)")
    passport_type: Optional[str] = Field(default="N", description="Passport type: N=Normal, D=Diplomatic, O=Official, S=Service")
    # Visa information (for international travel)
    visa_type: Optional[str] = Field(default=None, description="Visa type: TOURIST, BUSINESS, STUDENT, WORK, TRANSIT, VISA_FREE, ETA, EVISA, OTHER")
    visa_number: Optional[str] = Field(default=None, description="Visa number")
    visa_issuing_country: Optional[str] = Field(default=None, description="Country that issued the visa (ISO country code)")
    visa_issue_date: Optional[str] = Field(default=None, description="Visa issue date (YYYY-MM-DD)")
    visa_expiry_date: Optional[str] = Field(default=None, description="Visa expiry date (YYYY-MM-DD)")
    visa_entry_type: Optional[str] = Field(default="S", description="Visa entry type: S=Single Entry, M=Multiple Entry")
    visa_purpose: Optional[str] = Field(default="T", description="Visa purpose: T=Tourism, B=Business, S=Study, W=Work, O=Other")
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(default=None, description="Emergency contact full name")
    emergency_contact_phone: Optional[str] = Field(default=None, description="Emergency contact phone number")
    emergency_contact_relation: Optional[str] = Field(default=None, description="Emergency contact relation: SPOUSE, PARENT, FRIEND, OTHER")
    emergency_contact_email: Optional[str] = Field(default=None, description="Emergency contact email")
    hotel_number_of_guests: Optional[int] = Field(default=1, description="Number of guests (including main guest)")
    # Family members (co-travelers for booking: adults + children)
    family: List[FamilyMember] = Field(default_factory=list, description="List of family members (adult/child) for co-traveler selection")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_admin: bool = Field(default=False, description="Is admin/test user")

class Memory(BaseModel):
    """Memory document for AI Agent - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="User identifier")
    content: str = Field(..., description="The actual memory content")
    category: str = Field(default="preference", description="Category: preference, fact, past_trip")
    importance: int = Field(default=1, ge=1, le=5, description="Importance score (1-5)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# Session Collection
# =============================================================================
class SessionDocument(BaseModel):
    """Session document for MongoDB - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "arbitrary_types_allowed": True,
        "json_schema_extra": {
            "example": {
                "session_id": "user123::chat1",
                "user_id": "user123",
                "trip_plan": {
                    "flights": [],
                    "accommodations": [],
                    "ground_transport": []
                }
            }
        }
    }
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(..., description="Unique session identifier (uses chat_id)")
    user_id: str = Field(..., description="User identifier")
    trip_id: Optional[str] = Field(default=None, description="Trip identifier (1 trip can have multiple chats)")
    chat_id: Optional[str] = Field(default=None, description="Chat identifier (1 chat = 1 chat_id)")
    trip_plan: Dict[str, Any] = Field(..., description="Trip plan as dictionary")
    title: Optional[str] = Field(default=None, description="Chat title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    popular_destinations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Popular destinations when user searches 'all' in destination")
    
    @classmethod
    def from_user_session(cls, session) -> "SessionDocument":
        """
        Convert UserSession to SessionDocument
        ✅ CRITICAL: trip_plan.model_dump() includes all raw data (options_pool, selected_option)
        """
        try:
            trip_plan_dict = session.trip_plan.model_dump() if session.trip_plan else {}
            
            # Verify trip_plan contains raw data
            if trip_plan_dict:
                segments = (
                    trip_plan_dict.get("travel", {}).get("flights", {}).get("outbound", []) +
                    trip_plan_dict.get("travel", {}).get("flights", {}).get("inbound", []) +
                    trip_plan_dict.get("accommodation", {}).get("segments", []) +
                    trip_plan_dict.get("travel", {}).get("ground_transport", [])
                )
                # trip_plan.model_dump() should include all fields including options_pool and selected_option
                # This is verified by Pydantic's model_dump() method
            
            popular = getattr(session, "popular_destinations", None)
            return cls(
                session_id=session.session_id,
                user_id=session.user_id,
                trip_id=session.trip_id,
                chat_id=session.chat_id,
                trip_plan=trip_plan_dict,
                title=session.title,
                last_updated=datetime.fromisoformat(session.last_updated.replace('Z', '+00:00')),
                popular_destinations=popular
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error converting UserSession to SessionDocument: {e}", exc_info=True)
            # Return with empty trip_plan as fallback
            return cls(
                session_id=session.session_id,
                user_id=session.user_id,
                trip_id=session.trip_id,
                chat_id=session.chat_id,
                trip_plan={},
                title=session.title,
                last_updated=datetime.fromisoformat(session.last_updated.replace('Z', '+00:00'))
            )
    
    def to_user_session(self):
        """Convert SessionDocument to UserSession"""
        from app.models.session import UserSession
        return UserSession(
            session_id=self.session_id,
            user_id=self.user_id,
            trip_id=self.trip_id,
            chat_id=self.chat_id,
            trip_plan=TripPlan(**self.trip_plan),
            title=self.title,
            last_updated=self.last_updated.isoformat(),
            popular_destinations=getattr(self, "popular_destinations", None)
        )


# =============================================================================
# Conversation History Collection
# =============================================================================
class Message(BaseModel):
    """Single message in conversation - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation history document - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="List of messages")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# Booking Collection
# =============================================================================
class Booking(BaseModel):
    """Confirmed booking document - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {
        "extra": "allow",
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }
    
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    booking_id: str = Field(..., description="Unique booking identifier")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    trip_plan: Dict[str, Any] = Field(..., description="Complete trip plan")
    status: str = Field(default="confirmed", description="Booking status")
    total_price: Optional[float] = Field(default=None, description="Total booking price")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    confirmed_at: Optional[datetime] = Field(default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# MongoDB Indexes
# =============================================================================
SESSION_INDEXES = [
    IndexModel([("session_id", 1)], unique=True),
    IndexModel([("user_id", 1)]),
    IndexModel([("last_updated", -1)]),
    IndexModel([("user_id", 1), ("last_updated", -1)])
]

USER_INDEXES = [
    IndexModel([("user_id", 1)], unique=True),
    IndexModel([("email", 1)], unique=True, sparse=True),
    IndexModel([("last_active", -1)])
]

CONVERSATION_INDEXES = [
    IndexModel([("session_id", 1)]),
    IndexModel([("user_id", 1)]),
    IndexModel([("updated_at", -1)]),
    IndexModel([("session_id", 1), ("updated_at", -1)])
]

BOOKING_INDEXES = [
    IndexModel([("booking_id", 1)], unique=True, sparse=True),  # Sparse: ignore null values
    IndexModel([("user_id", 1)]),
    IndexModel([("status", 1)]),
    IndexModel([("created_at", -1)]),
    IndexModel([("user_id", 1), ("created_at", -1)])
]

# บัตรที่บันทึกไว้ต่อ User (Omise customer_id + cards)
SAVED_CARDS_INDEXES = [
    IndexModel([("user_id", 1)], unique=True),
    IndexModel([("updated_at", -1)]),
]

MEMORY_INDEXES = [
    # ✅ SECURITY: Index on user_id for fast queries and data isolation
    IndexModel([("user_id", 1)], name="user_id_idx"),
    # Index on importance for sorting
    IndexModel([("importance", -1)], name="importance_idx"),
    # Compound index for user-specific memory queries (user_id + importance)
    IndexModel([("user_id", 1), ("importance", -1)], name="user_importance_idx"),
    # Index on category for filtering
    IndexModel([("category", 1)], name="category_idx"),
    # Index on last_accessed for cleanup of old memories
    IndexModel([("last_accessed", -1)], name="last_accessed_idx"),
    IndexModel([("user_id", 1)]),
    IndexModel([("category", 1)]),
    IndexModel([("created_at", -1)]),
    IndexModel([("user_id", 1), ("created_at", -1)])
]

