"""เอเจนต์ท่องเที่ยวหลัก: คุยกับผู้ใช้, วางแผน, ค้นหา, เลือกตัวเลือก และประสาน MCP/LLM."""

from __future__ import annotations
from typing import Any, Dict, Optional, Callable, Awaitable, List, Tuple
from datetime import datetime, timedelta
import json
import asyncio
import hashlib
import httpx

from app.models import UserSession, TripPlan, Segment, ControllerAction, ActionLog, ActionType
from app.models.trip_plan import SegmentStatus, TravelMode
from app.storage.interface import StorageInterface
from app.services.llm import LLMService, get_production_llm, BrainType, ModelType
from app.services.memory import MemoryService
from app.services.travel_service import TravelOrchestrator, TravelSearchRequest
from app.services.data_aggregator import aggregator, StandardizedItem, ItemCategory
from app.core.exceptions import AgentException, LLMException
from app.core.logging import get_logger
from app.core.config import settings
from app.services.agent_monitor import agent_monitor
from app.engine.cost_tracker import cost_tracker, CostTracker
from app.services.options_cache import get_options_cache
from app.services.workflow_state import get_workflow_state_service, WorkflowStep as WfStep
from app.services.mcp_server import MCPToolExecutor
from app.services.model_selector import ModelSelector
from app.engine.reinforcement_learning import get_rl_learner, get_rl_service
from app.services.ml_keyword_service import get_ml_keyword_service
from app.engine.gemini_agent import (
    CONTROLLER_SYSTEM_PROMPT,
    get_responder_system_prompt,
    RESPONDER_SYSTEM_PROMPT,
)
# Agent Intelligence classes will be defined at the end of this file

logger = get_logger(__name__)

from app.core.constants import FALLBACK_RESPONSE_EMPTY  # noqa: E402

