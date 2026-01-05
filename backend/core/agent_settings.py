"""
Agent Settings Module - Level 3 Feature
Customizable agent behavior and preferences
"""

from __future__ import annotations
from typing import Any, Dict, Optional


class AgentSettings:
    """
    Agent Settings: Customizable agent behavior
    """
    
    # Default settings
    DEFAULT_SETTINGS = {
        "language": "th",  # th, en
        "tone": "friendly",  # formal, friendly, casual
        "response_style": "detailed",  # brief, detailed, verbose
        "auto_proceed": True,  # Auto proceed when info is sufficient
        "ask_before_search": False,  # Ask before executing search
        "memory_enabled": True,  # Enable memory features
        "suggestions_count": 5,  # Number of suggestions to show
        "summary_interval": 10,  # Messages before auto-summarize
    }
    
    # User-specific settings storage (should be in database)
    _user_settings: Dict[str, Dict[str, Any]] = {}
    
    @staticmethod
    def get_settings(user_id: str) -> Dict[str, Any]:
        """Get agent settings for user"""
        if user_id not in AgentSettings._user_settings:
            AgentSettings._user_settings[user_id] = dict(AgentSettings.DEFAULT_SETTINGS)
        return AgentSettings._user_settings[user_id]
    
    @staticmethod
    def update_settings(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update agent settings"""
        settings = AgentSettings.get_settings(user_id)
        settings.update(updates)
        AgentSettings._user_settings[user_id] = settings
        return settings
    
    @staticmethod
    def reset_settings(user_id: str) -> Dict[str, Any]:
        """Reset to default settings"""
        AgentSettings._user_settings[user_id] = dict(AgentSettings.DEFAULT_SETTINGS)
        return AgentSettings._user_settings[user_id]

