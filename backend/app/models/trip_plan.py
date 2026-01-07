"""
Trip Plan Models with Strict Pydantic V2 Validation
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


class Segment(BaseModel):
    """
    Single segment in a trip plan slot
    Strict validation with Pydantic V2
    """
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
        if req.get('origin') and req.get('destination') and req.get('date'):
            return True
        if req.get('location') and req.get('check_in') and req.get('check_out'):
            return True
        return False


class TripPlan(BaseModel):
    """
    Complete trip plan with 3 fixed slots
    Strict validation ensures data integrity
    """
    flights: List[Segment] = Field(
        default_factory=list,
        description="Flight segments"
    )
    accommodations: List[Segment] = Field(
        default_factory=list,
        description="Accommodation segments"
    )
    ground_transport: List[Segment] = Field(
        default_factory=list,
        description="Ground transport segments"
    )
    
    @model_validator(mode='after')
    def validate_trip_plan(self) -> 'TripPlan':
        """Validate trip plan structure"""
        for slot_name in ['flights', 'accommodations', 'ground_transport']:
            segments = getattr(self, slot_name)
            if not isinstance(segments, list):
                raise ValueError(f"{slot_name} must be a list")
            for segment in segments:
                if not isinstance(segment, Segment):
                    raise ValueError(f"Invalid segment type in {slot_name}")
        return self
    
    def get_active_segment(self) -> Optional[tuple[str, int, Segment]]:
        """
        Get the first non-completed segment
        Returns: (slot_name, segment_index, segment) or None
        """
        for slot_name in ['flights', 'accommodations', 'ground_transport']:
            segments = getattr(self, slot_name)
            for idx, segment in enumerate(segments):
                if not segment.is_complete():
                    return (slot_name, idx, segment)
        return None
    
    def is_complete(self) -> bool:
        """Check if all segments are completed"""
        for slot_name in ['flights', 'accommodations', 'ground_transport']:
            segments = getattr(self, slot_name)
            for segment in segments:
                if not segment.is_complete():
                    return False
        return True
