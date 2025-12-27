from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

from core.context import get_user_ctx
from core.slots import (
    DEFAULT_SLOTS,
    normalize_non_core_defaults,
    autopilot_fill_core_defaults,
    slot_extract_merge,
)
from core.plan_builder import build_plan_choices_3
from core.trip_planner import plan_trip_from_scratch, get_missing_slots
from services.amadeus_service import amadeus_search_async, empty_search_results, is_invalid_client
from services.gemini_service import generate_trip_title
from core.config import AMADEUS_SEARCH_ENV, AMADEUS_SEARCH_HOST

# Trigger constants (used by api/routes/chat.py)
TRIGGER_USER_MESSAGE = "user_message"
TRIGGER_REFRESH = "refresh"
TRIGGER_CHAT_INIT = "chat_init"
TRIGGER_CHAT_RESET = "chat_reset"


# ----------------------------
# Helpers
# ----------------------------
def parse_choice_selection(user_message: str) -> Optional[int]:
    import re

    m = re.search(r"(?:เลือกช้อยส์|เลือก\s*ช้อยส์|เลือก)\s*(\d+)", user_message or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def is_confirm_intent(user_message: str) -> bool:
    t = (user_message or "").strip().lower()
    if not t:
        return False
    keys = [
        "ยืนยัน",
        "ยืนยันจอง",
        "confirm",
        "book",
        "จองเลย",
        "โอเคยืนยัน",
        "ตกลงยืนยัน",
    ]
    return any(k in t for k in keys)


def handle_choice_select(user_id: str, choice_id: int, *, write_memory: bool = True) -> Dict[str, Any]:
    ctx = get_user_ctx(user_id)
    plans = ctx.get("last_plan_choices") or []
    if not plans:
        return {
            "response": "ตอนนี้ยังไม่มีช้อยส์ให้เลือกค่ะ ลองพิมพ์ทริป เช่น “กรุงเทพไปโอซาก้า 26 ธ.ค. 3 คืน ผู้ใหญ่ 2 เด็ก 1”",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": None,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": "collect", "step": "no_previous_choices", "steps": []},
            "suggestions": [
                "กรุงเทพไปโอซาก้า 26 ธ.ค. 3 คืน ผู้ใหญ่ 2 เด็ก 1",
                "เชียงใหม่ไปกระบี่ 26 ธ.ค. 4 คืน ผู้ใหญ่ 2 เด็ก 1",
            ],
        }

    chosen = next((p for p in plans if int(p.get("id", -1)) == int(choice_id)), None)
    if not chosen:
        return {
            "response": f"ยังไม่พบช้อยส์หมายเลข {choice_id} ในรายการล่าสุดค่ะ ลองเลือก 1–{len(plans)} อีกครั้งนะคะ",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,
            "current_plan": None,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": "present", "step": "choice_not_found", "steps": []},
            "suggestions": ["เลือกช้อยส์ 1", "เลือกช้อยส์ 2", "เลือกช้อยส์ 3"],
        }

    if write_memory:
        ctx["current_plan"] = chosen

    return {
        "response": (
            f"รับทราบค่ะ ✅ เลือกช้อยส์ {choice_id} แล้ว\n"
            "พิมพ์แก้ไขเฉพาะส่วนได้เลย เช่น:\n"
            "- “ขอไฟลต์เช้ากว่านี้”\n"
            "- “ขอที่พักถูกลง”\n"
            "- “ขยับวัน +1”\n"
            "หรือพิมพ์ “ยืนยันจอง” ได้เลยค่ะ"
        ),
        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
        "missing_slots": [],
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": plans,
        "current_plan": chosen,
        "trip_title": ctx.get("trip_title"),
        "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
        "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "ยืนยันจอง"],
    }


