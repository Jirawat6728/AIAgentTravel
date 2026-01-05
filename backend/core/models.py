from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "demo_user"
    existing_travel_slots: Optional[Dict[str, Any]] = None
    client_trip_id: Optional[str] = None
    # Agent brake control
    # - user_message: run agent
    # - refresh: regenerate (should not write memory)
    # - chat_init / chat_reset: do not run agent
    trigger: Optional[str] = "user_message"

class SelectChoiceRequest(BaseModel):
    user_id: Optional[str] = "demo_user"
    choice_id: int
    trip_id: Optional[str] = None  # ✅ เพิ่ม trip_id สำหรับ slot workflow
