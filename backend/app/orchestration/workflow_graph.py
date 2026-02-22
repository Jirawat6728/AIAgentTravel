"""
LangGraph Workflow State Machine for Travel Planning

กำหนดขั้นตอน workflow และการเปลี่ยนขั้นตอนที่ถูกต้อง:
planning → searching → selecting → summary → booking → done
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

# Allowed transitions: from_step -> [allowed_next_steps]
VALID_TRANSITIONS: Dict[str, List[str]] = {
    "planning": ["planning", "searching"],      # UPDATE_REQ stays planning, CALL_SEARCH -> searching
    "searching": ["searching", "selecting"],    # Multiple searches, then selecting when options ready
    "selecting": ["selecting", "summary"],      # User picks options, then summary when complete
    "summary": ["summary", "booking"],          # User confirms -> booking
    "booking": ["booking", "done"],             # Payment complete -> done
    "done": ["done"],                           # Terminal
}

WORKFLOW_STEPS = ["planning", "searching", "selecting", "summary", "booking", "done"]


def can_transition(from_step: str, to_step: str) -> bool:
    """ตรวจสอบว่าเปลี่ยนจาก from_step ไป to_step ได้หรือไม่"""
    from_step = (from_step or "planning").lower().strip()
    to_step = (to_step or "planning").lower().strip()
    allowed = VALID_TRANSITIONS.get(from_step, ["planning"])
    return to_step in allowed


def get_next_step_for_action(action_type: str, current_step: str) -> Optional[str]:
    """
    คืน workflow step ถัดไปตาม action ที่ Controller ตัดสินใจ
    - CREATE_ITINERARY, UPDATE_REQ -> planning
    - CALL_SEARCH (start) -> searching
    - CALL_SEARCH (done, options ready) -> selecting
    - All slots selected -> summary (ตัดสินจาก trip_plan.is_complete ภายนอก)
    """
    current = (current_step or "planning").lower().strip()
    action = (action_type or "").upper()

    if action in ("CREATE_ITINERARY", "UPDATE_REQ", "ASK_USER"):
        return "planning"
    if action == "CALL_SEARCH":
        # When starting search -> searching; when done (options cached) -> selecting
        # Caller should pass searching at start, selecting when options are cached
        if current == "planning":
            return "searching"
        if current == "searching":
            return "selecting"
        return "searching"
    if action == "SELECT_OPTION":
        return "selecting"
    if action in ("CONFIRM_BOOKING", "CREATE_BOOKING"):
        return "booking"
    return None
