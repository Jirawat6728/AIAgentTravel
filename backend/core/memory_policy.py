"""
Memory Policy System - Level 2 Feature
Implements intelligent memory retention, prioritization, and cleanup strategies
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import time


class MemoryPriority:
    """Memory priority levels"""
    CRITICAL = "critical"  # Always keep (current plan, active slots)
    HIGH = "high"  # Keep for active session (search results, choices)
    MEDIUM = "medium"  # Keep for a few hours (recent history)
    LOW = "low"  # Clean up after session (debug, temp data)


class MemoryPolicy:
    """
    Defines memory retention policies for different types of data
    """
    
    # Retention times (in seconds)
    RETENTION_TIMES = {
        MemoryPriority.CRITICAL: None,  # Never expire
        MemoryPriority.HIGH: 3600 * 2,  # 2 hours
        MemoryPriority.MEDIUM: 3600,  # 1 hour
        MemoryPriority.LOW: 300,  # 5 minutes
    }
    
    # Priority mapping for context keys
    KEY_PRIORITIES = {
        # Critical - always keep
        "current_plan": MemoryPriority.CRITICAL,
        "last_travel_slots": MemoryPriority.CRITICAL,
        
        # High - keep for active session
        "last_plan_choices": MemoryPriority.HIGH,
        "last_search_results": MemoryPriority.HIGH,
        "trip_title": MemoryPriority.HIGH,
        "last_agent_state": MemoryPriority.HIGH,
        
        # Medium - recent history
        "iata_cache": MemoryPriority.MEDIUM,
        "cooldowns": MemoryPriority.MEDIUM,
        
        # Low - temporary
        "debug": MemoryPriority.LOW,
        "temp": MemoryPriority.LOW,
    }
    
    @staticmethod
    def get_priority(key: str) -> str:
        """Get priority level for a context key"""
        return MemoryPolicy.KEY_PRIORITIES.get(key, MemoryPriority.MEDIUM)
    
    @staticmethod
    def should_retain(key: str, timestamp: Optional[float] = None) -> bool:
        """
        Determine if a memory item should be retained
        Returns True if the item should be kept, False if it should be cleaned up
        """
        priority = MemoryPolicy.get_priority(key)
        
        # Critical items are always retained
        if priority == MemoryPriority.CRITICAL:
            return True
        
        # If no timestamp, assume it's recent (keep it)
        if timestamp is None:
            return True
        
        # Check retention time
        retention_time = MemoryPolicy.RETENTION_TIMES.get(priority)
        if retention_time is None:
            return True  # Never expire
        
        age = time.time() - timestamp
        return age < retention_time
    
    @staticmethod
    def cleanup_context(ctx: Dict[str, Any], current_time: Optional[float] = None) -> Dict[str, Any]:
        """
        Clean up context based on memory policy
        Removes low-priority items that have expired
        """
        if current_time is None:
            current_time = time.time()
        
        cleaned = {}
        timestamps = ctx.get("_memory_timestamps", {})
        
        for key, value in ctx.items():
            if key.startswith("_"):
                continue  # Skip internal metadata
            
            priority = MemoryPolicy.get_priority(key)
            timestamp = timestamps.get(key, current_time)
            
            if MemoryPolicy.should_retain(key, timestamp):
                cleaned[key] = value
            # else: item expires, don't include it
        
        # Preserve timestamps for retained items
        if timestamps:
            cleaned_timestamps = {
                k: v for k, v in timestamps.items()
                if k in cleaned
            }
            if cleaned_timestamps:
                cleaned["_memory_timestamps"] = cleaned_timestamps
        
        return cleaned
    
    @staticmethod
    def update_timestamp(ctx: Dict[str, Any], key: str, timestamp: Optional[float] = None):
        """Update timestamp for a memory key"""
        if timestamp is None:
            timestamp = time.time()
        
        if "_memory_timestamps" not in ctx:
            ctx["_memory_timestamps"] = {}
        
        ctx["_memory_timestamps"][key] = timestamp
    
    @staticmethod
    def prioritize_memory(ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prioritize memory items - ensure critical items are always present
        Returns a prioritized view of the context
        """
        prioritized = {}
        
        # First, add critical items
        for key in ctx:
            if MemoryPolicy.get_priority(key) == MemoryPriority.CRITICAL:
                prioritized[key] = ctx[key]
        
        # Then, add high priority items
        for key in ctx:
            if MemoryPolicy.get_priority(key) == MemoryPriority.HIGH:
                prioritized[key] = ctx[key]
        
        # Then, medium priority
        for key in ctx:
            if MemoryPolicy.get_priority(key) == MemoryPriority.MEDIUM:
                prioritized[key] = ctx[key]
        
        # Finally, low priority
        for key in ctx:
            if MemoryPolicy.get_priority(key) == MemoryPriority.LOW:
                prioritized[key] = ctx[key]
        
        # Preserve metadata
        if "_memory_timestamps" in ctx:
            prioritized["_memory_timestamps"] = ctx["_memory_timestamps"]
        
        return prioritized

