from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "demo_user"
    existing_travel_slots: Optional[Dict[str, Any]] = None

class SelectChoiceRequest(BaseModel):
    user_id: Optional[str] = "demo_user"
    choice_id: int
