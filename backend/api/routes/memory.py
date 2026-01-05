"""
Memory API Routes - Level 3 Feature
Handles memory commit and retrieval
"""

from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from core.user_profile_memory import UserProfileMemory
from core.context import get_conversation_summaries, add_conversation_summary

router = APIRouter()


class MemoryCommitRequest(BaseModel):
    user_id: str
    memory_type: str  # "preference", "profile", "trip_summary"
    data: Dict[str, Any]
    description: str = ""


@router.post("/api/memory/commit")
async def commit_memory(req: MemoryCommitRequest):
    """
    Commit memory items (preferences, profile, trip summary)
    Separated from chat to control policy/security
    """
    try:
        if req.memory_type == "preference":
            # Update user preferences
            profile = UserProfileMemory.update_preferences(req.user_id, req.data)
            return {
                "ok": True,
                "message": "บันทึก preferences สำเร็จ",
                "profile": profile,
            }
        elif req.memory_type == "profile":
            # Update user profile
            profile = UserProfileMemory.update_preferences(req.user_id, req.data)
            return {
                "ok": True,
                "message": "บันทึก profile สำเร็จ",
                "profile": profile,
            }
        elif req.memory_type == "trip_summary":
            # Add trip summary
            add_conversation_summary(req.user_id, req.data)
            return {
                "ok": True,
                "message": "บันทึก trip summary สำเร็จ",
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unknown memory_type: {req.memory_type}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory commit failed: {str(e)}")


@router.get("/api/session/{session_id}")
async def get_session(session_id: str, user_id: str):
    """
    Get session data including working memory and summary
    For frontend rendering
    """
    from core.session_store import SessionStore
    from core.context import get_user_ctx
    
    # Parse session_id (format: user_id:trip_id)
    parts = session_id.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=400, detail="Invalid session_id format")
    
    parsed_user_id, trip_id = parts
    
    # Verify user_id matches
    if parsed_user_id != user_id:
        raise HTTPException(status_code=403, detail="User ID mismatch")
    
    # Get session
    session = SessionStore.get_session(user_id, trip_id)
    
    # Get context
    ctx = get_user_ctx(user_id)
    
    # Get summaries
    summaries = get_conversation_summaries(user_id)
    
    return {
        "ok": True,
        "session": session,
        "context": ctx,
        "summaries": summaries[-5:],  # Last 5 summaries
    }

