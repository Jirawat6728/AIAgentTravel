"""
Production-Grade Workflow Manager
Manages travel planning workflow, slot/segment routing, and option selection
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass

from app.models.trip_plan import SegmentStatus, Segment
from app.core.logging import get_logger

logger = get_logger(__name__)


class WorkflowStage(str, Enum):
    """Workflow stages"""
    INITIAL = "initial"           # No plan yet
    PLANNING = "planning"         # Creating itinerary
    SEARCHING = "searching"       # Searching for options
    SELECTING = "selecting"       # User/AI selecting options
    CONFIRMING = "confirming"     # Confirming selections
    BOOKING = "booking"          # Creating booking
    COMPLETE = "complete"        # Booking complete


class SlotType(str, Enum):
    """Travel slot types"""
    FLIGHTS_OUTBOUND = "flights_outbound"
    FLIGHTS_INBOUND = "flights_inbound"
    ACCOMMODATION = "accommodation"
    GROUND_TRANSPORT = "ground_transport"


@dataclass
class SlotState:
    """State of a travel slot"""
    slot_type: SlotType
    segment_index: int
    status: SegmentStatus
    has_requirements: bool
    has_options: bool
    has_selection: bool
    is_ready_for_search: bool
    is_ready_for_selection: bool
    is_complete: bool


@dataclass
class WorkflowState:
    """Current workflow state"""
    stage: WorkflowStage
    slots: List[SlotState]
    next_action: Optional[str]
    blocking_issues: List[str]
    progress_percentage: float


class WorkflowManager:
    """
    Production-grade workflow manager
    
    Features:
    - Clear route map for workflow progression
    - Stable slot/segment state management
    - Clear option selection logic
    - Workflow validation and error recovery
    """
    
    # Route map: Stage → Next Actions
    ROUTE_MAP = {
        WorkflowStage.INITIAL: ["CREATE_ITINERARY"],
        WorkflowStage.PLANNING: ["UPDATE_REQ", "CALL_SEARCH"],
        WorkflowStage.SEARCHING: ["CALL_SEARCH", "SELECT_OPTION"],
        WorkflowStage.SELECTING: ["SELECT_OPTION", "CALL_SEARCH"],  # Re-search if needed
        WorkflowStage.CONFIRMING: ["SELECT_OPTION", "AUTO_BOOK"],
        WorkflowStage.BOOKING: ["AUTO_BOOK"],
        WorkflowStage.COMPLETE: []
    }
    
    # Slot priority order (which slots to process first)
    SLOT_PRIORITY = [
        SlotType.FLIGHTS_OUTBOUND,  # Must do outbound first
        SlotType.FLIGHTS_INBOUND,   # Then inbound
        SlotType.ACCOMMODATION,     # Then hotels
        SlotType.GROUND_TRANSPORT   # Finally transfers
    ]
    
    def __init__(self):
        logger.info("WorkflowManager initialized")
    
    def analyze_slot_state(self, segment: Segment, slot_type: SlotType, segment_index: int) -> SlotState:
        """
        Analyze current state of a slot/segment
        
        Args:
            segment: Segment object
            slot_type: Type of slot
            segment_index: Index of segment
            
        Returns:
            SlotState with detailed status
        """
        has_requirements = bool(segment.requirements)
        has_options = bool(segment.options_pool) and len(segment.options_pool) > 0
        has_selection = segment.selected_option is not None
        status = segment.status
        
        # Determine readiness
        is_ready_for_search = (
            has_requirements and
            not has_options and
            status in [SegmentStatus.PENDING, SegmentStatus.SEARCHING]
        )
        
        is_ready_for_selection = (
            has_options and
            not has_selection and
            status == SegmentStatus.SELECTING
        )
        
        is_complete = (
            has_selection and
            status == SegmentStatus.CONFIRMED
        )
        
        return SlotState(
            slot_type=slot_type,
            segment_index=segment_index,
            status=status,
            has_requirements=has_requirements,
            has_options=has_options,
            has_selection=has_selection,
            is_ready_for_search=is_ready_for_search,
            is_ready_for_selection=is_ready_for_selection,
            is_complete=is_complete
        )
    
    def analyze_workflow(self, trip_plan) -> WorkflowState:
        """
        Analyze current workflow state
        
        Args:
            trip_plan: TripPlan object
            
        Returns:
            WorkflowState with current stage and next actions
        """
        # Collect all slots
        all_slots = []
        
        # Flights outbound
        for idx, seg in enumerate(trip_plan.travel.flights.outbound):
            slot_state = self.analyze_slot_state(seg, SlotType.FLIGHTS_OUTBOUND, idx)
            all_slots.append(slot_state)
        
        # Flights inbound
        for idx, seg in enumerate(trip_plan.travel.flights.inbound):
            slot_state = self.analyze_slot_state(seg, SlotType.FLIGHTS_INBOUND, idx)
            all_slots.append(slot_state)
        
        # Accommodation
        for idx, seg in enumerate(trip_plan.accommodation.segments):
            slot_state = self.analyze_slot_state(seg, SlotType.ACCOMMODATION, idx)
            all_slots.append(slot_state)
        
        # Ground transport
        for idx, seg in enumerate(trip_plan.travel.ground_transport):
            slot_state = self.analyze_slot_state(seg, SlotType.GROUND_TRANSPORT, idx)
            all_slots.append(slot_state)
        
        # Determine workflow stage
        stage = self._determine_stage(all_slots)
        
        # Find next action
        next_action = self._determine_next_action(stage, all_slots)
        
        # Find blocking issues
        blocking_issues = self._find_blocking_issues(all_slots)
        
        # Calculate progress
        progress = self._calculate_progress(all_slots)
        
        return WorkflowState(
            stage=stage,
            slots=all_slots,
            next_action=next_action,
            blocking_issues=blocking_issues,
            progress_percentage=progress
        )
    
    def _determine_stage(self, slots: List[SlotState]) -> WorkflowStage:
        """Determine current workflow stage"""
        if not slots:
            return WorkflowStage.INITIAL
        
        # Check if all complete
        if all(s.is_complete for s in slots):
            return WorkflowStage.COMPLETE
        
        # Check if any is booking
        if any(s.status == SegmentStatus.CONFIRMED and s.has_selection for s in slots):
            # Check if all required slots are confirmed
            required_slots = [s for s in slots if s.has_requirements]
            if all(s.is_complete for s in required_slots):
                return WorkflowStage.BOOKING
        
        # Check if any is selecting
        if any(s.is_ready_for_selection for s in slots):
            return WorkflowStage.SELECTING
        
        # Check if any is searching
        if any(s.status == SegmentStatus.SEARCHING for s in slots):
            return WorkflowStage.SEARCHING
        
        # Check if any has options (ready to select)
        if any(s.has_options for s in slots):
            return WorkflowStage.SELECTING
        
        # Check if any is ready for search
        if any(s.is_ready_for_search for s in slots):
            return WorkflowStage.SEARCHING
        
        # Otherwise planning
        return WorkflowStage.PLANNING
    
    def _determine_next_action(self, stage: WorkflowStage, slots: List[SlotState]) -> Optional[str]:
        """Determine next action based on stage and slots"""
        # Get next actions for this stage
        possible_actions = self.ROUTE_MAP.get(stage, [])
        
        if not possible_actions:
            return None
        
        # Find first actionable slot
        for slot_type in self.SLOT_PRIORITY:
            for slot in slots:
                if slot.slot_type != slot_type:
                    continue
                
                # Check what action is needed
                if slot.is_ready_for_search and "CALL_SEARCH" in possible_actions:
                    return f"CALL_SEARCH:{slot_type.value}:{slot.segment_index}"
                
                if slot.is_ready_for_selection and "SELECT_OPTION" in possible_actions:
                    return f"SELECT_OPTION:{slot_type.value}:{slot.segment_index}"
        
        # Default to first possible action
        return possible_actions[0] if possible_actions else None
    
    def _find_blocking_issues(self, slots: List[SlotState]) -> List[str]:
        """Find issues blocking workflow progress"""
        issues = []
        
        for slot in slots:
            if not slot.has_requirements:
                issues.append(f"{slot.slot_type.value}[{slot.segment_index}]: Missing requirements")
            
            if slot.status == SegmentStatus.SEARCHING:
                # Check if search is taking too long (would need timestamp)
                pass
            
            if slot.has_options and not slot.has_selection and slot.status != SegmentStatus.SELECTING:
                issues.append(f"{slot.slot_type.value}[{slot.segment_index}]: Has options but not in SELECTING state")
        
        return issues
    
    def _calculate_progress(self, slots: List[SlotState]) -> float:
        """Calculate workflow progress percentage"""
        if not slots:
            return 0.0
        
        completed = sum(1 for s in slots if s.is_complete)
        total = len(slots)
        
        return (completed / total * 100) if total > 0 else 0.0
    
    def get_next_slot_to_process(self, slots: List[SlotState]) -> Optional[Tuple[SlotType, int]]:
        """
        Get next slot that needs processing (following priority order)
        
        Returns:
            Tuple of (slot_type, segment_index) or None
        """
        for slot_type in self.SLOT_PRIORITY:
            for slot in slots:
                if slot.slot_type != slot_type:
                    continue
                
                if slot.is_ready_for_search:
                    return (slot.slot_type, slot.segment_index)
                
                if slot.is_ready_for_selection:
                    return (slot.slot_type, slot.segment_index)
        
        return None
    
    def validate_workflow(self, workflow_state: WorkflowState) -> Tuple[bool, List[str]]:
        """
        Validate workflow state for consistency
        
        Returns:
            Tuple of (is_valid, issues)
        """
        issues = []
        
        # Check for invalid state transitions
        # (would need history for this)
        
        # Check for blocking issues
        if workflow_state.blocking_issues:
            issues.extend(workflow_state.blocking_issues)
        
        # Check for orphaned segments (no requirements, no options, no selection)
        for slot in workflow_state.slots:
            if not slot.has_requirements and not slot.has_options and not slot.has_selection:
                issues.append(f"{slot.slot_type.value}[{slot.segment_index}]: Orphaned segment")
        
        return (len(issues) == 0, issues)
    
    def get_route_map(self) -> Dict[str, List[str]]:
        """Get route map for debugging"""
        return {
            stage.value: actions
            for stage, actions in self.ROUTE_MAP.items()
        }


class OptionSelector:
    """
    Production-grade option selector
    
    Features:
    - Clear selection criteria
    - Ranking algorithm
    - Confidence scoring
    """
    
    @staticmethod
    def rank_options(
        options: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float, Dict[str, Any]]]:
        """
        Rank options by quality score
        
        Args:
            options: List of option dictionaries
            user_preferences: Optional user preferences
            requirements: Optional segment requirements
            
        Returns:
            List of (index, score, option) tuples, sorted by score descending
        """
        ranked = []
        
        for idx, option in enumerate(options):
            score = OptionSelector._calculate_score(option, user_preferences, requirements)
            ranked.append((idx, score, option))
        
        # Sort by score descending
        ranked.sort(key=lambda x: x[1], reverse=True)
        
        return ranked
    
    @staticmethod
    def _calculate_score(
        option: Dict[str, Any],
        user_preferences: Optional[Dict[str, Any]],
        requirements: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate quality score for an option"""
        score = 0.0
        
        # 1. Recommended tag (40 points)
        if option.get("recommended") or "แนะนำ" in option.get("tags", []):
            score += 40.0
        
        # 2. Price value (30 points)
        price = option.get("price_amount") or option.get("price_total") or option.get("price", 0)
        if isinstance(price, (int, float)) and price > 0:
            # Lower price = higher score (inverse relationship)
            # Normalize to 0-30 range (assuming max price 100,000)
            normalized_price_score = max(0, 30 - (price / 100000 * 30))
            score += normalized_price_score
        
        # 3. Reviews/Ratings (20 points)
        rating = option.get("rating") or option.get("stars") or 0
        if isinstance(rating, (int, float)) and rating > 0:
            # 5 stars = 20 points, 4 stars = 16 points, etc.
            score += (rating / 5.0) * 20.0
        
        # 4. Convenience (10 points)
        # Check for direct flights, good locations, etc.
        if option.get("stops", 999) == 0:  # Direct flight
            score += 10.0
        elif option.get("stops", 999) == 1:  # One stop
            score += 5.0
        
        # 5. User preferences match (bonus)
        if user_preferences:
            # Check if option matches user preferences
            # (would need more sophisticated matching)
            pass
        
        return min(100.0, score)  # Cap at 100
    
    @staticmethod
    def select_best_option(
        options: List[Dict[str, Any]],
        user_preferences: Optional[Dict[str, Any]] = None,
        requirements: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, float, Dict[str, Any]]:
        """
        Select best option from list
        
        Returns:
            Tuple of (index, confidence, option)
        """
        if not options:
            raise ValueError("No options provided")
        
        ranked = OptionSelector.rank_options(options, user_preferences, requirements)
        
        if not ranked:
            raise ValueError("Ranking failed")
        
        best_idx, best_score, best_option = ranked[0]
        
        # Convert score to confidence (0-1)
        confidence = best_score / 100.0
        
        return (best_idx, confidence, best_option)
    
    @staticmethod
    def explain_selection(
        option: Dict[str, Any],
        score: float,
        ranked_options: List[Tuple[int, float, Dict[str, Any]]]
    ) -> str:
        """Generate explanation for why this option was selected"""
        reasons = []
        
        if option.get("recommended"):
            reasons.append("มี tag 'แนะนำ'")
        
        price = option.get("price_amount") or option.get("price_total") or option.get("price", 0)
        if price > 0:
            # Compare with average
            avg_price = sum(opt[2].get("price_amount") or opt[2].get("price_total") or 0 for opt in ranked_options[:3]) / min(3, len(ranked_options))
            if price < avg_price * 0.9:
                reasons.append("ราคาดีกว่าเฉลี่ย")
        
        rating = option.get("rating") or option.get("stars") or 0
        if rating >= 4.5:
            reasons.append(f"คะแนนสูง ({rating}/5)")
        
        if option.get("stops", 999) == 0:
            reasons.append("บินตรง (ไม่ต่อเครื่อง)")
        
        if not reasons:
            reasons.append("เป็นตัวเลือกที่ดีที่สุดตามคะแนนรวม")
        
        return " | ".join(reasons)
