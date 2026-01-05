from __future__ import annotations

import asyncio
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from core.context import get_user_ctx, reset_trip_ctx, update_user_ctx, add_conversation_summary
from core.memory_policy import MemoryPolicy
from core.proactive_flow import ProactiveSuggestions
from core.session_store import SessionStore
from core.planner import Planner, PlannerOutput
from core.executor import Executor, ExecutorOutput
from core.narrator import Narrator, NarratorOutput
from core.conversation_summary import ConversationSummarizer
from core.user_profile_memory import UserProfileMemory
from core.agent_settings import AgentSettings
from core.slots import (
    DEFAULT_SLOTS,
    normalize_non_core_defaults,
    autopilot_fill_core_defaults,
    slot_extract_merge,
)
from core.slot_manager import SlotManager
from core.router_agent import RouterAgent, RouterIntent
from core.plan_builder import build_plan_choices_3
from core.trip_planner import plan_trip_from_scratch, get_missing_slots
from services.amadeus_service import amadeus_search_async, amadeus_search_section_async, empty_search_results, is_invalid_client
from services.gemini_service import generate_trip_title
from services.slot_intent_service import detect_slot_intent
from services.single_item_intent_service import detect_single_item_intent
from services.segment_action_parser import parse_segment_actions
from core.config import AMADEUS_SEARCH_ENV, AMADEUS_SEARCH_HOST

# Trigger constants (used by api/routes/chat.py)
TRIGGER_USER_MESSAGE = "user_message"
TRIGGER_REFRESH = "refresh"
TRIGGER_CHAT_INIT = "chat_init"
TRIGGER_CHAT_RESET = "chat_reset"


def _should_force_new_search(user_message: str) -> bool:
    """
    ตรวจสอบว่าผู้ใช้ต้องการค้นหาใหม่หรือไม่
    ค้นหาใหม่เฉพาะเมื่อมีคำสั่งชัดเจน
    """
    msg_lower = user_message.lower().strip()
    
    # คำสั่งที่บ่งชี้ว่าต้องการค้นหาใหม่
    force_search_keywords = [
        "ค้นหาใหม่", "หาใหม่", "refresh", "reload", "ค้นหาใหม่", 
        "refresh search", "new search", "ค้นหาใหม่ทั้งหมด",
        "รีเฟรช", "รีโหลด", "ค้นหาใหม่", "หาใหม่ทั้งหมด"
    ]
    
    # ตรวจสอบว่ามีคำสั่งค้นหาใหม่หรือไม่
    for keyword in force_search_keywords:
        if keyword in msg_lower:
            return True
    
    return False


