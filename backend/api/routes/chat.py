from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from core.models import ChatRequest, SelectChoiceRequest
from core.orchestrator import orchestrate_chat, DEFAULT_SLOTS, normalize_non_core_defaults, handle_choice_select
from core.context import get_user_ctx
from services.amadeus_service import empty_search_results

router = APIRouter()


@router.post("/api/chat")
async def chat(req: ChatRequest):
    user_id = (req.user_id or "demo_user").strip()
    msg = (req.message or "").strip()
    if not msg:
        raise HTTPException(status_code=400, detail="message is empty")

    existing = dict(DEFAULT_SLOTS)
    if isinstance(req.existing_travel_slots, dict):
        existing.update(req.existing_travel_slots)

    out = await orchestrate_chat(user_id=user_id, user_message=msg, existing_slots=existing)

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
