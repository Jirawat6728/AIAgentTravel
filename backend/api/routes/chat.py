from __future__ import annotations

from typing import Any, Dict, Optional
import time
import json
import asyncio

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse

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
    
    # orchestrate_chat now handles V2/V3 internally based on USE_V3_ORCHESTRATOR flag
    out = await orchestrate_chat(user_id=user_id, user_message=msg, existing_slots=existing, trip_id=trip_id, write_memory=write_memory)

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


@router.post("/api/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    SSE endpoint สำหรับ realtime status updates
    ส่งสถานะการทำงานของ Agent แบบ realtime
    """
    user_id = (req.user_id or "demo_user").strip()
    msg = (req.message or "").strip()
    trigger = (req.trigger or TRIGGER_USER_MESSAGE).strip()
    trip_id = (req.client_trip_id or "").strip() or "default"

    if not msg:
        raise HTTPException(status_code=400, detail="message is empty")

    existing = dict(DEFAULT_SLOTS)
    if isinstance(req.existing_travel_slots, dict):
        existing.update(req.existing_travel_slots)

    # Queue สำหรับ status updates
    status_queue = asyncio.Queue()

    async def status_callback(status: str, message: str, step: str = "", data: Optional[Dict[str, Any]] = None):
        """Callback function สำหรับส่ง status updates"""
        await status_queue.put({
            "status": status,
            "message": message,
            "step": step,
            "data": data,
        })

    async def generate_status_updates():
        """Generate SSE events for status updates"""
        try:
            # Status 1: เริ่มต้น
            yield f"data: {json.dumps({'status': 'starting', 'message': 'กำลังเริ่มต้น...', 'step': 'init'})}\n\n"
            
            # Status 2: กำลังวิเคราะห์ข้อความ
            yield f"data: {json.dumps({'status': 'analyzing', 'message': 'กำลังวิเคราะห์ข้อความของคุณ...', 'step': 'analyze'})}\n\n"
            
            # Status 3: กำลังค้นหา IATA codes
            yield f"data: {json.dumps({'status': 'resolving', 'message': 'กำลังค้นหา IATA codes...', 'step': 'resolve_iata'})}\n\n"
            
            # Status 4: กำลังค้นหาเที่ยวบิน
            yield f"data: {json.dumps({'status': 'searching_flights', 'message': '✈️ กำลังค้นหาเที่ยวบิน...', 'step': 'search_flights'})}\n\n"
            
            # Status 5: กำลังค้นหาที่พัก
            yield f"data: {json.dumps({'status': 'searching_hotels', 'message': '🏨 กำลังค้นหาที่พัก...', 'step': 'search_hotels'})}\n\n"
            
            # Status 6: กำลังค้นหารถเช่า
            yield f"data: {json.dumps({'status': 'searching_cars', 'message': '🚗 กำลังค้นหารถเช่า...', 'step': 'search_cars'})}\n\n"
            
            # Status 7: กำลังค้นหาการขนส่งอื่นๆ
            yield f"data: {json.dumps({'status': 'searching_transport', 'message': '🚆 กำลังค้นหาการขนส่งอื่นๆ (รถไฟ, รถบัส, เรือ)...', 'step': 'search_transport'})}\n\n"
            
            # Status 8: กำลังสร้าง itinerary
            yield f"data: {json.dumps({'status': 'generating_itinerary', 'message': '📅 กำลังสร้าง Day-by-Day Itinerary...', 'step': 'generate_itinerary'})}\n\n"
            
            # Status 9: กำลังประมวลผลผลลัพธ์
            yield f"data: {json.dumps({'status': 'processing', 'message': 'กำลังประมวลผลผลลัพธ์...', 'step': 'process'})}\n\n"
            
            # เรียก orchestrate_chat จริงๆ
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
            out.setdefault("slot_intent", None)  # ✅ Slot editing intent
            out.setdefault("slot_choices", [])  # ✅ Slot-specific choices

            # Status 10: เสร็จสิ้น
            yield f"data: {json.dumps({'status': 'completed', 'message': 'เสร็จสิ้น!', 'step': 'completed', 'data': out})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'status': 'error', 'message': f'เกิดข้อผิดพลาด: {str(e)}', 'step': 'error'})}\n\n"

    return StreamingResponse(
        generate_status_updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    # Set defaults
    if not out.get("response"):
        out["response"] = ""
    if not out.get("travel_slots"):
        out["travel_slots"] = normalize_non_core_defaults(get_user_ctx(user_id).get("last_travel_slots") or DEFAULT_SLOTS)
    out["travel_slots"] = normalize_non_core_defaults(out["travel_slots"])
    if not out.get("trip_title"):
        out["trip_title"] = get_user_ctx(user_id).get("trip_title")
    if not out.get("missing_slots"):
        out["missing_slots"] = []
    if not out.get("search_results"):
        out["search_results"] = empty_search_results()
    # ✅ CRITICAL: Ensure plan_choices is ALWAYS set
    if not out.get("plan_choices"):
        out["plan_choices"] = get_user_ctx(user_id).get("last_plan_choices") or []
    
    # ✅ CRITICAL: Ensure current_plan is ALWAYS set
    # Priority: 1) from handle_choice_select output, 2) from plan_choices by choice_id, 3) from context
    import logging
    
    plans = out.get("plan_choices") or []
    
    if not out.get("current_plan"):
        # Method 1: Try to find from plan_choices by choice_id (most reliable)
        if plans:
            # Try by id field first
            chosen_fallback = next((p for p in plans if int(p.get("id", -1)) == int(choice_id)), None)
            if not chosen_fallback and choice_id > 0 and choice_id <= len(plans):
                # Try by index (choice_id is 1-based)
                chosen_fallback = plans[choice_id - 1]
                logging.info(f"select_choice: Using plan from plan_choices by index [{choice_id - 1}]")
            
            if chosen_fallback:
                out["current_plan"] = chosen_fallback
                logging.info(f"select_choice: Using fallback plan from plan_choices (choice_id={choice_id})")
        
        # Method 2: Try context as last resort
        if not out.get("current_plan"):
            ctx_plan = get_user_ctx(user_id).get("current_plan")
            if ctx_plan:
                out["current_plan"] = ctx_plan
                logging.debug(f"select_choice: Using current_plan from context for choice_id={choice_id}")
    
    # ✅ Final check - if still no current_plan, this is a critical error
    if not out.get("current_plan"):
        logging.error(f"select_choice: CRITICAL - No current_plan for choice_id={choice_id}, user_id={user_id}")
        logging.error(f"select_choice: plans_count={len(plans)}, available_ids={[p.get('id') for p in plans[:10]]}")
        # ✅ Last resort: return first plan if available
        if plans and len(plans) > 0:
            out["current_plan"] = plans[0]
            logging.warning(f"select_choice: Using first plan as last resort fallback")
    
    if not out.get("agent_state"):
        out["agent_state"] = {"intent": "edit", "step": "choice_selected", "steps": []}
    if not out.get("suggestions"):
        out["suggestions"] = ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "โอเค ยืนยันแพลนนี้"]
    
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
