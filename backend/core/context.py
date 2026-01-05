from __future__ import annotations

from typing import Any, Dict
from core.memory_policy import MemoryPolicy

USER_CONTEXTS: Dict[str, Dict[str, Any]] = {}
# Conversation summaries: {user_id: [summary1, summary2, ...]}
CONVERSATION_SUMMARIES: Dict[str, List[Dict[str, Any]]] = {}


def get_user_ctx(user_id: str, apply_policy: bool = True) -> Dict[str, Any]:
    """
    Get user context with optional memory policy application
    Level 2: Memory Policy integration
    """
    ctx = USER_CONTEXTS.get(user_id)
    if not ctx:
        ctx = {
            "last_plan_choices": [],
            "current_plan": None,
            "last_travel_slots": {},
            "last_search_results": None,
            "iata_cache": {},
            "trip_title": None,
            "cooldowns": {
                # {trip_id: unix_ts_seconds}
                "refresh_ts_by_trip": {},
            },
        }
        USER_CONTEXTS[user_id] = ctx
    
    # ensure new keys exist for older contexts
    ctx.setdefault("cooldowns", {"refresh_ts_by_trip": {}})
    ctx["cooldowns"].setdefault("refresh_ts_by_trip", {})
    
    # Level 2: Apply memory policy (cleanup expired items)
    if apply_policy:
        ctx = MemoryPolicy.cleanup_context(ctx)
        # Update context if cleaned
        if ctx != USER_CONTEXTS.get(user_id):
            USER_CONTEXTS[user_id] = ctx
    
    return ctx


def update_user_ctx(user_id: str, updates: Dict[str, Any]):
    """
    Update user context with memory policy timestamp tracking
    Level 2: Memory Policy integration
    """
    ctx = get_user_ctx(user_id, apply_policy=False)
    
    for key, value in updates.items():
        ctx[key] = value
        # Update timestamp for memory policy
        MemoryPolicy.update_timestamp(ctx, key)
    
    # Apply policy after updates
    ctx = MemoryPolicy.cleanup_context(ctx)
    USER_CONTEXTS[user_id] = ctx
    
    return ctx


def reset_trip_ctx(user_id: str, client_trip_id: str | None = None) -> Dict[str, Any]:
    """Reset in-memory trip state (does not run agent)."""
    ctx = get_user_ctx(user_id)
    trip_id = (client_trip_id or "").strip() or "default"
    # clear per-trip cooldown timestamp
    (ctx.get("cooldowns") or {}).get("refresh_ts_by_trip", {}).pop(trip_id, None)
    # clear last outputs (simple global reset in this demo)
    ctx["last_plan_choices"] = []
    ctx["current_plan"] = None
    ctx["last_travel_slots"] = {}
    ctx["last_search_results"] = None
    ctx["trip_title"] = None
    return ctx


def get_conversation_summaries(user_id: str) -> List[Dict[str, Any]]:
    """Get conversation summaries for user"""
    return CONVERSATION_SUMMARIES.get(user_id, [])


def add_conversation_summary(user_id: str, summary: Dict[str, Any]):
    """Add conversation summary"""
    if user_id not in CONVERSATION_SUMMARIES:
        CONVERSATION_SUMMARIES[user_id] = []
    CONVERSATION_SUMMARIES[user_id].append(summary)
    # Keep only last 10 summaries
    CONVERSATION_SUMMARIES[user_id] = CONVERSATION_SUMMARIES[user_id][-10:]
