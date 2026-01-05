"""
Session Store Module - Level 3 Feature
Stores agent_state and session data persistently
"""

from __future__ import annotations
from typing import Any, Dict, Optional
from datetime import datetime
import json


class SessionStore:
    """
    Session Store: Persistent storage for agent state and session data
    """
    
    # In-memory store (should be replaced with Redis/MongoDB in production)
    _sessions: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def get_session(user_id: str, trip_id: str) -> Dict[str, Any]:
        """
        Get session data including agent_state
        """
        session_key = f"{user_id}:{trip_id}"
        session = SessionStore._sessions.get(session_key)
        
        if not session:
            session = {
                "user_id": user_id,
                "trip_id": trip_id,
                "agent_state": {
                    "intent": "idle",
                    "step": "initial",
                    "steps": [],
                    "current_task": None,
                },
                "message_count": 0,
                "last_summary_at": 0,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }
            SessionStore._sessions[session_key] = session
        
        return session
    
    @staticmethod
    def update_session(
        user_id: str,
        trip_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update session data
        """
        session = SessionStore.get_session(user_id, trip_id)
        session.update(updates)
        session["updated_at"] = datetime.utcnow().isoformat()
        SessionStore._sessions[f"{user_id}:{trip_id}"] = session
        return session
    
    @staticmethod
    def update_agent_state(
        user_id: str,
        trip_id: str,
        agent_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update agent_state specifically
        """
        session = SessionStore.get_session(user_id, trip_id)
        session["agent_state"] = agent_state
        session["updated_at"] = datetime.utcnow().isoformat()
        SessionStore._sessions[f"{user_id}:{trip_id}"] = session
        return session
    
    @staticmethod
    def increment_message_count(user_id: str, trip_id: str) -> int:
        """
        Increment message count and return new count
        """
        session = SessionStore.get_session(user_id, trip_id)
        session["message_count"] = session.get("message_count", 0) + 1
        session["updated_at"] = datetime.utcnow().isoformat()
        SessionStore._sessions[f"{user_id}:{trip_id}"] = session
        return session["message_count"]
    
    @staticmethod
    def get_agent_state(user_id: str, trip_id: str) -> Dict[str, Any]:
        """
        Get current agent_state
        """
        session = SessionStore.get_session(user_id, trip_id)
        return session.get("agent_state", {})