def _get_stock_search_results(ctx: Dict[str, Any], travel_slots: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    ดึงข้อมูล search_results จาก stock (cache) ถ้ามี
    ตรวจสอบว่า travel_slots ตรงกับที่เก็บไว้หรือไม่
    """
    stock_results = ctx.get("last_search_results")
    stock_slots = ctx.get("last_travel_slots") or {}
    
    # ถ้าไม่มี stock results ให้ return None
    if not stock_results:
        return None
    
    # ตรวจสอบว่า travel_slots ตรงกับ stock_slots หรือไม่ (เฉพาะ core fields)
    core_fields = ["origin", "destination", "start_date", "adults", "children"]
    slots_match = True
    
    for field in core_fields:
        stock_value = stock_slots.get(field)
        current_value = travel_slots.get(field)
        
        # ถ้าค่าไม่ตรงกัน ให้ return None (ต้องค้นหาใหม่)
        if stock_value != current_value:
            slots_match = False
            break
    
    # ถ้า slots ตรงกัน ให้ return stock results
    if slots_match:
        return stock_results
    
    return None


# ----------------------------
# Helpers
# ----------------------------
def iso_date_or_none(s: Any) -> Optional[str]:
    """Helper to validate ISO date string."""
    if not s:
        return None
    if isinstance(s, str):
        s = s.strip()
        if len(s) == 10 and s.count("-") == 2:
            try:
                date.fromisoformat(s)
                return s
            except ValueError:
                return None
    return None


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


def _is_general_message(user_message: str) -> bool:
    """
    Detect if message is general conversation (greeting, thanks, goodbye) 
    that doesn't require travel planning processing.
    """
    if not user_message:
        return False
    
    msg_lower = user_message.strip().lower()
    
    # Greetings
    greetings = [
        "สวัสดี", "hello", "hi", "hey", "หวัดดี", "ดี", "ดีค่ะ", "ดีครับ",
        "สวัสดีค่ะ", "สวัสดีครับ", "good morning", "good afternoon", "good evening"
    ]
    
    # Thanks
    thanks = [
        "ขอบคุณ", "thank", "thanks", "ขอบใจ", "ขอบคุณมาก", "thank you",
        "ขอบคุณค่ะ", "ขอบคุณครับ"
    ]
    
    # Goodbye
    goodbyes = [
        "บาย", "bye", "goodbye", "ลาก่อน", "แล้วเจอกัน", "see you",
        "ขอบคุณมาก", "ขอบคุณค่ะแล้วเจอกัน"
    ]
    
    # Simple questions that don't need travel processing
    general_questions = [
        "ทำอะไร", "เป็นไง", "ยังไง", "อะไร", "who are you", "what are you",
        "คุณคืออะไร", "คุณทำอะไรได้", "help", "ช่วย"
    ]
    
    all_general = greetings + thanks + goodbyes + general_questions
    
    # Check if message is ONLY general words (no travel keywords)
    words = msg_lower.split()
    if len(words) <= 3:  # Short messages are more likely to be general
        if any(gen in msg_lower for gen in all_general):
            # But check if it contains travel keywords
            travel_keywords = [
                "เที่ยว", "ทริป", "ไป", "เดินทาง", "เที่ยวบิน", "ที่พัก", "โรงแรม",
                "travel", "trip", "flight", "hotel", "booking", "vacation", "holiday",
                "destination", "เมือง", "ประเทศ", "จอง", "ตั๋ว"
            ]
            if not any(travel in msg_lower for travel in travel_keywords):
                return True
    
    return False


def _try_regex_slot_extraction(user_message: str, existing_slots: Dict[str, Any], today: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Try to extract slots using regex patterns first (avoid Gemini API call for simple cases).
    Returns (merged_slots, assumptions)
    """
    import re
    from datetime import date, timedelta
    
    merged = dict(existing_slots or {})
    assumptions: List[str] = []
    msg = (user_message or "").strip()
    
    # Pattern 1: "ไป X จาก Y"
    m = re.search(r"ไป\s*([^\s]+(?:\s+[^\s]+)*?)\s*จาก\s*([^\s]+(?:\s+[^\s]+)*)", msg)
    if m:
        if not merged.get("destination"):
            merged["destination"] = m.group(1).strip()
            assumptions.append("regex destination from ไปXจากY")
        if not merged.get("origin"):
            merged["origin"] = m.group(2).strip()
            assumptions.append("regex origin from ไปXจากY")
    
    # Pattern 2: "X ไป Y" or "X → Y" or "X-Y" or "X to Y"
    m = re.search(r"([A-Za-zก-๙\.\s]+?)\s*(?:ไป|→|to|-)\s*([A-Za-zก-๙\.\s]+)", msg)
    if m:
        origin_candidate = m.group(1).strip()
        dest_candidate = m.group(2).strip()
        if "จาก" not in origin_candidate and "ไป" not in origin_candidate:
            if not merged.get("origin"):
                merged["origin"] = origin_candidate
                assumptions.append("regex origin from A->B")
            if not merged.get("destination"):
                merged["destination"] = dest_candidate
                assumptions.append("regex destination from A->B")
    
    # Pattern 3: "จาก X ไป Y"
    m = re.search(r"จาก\s*([A-Za-zก-๙\.\s]+?)\s*ไป\s*([A-Za-zก-๙\.\s]+)", msg)
    if m:
        if not merged.get("origin"):
            merged["origin"] = m.group(1).strip()
            assumptions.append("regex origin from จากXไปY")
        if not merged.get("destination"):
            merged["destination"] = m.group(2).strip()
            assumptions.append("regex destination from จากXไปY")
    
    # Date patterns (simple ones)
    date_patterns = [
        (r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", "MM/DD/YYYY"),
        (r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", "YYYY/MM/DD"),
        (r"(\d{1,2})\s+(ม\.?ค|ก\.?พ|มี\.?ค|เม\.?ย|พ\.?ค|มิ\.?ย|ก\.?ค|ส\.?ค|ก\.?ย|ต\.?ค|พ\.?ย|ธ\.?ค)", "DD Month"),
    ]
    
    for pattern, fmt in date_patterns:
        m = re.search(pattern, msg)
        if m and not merged.get("start_date"):
            # Simple date extraction (basic implementation)
            assumptions.append(f"regex date pattern {fmt}")
            break
    
    # Number extraction for adults
    # ✅ รองรับทั้ง "3 คน", "3 ผู้ใหญ่", "3 ผู้", "3 adult", "3 traveler"
    m = re.search(r"(\d+)\s*(?:คน|ผู้ใหญ่|ผู้|adult|adults|traveler|travelers)", msg, re.IGNORECASE)
    if m and not merged.get("adults"):
        try:
            merged["adults"] = int(m.group(1))
            assumptions.append("regex adults from number")
        except:
            pass
    
    return merged, assumptions


def _needs_gemini_extraction(user_message: str, regex_result: Dict[str, Any], existing_slots: Dict[str, Any]) -> bool:
    """
    Determine if we need Gemini API call for slot extraction.
    Return False if regex already extracted enough info.
    """
    # If regex extracted destination and (origin or date), we might not need Gemini
    has_destination = bool(regex_result.get("destination"))
    has_origin = bool(regex_result.get("origin"))
    has_date = bool(regex_result.get("start_date"))
    has_adults = bool(regex_result.get("adults"))
    
    # Simple patterns: destination + (origin OR date) - regex might be enough
    if has_destination and (has_origin or has_date):
        # Check if message is simple (short, no complex context)
        words = user_message.split()
        if len(words) <= 10:  # Short messages are more likely to be fully extractable by regex
            # Check if it contains complex instructions
            complex_keywords = [
                "ถ้า", "หรือ", "แต่", "ยกเว้น", "เฉพาะ", "except", "unless", "if",
                "ปรับ", "แก้", "เปลี่ยน", "edit", "change", "modify",
                "แนะนำ", "suggest", "recommend", "prefer"
            ]
            if not any(kw in user_message.lower() for kw in complex_keywords):
                return False  # Regex is probably enough
    
    # If we got something from regex, but missing critical info, still use Gemini
    if has_destination and not has_date and not has_adults:
        return True  # Need Gemini for date/adults extraction
    
    # Default: use Gemini for complex extraction
    return True


def _handle_general_message(user_message: str) -> str:
    """
    Generate quick response for general messages without heavy processing.
    """
    msg_lower = user_message.strip().lower()
    
    # Greetings
    if any(word in msg_lower for word in ["สวัสดี", "hello", "hi", "hey", "หวัดดี"]):
        return "สวัสดีค่ะ! 😊 ยินดีช่วยวางแผนทริปให้คุณค่ะ\nอยากไปเที่ยวที่ไหนคะ หรือมีอะไรให้ช่วยไหมคะ?"
    
    # Thanks
    if any(word in msg_lower for word in ["ขอบคุณ", "thank", "thanks", "ขอบใจ"]):
        return "ยินดีค่ะ! 😊\nถ้ามีอะไรให้ช่วยเพิ่มเติมเกี่ยวกับการวางแผนทริป บอกได้เลยนะคะ"
    
    # Goodbye
    if any(word in msg_lower for word in ["บาย", "bye", "goodbye", "ลาก่อน"]):
        return "ลาก่อนค่ะ! ขอให้เที่ยวให้สนุกนะคะ ✈️😊\nถ้ามีอะไรอยากถามเพิ่มเติม ติดต่อมาได้เสมอนะคะ"
    
    # Help/Questions
    if any(word in msg_lower for word in ["help", "ช่วย", "ทำอะไร", "คุณคือ"]):
        return "สวัสดีค่ะ! ฉันเป็น AI ที่ช่วยวางแผนทริปให้คุณค่ะ ✈️\n\nฉันสามารถช่วยได้:\n- ค้นหาเที่ยวบินและที่พัก\n- แนะนำทริปตามเทศกาล\n- วางแผนการเดินทาง\n\nลองบอกฉันว่าอยากไปเที่ยวที่ไหนดูสิคะ!"
    
    # Default
    return "สวัสดีค่ะ! 😊 ยินดีช่วยวางแผนทริปให้คุณค่ะ\nบอกฉันว่าอยากไปเที่ยวที่ไหน หรือมีอะไรให้ช่วยไหมคะ?"


def handle_choice_select(user_id: str, choice_id: int, *, write_memory: bool = True, trip_id: str = "default") -> Dict[str, Any]:
    ctx = get_user_ctx(user_id)
    session = SessionStore.get_session(user_id, trip_id)
    agent_state = ctx.get("last_agent_state") or session.get("agent_state") or {}
    slot_workflow = agent_state.get("slot_workflow", {})
    current_slot = slot_workflow.get("current_slot")
    slot_selections = slot_workflow.get("slot_selections", {})
    
    # Check if we're in slot-based workflow
    if current_slot:
        # Handle slot-based selection
        slot_choices = agent_state.get("slot_choices", [])
        if slot_choices and choice_id > 0 and choice_id <= len(slot_choices):
            selected_choice = slot_choices[choice_id - 1]
            slot_type = selected_choice.get("slot") or selected_choice.get("type")
            
            # Save selection
            slot_selections[slot_type] = selected_choice
            
            # Determine next slot
            if slot_type in ["flight", "route"]:
                # ✅ Check if user wants only flight (skip hotel selection)
                single_item_intent_type = ctx.get("single_item_intent_type", "full_trip")
                
                if single_item_intent_type == "flight_only":
                    # User wants only flight - skip to TripSummary
                    flight_obj = selected_choice.get("flight") or selected_choice
                    minimal_plan = {
                        "flight": flight_obj,
                        "total_price": selected_choice.get("total_price", 0),
                        "currency": selected_choice.get("currency", "THB"),
                    }
                    
                    if write_memory:
                        ctx["current_plan"] = minimal_plan
                        update_user_ctx(user_id, {
                            "current_plan": minimal_plan,
                            "last_agent_state": {
                                **agent_state,
                                "intent": "review",
                                "step": "trip_summary",
                                "slot_workflow": {
                                    "current_slot": "summary",
                                    "slot_selections": slot_selections,
                                },
                            },
                        })
                        SessionStore.update_agent_state(user_id, trip_id, {
                            **agent_state,
                            "intent": "review",
                            "step": "trip_summary",
                        })
                    
                    item_name = "เส้นทาง" if slot_type == "route" else "ไฟลต์"
                    return {
                        "response": (
                            f"รับทราบค่ะ ✅ เลือก{item_name} {choice_id} แล้ว\n"
                            f"ราคา: {selected_choice.get('total_price', 0):,.0f} {selected_choice.get('currency', 'THB')}\n\n"
                            "พิมพ์ \"ยืนยันจอง\" เพื่อดำเนินการจองได้เลยค่ะ"
                        ),
                        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                        "missing_slots": [],
                        "trip_title": ctx.get("trip_title"),
                        "search_results": ctx.get("last_search_results") or empty_search_results(),
                        "plan_choices": [],
                        "current_plan": minimal_plan,
                        "agent_state": {"intent": "flight_only", "step": "choice_selected", "steps": []},
                        "suggestions": ["ยืนยันจอง"],
                        "slot_selections": slot_selections,
                    }
                
                # Normal flow: Move to hotel slot
                new_current_slot = "hotel"
                
                # Get itinerary plan if available (for route-based workflow)
                itinerary_plan_data = slot_workflow.get("itinerary_plan")
                accommodation_slots = []
                if itinerary_plan_data and isinstance(itinerary_plan_data, dict):
                    accommodation_slots = itinerary_plan_data.get("accommodation_slots", [])
                
                # Get hotel choices
                from core.slot_builder import build_hotel_choices
                search_results = ctx.get("last_search_results") or empty_search_results()
                travel_slots = ctx.get("last_travel_slots") or {}
                
                # If we have accommodation slots from itinerary, filter hotels by city
                hotel_choices = build_hotel_choices(
                    search_results, 
                    travel_slots, 
                    selected_flight=selected_choice, 
                    limit=10
                )
                
                # Filter hotels by accommodation city if available
                if accommodation_slots:
                    first_accommodation = accommodation_slots[0]
                    city = first_accommodation.get("city")
                    if city:
                        # Filter hotels by city (simplified - would need better city matching)
                        hotel_choices = [
                            h for h in hotel_choices 
                            if city.lower() in (h.get("hotel", {}).get("city", "") or "").lower()
                        ][:10]
                
                new_agent_state = {
                    **agent_state,
                    "slot_workflow": {
                        "current_slot": new_current_slot,
                        "slot_selections": slot_selections,
                        "itinerary_plan": itinerary_plan_data,
                    },
                    "intent": "selecting",
                    "step": "selecting_hotel",
                    "slot_choices": hotel_choices,  # ✅ เก็บ hotel_choices ไว้ใน agent_state
                }
                
                if write_memory:
                    update_user_ctx(user_id, {
                        "last_agent_state": new_agent_state,
                    })
                    SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
                
                item_name = "เส้นทาง" if slot_type == "route" else "ไฟลต์"
                return {
                    "response": (
                        f"รับทราบค่ะ ✅ เลือก{item_name} {choice_id} แล้ว\n\n"
                        f"📋 Slot 2: เลือกที่พัก ({len(hotel_choices)} ช้อยส์)\n"
                        "กดการ์ดหรือพิมพ์ \"เลือกที่พัก X\" เพื่อเลือกได้เลยค่ะ"
                    ),
                    "travel_slots": normalize_non_core_defaults(travel_slots),
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": search_results,
                    "plan_choices": [],  # ✅ ไม่ส่ง plan_choices เมื่อใช้ slot workflow
                    "current_plan": None,
                    "agent_state": new_agent_state,
                    "slot_choices": hotel_choices,  # ✅ ส่ง slot_choices เท่านั้น
                    "slot_intent": "hotel",  # ✅ เพิ่ม slot_intent เพื่อให้ frontend แสดง slotChoices
                    "suggestions": [f"เลือกที่พัก {i+1}" for i in range(min(3, len(hotel_choices)))],
                }
            
            elif slot_type == "hotel":
                # ✅ Check if user wants only hotel (skip flight selection)
                single_item_intent_type = ctx.get("single_item_intent_type", "full_trip")
                
                if single_item_intent_type == "hotel_only":
                    # User wants only hotel - skip to TripSummary
                    hotel_obj = selected_choice.get("hotel") or selected_choice
                    minimal_plan = {
                        "hotel": hotel_obj,
                        "total_price": selected_choice.get("total_price", 0),
                        "currency": selected_choice.get("currency", "THB"),
                    }
                    
                    if write_memory:
                        ctx["current_plan"] = minimal_plan
                        update_user_ctx(user_id, {
                            "current_plan": minimal_plan,
                            "last_agent_state": {
                                **agent_state,
                                "intent": "review",
                                "step": "trip_summary",
                                "slot_workflow": {
                                    "current_slot": "summary",
                                    "slot_selections": slot_selections,
                                },
                            },
                        })
                        SessionStore.update_agent_state(user_id, trip_id, {
                            **agent_state,
                            "intent": "review",
                            "step": "trip_summary",
                        })
                    
                    return {
                        "response": (
                            f"รับทราบค่ะ ✅ เลือกที่พัก {choice_id} แล้ว\n"
                            f"ราคา: {selected_choice.get('total_price', 0):,.0f} {selected_choice.get('currency', 'THB')}\n\n"
                            "พิมพ์ \"ยืนยันจอง\" เพื่อดำเนินการจองได้เลยค่ะ"
                        ),
                        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                        "missing_slots": [],
                        "trip_title": ctx.get("trip_title"),
                        "search_results": ctx.get("last_search_results") or empty_search_results(),
                        "plan_choices": [],
                        "current_plan": minimal_plan,
                        "agent_state": {"intent": "hotel_only", "step": "choice_selected", "steps": []},
                        "suggestions": ["ยืนยันจอง"],
                        "slot_selections": slot_selections,
                    }
                
                # Normal flow: Move to car slot
                new_current_slot = "car"
                
                # Get car choices
                from core.slot_builder import build_car_choices
                search_results = ctx.get("last_search_results") or empty_search_results()
                travel_slots = ctx.get("last_travel_slots") or {}
                
                car_choices = build_car_choices(
                    search_results,
                    travel_slots,
                    selected_flight=slot_selections.get("flight"),
                    selected_hotel=selected_choice,
                    limit=10
                )
                
                # ✅ ถ้าไม่มี car choices (0 ช้อยส์) → ไปที่ summary ทันที
                if not car_choices or len(car_choices) == 0:
                    from core.slot_builder import build_trip_summary
                    summary = build_trip_summary(slot_selections, travel_slots)
                    
                    combined_plan = {
                        "flight": slot_selections.get("flight", {}).get("flight"),
                        "hotel": slot_selections.get("hotel", {}).get("hotel"),
                        "total_price": summary.get("total_price", 0),
                        "currency": "THB",
                    }
                    
                    new_agent_state = {
                        **agent_state,
                        "slot_workflow": {
                            "current_slot": "summary",
                            "slot_selections": slot_selections,
                        },
                        "intent": "review",
                        "step": "trip_summary",
                    }
                    
                    if write_memory:
                        ctx["current_plan"] = combined_plan
                        update_user_ctx(user_id, {
                            "last_agent_state": new_agent_state,
                            "current_plan": combined_plan,
                        })
                        SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
                    
                    return {
                        "response": (
                            f"รับทราบค่ะ ✅ เลือกที่พัก {choice_id} แล้ว\n\n"
                            "📋 สรุปทริป:\n"
                            f"{summary.get('summary_text', '')}\n\n"
                            f"💰 ราคารวม: {summary.get('total_price', 0):,.0f} THB\n\n"
                            "ถ้าจะแก้ไขเฉพาะส่วน พิมพ์ได้เลย เช่น:\n"
                            "- \"แก้ไขไฟลต์\"\n"
                            "- \"แก้ไขที่พัก\"\n"
                            "หรือพิมพ์ \"ยืนยันจอง\" เพื่อจองเลยค่ะ"
                        ),
                        "travel_slots": normalize_non_core_defaults(travel_slots),
                        "missing_slots": [],
                        "trip_title": ctx.get("trip_title"),
                        "search_results": search_results,
                        "plan_choices": [],
                        "current_plan": combined_plan,
                        "agent_state": new_agent_state,
                        "suggestions": ["แก้ไขไฟลต์", "แก้ไขที่พัก", "ยืนยันจอง"],
                    }
                
                new_agent_state = {
                    **agent_state,
                    "slot_workflow": {
                        "current_slot": new_current_slot,
                        "slot_selections": slot_selections,
                    },
                    "intent": "selecting",
                    "step": "selecting_car",
                    "slot_choices": car_choices,  # ✅ เก็บ car_choices ไว้ใน agent_state
                }
                
                if write_memory:
                    update_user_ctx(user_id, {
                        "last_agent_state": new_agent_state,
                    })
                    SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
                
                return {
                    "response": (
                        f"รับทราบค่ะ ✅ เลือกที่พัก {choice_id} แล้ว\n\n"
                        f"📋 Slot 3: เลือกรถเช่า ({len(car_choices)} ช้อยส์)\n"
                        "กดการ์ดหรือพิมพ์ \"เลือกรถ X\" เพื่อเลือกได้เลยค่ะ\n"
                        "หรือพิมพ์ \"ข้ามรถ\" เพื่อข้ามไปสรุปทริปได้เลยค่ะ"
                    ),
                    "travel_slots": normalize_non_core_defaults(travel_slots),
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": search_results,
                    "plan_choices": [],  # ✅ ไม่ส่ง plan_choices เมื่อใช้ slot workflow
                    "current_plan": None,
                    "agent_state": new_agent_state,
                    "slot_choices": car_choices,  # ✅ ส่ง slot_choices เท่านั้น
                    "slot_intent": "car",  # ✅ เพิ่ม slot_intent เพื่อให้ frontend แสดง slotChoices
                    "suggestions": [f"เลือกรถ {i+1}" for i in range(min(3, len(car_choices)))] + ["ข้ามรถ"],
                }
            
            elif slot_type == "car":
                # Normal flow: Move to summary
                from core.slot_builder import build_trip_summary
                travel_slots = ctx.get("last_travel_slots") or {}
                summary = build_trip_summary(slot_selections, travel_slots)
                
                # Create combined plan
                combined_plan = {
                    "flight": slot_selections.get("flight", {}).get("flight"),
                    "hotel": slot_selections.get("hotel", {}).get("hotel"),
                    "car": slot_selections.get("car", {}).get("car"),
                    "total_price": summary.get("total_price", 0) + (selected_choice.get("total_price", 0) or 0),
                    "currency": "THB",
                }
                
                new_agent_state = {
                    **agent_state,
                    "slot_workflow": {
                        "current_slot": "summary",
                        "slot_selections": slot_selections,
                    },
                    "intent": "review",
                    "step": "trip_summary",
                }
                
                if write_memory:
                    ctx["current_plan"] = combined_plan
                    update_user_ctx(user_id, {
                        "last_agent_state": new_agent_state,
                        "current_plan": combined_plan,
                    })
                    SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
                
                return {
                    "response": (
                        f"รับทราบค่ะ ✅ เลือกรถเช่า {choice_id} แล้ว\n\n"
                        "📋 สรุปทริป:\n"
                        f"{summary.get('summary_text', '')}\n"
                        f"{'🚗 รถเช่า: ' + str(selected_choice.get('label', 'รถเช่า')) + ' (' + str(selected_choice.get('total_price', 0)) + ' THB)' if selected_choice.get('total_price') else ''}\n\n"
                        f"💰 ราคารวม: {combined_plan.get('total_price', 0):,.0f} THB\n\n"
                        "ถ้าจะแก้ไขเฉพาะส่วน พิมพ์ได้เลย เช่น:\n"
                        "- \"แก้ไขไฟลต์\"\n"
                        "- \"แก้ไขที่พัก\"\n"
                        "- \"แก้ไขรถ\"\n"
                        "หรือพิมพ์ \"ยืนยันจอง\" เพื่อจองเลยค่ะ"
                    ),
                    "travel_slots": normalize_non_core_defaults(travel_slots),
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": ctx.get("last_search_results") or empty_search_results(),
                    "plan_choices": [],
                    "current_plan": combined_plan,
                    "agent_state": new_agent_state,
                    "suggestions": ["แก้ไขไฟลต์", "แก้ไขที่พัก", "แก้ไขรถ", "ยืนยันจอง"],
                }
    
    # Fallback to original plan_choices logic
    plans = ctx.get("last_plan_choices") or []
    
    # Debug: log available plans
    import logging
    logging.debug(f"handle_choice_select: choice_id={choice_id}, plans_count={len(plans)}, plan_ids={[p.get('id') for p in plans[:10]]}")
    
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

    # ✅ Try multiple ways to find the choice
    chosen = None
    
    # Method 1: Match by id field
    chosen = next((p for p in plans if int(p.get("id", -1)) == int(choice_id)), None)
    
    # Method 2: If not found, try by index (choice_id is 1-based)
    if not chosen and choice_id > 0 and choice_id <= len(plans):
        chosen = plans[choice_id - 1]
        import logging
        logging.info(f"handle_choice_select: Found choice by index {choice_id - 1} for choice_id={choice_id}")
    
    if not chosen:
        import logging
        logging.warning(f"handle_choice_select: Choice {choice_id} not found in {len(plans)} plans. Available IDs: {[p.get('id') for p in plans[:10]]}")
        return {
            "response": f"ยังไม่พบช้อยส์หมายเลข {choice_id} ในรายการล่าสุดค่ะ ลองเลือก 1–{len(plans)} อีกครั้งนะคะ",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,  # ✅ Always return plans even if choice not found
            "current_plan": None,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": "present", "step": "choice_not_found", "steps": []},
            "suggestions": ["เลือกช้อยส์ 1", "เลือกช้อยส์ 2", "เลือกช้อยส์ 3"],
        }
    
    # Debug: log chosen plan
    import logging
    logging.debug(f"Choice {choice_id} selected: has_flight={bool(chosen.get('flight'))}, has_hotel={bool(chosen.get('hotel'))}, total_price={chosen.get('total_price')}")

    # ✅ Check if this is a segment replacement (from slot_choices with target_segments)
    agent_state = ctx.get("last_agent_state", {})
    target_segments = agent_state.get("target_segments")
    slot_choices = agent_state.get("slot_choices", [])
    
    # ✅ If we have slot_choices and target_segments, this is segment replacement
    if target_segments and isinstance(target_segments, list) and slot_choices:
        if choice_id > 0 and choice_id <= len(slot_choices):
            chosen_slot = slot_choices[choice_id - 1]
            current_plan = ctx.get("current_plan")
            
            if not current_plan:
                # Fallback: use chosen from plans
                if write_memory:
                    ctx["current_plan"] = chosen
                return {
                    "response": f"รับทราบค่ะ ✅ เลือกช้อยส์ {choice_id} แล้ว",
                    "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                    "current_plan": chosen,
                    "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
                }
            
            # Handle hotel segment replacement or addition
            if chosen_slot.get("type") == "hotel":
                chosen_hotel = chosen_slot.get("hotel", {})
                is_add_segment = chosen_slot.get("is_add_segment", False)
                
                if is_add_segment:
                    # ✅ Adding new segment (not replacing)
                    if not current_plan.get("hotel"):
                        current_plan["hotel"] = {"segments": []}
                    hotel_segments = current_plan["hotel"].get("segments", [])
                    
                    # Add new segment
                    hotel_segments.append(chosen_hotel)
                    
                    # Recalculate price
                    new_price = sum(seg.get("price_total", 0) for seg in hotel_segments)
                    current_plan["hotel"]["segments"] = hotel_segments
                    current_plan["hotel"]["price_total"] = new_price
                    current_plan["total_price"] = (
                        current_plan.get("flight", {}).get("total_price", 0) +
                        new_price +
                        current_plan.get("transport", {}).get("price", 0)
                    )
                    
                    if write_memory:
                        ctx["current_plan"] = current_plan
                    
                    return {
                        "response": f"✅ เพิ่มที่พัก segment {len(hotel_segments)} สำเร็จ\nตอนนี้มีที่พัก {len(hotel_segments)} segment(s)",
                        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                        "current_plan": current_plan,
                        "agent_state": {"intent": "edit", "step": "hotel_segment_added", "steps": []},
                        "suggestions": ["แก้ไขที่พัก", "ยืนยันจอง"],
                    }
                
                # Replace specific segments (existing logic)
                if current_plan.get("hotel"):
                    hotel_segments = current_plan["hotel"].get("segments", [])
                    
                    # Replace specific segments
                new_segments = hotel_segments.copy()
                for seg_idx in target_segments:
                    if 0 <= seg_idx < len(new_segments):
                        original_seg = new_segments[seg_idx]
                        # Replace segment, keep segment-specific info
                        new_segments[seg_idx] = {
                            **chosen_hotel,
                            "nights": original_seg.get("nights", chosen_hotel.get("nights")),
                            "cityCode": original_seg.get("cityCode", chosen_hotel.get("cityCode")),
                        }
                
                # Recalculate price
                new_price = sum(seg.get("price_total", 0) or seg.get("price", 0) for seg in new_segments)
                
                # Update plan
                current_plan["hotel"]["segments"] = new_segments
                current_plan["hotel"]["price_total"] = new_price
                current_plan["total_price"] = (
                    current_plan.get("flight", {}).get("total_price", 0) +
                    new_price +
                    current_plan.get("transport", {}).get("price", 0)
                )
                
                if write_memory:
                    ctx["current_plan"] = current_plan
                    ctx["last_agent_state"] = {}  # Clear after use
                
                segment_nums = [str(idx + 1) for idx in target_segments]
                return {
                    "response": f"✅ แก้ไขที่พัก segment {', '.join(segment_nums)} เป็นช้อยส์ {choice_id} สำเร็จ",
                    "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                    "current_plan": current_plan,
                    "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
                    "suggestions": ["แก้ไขที่พัก", "ยืนยันจอง"],
                }
            
            # Handle flight segment replacement
            elif chosen_slot.get("type") == "flight" and current_plan.get("flight"):
                flight_segments = current_plan["flight"].get("segments", [])
                chosen_flight = chosen_slot.get("flight", {})
                chosen_segments = chosen_flight.get("segments", [])
                
                # Replace specific segments
                new_segments = flight_segments.copy()
                
                for i, seg_idx in enumerate(target_segments):
                    if 0 <= seg_idx < len(new_segments) and i < len(chosen_segments):
                        new_seg = chosen_segments[i]
                        
                        # ✅ Validate connection
                        # Check previous segment
                        if seg_idx > 0:
                            prev_seg = new_segments[seg_idx - 1]
                            if prev_seg.get("to") != new_seg.get("from"):
                                return {
                                    "response": f"⚠️ Segment {seg_idx + 1} ไม่เชื่อมต่อกับ segment {seg_idx}\n{prev_seg.get('to')} → {new_seg.get('from')}",
                                    "current_plan": current_plan,
                                    "agent_state": {"intent": "edit", "step": "flight_connection_error"},
                                }
                        
                        # Check next segment
                        if seg_idx < len(new_segments) - 1:
                            next_seg = new_segments[seg_idx + 1]
                            if new_seg.get("to") != next_seg.get("from"):
                                return {
                                    "response": f"⚠️ Segment {seg_idx + 1} ไม่เชื่อมต่อกับ segment {seg_idx + 2}\n{new_seg.get('to')} → {next_seg.get('from')}",
                                    "current_plan": current_plan,
                                    "agent_state": {"intent": "edit", "step": "flight_connection_error"},
                                }
                        
                        # Replace segment
                        new_segments[seg_idx] = new_seg
                
                # Recalculate price and duration
                new_price = chosen_flight.get("total_price", 0)
                total_duration = sum(seg.get("duration_sec", 0) for seg in new_segments)
                
                # Update plan
                current_plan["flight"]["segments"] = new_segments
                current_plan["flight"]["total_price"] = new_price
                current_plan["flight"]["total_duration_sec"] = total_duration
                current_plan["flight"]["is_non_stop"] = len(new_segments) == 1
                current_plan["flight"]["num_stops"] = len(new_segments) - 1
                
                current_plan["total_price"] = (
                    new_price +
                    current_plan.get("hotel", {}).get("price_total", 0) +
                    current_plan.get("transport", {}).get("price", 0)
                )
                
                if write_memory:
                    ctx["current_plan"] = current_plan
                    ctx["last_agent_state"] = {}  # Clear after use
                
                segment_nums = [str(idx + 1) for idx in target_segments]
                return {
                    "response": f"✅ แก้ไขไฟลต์ segment {', '.join(segment_nums)} เป็นช้อยส์ {choice_id} สำเร็จ",
                    "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
                    "current_plan": current_plan,
                    "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
                    "suggestions": ["แก้ไขไฟลต์", "ยืนยันจอง"],
                }

    if write_memory:
        ctx["current_plan"] = chosen
    
    # Check if this is a single-item choice (flight-only or hotel-only)
    choice_type = chosen.get("type")
    is_single_item = choice_type in {"flight", "hotel"}
    
    if is_single_item:
        # For single-item choices, create a minimal plan structure
        if choice_type == "flight":
            minimal_plan = {
                "flight": chosen.get("flight"),
                "total_price": chosen.get("total_price", 0),
                "currency": chosen.get("currency", "THB"),
            }
        else:  # hotel
            minimal_plan = {
                "hotel": chosen.get("hotel"),
                "total_price": chosen.get("total_price", 0),
                "currency": chosen.get("currency", "THB"),
            }
        
        if write_memory:
            ctx["current_plan"] = minimal_plan
        
        item_name = "เที่ยวบิน" if choice_type == "flight" else "ที่พัก"
        return {
            "response": (
                f"รับทราบค่ะ ✅ เลือก{item_name} {choice_id} แล้ว\n"
                f"ราคา: {chosen.get('total_price', 0):,.0f} {chosen.get('currency', 'THB')}\n\n"
                "พิมพ์ \"ยืนยันจอง\" เพื่อดำเนินการจองได้เลยค่ะ"
            ),
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,
            "current_plan": minimal_plan,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": choice_type, "step": "choice_selected", "steps": []},
            "suggestions": ["ยืนยันจอง"],
            "slot_selections": {},
        }
    
    # Full trip choice
    # ✅ Ensure chosen is not None before returning
    if not chosen:
        import logging
        logging.error(f"handle_choice_select: chosen is None for choice_id={choice_id}")
        return {
            "response": f"เกิดข้อผิดพลาดในการเลือกช้อยส์ {choice_id} กรุณาลองใหม่อีกครั้งค่ะ",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,
            "current_plan": None,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": "error", "step": "choice_selection_error", "steps": []},
            "suggestions": ["ลองใหม่", "เลือกช้อยส์ 1"],
        }
    
    # ✅ Final validation: ensure chosen is valid
    if not chosen:
        import logging
        logging.error(f"handle_choice_select: chosen is None for choice_id={choice_id} after validation")
        return {
            "response": f"เกิดข้อผิดพลาดในการเลือกช้อยส์ {choice_id} กรุณาลองใหม่อีกครั้งค่ะ",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": plans,
            "current_plan": None,
            "trip_title": ctx.get("trip_title"),
            "agent_state": {"intent": "error", "step": "choice_selection_error", "steps": []},
            "suggestions": ["ลองใหม่", "เลือกช้อยส์ 1"],
        }
    
    # ✅ Log successful selection
    import logging
    logging.info(f"handle_choice_select: Successfully selected choice_id={choice_id}, has_flight={bool(chosen.get('flight'))}, has_hotel={bool(chosen.get('hotel'))}")
    
    return {
        "response": (
            f"รับทราบค่ะ ✅ เลือกช้อยส์ {choice_id} แล้ว\n"
            "พิมพ์แก้ไขเฉพาะส่วนได้เลย เช่น:\n"
            "- “ขอไฟลต์เช้ากว่านี้”\n"
            "- “ขอที่พักถูกลง”\n"
            "- “ขยับวัน +1”\n"
            "หรือพิมพ์ \"ยืนยันจอง\" ได้เลยค่ะ"
        ),
        "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
        "missing_slots": [],
        "search_results": ctx.get("last_search_results") or empty_search_results(),
        "plan_choices": plans,
        "current_plan": chosen,  # ✅ Return chosen plan (guaranteed to be not None)
        "trip_title": ctx.get("trip_title"),
        "agent_state": {"intent": "edit", "step": "choice_selected", "steps": []},
        "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "ยืนยันจอง"],
        "slot_selections": {},  # ✅ Track selected slots
    }


async def handle_slot_edit(
    user_id: str,
    user_message: str,
    existing_slots: Dict[str, Any],
    slot_intent: str,
    current_plan: Dict[str, Any],
    *,
    write_memory: bool = True,
) -> Dict[str, Any]:
    """Handle editing a specific slot (flight, hotel, transport, dates, pax)."""
    ctx = get_user_ctx(user_id)
    today = date.today().isoformat()
    
    # ✅ Check for segment-specific actions (edit/delete/add by index)
    if slot_intent == "hotel" and current_plan:
        hotel = current_plan.get("hotel", {})
        hotel_segments = hotel.get("segments", [])
        
        if hotel_segments or True:  # Allow add even if no segments yet
            actions = parse_segment_actions(user_message)
            import logging
            logging.info(f"handle_slot_edit (hotel): parsed actions={actions}, hotel_segments_count={len(hotel_segments)}")
            
            # ✅ Handle add segment actions (เพิ่มที่พัก N segment)
            if actions.get("add", 0) > 0:
                num_to_add = actions["add"]
                # For now, we'll search for new hotels and let user choose
                # This will be handled by the normal hotel search flow below
                # We'll add a flag to indicate we want to add segments
                import logging
                logging.info(f"User wants to add {num_to_add} hotel segment(s)")
                # Continue to normal hotel search, but we'll track this in context
                if write_memory:
                    ctx["pending_add_segments"] = num_to_add
            
            # ✅ Handle remove segment actions (ลดที่พัก N segment)
            # "ลด" means remove from the end
            remove_patterns = [
                r'ลดที่พัก\s*(\d+)\s*segment',
                r'ลดที่พัก\s*(\d+)',
                r'ลดโรงแรม\s*(\d+)\s*segment',
                r'ลดโรงแรม\s*(\d+)',
            ]
            import re
            num_to_remove = 0
            for pattern in remove_patterns:
                matches = re.finditer(pattern, user_message, re.IGNORECASE)
                for match in matches:
                    num_to_remove = max(num_to_remove, int(match.group(1)))
            
            if num_to_remove > 0 and hotel_segments:
                if num_to_remove >= len(hotel_segments):
                    return {
                        "response": "⚠️ ไม่สามารถลบที่พักทั้งหมดได้ ต้องมีที่พักอย่างน้อย 1 segment",
                        "travel_slots": existing_slots,
                        "current_plan": current_plan,
                        "agent_state": {"intent": "edit", "step": "hotel_edit_error", "steps": []},
                    }
                
                # Remove last N segments
                new_segments = hotel_segments[:-num_to_remove]
                new_price = sum(seg.get("price_total", 0) for seg in new_segments)
                
                current_plan["hotel"]["segments"] = new_segments
                current_plan["hotel"]["price_total"] = new_price
                current_plan["total_price"] = (
                    current_plan.get("flight", {}).get("total_price", 0) +
                    new_price +
                    current_plan.get("transport", {}).get("price", 0)
                )
                
                if write_memory:
                    ctx["current_plan"] = current_plan
                
                return {
                    "response": f"✅ ลดที่พัก {num_to_remove} segment สำเร็จ\nเหลือที่พัก {len(new_segments)} segment(s)",
                    "travel_slots": existing_slots,
                    "current_plan": current_plan,
                    "agent_state": {"intent": "edit", "step": "hotel_segment_removed", "steps": []},
                    "suggestions": ["แก้ไขที่พัก", "ยืนยันจอง"],
                }
            
            # Handle delete actions first (to avoid index shifting issues)
            if actions["delete"]:
                valid_delete_indices = [idx for idx in actions["delete"] if 0 <= idx < len(hotel_segments)]
                
                if len(valid_delete_indices) == len(hotel_segments):
                    return {
                        "response": "⚠️ ไม่สามารถลบที่พักทั้งหมดได้ ต้องมีที่พักอย่างน้อย 1 segment",
                        "travel_slots": existing_slots,
                        "current_plan": current_plan,
                        "agent_state": {"intent": "edit", "step": "hotel_edit_error", "steps": []},
                    }
                
                # Delete segments (in reverse order to avoid index shifting)
                new_segments = [seg for idx, seg in enumerate(hotel_segments) if idx not in valid_delete_indices]
                
                # Recalculate price
                new_price = sum(seg.get("price_total", 0) for seg in new_segments)
                
                # Update plan
                current_plan["hotel"]["segments"] = new_segments
                current_plan["hotel"]["price_total"] = new_price
                current_plan["total_price"] = (
                    current_plan.get("flight", {}).get("total_price", 0) +
                    new_price +
                    current_plan.get("transport", {}).get("price", 0)
                )
                
                if write_memory:
                    ctx["current_plan"] = current_plan
                
                deleted_nums = [str(idx + 1) for idx in valid_delete_indices]
                response_text = f"✅ ลบที่พัก segment {', '.join(deleted_nums)} สำเร็จ\n"
                response_text += f"เหลือที่พัก {len(new_segments)} segment(s)"
                
                # If there are edit actions, continue to handle them
                if actions["edit"]:
                    # Adjust edit indices after deletion
                    remaining_edit_indices = []
                    for edit_idx in actions["edit"]:
                        # Count how many deleted segments are before this edit index
                        deleted_before = sum(1 for d_idx in valid_delete_indices if d_idx < edit_idx)
                        new_idx = edit_idx - deleted_before
                        import logging
                        logging.debug(f"handle_slot_edit: edit_idx={edit_idx}, deleted_before={deleted_before}, new_idx={new_idx}, new_segments_count={len(new_segments)}")
                        if 0 <= new_idx < len(new_segments):
                            remaining_edit_indices.append(new_idx)
                    
                    if remaining_edit_indices:
                        # ✅ IMPORTANT: Use updated current_plan (after deletion)
                        # current_plan has already been updated with new_segments
                        # Handle edit for specific segments
                        import logging
                        logging.info(f"handle_slot_edit: Proceeding to edit segments {remaining_edit_indices} after deletion. current_plan hotel segments count: {len(current_plan.get('hotel', {}).get('segments', []))}")
                        return await handle_edit_specific_hotel_segments(
                            user_id, user_message, existing_slots,
                            remaining_edit_indices, current_plan, write_memory
                        )
                    else:
                        # Edit indices became invalid after deletion
                        import logging
                        logging.warning(f"Edit indices {actions['edit']} became invalid after deletion. valid_delete_indices={valid_delete_indices}, new_segments_count={len(new_segments)}")
                
                return {
                    "response": response_text,
                    "travel_slots": existing_slots,
                    "current_plan": current_plan,
                    "agent_state": {"intent": "edit", "step": "hotel_segment_deleted", "steps": []},
                    "suggestions": ["แก้ไขที่พัก", "ยืนยันจอง"],
                }
            
            # Handle edit actions for specific segments (only if no delete actions were processed)
            # If delete actions were processed, edit actions are already handled above
            if actions["edit"] and not actions["delete"]:
                valid_edit_indices = [idx for idx in actions["edit"] if 0 <= idx < len(hotel_segments)]
                if valid_edit_indices:
                    return await handle_edit_specific_hotel_segments(
                        user_id, user_message, existing_slots,
                        valid_edit_indices, current_plan, write_memory
                    )
    
    # ✅ Check for flight segment-specific actions
    if slot_intent == "flight" and current_plan:
        flight = current_plan.get("flight", {})
        flight_segments = flight.get("segments", [])
        
        if flight_segments:
            actions = parse_segment_actions(user_message)
            
            # Handle delete actions (more complex for flights - need to maintain connection)
            if actions["delete"]:
                valid_delete_indices = [idx for idx in actions["delete"] if 0 <= idx < len(flight_segments)]
                
                if len(valid_delete_indices) == len(flight_segments):
                    return {
                        "response": "⚠️ ไม่สามารถลบเที่ยวบินทั้งหมดได้ ต้องมีเที่ยวบินอย่างน้อย 1 segment",
                        "travel_slots": existing_slots,
                        "current_plan": current_plan,
                        "agent_state": {"intent": "edit", "step": "flight_edit_error", "steps": []},
                    }
                
                # For flights, deletion is complex - need to reconnect segments
                # For now, we'll just warn and suggest editing instead
                return {
                    "response": "⚠️ การลบ flight segment อาจทำให้เส้นทางไม่เชื่อมต่อกัน\nแนะนำให้แก้ไข segment แทนการลบ",
                    "travel_slots": existing_slots,
                    "current_plan": current_plan,
                    "agent_state": {"intent": "edit", "step": "flight_delete_warning", "steps": []},
                    "suggestions": ["แก้ไขไฟลต์ 1", "แก้ไขไฟลต์ 2"],
                }
            
            # Handle edit actions for specific segments
            if actions["edit"]:
                valid_edit_indices = [idx for idx in actions["edit"] if 0 <= idx < len(flight_segments)]
                if valid_edit_indices:
                    return await handle_edit_specific_flight_segments(
                        user_id, user_message, existing_slots,
                        valid_edit_indices, current_plan, write_memory
                    )
    
    # Get current slots
    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(existing_slots or {})
    slots0 = normalize_non_core_defaults(slots0)
    
    # Merge new message into slots
    merged, assumptions = slot_extract_merge(today, user_id, user_message, slots0)
    merged = normalize_non_core_defaults(merged)
    
    # ✅ Detect changes for feedback (especially for dates/pax edits)
    old_slots = existing_slots or {}
    changes = []
    
    # Check for date changes
    if slot_intent == "dates":
        if merged.get("start_date") and merged.get("start_date") != old_slots.get("start_date"):
            changes.append(f"เปลี่ยนวันเดินทางเป็น {merged.get('start_date')}")
        if merged.get("nights") is not None and merged.get("nights") != old_slots.get("nights"):
            changes.append(f"เปลี่ยนจำนวนคืนเป็น {merged.get('nights')} คืน")
        if merged.get("days") is not None and merged.get("days") != old_slots.get("days"):
            changes.append(f"เปลี่ยนจำนวนวันเป็น {merged.get('days')} วัน")
    
    # Check for pax changes
    if slot_intent == "pax":
        if merged.get("adults") is not None and merged.get("adults") != old_slots.get("adults"):
            changes.append(f"เปลี่ยนจำนวนผู้ใหญ่เป็น {merged.get('adults')} คน")
        if merged.get("children") is not None and merged.get("children") != old_slots.get("children"):
            changes.append(f"เปลี่ยนจำนวนเด็กเป็น {merged.get('children')} คน")
    
    # Store updated slots with memory policy
    if write_memory:
        update_user_ctx(user_id, {"last_travel_slots": merged})
        ctx = get_user_ctx(user_id)  # Refresh context
    
    # Keep IATA cache
    iata_cache = ctx.get("iata_cache")
    if not isinstance(iata_cache, dict):
        iata_cache = {}
    if write_memory:
        ctx["iata_cache"] = iata_cache
    
    # Determine which sections to search
    # If dates/pax changed, we need to search flights, transport, and hotels (in order: flights → transport → hotels)
    # If flight/hotel intent, search only that section
    sections_to_search = []
    if slot_intent == "dates" or slot_intent == "pax":
        # Dates/pax change affects flights, transport, and hotels (in order)
        sections_to_search = ["flights", "cars", "hotels"]  # ✅ Order: flights → transport → hotels
    elif slot_intent == "flight":
        sections_to_search = ["flights"]
    elif slot_intent == "hotel":
        sections_to_search = ["hotels"]
    elif slot_intent == "transport":
        sections_to_search = ["cars"]  # Transport uses cars API
    else:
        sections_to_search = ["all"]
    
    # Get previous search results
    previous_results = ctx.get("last_search_results") or empty_search_results()
    
    # Search for the specific sections in order
    search_results = previous_results
    for section in sections_to_search:
        try:
            section_data = await asyncio.wait_for(
                amadeus_search_section_async(
                    merged,
                    user_iata_cache=iata_cache,
                    section=section,
                    previous=search_results,
                    overall_timeout_sec=25.0,  # ✅ Reduced timeout per section
                ),
                timeout=25.0,
            )
            if section_data.get("ok"):
                search_results = section_data.get("search_results", search_results)
        except (asyncio.TimeoutError, Exception) as e:
            # Continue with previous results if section search fails
            pass
    
    # Store search results
    if write_memory:
        ctx["last_search_results"] = search_results
    
    # Build plan choices for the specific slot
    slot_choices = []
    try:
        if slot_intent == "flight":
            # Build flight choices only
            flights = (search_results or {}).get("flights", {}).get("data") or []
            for idx, flight_offer in enumerate(flights[:5]):  # Limit to 5 choices
                from core.plan_builder import flight_offer_to_detailed
                f = flight_offer_to_detailed(flight_offer)
                first_seg = (f.get("segments") or [{}])[0]
                last_seg = (f.get("segments") or [{}])[-1]
                slot_choices.append({
                    "id": idx + 1,
                    "type": "flight",
                    "flight": f,
                    "label": f"{first_seg.get('from', '')} → {last_seg.get('to', '')}",
                    "display_text": f"ไฟลต์ {idx + 1}: {first_seg.get('from', '')} → {last_seg.get('to', '')}",
                })
        elif slot_intent == "hotel":
            # Build hotel choices only
            hotels = (search_results or {}).get("hotels", {}).get("data") or []
            nights = int(merged.get("nights") or 3)
            
            # ✅ Check if user wants to add segments
            pending_add = ctx.get("pending_add_segments", 0)
            if pending_add > 0:
                # User wants to add segments - show choices for selection
                for idx, hotel_item in enumerate(hotels[:10]):  # Show more choices for adding
                    from core.plan_builder import pick_hotel_fields
                    h = pick_hotel_fields(hotel_item, nights=nights)
                    slot_choices.append({
                        "id": idx + 1,
                        "type": "hotel",
                        "hotel": h,
                        "label": h.get("hotelName") or h.get("name") or "โรงแรม",
                        "display_text": f"ที่พัก {idx + 1}: {h.get('hotelName') or h.get('name') or 'โรงแรม'}",
                        "is_add_segment": True,  # Flag to indicate this is for adding
                    })
                # Clear the flag
                if write_memory:
                    ctx.pop("pending_add_segments", None)
            else:
                # Normal hotel edit - show choices for replacement
                for idx, hotel_item in enumerate(hotels[:5]):  # Limit to 5 choices
                    from core.plan_builder import pick_hotel_fields
                    h = pick_hotel_fields(hotel_item, nights=nights)
                    slot_choices.append({
                        "id": idx + 1,
                        "type": "hotel",
                        "hotel": h,
                        "label": h.get("hotelName") or h.get("name") or "โรงแรม",
                        "display_text": f"ที่พัก {idx + 1}: {h.get('hotelName') or h.get('name') or 'โรงแรม'}",
                    })
        elif slot_intent == "dates" or slot_intent == "pax":
            # When dates/pax change, rebuild full plan choices
            from core.plan_builder import build_plan_choices_3
            debug_info = (search_results or {}).get("debug", {})
            plan_choices = await asyncio.wait_for(
                build_plan_choices_3(search_results, merged, debug_info),
                timeout=12.0,
            )
            slot_choices = plan_choices[:5]  # Limit to 5 choices
    except (asyncio.TimeoutError, Exception):
        pass
    
    # Response message
    slot_names = {
        "flight": "เที่ยวบิน",
        "hotel": "ที่พัก",
        "transport": "การเดินทาง",
        "dates": "วันเดินทาง",
        "pax": "จำนวนผู้โดยสาร",
    }
    slot_name = slot_names.get(slot_intent, "ส่วนที่เลือก")
    
    # ✅ Add feedback prefix if there were changes (for dates/pax edits)
    prefix = ""
    if changes:
        prefix = f"✅ {' '.join(changes)}. "
    
    if slot_choices:
        response_text = prefix + f"✅ พบตัวเลือก{slot_name} {len(slot_choices)} รายการ\n"
        if slot_intent == "dates" or slot_intent == "pax":
            response_text += "เนื่องจากมีการเปลี่ยนแปลงข้อมูลพื้นฐาน ระบบได้ค้นหาใหม่แล้ว\n"
        if slot_intent == "hotel" and ctx.get("pending_add_segments", 0) > 0:
            response_text += f"เลือกที่พักเพื่อเพิ่ม {ctx.get('pending_add_segments')} segment:\n"
        response_text += "พิมพ์หมายเลขเพื่อเลือก หรือพิมพ์คำขอแก้ไขเพิ่มเติมได้เลยค่ะ"
    else:
        response_text = prefix + f"⚠️ ไม่พบตัวเลือก{slot_name} กรุณาลองแก้ไขเงื่อนไขใหม่ค่ะ"
    
    return {
        "response": response_text,
        "travel_slots": merged,
        "missing_slots": [],
        "trip_title": ctx.get("trip_title"),
        "search_results": search_results,
        "plan_choices": slot_choices,
        "current_plan": current_plan,  # Keep current plan
        "agent_state": {"intent": "edit", "step": f"editing_{slot_intent}", "steps": []},
        "suggestions": [f"เลือก{slot_name} 1", f"เลือก{slot_name} 2"] if slot_choices else [],
        "slot_intent": slot_intent,  # ✅ Indicate which slot is being edited
        "slot_choices": slot_choices,  # ✅ Choices for this specific slot
    }


async def handle_edit_specific_hotel_segments(
    user_id: str,
    user_message: str,
    existing_slots: Dict[str, Any],
    segment_indices: List[int],  # [0] for "ที่พัก 1"
    current_plan: Dict[str, Any],
    write_memory: bool = True,
) -> Dict[str, Any]:
    """Handle editing specific hotel segments by index."""
    ctx = get_user_ctx(user_id)
    today = date.today().isoformat()
    
    # Get current slots
    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(existing_slots or {})
    slots0 = normalize_non_core_defaults(slots0)
    
    # ✅ Preserve critical fields (adults, children) from existing slots before merging
    preserved_adults = slots0.get("adults")
    preserved_children = slots0.get("children")
    
    # Merge new message into slots (extract hotel preferences)
    merged, assumptions = slot_extract_merge(today, user_id, user_message, slots0)
    merged = normalize_non_core_defaults(merged)
    
    # ✅ Restore preserved fields if not explicitly changed in new message
    if preserved_adults is not None and merged.get("adults") is None:
        merged["adults"] = preserved_adults
    if preserved_children is not None and merged.get("children") is None:
        merged["children"] = preserved_children
    
    # Get segment info for context
    hotel = current_plan.get("hotel", {})
    hotel_segments = hotel.get("segments", [])
    
    # ✅ Debug logging
    import logging
    logging.debug(f"handle_edit_specific_hotel_segments: segment_indices={segment_indices}, hotel_segments_count={len(hotel_segments)}, hotel_segments={[s.get('hotelName', 'N/A') for s in hotel_segments]}")
    
    # Validate indices
    valid_indices = [idx for idx in segment_indices if 0 <= idx < len(hotel_segments)]
    if not valid_indices:
        logging.warning(f"handle_edit_specific_hotel_segments: No valid indices. segment_indices={segment_indices}, hotel_segments_count={len(hotel_segments)}")
        return {
            "response": f"⚠️ ไม่พบ segment ที่ระบุ (มี {len(hotel_segments)} segments)",
            "current_plan": current_plan,
            "agent_state": {"intent": "edit", "step": "hotel_edit_error"},
        }
    
    # Search hotels
    search_results = ctx.get("last_search_results") or empty_search_results()
    iata_cache = ctx.get("iata_cache", {})
    
    try:
        section_data = await asyncio.wait_for(
            amadeus_search_section_async(
                merged,
                user_iata_cache=iata_cache,
                section="hotels",
                previous=search_results,
                overall_timeout_sec=25.0,
            ),
            timeout=25.0,
        )
        if section_data.get("ok"):
            search_results = section_data.get("search_results", search_results)
    except (asyncio.TimeoutError, Exception) as e:
        import logging
        logging.warning(f"Error searching hotels in handle_edit_specific_hotel_segments: {e}")
        # Continue with existing search_results if available
    
    # Build hotel choices for replacement
    hotels = (search_results or {}).get("hotels", {}).get("data") or []
    nights = int(merged.get("nights") or 3)
    
    # ✅ Ensure adults count is preserved (required for accurate pricing)
    adults = int(merged.get("adults") or 1)
    if adults < 1:
        adults = 1  # Minimum 1 adult
    
    slot_choices = []
    for idx, hotel_item in enumerate(hotels[:5]):
        try:
            from core.plan_builder import pick_hotel_fields
            h = pick_hotel_fields(hotel_item, nights=nights)
            slot_choices.append({
                "id": idx + 1,
                "type": "hotel",
                "hotel": h,
                "label": h.get("hotelName") or h.get("name") or "โรงแรม",
                "display_text": f"ที่พัก {idx + 1}: {h.get('hotelName') or h.get('name') or 'โรงแรม'}",
                "target_segments": valid_indices,  # ✅ Indicate which segments to replace
            })
        except Exception as e:
            import logging
            logging.warning(f"Error processing hotel item {idx + 1}: {e}")
            continue  # Skip this item and continue with next
    
    segment_nums = [str(idx + 1) for idx in valid_indices]
    response_text = f"✅ พบตัวเลือกที่พักสำหรับแก้ไข segment {', '.join(segment_nums)}\n"
    response_text += "พิมพ์หมายเลขเพื่อเลือก หรือพิมพ์คำขอแก้ไขเพิ่มเติมได้เลยค่ะ"
    
    # ✅ Store target_segments and slot_choices in context for later use
    if write_memory:
        ctx["last_agent_state"] = {
            "intent": "edit",
            "step": "editing_hotel_segments",
            "target_segments": valid_indices,
            "slot_choices": slot_choices,  # ✅ Store slot_choices for handle_choice_select
        }
        ctx["last_search_results"] = search_results
        ctx["last_travel_slots"] = merged
    
    return {
        "response": response_text,
        "travel_slots": merged,
        "search_results": search_results,
        "slot_choices": slot_choices,
        "slot_intent": "hotel",
        "current_plan": current_plan,
        "agent_state": {
            "intent": "edit",
            "step": "editing_hotel_segments",
            "target_segments": valid_indices,  # ✅ Frontend needs this
        },
        "suggestions": ["เลือกที่พัก 1", "เลือกที่พัก 2"] if slot_choices else [],
    }


async def handle_edit_specific_flight_segments(
    user_id: str,
    user_message: str,
    existing_slots: Dict[str, Any],
    segment_indices: List[int],  # [0] for "ไฟลต์ 1"
    current_plan: Dict[str, Any],
    write_memory: bool = True,
) -> Dict[str, Any]:
    """Handle editing specific flight segments by index."""
    ctx = get_user_ctx(user_id)
    today = date.today().isoformat()
    
    # Get current slots
    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(existing_slots or {})
    slots0 = normalize_non_core_defaults(slots0)
    
    # ✅ Preserve critical fields (adults, children) from existing slots before merging
    preserved_adults = slots0.get("adults")
    preserved_children = slots0.get("children")
    
    # Get current flight segments
    flight = current_plan.get("flight", {})
    flight_segments = flight.get("segments", [])
    
    # Validate indices
    valid_indices = [idx for idx in segment_indices if 0 <= idx < len(flight_segments)]
    if not valid_indices:
        return {
            "response": "⚠️ ไม่พบ flight segment ที่ระบุ",
            "current_plan": current_plan,
            "agent_state": {"intent": "edit", "step": "flight_edit_error"},
        }
    
    # Get segment info for context (to maintain connection)
    target_segment = flight_segments[valid_indices[0]]
    origin = target_segment.get("from")
    destination = target_segment.get("to")
    date_str = target_segment.get("departure") or target_segment.get("depart_at")
    
    # Extract preferences from message
    merged, assumptions = slot_extract_merge(today, user_id, user_message, slots0)
    merged = normalize_non_core_defaults(merged)
    
    # ✅ Restore preserved fields if not explicitly changed in new message
    if preserved_adults is not None and merged.get("adults") is None:
        merged["adults"] = preserved_adults
    if preserved_children is not None and merged.get("children") is None:
        merged["children"] = preserved_children
    
    # Override with segment-specific info if needed
    if origin:
        merged["origin"] = origin
    if destination:
        merged["destination"] = destination
    if date_str:
        # Extract date from segment
        try:
            if isinstance(date_str, str):
                merged["start_date"] = date_str.split('T')[0]  # Get date part
        except:
            pass
    
    # Search flights
    search_results = ctx.get("last_search_results") or empty_search_results()
    iata_cache = ctx.get("iata_cache", {})
    
    try:
        section_data = await asyncio.wait_for(
            amadeus_search_section_async(
                merged,
                user_iata_cache=iata_cache,
                section="flights",
                previous=search_results,
                overall_timeout_sec=25.0,
            ),
            timeout=25.0,
        )
        if section_data.get("ok"):
            search_results = section_data.get("search_results", search_results)
    except (asyncio.TimeoutError, Exception) as e:
        import logging
        logging.warning(f"Error searching flights in handle_edit_specific_flight_segments: {e}")
        # Continue with existing search_results if available
    
    # Build flight choices
    flights = (search_results or {}).get("flights", {}).get("data") or []
    
    # ✅ Ensure adults count is preserved (required for accurate pricing)
    adults = int(merged.get("adults") or 1)
    if adults < 1:
        adults = 1  # Minimum 1 adult
    
    slot_choices = []
    for idx, flight_offer in enumerate(flights[:5]):
        try:
            from core.plan_builder import flight_offer_to_detailed
            f = flight_offer_to_detailed(flight_offer)
            first_seg = (f.get("segments") or [{}])[0]
            last_seg = (f.get("segments") or [{}])[-1]
            
            slot_choices.append({
                "id": idx + 1,
                "type": "flight",
                "flight": f,
                "label": f"{first_seg.get('from', '')} → {last_seg.get('to', '')}",
                "display_text": f"ไฟลต์ {idx + 1}: {first_seg.get('from', '')} → {last_seg.get('to', '')}",
                "target_segments": valid_indices,  # ✅ Mark which segments to replace
            })
        except Exception as e:
            import logging
            logging.warning(f"Error processing flight offer {idx + 1}: {e}")
            continue  # Skip this item and continue with next
    
    segment_nums = [str(idx + 1) for idx in valid_indices]
    response_text = f"✅ พบตัวเลือกเที่ยวบินสำหรับแก้ไข segment {', '.join(segment_nums)}\n"
    response_text += "พิมพ์หมายเลขเพื่อเลือก หรือพิมพ์คำขอแก้ไขเพิ่มเติมได้เลยค่ะ"
    
    # ✅ Store target_segments and slot_choices in context
    if write_memory:
        ctx["last_agent_state"] = {
            "intent": "edit",
            "step": "editing_flight_segments",
            "target_segments": valid_indices,
            "slot_choices": slot_choices,  # ✅ Store slot_choices for handle_choice_select
        }
        ctx["last_search_results"] = search_results
        ctx["last_travel_slots"] = merged
    
    return {
        "response": response_text,
        "travel_slots": merged,
        "search_results": search_results,
        "slot_choices": slot_choices,
        "slot_intent": "flight",
        "current_plan": current_plan,
        "agent_state": {
            "intent": "edit",
            "step": "editing_flight_segments",
            "target_segments": valid_indices,
        },
        "suggestions": ["เลือกไฟลต์ 1", "เลือกไฟลต์ 2"] if slot_choices else [],
    }


# ----------------------------
# Main Orchestrator
# ----------------------------
async def orchestrate_chat(
    user_id: str,
    user_message: str,
    existing_slots: Dict[str, Any],
    trip_id: str = "default",
    *,
    write_memory: bool = True,
    status_callback: Optional[Any] = None,  # Callback for real-time status updates
) -> Dict[str, Any]:
    """
    Main Orchestrator - Unified V2/V3 architecture
    Integrates Level 3 features (Planner/Executor/Narrator) into main flow
    """
    
    # Get session (Level 3)
    session = SessionStore.get_session(user_id, trip_id)
    message_count = SessionStore.increment_message_count(user_id, trip_id)
    
    # Get agent settings (Level 3)
    settings = AgentSettings.get_settings(user_id)
    
    # Get user profile for preference application (Level 3)
    user_profile = UserProfileMemory.get_profile(user_id)
    
    # 1) explicit choice select by text
    choice_id = parse_choice_selection(user_message)
    if choice_id is not None:
        # ✅ Check for segment-specific selection: "เลือกที่พัก 5 สำหรับ segment 1"
        import re
        segment_match = re.search(
            r'เลือก(?:ที่พัก|ไฟลต์|เที่ยวบิน)\s*(\d+)\s*สำหรับ\s*segment\s*([\d,\s]+)', 
            user_message, 
            re.IGNORECASE
        )
        
        if segment_match:
            # This is handled by handle_choice_select with segment replacement logic
            # The segment info is already stored in last_agent_state
            pass
        
        result = handle_choice_select(user_id, choice_id, write_memory=write_memory)
        # Update agent state (Level 3)
        if write_memory:
            SessionStore.update_agent_state(user_id, trip_id, result.get("agent_state", {}))
        return result

    ctx = get_user_ctx(user_id)

    # ✅ 0) Router Pattern: Classify intent first (ก่อนทำอะไรอื่น)
    # Router มีหน้าที่เดียว: ฟังแล้วชี้ทาง (ห้ามตอบเนื้อหา)
    if status_callback:
        await status_callback("routing", "🔀 Router: กำลังวิเคราะห์ intent...", "router")
    
    router_context = {
        "current_plan": ctx.get("current_plan"),
        "slot_workflow": (SessionStore.get_agent_state(user_id, trip_id) or {}).get("slot_workflow"),
    }
    router_result = await RouterAgent.route(user_message, router_context)
    
    import logging
    logging.info(f"Router Result: intent={router_result.intent}, confidence={router_result.confidence}, reason={router_result.reason}")
    
    # ✅ Route to appropriate handler based on intent
    intent = router_result.intent
    
    # 1) Handle explicit choice selection (bypass router for direct actions)
    choice_id = parse_choice_selection(user_message)
    if choice_id is not None:
        import re
        segment_match = re.search(
            r'เลือก(?:ที่พัก|ไฟลต์|เที่ยวบิน)\s*(\d+)\s*สำหรับ\s*segment\s*([\d,\s]+)', 
            user_message, 
            re.IGNORECASE
        )
        result = handle_choice_select(user_id, choice_id, trip_id=trip_id, write_memory=write_memory)
        if write_memory:
            SessionStore.update_agent_state(user_id, trip_id, result.get("agent_state", {}))
        return result

    # 2) Route based on Router intent classification
    # 2.1) General chat / greeting / help
    if intent in ["general_chat", "greeting", "help"]:
        agent_state = {"intent": intent, "step": "general_conversation", "steps": []}
        if write_memory:
            SessionStore.update_agent_state(user_id, trip_id, agent_state)
        
        # Quick response for general messages - no heavy processing
        if intent == "greeting":
            general_response = "สวัสดีค่ะ! 😊 ยินดีช่วยวางแผนทริปให้คุณค่ะ พูดได้เลยว่าอยากไปเที่ยวที่ไหน"
        elif intent == "help":
            general_response = (
                "ฉันช่วยคุณได้ค่ะ! 🎯\n\n"
                "คุณสามารถ:\n"
                "- พูดว่า \"ไปเที่ยว [เมือง] [วันที่]\" เพื่อวางแผนทริป\n"
                "- พูดว่า \"จองตั๋วไป [เมือง]\" เพื่อค้นหาเที่ยวบิน\n"
                "- พูดว่า \"หาที่พัก [เมือง]\" เพื่อค้นหาที่พัก\n"
                "- พูดว่า \"แก้ไขไฟลต์\" หรือ \"แก้ไขที่พัก\" เพื่อแก้ไขทริป\n"
                "- พูดว่า \"ยืนยันจอง\" เพื่อจองทริป\n\n"
                "ลองพูดดูได้เลยค่ะ!"
            )
        else:
            general_response = _handle_general_message(user_message)
        
        return {
            "response": general_response,
            "travel_slots": existing_slots or normalize_non_core_defaults(DEFAULT_SLOTS),
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": ctx.get("current_plan"),
            "agent_state": agent_state,
            "suggestions": ["อยากไปเที่ยวที่ไหนคะ?", "ช่วยวางแผนทริปให้หน่อย", "แนะนำที่เที่ยว"],
            "debug": {"message_type": "general", "router_intent": intent, "router_confidence": router_result.confidence},
        }
    
    # 2.2) Payment intent
    if intent == "payment":
        current_plan = ctx.get("current_plan")
        if not current_plan:
            return {
                "response": "⚠️ ยังไม่มีทริปที่เลือกไว้ค่ะ กรุณาเลือกทริปก่อน",
                "travel_slots": existing_slots or normalize_non_core_defaults(DEFAULT_SLOTS),
                "missing_slots": [],
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "payment", "step": "no_plan_selected", "steps": []},
                "suggestions": ["วางแผนทริปใหม่"],
                "debug": {"router_intent": intent},
            }
        return {
            "response": "พร้อมจองแล้วค่ะ ✅ กรุณากดปุ่ม \"ยืนยันจอง\" เพื่อดำเนินการจองค่ะ",
            "travel_slots": normalize_non_core_defaults(ctx.get("last_travel_slots") or DEFAULT_SLOTS),
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": [],
            "current_plan": current_plan,
            "agent_state": {"intent": "payment", "step": "ready_to_book", "steps": []},
            "suggestions": ["ยืนยันจอง"],
            "debug": {"router_intent": intent},
        }
    
    # 2.3) Cancel booking intent
    if intent == "cancel_booking":
        return {
            "response": (
                "คุณต้องการยกเลิกการจองใช่ไหมคะ?\n"
                "กรุณาไปที่หน้า \"My Bookings\" เพื่อยกเลิกการจองได้เลยค่ะ"
            ),
            "travel_slots": existing_slots or normalize_non_core_defaults(DEFAULT_SLOTS),
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": empty_search_results(),
            "plan_choices": [],
            "current_plan": ctx.get("current_plan"),
            "agent_state": {"intent": "cancel_booking", "step": "redirect_to_bookings", "steps": []},
            "suggestions": ["ไปที่ My Bookings"],
            "debug": {"router_intent": intent},
        }
    
    # 2.4) Edit intents (edit_flight, edit_hotel, edit_car)
    if intent in ["edit_flight", "edit_hotel", "edit_car"]:
        current_plan = ctx.get("current_plan")
        if current_plan:
            # Map router intent to slot_intent
            slot_intent_map = {
                "edit_flight": "flight",
                "edit_hotel": "hotel",
                "edit_car": "transport",
            }
            slot_intent_type = slot_intent_map.get(intent, "all")
            
            return await handle_slot_edit(
                user_id=user_id,
                user_message=user_message,
                existing_slots=existing_slots,
                slot_intent=slot_intent_type,
                current_plan=current_plan,
                write_memory=write_memory,
            )
        else:
            return {
                "response": "⚠️ ยังไม่มีทริปที่เลือกไว้ค่ะ กรุณาเลือกทริปก่อนแก้ไข",
                "travel_slots": existing_slots or normalize_non_core_defaults(DEFAULT_SLOTS),
                "missing_slots": [],
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": intent, "step": "no_plan_to_edit", "steps": []},
                "suggestions": ["วางแผนทริปใหม่"],
                "debug": {"router_intent": intent},
            }
    
    # ✅ 2.3) Check for ongoing slot workflow and continue if message doesn't change direction
    # IMPORTANT: Check this BEFORE processing search intents, to allow workflow continuation
    agent_state = SessionStore.get_agent_state(user_id, trip_id) or ctx.get("last_agent_state") or {}
    slot_workflow = agent_state.get("slot_workflow", {})
    current_slot = slot_workflow.get("current_slot")
    
    # ✅ Check if message changes direction (new trip request, different destination, etc.)
    def _message_changes_direction(msg: str, current_state: Dict[str, Any]) -> bool:
        """Check if user message indicates a new direction (new trip, different destination, etc.)"""
        msg_lower = msg.lower()
        
        # New trip keywords
        new_trip_keywords = ["ทริปใหม่", "วางแผนใหม่", "เริ่มใหม่", "new trip", "plan new", "เริ่มใหม่"]
        if any(kw in msg_lower for kw in new_trip_keywords):
            return True
        
        # Check if message contains destination that's different from current
        current_dest = (current_state.get("last_travel_slots") or {}).get("destination", "")
        if current_dest:
            # Simple check: if message mentions a different city/country, it's a new direction
            # This is a heuristic - could be improved with better NLP
            pass  # For now, we'll be conservative and only check explicit new trip keywords
        
        return False
    
    # ✅ Continue slot workflow if:
    # 1. There's an ongoing slot workflow
    # 2. Message doesn't change direction
    # 3. Message is not a choice selection (already handled above)
    # 4. Message is not a general message (already handled above)
    # 5. Router intent is NOT a search intent (or if it is, check if it's just continuing)
    if current_slot and current_slot != "summary":
        # Check if message changes direction
        if not _message_changes_direction(user_message, ctx):
            # Check if Router classified as search but it's actually just continuing workflow
            # (e.g., user says "หาไฟลต์" while in flight slot = just refresh/continue)
            is_search_intent = intent in ["search_flight", "search_hotel", "search_car", "search_trip"]
            if not is_search_intent or (is_search_intent and current_slot in ["flight", "hotel", "car"]):
                # Continue from current slot - show current slot choices again
                slot_choices = agent_state.get("slot_choices", [])
                slot_selections = slot_workflow.get("slot_selections", {})
                travel_slots = ctx.get("last_travel_slots") or existing_slots or {}
                search_results = ctx.get("last_search_results") or empty_search_results()
                
                # Determine slot name and response message
                slot_names = {
                    "flight": ("ไฟลต์", "ไฟลต์"),
                    "hotel": ("ที่พัก", "ที่พัก"),
                    "car": ("รถเช่า", "รถ"),
                }
                slot_name_thai, slot_name_alt = slot_names.get(current_slot, (current_slot, current_slot))
                
                return {
                    "response": (
                        f"📋 Slot {current_slot}: เลือก{slot_name_thai} ({len(slot_choices)} ช้อยส์)\n"
                        f"กดการ์ดหรือพิมพ์ \"เลือก{slot_name_alt} X\" เพื่อเลือกได้เลยค่ะ"
                        + (f"\nหรือพิมพ์ \"ข้ามรถ\" เพื่อข้ามไปสรุปทริปได้เลยค่ะ" if current_slot == "car" else "")
                    ),
                    "travel_slots": normalize_non_core_defaults(travel_slots),
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": search_results,
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": agent_state,
                    "slot_choices": slot_choices,
                    "slot_intent": current_slot,
                    "suggestions": [f"เลือก{slot_name_alt} {i+1}" for i in range(min(3, len(slot_choices)))] + (["ข้ามรถ"] if current_slot == "car" else []),
                }
    
    # ✅ 2.4) Handle "ข้ามรถ" (skip car) when in car slot workflow
    if current_slot == "car" and ("ข้ามรถ" in user_message or "skip car" in user_message.lower() or ("skip" in user_message.lower() and "car" in user_message.lower())):
        return {
            "response": (
                "พร้อมจองแล้วค่ะ ✅\n"
                "กำลังส่งคำขอจองไปที่ Amadeus Sandbox...\n"
                "(ถ้าจองสำเร็จ ระบบจะแจ้งว่า 'จองเสร็จสิ้น กรุณาชำระเงินเพื่อยืนยันจอง')"
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

    # 2.5) Search intents (search_flight, search_hotel, search_car, search_trip)
    # Continue with normal flow for search intents
    # Router has already classified, so we proceed with trip planning
        # User wants to skip car selection → go to summary
        from core.slot_builder import build_trip_summary
        slot_selections = slot_workflow.get("slot_selections", {})
        travel_slots = ctx.get("last_travel_slots") or existing_slots or {}
        
        summary = build_trip_summary(slot_selections, travel_slots)
        
        combined_plan = {
            "flight": slot_selections.get("flight", {}).get("flight"),
            "hotel": slot_selections.get("hotel", {}).get("hotel"),
            "total_price": summary.get("total_price", 0),
            "currency": "THB",
        }
        
        new_agent_state = {
            **agent_state,
            "slot_workflow": {
                "current_slot": "summary",
                "slot_selections": slot_selections,
            },
            "intent": "review",
            "step": "trip_summary",
        }
        
        if write_memory:
            ctx["current_plan"] = combined_plan
            update_user_ctx(user_id, {
                "last_agent_state": new_agent_state,
                "current_plan": combined_plan,
            })
            SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
        
        return {
            "response": (
                "รับทราบค่ะ ✅ ข้ามการเลือกรถเช่าแล้ว\n\n"
                "📋 สรุปทริป:\n"
                f"{summary.get('summary_text', '')}\n\n"
                f"💰 ราคารวม: {summary.get('total_price', 0):,.0f} THB\n\n"
                "ต้องการแก้ไข slot หรือ segment ไหมคะ?\n"
                "- \"แก้ไขไฟลต์\" หรือ \"แก้ไขไฟลต์ segment 1\"\n"
                "- \"แก้ไขที่พัก\" หรือ \"แก้ไขที่พัก segment 1\"\n"
                "หรือพิมพ์ \"ยืนยันจอง\" เพื่อจองเลยค่ะ"
            ),
            "travel_slots": normalize_non_core_defaults(travel_slots),
            "missing_slots": [],
            "trip_title": ctx.get("trip_title"),
            "search_results": ctx.get("last_search_results") or empty_search_results(),
            "plan_choices": [],
            "current_plan": combined_plan,
            "agent_state": new_agent_state,
            "suggestions": ["แก้ไขไฟลต์", "แก้ไขที่พัก", "ยืนยันจอง"],
        }
        
    # ✅ 2.5) Handle slot editing when current_plan exists
    current_plan = ctx.get("current_plan")
    if current_plan:
        # Detect which slot user wants to edit
        slot_intent = detect_slot_intent(user_message, current_plan)
        intent_type = slot_intent.get("intent", "all")
        
        # If user wants to edit a specific slot, handle it
        if intent_type in {"flight", "hotel", "transport", "dates", "pax"}:
            return await handle_slot_edit(
                user_id=user_id,
                user_message=user_message,
                existing_slots=existing_slots,
                slot_intent=intent_type,
                current_plan=current_plan,
                write_memory=write_memory,
            )

    today = date.today().isoformat()

    # ✅ 1) Initialize SlotManager with existing state (Single Source of Truth)
    # Restore from context if available
    slot_manager_state = ctx.get("slot_manager_state")
    if slot_manager_state:
        slot_manager = SlotManager.from_dict(slot_manager_state)
        # Update with any new existing_slots
        slot_manager.update_state(existing_slots or {}, preserve_existing=True)
    else:
        # Create new SlotManager
        slot_manager = SlotManager(initial_state=existing_slots or {})
    
    # baseline slots (for backward compatibility)
    slots0 = dict(DEFAULT_SLOTS)
    slots0.update(slot_manager.get_state())
    slots0 = normalize_non_core_defaults(slots0)
    
    # Level 3: Apply user profile preferences (if available)
    if user_profile:
        slots0 = UserProfileMemory.apply_profile_to_slots(slots0, user_profile)
        # Update slot_manager with profile preferences
        slot_manager.update_state(slots0, preserve_existing=True)

    # 3) merge new message into slots (Gemini slot extraction + regex)
    # Try regex extraction first for simple patterns (avoid Gemini API call if possible)
    merged, assumptions = _try_regex_slot_extraction(user_message, slots0, today)
    
    # Only call Gemini API if regex didn't extract key info or message is complex
    if _needs_gemini_extraction(user_message, merged, slots0):
        # ✅ LLM แค่ extract ข้อมูลใหม่ (ไม่ต้องเก็บ state)
        # ส่ง existing state ไปให้ LLM รู้บริบท แต่ไม่ให้ LLM เก็บ state เอง
        merged_gemini, assumptions_gemini = slot_extract_merge(today, user_id, user_message, slots0)
        # Merge results, preferring Gemini's extraction for complex cases
        merged = {**merged, **merged_gemini}  # Gemini overwrites regex
        assumptions.extend(assumptions_gemini or [])
    
    # ✅ Smart Merge: อัปเดต SlotManager ด้วยข้อมูลใหม่ (รองรับการเปลี่ยนใจ)
    # ตรวจสอบว่าผู้ใช้ต้องการแก้ไขหรือไม่ (จาก Router หรือ keyword)
    is_correction_intent = any(kw in user_message.lower() for kw in [
        "เปลี่ยนใจ", "เปลี่ยน", "แก้ไข", "ไม่เอา", "เอา", "แทน",
        "change", "modify", "edit", "instead", "rather"
    ])
    
    # ใช้ preserve_existing=False เมื่อมีการเปลี่ยนใจ เพื่อให้เขียนทับได้
    preserve_existing = not is_correction_intent
    
    update_result = slot_manager.update_state(merged, preserve_existing=preserve_existing)
    updated_keys = update_result.get("updated_keys", [])
    changes = update_result.get("changes", [])
    is_correction = update_result.get("is_correction", False)
    
    # Get merged state from SlotManager (Single Source of Truth)
    merged = slot_manager.get_state()
    merged = normalize_non_core_defaults(merged)
    
    # ✅ Persist SlotManager state to context
    if write_memory:
        ctx["slot_manager_state"] = slot_manager.to_dict()
    
    # ✅ Store changes for feedback (จะใช้ใน response generation)
    if write_memory:
        ctx["last_state_changes"] = changes
        ctx["last_is_correction"] = is_correction

    assumptions2: List[str] = list(assumptions or [])
    
    # Check if we have enough info to search, or need to ask questions
    missing = get_missing_slots(merged)
    has_vague_request = not merged.get("destination") or (
        merged.get("destination") and merged.get("destination").lower() in {"เที่ยว", "ไปเที่ยว", "ทริป", "vacation", "travel"}
    )
    
    # If user has vague request or missing critical info, use trip planner
    if has_vague_request or (missing and len(missing) >= 2):
        planning_result = plan_trip_from_scratch(user_message, merged, today)
        
        # ✅ Generate trip title early if we have destination (even if incomplete)
        # Only generate if title doesn't exist or destination changed
        current_trip_title = ctx.get("trip_title")
        should_generate_title = (
            not current_trip_title  # No title yet
            and merged.get("destination")  # Has destination
            and merged.get("destination") not in {"เที่ยว", "ไปเที่ยว", "ทริป", "vacation", "travel"}  # Not vague
        )
        
        if should_generate_title:
            try:
                trip_title = await asyncio.wait_for(
                    asyncio.to_thread(generate_trip_title, merged),
                    timeout=2.0
                )
                if trip_title and write_memory:
                    ctx["trip_title"] = trip_title
                    current_trip_title = trip_title
            except (asyncio.TimeoutError, Exception):
                pass
        
        if planning_result.get("action") == "ask_question":
            # Ask a question to gather more info
            question = planning_result.get("question") or "อยากไปเที่ยวที่ไหนคะ?"
            suggestions = planning_result.get("suggestions") or []
            festival_suggestions = planning_result.get("festival_suggestions") or []
            
            # ✅ Add feedback prefix if there were changes (correction)
            prefix = ""
            if changes:
                prefix = f"✅ {' '.join(changes)}. "
            
            response_text = prefix + question
            if festival_suggestions:
                response_text += "\n\n🎉 แนะนำทริปตามเทศกาล/เดือน:\n"
                for fest in festival_suggestions[:5]:  # Limit to 5 suggestions
                    response_text += f"- {fest.get('festival')} → {fest.get('destination')}\n"
                    response_text += f"  {fest.get('description')}\n"
            
            # Level 3: Update agent state
            agent_state = {"intent": "collect", "step": "asking_preferences", "steps": missing}
            if write_memory:
                SessionStore.update_agent_state(user_id, trip_id, agent_state)
                session = SessionStore.get_session(user_id, trip_id)  # Refresh session
            
            return {
                "response": response_text,
                "travel_slots": merged,
                "missing_slots": missing,
                "trip_title": current_trip_title or ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": agent_state,
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
            
            # Level 3: Update agent state
            agent_state = {"intent": "collect", "step": "suggesting_destinations", "steps": missing}
            if write_memory:
                SessionStore.update_agent_state(user_id, trip_id, agent_state)
                session = SessionStore.get_session(user_id, trip_id)  # Refresh session
            
            return {
                "response": response_text,
                "travel_slots": merged,
                "missing_slots": missing,
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": agent_state,
                "suggestions": suggestions,
                "debug": {"assumptions": assumptions2, "planning": planning_result},
            }
    
    # ✅ 3.5) Detect single-item intent (flight-only or hotel-only search)
    single_item_intent = detect_single_item_intent(user_message, merged)
    intent_type = single_item_intent.get("intent", "full_trip")
    
    # ✅ Store single_item_intent in context for later use in handle_choice_select
    if write_memory:
        ctx["single_item_intent"] = single_item_intent
        ctx["single_item_intent_type"] = intent_type
    
    # Handle single-item searches (flight-only or hotel-only)
    if intent_type in {"flight_only", "hotel_only"}:
        # Fill minimal defaults for single-item search
        # For flight-only: need origin, destination, start_date, adults
        # For hotel-only: need destination, start_date, nights, adults
        if intent_type == "flight_only":
            # Flight-only: don't require nights
            if not merged.get("origin"):
                merged["origin"] = "Bangkok"
                assumptions2.append("default origin=Bangkok for flight search")
            if not merged.get("destination"):
                # ✅ Add feedback prefix if there were changes
                prefix = ""
                if changes:
                    prefix = f"✅ {' '.join(changes)}. "
                
                return {
                    "response": prefix + "กรุณาระบุจุดหมายปลายทางสำหรับค้นหาเที่ยวบินค่ะ เช่น 'หาเที่ยวบินจากกรุงเทพไปภูเก็ต'",
                    "travel_slots": merged,
                    "missing_slots": ["destination"],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": empty_search_results(),
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": "collect", "step": "flight_only_missing_destination", "steps": []},
                    "suggestions": ["หาเที่ยวบินจากกรุงเทพไปภูเก็ต", "หาไฟลต์ไปญี่ปุ่น"],
                }
            if not merged.get("start_date"):
                # ✅ Add feedback prefix if there were changes
                prefix = ""
                if changes:
                    prefix = f"✅ {' '.join(changes)}. "
                
                return {
                    "response": prefix + "กรุณาระบุวันที่เดินทางสำหรับค้นหาเที่ยวบินค่ะ เช่น 'หาเที่ยวบินจากกรุงเทพไปภูเก็ต วันที่ 25 ธ.ค.'",
                    "travel_slots": merged,
                    "missing_slots": ["start_date"],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": empty_search_results(),
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": "collect", "step": "flight_only_missing_date", "steps": []},
                    "suggestions": ["วันที่ 25 ธ.ค.", "พรุ่งนี้", "อาทิตย์หน้า"],
                }
            if merged.get("adults") is None:
                merged["adults"] = 1
                assumptions2.append("default adults=1 for flight search")
        elif intent_type == "hotel_only":
            # Hotel-only: need destination, start_date, nights, adults
            if not merged.get("destination"):
                # ✅ Add feedback prefix if there were changes
                prefix = ""
                if changes:
                    prefix = f"✅ {' '.join(changes)}. "
                
                return {
                    "response": prefix + "กรุณาระบุเมืองสำหรับค้นหาที่พักค่ะ เช่น 'หาที่พักในกรุงเทพ'",
                    "travel_slots": merged,
                    "missing_slots": ["destination"],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": empty_search_results(),
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": "collect", "step": "hotel_only_missing_destination", "steps": []},
                    "suggestions": ["หาที่พักในกรุงเทพ", "หาโรงแรมที่ภูเก็ต"],
                }
            if not merged.get("start_date"):
                # ✅ Add feedback prefix if there were changes
                prefix = ""
                if changes:
                    prefix = f"✅ {' '.join(changes)}. "
                
                return {
                    "response": prefix + "กรุณาระบุวันที่เช็คอินสำหรับค้นหาที่พักค่ะ เช่น 'หาที่พักในกรุงเทพ วันที่ 25 ธ.ค.'",
                    "travel_slots": merged,
                    "missing_slots": ["start_date"],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": empty_search_results(),
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": "collect", "step": "hotel_only_missing_date", "steps": []},
                    "suggestions": ["วันที่ 25 ธ.ค.", "พรุ่งนี้", "อาทิตย์หน้า"],
                }
            if not merged.get("nights"):
                merged["nights"] = 1
                assumptions2.append("default nights=1 for hotel search")
            if merged.get("adults") is None:
                merged["adults"] = 1
                assumptions2.append("default adults=1 for hotel search")
        
        # Store slots
        if write_memory:
            ctx["last_travel_slots"] = merged
        
        # Keep IATA cache
        iata_cache = ctx.get("iata_cache")
        if not isinstance(iata_cache, dict):
            iata_cache = {}
        if write_memory:
            ctx["iata_cache"] = iata_cache
        
        # Search only the specific section
        section = "flights" if intent_type == "flight_only" else "hotels"
        try:
            section_data = await asyncio.wait_for(
                amadeus_search_section_async(
                    merged,
                    user_iata_cache=iata_cache,
                    section=section,
                    previous=empty_search_results(),
                    overall_timeout_sec=30.0,
                ),
                timeout=30.0,
            )
            
            if not section_data.get("ok"):
                err = section_data.get("error") or {}
                status = (err or {}).get("status")
                body = (err or {}).get("body")
                msg = None
                if isinstance(body, dict):
                    msg = body.get("message") or body.get("error_description") or body.get("error")
                elif isinstance(body, str):
                    msg = body
                
                return {
                    "response": (
                        f"❌ ค้นหา{'เที่ยวบิน' if intent_type == 'flight_only' else 'ที่พัก'}ไม่สำเร็จค่ะ\n"
                        f"- Status: {status}\n"
                        f"- Reason: {msg or str(err) or 'unknown'}\n"
                        "ลองขยับวัน +1 หรือเปลี่ยนเมืองดูได้เลยค่ะ"
                    ),
                    "travel_slots": merged,
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": empty_search_results(),
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": "error", "step": f"{intent_type}_search_error", "steps": []},
                    "suggestions": ["ขยับวัน +1", "เปลี่ยนเมือง"],
                    "debug": {"assumptions": assumptions2, "error": err},
                }
            
            search_results = section_data.get("search_results") or empty_search_results()
            if write_memory:
                ctx["last_search_results"] = search_results
            
            # Build choices for single item
            slot_choices = []
            try:
                if intent_type == "flight_only":
                    flights = (search_results or {}).get("flights", {}).get("data") or []
                    from core.plan_builder import flight_offer_to_detailed
                    for idx, flight_offer in enumerate(flights[:10]):  # Limit to 10 choices
                        f = flight_offer_to_detailed(flight_offer)
                        first_seg = (f.get("segments") or [{}])[0]
                        last_seg = (f.get("segments") or [{}])[-1]
                        slot_choices.append({
                            "id": idx + 1,
                            "type": "flight",
                            "flight": f,
                            "total_price": f.get("total_price", 0),
                            "currency": f.get("currency", "THB"),
                            "label": f"{first_seg.get('from', '')} → {last_seg.get('to', '')}",
                            "display_text": f"ไฟลต์ {idx + 1}: {first_seg.get('from', '')} → {last_seg.get('to', '')} ราคา {f.get('total_price', 0):,.0f} {f.get('currency', 'THB')}",
                        })
                elif intent_type == "hotel_only":
                    hotels = (search_results or {}).get("hotels", {}).get("data") or []
                    nights = int(merged.get("nights") or 1)
                    from core.plan_builder import pick_hotel_fields
                    for idx, hotel_item in enumerate(hotels[:10]):  # Limit to 10 choices
                        h = pick_hotel_fields(hotel_item, nights=nights)
                        slot_choices.append({
                            "id": idx + 1,
                            "type": "hotel",
                            "hotel": h,
                            "total_price": h.get("total_price", 0),
                            "currency": h.get("currency", "THB"),
                            "label": h.get("hotelName") or h.get("name") or "โรงแรม",
                            "display_text": f"ที่พัก {idx + 1}: {h.get('hotelName') or h.get('name') or 'โรงแรม'} ราคา {h.get('total_price', 0):,.0f} {h.get('currency', 'THB')}",
                        })
            except Exception as e:
                import logging
                logging.warning(f"Error building single-item choices: {e}")
            
            if write_memory:
                ctx["last_plan_choices"] = slot_choices
            
            item_name = "เที่ยวบิน" if intent_type == "flight_only" else "ที่พัก"
            items_n = len(slot_choices)
            
            if not slot_choices:
                return {
                    "response": (
                        f"ไม่พบ{item_name}ที่ตรงกับเงื่อนไขค่ะ\n"
                        "ลองขยับวัน +1 หรือเปลี่ยนเมืองดูได้เลยค่ะ"
                    ),
                    "travel_slots": merged,
                    "missing_slots": [],
                    "trip_title": ctx.get("trip_title"),
                    "search_results": search_results,
                    "plan_choices": [],
                    "current_plan": None,
                    "agent_state": {"intent": intent_type, "step": "no_choices", "steps": []},
                    "suggestions": ["ขยับวัน +1", "เปลี่ยนเมือง"],
                    "debug": {"assumptions": assumptions2},
                }
            
            # Present choices
            blocks: List[str] = []
            for c in slot_choices:
                blocks.append(c.get("display_text", ""))
                blocks.append("\n" + "-" * 42 + "\n")
            
            # ✅ Add feedback prefix if there were changes (correction)
            prefix = ""
            if changes:
                prefix = f"✅ {' '.join(changes)}. "
            
            header = (
                prefix +
                f"พบ{item_name} {items_n} รายการค่ะ (Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n"
                f"กดการ์ดหรือพิมพ์ \"เลือก{item_name} X\" เพื่อเลือกและดำเนินการจองได้เลยค่ะ"
            ).strip()
            
            return {
                "response": header + "\n\n" + "\n".join(blocks).strip(),
                "travel_slots": merged,
                "trip_title": ctx.get("trip_title"),
                "missing_slots": [],
                "search_results": search_results,
                "plan_choices": slot_choices,
                "current_plan": None,
                "agent_state": {"intent": intent_type, "step": "choices_ready", "steps": []},
                "suggestions": [f"เลือก{item_name} 1", f"เลือก{item_name} 2", f"เลือก{item_name} 3"],
                "debug": {"assumptions": assumptions2, "single_item_intent": single_item_intent},
            }
        except (asyncio.TimeoutError, Exception) as e:
            import logging
            logging.error(f"Single-item search error: {e}")
            return {
                "response": f"❌ เกิดข้อผิดพลาดในการค้นหา{item_name}ค่ะ: {str(e)}",
                "travel_slots": merged,
                "missing_slots": [],
                "trip_title": ctx.get("trip_title"),
                "search_results": empty_search_results(),
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "error", "step": f"{intent_type}_search_error", "steps": []},
                "suggestions": ["ลองใหม่", "เปลี่ยนเมือง"],
                "debug": {"assumptions": assumptions2, "error": str(e)},
            }
    
    # Continue with normal flow - fill defaults and search
    # Only force defaults if we have enough info to search
    merged = autopilot_fill_core_defaults(merged, assumptions2, force_defaults=(not missing or len(missing) < 2))
    
    # ✅ Generate trip title early if we have destination (before search to ensure it's available)
    current_trip_title = ctx.get("trip_title")
    if not current_trip_title and merged.get("destination"):
        try:
            trip_title = await asyncio.wait_for(
                asyncio.to_thread(generate_trip_title, merged),
                timeout=2.0
            )
            if trip_title and write_memory:
                ctx["trip_title"] = trip_title
                current_trip_title = trip_title
        except (asyncio.TimeoutError, Exception):
            pass  # ถ้า timeout ไม่เป็นไร จะ generate ใหม่หลัง search

    # ✅ store slots - ensure critical fields (adults, children) are preserved
    if write_memory:
        # Preserve existing adults/children if they exist and merged doesn't override them
        existing_slots = ctx.get("last_travel_slots") or {}
        if existing_slots.get("adults") is not None and merged.get("adults") is None:
            merged["adults"] = existing_slots["adults"]
        if existing_slots.get("children") is not None and merged.get("children") is None:
            merged["children"] = existing_slots["children"]
        ctx["last_travel_slots"] = merged

    # Keep an IATA cache per user (used by both ref-data and Gemini-based resolution).
    iata_cache = ctx.get("iata_cache")
    if not isinstance(iata_cache, dict):
        iata_cache = {}
    if write_memory:
        ctx["iata_cache"] = iata_cache

    # ✅ 4) Check stock (cache) before searching
    # ดึงข้อมูลจาก stock ก่อน ถ้าไม่มีหรือผู้ใช้สั่งค้นหาใหม่ ให้ค้นหาใหม่
    force_new_search = _should_force_new_search(user_message)
    stock_results = None
    used_stock = False
    
    if not force_new_search:
        # ลองดึงจาก stock ก่อน
        stock_results = _get_stock_search_results(ctx, merged)
        if stock_results:
            import logging
            logging.info("✅ Using stock (cached) search results")
            used_stock = True
    
    # 4) Amadeus search (with timeout to guarantee < 1 minute total)
    # ค้นหาใหม่เฉพาะเมื่อไม่มี stock หรือผู้ใช้สั่งค้นหาใหม่
    if force_new_search or not stock_results:
        try:
            data = await asyncio.wait_for(
                amadeus_search_async(merged, user_iata_cache=iata_cache),
                timeout=45.0  # ✅ 45 วินาทีสำหรับ Amadeus search
            )
        except RuntimeError as e:
            # ถ้า error แต่มี stock results ให้ใช้ stock แทน
            if stock_results:
                import logging
                logging.warning(f"Amadeus search error, using stock results: {e}")
                data = {"ok": True, "search_results": stock_results}
                used_stock = True
            else:
                # Re-raise if no stock available
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

    # ✅ 5) Store search results in stock (cache) after successful search
    # เก็บใน stock เฉพาะเมื่อค้นหาใหม่ (ไม่ใช่ใช้ stock)
    search_results = data.get("search_results") or empty_search_results()
    if write_memory and data.get("ok") and search_results and not used_stock:
        ctx["last_search_results"] = search_results
        # Update travel_slots in stock to match current search
        ctx["last_travel_slots"] = merged

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

    # 6) Build choices - Check if user wants full combined workflow or slot-based
    search_results = data.get("search_results") or empty_search_results()
    amadeus_dbg = data.get("debug") or {}
    
    # Check if user explicitly wants full combined workflow (จัดมาหมดเลย, จัดให้หมด, etc.)
    user_msg_lower = (user_message or "").strip().lower()
    wants_full_workflow = any(keyword in user_msg_lower for keyword in [
        "จัดมาหมดเลย", "จัดให้หมด", "จัดทั้งหมด", "จัดให้หมดเลย",
        "จัดมาหมด", "จัดมาให้หมด", "จัดให้ครบ", "จัดครบ",
        "all at once", "all together", "everything", "full plan"
    ])
    
    # Check if we should use slot-based workflow (new trips, not edits, and not explicitly requesting full workflow)
    use_slot_workflow = not ctx.get("current_plan") and not wants_full_workflow  # Only for new trips, unless user wants full
    
    if use_slot_workflow:
        # Slot-based workflow: Show flight choices first
        from core.slot_builder import build_flight_choices
        
        try:
            flight_choices = build_flight_choices(search_results, limit=10)
        except Exception as e:
            import logging
            logging.error(f"Error building flight choices: {e}")
            flight_choices = []
        
        flights_n = len((search_results.get("flights") or {}).get("data") or [])
        hotels_n = len((search_results.get("hotels") or {}).get("data") or [])
        
        if not flight_choices:
            return {
                "response": (
                    "ไม่พบเที่ยวบินที่ตรงกับเงื่อนไขค่ะ\n"
                    f"- ไฟลต์: {flights_n} รายการ\n"
                    f"- โรงแรม: {hotels_n} รายการ\n"
                    "ลองขยับวัน +1 หรือเปลี่ยนเมืองดูได้เลยค่ะ"
                ),
                "travel_slots": merged,
                "missing_slots": [],
                "trip_title": ctx.get("trip_title"),
                "search_results": search_results,
                "plan_choices": [],
                "current_plan": None,
                "agent_state": {"intent": "error", "step": "no_flights", "steps": []},
                "suggestions": ["ขยับวัน +1", "เปลี่ยนเมือง"],
                "debug": {"assumptions": assumptions2},
            }
        
        # Initialize slot workflow state (always, regardless of write_memory)
        new_agent_state = {
            "intent": "selecting",
            "step": "selecting_flight",
            "slot_workflow": {
                "current_slot": "flight",
                "slot_selections": {},
            },
            "slot_choices": flight_choices,
        }
        
        # Persist search results and agent state
        if write_memory:
            update_user_ctx(user_id, {
                "last_search_results": search_results,
            })
            ctx = get_user_ctx(user_id)
            
            update_user_ctx(user_id, {
                "last_agent_state": new_agent_state,
            })
            SessionStore.update_agent_state(user_id, trip_id, new_agent_state)
        
        # Present flight choices (Slot 1)
        # ✅ Add feedback prefix if there were changes (correction)
        prefix = ""
        if changes:
            prefix = f"✅ {' '.join(changes)}. "
        
        header = (
            prefix +
            f"ฉันหาได้แล้วค่ะ (Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n"
            f"- ไฟลต์: {flights_n} รายการ\n"
            f"- โรงแรม: {hotels_n} รายการ\n\n"
            f"📋 Slot 1: เลือกไฟลต์ ({len(flight_choices)} ช้อยส์)\n"
            "กดการ์ดหรือพิมพ์ \"เลือกไฟลต์ X\" เพื่อเลือกได้เลยค่ะ"
        ).strip()
        
        return {
            "response": header,
            "travel_slots": merged,
            "trip_title": current_trip_title or ctx.get("trip_title"),
            "missing_slots": [],
            "search_results": search_results,
            "plan_choices": [],  # ✅ ไม่ส่ง plan_choices เมื่อใช้ slot workflow (ให้แสดง slot_choices เท่านั้น)
            "current_plan": None,
            "agent_state": {
                **new_agent_state,
                "step": "selecting_flight",  # ✅ ใช้ step ที่ชัดเจนว่าเป็น slot workflow
            },
            "slot_choices": flight_choices,  # ✅ ส่ง slot_choices เพื่อให้ frontend แสดง
            "slot_intent": "flight",  # ✅ เพิ่ม slot_intent เพื่อให้ frontend แสดง slotChoices
            "suggestions": [f"เลือกไฟลต์ {i+1}" for i in range(min(3, len(flight_choices)))],
            "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg, "workflow": "slot-based"},
        }
    
    # Fallback to original combined workflow (for edits or legacy)
    try:
        plan_choices = await asyncio.wait_for(
            build_plan_choices_3(search_results, merged, amadeus_dbg),
            timeout=12.0
        )
    except asyncio.TimeoutError:
        plan_choices = []
        amadeus_dbg["build_choices_timeout"] = True

    # Persist search results + choices with memory policy
    if write_memory:
        update_user_ctx(user_id, {
            "last_search_results": search_results,
            "last_plan_choices": plan_choices,
        })
        ctx = get_user_ctx(user_id)
        import logging
        logging.info(f"orchestrate_chat: Persisted {len(plan_choices)} plan_choices for user_id={user_id}, choice_ids={[p.get('id') for p in plan_choices[:5]]}")

    # ✅ Trip title: Generate/update if we have destination and don't have title yet, or if slots changed significantly
    current_trip_title = ctx.get("trip_title")
    should_regenerate_title = (
        not current_trip_title  # ไม่มี title อยู่
        or merged.get("destination") != (ctx.get("last_travel_slots") or {}).get("destination")  # เปลี่ยน destination
        or merged.get("style") != (ctx.get("last_travel_slots") or {}).get("style")  # เปลี่ยน style
    )
    
    # ✅ Generate trip title ถ้ายังไม่มีและมี destination แล้ว
    if should_regenerate_title and merged.get("destination"):
        try:
            trip_title = await asyncio.wait_for(
                asyncio.to_thread(generate_trip_title, merged),
                timeout=2.0  # ✅ 2 วินาทีสำหรับ trip title
            )
            if trip_title and write_memory:
                ctx["trip_title"] = trip_title
                current_trip_title = trip_title
        except (asyncio.TimeoutError, Exception) as e:
            # Silent failure - trip title is non-critical
            # Only log at debug level to avoid warning spam
            import logging
            logging.debug(f"Trip title generation skipped (non-critical): {type(e).__name__}")
            pass  # ถ้า timeout ไม่เป็นไร ใช้ title เดิม

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

        # Level 3: Update agent state
        agent_state = {"intent": "edit", "step": "edited_rebuilt", "steps": []}
        if write_memory:
            SessionStore.update_agent_state(user_id, trip_id, agent_state)
            session = SessionStore.get_session(user_id, trip_id)  # Refresh session
        
        # Level 3: Generate memory suggestions
        memory_suggestions = UserProfileMemory.extract_preferences_from_context(ctx)
        memory_suggestions_list = []
        if memory_suggestions:
            for key, value in memory_suggestions.items():
                if value:
                    memory_suggestions_list.append({
                        "type": "preference",
                        "key": key,
                        "value": value,
                        "description": key
                    })

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
            "trip_title": current_trip_title or ctx.get("trip_title"),  # ✅ ใช้ title ที่ generate ใหม่
            "missing_slots": [],
            "search_results": search_results,
            "plan_choices": plan_choices,
            "current_plan": chosen,
            "agent_state": agent_state,
            "suggestions": ["ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1", "ยืนยันจอง"],
            "memory_suggestions": memory_suggestions_list if memory_suggestions_list else None,  # Level 3
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
            "trip_title": current_trip_title or ctx.get("trip_title"),  # ✅ ใช้ title ที่ generate ใหม่
            "missing_slots": [],
            "search_results": search_results,
            "plan_choices": [],
            "current_plan": None,
            "agent_state": {"intent": "needs_adjust", "step": "no_choices", "steps": []},
            "suggestions": ["ขยับวัน +1", "ขยับวัน -1", "เปลี่ยนเมืองปลายทาง"],
            "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg},
        }

    # 9) Present choices
    # ✅ ไม่แสดง display_text ของแต่ละ choice ในแชท รายละเอียดทั้งหมดจะแสดงใน PlanChoiceCard
    choices_count = len(plan_choices)
    header = (
        f"ฉันหาได้แล้วค่ะ (Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n"
        f"- ไฟลต์: {flights_n} รายการ\n"
        f"- โรงแรม: {hotels_n} รายการ\n\n"
        f"นี่คือ {choices_count} ช้อยส์แบบละเอียด (เรียงตามราคาถูกก่อน) (กดการ์ดหรือพิมพ์ \"เลือกช้อยส์ X\" เพื่อเลือก/แก้ทีละส่วนได้เลยค่ะ)"
    ).strip()

    # IMPORTANT: do not clear current_plan here; let it be None until user selects
    if write_memory and not had_selected:
        update_user_ctx(user_id, {"current_plan": None})
        ctx = get_user_ctx(user_id)

    # Level 2: Generate proactive suggestions
    agent_state = {"intent": "present", "step": "3_choices_ready", "steps": []}
    proactive_suggestions = ProactiveSuggestions.get_suggestions(ctx, {"agent_state": agent_state})
    # Use proactive suggestions if available, otherwise use defaults
    final_suggestions = proactive_suggestions if proactive_suggestions else ["เลือกช้อยส์ 1", "ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1"]

    return {
        "response": header,
        "travel_slots": merged,
        "trip_title": current_trip_title or ctx.get("trip_title"),  # ✅ ใช้ title ที่ generate ใหม่
        "missing_slots": [],
        "search_results": search_results,
        "plan_choices": plan_choices,
        "current_plan": None,
        "agent_state": agent_state,
        "suggestions": final_suggestions,
        "debug": {"assumptions": assumptions2, "amadeus_debug": amadeus_dbg},
    }
