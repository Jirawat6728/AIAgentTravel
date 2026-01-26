"""
User Session Model with Strict Validation
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

from app.models.trip_plan import TripPlan


class UserSession(BaseModel):
    """
    User session with trip plan state
    Strict validation ensures session integrity
    extra='allow' to handle unexpected fields from external APIs
    
    Structure:
    - trip_id: สำหรับ 1 ทริป (1 trip = หลาย chat ได้)
    - chat_id: สำหรับแต่ละแชท (1 chat = 1 chat_id)
    - session_id: ใช้ chat_id เป็น session_id (backward compatible)
    """
    model_config = {"extra": "allow"}
    
    session_id: str = Field(..., min_length=1, description="Unique session identifier (uses chat_id)")
    user_id: str = Field(..., min_length=1, description="User identifier")
    trip_id: Optional[str] = Field(
        default=None,
        description="Trip identifier (1 trip can have multiple chats)"
    )
    chat_id: Optional[str] = Field(
        default=None,
        description="Chat identifier (1 chat = 1 chat_id)"
    )
    trip_plan: TripPlan = Field(
        default_factory=TripPlan,
        description="Current trip plan state"
    )
    title: Optional[str] = Field(
        default=None,
        description="Chat title (generated from first conversation)"
    )
    last_updated: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Last update timestamp (ISO format)"
    )
    
    @field_validator('session_id', 'user_id', 'trip_id', 'chat_id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Validate ID fields"""
        if v is None:
            return v  # Allow None for optional fields
        if not v or not v.strip():
            raise ValueError("ID cannot be empty")
        return v.strip()
    
    @field_validator('last_updated')
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate timestamp format"""
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
            return v
        except ValueError:
            raise ValueError(f"Invalid timestamp format: {v}")
    
    def update_timestamp(self):
        """Update the last_updated timestamp"""
        self.last_updated = datetime.utcnow().isoformat()
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return self.model_dump()
    
    @classmethod
    def from_dict(cls, data: dict) -> 'UserSession':
        """Create UserSession from dictionary with validation"""
        try:
            return cls(**data)
        except Exception as e:
            raise ValueError(f"Invalid session data: {e}") from e
