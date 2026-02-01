"""
โมเดลแอ็กชันสำหรับ Controller และการบันทึกแอ็กชัน
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Strict action type enum"""
    UPDATE_REQ = "UPDATE_REQ"
    CALL_SEARCH = "CALL_SEARCH"
    SELECT_OPTION = "SELECT_OPTION"
    ASK_USER = "ASK_USER"
    BATCH = "BATCH"
    CREATE_ITINERARY = "CREATE_ITINERARY"  # Added BATCH action type


class ControllerAction(BaseModel):
    """
    Action returned by Controller
    Supports single action or batch actions (optimized for speed)
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    thought: str = Field(..., min_length=1, description="Reasoning for this action")
    action: ActionType = Field(..., description="Primary action to take")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action-specific payload"
    )
    # New field for batch processing
    batch_actions: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="List of actions to execute in parallel. Each dict must have 'action' and 'payload'."
    )
    
    @field_validator('action', mode='before')
    @classmethod
    def validate_action(cls, v: Any) -> ActionType:
        """Validate and convert action to enum"""
        if isinstance(v, ActionType):
            return v
        if isinstance(v, str):
            try:
                return ActionType(v.upper())
            except ValueError:
                # If invalid, default to ASK_USER instead of crashing
                return ActionType.ASK_USER
        return ActionType.ASK_USER
    
    @field_validator('thought')
    @classmethod
    def validate_thought(cls, v: str) -> str:
        """Validate thought is not empty"""
        if not v or not v.strip():
            raise ValueError("thought cannot be empty")
        return v.strip()


class ActionLogEntry(BaseModel):
    """Single action log entry - extra='allow' to handle unexpected fields from external APIs"""
    model_config = {"extra": "allow"}
    action: str = Field(..., description="Action name")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action payload")
    result: Optional[str] = Field(default=None, description="Action result")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Action timestamp"
    )
    success: bool = Field(default=True, description="Whether action succeeded")

    @property
    def action_type(self) -> str:
        """Alias for the stored action name (needed for intelligence warnings)."""
        return self.action


class ActionLog(BaseModel):
    """
    Log of actions taken in Controller Loop
    Used by Responder to generate response
    extra='allow' to handle unexpected fields from external APIs
    """
    model_config = {"extra": "allow"}
    actions: List[ActionLogEntry] = Field(
        default_factory=list,
        description="List of actions executed"
    )
    
    def add_action(
        self,
        action: str,
        payload: Dict[str, Any],
        result: Optional[str] = None,
        success: bool = True
    ):
        """Add an action to the log"""
        entry = ActionLogEntry(
            action=action,
            payload=payload,
            result=result,
            success=success
        )
        self.actions.append(entry)
    
    def get_last_action(self) -> Optional[ActionLogEntry]:
        """Get the last action entry"""
        return self.actions[-1] if self.actions else None
    
    def has_failures(self) -> bool:
        """Check if any actions failed"""
        return any(not entry.success for entry in self.actions)
