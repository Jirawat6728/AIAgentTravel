"""
User Profile Memory Module - Level 3 Feature
Long-term memory for user preferences and profile
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime


class UserProfileMemory:
    """
    User Profile Memory: Long-term preferences and profile
    Stores user preferences, travel patterns, and profile info
    """
    
    @staticmethod
    def get_profile(user_id: str) -> Dict[str, Any]:
        """
        Get user profile from storage
        Should be integrated with MongoDB/database
        """
        # TODO: Integrate with database
        # For now, return default structure
        return {
            "user_id": user_id,
            "preferences": {
                "travel_style": None,  # "budget", "comfort", "luxury"
                "flight_preferences": {
                    "prefer_morning": None,
                    "prefer_direct": None,
                    "preferred_airlines": [],
                },
                "hotel_preferences": {
                    "preferred_stars": None,  # 3, 4, 5
                    "preferred_budget_range": None,
                },
                "budget_range": None,
            },
            "frequent_passengers": [],  # List of passenger info
            "created_at": None,
            "updated_at": None,
        }
    
    @staticmethod
    def update_preferences(
        user_id: str,
        preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user preferences
        Should be integrated with database
        """
        profile = UserProfileMemory.get_profile(user_id)
        
        # Merge new preferences
        if "preferences" not in profile:
            profile["preferences"] = {}
        
        # Deep merge preferences
        UserProfileMemory._deep_merge(profile["preferences"], preferences)
        profile["updated_at"] = datetime.utcnow().isoformat()
        
        # TODO: Save to database
        # await save_user_profile(user_id, profile)
        
        return profile
    
    @staticmethod
    def extract_preferences_from_context(context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract preference suggestions from current context
        Returns preferences that could be remembered
        """
        travel_slots = context.get("last_travel_slots") or {}
        preferences = {}
        
        # Extract travel style
        if travel_slots.get("style"):
            preferences["travel_style"] = travel_slots.get("style")
        
        # Extract budget if available
        if travel_slots.get("budget"):
            preferences["budget_range"] = travel_slots.get("budget")
        
        # Extract flight preferences from plan choices
        plan_choices = context.get("last_plan_choices") or []
        if plan_choices:
            # Check if user tends to select non-stop flights
            selected_non_stop = any(
                choice.get("is_non_stop") or choice.get("flight", {}).get("stops") == 0
                for choice in plan_choices[:3]  # Check top 3
            )
            if selected_non_stop:
                preferences.setdefault("flight_preferences", {})
                preferences["flight_preferences"]["prefer_direct"] = True
        
        return preferences
    
    @staticmethod
    def apply_profile_to_slots(
        travel_slots: Dict[str, Any],
        profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply user profile preferences to travel slots
        Fills in defaults based on user preferences
        """
        enhanced_slots = dict(travel_slots)
        prefs = profile.get("preferences", {})
        
        # Apply travel style if not specified
        if not enhanced_slots.get("style") and prefs.get("travel_style"):
            enhanced_slots["style"] = prefs["travel_style"]
        
        # Apply budget if not specified
        if not enhanced_slots.get("budget") and prefs.get("budget_range"):
            enhanced_slots["budget"] = prefs["budget_range"]
        
        return enhanced_slots
    
    @staticmethod
    def _deep_merge(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                UserProfileMemory._deep_merge(base[key], value)
            else:
                base[key] = value
        return base

