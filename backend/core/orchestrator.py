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
from services.amadeus_service import amadeus_search_async, empty_search_results, is_invalid_client
from services.gemini_service import generate_trip_title
from core.config import AMADEUS_ENV, AMADEUS_HOST


def parse_choice_selection(user_message: str) -> Optional[int]:
    import re
    m = re.search(r"(?:เลือกช้อยส์|เลือก\s*ช้อยส์|เลือก)\s*(\d+)", user_message or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def handle_choice_select(user_id: str, choice_id: int) -> Dict[str, Any]:
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
            "suggestions": ["กรุงเทพไปโอซาก้า 26 ธ.ค. 3 คืน ผู้ใหญ่ 2 เด็ก 1", "เชียงใหม่ไปกระบี่ 26 ธ.ค. 4 คืน ผู้ใหญ่ 2 เด็ก 1"],
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

    ctx["current_plan"] = chosen
    return {
        "response": f"รับทราบค่ะ ✅ เลือกช้อยส์ {choice_id} แล้ว\nอยากแก้ส่วนไหนก่อนคะ: ไฟลต์ / ที่พัก / วันเดินทาง / จำนวนคืน / จำนวนคน",
        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
        "missing_slots": [],
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": plans,
        "current_plan": chosen,
        "trip_title": ctx.get("trip_title"),
        "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
        "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "โอเค ยืนยันแพลนนี้"],
    }


async def orchestrate_chat(user_id: str, user_message: str, existing_slots: Dict[str, Any]) -> Dict[str, Any]:
    choice_id = parse_choice_selection(user_message)
    if choice_id is not None:
        return handle_choice_select(user_id, choice_id)

    today = date.today().isoformat()

    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(existing_slots or {})
    slots0 = normalize_non_core_defaults(slots0)

    merged, assumptions = slot_extract_merge(today, user_id, user_message, slots0)
    merged = normalize_non_core_defaults(merged)

    assumptions2: List[str] = list(assumptions or [])
    merged = autopilot_fill_core_defaults(merged, assumptions2)

    ctx = get_user_ctx(user_id)
    ctx["last_travel_slots"] = merged

    # Amadeus client is lazily initialized. If .env isn't loaded correctly,
    # we don't want to crash with 500—return a clear response instead.
    try:
        data = await amadeus_search_async(merged, user_iata_cache=ctx.get("iata_cache") or {})
    except RuntimeError as e:
        return {
            "response": (
                "❌ ยังตั้งค่า Amadeus ไม่ครบค่ะ\n"
                f"สาเหตุ: {str(e)}\n\n"
                "วิธีแก้เร็ว ๆ:\n"
                "1) เช็คว่ามีไฟล์ backend/.env จริง และมี AMADEUS_API_KEY / AMADEUS_API_SECRET\n"
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
    if not data.get("ok"):
        err = data.get("error") or {}
        dbg = data.get("debug") or {}

        if is_invalid_client(err):
            return {
                "response": (
                    "❌ เชื่อมต่อ Amadeus ไม่ได้ (invalid_client)\n"
                    "สรุป: API Key/Secret ไม่ถูกต้อง หรือโหลด .env ผิดที่\n"
                    f"- AMADEUS_ENV: {AMADEUS_ENV}\n"
                    f"- AMADEUS_HOST: {AMADEUS_HOST}\n"
                    "กรุณาตรวจสอบ AMADEUS_API_KEY/AMADEUS_API_SECRET แล้ว restart uvicorn ค่ะ"
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

        return {
            "response": "❌ ค้นหา Amadeus ไม่สำเร็จค่ะ (อาจเป็น sandbox data จำกัด หรือเส้นทาง/วันไม่มี)\nลองขยับวัน +1 หรือเปลี่ยนเมืองปลายทางได้ค่ะ",
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

    search_results = data.get("search_results") or empty_search_results()
    dbg = data.get("debug") or {}

    plan_choices = build_plan_choices_3(search_results, merged, dbg)

    ctx["last_search_results"] = search_results
    ctx["last_plan_choices"] = plan_choices
    ctx["current_plan"] = None

    trip_title = generate_trip_title(merged)
    if trip_title:
        ctx["trip_title"] = trip_title

    flights_n = len((search_results.get("flights") or {}).get("data") or [])
    hotels_n = len((search_results.get("hotels") or {}).get("data") or [])

    if not plan_choices:
        return {
            "response": (
                f"ตอนนี้ยังไม่พบตัวเลือกพอสำหรับสร้างช้อยส์ค่ะ\n"
                f"- ไฟลต์: {flights_n} รายการ\n"
                f"- โรงแรม: {hotels_n} รายการ\n"
                "ใน sandbox บางเมืองอาจไม่มีราคาโรงแรม/ไฟลต์ในบางช่วงวันค่ะ\n"
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
            "debug": {"assumptions": assumptions2, "amadeus_debug": dbg},
        }

    blocks: List[str] = []
    for c in plan_choices:
        blocks.append(c.get("display_text", ""))
        blocks.append("\n" + "-" * 42 + "\n")

    header = (
        f"ฉันหาได้แล้วค่ะ (Amadeus {('Sandbox' if AMADEUS_ENV=='test' else 'Production')})\n"
        f"- ไฟลต์: {flights_n} รายการ\n"
        f"- โรงแรม: {hotels_n} รายการ\n\n"
        "นี่คือ 3 ช้อยส์แบบละเอียด (กดการ์ดหรือพิมพ์ “เลือกช้อยส์ X” เพื่อเลือก/แก้ทีละส่วนได้เลยค่ะ)"
    ).strip()

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
        "debug": {"assumptions": assumptions2, "amadeus_debug": dbg},
    }
