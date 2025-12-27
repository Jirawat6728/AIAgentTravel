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
            "cooldowns": {
                # {trip_id: unix_ts_seconds}
                "refresh_ts_by_trip": {},
            },
        }
        USER_CONTEXTS[user_id] = ctx
    # ensure new keys exist for older contexts
    ctx.setdefault("cooldowns", {"refresh_ts_by_trip": {}})
    ctx["cooldowns"].setdefault("refresh_ts_by_trip", {})
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
