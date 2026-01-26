"""
Production-Grade Slot/Segment Manager
Stable management of travel slots and segments
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from enum import Enum

from app.models.trip_plan import Segment, SegmentStatus, TripPlan
from app.core.logging import get_logger
from app.core.exceptions import AgentException

logger = get_logger(__name__)


class SlotType(str, Enum):
    """Travel slot types with clear mapping"""
    FLIGHTS_OUTBOUND = "flights_outbound"
    FLIGHTS_INBOUND = "flights_inbound"
    ACCOMMODATION = "accommodation"
    GROUND_TRANSPORT = "ground_transport"


class SlotManager:
    """
    Production-grade slot/segment manager
    
    Features:
    - Stable slot access patterns
    - Clear segment lifecycle management
    - Validation and consistency checks
    - Error recovery
    """
    
    def __init__(self):
        logger.info("SlotManager initialized")
    
    def get_segment(
        self,
        trip_plan: TripPlan,
        slot_name: str,
        segment_index: int,
        create_if_missing: bool = False
    ) -> Tuple[Segment, List[Segment]]:
        """
        Get segment from trip plan with stable routing
        
        Args:
            trip_plan: TripPlan object
            slot_name: Slot name (e.g., "flights_outbound", "accommodation")
            segment_index: Segment index
            create_if_missing: Create segment if it doesn't exist
            
        Returns:
            Tuple of (segment, segments_list)
        """
        # Normalize slot name
        slot_name = self._normalize_slot_name(slot_name)
        
        # Get segments list
        segments = self._get_segments_list(trip_plan, slot_name)
        
        if not segments:
            raise AgentException(f"No segments found for slot: {slot_name}")
        
        # Check index
        if segment_index < 0:
            raise AgentException(f"Invalid segment_index: {segment_index} (must be >= 0)")
        
        if segment_index >= len(segments):
            if create_if_missing:
                # Create missing segment
                new_segment = Segment()
                segments.append(new_segment)
                logger.info(f"Created new segment for {slot_name}[{segment_index}]")
                return (new_segment, segments)
            else:
                raise AgentException(
                    f"Segment index {segment_index} out of range for {slot_name} "
                    f"(has {len(segments)} segments)"
                )
        
        return (segments[segment_index], segments)
    
    def _normalize_slot_name(self, slot_name: str) -> str:
        """Normalize slot name to standard format"""
        slot_name = slot_name.lower().strip()
        
        # Map aliases to standard names
        slot_aliases = {
            "flights": "flights_outbound",  # Default to outbound
            "flight": "flights_outbound",
            "hotels": "accommodation",
            "hotel": "accommodation",
            "accommodations": "accommodation",
            "transfers": "ground_transport",
            "transfer": "ground_transport",
            "transport": "ground_transport",
            "ground": "ground_transport"
        }
        
        return slot_aliases.get(slot_name, slot_name)
    
    def _get_segments_list(self, trip_plan: TripPlan, slot_name: str) -> List[Segment]:
        """Get segments list for a slot name"""
        slot_name = self._normalize_slot_name(slot_name)
        
        if slot_name == SlotType.FLIGHTS_OUTBOUND.value:
            return trip_plan.travel.flights.outbound
        elif slot_name == SlotType.FLIGHTS_INBOUND.value:
            return trip_plan.travel.flights.inbound
        elif slot_name == SlotType.ACCOMMODATION.value:
            return trip_plan.accommodation.segments
        elif slot_name == SlotType.GROUND_TRANSPORT.value:
            return trip_plan.travel.ground_transport
        else:
            raise AgentException(f"Unknown slot type: {slot_name}")
    
    def get_all_segments(self, trip_plan: TripPlan) -> List[Tuple[str, Segment, int]]:
        """
        Get all segments with their slot names and indices
        
        Returns:
            List of (slot_name, segment, index) tuples
        """
        all_segments = []
        
        # Flights outbound
        for idx, seg in enumerate(trip_plan.travel.flights.outbound):
            all_segments.append((SlotType.FLIGHTS_OUTBOUND.value, seg, idx))
        
        # Flights inbound
        for idx, seg in enumerate(trip_plan.travel.flights.inbound):
            all_segments.append((SlotType.FLIGHTS_INBOUND.value, seg, idx))
        
        # Accommodation
        for idx, seg in enumerate(trip_plan.accommodation.segments):
            all_segments.append((SlotType.ACCOMMODATION.value, seg, idx))
        
        # Ground transport
        for idx, seg in enumerate(trip_plan.travel.ground_transport):
            all_segments.append((SlotType.GROUND_TRANSPORT.value, seg, idx))
        
        return all_segments
    
    def validate_segment(self, segment: Segment, slot_name: str) -> Tuple[bool, List[str]]:
        """
        Validate segment state
        
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check status consistency
        if segment.status == SegmentStatus.CONFIRMED and not segment.selected_option:
            issues.append(f"{slot_name}: Status is CONFIRMED but no selected_option")
        
        if segment.status == SegmentStatus.SELECTING and not segment.options_pool:
            issues.append(f"{slot_name}: Status is SELECTING but no options_pool")
        
        if segment.selected_option and segment.status not in [SegmentStatus.CONFIRMED, SegmentStatus.SELECTING]:
            issues.append(f"{slot_name}: Has selected_option but status is {segment.status}")
        
        # Check requirements
        if not segment.requirements:
            issues.append(f"{slot_name}: Missing requirements")
        
        return (len(issues) == 0, issues)
    
    def ensure_segment_state(self, segment: Segment, slot_name: str) -> bool:
        """
        Ensure segment state is consistent (auto-fix if possible)
        
        Returns:
            True if state was fixed
        """
        fixed = False
        
        # Fix: CONFIRMED without selected_option
        if segment.status == SegmentStatus.CONFIRMED and not segment.selected_option:
            logger.warning(f"Fixing {slot_name}: CONFIRMED without selected_option → PENDING")
            segment.status = SegmentStatus.PENDING
            fixed = True
        
        # Fix: SELECTING without options_pool
        if segment.status == SegmentStatus.SELECTING and not segment.options_pool:
            logger.warning(f"Fixing {slot_name}: SELECTING without options_pool → PENDING")
            segment.status = SegmentStatus.PENDING
            fixed = True
        
        # Fix: Has selected_option but wrong status
        if segment.selected_option and segment.status not in [SegmentStatus.CONFIRMED, SegmentStatus.SELECTING]:
            logger.warning(f"Fixing {slot_name}: Has selected_option but status {segment.status} → CONFIRMED")
            segment.status = SegmentStatus.CONFIRMED
            fixed = True
        
        # Fix: Has options_pool but not SELECTING
        if segment.options_pool and segment.status == SegmentStatus.PENDING and not segment.selected_option:
            logger.info(f"Fixing {slot_name}: Has options_pool but PENDING → SELECTING")
            segment.status = SegmentStatus.SELECTING
            fixed = True
        
        return fixed
    
    def clear_segment_options(self, segment: Segment, slot_name: str, reason: str = ""):
        """Clear options and reset segment state"""
        logger.info(f"Clearing options for {slot_name}: {reason}")
        segment.options_pool = []
        segment.selected_option = None
        if segment.status == SegmentStatus.SELECTING:
            segment.status = SegmentStatus.PENDING
    
    def set_segment_selected(self, segment: Segment, slot_name: str, option_index: int):
        """Set segment selected option and update status"""
        if option_index >= len(segment.options_pool):
            raise AgentException(f"Option index {option_index} out of range (has {len(segment.options_pool)} options)")
        
        segment.selected_option = segment.options_pool[option_index]
        segment.status = SegmentStatus.CONFIRMED
        logger.info(f"Set {slot_name} selected_option to index {option_index}, status → CONFIRMED")
    
    def get_segment_summary(self, segment: Segment, slot_name: str) -> Dict[str, Any]:
        """Get summary of segment state"""
        return {
            "slot": slot_name,
            "status": segment.status.value if isinstance(segment.status, SegmentStatus) else str(segment.status),
            "has_requirements": bool(segment.requirements),
            "requirements_count": len(segment.requirements) if segment.requirements else 0,
            "has_options": bool(segment.options_pool) and len(segment.options_pool) > 0,
            "options_count": len(segment.options_pool) if segment.options_pool else 0,
            "has_selection": segment.selected_option is not None,
            "is_complete": segment.status == SegmentStatus.CONFIRMED and segment.selected_option is not None
        }
