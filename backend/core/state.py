from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import uuid

@dataclass
class AgentState:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    last_plan_choices: list[dict] = field(default_factory=list)
    selected_choice_id: Optional[int] = None

_STATE = AgentState()

def get_state() -> AgentState:
    return _STATE

def reset_state() -> AgentState:
    global _STATE
    _STATE = AgentState()
    return _STATE