# ✅ Helper function to safely write debug logs
def _write_debug_log(data: dict):
    """Safely write debug log, creating directory if needed"""
    try:
        import os
        from pathlib import Path
        debug_log_dir = Path(__file__).parent.parent.parent / 'data' / 'logs' / 'debug'
        debug_log_dir.mkdir(parents=True, exist_ok=True)
        debug_log_path = debug_log_dir / 'agent_debug.log'
        with open(debug_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception:
        pass  # Silently ignore debug log errors

def _strip_options_pool_for_controller(state: dict) -> dict:
    """Remove raw options_pool data from trip plan state before sending to Controller LLM.

    options_pool can contain full Amadeus API responses (50-200 KB each).
    The Controller only needs to know *whether* options exist and how many,
    not the full content.  This keeps the context window small and fast.
    """
    def _strip_segment(seg: dict) -> dict:
        pool = seg.get("options_pool")
        if pool:
            seg = dict(seg)
            seg["options_pool"] = f"[{len(pool)} options available]"
        return seg

    def _strip_list(segments: list) -> list:
        return [_strip_segment(s) if isinstance(s, dict) else s for s in segments]

    import copy
    s = copy.deepcopy(state)
    try:
        travel = s.get("travel", {})
        flights = travel.get("flights", {})
        if isinstance(flights.get("outbound"), list):
            flights["outbound"] = _strip_list(flights["outbound"])
        if isinstance(flights.get("inbound"), list):
            flights["inbound"] = _strip_list(flights["inbound"])
        if isinstance(travel.get("ground_transport"), list):
            travel["ground_transport"] = _strip_list(travel["ground_transport"])
        acc = s.get("accommodation", {})
        if isinstance(acc.get("segments"), list):
            acc["segments"] = _strip_list(acc["segments"])
    except Exception:
        pass  # Never break the main flow for a logging helper
    return s


class TravelAgent:
    """
    Production-Grade Travel Agent with Two-Pass ReAct Loop
    Robust error handling and logging
    """
    
    def __init__(
        self,
        storage: StorageInterface,
        llm_service: Optional[LLMService] = None,
        agent_personality: str = "friendly",
        response_style: str = "balanced",
        detail_level: str = "medium",
        chat_language: str = "th",
        reinforcement_learning: bool = True,
    ):
        """
        Initialize Travel Agent

        Args:
            storage: Storage interface implementation
            llm_service: Optional LLM service (creates new if None)
            agent_personality: Agent personality type (friendly, professional, casual, teenager, detailed, concise)
            response_style: Response length style (short, balanced, long)
            detail_level: Recommendation detail level (low, medium, high)
            chat_language: Conversation language (th, en, auto)
            reinforcement_learning: Whether to enable RL learning from user feedback
        """
        self.storage = storage
        self.llm = llm_service or LLMService()
        self.agent_personality = agent_personality or "friendly"
        self.response_style = response_style or "balanced"
        self.detail_level = detail_level or "medium"
        self.chat_language = chat_language or "th"
        self.reinforcement_learning_enabled = reinforcement_learning
        # Generate responder prompt based on personality and preferences
        self.responder_system_prompt = get_responder_system_prompt(
            self.agent_personality,
            response_style=self.response_style,
            detail_level=self.detail_level,
            chat_language=self.chat_language,
        )
        # ✅ Intent-Based LLM Service with tool calling (Gemini)
        try:
            from app.services.llm import IntentBasedLLM
            self.intent_llm = IntentBasedLLM()
            logger.info("IntentBasedLLM initialized with tool calling support")
        except Exception as e:
            logger.warning(f"Failed to initialize IntentBasedLLM: {e}, using fallback")
            self.intent_llm = None
        # ✅ Production LLM Service with 3 brains
        try:
            self.production_llm = get_production_llm()
            logger.info("Production LLM Service (3 brains) initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Production LLM Service: {e}, using fallback")
            self.production_llm = None
        self.memory = MemoryService(self.llm)
        self.orchestrator = TravelOrchestrator()
        self.cost_tracker = cost_tracker
        from app.engine.workflow_manager import get_slot_manager
        self.slot_manager = get_slot_manager()
        # ✅ Initialize MCP Tool Executor for Amadeus
        try:
            self.mcp_executor = MCPToolExecutor()
            logger.info("MCPToolExecutor initialized for Google Maps and Amadeus")
        except Exception as e:
            logger.warning(f"Failed to initialize MCPToolExecutor: {e}, will use fallback methods")
            self.mcp_executor = None
        # Get database instance for user profile queries
        try:
            from app.storage.connection_manager import MongoConnectionManager
            self.db = MongoConnectionManager.get_instance().get_database()
        except Exception as e:
            logger.warning(f"Failed to get database instance: {e}, user profile context will be empty")
            self.db = None
        agent_monitor.log_activity("system", "system", "start", "TravelAgent instance created")
        logger.info("TravelAgent initialized with Brain/Memory support, TravelOrchestrator, and Amadeus MCP Tools")
    
    async def run_turn(
        self,
        session_id: str,
        user_input: str,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        mode: str = "normal"  # ✅ 'normal' = ผู้ใช้เลือกช้อยส์เอง, 'agent' = AI ดำเนินการเอง
    ) -> str:
        """
        Run one turn of conversation (main entry point)
        ✅ SAFETY FIRST: Wrapped in global try-except to prevent crashes
        
        Args:
            session_id: Session identifier
            user_input: User's message
            status_callback: Optional async callback for status updates (status, message, step)
            mode: Chat mode - 'normal' (user selects) or 'agent' (AI auto-selects and books)
            
        Returns:
            Response message in Thai (ALWAYS returns, never raises)
        """
        # ✅ GLOBAL TRY-EXCEPT: Catch ALL errors and return fallback response
        last_known_data = None
        session = None
        try:
            # Load session
            session = await self.storage.get_session(session_id)
            if not session:
                logger.error(f"Failed to load session {session_id}")
                agent_monitor.log_activity(session_id, "unknown", "error", f"Failed to load session")
                # ✅ SAFETY: Return fallback instead of raising
                return "ระบบเกิดขัดข้องเล็กน้อย ไม่สามารถโหลด session ได้ กรุณาลองใหม่อีกครั้ง"
            
            user_id = session.user_id
            # ✅ Store last known data for fallback
            last_known_data = session.trip_plan.model_dump() if session.trip_plan else {}
            agent_monitor.log_activity(session_id, user_id, "start", f"Processing message: {user_input[:50]}...")
            
            # Phase 0: Recall (Brain Memory) & Get User Profile
            if status_callback:
                await status_callback("thinking", "🤖 Agent กำลังระลึกความจำ...", "recall_start")
            
            user_memories = await self.memory.recall(session.user_id)
            memory_context = self.memory.format_memories_for_prompt(user_memories)
            
            # Get user profile for personalized context
            user_profile_context = await self._get_user_profile_context(user_id)
            
            # Phase 1 & 2: Controller Loop + Responder (Think & Act & Speak)
            if status_callback:
                mode_text = "โหมด Agent" if mode == "agent" else "โหมดปกติ"
                await status_callback("thinking", f"กำลังวางแผนทริป ({mode_text})...", "controller_start")

            if getattr(settings, "enable_langgraph_full_workflow", False):
                # ✅ LangGraph จัดการ workflow ทั้งหมดแทน agent.run_controller
                try:
                    from app.orchestration.full_workflow_graph import run_full_workflow
                    action_log = ActionLog()
                    response_message = await run_full_workflow(
                        self,
                        session,
                        action_log,
                        user_input,
                        mode=mode,
                        status_callback=status_callback,
                        memory_context=memory_context,
                        user_profile_context=user_profile_context,
                    )
                except Exception as lgf_err:
                    logger.warning(f"LangGraph full workflow failed, falling back to agent loop: {lgf_err}")
                    action_log = await self.run_controller(session, user_input, status_callback, memory_context, user_profile_context, mode=mode)
                    await self.storage.save_session(session)
                    if status_callback:
                        await status_callback("speaking", "🤖 Agent กำลังสรุปคำตอบ...", "responder_start")
                    response_message = await self.generate_response(
                        session, action_log, memory_context, user_profile_context, mode=mode, user_input=user_input
                    )
                else:
                    # Agent Mode: final auto-select + auto-book
                    if mode == "agent":
                        all_segments = (
                            session.trip_plan.travel.flights.outbound
                            + session.trip_plan.travel.flights.inbound
                            + session.trip_plan.accommodation.segments
                            + session.trip_plan.travel.ground_transport
                        )
                        has_options_to_select = any(
                            seg.options_pool and not seg.selected_option for seg in all_segments
                        )
                        # ✅ ถ้ามี selected options อยู่แล้ว (เช่น flight selected แต่ hotel ไม่มี options)
                        # ให้ trigger booking ด้วย แทนที่จะข้ามไป
                        has_any_selected = any(
                            seg.selected_option is not None for seg in all_segments
                        )
                        should_run_auto_complete = has_options_to_select or has_any_selected
                        if has_options_to_select and status_callback:
                            await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด (รอบสุดท้าย)...", "agent_auto_select_final")
                        if should_run_auto_complete:
                            await self._run_agent_mode_auto_complete(session, action_log, status_callback)
                            await self.storage.save_session(session)
            else:
                action_log = await self.run_controller(session, user_input, status_callback, memory_context, user_profile_context, mode=mode)
                # Save state after Phase 1
                await self.storage.save_session(session)
                # Phase 2: Responder (Speak)
                if status_callback:
                    await status_callback("speaking", "🤖 Agent กำลังสรุปคำตอบ...", "responder_start")
                response_message = await self.generate_response(
                    session, action_log, memory_context, user_profile_context, mode=mode, user_input=user_input
                )
            
            # ✅ CRITICAL: Ensure response_message is never None or empty
            if not response_message or not response_message.strip():
                logger.error(
                    "generate_response returned empty message, using fallback",
                    extra={"session_id": session.session_id, "fallback_reason": "run_turn_empty_response"},
                )
                response_message = FALLBACK_RESPONSE_EMPTY
            
            logger.info(f"run_turn completed: session={session.session_id}, response_length={len(response_message)}")
            
            # Phase 3: Consolidate (Learning)
            # Run in background to not block response
            asyncio.create_task(self.memory.consolidate(session.user_id, user_input, response_message))
            
            # ✅ CRITICAL: Final save to persist trip_plan with all plan choices, selected options, and raw data
            session_saved = await self.storage.save_session(session)
            if not session_saved:
                logger.error(f"Failed to save session after agent run_turn: session_id={session.session_id}")
            else:
                # Log trip_plan data preservation
                trip_plan = session.trip_plan
                total_segments_with_data = 0
                for seg in (trip_plan.travel.flights.outbound + 
                           trip_plan.travel.flights.inbound +
                           trip_plan.accommodation.segments +
                           trip_plan.travel.ground_transport):
                    if seg.options_pool or seg.selected_option:
                        total_segments_with_data += 1
                
                if total_segments_with_data > 0:
                    logger.info(f"Session saved with trip_plan raw data: {total_segments_with_data} segments with options/selection: session_id={session.session_id}")
            
            # ✅ Agent Mode auto-book: ส่ง flag ไป frontend เพื่อแสดงป๊อปอัปจองสำเร็จ
            # Return type is always str; auto_booked flag is surfaced via session attribute
            # so callers can check session._agent_auto_booked without a tuple return.
            return response_message
        
        except Exception as e:
            # ✅ SAFETY FIRST: Catch ALL exceptions and return fallback response with last known data
            logger.error(f"Error in run_turn (any exception): {e}", exc_info=True)
            
            # Build fallback response showing last known data
            fallback_parts = ["ระบบเกิดขัดข้องเล็กน้อย แต่ฉันได้รับข้อมูลว่า:"]
            
            if session and session.trip_plan:
                trip_plan = session.trip_plan
                
                # Extract what we know
                has_flights = bool(trip_plan.travel.flights.outbound or trip_plan.travel.flights.inbound)
                has_hotels = bool(trip_plan.accommodation.segments)
                has_transport = bool(trip_plan.travel.ground_transport)
                
                if has_flights:
                    outbound = trip_plan.travel.flights.outbound[0] if trip_plan.travel.flights.outbound else None
                    if outbound and outbound.requirements:
                        origin = outbound.requirements.get("origin")
                        dest = outbound.requirements.get("destination")
                        date = outbound.requirements.get("departure_date")
                        if origin or dest:
                            flight_info = f"เที่ยวบิน: {origin or '?'} → {dest or '?'}"
                            if date:
                                flight_info += f" วันที่ {date}"
                            fallback_parts.append(flight_info)
                
                if has_hotels:
                    hotel_seg = trip_plan.accommodation.segments[0] if trip_plan.accommodation.segments else None
                    if hotel_seg and hotel_seg.requirements:
                        location = hotel_seg.requirements.get("location")
                        check_in = hotel_seg.requirements.get("check_in")
                        if location:
                            hotel_info_str = f"โรงแรม: {location}"
                            if check_in:
                                hotel_info_str += f" เข้า {check_in}"
                            fallback_parts.append(hotel_info_str)
            
            fallback_parts.append("กรุณาลองใหม่อีกครั้ง หรืออธิบายเพิ่มเติมเพื่อให้ฉันช่วยคุณได้")
            
            fallback_message = " ".join(fallback_parts)
            
            # Try to save session if we have it
            if session:
                try:
                    await self.storage.save_session(session)
                except Exception as save_error:
                    logger.error(f"Failed to save session in error handler: {save_error}")
            
            return fallback_message
    
    async def _get_user_profile_context(self, user_id: str) -> str:
        """
        Get user profile context for personalized service
        
        Args:
            user_id: User identifier
            
        Returns:
            Formatted user profile context string
        """
        if self.db is None or not user_id or user_id == "anonymous":
            return ""
        
        try:
            users_collection = self.db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            
            if not user_doc:
                return ""
            
            # Extract user information
            name = user_doc.get("full_name") or user_doc.get("name") or user_doc.get("first_name") or ""
            first_name_th = user_doc.get("first_name_th") or ""
            email = user_doc.get("email") or ""
            phone = user_doc.get("phone") or ""
            preferences = user_doc.get("preferences", {})
            
            # Build context string
            context_parts = []
            
            if name or first_name_th:
                display_name = first_name_th if first_name_th else name
                context_parts.append(f"👤 ชื่อผู้ใช้: {display_name}")
            
            if email:
                context_parts.append(f"📧 Email: {email}")
            
            # Add preferences if available
            if preferences:
                learned_prefs = preferences.get("memory_summaries", [])
                if learned_prefs:
                    context_parts.append(f"💡 ความชอบที่เรียนรู้มา: {', '.join(learned_prefs[-3:])}")  # Last 3 preferences
            
            # 🛂 Visa section (for flight/transfer search and planning - filter/plan by visa)
            visa_type = user_doc.get("visa_type") or ""
            visa_number = user_doc.get("visa_number") or ""
            has_visa = bool(visa_type or visa_number)
            if has_visa:
                visa_issuing = user_doc.get("visa_issuing_country") or ""
                visa_expiry = user_doc.get("visa_expiry_date") or ""
                visa_entry = user_doc.get("visa_entry_type") or "S"
                visa_purpose = user_doc.get("visa_purpose") or "T"
                entry_label = "หลายครั้ง (M)" if visa_entry == "M" else "ครั้งเดียว (S)"
                purpose_labels = {"T": "ท่องเที่ยว", "B": "ธุรกิจ", "S": "ศึกษา", "W": "ทำงาน", "TR": "ผ่านทาง", "O": "อื่นๆ"}
                purpose_label = purpose_labels.get(visa_purpose, visa_purpose)
                context_parts.append(
                    f"🛂 วีซ่า: มี | ประเภท: {visa_type} | ประเทศที่ออก: {visa_issuing} | "
                    f"หมดอายุ: {visa_expiry} | การเข้าประเทศ: {entry_label} | วัตถุประสงค์: {purpose_label}"
                )
            else:
                context_parts.append("🛂 วีซ่า: ไม่มีในโปรไฟล์ (ใช้ช่วยกรองเที่ยวบิน/Transit ได้)")
            
            if context_parts:
                return "\n".join(["=== USER PROFILE ==="] + context_parts)
            
            return ""
        except Exception as e:
            logger.warning(f"Failed to get user profile context for {user_id}: {e}")
            return ""

    async def _get_main_booker_dob(self, user_id: str) -> Optional[str]:
        """Get main booker's date of birth (YYYY-MM-DD) for age-based adult/child logic. ผู้ใหญ่ = อายุ > 20 ปี."""
        if self.db is None or not user_id or user_id == "anonymous":
            return None
        try:
            users_collection = self.db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            if not user_doc:
                return None
            return user_doc.get("dob") or user_doc.get("date_of_birth") or None
        except Exception as e:
            logger.debug(f"Failed to get main booker DOB for {user_id}: {e}")
            return None
    
    async def run_controller(
        self,
        session: UserSession,
        user_input: str,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        memory_context: str = "",
        user_profile_context: str = "",
        mode: str = "normal"  # ✅ 'normal' = ผู้ใช้เลือกช้อยส์เอง, 'agent' = AI ดำเนินการเอง
    ) -> ActionLog:
        """
        Phase 1: Controller Loop
        Loop (max 3 times) to execute actions until ASK_USER
        CRITICAL: All actions wrapped in try/except to prevent crashes
        NEW: Includes Loop Detection, Cost Tracking, and Workflow Visualization
        
        Args:
            session: UserSession with current state
            user_input: User's message
            status_callback: Optional async callback for status updates
            memory_context: Background information about user preferences
            mode: Chat mode - 'normal' (user selects) or 'agent' (AI auto-selects and books)
            
        Returns:
            ActionLog with all actions taken
        """
        action_log = ActionLog()
        # Cap at 3 iterations max to balance completeness vs latency.
        # settings.controller_max_iterations can be set to 1 or 2 for faster responses.
        max_iterations = max(1, min(settings.controller_max_iterations, 3))
        
        # 🆕 LOOP DETECTION: Track action history to detect infinite loops
        action_history: List[tuple[str, str]] = []  # (action_type, payload_hash)
        loop_detection_threshold = 2  # Stop if same action repeats 2 times
        
        # 🆕 COST TRACKING: Budget limit for agent mode (default: $1.00)
        max_budget_usd = 1.0 if mode == "agent" else 5.0  # Agent mode has lower limit
        
        logger.info(
            f"[CONTROLLER] Starting loop with strict limit: {max_iterations} iterations max, "
            f"Loop Detection: ON, Cost Budget: ${max_budget_usd:.2f}",
            extra={"session_id": session.session_id, "user_id": session.user_id, "mode": mode}
        )
        
        # ✅ ML KEYWORD DECODE: ถอดรหัส intent จากข้อความผู้ใช้แบบรวดเร็ว (~90% แม่นยำ) สำหรับวางแผนใน 1 นาที
        ml_intent_hint = None
        ml_validation_result = None
        try:
            ml_svc = get_ml_keyword_service()
            ml_intent_hint = ml_svc.decode_keywords(user_input)
            if ml_intent_hint and ml_intent_hint.get("confidence", 0) >= 0.5:
                model_used = ml_intent_hint.get("model", "ml")
                logger.info(
                    "[%s] Keyword decode: intent=%s confidence=%.2f workflow=%s",
                    "DL" if model_used == "dl_mlp" else "ML",
                    ml_intent_hint.get("intent"),
                    ml_intent_hint.get("confidence", 0),
                    ml_intent_hint.get("workflow_intent"),
                    extra={"session_id": session.session_id, "model": model_used},
                )
            # ✅ ML DATA VALIDATION: ตรวจสอบวันที่/จำนวนคน/งบประมาณจาก trip_plan
            extracted_data = self._extract_trip_data_for_ml_validation(session.trip_plan)
            if extracted_data:
                ml_validation_result = ml_svc.validate_extracted_data(extracted_data)
                if ml_validation_result and not ml_validation_result.get("valid", True):
                    logger.info(
                        "[ML] Data validation: valid=%s confidence=%.2f issues=%s",
                        ml_validation_result.get("valid"),
                        ml_validation_result.get("confidence", 0),
                        ml_validation_result.get("issues", []),
                        extra={"session_id": session.session_id},
                    )
        except Exception as ml_err:
            logger.debug("ML keyword/validation skipped: %s", ml_err)

        for iteration in range(max_iterations):
            logger.info(f"Controller Loop iteration {iteration + 1}/{max_iterations}", 
                       extra={"session_id": session.session_id, "user_id": session.user_id})
            
            if status_callback:
                await status_callback("thinking", f"🤖 Agent กำลังวิเคราะห์และวางแผนทริป...", f"controller_iter_{iteration + 1}")
            
            try:
                # Get current state as JSON — strip options_pool to avoid huge context windows
                _raw_state = session.trip_plan.model_dump()
                _raw_state = _strip_options_pool_for_controller(_raw_state)
                state_json = json.dumps(_raw_state, ensure_ascii=False, indent=2)
                # ✅ Workflow state สำหรับให้ Controller ตรวจและ validate
                workflow_state = None
                try:
                    wf = get_workflow_state_service()
                    workflow_state = await wf.get_workflow_state(session.session_id)
                except Exception as wf_err:
                    logger.debug(f"Workflow state fetch: {wf_err}")
                # Call Controller LLM (with ML intent hint for faster & accurate planning)
                try:
                    action = await self._call_controller_llm(
                        state_json,
                        user_input,
                        action_log,
                        memory_context,
                        user_profile_context,
                        mode=mode,
                        session_id=session.session_id,
                        user_id=session.user_id,
                        workflow_validation=workflow_state,
                        ml_intent_hint=ml_intent_hint,
                        ml_validation_result=ml_validation_result,
                    )
                except Exception as e:
                    logger.error(f"Failed to call controller LLM: {e}", exc_info=True)
                    action = None
                
                if not action:
                    logger.warning("Controller LLM failed to return an action, using default ASK_USER")
                    agent_monitor.log_activity(session.session_id, session.user_id, "warning", "LLM failed to return action")
                    action = ControllerAction(
                        thought="I failed to decide an action due to an error. I will ask the user for clarification.",
                        action=ActionType.ASK_USER,
                        payload={"missing_fields": []}
                    )
                
                # 🆕 LOOP DETECTION: Check for repeated actions
                action_type_str = action.action.value if hasattr(action.action, 'value') else str(action.action)
                payload_hash = hashlib.md5(json.dumps(action.payload, sort_keys=True).encode()).hexdigest()[:8]
                action_signature = (action_type_str, payload_hash)
                
                # Count how many times this action has been executed
                action_count = action_history.count(action_signature)
                action_history.append(action_signature)
                
                if action_count >= loop_detection_threshold:
                    logger.warning(
                        f"[LOOP DETECTION] Action '{action_type_str}' repeated {action_count + 1} times! "
                        f"Breaking loop to prevent infinite cycle.",
                        extra={"session_id": session.session_id, "action": action_type_str}
                    )
                    action_log.add_action(
                        "LOOP_DETECTED",
                        {"repeated_action": action_type_str, "count": action_count + 1},
                        f"Loop detected: {action_type_str} repeated too many times",
                        success=False
                    )
                    break
                
                # ✅ EXPLICIT LOGGING: Log every Thought and Action to terminal
                thought_text = action.thought[:200] if action.thought else "No thought"
                action_text = action.action.value if hasattr(action.action, 'value') else str(action.action)
                logger.info(
                    f"[CONTROLLER] Iteration {iteration+1}/{max_iterations} - Thought: {thought_text}",
                    extra={"session_id": session.session_id, "user_id": session.user_id, "action": action_text}
                )
                logger.info(
                    f"[CONTROLLER] Iteration {iteration+1}/{max_iterations} - Action: {action_text}",
                    extra={"session_id": session.session_id, "user_id": session.user_id, "payload": action.payload}
                )
                
                # Log to monitor
                agent_monitor.log_activity(
                    session.session_id, 
                    session.user_id, 
                    "thought", 
                    f"Iteration {iteration+1}: {action.thought[:100]}",
                    {"action": action.action.value, "payload": action.payload}
                )
                
                # Log action
                log_payload = action.payload.copy() if action.payload else {}
                if action.action == ActionType.BATCH and action.batch_actions:
                    log_payload["batch_actions"] = action.batch_actions

                action_log.add_action(
                    action.action.value,
                    log_payload,
                    f"Iteration {iteration + 1}"
                )
                
                # Execute actions (Single or Batch)
                actions_to_execute = []
                
                if action.batch_actions:
                    logger.info(f"Executing batch actions: {len(action.batch_actions)} actions")
                    for batch_item in action.batch_actions:
                        # Convert dict to proper format for execution
                        act_type_str = batch_item.get("action")
                        payload = batch_item.get("payload", {})
                        if act_type_str:
                            try:
                                # Normalize and validate action type
                                normalized_type = act_type_str.upper().strip()
                                if normalized_type == "BATCH":
                                    continue # Ignore nested batch
                                    
                                act_type = ActionType(normalized_type)
                                actions_to_execute.append((act_type, payload))
                            except ValueError:
                                logger.warning(f"Invalid action type in batch: {act_type_str}")
                                continue
                else:
                    # Single action
                    actions_to_execute.append((action.action, action.payload))
                
                # Process all actions
                has_ask_user = False
                update_tasks = []
                search_tasks = []
                
                for act_type, payload in actions_to_execute:
                    if act_type == ActionType.BATCH:
                        continue # Skip BATCH as it's just a container
                        
                    elif act_type == ActionType.ASK_USER:
                        # ✅ Normal Mode: Allow ASK_USER (user needs to provide information)
                        if mode == "normal":
                            has_ask_user = True
                            logger.info(f"Normal Mode: ASK_USER action - waiting for user input")
                        # ✅ Agent Mode: NEVER ASK_USER - always infer intelligently
                        else:
                            logger.info(f"Agent Mode: Controller suggested ASK_USER, but Agent Mode NEVER asks - inferring intelligently instead")
                            # Don't set has_ask_user - continue with intelligent inference
                            # Agent should create itinerary with smart defaults
                            if not session.trip_plan or not any([
                                session.trip_plan.travel.flights.outbound,
                                session.trip_plan.travel.flights.inbound,
                                session.trip_plan.accommodation.segments
                            ]):
                                # Only if no plan exists, create one with intelligent defaults
                                try:
                                    if status_callback:
                                        await status_callback("acting", "🧠 Agent กำลังใช้ AI วิเคราะห์และสร้างแผนการเดินทางด้วยตัวเอง...", "agent_intelligent_inference")
                                    # Create itinerary with intelligent defaults
                                    intelligent_payload = {
                                        "destination": payload.get("destination") or user_input or "Bangkok",  # Parse from input or default
                                        "start_date": payload.get("start_date") or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                                        "end_date": payload.get("end_date") or (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                                        "travel_mode": payload.get("travel_mode") or "both",
                                        "trip_type": payload.get("trip_type") or "round_trip",
                                        "guests": payload.get("guests") or 1,
                                        "origin": payload.get("origin") or "Bangkok",
                                        "focus": ["flights", "hotels", "transfers"]
                                    }
                                    await self._execute_create_itinerary(session, intelligent_payload, action_log, user_input)
                                except Exception as e:
                                    logger.error(f"Agent Mode: Error in intelligent inference: {e}", exc_info=True)
                            continue  # Skip ASK_USER in Agent Mode
                    
                    elif act_type == ActionType.CREATE_ITINERARY:
                        if status_callback:
                            await status_callback("acting", "กำลังสร้างแผนการเดินทาง...", "create_itinerary")
                        try:
                            await self._execute_create_itinerary(session, payload, action_log, user_input)
                        except Exception as e:
                            logger.error(f"Error executing CREATE_ITINERARY: {e}", exc_info=True)

                    elif act_type == ActionType.UPDATE_REQ:
                        if status_callback:
                            await status_callback("acting", "🤖 Agent กำลังอัปเดตข้อมูลทริป...", "update_req")
                        # Add to parallel tasks if possible, but UPDATE usually needs to happen before SEARCH
                        # For safety, execute UPDATEs sequentially first, then SEARCHes in parallel
                        try:
                            await self._execute_update_req(session, payload, action_log)
                        except Exception as e:
                            logger.error(f"Error executing UPDATE_REQ: {e}", exc_info=True)
                    
                    elif act_type == ActionType.CALL_SEARCH:
                        # ✅ ML validation ก่อนยิง search: ถ้าข้อมูลทริปไม่ผ่าน (วันที่/คน/งบประมาณ) ไม่ยิง search และถามผู้ใช้แก้ไข
                        if ml_validation_result and isinstance(ml_validation_result, dict) and ml_validation_result.get("valid") is False:
                            issues = ml_validation_result.get("issues", [])
                            warnings = ml_validation_result.get("warnings", [])
                            logger.info(
                                "[ML] Blocking CALL_SEARCH: data validation failed (valid=False). issues=%s",
                                issues,
                                extra={"session_id": session.session_id},
                            )
                            action_log.add_action(
                                "ASK_USER",
                                {
                                    "validation_issues": issues,
                                    "validation_warnings": warnings,
                                    "reason": "ml_validation_block_search",
                                    "message_hint": "กรุณาแก้ไขข้อมูลทริป (วันที่/จำนวนคน/งบประมาณ) ก่อนค้นหา",
                                },
                                "Block search: ML data validation failed; ask user to fix",
                                success=True,
                            )
                            has_ask_user = True
                            continue
                        # Collect search tasks for parallel execution
                        search_tasks.append(self._execute_call_search(session, payload, action_log))
                    
                    elif act_type == ActionType.SELECT_OPTION:
                        if status_callback:
                            await status_callback("selecting", "🤖 Agent กำลังบันทึกตัวเลือก...", "select_option")
                        try:
                            await self._execute_select_option(session, payload, action_log)
                        except Exception as e:
                            logger.error(f"Error executing SELECT_OPTION: {e}", exc_info=True)

                # ✅ Execute all search tasks in parallel with timeout for 1-minute completion
                if search_tasks:
                    if status_callback:
                        await status_callback("searching", "🤖 Agent กำลังค้นหาเที่ยวบินและที่พัก...", "call_search")
                    try:
                        # ✅ Set timeout for parallel searches: 35 seconds max (leaving time for LLM calls and other operations within 1.5-minute target)
                        results = await asyncio.wait_for(
                            asyncio.gather(*search_tasks, return_exceptions=True),
                            timeout=35.0  # ✅ Optimized for 1.5-minute completion
                        )
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Search tasks timed out after 35s - {len(search_tasks)} tasks")
                        # Cancel remaining tasks
                        for task in search_tasks:
                            if not task.done():
                                task.cancel()
                        # Return partial results if any completed
                        results = []
                        for task in search_tasks:
                            try:
                                if task.done():
                                    results.append(task.result())
                                else:
                                    results.append(Exception("Search timed out"))
                            except Exception as e:
                                results.append(e)
                    
                    # ✅ Validate search results; ถ้าล้มเหลวเพราะ ML validation ให้ถามผู้ใช้แก้ไข
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Search task failed: {result}")
                            err_msg = str(result)
                            if "ML_VALIDATION_BLOCK_SEARCH" in err_msg:
                                action_log.add_action(
                                    "ASK_USER",
                                    {
                                        "validation_issues": [err_msg.replace("ML_VALIDATION_BLOCK_SEARCH: ", "").strip()],
                                        "reason": "ml_validation_block_search",
                                        "message_hint": "กรุณาแก้ไขข้อมูลทริป (วันที่/จำนวนคน/งบประมาณ) ก่อนค้นหา",
                                    },
                                    "Search blocked by ML validation",
                                    success=True,
                                )
                                has_ask_user = True
                    
                    # ✅ Validate segment states after search
                    for slot_name, segment, idx in self.slot_manager.get_all_segments(session.trip_plan):
                        self.slot_manager.ensure_segment_state(segment, slot_name)
                    
                    # ✅ CRUD STABILITY: Agent Mode: Auto-select and auto-book immediately after search completes
                    if mode == "agent":
                        # Guard against concurrent auto-select calls
                        if not getattr(session, '_auto_select_in_progress', False):
                            setattr(session, '_auto_select_in_progress', True)
                            if status_callback:
                                await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด...", "agent_auto_select_immediate")

                            logger.info("Agent Mode: Search completed, immediately auto-selecting options...")
                            try:
                                await self._run_agent_mode_auto_complete(session, action_log, status_callback)
                            except Exception as auto_select_error:
                                logger.error(f"Agent Mode: Auto-select failed after search: {auto_select_error}", exc_info=True)
                            finally:
                                setattr(session, '_auto_select_in_progress', False)
                            
                            # ✅ CRUD STABILITY: Save session after auto-select to persist state
                            try:
                                await self.storage.save_session(session)
                            except Exception as save_error:
                                logger.warning(f"Agent Mode: Failed to save session after auto-select: {save_error}")
                        else:
                            logger.debug("Agent Mode: Auto-select already in progress, skipping duplicate call")
                
                # If any action was ASK_USER, break the loop
                if has_ask_user:
                    logger.info("Action includes ASK_USER, breaking loop")
                    break
            
            except Exception as e:
                logger.error(f"Error in controller loop iteration {iteration + 1}: {e}", exc_info=True)
                action_log.add_action(
                    "ERROR",
                    {},
                    f"Loop error: {str(e)}",
                    success=False
                )
                # Continue to next iteration instead of crashing
                continue
        
        # ✅ Agent Mode: Auto-select best options and auto-book (final check after all iterations)
        # Note: Auto-select also happens immediately after each search completes (inside loop)
        # This is a final check to ensure we catch any options that might have been missed
        if mode == "agent":
            # Check if there are still segments with options that need selection
            all_segments = (
                session.trip_plan.travel.flights.outbound +
                session.trip_plan.travel.flights.inbound +
                session.trip_plan.accommodation.segments +
                session.trip_plan.travel.ground_transport
            )
            
            has_options_to_select = any(
                seg.options_pool and not seg.selected_option 
                for seg in all_segments
            )
            # ✅ ถ้ามี selected options อยู่แล้ว (เช่น flight selected แต่ hotel ไม่มี options)
            # ให้ trigger booking ด้วย แทนที่จะข้ามไป
            has_any_selected = any(
                seg.selected_option is not None for seg in all_segments
            )
            
            if has_options_to_select or has_any_selected:
                if has_options_to_select and status_callback:
                    await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด (รอบสุดท้าย)...", "agent_auto_select_final")
                
                await self._run_agent_mode_auto_complete(session, action_log, status_callback)
                
                # Save session after final auto-select
                await self.storage.save_session(session)
        
        # ✅ Guardrail: After max_iterations, check if we need to ask user
        # If no ASK_USER action was taken and loop completed, we should have a response
        # But if state is incomplete, log a warning and force fallback to Responder
        if len(action_log.actions) > 0:
            last_action = action_log.actions[-1]
            if last_action.action != "ASK_USER" and last_action.action != "ERROR":
                # Check if we have any incomplete segments that need user input
                has_incomplete = False
                all_segments = (
                    session.trip_plan.travel.flights.outbound +
                    session.trip_plan.travel.flights.inbound +
                    session.trip_plan.accommodation.segments +
                    session.trip_plan.travel.ground_transport
                )
                for seg in all_segments:
                    if seg.status == SegmentStatus.PENDING and not seg.needs_search():
                        has_incomplete = True
                        break
                
                if has_incomplete:
                    logger.warning(
                        f"Controller loop completed ({max_iterations} iterations) without ASK_USER, but some segments may need user input. "
                        f"Forcing fallback to Responder.",
                        extra={"session_id": session.session_id, "user_id": session.user_id}
                    )
                    # Add a final ASK_USER action to force fallback
                    action_log.add_action(
                        "ASK_USER",
                        {"missing_fields": ["segment_completion"], "reason": "max_iterations_reached"},
                        "Force fallback after max iterations",
                        success=True
                    )
        
        # 🆕 COST TRACKING: Check budget and log summary
        try:
            is_over, current_cost, warning = self.cost_tracker.check_budget_limit(
                session.session_id,
                max_cost_usd=max_budget_usd
            )
            
            if is_over:
                logger.warning(
                    f"[COST] {warning}",
                    extra={"session_id": session.session_id, "cost_usd": current_cost}
                )
                agent_monitor.log_activity(
                    session.session_id,
                    session.user_id,
                    "cost_warning",
                    warning,
                    {"cost_usd": current_cost, "limit_usd": max_budget_usd}
                )
            else:
                logger.info(f"[COST] {warning}")
            
            # Get cost breakdown
            cost_breakdown = self.cost_tracker.get_cost_by_brain_type(session.session_id)
            if cost_breakdown:
                logger.info(
                    f"[COST] Breakdown by brain: {json.dumps(cost_breakdown, indent=2)}",
                    extra={"session_id": session.session_id}
                )
        except Exception as e:
            logger.warning(f"Failed to check cost budget: {e}")
        
        logger.info(
            f"[CONTROLLER] Loop completed after {max_iterations} iterations. Total actions: {len(action_log.actions)}",
            extra={"session_id": session.session_id, "user_id": session.user_id}
        )
        
        return action_log

    async def execute_controller_action(
        self,
        session: UserSession,
        action_log: ActionLog,
        user_input: str,
        mode: str,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        action: ControllerAction = None,
        ml_validation_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Execute one controller action (single or BATCH). Used by LangGraph full workflow.
        Returns True if has_ask_user (should break and go to responder).
        """
        if not action:
            return True
        actions_to_execute = []
        if action.batch_actions:
            for batch_item in action.batch_actions:
                act_type_str = batch_item.get("action")
                payload = batch_item.get("payload", {})
                if act_type_str and act_type_str.upper().strip() != "BATCH":
                    try:
                        actions_to_execute.append((ActionType(act_type_str.upper().strip()), payload))
                    except ValueError:
                        continue
        else:
            actions_to_execute.append((action.action, action.payload or {}))
        has_ask_user = False
        search_tasks = []
        for act_type, payload in actions_to_execute:
            if act_type == ActionType.BATCH:
                continue
            elif act_type == ActionType.ASK_USER:
                if mode == "normal":
                    has_ask_user = True
                    break
                if not session.trip_plan or not any([
                    session.trip_plan.travel.flights.outbound,
                    session.trip_plan.travel.flights.inbound,
                    session.trip_plan.accommodation.segments,
                ]):
                    try:
                        if status_callback:
                            await status_callback("acting", "🧠 Agent กำลังใช้ AI วิเคราะห์และสร้างแผนการเดินทางด้วยตัวเอง...", "agent_intelligent_inference")
                        intelligent_payload = {
                            "destination": payload.get("destination") or user_input or "Bangkok",
                            "start_date": payload.get("start_date") or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "end_date": payload.get("end_date") or (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                            "travel_mode": payload.get("travel_mode") or "both",
                            "trip_type": payload.get("trip_type") or "round_trip",
                            "guests": payload.get("guests") or 1,
                            "origin": payload.get("origin") or "Bangkok",
                            "focus": ["flights", "hotels", "transfers"],
                        }
                        await self._execute_create_itinerary(session, intelligent_payload, action_log, user_input)
                    except Exception as e:
                        logger.error(f"Agent Mode intelligent inference: {e}", exc_info=True)
                continue
            elif act_type == ActionType.CREATE_ITINERARY:
                if status_callback:
                    await status_callback("acting", "กำลังสร้างแผนการเดินทาง...", "create_itinerary")
                try:
                    await self._execute_create_itinerary(session, payload, action_log, user_input)
                except Exception as e:
                    logger.error(f"Error executing CREATE_ITINERARY: {e}", exc_info=True)
            elif act_type == ActionType.UPDATE_REQ:
                if status_callback:
                    await status_callback("acting", "🤖 Agent กำลังอัปเดตข้อมูลทริป...", "update_req")
                try:
                    await self._execute_update_req(session, payload, action_log)
                except Exception as e:
                    logger.error(f"Error executing UPDATE_REQ: {e}", exc_info=True)
            elif act_type == ActionType.CALL_SEARCH:
                if ml_validation_result and isinstance(ml_validation_result, dict) and ml_validation_result.get("valid") is False:
                    action_log.add_action(
                        "ASK_USER",
                        {
                            "validation_issues": ml_validation_result.get("issues", []),
                            "validation_warnings": ml_validation_result.get("warnings", []),
                            "reason": "ml_validation_block_search",
                            "message_hint": "กรุณาแก้ไขข้อมูลทริป (วันที่/จำนวนคน/งบประมาณ) ก่อนค้นหา",
                        },
                        "Block search: ML data validation failed; ask user to fix",
                        success=True,
                    )
                    has_ask_user = True
                    continue
                search_tasks.append(self._execute_call_search(session, payload, action_log))
            elif act_type == ActionType.SELECT_OPTION:
                if status_callback:
                    await status_callback("selecting", "🤖 Agent กำลังบันทึกตัวเลือก...", "select_option")
                try:
                    await self._execute_select_option(session, payload, action_log)
                except Exception as e:
                    logger.error(f"Error executing SELECT_OPTION: {e}", exc_info=True)
        if search_tasks:
            if status_callback:
                await status_callback("searching", "🤖 Agent กำลังค้นหาเที่ยวบินและที่พัก...", "call_search")
            # Wrap coroutines as Tasks so we can cancel them on timeout
            search_task_objects = [asyncio.ensure_future(coro) for coro in search_tasks]
            try:
                results = await asyncio.wait_for(
                    asyncio.gather(*search_task_objects, return_exceptions=True),
                    timeout=35.0,
                )
            except asyncio.TimeoutError:
                for t in search_task_objects:
                    if not t.done():
                        t.cancel()
                results = [Exception("Search timed out")] * len(search_task_objects)
            for result in results:
                if isinstance(result, Exception) and "ML_VALIDATION_BLOCK_SEARCH" in str(result):
                    has_ask_user = True
                    break
            for slot_name, segment, idx in self.slot_manager.get_all_segments(session.trip_plan):
                self.slot_manager.ensure_segment_state(segment, slot_name)
            if mode == "agent" and not (getattr(session, "_auto_select_in_progress", False)):
                if status_callback:
                    await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด...", "agent_auto_select_immediate")
                try:
                    await self._run_agent_mode_auto_complete(session, action_log, status_callback)
                    await self.storage.save_session(session)
                except Exception as e:
                    logger.error(f"Agent Mode auto-select after search: {e}", exc_info=True)
        return has_ask_user

    def _extract_trip_data_for_ml_validation(self, trip_plan: TripPlan) -> Dict[str, Any]:
        """ดึงข้อมูลทริปจาก TripPlan เป็น dict สำหรับ ML validate_extracted_data (วันที่, จำนวนคน, งบประมาณ)."""
        data: Dict[str, Any] = {}
        # departure_date / start_date จากเที่ยวบินขาไป
        outbound = (trip_plan.travel.flights.outbound or [])
        if outbound and outbound[0].requirements:
            data["departure_date"] = outbound[0].requirements.get("departure_date") or outbound[0].requirements.get("date")
            data["start_date"] = data.get("departure_date")
        # return_date / end_date จากเที่ยวบินขากลับ หรือที่พัก check_out
        inbound = (trip_plan.travel.flights.inbound or [])
        if inbound and inbound[0].requirements:
            data["return_date"] = inbound[0].requirements.get("departure_date") or inbound[0].requirements.get("date")
            data["end_date"] = data.get("return_date")
        acc = trip_plan.accommodation.segments or []
        if not data.get("start_date") and acc and acc[0].requirements:
            data["start_date"] = acc[0].requirements.get("check_in")
            data["departure_date"] = data.get("start_date")
        if not data.get("end_date") and acc and acc[0].requirements:
            data["end_date"] = acc[0].requirements.get("check_out")
            data["return_date"] = data.get("end_date")
        # guests / adults จาก segment ใดก็ได้
        for seg_list in [outbound, inbound, acc, (trip_plan.travel.ground_transport or [])]:
            for seg in seg_list:
                if not seg.requirements:
                    continue
                g = seg.requirements.get("guests") or seg.requirements.get("adults")
                if g is not None:
                    try:
                        data["guests"] = int(g) if isinstance(g, (int, float)) else int(str(g).strip())
                    except (TypeError, ValueError):
                        pass
                    else:
                        data["adults"] = data["guests"]
                        break
            if data.get("guests") is not None:
                break
        # budget จาก requirements ใดก็ได้
        for seg_list in [outbound, inbound, acc]:
            for seg in seg_list:
                if not seg.requirements:
                    continue
                b = seg.requirements.get("budget") or seg.requirements.get("budget_max")
                if b is not None:
                    data["budget"] = b
                    break
            if data.get("budget") is not None:
                break
        return data
    
    async def _call_controller_llm(
        self,
        state_json: str,
        user_input: str,
        action_log: ActionLog,
        memory_context: str = "",
        user_profile_context: str = "",
        mode: str = "normal",  # ✅ Pass mode to LLM
        session_id: str = "unknown",  # 🆕 For cost tracking
        user_id: str = "unknown",  # 🆕 For cost tracking
        workflow_validation: Optional[Dict[str, Any]] = None,  # ✅ สำหรับตรวจ workflow และ validate
        ml_intent_hint: Optional[Dict[str, Any]] = None,  # ✅ ML keyword decode สำหรับวางแผนแม่นยำ ~90% ใน 1 นาที
        ml_validation_result: Optional[Dict[str, Any]] = None,  # ✅ ML validate_extracted_data สำหรับวันที่/คน/งบประมาณ
    ) -> Optional[ControllerAction]:
        """
        Call Controller LLM to get next action
        
        Args:
            state_json: Current state as JSON string
            user_input: User's message
            action_log: Previous actions taken
            memory_context: Long-term memory about the user
            workflow_validation: Current workflow state (step, slots_complete) from Redis
            
        Returns:
            ControllerAction or None
        """
        try:
            # Build prompt
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt_with_date = CONTROLLER_SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", current_date)
            
            prompt_parts = [
                user_profile_context if user_profile_context else "",
                "=== USER LONG-TERM MEMORY (BRAIN) ===\n",
                memory_context,
                "\n=== CURRENT STATE (TRIP PLAN) ===\n",
                state_json,
                "\n=== LATEST USER INPUT ===\n",
                user_input,
            ]
            # ✅ ML KEYWORD DECODE: ใช้สำหรับวางแผนให้แม่นยำ ~90% และรวดเร็วใน 1 นาที
            if ml_intent_hint and isinstance(ml_intent_hint, dict) and ml_intent_hint.get("confidence", 0) >= 0.5:
                conf = ml_intent_hint.get("confidence", 0)
                intent = ml_intent_hint.get("intent", "")
                workflow_intent = ml_intent_hint.get("workflow_intent", intent)
                suggested = ml_intent_hint.get("suggested_slot", "")
                keywords = ml_intent_hint.get("keywords", [])
                prompt_parts.append("\n=== ML KEYWORD DECODE (USE FOR FASTER & ACCURATE PLANNING) ===\n")
                prompt_parts.append(
                    f"Intent: {intent} | workflow_intent: {workflow_intent} | confidence: {conf} | keywords: {keywords}"
                )
                if suggested:
                    prompt_parts.append(f"Planning hint: {suggested}")
                prompt_parts.append(
                    "When confidence >= 0.7, prefer actions that match this intent (e.g. UPDATE_REQ or CALL_SEARCH for the suggested slot) to complete in ~1 minute."
                )
            # ✅ Workflow state สำหรับให้ Controller ตรวจและ validate
            if workflow_validation:
                prompt_parts.append("\n=== WORKFLOW STATE (CHECK & VALIDATE) ===\n")
                prompt_parts.append(json.dumps(workflow_validation, ensure_ascii=False, indent=2))
                prompt_parts.append("\n(Use workflow.step to decide allowed actions; validate segment status and options_pool/selected_option consistency.)")
            # ✅ ML DATA VALIDATION: วันที่/จำนวนคน/งบประมาณ — ถ้า invalid หรือมี issues ให้แก้ด้วย UPDATE_REQ หรือ ASK_USER
            if ml_validation_result and isinstance(ml_validation_result, dict):
                valid = ml_validation_result.get("valid", True)
                conf = ml_validation_result.get("confidence", 1.0)
                issues = ml_validation_result.get("issues", [])
                warnings = ml_validation_result.get("warnings", [])
                prompt_parts.append("\n=== ML DATA VALIDATION (TRIP DATES / GUESTS / BUDGET) ===\n")
                prompt_parts.append(f"Valid: {valid} | confidence: {conf}")
                if issues:
                    prompt_parts.append(f"Issues (fix with UPDATE_REQ or ASK_USER): {issues}")
                if warnings:
                    prompt_parts.append(f"Warnings: {warnings}")
                prompt_parts.append("If valid is False or there are issues, prefer UPDATE_REQ to correct the trip plan or ASK_USER to clarify.")
            
            # Add action log if available
            if action_log.actions:
                prompt_parts.extend([
                    "\n=== ACTIONS TAKEN IN THIS TURN ===\n",
                    json.dumps([a.model_dump() for a in action_log.actions[-3:]], ensure_ascii=False, indent=2)
                ])
            
            # ✅ Add mode-specific instructions for GENIUS AUTONOMOUS mode
            if mode == "agent":
                prompt_parts.append(f"\n=== 🤖 AGENT MODE (100% GENIUS AUTONOMOUS) - CRITICAL RULES ===\n")
                prompt_parts.append("""You are a GENIUS AUTONOMOUS travel agent with FULL AI INTELLIGENCE.

🎯 MISSION: Complete the ENTIRE booking workflow WITHOUT asking the user questions.

🧠 INTELLIGENCE REQUIREMENTS:
1. **NEVER USE ASK_USER** - Only use ASK_USER if BOTH origin AND destination are completely missing AND cannot be inferred from ANY context
2. **INFER EVERYTHING** - Use your AI intelligence to infer ALL missing information:
   - Missing origin? Default to "Bangkok" (most common)
   - Missing date? Default to tomorrow or next weekend
   - Missing guests? Default by main booker age (ตามปีเกิด): age > 20 → 1 ผู้ใหญ่ (ผู้จองหลัก); age ≤ 20 → 1 ผู้ใหญ่ (ผู้จองร่วม) + 1 เด็ก (ผู้จองหลัก) = 2 คน. Infer 2+ only when explicit ("family" = 3-4, "couple" = 2)
   - Missing budget? Infer reasonable budget based on destination type
   - Missing trip_type? Default to "round_trip"
   - Missing travel_mode? Default to "both" for complete experience

3. **PREDICTIVE INTELLIGENCE**:
   - Beach destinations (Phuket, Samui, Krabi): Infer 2-4 nights, focus on hotels
   - City destinations (Tokyo, Seoul, Singapore): Infer 3-5 nights, focus on hotels + transport
   - Cultural destinations (Chiang Mai, Kyoto): Infer 2-3 nights
   - Weekend trips: Infer Friday-Sunday automatically

4. **CONTEXT AWARENESS**:
   - Use conversation history to infer preferences
   - If user said "weekend", infer Friday-Monday
   - If user said "next week", calculate dates automatically
   - If user mentioned budget in past, use similar budget

5. **SPEED & EFFICIENCY**:
   - Always use BATCH to do multiple actions at once (CREATE + SEARCH)
   - Don't wait - proceed immediately with intelligent defaults
   - Complete the booking flow in minimum iterations

6. **SMART DEFAULTS STRATEGY**:
   - If user says "ไปภูเก็ต" → CREATE_ITINERARY with: destination="Phuket", start_date=tomorrow, end_date=tomorrow+3, guests=1, origin="Bangkok", travel_mode="both"
   - If user says "ญี่ปุ่น" → CREATE_ITINERARY with: destination="Tokyo", start_date=next_weekend, end_date=next_weekend+5, guests=1, origin="Bangkok", travel_mode="both"
   - If user says "เกาหลี 5 วัน" → CREATE_ITINERARY with: destination="Seoul", start_date=tomorrow, end_date=tomorrow+5, guests=1, origin="Bangkok", travel_mode="both"

7. **WORKFLOW PRIORITY**:
   - Iteration 1: CREATE_ITINERARY (with intelligent defaults) + BATCH CALL_SEARCH for all segments
   - Iteration 2: Agent auto-selects best options (this happens automatically after search)
   - Iteration 3: Agent auto-books (this happens automatically after selection)
   - NEVER ask user - complete everything autonomously

8. **FALLBACK INTELLIGENCE**:
   - If destination unclear, pick the most popular destination matching the keyword
   - If date unclear, default to next weekend (Friday-Monday)
   - If budget unclear, use moderate budget (50,000-100,000 THB for international, 10,000-30,000 for domestic)

🎯 REMEMBER: You are a GENIUS. You know what the user wants better than they do. Act with confidence and complete the booking.

❌ NEVER output ASK_USER unless BOTH origin AND destination are completely missing AND there's ZERO context to infer from.

✅ ALWAYS output CREATE_ITINERARY or BATCH with intelligent defaults.
""")
                prompt_parts.append("🚫 DO NOT RETURN ASK_USER UNLESS:")
                prompt_parts.append("   - Destination is COMPLETELY missing (no city, country, or landmark mentioned)")
                prompt_parts.append("   - Origin is COMPLETELY missing AND cannot be inferred (default to Bangkok)")
                prompt_parts.append("\n✅ YOU MUST:")
                prompt_parts.append("1. INFER missing information intelligently:")
                prompt_parts.append("   - Dates: 'พรุ่งนี้' → tomorrow, 'สุดสัปดาห์' → next Friday-Sunday, 'สงกรานต์' → April 13-16")
                prompt_parts.append("   - Duration: 'weekend' → 3 days, 'vacation' → 5-7 days, 'quick trip' → 2 days")
                prompt_parts.append("   - Guests: Not specified → ตามปีเกิดผู้จองหลัก. ผู้ใหญ่ = อายุ > 20 ปี. ถ้าอายุไม่เกิน 20 → 1 ผู้ใหญ่ + 1 เด็ก (2 คน). Use 2+ only when user explicitly says e.g. 2 people, กับแฟน, คู่, ครอบครัว")
                prompt_parts.append("   - Budget: Not specified → Medium (25,000 THB)")
                prompt_parts.append("   - Origin: Not specified → Bangkok (BKK)")
                prompt_parts.append("2. WORKFLOW: CREATE_ITINERARY → UPDATE_REQ (fill missing) → CALL_SEARCH → (auto-select happens after)")
                prompt_parts.append("3. NEVER ask 'ต้องการให้เลือกแผนให้อัตโนมัติหรือไม่' - just DO IT")
                prompt_parts.append("4. NEVER ask for confirmation - just proceed with intelligent defaults")
                prompt_parts.append("5. If user says 'อยากไป X' → CREATE_ITINERARY immediately with inferred dates/budget")
                prompt_parts.append("\n")
            
            prompt_parts.append("\n=== INSTRUCTIONS ===\n")
            if mode == "agent":
                prompt_parts.append("🤖 AGENT MODE - FULL AUTONOMY:")
                prompt_parts.append("1. EXTRACT ALL information from User Input (dates, locations, guests, preferences).")
                prompt_parts.append("2. INFER missing information using intelligent defaults (see AGENT MODE rules above).")
                prompt_parts.append("3. CREATE_ITINERARY immediately if destination is mentioned (even if dates/budget missing).")
                prompt_parts.append("4. UPDATE_REQ to fill any missing details with inferred values.")
                prompt_parts.append("5. CALL_SEARCH immediately after requirements are set (don't wait for user).")
                prompt_parts.append("6. ❌ NEVER return ASK_USER - infer everything automatically.")
                prompt_parts.append("7. Use 'batch_actions' to do CREATE + UPDATE + SEARCH in one turn if possible.")
                prompt_parts.append("8. After CALL_SEARCH, auto-select and auto-book will happen automatically (you don't need to do it).")
            else:
                prompt_parts.append("📋 NORMAL MODE - USER SELECTS:")
                prompt_parts.append("1. EXTRACT ALL information from User Input (dates, locations, guests, preferences).")
                prompt_parts.append("2. OPTIMIZE SPEED: Use 'batch_actions' to perform multiple updates/searches in one turn.")
                prompt_parts.append("3. If user provides details for multiple slots, UPDATE ALL of them.")
                prompt_parts.append("4. If requirements are COMPLETE, CALL_SEARCH immediately.")
                prompt_parts.append("5. ❌ NEVER auto-select options - set status to SELECTING and wait for user to choose.")
                prompt_parts.append("6. ❌ NEVER auto-book - user must click booking button themselves.")
                prompt_parts.append("7. If user asks to select/book, use ASK_USER to clarify (but usually they'll select via UI).")
            prompt_parts.append("8. Output VALID JSON ONLY.")
            
            prompt = "\n".join(prompt_parts)
            
            # ✅ Use Production LLM Service - Controller Brain
            start_time = asyncio.get_running_loop().time()
            if self.production_llm:
                # วิเคราะห์ความยากจากข้อความผู้ใช้ แล้วสลับ Flash/Pro
                try:
                    task_complexity = ModelSelector.analyze_complexity(
                        user_input, context="controller", task_type=None
                    )
                    complexity = task_complexity.value  # "simple" | "moderate" | "complex"
                    if mode == "agent" and complexity == "simple":
                        complexity = "moderate"  # โหมด Agent อย่างน้อย moderate
                except Exception as e:
                    logger.debug(f"ModelSelector.analyze_complexity failed: {e}, using mode-based complexity")
                    complexity = "complex" if mode == "agent" else "moderate"
                data = await self.production_llm.controller_generate(
                    prompt=prompt,
                    system_prompt=system_prompt_with_date,
                    complexity=complexity
                )
                model_used = "gemini-2.5-pro"  # Default model for controller
                
                logger.debug(f"Controller LLM (production): model={model_used} has_thought={'thought' in data if isinstance(data, dict) else False} has_action={'action' in data if isinstance(data, dict) else False}")
            else:
                # Fallback to old LLM service
                data = await self.llm.generate_json(
                    prompt=prompt,
                    system_prompt=system_prompt_with_date,
                    temperature=settings.controller_temperature,
                    auto_select_model=True,
                    context="controller"
                )
                model_used = settings.gemini_flash_model  # Use from .env
            
            # 🆕 COST TRACKING: Track LLM call (estimate tokens from text length)
            # Note: 1 token ≈ 4 chars for English, ≈ 2-3 for Thai (we use 3 as average)
            try:
                end_time = asyncio.get_running_loop().time()
                latency_ms = (end_time - start_time) * 1000
                
                # Estimate tokens (rough approximation)
                input_tokens = len(prompt) // 3
                output_tokens = len(json.dumps(data)) // 3 if data else 0
                
                # Track the call
                self.cost_tracker.track_llm_call(
                    session_id=session_id,
                    user_id=user_id,
                    model=model_used,
                    brain_type="controller",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    mode=mode,
                    latency_ms=latency_ms,
                    success=True
                )
            except Exception as e:
                logger.warning(f"Failed to track LLM cost: {e}")
            
            logger.debug(f"Controller LLM raw response: type={type(data).__name__} exists={data is not None} preview={str(data)[:200] if data else None}")
            
            if not data or not isinstance(data, dict):
                logger.error(f"Invalid response from Controller LLM: {data}")
                # 🧠 Error Recovery: Return safe default action based on mode
                if mode == "agent":
                    # Agent Mode: Never ask, create itinerary with defaults
                    return ControllerAction(
                        thought="LLM returned invalid JSON, Agent Mode: creating itinerary with intelligent defaults",
                        action="CREATE_ITINERARY",
                        payload={
                            "destination": user_input or "Bangkok",
                            "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                            "end_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                            "guests": 1,
                            "origin": "Bangkok",
                            "travel_mode": "both",
                            "trip_type": "round_trip"
                        }
                    )
                else:
                    # Normal Mode: Ask user
                    return ControllerAction(
                        thought="LLM returned invalid JSON, asking user for clarification",
                        action="ASK_USER",
                        payload={"missing_fields": ["all"]}
                    )
            
            logger.debug(f"Controller LLM self-correction check: action={data.get('action')} thought={'present' if 'thought' in data else 'missing'}")
            
            # 🧠 Self-Correction: Check for missing keys and add defaults based on mode
            # ✅ FIX: Add default thought if missing (common LLM oversight)
            if "thought" not in data:
                action_type = data.get("action", "action")
                data["thought"] = f"Processing {action_type} with intelligent defaults"
                logger.warning(f"LLM response missing 'thought' field, added default: '{data['thought']}'")
            
            if "action" not in data:
                if mode == "agent":
                    logger.warning("Controller LLM response missing 'action', Agent Mode: defaulting to CREATE_ITINERARY")
                    data["action"] = "CREATE_ITINERARY"
                    data["thought"] = data.get("thought", "Missing action in response - Agent Mode: creating itinerary with defaults")
                    data["payload"] = data.get("payload", {
                        "destination": user_input or "Bangkok",
                        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "end_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                        "guests": 1,
                        "origin": "Bangkok"
                    })
                else:
                    logger.warning("Controller LLM response missing 'action', Normal Mode: defaulting to ASK_USER")
                    data["action"] = "ASK_USER"
                    data["thought"] = data.get("thought", "Missing action in response - recovering with ASK_USER")
                    data["payload"] = data.get("payload", {"missing_fields": []})

            # Fix common BATCH error where list is in payload instead of batch_actions
            if data.get("action") == "BATCH" and isinstance(data.get("payload"), list):
                logger.warning("Fixing BATCH action: payload is list, moving to batch_actions")
                data["batch_actions"] = data["payload"]
                data["payload"] = {}

            logger.debug(f"Controller LLM: validating ControllerAction action={data.get('action')}")

            # Validate and create ControllerAction
            action = ControllerAction(**data)
            
            # ✅ Agent Mode: ALWAYS override ASK_USER - never ask user in Agent Mode
            if mode == "agent" and action.action == ActionType.ASK_USER:
                logger.info("Agent Mode: Overriding ASK_USER - Agent Mode never asks user, inferring everything automatically")
                # Always create itinerary with intelligent defaults
                action = ControllerAction(
                    thought="Agent Mode: Overriding ASK_USER - inferring all missing information automatically",
                    action=ActionType.CREATE_ITINERARY,
                    payload={
                        "destination": user_input or "Bangkok",  # Parse from input or default
                        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),  # Tomorrow
                        "end_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),  # 3 nights
                        "guests": 1,  # Default: 1 ผู้ใหญ่ (ผู้จองหลัก)
                        "origin": "Bangkok",  # Default
                        "travel_mode": "both",
                        "trip_type": "round_trip",
                        "focus": ["flights", "hotels", "transfers"]
                    }
                )
                # Log override
                action_log.add_action(
                    "OVERRIDE_ASK_USER_TO_CREATE",
                    action.payload,
                    "Agent Mode: Forced CREATE_ITINERARY with intelligent defaults (never ask user)"
                )
            
            return action
        
        except LLMException as e:
            logger.error(f"LLM error in controller (timeout/API error): {e}", exc_info=True)
            # 🧠 Error Recovery: Always return a valid ControllerAction, never None
            if mode == "agent":
                # Agent Mode: Try to create itinerary anyway with intelligent defaults
                logger.info(f"Agent Mode: LLM error, creating itinerary with intelligent defaults")
                return ControllerAction(
                    thought=f"LLM error but Agent Mode: creating itinerary with intelligent defaults",
                    action=ActionType.CREATE_ITINERARY,
                    payload={
                        "destination": user_input or "Bangkok",
                        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                        "end_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),
                        "guests": 1,
                        "origin": "Bangkok",
                        "travel_mode": "both",
                        "trip_type": "round_trip"
                    }
                )
            # Normal Mode: Ask user
            return ControllerAction(
                thought=f"LLM service error: {str(e)[:100]}. Asking user to retry or rephrase.",
                action="ASK_USER",
                payload={"error": "llm_service_error", "message": "กรุณาลองใหม่อีกครั้งหรือพูดใหม่อีกรอบ"}
            )
        except Exception as e:
            logger.error(f"Error calling Controller LLM: {e}", exc_info=True)
            # 🧠 Error Recovery: In Agent Mode, try to infer and continue
            if mode == "agent":
                return ControllerAction(
                    thought=f"Error but Agent Mode: attempting to create itinerary with defaults",
                    action="CREATE_ITINERARY",
                    payload={
                        "destination": user_input,
                        "start_date": "tomorrow",
                        "guests": 1,
                        "origin": "Bangkok"
                    }
                )
            # Normal Mode: Ask user
            return ControllerAction(
                thought=f"Unexpected error: {str(e)[:100]}. Asking user for help.",
                action="ASK_USER",
                payload={"error": "unexpected_error", "message": "เกิดข้อผิดพลาด กรุณาลองอธิบายอีกครั้ง"}
            )
    
    async def _execute_create_itinerary(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog,
        user_input: str = ""  # 🆕 Add user_input for fallback extraction
    ):
        """
        Execute CREATE_ITINERARY action with Intelligence Layer.
        Automatically structures the TripPlan based on high-level intent.
        Enhanced with: validation, location intelligence, budget advisory, proactive suggestions.
        ผู้ใหญ่ = อายุ > 20 ปี (ตามปีเกิด). ถ้าผู้จองหลักอายุไม่เกิน 20 → 1 ผู้ใหญ่ + 1 เด็ก = 2 คน
        """
        # ✅ ดึงปีเกิดผู้จองหลักเพื่อกำหนด default ผู้ใหญ่/เด็ก (อายุ > 20 = ผู้ใหญ่)
        main_booker_dob = await self._get_main_booker_dob(session.user_id)
        # ✅ ACCURACY ~90%: Normalize and correct payload before use
        payload = self._normalize_create_itinerary_payload(payload, user_input, main_booker_dob)
        
        destination = payload.get("destination")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        travel_mode_str = (payload.get("travel_mode") or "both").strip().lower()
        adults = int(payload.get("adults") or payload.get("guests", 1))
        children = int(payload.get("children", 0))
        guests = adults + children  # total for segment requirements
        origin = (payload.get("origin") or "Bangkok").strip() or "Bangkok"
        budget = payload.get("budget")
        focus = payload.get("focus")
        if not isinstance(focus, list):
            focus = ["flights", "hotels", "transfers"]
        focus = [str(f).strip().lower() for f in focus if f]
        if not focus:
            focus = ["flights", "hotels", "transfers"]
        
        # ✅ บินตรง: ถ้าผู้ใช้พิมพ์ "บินตรง" / direct / nonstop ในข้อความ ให้ใส่ direct_flight ใน payload
        if payload.get("direct_flight") is not True and payload.get("non_stop") is not True and user_input:
            ui_lower = (user_input or "").strip().lower()
            if "บินตรง" in user_input or "direct" in ui_lower or "nonstop" in ui_lower or "ไม่ต่อเครื่อง" in user_input:
                payload["direct_flight"] = True
        
        # 🛂 ปลายทาง "ทั้งหมด" / "all" / "ทุกที่" → แสดงจุดหมายยอดนิยม (ไม่สร้างเที่ยวบิน/ที่พัก)
        dest_lower = (destination or "").strip().lower()
        if dest_lower in ["ทั้งหมด", "all", "ทุกที่", "ทุกแห่ง", "ทุกแห่งหน"]:
            try:
                from app.services.travel_service import orchestrator
                destinations = await orchestrator.get_popular_destinations()
                session.popular_destinations = destinations
                session.update_timestamp()
                action_log.add_action(
                    "POPULAR_DESTINATIONS",
                    {"destinations": destinations, "count": len(destinations)},
                    f"พบจุดหมายยอดนิยม {len(destinations)} แห่ง (ผู้ใช้ค้นหา 'ทั้งหมด' ในปลายทาง)"
                )
                logger.info(f"✅ User searched 'all' in destination: returning {len(destinations)} popular destinations")
                return
            except Exception as e:
                logger.warning(f"Failed to get popular destinations for 'all' search: {e}")
                action_log.add_action("POPULAR_DESTINATIONS", {"error": str(e)}, "ไม่สามารถโหลดจุดหมายยอดนิยมได้")
                return
        
        # ✅ Smart end_date inference from days/nights
        days_mentioned = payload.get("days") or payload.get("nights")
        
        # 🆕 FALLBACK: Extract days from user_input if LLM didn't provide it
        if not days_mentioned and user_input:
            # Match patterns like "3 วัน", "4 days", "2 คืน", "5 nights"
            import re
            match = re.search(r'(\d+)\s*(?:วัน|days?|คืน|nights?)', user_input, re.IGNORECASE)
            if match:
                days_mentioned = int(match.group(1))
                logger.info(f"🔍 Extracted days from user_input as fallback: {days_mentioned} days")
        
        # ✅ CRITICAL FIX: Always recalculate end_date if days_mentioned exists
        # This ensures correct calculation even if LLM provided wrong end_date
        if start_date and days_mentioned:
            try:
                days = int(days_mentioned)
                normalized_start = self._normalize_date(start_date)
                if normalized_start:
                    start_dt = datetime.strptime(normalized_start, "%Y-%m-%d")
                    # "Stay for X days" means X nights, so return/check-out date = start_date + X days
                    # Example: start_date=Jan 30, "stay for 3 days" → end_date=Feb 2 (not Feb 1)
                    end_dt = start_dt + timedelta(days=days)
                    calculated_end_date = end_dt.strftime("%Y-%m-%d")
                    
                    # ✅ If LLM provided end_date but it differs from calculated, use calculated and warn
                    if end_date and end_date != calculated_end_date:
                        logger.warning(f"⚠️ LLM provided end_date={end_date} but calculated={calculated_end_date} from {days} days. Using calculated value.")
                    
                    end_date = calculated_end_date
                    logger.info(f"✅ Calculated end_date from {days} days: {start_date} + {days} days = {end_date}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Could not infer end_date from days/nights: {e}")
        
        # 🧠 Intelligence Layer: Input Validation
        validation_warnings = []
        
        # Validate dates
        normalized_start = self._normalize_date(start_date)
        normalized_end = self._normalize_date(end_date) if end_date else None
        
        if normalized_start and normalized_end:
            is_valid_dates, date_error = agent_intelligence.validator.validate_date_range(normalized_start, normalized_end)
            if not is_valid_dates:
                validation_warnings.append(f"⚠️ วันที่: {date_error}")
                logger.warning(f"Date validation failed: {date_error}")
            else:
                logger.info(f"✅ Date validation passed: {normalized_start} to {normalized_end} ({(datetime.strptime(normalized_end, '%Y-%m-%d') - datetime.strptime(normalized_start, '%Y-%m-%d')).days} days)")
        elif normalized_start:
            logger.info(f"✅ Start date set: {normalized_start} (one-way trip or end_date will be set later)")
        
        # Validate guests
        is_valid_guests, guest_error = agent_intelligence.validator.validate_guests(guests)
        if not is_valid_guests:
            validation_warnings.append(f"⚠️ จำนวนผู้เดินทาง: {guest_error}")
            logger.warning(f"Guest validation failed: {guest_error}")
        
        # Validate budget (if provided)
        if budget:
            is_valid_budget, budget_error = agent_intelligence.validator.validate_budget(budget)
            if not is_valid_budget:
                validation_warnings.append(f"⚠️ งบประมาณ: {budget_error}")
                logger.warning(f"Budget validation failed: {budget_error}")
        
        # 🧠 Intelligence Layer: Location Resolution
        # For flights, landmarks are resolved to cities
        # For hotels, landmarks are kept as precise search locations
        
        dest_info = LocationIntelligence.resolve_location(destination, context="flight")
        origin_info = LocationIntelligence.resolve_location(origin, context="flight")
        
        # Extract the appropriate location for flight bookings
        if dest_info.get("is_landmark") or dest_info.get("airport_code"):
            flight_destination = dest_info.get("airport_code") or dest_info["city"]
            hotel_destination = dest_info.get("landmark_name") or dest_info["city"]
            logger.info(f"Resolved destination: '{destination}' -> Flights to {flight_destination}, Hotels near {hotel_destination}")
        else:
            flight_destination = destination
            hotel_destination = destination
        
        if origin_info.get("is_landmark") or origin_info.get("airport_code"):
            flight_origin = origin_info.get("airport_code") or origin_info["city"]
            logger.info(f"Resolved origin: '{origin}' -> Flights from {flight_origin}")
        else:
            flight_origin = origin
        
        # ✅ STEP 2: Route Planning using Google Maps MCP (plan_route or plan_route_with_waypoints)
        route_plan = None
        route_plan_through = None  # Full result when waypoints used (has route.waypoints, route_details.legs)
        origin_airport_iata = None
        dest_airport_iata = None
        recommended_transport = []
        waypoints = list(payload.get("waypoints") or [])
        waypoints = [str(w).strip() for w in waypoints if w and str(w).strip()]
        
        if self.mcp_executor and origin and destination:
            try:
                if waypoints:
                    logger.info(f"🗺️ Plan through: {origin} → {' → '.join(waypoints)} → {destination}")
                    route_result = await asyncio.wait_for(
                        self.mcp_executor.execute_tool(
                            "plan_route_with_waypoints",
                            {
                                "origin": origin,
                                "destination": destination,
                                "waypoints": waypoints,
                                "travel_mode": "driving"
                            }
                        ),
                        timeout=15.0
                    )
                    if route_result.get("success") and route_result.get("route"):
                        route_plan_through = route_result
                        r = route_result["route"]
                        route_plan = {
                            "origin": r.get("origin", {}),
                            "destination": r.get("destination", {}),
                            "distance_km": r.get("distance_km"),
                            "recommended_transportation": ["car", "bus", "train"],
                            "waypoints": r.get("waypoints", []),
                            "route_details": route_result.get("route", {}).get("route_details") or route_result.get("route")
                        }
                        origin_airport_iata = (r.get("origin") or {}).get("nearest_airport")
                        dest_airport_iata = (r.get("destination") or {}).get("nearest_airport")
                        recommended_transport = route_plan.get("recommended_transportation", [])
                        action_log.add_action(
                            "ROUTE_PLANNING_THROUGH",
                            {"origin": origin, "waypoints": waypoints, "destination": destination},
                            f"Route planned through {len(waypoints)} waypoints, {route_plan.get('distance_km')} km"
                        )
                else:
                    logger.info(f"🗺️ Planning route from {origin} to {destination} using Google Maps...")
                    route_result = await asyncio.wait_for(
                        self.mcp_executor.execute_tool(
                            "plan_route",
                            {
                                "origin": origin,
                                "destination": destination,
                                "travel_mode": "driving"
                            }
                        ),
                        timeout=10.0
                    )
                
                if not waypoints and route_result.get("success") and route_result.get("route"):
                    route_plan = route_result["route"]
                    origin_airport_iata = route_plan.get("origin", {}).get("nearest_airport")
                    dest_airport_iata = route_plan.get("destination", {}).get("nearest_airport")
                    recommended_transport = route_plan.get("recommended_transportation", [])
                    distance_km = route_plan.get("distance_km", 0)
                    logger.info(f"✅ Route planned: {distance_km} km, Origin Airport: {origin_airport_iata}, Dest Airport: {dest_airport_iata}")
                    logger.info(f"✅ Recommended transport: {recommended_transport}")
                    if origin_airport_iata:
                        flight_origin = origin_airport_iata
                    if dest_airport_iata:
                        flight_destination = dest_airport_iata
                    action_log.add_action(
                        "ROUTE_PLANNING",
                        {"origin": origin, "destination": destination},
                        f"Route planned: {distance_km} km, airports: {origin_airport_iata}→{dest_airport_iata}, transport: {recommended_transport}"
                    )
                elif waypoints and not route_plan:
                    logger.warning(f"Plan-through route failed or no route: {route_result}")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Route planning timed out - continuing without route plan")
            except Exception as e:
                logger.warning(f"Route planning error (non-fatal): {e}", exc_info=True)
        
        # Update variables for flight booking
        origin = flight_origin
        # For destination, we'll use flight_destination for flights and hotel_destination for hotels later
        
        # 🧠 Intelligence Layer: Budget Advisory
        budget_warnings = []
        if normalized_start and normalized_end:
            try:
                nights = (datetime.fromisoformat(normalized_end) - datetime.fromisoformat(normalized_start)).days
                estimated = BudgetAdvisor.estimate_trip_cost(
                    destination=destination,
                    nights=nights,
                    guests=guests,
                    travel_mode=travel_mode_str,
                    style="moderate"
                )
                
                logger.info(f"Budget estimate: {estimated.total:,} THB (Flights: {estimated.flights:,}, Hotels: {estimated.hotels:,}, Food: {estimated.food:,})")
                
                if budget:
                    is_feasible, budget_msg = BudgetAdvisor.check_budget_feasibility(budget, estimated.total)
                    if not is_feasible:
                        budget_warnings.append(f"💰 {budget_msg}")
                        logger.warning(f"Budget feasibility: {budget_msg}")
                else:
                    # Suggest a budget
                    budget_warnings.append(f"💡 งบประมาณแนะนำ: {estimated.total:,} บาท")
                
                # Add budget warnings from estimator
                if estimated.warnings:
                    budget_warnings.extend([f"💡 {w}" for w in estimated.warnings])
                    
            except Exception as e:
                logger.error(f"Budget estimation error: {e}")
        
        # Log all intelligence warnings
        if validation_warnings or budget_warnings:
            all_warnings = validation_warnings + budget_warnings
            logger.info(f"Intelligence warnings: {all_warnings}")
            # Store warnings in action_log for response generation
            action_log.add_action("INTELLIGENCE_CHECK", {"warnings": all_warnings}, f"Found {len(all_warnings)} intelligence warnings")
        
        # Normalize travel mode
        try:
            travel_mode = TravelMode(travel_mode_str)
        except ValueError:
            travel_mode = TravelMode.BOTH

        # -------------------------------------------------------------------------
        # GUARD: Check for Duplicate/Refresh Request
        # If the plan already has options for the SAME start_date, assume it's a refresh.
        # This prevents the agent from wiping the plan and re-searching unnecessarily.
        # -------------------------------------------------------------------------
        has_options = False
        matching_date = False
        normalized_start = self._normalize_date(start_date)
        
        all_segments = (
            session.trip_plan.travel.flights.outbound + 
            session.trip_plan.travel.flights.inbound + 
            session.trip_plan.accommodation.segments + 
            session.trip_plan.travel.ground_transport
        )
        
        for seg in all_segments:
            if len(seg.options_pool) > 0:
                has_options = True
                # Check date match
                req_date = seg.requirements.get("departure_date") or seg.requirements.get("check_in") or seg.requirements.get("date")
                if req_date == normalized_start:
                    matching_date = True
                    break
        
        if has_options and matching_date:
             logger.info(f"CREATE_ITINERARY: Detected duplicate/refresh request for date {normalized_start}. Preserving existing plan.")
             action_log.add_action("CREATE_ITINERARY", payload, "Preserved existing plan (Duplicate/Refresh detected)")
             return
        # -------------------------------------------------------------------------

        # Reset Trip Plan
        session.trip_plan = TripPlan()
        session.trip_plan.travel.mode = travel_mode
        
        # Trip Type Detection
        trip_type = payload.get("trip_type", "round_trip")
        
        # ✅ Smart end_date inference for multi-day trips
        # If end_date is missing but we have start_date, try to infer from context
        if not end_date and start_date:
            # Check if user mentioned days/nights in payload or requirements
            nights_mentioned = payload.get("nights") or payload.get("days")
            if nights_mentioned:
                try:
                    nights = int(nights_mentioned)
                    start_dt = datetime.strptime(self._normalize_date(start_date), "%Y-%m-%d")
                    # "Stay for X days" means X nights, so return/check-out date = start_date + X days
                    # Example: start_date=Jan 30, "stay for 3 days" → end_date=Feb 2 (not Feb 1)
                    end_dt = start_dt + timedelta(days=nights)
                    end_date = end_dt.strftime("%Y-%m-%d")
                    logger.info(f"Inferred end_date from {nights} days: {end_date}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not infer end_date from nights: {e}")
        
        # Heuristic: If end_date is missing, force one_way. 
        # But if it's round_trip and end_date is missing, we might assume same day return or just fallback to one_way.
        # However, default is round_trip, so if end_date IS present, it stays round_trip.
        if not end_date:
            trip_type = "one_way"
        else:
            # If end_date exists, ensure it's round_trip (unless explicitly one_way)
            if trip_type != "one_way":
                trip_type = "round_trip"
        
        # ✅ Save trip type to travel slot
        session.trip_plan.travel.trip_type = trip_type 

        # 1. Setup Flights (only if in focus and mode is flight/both)
        if "flights" in focus and travel_mode in [TravelMode.FLIGHT_ONLY, TravelMode.BOTH]:
            # ✅ Use airport IATA codes from route planning if available
            flight_origin_code = origin_airport_iata or origin
            flight_dest_code = dest_airport_iata or flight_destination
            
            # Outbound (use airport IATA codes from route planning)
            outbound = Segment()
            outbound.requirements = {
                "origin": flight_origin_code,
                "destination": flight_dest_code,
                "departure_date": self._normalize_date(start_date),
                "adults": adults,
                "children": children,
                "guests": guests,
            }
            # ✅ Store route planning results in requirements
            if route_plan:
                outbound.requirements["_route_plan"] = {
                    "distance_km": route_plan.get("distance_km"),
                    "recommended_transportation": recommended_transport,
                    "origin_airport": origin_airport_iata,
                    "dest_airport": dest_airport_iata
                }
            if budget:
                outbound.requirements["max_price"] = budget
            # ✅ บินตรง: ใส่ direct_flight ใน requirements เมื่อผู้ใช้ขอ "บินตรง" / direct / nonstop
            if payload.get("direct_flight") is True or payload.get("non_stop") is True:
                outbound.requirements["direct_flight"] = True
            session.trip_plan.travel.flights.outbound.append(outbound)
            
            # Return (Default behavior: Always add return flight unless explicitly one_way OR no end_date)
            if trip_type == "round_trip" and end_date:
                return_flight = Segment()
                return_flight.requirements = {
                    "origin": flight_dest_code,  # Use airport IATA from route planning
                    "destination": flight_origin_code,  # Use airport IATA from route planning
                    "departure_date": self._normalize_date(end_date),
                    "adults": adults,
                    "children": children,
                    "guests": guests,
                }
                # ✅ Store route planning results in requirements
                if route_plan:
                    return_flight.requirements["_route_plan"] = {
                        "distance_km": route_plan.get("distance_km"),
                        "recommended_transportation": recommended_transport,
                        "origin_airport": dest_airport_iata,
                        "dest_airport": origin_airport_iata
                    }
                if budget:
                    return_flight.requirements["max_price"] = budget
                # ✅ บินตรง: ใส่ direct_flight ใน requirements เมื่อผู้ใช้ขอ "บินตรง" / direct / nonstop
                if payload.get("direct_flight") is True or payload.get("non_stop") is True:
                    return_flight.requirements["direct_flight"] = True
                session.trip_plan.travel.flights.inbound.append(return_flight)

        # 2. Setup Accommodation (only if in focus: hotels or rentals ที่พักให้เช่า)
        if "hotels" in focus or "rentals" in focus:
            # 🧠 ENHANCED: Intelligent destination type detection for smart planning
            destination_type = self._detect_destination_type(destination)
            logger.info(f"🧠 Detected destination type: {destination_type} for {destination}")
            
            # Use hotel_destination (which preserves landmarks like "Siam Paragon")
            # Multi-city detection
            cities = []
            hotel_search_location = hotel_destination if dest_info.get("is_landmark") else destination
            
            if " และ " in hotel_search_location:
                cities = [c.strip() for c in hotel_search_location.split(" และ ")]
            elif " and " in hotel_search_location.lower():
                import re
                cities = [c.strip() for c in re.split(r" and ", hotel_search_location, flags=re.IGNORECASE)]
            elif "," in hotel_search_location:
                cities = [c.strip() for c in hotel_search_location.split(",")]
            else:
                cities = [hotel_search_location]
            
            # 🧠 ENHANCED: Smart nights inference based on destination type
            if start_date and end_date:
                try:
                    d1 = datetime.strptime(self._normalize_date(start_date), "%Y-%m-%d")
                    d2 = datetime.strptime(self._normalize_date(end_date), "%Y-%m-%d")
                    calculated_nights = (d2 - d1).days
                    
                    # 🧠 Suggest optimal nights based on destination type
                    suggested_nights = self._suggest_optimal_nights(destination_type, calculated_nights)
                    if suggested_nights != calculated_nights and calculated_nights <= 1:
                        logger.info(f"🧠 Destination type '{destination_type}' suggests {suggested_nights} nights (current: {calculated_nights})")
                        # Update end_date if too short
                        if calculated_nights < suggested_nights:
                            new_end_date = (d1 + timedelta(days=suggested_nights)).strftime("%Y-%m-%d")
                            end_date = new_end_date
                            logger.info(f"🧠 Adjusted end_date to {end_date} for better {destination_type} experience")
                except Exception as e:
                    logger.warning(f"Could not adjust nights based on destination type: {e}")

            if start_date and end_date and len(cities) > 0:
                try:
                    d1 = datetime.strptime(self._normalize_date(start_date), "%Y-%m-%d")
                    d2 = datetime.strptime(self._normalize_date(end_date), "%Y-%m-%d")
                    total_nights = (d2 - d1).days
                    
                    if total_nights > 0:
                        nights_per_city = total_nights // len(cities)
                        remainder = total_nights % len(cities)
                        
                        current_check_in = d1
                        for i, city in enumerate(cities):
                            # Last city gets the remainder nights
                            stay_nights = nights_per_city + (1 if i < remainder else 0)
                            if stay_nights <= 0 and i > 0: continue # Skip if no nights left
                            
                            check_out = current_check_in + timedelta(days=stay_nights)
                            
                            acc_segment = Segment()
                            acc_segment.requirements = {
                                "location": city,
                                "check_in": current_check_in.strftime("%Y-%m-%d"),
                                "check_out": check_out.strftime("%Y-%m-%d"),
                                "guests": guests,
                                "adults": adults,
                                "children": children,
                            }
                            if budget:
                                acc_segment.requirements["max_price"] = budget
                            session.trip_plan.accommodation.segments.append(acc_segment)
                            
                            current_check_in = check_out
                    else:
                        # Same day or invalid, just add one segment for the first city
                        acc_segment = Segment()
                        acc_segment.requirements = {
                            "location": cities[0],
                            "check_in": self._normalize_date(start_date),
                            "check_out": self._normalize_date(end_date),
                            "guests": guests,
                            "adults": adults,
                            "children": children,
                        }
                        session.trip_plan.accommodation.segments.append(acc_segment)
                except Exception as e:
                    logger.error(f"Error calculating multi-city nights: {e}")
                    # Fallback to single segment
                    acc_segment = Segment()
                    acc_segment.requirements = {
                        "location": destination,
                        "check_in": self._normalize_date(start_date),
                        "check_out": self._normalize_date(end_date),
                        "guests": guests,
                        "adults": adults,
                        "children": children,
                    }
                    session.trip_plan.accommodation.segments.append(acc_segment)
        
        # 3. Setup Ground Transport (if in focus) - 🧠 ENHANCED: Logical ordering + plan_through legs
        if "transfers" in focus:
            # ✅ Plan through: create one ground_transport segment per leg (origin→wp1, wp1→wp2, ...→destination)
            if waypoints and route_plan_through and route_plan_through.get("route"):
                r = route_plan_through["route"]
                legs = (r.get("route_details") or {}) if isinstance(r.get("route_details"), dict) else {}
                leg_list = legs.get("legs") if isinstance(legs.get("legs"), list) else []
                if not leg_list and waypoints:
                    # Build legs from waypoints: origin→wp0, wp0→wp1, ..., wpN→destination
                    all_stops = [origin] + waypoints + [destination]
                    for i in range(len(all_stops) - 1):
                        seg = Segment()
                        seg.requirements = {
                            "origin": all_stops[i],
                            "destination": all_stops[i + 1],
                            "date": self._normalize_date(start_date),
                            "passengers": guests
                        }
                        seg.requirements["_plan_through_leg"] = True
                        if budget:
                            seg.requirements["max_price"] = budget
                        session.trip_plan.travel.ground_transport.append(seg)
                    logger.info(f"✅ Plan through: added {len(all_stops)-1} ground_transport segments (origin→waypoints→destination)")
                elif leg_list:
                    for leg in leg_list:
                        seg = Segment()
                        seg.requirements = {
                            "origin": leg.get("from") or origin,
                            "destination": leg.get("to") or destination,
                            "date": self._normalize_date(start_date),
                            "passengers": guests
                        }
                        seg.requirements["_plan_through_leg"] = True
                        if budget:
                            seg.requirements["max_price"] = budget
                        session.trip_plan.travel.ground_transport.append(seg)
                    logger.info(f"✅ Plan through: added {len(leg_list)} ground_transport segments from route legs")
            elif travel_mode == TravelMode.BOTH:
                # 🧠 ENHANCED: Only add transfers if flights exist (logical ordering)
                has_flights = len(session.trip_plan.travel.flights.outbound) > 0 or len(session.trip_plan.travel.flights.inbound) > 0
                
                if has_flights:
                    # Airport Transfer (Arrival) - 🧠 Use airport IATA from route planning
                    transfer_arr = Segment()
                    transfer_arr.requirements = {
                        "origin": dest_airport_iata or f"{destination} Airport",
                        "destination": hotel_destination or destination,
                        "date": self._normalize_date(start_date),
                        "passengers": guests
                    }
                    # 🧠 Store route planning context
                    if route_plan:
                        transfer_arr.requirements["_route_plan"] = {
                            "destination_airport": dest_airport_iata,
                            "hotel_location": hotel_destination
                        }
                    if budget:
                        transfer_arr.requirements["max_price"] = budget
                    session.trip_plan.travel.ground_transport.append(transfer_arr)
                    
                    # Airport Transfer (Departure) - Only if round_trip or end_date exists
                    if trip_type == "round_trip" and end_date:
                        transfer_dep = Segment()
                        transfer_dep.requirements = {
                            "origin": hotel_destination or destination,
                            "destination": dest_airport_iata or f"{destination} Airport",
                            "date": self._normalize_date(end_date),
                            "passengers": guests
                        }
                        # 🧠 Store route planning context
                        if route_plan:
                            transfer_dep.requirements["_route_plan"] = {
                                "origin_airport": dest_airport_iata,
                                "hotel_location": hotel_destination
                            }
                        if budget:
                            transfer_dep.requirements["max_price"] = budget
                        session.trip_plan.travel.ground_transport.append(transfer_dep)
                else:
                    logger.info("🧠 Skipping airport transfers - no flights in itinerary")
                    
            elif travel_mode == TravelMode.CAR_ONLY:
                # Car Rental or Drive
                car_seg = Segment()
                car_seg.requirements = {
                    "origin": origin,
                    "destination": destination,
                    "date": self._normalize_date(start_date),
                    "passengers": guests
                }
                if budget:
                    car_seg.requirements["max_price"] = budget
                session.trip_plan.travel.ground_transport.append(car_seg)

        # Try to convert City names to IATA for flights immediately
        all_flight_segs = session.trip_plan.travel.flights.all_segments
        if "flights" in focus and travel_mode in [TravelMode.FLIGHT_ONLY, TravelMode.BOTH]:
            for seg in all_flight_segs:
                if "origin" in seg.requirements:
                    iata = await self._city_to_iata(seg.requirements["origin"])
                    if iata: seg.requirements["origin"] = iata
                if "destination" in seg.requirements:
                    iata = await self._city_to_iata(seg.requirements["destination"])
                    if iata: seg.requirements["destination"] = iata

        action_log.add_action(
            "CREATE_ITINERARY",
            payload,
            f"Created plan with focus {focus}: {len(all_flight_segs)} flights, {len(session.trip_plan.accommodation.segments)} hotels."
        )
        session.update_timestamp()
        # ✅ เริ่ม workflow: planning
        try:
            wf = get_workflow_state_service()
            await wf.set_workflow_state(session.session_id, WfStep.PLANNING)
        except Exception as wf_err:
            logger.warning(f"Failed to set workflow state: {wf_err}")

    async def _execute_update_req(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog
    ):
        """Execute UPDATE_REQ action with intelligent data extraction"""
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        updates = payload.get("updates", {})
        clear_existing = payload.get("clear_existing", False)
        
        if not slot_name:
            raise AgentException("UPDATE_REQ: Missing slot name")
        
        # ✅ Use SlotManager for stable segment access
        try:
            segment, segments = self.slot_manager.get_segment(
                session.trip_plan,
                slot_name,
                segment_index,
                create_if_missing=True  # Create if missing
            )
        except AgentException as e:
            logger.error(f"UPDATE_REQ failed: {e}")
            raise
        
        # ✅ Normalize and enhance updates using LLM if needed (with error handling)
        try:
            enhanced_updates = await self._enhance_requirements(slot_name, updates, segment.requirements)
            # ✅ Validate enhanced_updates
            if not isinstance(enhanced_updates, dict):
                logger.warning(f"_enhance_requirements returned non-dict: {type(enhanced_updates)}, using original updates")
                enhanced_updates = updates if isinstance(updates, dict) else {}
        except Exception as e:
            logger.warning(f"Error enhancing requirements: {e}, using original updates")
            enhanced_updates = updates if isinstance(updates, dict) else {}
        
        # Check if critical requirements are changing
        # If so, we MUST clear existing options to force a re-search
        critical_keys = [
            "origin", "destination", "location",
            "date", "departure_date", "check_in", "check_out",
            "direct_flight", "non_stop",  # บินตรง → ต้องค้นใหม่เฉพาะเที่ยวบินตรง
        ]
        
        should_clear = clear_existing
        if not should_clear:
            for key in enhanced_updates:
                if key in critical_keys and enhanced_updates[key] != segment.requirements.get(key):
                    should_clear = True
                    break
        
        if should_clear:
            logger.info(f"Clearing options for {slot_name}[{segment_index}] due to requirements change or force clear")
            segment.options_pool = []
            segment.selected_option = None
            segment.status = SegmentStatus.PENDING
        
        # Update requirements (merge with existing)
        prev_requirements = segment.requirements.copy()
        segment.requirements.update(enhanced_updates)
        try:
            # Destination change (flight) -> update accommodation.location and transfers destination airport/city
            if "destination" in enhanced_updates and "flights" in slot_name:
                new_dest = enhanced_updates.get("destination")
                old_dest = prev_requirements.get("destination")
                # Update accommodation segments if they were pointing to old destination (or empty)
                for acc in session.trip_plan.accommodation.segments:
                    loc = acc.requirements.get("location")
                    if not loc or (old_dest and loc == old_dest):
                        acc.requirements["location"] = new_dest
                        if should_clear:
                            acc.options_pool = []
                            acc.selected_option = None
                            acc.status = SegmentStatus.PENDING
                # Update ground transport segments that mention destination airport/hotel strings (best-effort)
                for gt in session.trip_plan.travel.ground_transport:
                    # If destination field equals old destination or contains it, swap
                    if "destination" in gt.requirements:
                        d = gt.requirements.get("destination")
                        if not d or (old_dest and d == old_dest):
                            gt.requirements["destination"] = new_dest
                    if "origin" in gt.requirements:
                        o = gt.requirements.get("origin")
                        if isinstance(o, str) and old_dest and old_dest in o:
                            gt.requirements["origin"] = o.replace(old_dest, str(new_dest))
                    if isinstance(gt.requirements.get("destination"), str) and old_dest and old_dest in gt.requirements["destination"]:
                        gt.requirements["destination"] = gt.requirements["destination"].replace(old_dest, str(new_dest))
                    if should_clear:
                        gt.options_pool = []
                        gt.selected_option = None
                        gt.status = SegmentStatus.PENDING

            # Date change in flights -> keep transfers date aligned if they match previous
            if "departure_date" in enhanced_updates and "flights" in slot_name:
                new_date = self._normalize_date(enhanced_updates.get("departure_date"))
                old_date = prev_requirements.get("departure_date") or prev_requirements.get("date")
                for gt in session.trip_plan.travel.ground_transport:
                    d = gt.requirements.get("date")
                    if not d or (old_date and d == old_date):
                        gt.requirements["date"] = new_date
                        if should_clear:
                            gt.options_pool = []
                            gt.selected_option = None
                            gt.status = SegmentStatus.PENDING

            # Accommodation date change -> keep hotel check-in/out normalized
            if ("check_in" in enhanced_updates) or ("check_out" in enhanced_updates):
                for acc in session.trip_plan.accommodation.segments:
                    if "check_in" in enhanced_updates:
                        acc.requirements["check_in"] = self._normalize_date(enhanced_updates["check_in"])
                    if "check_out" in enhanced_updates:
                        acc.requirements["check_out"] = self._normalize_date(enhanced_updates["check_out"])
                    if should_clear:
                        acc.options_pool = []
                        acc.selected_option = None
                        acc.status = SegmentStatus.PENDING
        except Exception as e:
            logger.warning(f"Workflow sync failed (non-fatal): {e}")
        
        # Convert city names to IATA codes for flights if needed
        if "flights" in slot_name:
            if "origin" in segment.requirements and not self._is_iata_code(segment.requirements["origin"]):
                try:
                    origin_iata = await self._city_to_iata(segment.requirements["origin"])
                    if origin_iata:
                        segment.requirements["origin"] = origin_iata
                except Exception as e:
                    logger.warning(f"Could not convert origin to IATA: {e}")
            
            if "destination" in segment.requirements and not self._is_iata_code(segment.requirements["destination"]):
                try:
                    dest_iata = await self._city_to_iata(segment.requirements["destination"])
                    if dest_iata:
                        segment.requirements["destination"] = dest_iata
                except Exception as e:
                    logger.warning(f"Could not convert destination to IATA: {e}")
        
        # Normalize date formats
        if "date" in segment.requirements:
            segment.requirements["departure_date"] = segment.requirements.pop("date")
        if "departure_date" in segment.requirements:
            segment.requirements["departure_date"] = self._normalize_date(segment.requirements["departure_date"])
        
        # Update status if needed
        if segment.needs_search():
            segment.status = SegmentStatus.PENDING  # Will trigger search in next iteration
        
        action_log.add_action(
            "UPDATE_REQ",
            payload,
            f"Updated {slot_name}[{segment_index}] requirements: {list(enhanced_updates.keys())}"
        )
        session.update_timestamp()
    
    async def _enhance_requirements(self, slot_name: str, updates: Dict[str, Any], existing: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance requirements using LLM for better extraction
        
        Args:
            slot_name: Slot name (flights_outbound, accommodation, etc.)
            updates: New updates from user
            existing: Existing requirements
            
        Returns:
            Enhanced updates dict
        """
        # ✅ Validate inputs
        if not isinstance(updates, dict):
            logger.warning(f"_enhance_requirements: updates is not dict ({type(updates)}), returning empty dict")
            return {}
        if not isinstance(existing, dict):
            logger.warning(f"_enhance_requirements: existing is not dict ({type(existing)}), using empty dict")
            existing = {}
        
        # For now, return updates as-is, but this can be enhanced with LLM extraction
        # if the updates are incomplete or ambiguous
        # ✅ Filter out None values to avoid overwriting with None
        filtered_updates = {k: v for k, v in updates.items() if v is not None}
        return filtered_updates
    
    def _is_iata_code(self, code: str) -> bool:
        """Check if string is likely an IATA code (3 uppercase letters)"""
        return isinstance(code, str) and len(code) == 3 and code.isupper() and code.isalpha()
    
    async def _city_to_iata(self, city_name: str) -> Optional[str]:
        """Convert city name to IATA code using TravelOrchestrator"""
        # ✅ If already an IATA code, return it directly
        if self._is_iata_code(city_name):
            logger.debug(f"'{city_name}' is already an IATA code, returning as-is")
            return city_name
        
        try:
            # Use orchestrator's geocoding and IATA finding
            loc_info = await self.orchestrator.get_coordinates(city_name)
            iata = await self.orchestrator.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            return iata
        except Exception as e:
            logger.warning(f"Failed to convert {city_name} to IATA: {e}")
            return None
    
    def _detect_destination_type(self, destination: str) -> str:
        """
        🧠 ENHANCED: Detect destination type for intelligent planning
        
        Returns:
            "beach", "city", "cultural", "mountain", or "unknown"
        """
        if not destination:
            return "unknown"
        
        destination_lower = str(destination).lower()
        
        # Beach destinations
        beach_keywords = ["phuket", "samui", "krabi", "pattaya", "koh", "island", "beach", "resort", "coast", "seaside", "ocean", "sea"]
        if any(keyword in destination_lower for keyword in beach_keywords):
            return "beach"
        
        # City destinations
        city_keywords = ["bangkok", "tokyo", "seoul", "singapore", "hong kong", "taipei", "kuala lumpur", "jakarta", "manila", "city", "downtown", "urban"]
        if any(keyword in destination_lower for keyword in city_keywords):
            return "city"
        
        # Cultural destinations
        cultural_keywords = ["chiang mai", "chiang rai", "kyoto", "nara", "bali", "ubud", "temple", "ancient", "heritage", "historical", "cultural"]
        if any(keyword in destination_lower for keyword in cultural_keywords):
            return "cultural"
        
        # Mountain destinations
        mountain_keywords = ["mountain", "hill", "peak", "summit", "alpine", "ski", "snow"]
        if any(keyword in destination_lower for keyword in mountain_keywords):
            return "mountain"
        
        return "unknown"
    
    def _suggest_optimal_nights(self, destination_type: str, current_nights: int) -> int:
        """
        🧠 ENHANCED: Suggest optimal number of nights based on destination type
        
        Args:
            destination_type: "beach", "city", "cultural", "mountain", or "unknown"
            current_nights: Current number of nights planned
            
        Returns:
            Suggested number of nights
        """
        # Default suggestions by destination type
        suggestions = {
            "beach": 3,      # Beach destinations: 2-4 nights ideal
            "city": 4,       # City destinations: 3-5 nights ideal
            "cultural": 3,   # Cultural destinations: 2-3 nights ideal
            "mountain": 2,   # Mountain destinations: 1-2 nights ideal
            "unknown": 3     # Default: 3 nights
        }
        
        suggested = suggestions.get(destination_type, 3)
        
        # If current_nights is too short (<= 1), suggest minimum
        if current_nights <= 1:
            return suggested
        
        # If current_nights is reasonable, keep it
        return current_nights
    
    def _normalize_create_itinerary_payload(self, payload: Dict[str, Any], user_input: str = "", main_booker_dob: Optional[str] = None) -> Dict[str, Any]:
        """
        Normalize and correct CREATE_ITINERARY payload for ~90% data accuracy.
        - Dates to YYYY-MM-DD; fix end_date < start_date
        - Guests/adults/children: ผู้ใหญ่ = อายุ > 20 ปี (ตามปีเกิด). ถ้าผู้จองหลักอายุไม่เกิน 20 ต้องมีผู้จองร่วมผู้ใหญ่ 1 คน → 1 ผู้ใหญ่ + 1 เด็ก = 2 คน
        - Trim origin/destination; non-empty strings
        - focus as list of strings
        """
        if not payload or not isinstance(payload, dict):
            return payload
        out = dict(payload)
        # Dates
        start = out.get("start_date")
        end = out.get("end_date")
        if start and isinstance(start, str):
            norm_start = self._normalize_date(start.strip())
            if norm_start:
                out["start_date"] = norm_start
        if end and isinstance(end, str):
            norm_end = self._normalize_date(end.strip())
            if norm_end:
                out["end_date"] = norm_end
        # Fix end_date < start_date
        ns, ne = out.get("start_date"), out.get("end_date")
        if ns and ne:
            try:
                ds = datetime.strptime(ns, "%Y-%m-%d")
                de = datetime.strptime(ne, "%Y-%m-%d")
                if de < ds:
                    out["end_date"] = (ds + timedelta(days=1)).strftime("%Y-%m-%d")
                    logger.info(f"✅ Auto-corrected end_date (was before start_date) -> {out['end_date']}")
            except ValueError:
                pass
        # Guests: default by age. ผู้ใหญ่ = อายุ > 20 ปี (ตามปีเกิด). ถ้าผู้จองหลักอายุไม่เกิน 20 → 1 ผู้ใหญ่ + 1 เด็ก = 2 คน
        g = out.get("guests")
        try:
            g = int(g) if g is not None else 1
        except (TypeError, ValueError):
            g = 1
        explicit_guests = False
        if user_input and isinstance(user_input, str):
            user_lower = user_input.strip().lower()
            explicit_guests = (
                "2 คน" in user_lower or "3 คน" in user_lower or "4 คน" in user_lower or "5 คน" in user_lower
                or "2 people" in user_lower or "3 people" in user_lower or "2 adults" in user_lower or "3 adults" in user_lower
                or "กับแฟน" in user_lower or "คู่" in user_lower or "ครอบครัว" in user_lower or "พาคุณแม่" in user_lower or "พาเพื่อน" in user_lower
                or "couple" in user_lower or "family" in user_lower or "สองคน" in user_lower or "สองท่าน" in user_lower
                or "2 ท่าน" in user_lower or "3 ท่าน" in user_lower or "for 2" in user_lower or "for 3" in user_lower
            )
            if not explicit_guests and g != 1:
                g = 1
        # ถ้าไม่ระบุจำนวนคน และมีปีเกิดผู้จองหลัก → อายุ > 20 = ผู้ใหญ่, อายุไม่เกิน 20 = ต้องมีผู้จองร่วมผู้ใหญ่ 1 คน (1 ผู้ใหญ่ + 1 เด็ก = 2 คน)
        if not explicit_guests and main_booker_dob:
            try:
                birth = datetime.strptime(main_booker_dob.strip()[:10], "%Y-%m-%d")
                today = datetime.now()
                age = today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))
                if age <= 20:
                    out["guests"] = 2
                    out["adults"] = 1
                    out["children"] = 1
                    logger.info("Main booker age <= 20; default 1 adult (co-booker) + 1 child (ผู้จองหลัก) = 2 people")
                else:
                    out["guests"] = 1
                    out["adults"] = 1
                    out["children"] = 0
                    logger.info("Main booker age > 20; default 1 adult (ผู้จองหลัก)")
            except (ValueError, TypeError):
                out["guests"] = max(1, min(9, g))
                if "adults" not in out:
                    out["adults"] = out["guests"]
                if "children" not in out:
                    out["children"] = 0
        else:
            out["guests"] = max(1, min(9, g))
            if "adults" not in out:
                out["adults"] = out["guests"]
            if "children" not in out:
                out["children"] = 0
        # Origin/destination: trim, ensure non-empty where required
        if "origin" in out and out["origin"] is not None:
            out["origin"] = str(out["origin"]).strip() or "Bangkok"
        if "destination" in out and out["destination"] is not None:
            out["destination"] = str(out["destination"]).strip()
        # Focus: list of strings
        f = out.get("focus")
        if f is not None and not isinstance(f, list):
            out["focus"] = ["flights", "hotels", "transfers"]
        elif isinstance(f, list):
            out["focus"] = [str(x).strip().lower() for x in f if x]
            if not out["focus"]:
                out["focus"] = ["flights", "hotels", "transfers"]
        # Plan through / waypoints: list of non-empty strings
        w = out.get("waypoints") or out.get("plan_through")
        if w is not None:
            if not isinstance(w, list):
                w = [w] if w else []
            out["waypoints"] = [str(x).strip() for x in w if x and str(x).strip()]
        else:
            out["waypoints"] = []
        return out
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize date string to YYYY-MM-DD format.
        Now uses SmartDateParser for enhanced natural language understanding.
        Supports: พรุ่งนี้, สงกรานต์, สัปดาห์หน้า, Thai months, Buddhist Era years, etc.
        """
        if not date_str or not isinstance(date_str, str):
            return date_str
        
        try:
            # Use the new SmartDateParser for enhanced intelligence
            parsed_date = SmartDateParser.parse(date_str)
            if parsed_date:
                logger.info(f"✅ SmartDateParser: '{date_str}' -> '{parsed_date}'")
                # ✅ Validate parsed date is not in the past (unless explicitly specified)
                try:
                    from datetime import datetime
                    parsed_dt = datetime.fromisoformat(parsed_date)
                    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    if parsed_dt < today:
                        logger.warning(f"⚠️ Parsed date '{parsed_date}' is in the past. Current date: {today.strftime('%Y-%m-%d')}")
                except Exception as e:
                    logger.warning(f"⚠️ Could not validate parsed date '{parsed_date}': {e}")
                return parsed_date
            
            # If SmartDateParser fails, return as-is
            logger.warning(f"⚠️ Could not parse date: '{date_str}' - returning as-is")
            return date_str
            
        except Exception as e:
            logger.error(f"Date parsing error for '{date_str}': {e}")
            return date_str
    
    def _create_cache_key(self, requirements: Dict[str, Any], slot_name: str) -> str:
        """
        สร้าง cache key จาก requirements เพื่อใช้ตรวจสอบว่า requirements ตรงกันหรือไม่
        
        Args:
            requirements: Segment requirements dict
            slot_name: Slot name (flights_outbound, accommodation, etc.)
            
        Returns:
            Cache key string (MD5 hash)
        """
        # สร้าง key จาก requirements ที่สำคัญ (ไม่รวม _cache_key)
        key_data = {
            "slot": slot_name,
            "origin": requirements.get("origin") or requirements.get("departure_airport"),
            "destination": requirements.get("destination") or requirements.get("arrival_airport"),
            "departure_date": requirements.get("departure_date") or requirements.get("date"),
            "return_date": requirements.get("return_date"),
            "location": requirements.get("location"),
            "check_in": requirements.get("check_in"),
            "check_out": requirements.get("check_out"),
            "adults": requirements.get("adults") or requirements.get("guests") or 1,
            "children": requirements.get("children", 0),
            "infants": requirements.get("infants", 0)
        }
        
        # สร้าง hash จาก key_data
        key_str = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        cache_key = hashlib.md5(key_str.encode('utf-8')).hexdigest()[:16]
        
        return cache_key
    
    async def _execute_call_search(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog
    ):
        """Execute CALL_SEARCH action using DataAggregator (Unified Data Layer).
        ราคา: API คืนราคารวมตามจำนวนคนที่ขอ (1 คน = ราคาสำหรับ 1 คน, N คน = ราคารวมสำหรับ N คน).
        """
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        
        if not slot_name:
            raise AgentException("CALL_SEARCH: Missing slot name")
        
        # Get segment
        # Handle the new flight structure
        if slot_name == "flights_outbound":
            segments = session.trip_plan.travel.flights.outbound
        elif slot_name == "flights_inbound":
            segments = session.trip_plan.travel.flights.inbound
        elif slot_name == "flights":
             if segment_index < len(session.trip_plan.travel.flights.outbound):
                 segments = session.trip_plan.travel.flights.outbound
             else:
                 segments = session.trip_plan.travel.flights.inbound
                 segment_index = segment_index - len(session.trip_plan.travel.flights.outbound)
        elif slot_name == "ground_transport" or slot_name == "transfers":
            segments = session.trip_plan.travel.ground_transport
        elif slot_name == "accommodation" or slot_name == "accommodations" or slot_name == "hotels":
            segments = session.trip_plan.accommodation.segments
        else:
             segments = getattr(session.trip_plan, slot_name, [])

        if segment_index >= len(segments):
            raise AgentException(f"CALL_SEARCH: Segment index {segment_index} out of range")
        
        segment = segments[segment_index]
        
        # ✅ ML validation ก่อนยิง search (ชั้นที่สอง): ตรวจสอบข้อมูลทริปอีกครั้งก่อนเรียก API
        try:
            ml_svc = get_ml_keyword_service()
            extracted = self._extract_trip_data_for_ml_validation(session.trip_plan)
            if extracted:
                val = ml_svc.validate_extracted_data(extracted)
                if val and val.get("valid") is False:
                    issues = val.get("issues", [])
                    raise AgentException(
                        "ML_VALIDATION_BLOCK_SEARCH: " + (", ".join(issues) if issues else "ข้อมูลทริปไม่ผ่านการตรวจสอบ")
                    )
        except AgentException:
            raise
        except Exception as e:
            logger.debug("ML validation in _execute_call_search skipped: %s", e)
        
        # Check if requirements are complete
        if not segment.needs_search():
            logger.info(f"CALL_SEARCH: Segment {slot_name}[{segment_index}] doesn't need search")
            return
        
        # Update status to searching
        segment.status = SegmentStatus.SEARCHING
        session.update_timestamp()

        # ✅ อัปเดต workflow step = searching (ก่อนยิง API)
        try:
            wf = get_workflow_state_service()
            await wf.set_workflow_state(session.session_id, WfStep.SEARCHING)
        except Exception as wf_err:
            logger.warning(f"Failed to set workflow state: {wf_err}")
        
        try:
            req = segment.requirements
            logger.info(f"Searching {slot_name} via Aggregator: {req}")
            
            # ✅ Cache Check: ถ้ามี options_pool อยู่แล้วและ requirements ตรงกัน ให้ใช้ raw data มาจัดใหม่
            if segment.options_pool and len(segment.options_pool) > 0:
                # สร้าง cache key จาก requirements
                cache_key = self._create_cache_key(req, slot_name)
                existing_key = segment.requirements.get("_cache_key")
                
                # ถ้า requirements ตรงกัน (cache key ตรงกัน) ให้ใช้ raw data ที่มีอยู่
                if existing_key == cache_key:
                    logger.info(f"✅ Using cached raw data for {slot_name}[{segment_index}] (cache_key: {cache_key})")
                    # Convert dict back to StandardizedItem objects for re-normalization
                    cached_items = []
                    for opt_dict in segment.options_pool:
                        try:
                            # Reconstruct StandardizedItem from dict
                            # Handle category enum conversion
                            if isinstance(opt_dict.get("category"), str):
                                opt_dict["category"] = ItemCategory(opt_dict["category"])
                            item = StandardizedItem(**opt_dict)
                            cached_items.append(item)
                        except Exception as e:
                            logger.warning(f"Failed to reconstruct StandardizedItem from cache: {e}, opt_dict keys: {list(opt_dict.keys()) if isinstance(opt_dict, dict) else 'not dict'}")
                            continue
                    
                    if cached_items:
                        # ✅ Re-normalize cached data (sort, filter, tag) โดยใช้ aggregator
                        # แต่ไม่ต้องเรียก API ใหม่ แค่ใช้ raw_data ที่มีอยู่มาจัดใหม่
                        standardized_results = cached_items
                        logger.info(f"✅ Reused {len(standardized_results)} cached options for {slot_name}[{segment_index}] (no API call needed)")
                    else:
                        # Fallback: clear cache and search fresh
                        logger.warning(f"Failed to reconstruct cached items, falling back to fresh search")
                        segment.options_pool = []
                        standardized_results = None
                else:
                    # Requirements เปลี่ยน → clear cache และ search ใหม่
                    logger.info(f"Requirements changed (old_key: {existing_key}, new_key: {cache_key}), clearing cache and searching fresh")
                    segment.options_pool = []
                    standardized_results = None
            else:
                standardized_results = None
            
            # ถ้ายังไม่มี results ให้ search ใหม่
            if standardized_results is None:
                # ✅ ตรวจสอบ cache ก่อน search
                try:
                    options_cache = get_options_cache()
                    cached_options = await options_cache.get_options(
                        session_id=session.session_id,
                        slot_name=slot_name,
                        segment_index=segment_index,
                        requirements=req
                    )
                    
                    if cached_options and len(cached_options) > 0:
                        logger.info(f"✅ Using cached options for {slot_name}[{segment_index}]: {len(cached_options)} options")
                        # Convert cached dicts back to StandardizedItem objects
                        cached_items = []
                        for opt_dict in cached_options:
                            try:
                                if isinstance(opt_dict.get("category"), str):
                                    opt_dict["category"] = ItemCategory(opt_dict["category"])
                                item = StandardizedItem(**opt_dict)
                                cached_items.append(item)
                            except Exception as e:
                                logger.warning(f"Failed to reconstruct StandardizedItem from cache: {e}")
                                continue
                        
                        if cached_items:
                            standardized_results = cached_items
                            # เก็บ cache key
                            cache_key = self._create_cache_key(req, slot_name)
                            segment.requirements["_cache_key"] = cache_key
                except Exception as cache_error:
                    logger.warning(f"Cache check failed, proceeding with fresh search: {cache_error}")
                
                # ถ้ายังไม่มี results จาก cache ให้ search ใหม่
                if standardized_results is None:
                    # ✅ STEP 4: Use Amadeus MCP Tools based on route planning
                    # Try MCP tools first, fallback to DataAggregator if needed
                    mcp_results = None
                    
                    if self.mcp_executor:
                        try:
                            if "flight" in slot_name:
                                # Use Amadeus MCP search_flights
                                logger.info(f"🔍 Using Amadeus MCP search_flights for {slot_name}[{segment_index}]")
                                # ✅ ส่ง non_stop เมื่อผู้ใช้ขอ "บินตรง" / direct / nonstop
                                non_stop = req.get("direct_flight") is True or req.get("non_stop") is True
                                mcp_result = await asyncio.wait_for(
                                    self.mcp_executor.execute_tool(
                                        "search_flights",
                                        {
                                            "origin": req.get("origin"),
                                            "destination": req.get("destination"),
                                            "departure_date": req.get("departure_date") or req.get("date"),
                                            "adults": req.get("adults") or req.get("guests", 1),
                                            "children": req.get("children", 0),
                                            "infants": req.get("infants", 0),
                                            "return_date": req.get("return_date") if "inbound" not in slot_name else None,
                                            "non_stop": non_stop,
                                        }
                                    ),
                                    timeout=20.0,
                                )
                                
                                if mcp_result.get("success") and mcp_result.get("flights"):
                                    mcp_results = mcp_result["flights"]
                                    logger.info(f"✅ Amadeus MCP returned {len(mcp_results)} flight options")
                            
                            elif "accommodation" in slot_name or "hotel" in slot_name:
                                # Use Amadeus MCP search_hotels
                                logger.info(f"🔍 Using Amadeus MCP search_hotels for {slot_name}[{segment_index}]")
                                location = req.get("location") or req.get("destination")
                                mcp_result = await asyncio.wait_for(
                                    self.mcp_executor.execute_tool(
                                        "search_hotels",
                                        {
                                            "location": location,
                                            "check_in": req.get("check_in"),
                                            "check_out": req.get("check_out"),
                                            "guests": req.get("guests") or req.get("adults", 1),
                                        }
                                    ),
                                    timeout=20.0,
                                )
                                
                                if mcp_result.get("success") and mcp_result.get("hotels"):
                                    mcp_results = mcp_result["hotels"]
                                    logger.info(f"✅ Amadeus MCP returned {len(mcp_results)} hotel options")
                            
                            elif "ground_transport" in slot_name or "transfer" in slot_name:
                                # Use Amadeus MCP search_transfers
                                logger.info(f"🔍 Using Amadeus MCP search_transfers for {slot_name}[{segment_index}]")
                                # Try to get coordinates from route plan or geocode
                                origin_coords = None
                                dest_coords = None
                                
                                # Check if we have route plan with coordinates
                                route_plan = req.get("_route_plan")
                                if route_plan:
                                    origin_coords = route_plan.get("origin", {}).get("coordinates")
                                    dest_coords = route_plan.get("destination", {}).get("coordinates")
                                
                                if origin_coords and dest_coords:
                                    mcp_result = await self.mcp_executor.execute_tool(
                                        "search_transfers_by_geo",
                                        {
                                            "start_lat": origin_coords.get("latitude"),
                                            "start_lng": origin_coords.get("longitude"),
                                            "end_lat": dest_coords.get("latitude"),
                                            "end_lng": dest_coords.get("longitude"),
                                            "start_time": req.get("date") or req.get("departure_date")
                                        }
                                    )
                                    
                                    if mcp_result.get("success") and mcp_result.get("transfers"):
                                        mcp_results = mcp_result["transfers"]
                                        logger.info(f"✅ Amadeus MCP returned {len(mcp_results)} transfer options")
                        except Exception as mcp_error:
                            logger.warning(f"Amadeus MCP tool failed (fallback to DataAggregator): {mcp_error}")
                    
                    # If MCP tools returned results, convert to StandardizedItem format
                    if mcp_results:
                        # ✅ เก็บ raw Amadeus ไว้ที่ Redis (สำหรับจัดช้อย/แก้ไข)
                        try:
                            options_cache = get_options_cache()
                            await options_cache.save_raw_amadeus(
                                session_id=session.session_id,
                                slot_name=slot_name,
                                segment_index=segment_index,
                                raw_response=mcp_results,
                            )
                        except Exception as raw_err:
                            logger.warning(f"Failed to save raw Amadeus to Redis: {raw_err}")
                        try:
                            # Convert MCP results to StandardizedItem via DataAggregator
                            # Map slot_name to aggregator category
                            if "flight" in slot_name: 
                                agg_category = "flight"
                            elif "accommodation" in slot_name or "hotel" in slot_name: 
                                agg_category = "hotel"
                            elif "ground_transport" in slot_name or "transfer" in slot_name: 
                                agg_category = "transfer"
                            else:
                                agg_category = slot_name.rstrip('s') # Fallback
                            
                            # Use DataAggregator to normalize MCP results
                            standardized_results = await aggregator.normalize_mcp_results(
                                request_type=agg_category,
                                raw_results=mcp_results,
                                requirements=req
                            )
                            logger.info(f"✅ Normalized {len(standardized_results)} options from Amadeus MCP")
                        except Exception as normalize_error:
                            logger.warning(f"Failed to normalize MCP results (fallback to direct search): {normalize_error}")
                            standardized_results = None
                    
                    # Fallback to DataAggregator direct search if MCP failed or no results
                    if not standardized_results:
                        # Map slot_name to aggregator category
                        if "flight" in slot_name: 
                            agg_category = "flight"
                        elif "accommodation" in slot_name or "hotel" in slot_name: 
                            agg_category = "hotel"
                        elif "ground_transport" in slot_name or "transfer" in slot_name: 
                            agg_category = "transfer"
                        else:
                            agg_category = slot_name.rstrip('s') # Fallback

                        # Use DataAggregator for smart, unified search
                        logger.info(f"🔍 Using DataAggregator fallback for {slot_name}[{segment_index}]")
                        standardized_results = await aggregator.search_and_normalize(
                            request_type=agg_category,
                            user_id=session.user_id,
                            mode="normal",
                            **req # Pass all requirements as kwargs
                        )
                    
                    # ✅ เก็บ cache key ไว้ใน requirements เพื่อใช้ตรวจสอบครั้งต่อไป
                    if standardized_results:
                        cache_key = self._create_cache_key(req, slot_name)
                        segment.requirements["_cache_key"] = cache_key
            
            # If no results, try alternative search or provide helpful message
            if not standardized_results:
                logger.warning(f"No results found for {slot_name} with requirements: {req}")
                segment.status = SegmentStatus.PENDING
                
                # Check if date is close (today/tomorrow) to add specific hint for Responder
                req_date = req.get("departure_date") or req.get("check_in") or req.get("date")
                date_hint = ""
                if req_date:
                    try:
                        d = datetime.fromisoformat(req_date)
                        now = datetime.now()
                        if (d - now).days < 1: # Today or past
                            date_hint = " (Date is today/past/close - suggest changing date if empty)"
                    except Exception:
                        pass

                action_log.add_action(
                    "CALL_SEARCH",
                    payload,
                    f"Searched {slot_name}[{segment_index}] but found 0 options.{date_hint}"
                )
                return
            
            # ✅ Validate ข้อมูลเที่ยวบิน: ถ้าขอบินตรง ให้กรองเฉพาะเที่ยวบินตรงจริง (ป้องกันแสดงต่อเครื่อง)
            if "flight" in slot_name and (req.get("direct_flight") is True or req.get("non_stop") is True):
                def _is_non_stop_option(opt):
                    raw = getattr(opt, "raw_data", None) or (opt if isinstance(opt, dict) else {}).get("raw_data") or (opt if isinstance(opt, dict) else {})
                    if not isinstance(raw, dict):
                        return False
                    for itin in raw.get("itineraries") or []:
                        if len(itin.get("segments") or []) > 1:
                            return False
                    return True
                before_count = len(standardized_results)
                standardized_results = [o for o in standardized_results if _is_non_stop_option(o)]
                if before_count > len(standardized_results):
                    logger.warning(f"✅ Validated direct flight: filtered out {before_count - len(standardized_results)} connecting options (kept {len(standardized_results)} non-stop)")
            
            # Update segment with standardized results (converted to dict for storage)
            # ✅ เก็บ raw data พร้อม cache key
            segment.options_pool = [item.model_dump() for item in standardized_results]
            if standardized_results and not segment.requirements.get("_cache_key"):
                # เก็บ cache key ถ้ายังไม่มี
                cache_key = self._create_cache_key(segment.requirements, slot_name)
                segment.requirements["_cache_key"] = cache_key
            
            # ✅ บันทึก options ลง cache service
            try:
                options_cache = get_options_cache()
                await options_cache.save_options(
                    session_id=session.session_id,
                    slot_name=slot_name,
                    segment_index=segment_index,
                    requirements=segment.requirements,
                    options=segment.options_pool,
                    ttl_hours=24
                )
                logger.info(f"✅ Cached {len(segment.options_pool)} options for {slot_name}[{segment_index}]")
            except Exception as cache_error:
                logger.warning(f"Failed to cache options: {cache_error}")
            
            segment.status = SegmentStatus.SELECTING
            
            self.slot_manager.ensure_segment_state(segment, slot_name)
            
            # ✅ อัปเดต workflow step = selecting (มีตัวเลือกให้เลือกใน PlanChoiceCard)
            try:
                wf = get_workflow_state_service()
                await wf.set_workflow_state(session.session_id, WfStep.SELECTING)
            except Exception as wf_err:
                logger.warning(f"Failed to set workflow state: {wf_err}")
            
            action_log.add_action(
                "CALL_SEARCH",
                payload,
                f"Searched {slot_name}[{segment_index}] via Aggregator, found {len(standardized_results)} options"
            )
            session.update_timestamp()
        
        except Exception as e:
            logger.error(f"Error in CALL_SEARCH via Aggregator: {e}", exc_info=True)
            segment.status = SegmentStatus.PENDING
            action_log.add_action(
                "CALL_SEARCH",
                payload,
                f"Search failed: {str(e)}",
                success=False
            )
    
    async def _execute_select_option(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog
    ):
        """Execute SELECT_OPTION action with stable slot management"""
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        option_index = payload.get("option_index", 0)
        
        if not slot_name:
            raise AgentException("SELECT_OPTION: Missing slot name")
        
        # ✅ Use SlotManager for stable segment access
        try:
            segment, segments = self.slot_manager.get_segment(
                session.trip_plan,
                slot_name,
                segment_index,
                create_if_missing=False
            )
        except AgentException as e:
            logger.error(f"SELECT_OPTION failed: {e}")
            raise
        
        self.slot_manager.ensure_segment_state(segment, slot_name)
        # Check if option exists
        if not segment.options_pool or len(segment.options_pool) == 0:
            raise AgentException(f"SELECT_OPTION: No options available for {slot_name}[{segment_index}]")
        
        if option_index < 0 or option_index >= len(segment.options_pool):
            raise AgentException(
                f"SELECT_OPTION: Option index {option_index} out of range "
                f"(has {len(segment.options_pool)} options)"
            )
        
        self.slot_manager.set_segment_selected(segment, slot_name, option_index)
        # Log selection details
        selected_option = segment.selected_option
        option_summary = {
            "index": option_index,
            "price": selected_option.get("price_amount") or selected_option.get("price_total") if isinstance(selected_option, dict) else None,
            "name": selected_option.get("display_name") or selected_option.get("name") if isinstance(selected_option, dict) else None
        }
        
        # ✅ บันทึก selected option ลง cache service
        try:
            options_cache = get_options_cache()
            await options_cache.save_selected_option(
                session_id=session.session_id,
                slot_name=slot_name,
                segment_index=segment_index,
                requirements=segment.requirements,
                selected_option=selected_option
            )
            logger.info(f"✅ Cached selected option for {slot_name}[{segment_index}]")
        except Exception as cache_error:
            logger.warning(f"Failed to cache selected option: {cache_error}")
        
        # 🧠 RL: Record reward for user selecting option (only if RL is enabled)
        if getattr(self, 'reinforcement_learning_enabled', True):
            try:
                selected_opt = None
                if segment.options_pool and option_index < len(segment.options_pool):
                    raw = segment.options_pool[option_index]
                    selected_opt = raw.model_dump() if hasattr(raw, 'model_dump') else raw
                rl_svc = get_rl_service()
                await rl_svc.record_reward(
                    user_id=session.user_id,
                    action_type="select_option",
                    slot_name=slot_name,
                    option=selected_opt,
                    context={"session_id": session.session_id},
                )
                logger.info(f"🧠 RL: Recorded reward for user selecting {slot_name}[{option_index}]")
            except Exception as rl_error:
                logger.warning(f"Failed to record RL reward: {rl_error}")
        else:
            logger.debug(f"🧠 RL: Skipped reward recording (reinforcementLearning disabled by user)")
        
        action_log.add_action(
            "SELECT_OPTION",
            {**payload, "option_summary": option_summary},
            f"Selected option {option_index} for {slot_name}[{segment_index}]: {option_summary.get('name', 'N/A')}"
        )
        
        # ✅ FIX: After selecting transport, trigger search for accommodation if needed
        # Check if this is a transport selection (ground_transport, transport, or transfer)
        is_transport_selection = slot_name in ["ground_transport", "transport", "transfer"]
        
        logger.debug(f"SELECT_OPTION: slot={slot_name} is_transport={is_transport_selection} status={segment.status}")

        if is_transport_selection and segment.status == SegmentStatus.CONFIRMED:
            # Check if accommodation segments need search
            for acc_idx, acc_seg in enumerate(session.trip_plan.accommodation.segments):
                if acc_seg.status in [SegmentStatus.PENDING, SegmentStatus.SEARCHING] and acc_seg.needs_search():
                    # Trigger search for accommodation
                    action_log.add_action(
                        "CALL_SEARCH",
                        {"slot": "accommodation", "segment_index": acc_idx},
                        f"Auto-triggered search for accommodation after transport selection"
                    )
                    logger.info(f"Transport selected - auto-triggering search for accommodation[{acc_idx}]")

                    # Execute search immediately
                    try:
                        await self._execute_call_search(
                            session,
                            {"slot": "accommodation", "segment_index": acc_idx},
                            action_log
                        )
                        logger.debug(f"Accommodation search completed: idx={acc_idx} options={len(acc_seg.options_pool) if acc_seg.options_pool else 0}")
                    except Exception as e:
                        logger.error(f"Error auto-triggering accommodation search: {e}", exc_info=True)
        
        session.update_timestamp()

    async def _run_agent_mode_auto_complete(
        self,
        session: UserSession,
        action_log: ActionLog,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    ) -> None:
        """
        รัน Agent Mode auto-select + auto-book
        ถ้า ENABLE_LANGGRAPH_AGENT_MODE=true ใช้ LangGraph, ไม่ก็เรียก _auto_select_and_book โดยตรง
        """
        from app.core.config import settings
        if getattr(settings, "enable_langgraph_agent_mode", False):
            try:
                from app.orchestration.agent_mode_graph import run_agent_mode_via_graph
                ok = await run_agent_mode_via_graph(self, session, action_log, status_callback)
                if ok:
                    return
                logger.debug("LangGraph agent mode returned False, falling back to direct call")
            except Exception as e:
                logger.warning(f"LangGraph agent mode failed: {e}, falling back to direct call")
        await self._auto_select_and_book(session, action_log, status_callback)
    
    async def _auto_select_and_book(
        self,
        session: UserSession,
        action_log: ActionLog,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None
    ):
        """
        ✅ Agent Mode: Ultra-Advanced Auto-Select and Auto-Book using LLM Intelligence
        
        Enhanced Logic:
        1. Use LLM to analyze all options and select the BEST one based on:
           - User preferences from memory
           - Price/value ratio
           - Reviews and ratings
           - Convenience (duration, stops, location)
        2. Fill missing passenger details intelligently
        3. Auto-book with confidence
        4. Handle errors gracefully with retry
        
        ✅ CRUD STABILITY IMPROVEMENTS:
        - Prevent duplicate bookings with atomic checks
        - Validate all selections before booking
        - Retry logic for transient failures
        - State consistency verification
        - Comprehensive error handling
        """
        try:
            # ✅ CRUD STABILITY: Check if already processing (prevent concurrent execution)
            if getattr(session, '_auto_select_in_progress', False):
                logger.warning("Agent Mode: Auto-select already in progress, skipping duplicate call")
                return
            setattr(session, '_auto_select_in_progress', True)
            # ✅ Use SlotManager to get all segments with stable access
            all_segments_managed = self.slot_manager.get_all_segments(session.trip_plan)
            
            # Filter to only segments with options that need selection
            segments_to_select = [
                (slot_name, segment, idx)
                for slot_name, segment, idx in all_segments_managed
                if segment.options_pool and len(segment.options_pool) > 0 and not segment.selected_option
            ]
            
            logger.info(f"Agent Mode: Auto-select check - found {len(segments_to_select)} segments with options that need selection")
            for slot_name, segment, idx in segments_to_select:
                logger.info(f"Agent Mode: Segment needs selection - {slot_name}[{idx}]: {len(segment.options_pool)} options, selected: {segment.selected_option is not None}")
            
            if not segments_to_select:
                logger.info("Agent Mode: No segments with options to auto-select - segments may already be selected, continuing to booking check")
                # ✅ Continue to booking check even if no segments to select (might already be selected)
            
            from app.engine.workflow_manager import SlotType
            priority_order = [
                SlotType.FLIGHTS_OUTBOUND.value,
                SlotType.FLIGHTS_INBOUND.value,
                SlotType.ACCOMMODATION.value,
                SlotType.GROUND_TRANSPORT.value
            ]
            
            # Sort segments by priority
            sorted_segments = sorted(
                segments_to_select,
                key=lambda x: priority_order.index(x[0]) if x[0] in priority_order else 999
            )
            
            # ✅ Use LLM to intelligently select best options for each segment
            logger.info(f"Agent Mode: Starting auto-select for {len(sorted_segments)} segments")
            for slot_name, segment, segment_index in sorted_segments:
                logger.info(f"Agent Mode: Processing {slot_name}[{segment_index}] - options: {len(segment.options_pool)}, selected: {segment.selected_option is not None}")
                num_options = len(segment.options_pool) if segment.options_pool else 0
                
                # ✅ แสดงรายละเอียด: พบ options กี่ตัว
                slot_display = {
                    SlotType.FLIGHTS_OUTBOUND.value: "เที่ยวบินขาไป",
                    SlotType.FLIGHTS_INBOUND.value: "เที่ยวบินขากลับ",
                    SlotType.ACCOMMODATION.value: "ที่พัก",
                    SlotType.GROUND_TRANSPORT.value: "การเดินทาง"
                }.get(slot_name, slot_name)
                
                if status_callback and num_options > 0:
                    await status_callback("analyzing", f"📊 พบ {num_options} options สำหรับ{slot_display} - กำลังวิเคราะห์ทั้งหมด...", f"agent_analyze_{slot_name}_start")
                
                # Get user preferences from memory
                user_memories = await self.memory.recall(session.user_id)
                memory_summary = self.memory.format_memories_for_prompt(user_memories)

                if status_callback and num_options > 0:
                    await status_callback("analyzing", f"🤖 Agent กำลังวิเคราะห์ตัวเลือกที่ดีที่สุดสำหรับ{slot_display}...", f"agent_analyze_{slot_name}")

                # 🧠 RL: Get per-user Q-scores and re-rank options before LLM selection
                rl_context = ""
                raw_options = [opt.model_dump() if hasattr(opt, 'model_dump') else opt for opt in segment.options_pool]
                if getattr(self, 'reinforcement_learning_enabled', True):
                    try:
                        rl_svc = get_rl_service()
                        # 1. Get numeric Q-scores for each option (List[float], index-aligned)
                        rl_scores: list = await rl_svc.get_option_scores(session.user_id, slot_name, raw_options)
                        # 2. Combine: final_score = weighted_score (0–1) + rl_bonus (scaled to 0–0.2)
                        #    RL bonus: map Q-value range [-1, +1] → [0, 0.2]
                        for i, opt in enumerate(raw_options):
                            ws = float(opt.get("weighted_score", 0.0))
                            q = float(rl_scores[i]) if i < len(rl_scores) else 0.0
                            rl_bonus = (q + 1.0) / 2.0 * 0.20  # normalize Q [-1,1] → [0, 0.2]
                            opt["_final_score"] = round(ws + rl_bonus, 4)
                        # 3. Sort by final_score descending so LLM sees best options first
                        raw_options.sort(key=lambda x: -x.get("_final_score", 0.0))
                        # 4. Build text context for LLM reasoning
                        rl_context = await rl_svc.build_rl_context(session.user_id, slot_name, raw_options)
                    except Exception as rl_ctx_err:
                        logger.debug(f"RL context build failed (non-critical): {rl_ctx_err}")

                # Build LLM prompt for smart selection
                options_json = json.dumps(raw_options, ensure_ascii=False, indent=2)

                selection_prompt = f"""You are an expert travel advisor. Analyze these options and select the BEST one.

=== USER PREFERENCES ===
{memory_summary or "No specific preferences recorded"}
{rl_context}
=== REQUIREMENTS ===
{json.dumps(segment.requirements, ensure_ascii=False)}

=== AVAILABLE OPTIONS ===
{options_json}

=== SELECTION CRITERIA ===
1. **RL History**: HIGHEST priority — boost options the user historically preferred, avoid rejected ones
2. **Value**: Best price/quality ratio
3. **Convenience**: Shortest duration, fewest stops, best locations
4. **Reviews**: Higher ratings preferred
5. **Recommended**: Prefer options tagged as recommended

Output JSON with your analysis and selection:
{{
  "analysis": "Brief reasoning for the selection",
  "selected_index": 0,
  "confidence": 0.95,
  "reasoning": "Why this is the best choice"
}}"""

                try:
                    # ✅ Use Production LLM Service - Intelligence Brain
                    if self.production_llm:
                        selection_data = await self.production_llm.intelligence_generate(
                            prompt=selection_prompt,
                            system_prompt="You are an expert at selecting the best travel options. Always output valid JSON.",
                            complexity="complex"  # Complex analysis needed
                        )
                    else:
                        # Fallback to old LLM service
                        selection_data = await self.llm.generate_json(
                            prompt=selection_prompt,
                            system_prompt="You are an expert at selecting the best travel options. Always output valid JSON.",
                            temperature=0.3,
                            auto_select_model=True,
                            context="agent_selector"
                        )
                    
                    best_option_index = selection_data.get("selected_index", 0)
                    reasoning = selection_data.get("reasoning", "Auto-selected by AI")
                    confidence = selection_data.get("confidence", 0.9)
                    
                    logger.info(f"Agent Mode: LLM selected option {best_option_index} for {slot_name} (confidence: {confidence})")
                    logger.info(f"Reasoning: {reasoning}")
                    
                except Exception as e:
                    # Fallback: Use simple heuristic
                    logger.warning(f"LLM selection failed, using fallback: {e}")
                    best_option_index = 0
                    for idx, option in enumerate(segment.options_pool):
                        if option.get("recommended") or option.get("tags", []).count("แนะนำ") > 0:
                            best_option_index = idx
                            break
                    reasoning = "Fallback: Selected recommended option"
                    confidence = 0.85
                
                # ✅ แสดงรายละเอียด: กำลังเลือก option ที่ดีที่สุด
                if status_callback and num_options > 0:
                    selected_option = segment.options_pool[best_option_index] if best_option_index < len(segment.options_pool) else None
                    option_info = ""
                    if selected_option:
                        # แสดงรายละเอียด option ที่เลือก
                        if slot_name in [SlotType.FLIGHTS_OUTBOUND.value, SlotType.FLIGHTS_INBOUND.value]:
                            flight_num = selected_option.get("flight_number") or selected_option.get("display_name", "").split()[0] if selected_option.get("display_name") else ""
                            price = selected_option.get("price_amount") or selected_option.get("price_total") or selected_option.get("price", 0)
                            option_info = f": {flight_num} (ราคา {int(price):,} บาท)"
                        elif slot_name == SlotType.ACCOMMODATION.value:
                            hotel_name = selected_option.get("display_name") or selected_option.get("name", "โรงแรม")
                            price = selected_option.get("price_amount") or selected_option.get("price_total") or selected_option.get("price", 0)
                            nights = segment.requirements.get("nights") or 1
                            total_price = float(price) * nights if isinstance(price, (int, float)) else float(price)
                            option_info = f": {hotel_name} ({int(total_price):,} บาทสำหรับ {nights} คืน)"
                    
                    await status_callback("selecting", f"🎯 กำลังเลือก{slot_display}ที่ดีที่สุด{option_info}...", f"agent_select_{slot_name}_analyzing")
                
                # ✅ Use SlotManager to set selection (validates state)
                if status_callback and num_options > 0:
                    selected_option_detail = segment.options_pool[best_option_index] if best_option_index < len(segment.options_pool) else None
                    selection_detail = ""
                    if selected_option_detail:
                        if slot_name in [SlotType.FLIGHTS_OUTBOUND.value, SlotType.FLIGHTS_INBOUND.value]:
                            flight_num = selected_option_detail.get("flight_number") or selected_option_detail.get("display_name", "").split()[0] if selected_option_detail.get("display_name") else ""
                            price = selected_option_detail.get("price_amount") or selected_option_detail.get("price_total") or selected_option_detail.get("price", 0)
                            selection_detail = f": {flight_num} (ราคา {int(price):,} บาท)"
                        elif slot_name == SlotType.ACCOMMODATION.value:
                            hotel_name = selected_option_detail.get("display_name") or selected_option_detail.get("name", "โรงแรม")
                            price = selected_option_detail.get("price_amount") or selected_option_detail.get("price_total") or selected_option_detail.get("price", 0)
                            nights = segment.requirements.get("nights") or 1
                            total_price = float(price) * nights if isinstance(price, (int, float)) else float(price)
                            selection_detail = f": {hotel_name} (ราคา {int(total_price):,} บาทสำหรับ {nights} คืน)"
                    
                    await status_callback("selecting", f"✅ เลือก{slot_display}แล้ว{selection_detail} (AI มั่นใจ {int(confidence*100)}%)", f"agent_select_{slot_name}")
                
                try:
                    logger.info(f"Agent Mode: Setting selection for {slot_name}[{segment_index}] - option_index: {best_option_index}, options_count: {len(segment.options_pool)}")
                    self.slot_manager.set_segment_selected(segment, slot_name, best_option_index)
                    
                    # ✅ Verify selection was set correctly
                    if segment.selected_option is None:
                        logger.error(f"Agent Mode: CRITICAL - selected_option is None after set_segment_selected! slot: {slot_name}, index: {best_option_index}")
                        raise Exception(f"Failed to set selected_option for {slot_name}[{segment_index}]")
                    
                    logger.info(f"Agent Mode: ✅ Successfully set selected_option for {slot_name}[{segment_index}] - status: {segment.status}")
                    
                    # 🧠 RL: Record reward for option selection (only if RL is enabled)
                    if getattr(self, 'reinforcement_learning_enabled', True):
                        try:
                            _raw_opt = None
                            if segment.options_pool and best_option_index < len(segment.options_pool):
                                _r = segment.options_pool[best_option_index]
                                _raw_opt = _r.model_dump() if hasattr(_r, 'model_dump') else _r
                            rl_svc = get_rl_service()
                            await rl_svc.record_reward(
                                user_id=session.user_id,
                                action_type="select_option",
                                slot_name=slot_name,
                                option=_raw_opt,
                                context={"session_id": session.session_id, "confidence": confidence},
                            )
                            logger.info(f"🧠 RL: Recorded reward for selecting {slot_name}[{best_option_index}]")
                        except Exception as rl_error:
                            logger.warning(f"Failed to record RL reward: {rl_error}")
                    
                    action_log.add_action(
                        "AGENT_SMART_SELECT",
                        {"slot": slot_name, "index": best_option_index, "reasoning": reasoning, "confidence": confidence},
                        f"Agent Mode: Intelligently selected option {best_option_index} (confidence: {confidence:.2f})"
                    )
                    
                    # ✅ Validate segment state after selection
                    is_valid, issues = self.slot_manager.validate_segment(segment, slot_name)
                    if not is_valid:
                        logger.warning(f"Segment state issues after selection: {issues}")
                        self.slot_manager.ensure_segment_state(segment, slot_name)
                    
                    # ✅ Save session after each selection to ensure state is persisted
                    await self.storage.save_session(session)
                    logger.info(f"Agent Mode: ✅ Session saved after selection for {slot_name}[{segment_index}]")
                except Exception as e:
                    logger.error(f"Failed to set selection for {slot_name}[{segment_index}]: {e}", exc_info=True)
                    raise
            
            # ✅ Re-check segments after auto-select (they may have changed)
            all_flights = session.trip_plan.travel.flights.outbound + session.trip_plan.travel.flights.inbound
            all_accommodations = session.trip_plan.accommodation.segments
            
            # ✅ Agent Mode: Book immediately when options are selected (don't wait for CONFIRMED status)
            has_selected_flight = any(seg.selected_option is not None for seg in all_flights)
            has_selected_hotel = any(seg.selected_option is not None for seg in all_accommodations)
            
            # ✅ DEBUG: Log detailed state after auto-select
            logger.info(f"Agent Mode: After auto-select - flights: {len(all_flights)} (selected: {sum(1 for s in all_flights if s.selected_option is not None)}), hotels: {len(all_accommodations)} (selected: {sum(1 for s in all_accommodations if s.selected_option is not None)})")
            for i, seg in enumerate(all_flights):
                logger.debug(f"Agent Mode: Flight[{i}] after select - selected_option: {seg.selected_option is not None}, status: {seg.status}")
            for i, seg in enumerate(all_accommodations):
                logger.debug(f"Agent Mode: Hotel[{i}] after select - selected_option: {seg.selected_option is not None}, status: {seg.status}")
            
            # Also check confirmed status as fallback
            has_confirmed_flight = any(seg.status == SegmentStatus.CONFIRMED for seg in all_flights)
            has_confirmed_hotel = any(seg.status == SegmentStatus.CONFIRMED for seg in all_accommodations)
            
            logger.info(f"Agent Mode: Booking check - flights: {len(all_flights)} (selected: {sum(1 for s in all_flights if s.selected_option is not None)}, confirmed: {sum(1 for s in all_flights if s.status == SegmentStatus.CONFIRMED)}), hotels: {len(all_accommodations)} (selected: {sum(1 for s in all_accommodations if s.selected_option is not None)}, confirmed: {sum(1 for s in all_accommodations if s.status == SegmentStatus.CONFIRMED)})")
            
            # ✅ DEBUG: Log detailed segment info for troubleshooting
            for seg in all_flights:
                logger.debug(f"Agent Mode: Flight segment - has_options: {bool(seg.options_pool)}, has_selected: {seg.selected_option is not None}, status: {seg.status}")
            for seg in all_accommodations:
                logger.debug(f"Agent Mode: Hotel segment - has_options: {bool(seg.options_pool)}, has_selected: {seg.selected_option is not None}, status: {seg.status}")
            
            # ✅ Auto-book immediately if we have at least flight OR hotel with selected_option (Agent Mode books instantly)
            # ✅ Also allow booking if we have options_pool but no selected_option yet (will auto-select first)
            has_options_available = any(
                (seg.options_pool and len(seg.options_pool) > 0) 
                for seg in all_flights + all_accommodations
            )
            
            if has_selected_flight or has_selected_hotel or has_confirmed_flight or has_confirmed_hotel or has_options_available:
                logger.info(f"Agent Mode: Ready to auto-book! has_selected_flight={has_selected_flight}, has_selected_hotel={has_selected_hotel}, has_confirmed_flight={has_confirmed_flight}, has_confirmed_hotel={has_confirmed_hotel}, has_options_available={has_options_available}")
                
                # ✅ If we have options but no selected_option yet, auto-select first
                if has_options_available and not (has_selected_flight or has_selected_hotel):
                    logger.info("Agent Mode: Options available but not selected yet - will auto-select first before booking")
                    # Auto-select will happen in the loop above, so we continue to booking check
                
                # ✅ CRUD STABILITY: Check if booking already exists to prevent duplicates (atomic check)
                from app.core.config import settings
                booking_check_url = f"{getattr(settings, 'api_base_url', 'http://localhost:8000')}/api/booking/list"
                existing_booking = None
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        check_response = await client.get(
                            booking_check_url,
                            params={"trip_id": session.trip_id or session.session_id},
                            headers={"X-User-ID": session.user_id}
                        )
                        if check_response.is_success:
                            check_data = check_response.json()
                            if check_data.get("ok") and check_data.get("bookings"):
                                # ✅ CRUD STABILITY: Check for existing booking with multiple criteria
                                trip_id_match = session.trip_id or session.session_id
                                existing_booking = next(
                                    (b for b in check_data.get("bookings", []) 
                                     if (b.get("trip_id") == trip_id_match or 
                                         b.get("session_id") == session.session_id) 
                                     and b.get("status") in ["pending_payment", "confirmed", "paid"]),
                                    None
                                )
                                if existing_booking:
                                    booking_id = existing_booking.get('booking_id', 'unknown')
                                    logger.info(f"Agent Mode: ✅ Duplicate booking prevented - existing booking_id: {booking_id}, status: {existing_booking.get('status')}")
                except httpx.TimeoutException:
                    logger.warning("Agent Mode: Booking check timeout - proceeding with caution")
                except Exception as e:
                    logger.warning(f"Agent Mode: Could not check existing bookings: {e}, proceeding with booking")
                
                # ✅ Skip booking if already exists
                if existing_booking:
                    if status_callback:
                        await status_callback("booking", f"ℹ️ พบการจองที่มีอยู่แล้ว (ID: {existing_booking.get('booking_id')[:8]}...) - ข้ามการจองซ้ำ", "agent_auto_book_skipped")
                    logger.info(f"Agent Mode: Booking already exists, skipping duplicate")
                    action_log.add_action(
                        "AUTO_BOOK_SKIPPED",
                        {"existing_booking_id": existing_booking.get("booking_id")},
                        f"Agent Mode: Skipped duplicate booking (already exists: {existing_booking.get('booking_id')})"
                    )
                else:
                    if status_callback:
                        await status_callback("booking", "💳 กำลังคำนวณราคารวมของทริป...", "agent_auto_book_calculating")
                    
                    try:
                        # ✅ CRUD STABILITY: Calculate total price from segments with selected_option (with validation)
                        total_price = 0.0
                        currency = "THB"
                        price_details = []
                        
                        # ✅ CRUD STABILITY: Check if we have any selected options (comprehensive check)
                        segments_with_selection = [seg for seg in all_flights + all_accommodations if seg.selected_option is not None]
                        
                        if not segments_with_selection:
                            logger.warning("Agent Mode: No segments with selected_option found - cannot create booking without selections")
                            logger.warning(f"Agent Mode: Debug - all_flights: {len(all_flights)}, all_accommodations: {len(all_accommodations)}")
                            for i, seg in enumerate(all_flights):
                                logger.warning(f"Agent Mode: Flight[{i}] - has_options: {bool(seg.options_pool)}, has_selected: {seg.selected_option is not None}, status: {seg.status}")
                            for i, seg in enumerate(all_accommodations):
                                logger.warning(f"Agent Mode: Hotel[{i}] - has_options: {bool(seg.options_pool)}, has_selected: {seg.selected_option is not None}, status: {seg.status}")
                            
                            if status_callback:
                                await status_callback("booking", "⚠️ ไม่พบตัวเลือกที่เลือกไว้ - กำลังเลือกให้อัตโนมัติ...", "agent_auto_book_no_selection")
                            
                            # ✅ CRUD STABILITY: Retry auto-select if we have options but no selection
                            has_options_but_no_selection = any(
                                (seg.options_pool and len(seg.options_pool) > 0) 
                                for seg in all_flights + all_accommodations
                            )
                            
                            if has_options_but_no_selection:
                                logger.warning("Agent Mode: Options available but not selected - retrying auto-select")
                                segments_to_retry = [
                                    (slot_name, seg, idx)
                                    for slot_name, seg, idx in self.slot_manager.get_all_segments(session.trip_plan)
                                    if seg.options_pool and len(seg.options_pool) > 0 and not seg.selected_option
                                ]
                                # Guard against unbounded recursion: allow at most 1 retry
                                retry_count = getattr(session, "_auto_select_retry_count", 0)
                                if segments_to_retry and retry_count < 1:
                                    logger.info(f"Agent Mode: Retrying auto-select for {len(segments_to_retry)} segments (attempt {retry_count + 1}/1)")
                                    setattr(session, "_auto_select_in_progress", False)
                                    setattr(session, "_auto_select_retry_count", retry_count + 1)
                                    await self._run_agent_mode_auto_complete(session, action_log, status_callback)
                                    return
                                elif segments_to_retry:
                                    logger.error("Agent Mode: Auto-select retry limit reached (1). Giving up to prevent infinite recursion.")
                                else:
                                    logger.error("Agent Mode: CRITICAL - Options available but auto-select failed. Cannot proceed with booking.")
                                    return
                            else:
                                logger.error("Agent Mode: CRITICAL - No options and no selections. Cannot proceed with booking.")
                                return
                        
                        # ✅ CRUD STABILITY: Calculate price with validation and error handling
                        for seg in all_flights + all_accommodations:
                            # ✅ Book immediately if segment has selected_option (don't wait for CONFIRMED status)
                            if seg.selected_option:
                                option = seg.selected_option
                                
                                # ✅ CRUD STABILITY: Validate option structure
                                if not isinstance(option, dict):
                                    logger.warning(f"Agent Mode: Invalid option type for segment - expected dict, got {type(option)}")
                                    continue
                                
                                price = option.get("price_amount") or option.get("price_total") or option.get("price", 0)
                                
                                # ✅ CRUD STABILITY: Validate price is numeric and non-negative
                                try:
                                    price_float = float(price) if price else 0.0
                                    if price_float < 0:
                                        logger.warning(f"Agent Mode: Negative price detected: {price_float}, using 0")
                                        price_float = 0.0
                                    total_price += price_float
                                    
                                    # เพิ่มรายละเอียดราคา
                                    if seg in all_flights:
                                        flight_num = option.get("flight_number") or option.get("display_name", "").split()[0] if option.get("display_name") else "เที่ยวบิน"
                                        price_details.append(f"{flight_num}: {int(price_float):,} บาท")
                                    elif seg in all_accommodations:
                                        hotel_name = option.get("display_name") or option.get("name", "ที่พัก")
                                        # ✅ CRUD STABILITY: Calculate hotel price per night if needed
                                        nights = seg.requirements.get("nights") or 1
                                        hotel_total = price_float * nights if nights > 1 else price_float
                                        price_details.append(f"{hotel_name}: {int(hotel_total):,} บาท ({nights} คืน)")
                                except (ValueError, TypeError) as price_error:
                                    logger.warning(f"Agent Mode: Invalid price format: {price}, error: {price_error}")
                                    # Continue with 0 price for this segment
                                
                                if option.get("currency"):
                                    currency = option.get("currency")
                        
                        # ✅ CRUD STABILITY: Validate total_price before booking
                        if total_price < 0:
                            logger.error(f"Agent Mode: Invalid total price: {total_price} - cannot create booking with negative price")
                            raise Exception(f"Invalid total price: {total_price}")
                        
                        if total_price == 0:
                            logger.warning(f"Agent Mode: Total price is 0 - this might be an issue. Segments with selection: {len(segments_with_selection)}")
                            # Still proceed with booking even if price is 0 (might be free or price not set)
                            # But log warning for monitoring
                        
                        # ✅ แสดง Trip Summary ก่อน แล้วค่อยจอง: ตั้ง workflow = SUMMARY และส่ง event ให้ frontend แสดงการ์ด
                        try:
                            wf = get_workflow_state_service()
                            await wf.set_workflow_state(session.session_id, WfStep.SUMMARY)
                        except Exception as wf_err:
                            logger.warning(f"Agent Mode: set_workflow_state(SUMMARY) failed: {wf_err}")
                        if status_callback:
                            await status_callback("summary", "สรุปทริป", "agent_show_summary")
                        
                        # ✅ แสดงรายละเอียดราคารวม
                        if status_callback and price_details:
                            price_summary = " + ".join(price_details) + f" = {int(total_price):,} บาท"
                            await status_callback("booking", f"💰 ราคารวม: {price_summary}", "agent_auto_book_price")
                        
                        if status_callback:
                            await status_callback("booking", "🤖 Agent กำลังจองทริปทันที...", "agent_auto_book")
                        
                        # Create booking via HTTP request to booking API
                        _api_base = (
                            getattr(settings, "api_base_url", None)
                            or getattr(settings, "backend_url", None)
                            or "http://localhost:8000"
                        )
                        if "localhost" in _api_base and not getattr(settings, "api_base_url", None):
                            logger.warning(
                                "Agent Mode booking: api_base_url not configured in settings, "
                                "falling back to localhost:8000. Set API_BASE_URL in .env for production."
                            )
                        booking_url = f"{_api_base.rstrip('/')}/api/booking/create"
                        # ✅ Build travel_slots with proper structure
                        travel_slots = {}
                        
                        # Extract origin/destination from flight segments
                        if all_flights and all_flights[0].requirements:
                            req = all_flights[0].requirements
                            travel_slots["origin_city"] = req.get("origin") or req.get("origin_city") or ""
                            travel_slots["destination_city"] = req.get("destination") or req.get("destination_city") or ""
                            travel_slots["departure_date"] = req.get("departure_date") or req.get("start_date") or ""
                            travel_slots["adults"] = req.get("adults") or req.get("guests") or 1
                            travel_slots["children"] = req.get("children") or 0
                        
                        # Extract return date from inbound flight
                        inbound_flights = [s for s in all_flights if s in session.trip_plan.travel.flights.inbound]
                        if inbound_flights and inbound_flights[0].requirements:
                            req = inbound_flights[0].requirements
                            travel_slots["return_date"] = req.get("departure_date") or req.get("return_date") or ""
                        
                        # Extract check-in/check-out from hotel segments
                        if all_accommodations and all_accommodations[0].requirements:
                            req = all_accommodations[0].requirements
                            travel_slots["check_in"] = req.get("check_in") or req.get("check_in_date") or ""
                            travel_slots["check_out"] = req.get("check_out") or req.get("check_out_date") or ""
                            # Calculate nights
                            if travel_slots.get("check_in") and travel_slots.get("check_out"):
                                try:
                                    from datetime import datetime
                                    check_in = datetime.fromisoformat(travel_slots["check_in"].replace("Z", "+00:00"))
                                    check_out = datetime.fromisoformat(travel_slots["check_out"].replace("Z", "+00:00"))
                                    nights = (check_out - check_in).days
                                    travel_slots["nights"] = max(1, nights)
                                except Exception:
                                    travel_slots["nights"] = 1
                        
                        # Include segment data
                        travel_slots["flights"] = [s.model_dump() for s in all_flights if s.selected_option is not None]
                        travel_slots["accommodations"] = [s.model_dump() for s in all_accommodations if s.selected_option is not None]
                        travel_slots["ground_transport"] = [s.model_dump() for s in session.trip_plan.travel.ground_transport if s.selected_option is not None]
                        
                        booking_payload = {
                            "trip_id": session.trip_id or session.session_id,
                            "chat_id": session.chat_id,
                            "user_id": session.user_id,
                            "plan": session.trip_plan.model_dump(),
                            "travel_slots": travel_slots,
                            "total_price": total_price,
                            "currency": currency,
                            "mode": "agent",  # ✅ Mark as agent mode
                            "auto_booked": True  # ✅ Mark as auto-booked
                        }
                        
                        logger.info(f"Agent Mode: Sending booking request to {booking_url}")
                        logger.debug(f"Agent Mode: Booking payload - trip_id: {booking_payload.get('trip_id')}, user_id: {booking_payload.get('user_id')}, total_price: {total_price}")
                        
                        # ✅ CRUD STABILITY: Retry logic for booking API call
                        max_retries = 3
                        retry_delay = 1.0
                        booking_result = None
                        
                        for attempt in range(max_retries):
                            try:
                                # ✅ ส่ง X-User-ID header เพื่อให้ booking ถูกบันทึกด้วย user_id ที่ถูกต้อง
                                # (agent เรียก internal HTTP ไม่มี session cookie)
                                _booking_headers = {
                                    "Content-Type": "application/json",
                                    "X-User-ID": session.user_id,
                                }
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    response = await client.post(booking_url, json=booking_payload, headers=_booking_headers)
                                    logger.info(f"Agent Mode: Booking API response status: {response.status_code} (attempt {attempt + 1}/{max_retries})")
                                    
                                    if not response.is_success:
                                        error_text = await response.text()
                                        
                                        # ✅ CRUD STABILITY: Handle duplicate booking error (409 Conflict)
                                        if response.status_code == 409:
                                            logger.warning(f"Agent Mode: Duplicate booking detected (409 Conflict): {error_text[:200]}")
                                            # Extract existing booking_id if possible
                                            try:
                                                error_data = response.json()
                                                existing_id = error_data.get("detail", "").split("booking_id")[-1] if "booking_id" in str(error_data) else "unknown"
                                                logger.info(f"Agent Mode: Skipping duplicate booking - existing booking_id: {existing_id}")
                                                action_log.add_action(
                                                    "AUTO_BOOK_SKIPPED",
                                                    {"reason": "duplicate", "existing_booking_id": existing_id},
                                                    f"Agent Mode: Skipped duplicate booking (409 Conflict)"
                                                )
                                                if status_callback:
                                                    await status_callback("booking", f"ℹ️ พบการจองที่มีอยู่แล้ว - ข้ามการจองซ้ำ", "agent_auto_book_duplicate")
                                                return  # Exit successfully - duplicate is not an error
                                            except Exception:
                                                pass
                                        
                                        # ✅ CRUD STABILITY: Retry on 5xx errors (server errors)
                                        if response.status_code >= 500 and attempt < max_retries - 1:
                                            logger.warning(f"Agent Mode: Server error {response.status_code}, retrying in {retry_delay}s...")
                                            await asyncio.sleep(retry_delay)
                                            retry_delay *= 2  # Exponential backoff
                                            continue
                                        
                                        logger.error(f"Agent Mode: Booking API error - Status: {response.status_code}, Response: {error_text[:200]}")
                                        raise Exception(f"Booking API returned {response.status_code}: {error_text[:200]}")
                                    
                                    booking_result = response.json()
                                    logger.debug(f"Agent Mode: Booking API response: {booking_result}")
                                    break  # Success, exit retry loop
                                    
                            except httpx.TimeoutException:
                                if attempt < max_retries - 1:
                                    logger.warning(f"Agent Mode: Booking API timeout (30s), retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2
                                    continue
                                else:
                                    logger.error("Agent Mode: Booking API timeout after all retries")
                                    raise Exception("Booking API timeout - server may be slow")
                            except httpx.RequestError as e:
                                if attempt < max_retries - 1:
                                    logger.warning(f"Agent Mode: Booking API request error: {e}, retrying in {retry_delay}s... (attempt {attempt + 1}/{max_retries})")
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2
                                    continue
                                else:
                                    logger.error(f"Agent Mode: Booking API request error after all retries: {e}")
                                    raise Exception(f"Booking API request failed: {str(e)}")
                        
                        if not booking_result:
                            raise Exception("Booking API call failed after all retries")
                        
                        # ✅ CRUD STABILITY: Validate booking response
                        booking_id = booking_result.get("booking_id")
                        booking_status = booking_result.get("status", "pending_payment")  # ✅ Status is pending_payment (needs payment)
                        
                        if not booking_id:
                            logger.error(f"Agent Mode: Booking API returned no booking_id. Response: {booking_result}")
                            # ✅ CRUD STABILITY: Check if booking was created but ID not returned
                            if booking_result.get("ok") and booking_result.get("message"):
                                logger.warning(f"Agent Mode: Booking may have been created but ID not returned: {booking_result.get('message')}")
                            raise Exception("Booking API did not return booking_id")
                        
                        # ✅ CRUD STABILITY: Validate booking_id format
                        if not isinstance(booking_id, str) or len(booking_id) < 5:
                            logger.warning(f"Agent Mode: Suspicious booking_id format: {booking_id}")
                        
                        logger.info(f"Agent Mode: Auto-booked successfully (instant booking): {booking_id} (status: {booking_status})")
                        
                        # 🧠 RL: Record reward for completing booking (only if RL is enabled)
                        if getattr(self, 'reinforcement_learning_enabled', True):
                            try:
                                rl_svc = get_rl_service()
                                for seg in all_flights + all_accommodations:
                                    if seg.selected_option is None:
                                        continue
                                    _sn = None
                                    if seg in all_flights:
                                        if seg in session.trip_plan.travel.flights.outbound:
                                            _sn = "flights_outbound"
                                        elif seg in session.trip_plan.travel.flights.inbound:
                                            _sn = "flights_inbound"
                                    elif seg in all_accommodations:
                                        _sn = "accommodation"
                                    if _sn:
                                        _opt = seg.selected_option
                                        if hasattr(_opt, 'model_dump'):
                                            _opt = _opt.model_dump()
                                        await rl_svc.record_reward(
                                            user_id=session.user_id,
                                            action_type="complete_booking",
                                            slot_name=_sn,
                                            option=_opt,
                                            context={
                                                "session_id": session.session_id,
                                                "booking_id": booking_id,
                                                "total_price": total_price,
                                            },
                                        )
                                logger.info(f"🧠 RL: Recorded rewards for completing booking {booking_id}")
                            except Exception as rl_error:
                                logger.warning(f"Failed to record RL reward for booking: {rl_error}")

                        # ✅ แสดงผลการจองสำเร็จ
                        if status_callback:
                            status_text = "✅ จองสำเร็จแล้ว!" if booking_status == "confirmed" else "✅ สร้างการจองสำเร็จแล้ว (รอชำระเงิน)"
                            await status_callback("booking", f"{status_text} ราคารวม {int(total_price):,} บาท - Booking ID: {booking_id[:8]}...", "agent_auto_book_success")
                        
                        action_log.add_action(
                            "AUTO_BOOK",
                            {
                                "booking_id": booking_id,
                                "status": booking_status,
                                "total_price": total_price,
                                "currency": currency
                            },
                            f"Agent Mode: Auto-booked trip instantly (ID: {booking_id}, status: {booking_status}, total: {total_price} {currency})"
                        )
                        
                        # ✅ Flag for frontend: Agent Mode จองอัตโนมัติสำเร็จ
                        setattr(session, "_agent_auto_booked", True)
                        logger.info(f"Agent Mode: _agent_auto_booked set True (booking_id={booking_id})")
                        # ✅ CRUD STABILITY: Save session after booking to ensure state is persisted
                        try:
                            await self.storage.save_session(session)
                        except Exception as save_error:
                            logger.error(f"Agent Mode: Failed to save session after booking: {save_error}", exc_info=True)
                            # Don't fail the booking if session save fails - booking is already created
                    except Exception as e:
                        logger.error(f"Agent Mode: Failed to auto-book: {e}", exc_info=True)
                        action_log.add_action(
                            "AUTO_BOOK_ERROR",
                            {"error": str(e)},
                            "Agent Mode: Failed to auto-book",
                            success=False
                        )
                        # ✅ CRUD STABILITY: Re-raise to allow caller to handle
                        raise
            
        except Exception as e:
            logger.error(f"Agent Mode: Error in auto-select-and-book: {e}", exc_info=True)
            action_log.add_action(
                "AUTO_SELECT_ERROR",
                {"error": str(e)},
                "Agent Mode: Failed to auto-select options",
                success=False
            )
            # ✅ CRUD STABILITY: Don't re-raise - allow turn to continue with error logged
        finally:
            # ✅ CRUD STABILITY: Always reset flags in finally block
            setattr(session, '_auto_select_in_progress', False)
            setattr(session, '_auto_select_retry_count', 0)
    
    async def generate_response(
        self,
        session: UserSession,
        action_log: ActionLog,
        memory_context: str = "",
        user_profile_context: str = "",
        mode: str = "normal",  # ✅ Pass mode to responder
        user_input: str = ""  # ✅ ใช้วิเคราะห์ความยากสำหรับสลับ Flash/Pro
    ) -> str:
        """
        Phase 2: Generate response message in Thai with Proactive Intelligence.
        Enhanced with: validation results, budget advisories, contextual suggestions.
        
        Args:
            session: UserSession with current state
            action_log: Actions taken in Phase 1
            memory_context: Long-term memory about the user
            user_profile_context: User profile information (name, email, preferences)
            
        Returns:
            Response message in Thai with proactive suggestions
        """
        try:
            # 🧠 Intelligence Layer: Generate Proactive Suggestions
            suggestions = []
            
            # Extract trip details for context-aware recommendations
            destination = None
            nights = 0
            
            # Check if we have accommodation segments to infer destination and duration
            if session.trip_plan.accommodation.segments:
                acc_seg = session.trip_plan.accommodation.segments[0]
                req = acc_seg.requirements
                destination = req.get("location")
                check_in = req.get("check_in")
                check_out = req.get("check_out")
                
                if check_in and check_out:
                    try:
                        # 🧠 ROBUSTNESS: Ensure check_in/check_out are valid ISO strings before parsing
                        if isinstance(check_in, str) and len(check_in) >= 10 and isinstance(check_out, str) and len(check_out) >= 10:
                            d1 = datetime.fromisoformat(check_in[:10])
                            d2 = datetime.fromisoformat(check_out[:10])
                            nights = (d2 - d1).days
                    except Exception as e:
                        logger.warning(f"Failed to calculate nights for suggestion: {e}")
                        nights = 3 # Default fallback
            
            # Or infer from flights
            if not destination and session.trip_plan.travel.flights.outbound:
                flight_seg = session.trip_plan.travel.flights.outbound[0]
                destination = flight_seg.requirements.get("destination")
            
            # Generate suggestions if we have enough context
            if destination:
                try:
                    # ProactiveRecommendations is now in this file
                    suggestions = ProactiveRecommendations.suggest_based_on_trip(destination, nights or 3)
                    logger.info(f"Generated {len(suggestions)} proactive suggestions for {destination}")
                except Exception as e:
                    logger.warning(f"ProactiveRecommendations failed: {e}")
                    suggestions = []
            
            # 🧠 Intelligence Layer: Extract Intelligence Warnings from Action Log
            intelligence_warnings = []
            for action in action_log.actions:
                if action.action_type == "INTELLIGENCE_CHECK" and action.payload:
                    warnings = action.payload.get("warnings", [])
                    intelligence_warnings.extend(warnings)
            
            # Build enhanced prompt with intelligence context
            # Strip options_pool to keep context window manageable for Responder LLM
            _resp_state = _strip_options_pool_for_controller(session.trip_plan.model_dump())
            state_json = json.dumps(_resp_state, ensure_ascii=False, indent=2)
            action_log_json = json.dumps([a.model_dump() for a in action_log.actions], ensure_ascii=False, indent=2)
            
            intelligence_context = ""
            if intelligence_warnings:
                intelligence_context += "\n=== ⚠️ INTELLIGENCE WARNINGS ===\n"
                intelligence_context += "\n".join(intelligence_warnings)
                intelligence_context += "\n(แจ้งเตือนเหล่านี้ให้ผู้ใช้รู้อย่างนุ่มนวล)\n"
            
            if suggestions:
                intelligence_context += "\n=== 💡 PROACTIVE SUGGESTIONS ===\n"
                intelligence_context += "\n".join(suggestions)
                intelligence_context += "\n(แนะนำสิ่งเหล่านี้อย่างเป็นธรรมชาติในการตอบ)\n"
            
            # ✅ Check if Agent Mode is active (from mode parameter)
            is_agent_mode = (mode == "agent")
            
            # ✅ Check if Agent Mode actions were taken
            agent_mode_actions = [a for a in action_log.actions if a.action_type in ["AGENT_SMART_SELECT", "AUTO_BOOK"]]
            
            # ✅ Check if Agent Mode is active by checking if there are segments with options_pool but no selected_option
            # This means Agent should be auto-selecting
            has_options_pending_selection = False
            all_segments = (
                session.trip_plan.travel.flights.outbound +
                session.trip_plan.travel.flights.inbound +
                session.trip_plan.accommodation.segments +
                session.trip_plan.travel.ground_transport
            )
            for seg in all_segments:
                if seg.options_pool and len(seg.options_pool) > 0 and not seg.selected_option:
                    has_options_pending_selection = True
                    break
            
            agent_mode_context = ""
            
            # ✅ In Agent Mode, ALWAYS provide autonomous context (even if no actions yet)
            if is_agent_mode or agent_mode_actions or has_options_pending_selection:
                agent_mode_context = "\n=== 🤖 AGENT MODE (100% AUTONOMOUS) ===\n"
                agent_mode_context += "⚠️ CRITICAL: You are operating in FULLY AUTONOMOUS mode. The AI makes ALL decisions automatically.\n\n"
                agent_mode_context += "🚫 ABSOLUTE PROHIBITIONS (NEVER DO THESE):\n"
                agent_mode_context += "1. ❌ NEVER say 'กรุณาเลือก' or 'ต้องการให้เลือก' or 'เหลือเพียงให้คุณเลือก'\n"
                agent_mode_context += "2. ❌ NEVER say 'คุณต้องการให้จองเลยไหม' or 'ต้องการให้จองเลยไหมคะ'\n"
                agent_mode_context += "3. ❌ NEVER say 'บอกดิฉันได้เลย' or 'บอกดิฉันได้เลยค่ะ' (asking for user input)\n"
                agent_mode_context += "4. ❌ NEVER end with questions asking user to do something\n"
                agent_mode_context += "5. ❌ NEVER say 'ขั้นตอนถัดไป: ให้คุณเลือก...' - say 'กำลังเลือกให้อัตโนมัติ...' instead\n\n"
                agent_mode_context += "✅ WHAT TO SAY INSTEAD:\n"
                agent_mode_context += "1. ✅ If options exist but not selected: 'พบ X options - กำลังเลือกตัวเลือกที่ดีที่สุดให้อัตโนมัติ...'\n"
                agent_mode_context += "2. ✅ If selected_option exists: 'ได้เลือก [item] แล้ว' (already done, don't ask)\n"
                agent_mode_context += "3. ✅ If booking in progress: 'กำลังจองทริปให้อัตโนมัติ...'\n"
                agent_mode_context += "4. ✅ If booking done: '✅ จองเสร็จแล้วนะ ไปจ่ายตังด้วย!'\n"
                agent_mode_context += "5. ✅ Always focus on WHAT WAS DONE AUTONOMOUSLY, not what needs user action\n\n"
                
                if agent_mode_actions:
                    agent_mode_context += "Actions taken autonomously:\n"
                    for action in agent_mode_actions:
                        if action.action_type == "AGENT_SMART_SELECT":
                            slot_name = action.payload.get('slot', '')
                            slot_display = {
                                'flights_outbound': 'เที่ยวบินขาไป',
                                'flights_inbound': 'เที่ยวบินขากลับ',
                                'accommodation': 'ที่พัก',
                                'ground_transport': 'การเดินทาง'
                            }.get(slot_name, slot_name)
                            confidence = action.payload.get('confidence', 0.9)
                            reasoning = action.payload.get('reasoning', 'Best value')
                            agent_mode_context += f"- ✅ เลือก{slot_display}แล้ว (AI มั่นใจ {int(confidence*100)}%): {reasoning}\n"
                        elif action.action_type == "AUTO_BOOK":
                            booking_id = action.payload.get('booking_id')
                            booking_status = action.payload.get('status', 'pending_payment')
                            total_price = action.payload.get('total_price', 0)
                            agent_mode_context += f"- ✅ จองทริปสำเร็จแล้ว! Booking ID: {booking_id[:8]}... (ราคารวม: {int(total_price):,} บาท)\n"
                            agent_mode_context += f"  Status: {booking_status} - ต้องชำระเงินเพื่อยืนยันการจอง\n"
                
                if has_options_pending_selection:
                    agent_mode_context += "\n⚠️ IMPORTANT: There are options available but not yet selected.\n"
                    agent_mode_context += "Say: 'พบตัวเลือกแล้ว - กำลังเลือกตัวเลือกที่ดีที่สุดให้อัตโนมัติ...' (NOT 'กรุณาเลือก')\n"
                
                agent_mode_context += "\n(Explain what was done autonomously in a confident, reassuring way. NEVER ask questions.)\n"
            
            # ✅ Extract origin and destination from trip plan for explicit instruction
            origin_full = None
            destination_full = None
            try:
                if session.trip_plan.travel.flights.outbound:
                    origin_full = session.trip_plan.travel.flights.outbound[0].requirements.get("origin")
                    destination_full = session.trip_plan.travel.flights.outbound[0].requirements.get("destination")
                elif session.trip_plan.accommodation.segments:
                    destination_full = session.trip_plan.accommodation.segments[0].requirements.get("location")
            except Exception:
                pass
            
            city_names_context = ""
            if origin_full or destination_full:
                city_names_context = f"\n=== 🏙️ CITY NAMES (USE COMPLETE NAMES) ===\n"
                if origin_full:
                    city_names_context += f"Origin (ต้นทาง): {origin_full}\n"
                if destination_full:
                    city_names_context += f"Destination (ปลายทาง): {destination_full}\n"
                city_names_context += "⚠️ CRITICAL: When mentioning these cities in your response, ALWAYS use the COMPLETE name as shown above.\n"
                city_names_context += "✅ CORRECT: 'กรุงเทพฯ - ภูเก็ต' (complete)\n"
                city_names_context += "❌ WRONG: 'กรุงเทพฯ - ภู' (incomplete - NEVER do this)\n"
                city_names_context += "✅ CORRECT: 'กรุงเทพฯ - เชียงใหม่' (complete)\n"
                city_names_context += "❌ WRONG: 'กรุงเทพฯ - เชียง' (incomplete - NEVER do this)\n\n"
            
            prompt = f"""{user_profile_context if user_profile_context else ""}

=== USER LONG-TERM MEMORY ===
{memory_context}

=== CURRENT STATE ===
{state_json}

=== ACTIONS TAKEN ===
{action_log_json}
{intelligence_context}
{agent_mode_context}
{city_names_context}

=== INSTRUCTIONS ===
Generate a response message in Thai:
1. **CRITICAL: ALWAYS USE COMPLETE CITY NAMES** - Never truncate or abbreviate:
   - ✅ "กรุงเทพฯ - ภูเก็ต" (complete)
   - ❌ "กรุงเทพฯ - ภู" (incomplete - NEVER do this)
   - ✅ "กรุงเทพฯ - เชียงใหม่" (complete)
   - ❌ "กรุงเทพฯ - เชียง" (incomplete - NEVER do this)
   - When summarizing trip details, ALWAYS use FULL city names from the trip plan

2. Summarize what was done (from action_log)

3. If NORMAL MODE (mode='normal'):
   - ✅ If options_pool exists, say: "พบ X ตัวเลือก - กรุณาเลือกตัวเลือกที่ต้องการจากรายการด้านล่างค่ะ"
   - ✅ If user selects option, say: "ได้เลือก [item] แล้ว - สามารถแก้ไขได้หากต้องการ"
   - ✅ If all options selected, say: "พร้อมจองแล้ว - กรุณากดปุ่ม 'Confirm Booking' เพื่อดำเนินการจอง"
   - ✅ Always remind: "สามารถแก้ไขตัวเลือกได้ตลอดเวลาค่ะ"
   - ❌ NEVER say Agent did something - user selects manually

4. If AGENT MODE (mode='agent') was used:
   - ✅ Explain what AI did autonomously (selected, booked, etc.)
   - ✅ Say "ดิฉันได้เลือก/จองให้อัตโนมัติแล้วค่ะ" (I did it automatically)
   - ❌ NEVER ask "คุณต้องการให้เลือก..." or "กรุณาเลือก..."
   - ❌ NEVER say "เหลือเพียงให้คุณเลือก..." - say "กำลังเลือกให้อัตโนมัติ..." instead
   - ❌ NEVER end with questions - Agent Mode never asks

5. If AUTO_BOOK succeeded, celebrate and say "✅ จองเสร็จแล้วนะ ไปจ่ายตังด้วย! รายละเอียดอยู่ใน My Bookings"

6. If options_pool exists but no selected_option yet:
   - 📋 NORMAL MODE: Say "พบ X ตัวเลือก - กรุณาเลือกตัวเลือกที่ต้องการจากรายการด้านล่างค่ะ"
   - 🤖 AGENT MODE: Say "พบ X options - กำลังเลือกตัวเลือกที่ดีที่สุดให้อัตโนมัติ..."
   - ❌ DON'T say "กรุณาเลือก" in Agent Mode

7. If selected_option exists:
   - 📋 NORMAL MODE: Say "ได้เลือก [item] แล้ว - สามารถแก้ไขได้หากต้องการ"
   - 🤖 AGENT MODE: Say "ได้เลือก [item] แล้ว" (already done, don't ask)
   - ❌ DON'T ask for confirmation in Agent Mode

8. If there are INTELLIGENCE WARNINGS, mention them naturally and helpfully
9. If there are PROACTIVE SUGGESTIONS, weave 1-2 of them into the response naturally
10. If everything is complete, summarize the complete Trip Plan (ALWAYS use FULL city names)
11. Use USER MEMORY to personalize the response if relevant (e.g. if they like beach, mention it)
11. In Agent Mode: Focus on WHAT WAS DONE, not what needs user action
12. In Normal Mode: Guide user to select options and book manually

Tone: Professional, helpful, proactive, friendly, confident. In Agent Mode: AUTONOMOUS. In Normal Mode: GUIDING (help user select and book).
Respond in Thai text only (no JSON, no markdown)."""
            
            # ✅ CRITICAL: Initialize response_text to avoid UnboundLocalError
            response_text = None
            
            # ✅ Use Intent-Based LLM (Gemini) for tool calling when appropriate
            # Check if we should use intent-based LLM (for direct queries that might need tools)
            use_intent_llm = False
            if self.intent_llm and action_log.actions:
                # Use IntentBasedLLM if user is asking for search/query directly
                last_action = action_log.actions[-1] if action_log.actions else None
                user_intent_keywords = ['หาตั๋ว', 'หาที่พัก', 'search', 'find', 'flight', 'hotel', 'บิน', 'ตั๋ว', 'โรงแรม', 'ที่พัก']
                # Check if any action was CALL_SEARCH (meaning user wants to search)
                if last_action and last_action.action_type == "CALL_SEARCH":
                    use_intent_llm = True
                # Or if user input contains search keywords
                # Note: We'll get user_input from context - for now, use action log as indicator
            
            if use_intent_llm and self.intent_llm:
                logger.info("Using IntentBasedLLM for intent analysis and tool calling")
                try:
                    # Build conversation history for intent analysis
                    # Note: We'll need to pass user_input - for now use action_log context
                    intent_result = await self.intent_llm.analyze_intent_and_respond(
                        user_input=f"Based on actions: {action_log_json}",
                        system_prompt=self.responder_system_prompt,
                        max_tool_calls=3,
                        temperature=settings.responder_temperature
                    )
                    if intent_result.get('success') and intent_result.get('text'):
                        response_text = intent_result.get('text', '')
                        logger.info(f"IntentBasedLLM response: intent={intent_result.get('intent')}, tools_called={intent_result.get('tools_called')}")
                    else:
                        # Fallback to normal responder if intent LLM fails
                        use_intent_llm = False
                        logger.warning("IntentBasedLLM returned empty, falling back to normal responder")
                except Exception as e:
                    logger.warning(f"IntentBasedLLM failed: {e}, falling back to normal responder")
                    use_intent_llm = False
            
            if not use_intent_llm or response_text is None:
                # ✅ Use Production LLM Service - Responder Brain
                if self.production_llm:
                    # วิเคราะห์ความยากจากข้อความผู้ใช้ แล้วสลับ Flash/Pro
                    try:
                        task_complexity = ModelSelector.analyze_complexity(
                            user_input or "", context="responder", task_type=None
                        )
                        complexity = task_complexity.value
                        if agent_mode_actions and complexity == "simple":
                            complexity = "moderate"  # มี agent actions อย่างน้อย moderate
                        if agent_mode_actions and complexity == "moderate":
                            complexity = "complex"  # Agent Mode ใช้ Pro สำหรับตอบ
                    except Exception as e:
                        logger.debug(f"ModelSelector.analyze_complexity failed: {e}, using action-based complexity")
                        complexity = "complex" if agent_mode_actions else "simple"
                    start_time = asyncio.get_running_loop().time()
                    try:
                        logger.info(f"Calling production_llm.responder_generate: complexity={complexity}, prompt_length={len(prompt)}")
                        response_text = await self.production_llm.responder_generate(
                            prompt=prompt,
                            system_prompt=self.responder_system_prompt,
                            complexity=complexity
                        )
                        logger.info(f"Production LLM response generated: length={len(response_text) if response_text else 0}, is_none={response_text is None}, is_empty={not response_text.strip() if response_text else True}")
                        # ✅ ถ้า production คืนค่าว่าง ให้ลองใช้ basic LLM แทน (ถือว่าเป็น transient failure)
                        if response_text is not None and isinstance(response_text, str) and not response_text.strip():
                            logger.warning("Production LLM returned empty string, will try basic LLM")
                            response_text = None
                        
                        # 🆕 COST TRACKING: Track Responder LLM call
                        try:
                            end_time = asyncio.get_running_loop().time()
                            latency_ms = (end_time - start_time) * 1000
                            
                            # Estimate tokens
                            input_tokens = len(prompt) // 3
                            output_tokens = len(response_text) // 3 if response_text else 0
                            
                            # Track the call
                            self.cost_tracker.track_llm_call(
                                session_id=session.session_id,
                                user_id=session.user_id,
                                model=settings.gemini_flash_model,  # Use from .env
                                brain_type="responder",
                                input_tokens=input_tokens,
                                output_tokens=output_tokens,
                                mode=mode,
                                latency_ms=latency_ms,
                                success=True
                            )
                        except Exception as track_error:
                            logger.warning(f"Failed to track responder cost: {track_error}")
                    except Exception as e:
                        logger.error(f"Production LLM failed: {e}", exc_info=True)
                        response_text = None
                
                # Fallback to basic LLM when production failed, unavailable, or returned empty
                if response_text is None or (isinstance(response_text, str) and not response_text.strip()):
                    logger.info(f"Falling back to basic LLM service: production_llm={self.production_llm is not None}, llm={self.llm is not None}")
                    try:
                        response_text = await self.llm.generate_content(
                            prompt=prompt,
                            system_prompt=self.responder_system_prompt,
                            temperature=settings.responder_temperature,
                            max_tokens=2500,  # ✅ Increased from 2000 to 2500 to ensure complete city names are included
                            auto_select_model=True,
                            context="responder"
                        )
                        logger.info(f"Basic LLM response generated: length={len(response_text) if response_text else 0}, is_none={response_text is None}, is_empty={not response_text.strip() if response_text else True}")
                    except LLMException as llm_error:
                        logger.error(f"Basic LLM failed with LLMException: {llm_error}")
                        error_str = str(llm_error).lower()
                        # Detect quota errors from error message (LLMException has no is_quota_error attr)
                        _is_quota_error = any(x in error_str for x in ["429", "quota", "exceeded", "resource exhausted"])
                        if _is_quota_error:
                            retry_delay = getattr(llm_error, 'retry_delay', 10)
                            logger.warning(f"Quota exceeded, waiting {retry_delay} seconds before retry...")
                            await asyncio.sleep(min(retry_delay, 60))  # Cap at 60 seconds
                            # Retry once after waiting
                            try:
                                logger.info("Retrying after quota wait period...")
                                response_text = await self.llm.generate_content(
                                    prompt=prompt,
                                    system_prompt=self.responder_system_prompt,
                                    temperature=settings.responder_temperature,
                                    max_tokens=2500,  # ✅ Increased from 2000 to 2500 to ensure complete city names are included
                                    auto_select_model=True,
                                    context="responder"
                                )
                                logger.info(f"Basic LLM retry successful: length={len(response_text) if response_text else 0}")
                            except Exception as retry_error:
                                logger.error(f"Retry after quota wait also failed: {retry_error}")
                                response_text = (
                                    "ขออภัยค่ะ API quota หมดแล้วสำหรับวันนี้ (Free tier limit: 20 requests/day)\n\n"
                                    "กรุณา:\n"
                                    "1. รอจนกว่า quota จะ reset (ทุกวัน)\n"
                                    "2. หรือ upgrade Google Cloud plan เพื่อเพิ่ม quota\n\n"
                                    "หากต้องการใช้งานต่อทันที กรุณาติดต่อ support"
                                )
                        # Check if it's API key issue
                        elif "api" in str(llm_error).lower() and "key" in str(llm_error).lower():
                            response_text = (
                                "ขออภัยค่ะ ระบบไม่สามารถเชื่อมต่อกับ AI service ได้\n\n"
                                "กรุณาตรวจสอบ:\n"
                                "1. GEMINI_API_KEY ถูกตั้งค่าในไฟล์ .env แล้ว\n"
                                "2. API key ถูกต้องและยังใช้งานได้\n"
                                "3. API key มีสิทธิ์ที่เหมาะสม\n\n"
                                "หากยังไม่ได้ตั้งค่า API key กรุณาดูคำแนะนำในเอกสารประกอบ"
                            )
                        elif "permission" in error_str or "403" in error_str:
                            response_text = (
                                "ขออภัยค่ะ ระบบไม่สามารถเชื่อมต่อกับ AI service ได้\n\n"
                                "ปัญหาสิทธิ์การเข้าถึง API:\n"
                                "1. ตรวจสอบว่า API key มีสิทธิ์ที่เหมาะสม\n"
                                "2. ตรวจสอบว่า Billing เปิดใช้งานใน Google Cloud project\n"
                                "3. ตรวจสอบ API key restrictions"
                            )
                        else:
                            # Extract first line of error for user-friendly message
                            error_lines = str(llm_error).split('\n')
                            first_error = error_lines[0][:150] if error_lines else str(llm_error)[:150]
                            response_text = f"ขออภัยค่ะ เกิดข้อผิดพลาดในการสร้างคำตอบ: {first_error}"
                    except Exception as e:
                        logger.error(f"Basic LLM also failed: {e}", exc_info=True)
                        agent_monitor.log_activity(session.session_id, session.user_id, "error", "Responder fallback: basic_llm_exception", {"error": str(e)[:200]})
                        response_text = "ขออภัยค่ะ ระบบไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
            if not response_text or response_text.strip() == "":
                logger.warning(
                    "Responder LLM returned empty text, using fallback",
                    extra={"session_id": session.session_id, "fallback_reason": "responder_empty_after_llm"},
                )
                agent_monitor.log_activity(session.session_id, session.user_id, "warning", "Responder returned empty text")
                response_text = FALLBACK_RESPONSE_EMPTY
            
            # ✅ CRITICAL: Final check before returning
            if not response_text or not response_text.strip():
                logger.error(
                    "Response text still empty after fallback",
                    extra={"session_id": session.session_id, "fallback_reason": "final_empty"},
                )
                response_text = "ขออภัยค่ะ ระบบไม่สามารถสร้างคำตอบได้ กรุณาลองใหม่อีกครั้ง"
                
            logger.info(f"generate_response completed: session={session.session_id}, response_length={len(response_text)}")
            agent_monitor.log_activity(session.session_id, session.user_id, "response", "Final response generated", {"text_preview": response_text[:100]})
            return response_text
        
        except LLMException as e:
            logger.error(f"LLM error in responder: {e}", exc_info=True)
            # Safe fallback message
            return "ขออภัย ระบบกำลังใช้งานหนัก กรุณาลองใหม่อีกครั้งในสักครู่"
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "ขออภัย เกิดข้อผิดพลาดในการสร้างข้อความตอบกลับ กรุณาลองใหม่อีกครั้ง"


# =============================================================================
# Agent Intelligence Layer - Production-Grade Enhancements
# =============================================================================
# Makes the Travel Agent smarter with:
# - Smart date parsing (พรุ่งนี้, สงกรานต์, etc.)
# - Location intelligence (landmarks, cities)
# - Google Maps intelligence (nearby search, place details)
# - Budget advisor
# - Input validation & sanitization
# - Self-correction mechanisms
# - Proactive recommendations
# =============================================================================

import re
from dataclasses import dataclass, field

# Google Maps client (lazy loaded)
_gmaps_client = None

def get_gmaps_client():
    """Lazy load Google Maps client"""
    global _gmaps_client
    if _gmaps_client is None and settings.google_maps_api_key:
        import googlemaps
        _gmaps_client = googlemaps.Client(key=settings.google_maps_api_key)
    return _gmaps_client


# =============================================================================
# 1. Smart Date Parser - เข้าใจวันที่แบบมนุษย์
# =============================================================================

THAI_MONTHS = {
    "มกราคม": 1, "ม.ค.": 1, "มค": 1,
    "กุมภาพันธ์": 2, "ก.พ.": 2, "กพ": 2,
    "มีนาคม": 3, "มี.ค.": 3, "มีค": 3,
    "เมษายน": 4, "เม.ย.": 4, "เมย": 4,
    "พฤษภาคม": 5, "พ.ค.": 5, "พค": 5,
    "มิถุนายน": 6, "มิ.ย.": 6, "มิย": 6,
    "กรกฎาคม": 7, "ก.ค.": 7, "กค": 7,
    "สิงหาคม": 8, "ส.ค.": 8, "สค": 8,
    "กันยายน": 9, "ก.ย.": 9, "กย": 9,
    "ตุลาคม": 10, "ต.ค.": 10, "ตค": 10,
    "พฤศจิกายน": 11, "พ.ย.": 11, "พย": 11,
    "ธันวาคม": 12, "ธ.ค.": 12, "ธค": 12
}

THAI_HOLIDAYS = {
    "ปีใหม่": (1, 1),
    "สงกรานต์": (4, 13),
    "วันแม่": (8, 12),
    "วันพ่อ": (12, 5),
    "ลอยกระทง": None  # Floating holiday, calculated separately
}


class SmartDateParser:
    """Parses human-friendly date expressions in Thai and English"""
    
    @staticmethod
    def parse(date_text: str, reference_date: Optional[datetime] = None) -> Optional[str]:
        """
        Parse natural language date to YYYY-MM-DD
        
        Examples:
        - "พรุ่งนี้" -> tomorrow
        - "สัปดาห์หน้า" -> next week
        - "สงกรานต์" -> April 13
        - "13 เมษายน" -> April 13
        - "13/4/2569" -> 2026-04-13 (converts พ.ศ.)
        """
        if not date_text:
            return None
            
        ref = reference_date or datetime.now()
        text = date_text.strip().lower()
        
        # 1. Relative dates (Thai)
        if "วันนี้" in text or "today" in text:
            return ref.strftime("%Y-%m-%d")
        if "พรุ่งนี้" in text or "tomorrow" in text:
            return (ref + timedelta(days=1)).strftime("%Y-%m-%d")
        if "มะรืนนี้" in text or "day after tomorrow" in text:
            return (ref + timedelta(days=2)).strftime("%Y-%m-%d")
        if "สัปดาห์หน้า" in text or "next week" in text:
            return (ref + timedelta(days=7)).strftime("%Y-%m-%d")
        if "เดือนหน้า" in text or "next month" in text:
            next_month = ref.replace(day=1) + timedelta(days=32)
            return next_month.replace(day=1).strftime("%Y-%m-%d")
        
        # 2. Thai holidays
        for holiday, month_day in THAI_HOLIDAYS.items():
            if holiday in text and month_day:
                month, day = month_day
                year = ref.year
                holiday_date = datetime(year, month, day)
                if holiday_date < ref:
                    year += 1
                return f"{year}-{month:02d}-{day:02d}"
        
        # 3. ✅ NEW: Handle "วันที่ 25" (day only, no month/year specified)
        # Match patterns like "วันที่ 25", "25 นี้", "วันที่ 20"
        day_only_match = re.search(r'วันที่?\s*(\d{1,2})(?:\s*นี้)?(?!\s*[/\-\.])', text)
        if day_only_match and not re.search(r'\d{1,2}\s*/\s*\d{1,2}', text):  # Not a date/month format
            try:
                day = int(day_only_match.group(1))
                if 1 <= day <= 31:
                    # Use current month first, if past, use next month
                    year = ref.year
                    month = ref.month
                    try:
                        candidate = datetime(year, month, day)
                        if candidate < ref:
                            # Date already passed this month, use next month
                            month += 1
                            if month > 12:
                                month = 1
                                year += 1
                        return f"{year}-{month:02d}-{day:02d}"
                    except ValueError:
                        # Invalid day for current month, try next month
                        month += 1
                        if month > 12:
                            month = 1
                            year += 1
                        try:
                            return f"{year}-{month:02d}-{day:02d}"
                        except ValueError:
                            logger.warning(f"Invalid day {day} for any month")
                            return None
            except (ValueError, AttributeError):
                pass
        
        # 4. Thai date format: "13 เมษายน", "13 เม.ย.", "30 ม.ค."
        for month_name, month_num in THAI_MONTHS.items():
            if month_name in text:
                match = re.search(r'(\d{1,2})', text)
                if match:
                    day = int(match.group(1))
                    year = ref.year
                    # ✅ Check for year in text (Buddhist Era or AD)
                    year_match = re.search(r'(\d{4})', text)
                    if year_match:
                        year = int(year_match.group(1))
                        if year > 2500:
                            # Buddhist Era (พ.ศ.) - convert to AD
                            year -= 543
                            logger.debug(f"Converted Buddhist Era year {year_match.group(1)} to AD {year}")
                    else:
                        # ✅ No year specified - use current year, but check if date is in the past
                        # If the date has already passed this year, use next year
                        try:
                            candidate = datetime(ref.year, month_num, day)
                            if candidate < ref:
                                # Date already passed this year, use next year
                                year = ref.year + 1
                                logger.debug(f"Date {day}/{month_num} already passed, using next year: {year}")
                        except ValueError:
                            # Invalid day for this month (e.g., Feb 30), try next year
                            year = ref.year + 1
                            logger.debug(f"Invalid day {day} for month {month_num} in {ref.year}, trying {year}")
                    try:
                        parsed_date = f"{year}-{month_num:02d}-{day:02d}"
                        # ✅ Validate the date is valid
                        datetime.strptime(parsed_date, "%Y-%m-%d")
                        logger.debug(f"✅ Parsed '{date_text}' -> '{parsed_date}'")
                        return parsed_date
                    except ValueError:
                        logger.warning(f"⚠️ Invalid date: {year}-{month_num:02d}-{day:02d} (day {day} doesn't exist in month {month_num})")
                        return None
        
        # 5. Numeric formats: "13/4", "13/4/2569", "2026-04-13"
        if re.match(r'\d{4}-\d{2}-\d{2}', text):
            return text[:10]
        
        match = re.match(r'(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?', text)
        if match:
            day = int(match.group(1))
            month = int(match.group(2))
            year = int(match.group(3)) if match.group(3) else ref.year
            
            if year > 2500:
                year -= 543
            elif year < 100:
                year += 2000
            
            try:
                return f"{year}-{month:02d}-{day:02d}"
            except ValueError:
                logger.warning(f"Invalid date: {year}-{month}-{day}")
                return None
        
        # 6. Day of week (approximate to next occurrence)
        weekdays = {
            "จันทร์": 0, "monday": 0,
            "อังคาร": 1, "tuesday": 1,
            "พุธ": 2, "wednesday": 2,
            "พฤหัสบดี": 3, "พฤหัส": 3, "thursday": 3,
            "ศุกร์": 4, "friday": 4,
            "เสาร์": 5, "saturday": 5,
            "อาทิตย์": 6, "sunday": 6
        }
        for day_name, day_num in weekdays.items():
            if day_name in text:
                days_ahead = day_num - ref.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                target_date = ref + timedelta(days=days_ahead)
                return target_date.strftime("%Y-%m-%d")
        
        logger.warning(f"Could not parse date: {date_text}")
        return None


# =============================================================================
# 2. Location Intelligence - รู้จักสถานที่ทั่วโลก
# =============================================================================

LANDMARKS = {
    # Thailand
    "สยามพารากอน": ("Bangkok", "Thailand", "BKK"),
    "siam paragon": ("Bangkok", "Thailand", "BKK"),
    "แหลมพรหมเทพ": ("Phuket", "Thailand", "HKT"),
    "laem promthep": ("Phuket", "Thailand", "HKT"),
    "วัดพระแก้ว": ("Bangkok", "Thailand", "BKK"),
    "grand palace": ("Bangkok", "Thailand", "BKK"),
    "ถนนคนเดินเชียงใหม่": ("Chiang Mai", "Thailand", "CNX"),
    "ตลาดน้ำดำเนินสะดวก": ("Ratchaburi", "Thailand", "BKK"),
    
    # Japan
    "tokyo tower": ("Tokyo", "Japan", "TYO"),
    "senso-ji": ("Tokyo", "Japan", "TYO"),
    "fushimi inari": ("Kyoto", "Japan", "KIX"),
    "osaka castle": ("Osaka", "Japan", "KIX"),
    "mount fuji": ("Shizuoka", "Japan", "NRT"),
    
    # Europe
    "eiffel tower": ("Paris", "France", "PAR"),
    "colosseum": ("Rome", "Italy", "ROM"),
    "big ben": ("London", "UK", "LON"),
    
    # USA
    "statue of liberty": ("New York", "USA", "NYC"),
    "times square": ("New York", "USA", "NYC"),
    "hollywood": ("Los Angeles", "USA", "LAX"),
}

MAJOR_CITIES = {
    # Thailand
    "bangkok": "BKK", "กรุงเทพ": "BKK", "กทม": "BKK",
    "chiang mai": "CNX", "เชียงใหม่": "CNX",
    "phuket": "HKT", "ภูเก็ต": "HKT",
    "pattaya": "UTP", "พัทยา": "UTP",
    "krabi": "KBV", "กระบี่": "KBV",
    "samui": "USM", "เกาะสมุย": "USM",
    
    # Asia
    "tokyo": "NRT", "โตเกียว": "NRT",
    "seoul": "ICN", "โซล": "ICN",
    "incheon": "ICN", "อินชอน": "ICN",
    "singapore": "SIN", "สิงคโปร์": "SIN",
    "hong kong": "HKG", "ฮ่องกง": "HKG",
    "taipei": "TPE", "ไทเป": "TPE",
    "osaka": "KIX", "โอซาก้า": "KIX",
    "kyoto": "KIX", "เกียวโต": "KIX",
    "sapporo": "CTS", "ซัปโปโร": "CTS",
    "fukuoka": "FUK", "ฟุกุโอกะ": "FUK",
    
    # Europe
    "london": "LON", "ลอนดอน": "LON",
    "paris": "PAR", "ปารีส": "PAR",
    "rome": "ROM", "โรม": "ROM",
    "barcelona": "BCN", "บาร์เซโลนา": "BCN",
    
    # USA
    "new york": "NYC", "นิวยอร์ก": "NYC",
    "los angeles": "LAX", "ลอสแองเจลิส": "LAX",
    "san francisco": "SFO", "ซานฟรานซิสโก": "SFO",
}


class LocationIntelligence:
    """Provides smart location resolution and context"""
    
    @staticmethod
    def resolve_location(location_text: str, context: str = "general") -> Dict[str, Any]:
        """Resolve a location string to city, country, and nearest airport"""
        if not location_text:
            return {"error": "Empty location"}
        
        text_lower = location_text.lower().strip()
        
        # Check if it's a known landmark
        for landmark, (city, country, airport) in LANDMARKS.items():
            if landmark in text_lower:
                if context == "hotel":
                    return {
                        "city": city,
                        "country": country,
                        "airport_code": airport,
                        "is_landmark": True,
                        "landmark_name": landmark.title(),
                        "location_for_search": location_text,
                        "original_text": location_text,
                        "resolved_from": "landmark_database",
                        "search_hint": f"Hotels near {landmark.title()}"
                    }
                else:
                    return {
                        "city": city,
                        "country": country,
                        "airport_code": airport,
                        "is_landmark": True,
                        "landmark_name": landmark.title(),
                        "location_for_search": city,
                        "original_text": location_text,
                        "resolved_from": "landmark_database",
                        "note": f"Landmark '{landmark.title()}' is in {city}"
                    }
        
        # Check if it's a known city
        for city_name, airport_code in MAJOR_CITIES.items():
            if city_name in text_lower:
                return {
                    "city": city_name.title(),
                    "country": None,
                    "airport_code": airport_code,
                    "is_landmark": False,
                    "location_for_search": city_name.title(),
                    "original_text": location_text,
                    "resolved_from": "city_database"
                }
        
        # If not found, return original with flag for external resolution
        return {
            "city": location_text,
            "country": None,
            "airport_code": None,
            "is_landmark": False,
            "location_for_search": location_text,
            "original_text": location_text,
            "resolved_from": "unknown",
            "requires_geocoding": True
        }
    
    @staticmethod
    def suggest_nearby_attractions(city: str) -> List[str]:
        """Suggest attractions near a city"""
        attractions_map = {
            "Bangkok": ["Grand Palace", "Wat Pho", "Chatuchak Market", "Siam Paragon"],
            "Phuket": ["Patong Beach", "Phi Phi Islands", "Big Buddha", "Old Phuket Town"],
            "Chiang Mai": ["Doi Suthep", "Old City Temples", "Night Bazaar", "Elephant Sanctuary"],
            "Tokyo": ["Tokyo Tower", "Senso-ji", "Shibuya Crossing", "Meiji Shrine"],
            "Paris": ["Eiffel Tower", "Louvre Museum", "Arc de Triomphe", "Notre-Dame"],
        }
        return attractions_map.get(city, [])
    
    @staticmethod
    async def search_nearby_google(location_name: str, place_type: str = "lodging", radius: int = 2000) -> List[Dict[str, Any]]:
        """Search for places near a location using Google Maps Places API"""
        gmaps = get_gmaps_client()
        if not gmaps:
            logger.warning("Google Maps API not configured")
            return []
        
        try:
            loop = asyncio.get_event_loop()
            geocode_result = await loop.run_in_executor(
                None,
                lambda: gmaps.geocode(location_name, language="th")
            )
            
            if not geocode_result:
                logger.warning(f"Could not geocode location: {location_name}")
                return []
            
            location = geocode_result[0]["geometry"]["location"]
            lat = location["lat"]
            lng = location["lng"]
            
            places_result = await loop.run_in_executor(
                None,
                lambda: gmaps.places_nearby(
                    location=(lat, lng),
                    radius=radius,
                    type=place_type,
                    language="th"
                )
            )
            
            places = places_result.get("results", [])
            formatted_places = []
            for place in places[:10]:
                formatted_places.append({
                    "name": place.get("name"),
                    "rating": place.get("rating"),
                    "user_ratings_total": place.get("user_ratings_total"),
                    "vicinity": place.get("vicinity"),
                    "place_id": place.get("place_id"),
                    "types": place.get("types", []),
                    "geometry": place.get("geometry", {}).get("location"),
                    "price_level": place.get("price_level"),
                    "opening_hours": place.get("opening_hours", {}).get("open_now")
                })
            
            return formatted_places
            
        except Exception as e:
            logger.error(f"Error searching nearby places: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def get_place_details_google(place_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a place using Google Place ID"""
        gmaps = get_gmaps_client()
        if not gmaps:
            return None
        
        try:
            loop = asyncio.get_event_loop()
            place_result = await loop.run_in_executor(
                None,
                lambda: gmaps.place(
                    place_id=place_id,
                    fields=["name", "formatted_address", "formatted_phone_number",
                           "geometry", "rating", "user_ratings_total", "reviews",
                           "website", "url", "price_level", "opening_hours", "photo"],
                    language="th"
                )
            )
            
            result = place_result.get("result")
            return result if result else None
            
        except Exception as e:
            logger.error(f"Error getting place details: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def find_hotels_near_landmark(landmark_name: str, radius: int = 2000, max_results: int = 10) -> List[Dict[str, Any]]:
        """Find hotels near a landmark with detailed information"""
        hotels = await LocationIntelligence.search_nearby_google(landmark_name, "lodging", radius)
        hotels_sorted = sorted(
            hotels,
            key=lambda x: (x.get("rating") or 0, x.get("user_ratings_total") or 0),
            reverse=True
        )
        return hotels_sorted[:max_results]
    
    @staticmethod
    async def get_area_recommendations(location_name: str, radius: int = 3000) -> Dict[str, List[Dict[str, Any]]]:
        """Get comprehensive recommendations for an area"""
        results = {"hotels": [], "restaurants": [], "attractions": [], "shopping": []}
        
        try:
            tasks = [
                LocationIntelligence.search_nearby_google(location_name, "lodging", radius),
                LocationIntelligence.search_nearby_google(location_name, "restaurant", radius),
                LocationIntelligence.search_nearby_google(location_name, "tourist_attraction", radius),
                LocationIntelligence.search_nearby_google(location_name, "shopping_mall", radius)
            ]
            
            hotels, restaurants, attractions, shopping = await asyncio.gather(*tasks)
            results["hotels"] = hotels[:5]
            results["restaurants"] = restaurants[:5]
            results["attractions"] = attractions[:5]
            results["shopping"] = shopping[:5]
            
        except Exception as e:
            logger.error(f"Error getting area recommendations: {e}", exc_info=True)
        
        return results


# =============================================================================
# 3. Budget Advisor - คำนวณและแนะนำงบประมาณ
# =============================================================================

@dataclass
class BudgetBreakdown:
    """Budget breakdown with estimates"""
    total: float
    flights: float
    hotels: float
    food: float
    transport: float
    activities: float
    buffer: float
    currency: str = "THB"
    is_realistic: bool = True
    warnings: List[str] = field(default_factory=list)


class BudgetAdvisor:
    """Smart budget calculation and recommendations"""
    
    DAILY_COSTS = {
        "budget": {"food": 500, "transport": 200, "activities": 300, "hotel": 800},
        "moderate": {"food": 1500, "transport": 500, "activities": 1000, "hotel": 2000},
        "luxury": {"food": 3000, "transport": 1500, "activities": 3000, "hotel": 5000}
    }
    
    FLIGHT_ESTIMATES = {
        "domestic": 3000,
        "regional": 8000,
        "international": 20000
    }
    
    @classmethod
    def estimate_trip_cost(cls, destination: str, nights: int, guests: int = 1, 
                          travel_mode: str = "both", style: str = "moderate") -> BudgetBreakdown:
        """Estimate realistic trip cost"""
        if style not in cls.DAILY_COSTS:
            style = "moderate"
        
        costs = cls.DAILY_COSTS[style]
        warnings = []
        
        dest_lower = destination.lower()
        if "tokyo" in dest_lower or "seoul" in dest_lower or "singapore" in dest_lower:
            flight_category = "regional"
        elif "paris" in dest_lower or "london" in dest_lower or "new york" in dest_lower:
            flight_category = "international"
        else:
            flight_category = "domestic"
        
        flight_cost = cls.FLIGHT_ESTIMATES[flight_category] * guests if travel_mode != "car_only" else 0
        hotel_cost = costs["hotel"] * nights * (guests if guests <= 2 else guests * 0.7)
        food_cost = costs["food"] * nights * guests
        transport_cost = costs["transport"] * nights * guests
        activities_cost = costs["activities"] * nights * guests
        
        subtotal = flight_cost + hotel_cost + food_cost + transport_cost + activities_cost
        buffer = subtotal * 0.1
        total = subtotal + buffer
        
        if nights < 2:
            warnings.append("ทริปสั้น: พิจารณาเพิ่มเวลาเพื่อคุ้มค่าค่าเครื่องบิน")
        if guests > 4:
            warnings.append("กลุ่มใหญ่: อาจต้องจองหลายห้อง/ที่นั่ง")
        if total > 100000:
            warnings.append("งบสูง: พิจารณาจองล่วงหน้าเพื่อประหยัด")
        
        return BudgetBreakdown(
            total=round(total),
            flights=round(flight_cost),
            hotels=round(hotel_cost),
            food=round(food_cost),
            transport=round(transport_cost),
            activities=round(activities_cost),
            buffer=round(buffer),
            currency="THB",
            is_realistic=True,
            warnings=warnings or []
        )
    
    @staticmethod
    def check_budget_feasibility(requested_budget: float, estimated_cost: float) -> Tuple[bool, str]:
        """Check if requested budget is realistic"""
        if requested_budget >= estimated_cost:
            return True, "งบประมาณเพียงพอ"
        
        shortfall = estimated_cost - requested_budget
        percent_short = (shortfall / estimated_cost) * 100
        
        if percent_short < 20:
            return True, f"งบประมาณเกือบพอ (ขาดอีก {int(shortfall):,} บาท หรือ {percent_short:.0f}%)"
        elif percent_short < 40:
            return False, f"งบประมาณต่ำไปหน่อย (แนะนำเพิ่มอีก {int(shortfall):,} บาท)"
        else:
            return False, f"งบประมาณต่ำเกินไป (ต้องการอย่างน้อย {int(estimated_cost):,} บาท)"


# =============================================================================
# 4. Input Validator & Sanitizer
# =============================================================================

class InputValidator:
    """Validates and sanitizes user inputs"""
    
    @staticmethod
    def validate_date_range(start_date: str, end_date: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """Validate date range"""
        try:
            start = datetime.fromisoformat(start_date)
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            if start < today:
                return False, "วันเดินทางต้องเป็นวันนี้หรืออนาคต"
            
            if start > today + timedelta(days=365):
                return False, "วันเดินทางห่างเกิน 1 ปี (ราคาอาจไม่แม่นยำ)"
            
            if end_date:
                end = datetime.fromisoformat(end_date)
                if end < start:
                    return False, "วันกลับต้องอยู่หลังวันไป"
                if (end - start).days > 60:
                    return False, "ทริปยาวเกิน 60 วัน (ตรวจสอบวันที่อีกครั้ง)"
            
            return True, None
            
        except ValueError:
            return False, "รูปแบบวันที่ไม่ถูกต้อง (ใช้ YYYY-MM-DD)"
    
    @staticmethod
    def validate_guests(guests: int) -> Tuple[bool, Optional[str]]:
        """Validate number of guests"""
        if guests < 1:
            return False, "จำนวนผู้เดินทางต้องมากกว่า 0"
        if guests > 9:
            return False, "จำนวนผู้เดินทางเกิน 9 คน (ติดต่อทีมงานโดยตรง)"
        return True, None
    
    @staticmethod
    def validate_budget(budget: float) -> Tuple[bool, Optional[str]]:
        """Validate budget amount"""
        if budget < 0:
            return False, "งบประมาณต้องเป็นจำนวนบวก"
        if budget > 0 and budget < 1000:
            return False, "งบประมาณน้อยเกินไป (ควรมากกว่า 1,000 บาท)"
        if budget > 10000000:
            return False, "งบประมาณสูงผิดปกติ (ตรวจสอบจำนวนอีกครั้ง)"
        return True, None


# =============================================================================
# 5. Proactive Recommendation Engine
# =============================================================================

class ProactiveRecommendations:
    """Generates proactive suggestions based on context"""
    
    @staticmethod
    def suggest_based_on_trip(destination: str, nights: int, season: Optional[str] = None) -> List[str]:
        """Generate contextual recommendations"""
        suggestions = []
        dest_lower = destination.lower()
        
        if "tokyo" in dest_lower or "japan" in dest_lower:
            suggestions.append("💡 แนะนำ: ซื้อ JR Pass สำหรับประหยัดค่าเดินทางในญี่ปุ่น")
            suggestions.append("📱 แนะนำ: เช่า Pocket WiFi หรือซื้อ SIM การด์ท้องถิ่น")
        
        if "europe" in dest_lower or "paris" in dest_lower or "london" in dest_lower:
            suggestions.append("🛂 เตือน: ตรวจสอบวีซ่า Schengen ล่วงหน้า")
            suggestions.append("💳 แนะนำ: แจ้งธนาคารก่อนใช้บัตรในต่างประเทศ")
        
        if "beach" in dest_lower or "phuket" in dest_lower or "samui" in dest_lower:
            suggestions.append("🏖️ แนะนำ: จองทัวร์เกาะล่วงหน้าในช่วง high season")
            suggestions.append("☀️ เตือน: อย่าลืมครีมกันแดดและหมวก")
        
        if nights < 3:
            suggestions.append("⚡ ทริปสั้น: วางแผนเส้นทางให้ดีเพื่อประหยัดเวลา")
        elif nights > 7:
            suggestions.append("🏨 ทริปยาว: พิจารณาเปลี่ยนที่พักเพื่อประสบการณ์หลากหลาย")
        
        if season:
            season_lower = season.lower()
            if "summer" in season_lower or "hot" in season_lower:
                suggestions.append("🌡️ ฤดูร้อน: เลือกที่พักที่มีแอร์และสระว่ายน้ำ")
            elif "winter" in season_lower or "cold" in season_lower:
                suggestions.append("🧥 ฤดูหนาว: เตรียมเสื้อกันหนาวและเช็คอุณหภูมิ")
        
        return suggestions[:3]


# =============================================================================
# 6. Self-Correction Validator
# =============================================================================

class SelfCorrectionValidator:
    """Validates agent decisions and corrects common mistakes"""
    
    @staticmethod
    def validate_trip_plan(plan_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate a trip plan for common issues"""
        issues = []
        
        if not plan_data.get("destination"):
            issues.append("ขาดข้อมูลจุดหมาย")
        
        if not plan_data.get("start_date"):
            issues.append("ขาดข้อมูลวันเดินทาง")
        
        start = plan_data.get("start_date")
        end = plan_data.get("end_date")
        if start and end:
            try:
                start_dt = datetime.fromisoformat(start)
                end_dt = datetime.fromisoformat(end)
                if end_dt < start_dt:
                    issues.append("วันกลับอยู่ก่อนวันไป (ควรสลับ)")
            except ValueError:
                issues.append("รูปแบบวันที่ไม่ถูกต้อง")
        
        guests = plan_data.get("guests", 1)
        try:
            guests = int(guests) if guests is not None else 1
        except (TypeError, ValueError):
            guests = 1
        if guests < 1 or guests > 20:
            issues.append(f"จำนวนผู้เดินทางผิดปกติ: {guests}")
        
        budget = plan_data.get("budget")
        if budget and budget > 0:
            nights = 1
            if start and end:
                try:
                    nights = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
                except Exception:
                    pass

            min_budget = guests * nights * 2000
            if budget < min_budget:
                issues.append(f"งบประมาณต่ำเกินไป (แนะนำอย่างน้อย {min_budget:,} บาท)")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def suggest_corrections(issues: List[str]) -> List[str]:
        """Generate correction suggestions from issues"""
        corrections = []
        for issue in issues:
            if "ขาดข้อมูล" in issue:
                corrections.append("ถามผู้ใช้ให้ข้อมูลเพิ่มเติม")
            elif "วันกลับอยู่ก่อนวันไป" in issue:
                corrections.append("สลับวันที่ไปกลับ")
            elif "งบประมาณต่ำเกินไป" in issue:
                corrections.append("แจ้งเตือนผู้ใช้และแนะนำงบที่เหมาะสม")
        return corrections


# =============================================================================
# 7. Complete Intelligence Facade
# =============================================================================

class AgentIntelligence:
    """
    Main facade for all intelligence features
    Use this class in the agent for all smart enhancements
    """
    
    def __init__(self):
        self.date_parser = SmartDateParser()
        self.location_intel = LocationIntelligence()
        self.budget_advisor = BudgetAdvisor()
        self.validator = InputValidator()
        self.recommender = ProactiveRecommendations()
        self.corrector = SelfCorrectionValidator()
    
    def enhance_user_input(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Analyze and enhance user input with intelligence"""
        enhanced = {
            "original_input": user_input,
            "dates": [],
            "locations": [],
            "suggestions": [],
            "warnings": []
        }
        
        date_patterns = re.findall(r'\d{1,2}[/\-]\d{1,2}(?:[/\-]\d{2,4})?', user_input)
        for date_str in date_patterns:
            parsed = self.date_parser.parse(date_str)
            if parsed:
                enhanced["dates"].append(parsed)
        
        for city in MAJOR_CITIES.keys():
            if city in user_input.lower():
                loc_info = self.location_intel.resolve_location(city)
                enhanced["locations"].append(loc_info)
        
        logger.info(f"Enhanced input: found {len(enhanced['dates'])} dates, {len(enhanced['locations'])} locations")
        return enhanced
    
    def validate_and_correct_plan(self, plan_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a trip plan and return corrections if needed"""
        is_valid, issues = self.corrector.validate_trip_plan(plan_data)
        corrections = self.corrector.suggest_corrections(issues) if issues else []
        
        if plan_data.get("destination") and plan_data.get("start_date") and plan_data.get("end_date"):
            try:
                nights = (datetime.fromisoformat(plan_data["end_date"]) - 
                         datetime.fromisoformat(plan_data["start_date"])).days
                suggestions = self.recommender.suggest_based_on_trip(plan_data["destination"], nights)
            except Exception:
                suggestions = []
        else:
            suggestions = []
        
        return {
            "is_valid": is_valid,
            "issues": issues,
            "corrections": corrections,
            "suggestions": suggestions,
            "original_plan": plan_data
        }


# Global singleton instance
agent_intelligence = AgentIntelligence()
