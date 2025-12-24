from __future__ import annotations

from typing import Any, Dict

USER_CONTEXTS: Dict[str, Dict[str, Any]] = {}


def get_user_ctx(user_id: str) -> Dict[str, Any]:
    ctx = USER_CONTEXTS.get(user_id)
    if not ctx:
        ctx = {
            "last_plan_choices": [],
            "current_plan": None,
            "last_travel_slots": {},
            "last_search_results": None,
            "iata_cache": {},
            "trip_title": None,
        }
        USER_CONTEXTS[user_id] = ctx
    return ctx
