"""
MongoDB Database Models and Schemas
Production-grade database design for AI Travel Agent
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
# User Collection
# =============================================================================
class User(BaseModel):
    """User model for MongoDB with Brain/Memory support"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="Unique user identifier")
    email: Optional[str] = Field(default=None, description="User email")
    name: Optional[str] = Field(default=None, description="User name")
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences (auto-learned)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Memory(BaseModel):
    """Memory document for AI Agent"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: str = Field(..., description="User identifier")
    content: str = Field(..., description="The actual memory content")
    category: str = Field(default="preference", description="Category: preference, fact, past_trip")
    importance: int = Field(default=1, ge=1, le=5, description="Importance score (1-5)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# =============================================================================
# Session Collection
# =============================================================================
class SessionDocument(BaseModel):
    """Session document for MongoDB"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="User identifier")
    trip_plan: Dict[str, Any] = Field(..., description="Trip plan as dictionary")
    title: Optional[str] = Field(default=None, description="Chat title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
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
    
    @classmethod
    def from_user_session(cls, session) -> "SessionDocument":
        """Convert UserSession to SessionDocument"""
        return cls(
            session_id=session.session_id,
            user_id=session.user_id,
            trip_plan=session.trip_plan.model_dump(),
            title=session.title,
            last_updated=datetime.fromisoformat(session.last_updated.replace('Z', '+00:00'))
        )
    
    def to_user_session(self):
        """Convert SessionDocument to UserSession"""
        from app.models.session import UserSession
        return UserSession(
            session_id=self.session_id,
            user_id=self.user_id,
            trip_plan=TripPlan(**self.trip_plan),
            title=self.title,
            last_updated=self.last_updated.isoformat()
        )


# =============================================================================
# Conversation History Collection
# =============================================================================
class Message(BaseModel):
    """Single message in conversation"""
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Conversation(BaseModel):
    """Conversation history document"""
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="List of messages")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


# =============================================================================
# Booking Collection
# =============================================================================
class Booking(BaseModel):
    """Confirmed booking document"""
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
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


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
    IndexModel([("booking_id", 1)], unique=True),
    IndexModel([("session_id", 1)]),
    IndexModel([("user_id", 1)]),
    IndexModel([("status", 1)]),
    IndexModel([("created_at", -1)]),
    IndexModel([("user_id", 1), ("created_at", -1)])
]

MEMORY_INDEXES = [
    IndexModel([("user_id", 1)]),
    IndexModel([("category", 1)]),
    IndexModel([("created_at", -1)]),
    IndexModel([("user_id", 1), ("created_at", -1)])
]

