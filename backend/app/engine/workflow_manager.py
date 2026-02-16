"""Slot/segment management สำหรับ Amadeus (flights, hotels, transfers). ไม่มี Workflow/PlanChoiceCard."""
from __future__ import annotations
from typing import Any, Dict, List, Tuple
from enum import Enum

from app.models.trip_plan import Segment, TripPlan, SegmentStatus
from app.core.logging import get_logger
from app.core.exceptions import AgentException

logger = get_logger(__name__)


class SlotType(str, Enum):
    """Travel slot types (Amadeus)."""
    FLIGHTS_OUTBOUND = "flights_outbound"
    FLIGHTS_INBOUND = "flights_inbound"
    ACCOMMODATION = "accommodation"
    GROUND_TRANSPORT = "ground_transport"


class SlotManager:
    """จัดการ segment (slot) สำหรับ Amadeus: flights, hotels, transfers."""
    
    def __init__(self):
        logger.info("SlotManager initialized")
    
    def get_segment(
        self,
        trip_plan: TripPlan,
        slot_name: str,
        segment_index: int,
        create_if_missing: bool = False
    ) -> Tuple[Segment, List[Segment]]:
        """Get segment from trip plan."""
        slot_name = self._normalize_slot_name(slot_name)
        segments = self._get_segments_list(trip_plan, slot_name)
        if not segments:
            raise AgentException(f"No segments found for slot: {slot_name}")
        if segment_index < 0:
            raise AgentException(f"Invalid segment_index: {segment_index}")
        if segment_index >= len(segments):
            if create_if_missing:
                new_segment = Segment()
                segments.append(new_segment)
                return (new_segment, segments)
            raise AgentException(f"Segment index {segment_index} out of range for {slot_name}")
        return (segments[segment_index], segments)
    
    def _normalize_slot_name(self, slot_name: str) -> str:
        slot_name = slot_name.lower().strip()
        aliases = {
            "flights": "flights_outbound", "flight": "flights_outbound",
            "hotels": "accommodation", "hotel": "accommodation",
            "accommodations": "accommodation",
            "transfers": "ground_transport", "transfer": "ground_transport",
            "transport": "ground_transport", "ground": "ground_transport"
        }
        return aliases.get(slot_name, slot_name)
    
    def _get_segments_list(self, trip_plan: TripPlan, slot_name: str) -> List[Segment]:
        if not trip_plan or not getattr(trip_plan, "travel", None) or not getattr(trip_plan, "accommodation", None):
            return []
        slot_name = self._normalize_slot_name(slot_name)
        try:
            if slot_name == SlotType.FLIGHTS_OUTBOUND.value:
                return (trip_plan.travel.flights and trip_plan.travel.flights.outbound) or []
            if slot_name == SlotType.FLIGHTS_INBOUND.value:
                return (trip_plan.travel.flights and trip_plan.travel.flights.inbound) or []
            if slot_name == SlotType.ACCOMMODATION.value:
                return (trip_plan.accommodation and trip_plan.accommodation.segments) or []
            if slot_name == SlotType.GROUND_TRANSPORT.value:
                return trip_plan.travel.ground_transport or []
        except (AttributeError, TypeError) as e:
            logger.warning(f"SlotManager: Error accessing {slot_name}: {e}")
            return []
    
    def get_all_segments(self, trip_plan: TripPlan) -> List[Tuple[str, Segment, int]]:
        """Get all segments (slot_name, segment, index)."""
        if not trip_plan or not getattr(trip_plan, "travel", None) or not getattr(trip_plan, "accommodation", None):
            return []
        out = []
        try:
            if trip_plan.travel.flights and trip_plan.travel.flights.outbound:
                for i, seg in enumerate(trip_plan.travel.flights.outbound):
                    if seg:
                        out.append((SlotType.FLIGHTS_OUTBOUND.value, seg, i))
            if trip_plan.travel.flights and trip_plan.travel.flights.inbound:
                for i, seg in enumerate(trip_plan.travel.flights.inbound):
                    if seg:
                        out.append((SlotType.FLIGHTS_INBOUND.value, seg, i))
            if trip_plan.accommodation and trip_plan.accommodation.segments:
                for i, seg in enumerate(trip_plan.accommodation.segments):
                    if seg:
                        out.append((SlotType.ACCOMMODATION.value, seg, i))
            if trip_plan.travel.ground_transport:
                for idx, seg in enumerate(trip_plan.travel.ground_transport):
                    if seg:
                        out.append((SlotType.GROUND_TRANSPORT.value, seg, idx))
        except (AttributeError, TypeError) as e:
            logger.warning(f"SlotManager: Error in get_all_segments: {e}")
        return out
    
    def validate_segment(self, segment: Segment, slot_name: str) -> Tuple[bool, List[str]]:
        issues = []
        if segment.status == SegmentStatus.CONFIRMED and not segment.selected_option:
            issues.append(f"{slot_name}: CONFIRMED but no selected_option")
        if segment.status == SegmentStatus.SELECTING and not segment.options_pool:
            issues.append(f"{slot_name}: SELECTING but no options_pool")
        return (len(issues) == 0, issues)
    
    def ensure_segment_state(self, segment: Segment, slot_name: str) -> bool:
        fixed = False
        if segment.status == SegmentStatus.CONFIRMED and not segment.selected_option:
            segment.status = SegmentStatus.PENDING
            fixed = True
        if segment.status == SegmentStatus.SELECTING and not segment.options_pool:
            segment.status = SegmentStatus.PENDING
            fixed = True
        if segment.selected_option and segment.status not in [SegmentStatus.CONFIRMED, SegmentStatus.SELECTING]:
            segment.status = SegmentStatus.CONFIRMED
            fixed = True
        if segment.options_pool and segment.status == SegmentStatus.PENDING and not segment.selected_option:
            segment.status = SegmentStatus.SELECTING
            fixed = True
        return fixed
    
    def set_segment_selected(self, segment: Segment, slot_name: str, option_index: int):
        if option_index >= len(segment.options_pool):
            raise AgentException(f"Option index {option_index} out of range")
        segment.selected_option = segment.options_pool[option_index]
        segment.status = SegmentStatus.CONFIRMED
        logger.info(f"Set {slot_name} selected_option to index {option_index}, status → CONFIRMED")
    

_slot_manager = None

def get_slot_manager() -> SlotManager:
    global _slot_manager
    if _slot_manager is None:
        _slot_manager = SlotManager()
    return _slot_manager
