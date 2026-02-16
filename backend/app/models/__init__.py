"""
โมเดล Pydantic V2 แบบเข้มงวด
จัดการ state แบบ type-safe
"""

from app.models.trip_plan import TripPlan, Segment, SegmentStatus
from app.models.session import UserSession
from app.models.actions import ControllerAction, ActionLog, ActionType

__all__ = [
    "TripPlan",
    "Segment",
    "SegmentStatus",
    "UserSession",
    "ControllerAction",
    "ActionLog",
    "ActionType"
]