# ----------------------------
# Main Orchestrator
# ----------------------------
async def orchestrate_chat(
    user_id: str,
    user_message: str,
    existing_slots: Dict[str, Any],
    *,
    write_memory: bool = True,
) -> Dict[str, Any]:
    # 1) explicit choice select by text
    choice_id = parse_choice_selection(user_message)
    if choice_id is not None:
        return handle_choice_select(user_id, choice_id, write_memory=write_memory)

    ctx = get_user_ctx(user_id)

    # 2) confirm intent after a choice is selected
    if is_confirm_intent(user_message) and ctx.get("current_plan"):
        return {
            "response": (
                "พร้อมจองแล้วค่ะ ✅\n"
                "กำลังส่งคำขอจองไปที่ Amadeus Sandbox...\n"
                "(ถ้าจองสำเร็จ ระบบจะแจ้งว่า “จองเสร็จสิ้น กรุณาชำระเงินเพื่อยืนยันจอง”)"
            ),
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": ctx.get("last_plan_choices") or [],
            "current_plan": ctx.get("current_plan"),
            "agent_state": {"intent": "booking", "step": "confirm_booking", "steps": []},
            "suggestions": [],
        }

    today = date.today().isoformat()

    # baseline slots
    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(existing_slots or {})
    slots0 = normalize_non_core_defaults(slots0)

    # 3) merge new message into slots (Gemini slot extraction + regex)
    merged, assumptions = slot_extract_merge(today, user_id, user_message, slots0)
    merged = normalize_non_core_defaults(merged)

    assumptions2: List[str] = list(assumptions or [])
    
    # Check if we have enough info to search, or need to ask questions
    missing = get_missing_slots(merged)
    has_vague_request = not merged.get("destination") or (
        merged.get("destination") and merged.get("destination").lower() in {"เที่ยว", "ไปเที่ยว", "ทริป", "vacation", "travel"}
    )
    
    # If user has vague request or missing critical info, use trip planner
    if has_vague_request or (missing and len(missing) >= 2):
        planning_result = plan_trip_from_scratch(user_message, merged, today)
        
        if planning_result.get("action") == "ask_question":
            # Ask a question to gather more info
            question = planning_result.get("question") or "อยากไปเที่ยวที่ไหนคะ?"
            suggestions = planning_result.get("suggestions") or []
            festival_suggestions = planning_result.get("festival_suggestions") or []
            
            response_text = question
            if festival_suggestions:
                response_text += "\n\n🎉 แนะนำทริปตามเทศกาล/เดือน:\n"
                for fest in festival_suggestions[:5]:  # Limit to 5 suggestions
                    response_text += f"- {fest.get('festival')} → {fest.get('destination')}\n"
                    response_text += f"  {fest.get('description')}\n"
            
            return {
                "response": response_text,
                "travel_slots": merged,
                "missing_slots": missing,
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "collect", "step": "asking_preferences", "steps": missing},
                "suggestions": suggestions + [f"{s}" for s in (planning_result.get("suggestions") or [])],
                "debug": {"assumptions": assumptions2, "planning": planning_result},
            }
        elif planning_result.get("action") == "suggest_destinations":
            # Suggest destinations based on month/festival
            suggestions = planning_result.get("suggestions") or []
            festival_suggestions = planning_result.get("festival_suggestions") or []
            
            response_text = "นี่คือทริปแนะนำตามที่คุณสนใจค่ะ:\n\n"
            if festival_suggestions:
                for fest in festival_suggestions[:5]:
                    response_text += f"🎉 {fest.get('festival')}\n"
                    response_text += f"📍 {fest.get('destination')}\n"
                    response_text += f"💡 {fest.get('description')}\n\n"
            
            if suggestions:
                response_text += "💡 ตัวอย่างทริปที่แนะนำ:\n"
                for sug in suggestions[:3]:
                    response_text += f"- {sug}\n"
                response_text += "\n"
            
            response_text += "พิมพ์ชื่อเมืองหรือประเทศที่สนใจได้เลยค่ะ เช่น:\n"
            response_text += "- 'ไปญี่ปุ่น' หรือ 'ไปดูซากุระ'\n"
            response_text += "- 'ไปเกาหลี' หรือ 'ไปยุโรป'\n"
            response_text += "- 'ไปภูเก็ต' หรือ 'ไปเกาะสมุย'"
            
            return {
                "response": response_text,
                "travel_slots": merged,
                "missing_slots": missing,
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "collect", "step": "suggesting_destinations", "steps": missing},
                "suggestions": suggestions,
                "debug": {"assumptions": assumptions2, "planning": planning_result},
            }
    
    # Continue with normal flow - fill defaults and search
    # Only force defaults if we have enough info to search
    merged = autopilot_fill_core_defaults(merged, assumptions2, force_defaults=(not missing or len(missing) < 2))

    # store slots
    if write_memory:
        ctx["last_travel_slots"] = merged

    # Keep an IATA cache per user (used by both ref-data and Gemini-based resolution).
    iata_cache = ctx.get("iata_cache")
    if not isinstance(iata_cache, dict):
        iata_cache = {}
    if write_memory:
        ctx["iata_cache"] = iata_cache

    # 4) Amadeus search
    try:
        data = await amadeus_search_async(merged, user_iata_cache=iata_cache)
    except RuntimeError as e:
        return {
            "response": (
                "❌ ยังตั้งค่า Amadeus ไม่ครบค่ะ\n"
                f"สาเหตุ: {str(e)}\n\n"
                "วิธีแก้เร็ว ๆ:\n"
                "1) เช็คว่า backend/.env มี AMADEUS_SEARCH_API_KEY / AMADEUS_SEARCH_API_SECRET (หรือ legacy AMADEUS_API_KEY/AMADEUS_API_SECRET)\n"
                "2) รัน uvicorn จากโฟลเดอร์ backend หรือกำหนด DOTENV_PATH=backend/.env\n"
                "3) restart uvicorn --reload ใหม่"
            ),
            "travel_slots": merged,
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": None,
            "agent_state": {"intent": "error", "step": "env_missing", "steps": []},
            "suggestions": ["ตรวจ backend/.env", "ตั้ง DOTENV_PATH", "restart uvicorn"],
            "debug": {"assumptions": assumptions2},
        }

    # 5) Amadeus error handling
    if not data.get("ok"):
        err = data.get("error") or {}
        dbg = data.get("debug") or {}

        if is_invalid_client(err):
            return {
                "response": (
                    "❌ เชื่อมต่อ Amadeus ไม่ได้ (invalid_client)\n"
                    "สรุป: API Key/Secret ไม่ถูกต้อง หรือโหลด .env ผิดที่\n"
                    f"- AMADEUS_SEARCH_ENV: {AMADEUS_SEARCH_ENV}\n"
                    f"- AMADEUS_SEARCH_HOST: {AMADEUS_SEARCH_HOST}\n"
                    "กรุณาตรวจสอบ AMADEUS_SEARCH_API_KEY/AMADEUS_SEARCH_API_SECRET (หรือ legacy AMADEUS_API_KEY/AMADEUS_API_SECRET) แล้ว restart uvicorn ค่ะ"
                ),
                "travel_slots": merged,
                "missing_slots": [],
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "error", "step": "amadeus_invalid_client", "steps": []},
                "suggestions": ["ตรวจ .env ในโฟลเดอร์ backend", "ลองสร้าง API Key/Secret ใหม่ใน Amadeus Self-Service"],
                "debug": {"error": err, "debug": dbg, "assumptions": assumptions2},
            }

        # Generic errors: show the real reason (status + message) and the actual host/env.
        status = (err or {}).get("status")
        body = (err or {}).get("body")
        msg = None
        if isinstance(body, dict):
            msg = body.get("message") or body.get("error_description") or body.get("error")
        elif isinstance(body, str):
            msg = body

        hint = "ลองขยับวัน +1 หรือเปลี่ยนเมืองปลายทางได้ค่ะ"
        if status == 422 and isinstance(msg, str):
            if "resolve" in msg or "IATA" in msg:
                hint = "ลองพิมพ์เมืองให้ชัดขึ้น (เช่น ‘Bangkok’/‘BKK’, ‘Tokyo’/‘NRT’) หรือเปลี่ยนเมืองปลายทางได้ค่ะ"
            elif "past" in msg:
                hint = "วันที่ที่เลือกเป็นอดีตค่ะ ลองขยับวันไปข้างหน้าใหม่"

        return {
            "response": (
                "❌ ค้นหา Amadeus ไม่สำเร็จค่ะ\n"
                f"- Search: {AMADEUS_SEARCH_HOST} ({AMADEUS_SEARCH_ENV})\n"
                f"- Status: {status}\n"
                f"- Reason: {msg or str(err) or 'unknown'}\n"
                f"{hint}"
            ),
            "travel_slots": merged,
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": None,
            "agent_state": {"intent": "error", "step": "amadeus_error", "steps": []},
            "suggestions": ["ขยับวัน +1", "ขยับวัน -1", "เปลี่ยนเมืองปลายทาง"],
            "debug": {"error": err, "debug": dbg, "assumptions": assumptions2},
        }

    # 6) Build choices
    search_results = data.get("search_results") or empty_search_results()
    amadeus_dbg = data.get("debug") or {}

    plan_choices = build_plan_choices_3(search_results, merged, amadeus_dbg)

    # Persist search results + choices
    if write_memory:
        ctx["last_search_results"] = search_results
        ctx["last_plan_choices"] = plan_choices

    # Trip title
    trip_title = generate_trip_title(merged)
    if trip_title and write_memory:
        ctx["trip_title"] = trip_title

    flights_n = len((search_results.get("flights") or {}).get("data") or [])
    hotels_n = len((search_results.get("hotels") or {}).get("data") or [])

    # 7) If user already had a selected plan, treat this message as "edit" and keep workflow continuous
    had_selected = bool(ctx.get("current_plan"))
    if had_selected and plan_choices:
        # Auto-pick the recommended one (id=1) as new current plan after edits
        # (You can later refine to keep closest matching plan)
        chosen = next((p for p in plan_choices if int(p.get("id", -1)) == 1), None) or plan_choices[0]
        if write_memory:
            ctx["current_plan"] = chosen

        # Build summary message
        summary_parts = []
        if chosen.get("flight"):
            f = chosen.get("flight")
            first_seg = (f.get("segments") or [{}])[0] if f.get("segments") else {}
            last_seg = (f.get("segments") or [{}])[-1] if f.get("segments") else {}
            origin = first_seg.get("from") or ""
            dest = last_seg.get("to") or ""
            if origin and dest:
                summary_parts.append(f"✈️ ไฟลต์: {origin} → {dest}")
        if chosen.get("hotel"):
            h = chosen.get("hotel")
            hotel_name = h.get("hotelName") or ""
            if hotel_name:
                summary_parts.append(f"🏨 ที่พัก: {hotel_name}")
        if chosen.get("total_price"):
            price = chosen.get("total_price")
            summary_parts.append(f"💰 ราคารวม: {price:,.0f} THB")

        summary_text = "\n".join(summary_parts) if summary_parts else ""

        return {
            "response": (
                "อัปเดตตามที่ขอแล้วค่ะ ✅\n"
                f"(Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n\n"
                "📋 สรุปแพลนล่าสุด:\n"
                + (summary_text + "\n\n" if summary_text else "")
                + "ถ้าจะปรับต่อ พิมพ์เฉพาะส่วนได้เลย เช่น:\n"
                "- “ขอที่พักถูกลง”\n"
                "- “ขอไฟลต์เช้ากว่านี้”\n"
                "- “ขยับวัน +1”\n\n"
                "หรือพิมพ์ “ยืนยันจอง” เพื่อจองเลยค่ะ"
            ),
            "travel_slots": merged,
            "trip_title": ctx.get("trip_title"),
            "missing_slots": [],
            "search_results": search_results,
            "plan_choices": plan_choices,
            "current_plan": chosen,
            "agent_state": {"intent": "edit", "step": "edited_rebuilt", "steps": []},
            "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "ยืนยันจอง"],
            "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg},
        }

    # 8) No choices -> guidance
    if not plan_choices:
        return {
            "response": (
                "ตอนนี้ยังไม่พบตัวเลือกพอสำหรับสร้างช้อยส์ค่ะ\n"
                f"- ไฟลต์: {flights_n} รายการ\n"
                f"- โรงแรม: {hotels_n} รายการ\n"
                "ลองขยับวัน +1 หรือเปลี่ยนเมืองดูได้เลย"
            ),
            "travel_slots": merged,
            "trip_title": ctx.get("trip_title"),
            "missing_slots": [],
            "search_results": search_results,
            "plan_choices": [],
            "current_plan": None,
            "agent_state": {"intent": "needs_adjust", "step": "no_choices", "steps": []},
            "suggestions": ["ขยับวัน +1", "ขยับวัน -1", "เปลี่ยนเมืองปลายทาง"],
            "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg},
        }

    # 9) Present choices
    blocks: List[str] = []
    for c in plan_choices:
        blocks.append(c.get("display_text", ""))
        blocks.append("\n" + "-" * 42 + "\n")

    choices_count = len(plan_choices)
    header = (
        f"ฉันหาได้แล้วค่ะ (Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n"
        f"- ไฟลต์: {flights_n} รายการ\n"
        f"- โรงแรม: {hotels_n} รายการ\n\n"
        f"นี่คือ {choices_count} ช้อยส์แบบละเอียด (เรียงตามราคาถูกก่อน) (กดการ์ดหรือพิมพ์ “เลือกช้อยส์ X” เพื่อเลือก/แก้ทีละส่วนได้เลยค่ะ)"
    ).strip()

    # IMPORTANT: do not clear current_plan here; let it be None until user selects
    if write_memory and not had_selected:
        ctx["current_plan"] = None

    return {
        "response": header + "\n\n" + "\n".join(blocks).strip(),
        "travel_slots": merged,
        "trip_title": ctx.get("trip_title"),
        "missing_slots": [],
        "search_results": search_results,
        "plan_choices": plan_choices,
        "current_plan": None,
        "agent_state": {"intent": "present", "step": "3_choices_ready", "steps": []},
        "suggestions": ["เลือกช้อยส์ 1", "ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1"],
        "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg},
    }
