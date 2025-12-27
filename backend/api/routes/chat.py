from __future__ import annotations

from typing import Any, Dict, Optional
import time

from fastapi import APIRouter, Body, HTTPException

from core.models import ChatRequest, SelectChoiceRequest
from core.orchestrator import (
    orchestrate_chat,
    handle_choice_select,
    TRIGGER_USER_MESSAGE,
    TRIGGER_REFRESH,
    TRIGGER_CHAT_INIT,
    TRIGGER_CHAT_RESET,
)
from core.slots import DEFAULT_SLOTS, normalize_non_core_defaults
from core.context import get_user_ctx, reset_trip_ctx
from services.amadeus_service import empty_search_results

router = APIRouter()

# Server-side cooldown for refresh/regenerate (seconds)
REFRESH_COOLDOWN_SECONDS = 3.0


@router.post("/api/chat")
async def chat(req: ChatRequest):
    user_id = (req.user_id or "demo_user").strip()
    msg = (req.message or "").strip()

    trigger = (req.trigger or TRIGGER_USER_MESSAGE).strip()
    trip_id = (req.client_trip_id or "").strip() or "default"

    # 🛑 Brake: do not run agent on init/reset triggers
    if trigger in {TRIGGER_CHAT_INIT, TRIGGER_CHAT_RESET}:
        return {
            "response": "",
            "travel_slots": normalize_non_core_defaults(get_user_ctx(user_id).get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": None,
            "trip_title": get_user_ctx(user_id).get("trip_title"),
            "agent_state": {"intent": "idle", "step": "brake", "steps": []},
            "suggestions": [],
            "meta": {"agent_ran": False, "reason": "braked", "trigger": trigger, "trip_id": trip_id},
        }

    if not msg:
        raise HTTPException(status_code=400, detail="message is empty")

    # 🔒 Refresh cooldown (server-side)
    if trigger == TRIGGER_REFRESH:
        ctx = get_user_ctx(user_id)
        cooldowns = ctx.get("cooldowns") or {}
        m = cooldowns.get("refresh_ts_by_trip") or {}
        now = time.time()
        last = float(m.get(trip_id) or 0.0)
        if last and (now - last) < REFRESH_COOLDOWN_SECONDS:
            wait = max(0.0, REFRESH_COOLDOWN_SECONDS - (now - last))
            return {
                "response": f"⏳ กดรีเฟรชถี่ไปนิดนะคะ รออีก ~{wait:.1f}s แล้วลองใหม่ค่ะ",
                "travel_slots": normalize_non_core_defaults(get_user_ctx(user_id).get("last_travel_slots") or DEFAULT_SLOTS),
                "missing_slots": [],
                "search_results": get_user_ctx(user_id).get("last_search_results") or empty_search_results(),
                "plan_choices": get_user_ctx(user_id).get("last_plan_choices") or [],
                "current_plan": get_user_ctx(user_id).get("current_plan"),
                "trip_title": get_user_ctx(user_id).get("trip_title"),
                "agent_state": {"intent": "idle", "step": "cooldown", "steps": []},
                "suggestions": [],
                "meta": {"agent_ran": False, "reason": "cooldown", "trigger": trigger, "trip_id": trip_id},
            }
        m[trip_id] = now
        cooldowns["refresh_ts_by_trip"] = m
        ctx["cooldowns"] = cooldowns

    existing = dict(DEFAULT_SLOTS)
    if isinstance(req.existing_travel_slots, dict):
        existing.update(req.existing_travel_slots)

    # 🧠 refresh should regenerate without writing memory
    write_memory = (trigger != TRIGGER_REFRESH)
    out = await orchestrate_chat(user_id=user_id, user_message=msg, existing_slots=existing, write_memory=write_memory)

    # stabilize schema
    out.setdefault("response", "")
    out.setdefault("travel_slots", normalize_non_core_defaults(existing))
    out["travel_slots"] = normalize_non_core_defaults(out["travel_slots"])
    out.setdefault("trip_title", get_user_ctx(user_id).get("trip_title"))
    out.setdefault("missing_slots", [])
    out.setdefault("search_results", empty_search_results())
    out.setdefault("plan_choices", [])
    out.setdefault("current_plan", None)
    out.setdefault("agent_state", {"intent": "idle", "step": "final", "steps": []})
    out.setdefault("suggestions", [])
    return out


@router.post("/api/chat/reset")
async def reset_chat(payload: Optional[Dict[str, Any]] = Body(default=None)):
    """Accept empty body (avoid 422). Optional payload: user_id, client_trip_id."""
    payload = payload or {}
    user_id = (payload.get("user_id") or "demo_user").strip()
    trip_id = (payload.get("client_trip_id") or "").strip() or "default"
    reset_trip_ctx(user_id=user_id, client_trip_id=trip_id)
    return {"ok": True, "user_id": user_id, "client_trip_id": trip_id}


@router.post("/api/select_choice")
async def select_choice(req: SelectChoiceRequest):
    user_id = (req.user_id or "demo_user").strip()
    choice_id = int(req.choice_id)

    out = handle_choice_select(user_id=user_id, choice_id=choice_id)

    out.setdefault("response", "")
    out.setdefault("travel_slots", normalize_non_core_defaults(get_user_ctx(user_id).get("last_travel_slots") or DEFAULT_SLOTS))
    out["travel_slots"] = normalize_non_core_defaults(out["travel_slots"])
    out.setdefault("trip_title", get_user_ctx(user_id).get("trip_title"))
    out.setdefault("missing_slots", [])
    out.setdefault("search_results", empty_search_results())
    out.setdefault("plan_choices", get_user_ctx(user_id).get("last_plan_choices") or [])
    out.setdefault("current_plan", get_user_ctx(user_id).get("current_plan"))
    out.setdefault("agent_state", {"intent": "edit", "step": "choice_selected", "steps": []})
    out.setdefault("suggestions", ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "โอเค ยืนยันแพลนนี้"])
    return out


@router.get("/api/current_plan")
async def current_plan(user_id: str = "demo_user"):
    user_id = (user_id or "demo_user").strip()
    ctx = get_user_ctx(user_id)
    return {
        "ok": True,
        "user_id": user_id,
        "trip_title": ctx.get("trip_title"),
        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
        "plan_choices": ctx.get("last_plan_choices") or [],
        "current_plan": ctx.get("current_plan"),
    }
