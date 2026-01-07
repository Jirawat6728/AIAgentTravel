"""
Production-Grade Travel Agent Engine
Two-Pass ReAct Loop Architecture
Phase 1: Controller (Think & Act)
Phase 2: Responder (Speak)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, Callable, Awaitable, List
from datetime import datetime
import json

from app.models import UserSession, TripPlan, Segment, ControllerAction, ActionLog, ActionType
from app.models.trip_plan import SegmentStatus
from app.storage.interface import StorageInterface
from app.services.llm import LLMService
from app.services.memory import MemoryService
from app.services.travel_service import TravelOrchestrator, TravelSearchRequest
from app.core.exceptions import AgentException, LLMException
from app.core.logging import get_logger
from app.core.config import settings
from app.services.agent_monitor import agent_monitor

logger = get_logger(__name__)


# =============================================================================
# Phase 1: Controller System Prompt
# =============================================================================
CONTROLLER_SYSTEM_PROMPT = """You are an intelligent Workflow Controller for a Travel Agent AI.
Analyze the current State and User Input, then decide the NEXT ACTIONS.

CRITICAL RULES:
1. Output VALID JSON ONLY. No other text.
2. EXTRACT ALL information from user input immediately (dates, locations, guests, preferences).
3. OPTIMIZE SPEED: Perform multiple actions in parallel if possible (Batch Actions).
4. If user provides new info -> UPDATE_REQ (can update multiple slots).
5. If requirements are COMPLETE for any slot and NO options_pool -> CALL_SEARCH (can search multiple slots).
6. If options_pool exists but no selected_option -> ASK_USER.

Batch Actions:
You can return a list of actions in `batch_actions` field.
Example: Update flights and hotels, then search both in one turn.

Available Actions:
- UPDATE_REQ: {"slot": "flights"|"accommodations"|"ground_transport", "segment_index": 0, "updates": {...}}
- CALL_SEARCH: {"slot": "...", "segment_index": 0}
- SELECT_OPTION: {"slot": "...", "segment_index": 0, "option_index": 0}
- ASK_USER: {"missing_fields": ["origin", "destination"]}

JSON Format:
{
  "thought": "Reasoning...",
  "action": "UPDATE_REQ",  // Primary action type (or use "BATCH" if multiple types)
  "payload": {},           // Payload for primary action (optional if batch_actions used)
  "batch_actions": [       // Optional: List of actions to run in parallel
    {"action": "UPDATE_REQ", "payload": {...}},
    {"action": "CALL_SEARCH", "payload": {...}}
  ]
}

Example (User: "I want to go to Tokyo on Dec 10 for 5 days"):
{
  "thought": "User provided destination and dates. I will update flights and hotels requirements.",
  "action": "UPDATE_REQ",
  "batch_actions": [
    {"action": "UPDATE_REQ", "payload": {"slot": "flights", "segment_index": 0, "updates": {"destination": "Tokyo", "departure_date": "2024-12-10"}}},
    {"action": "UPDATE_REQ", "payload": {"slot": "accommodations", "segment_index": 0, "updates": {"location": "Tokyo", "check_in": "2024-12-10", "check_out": "2024-12-15"}}}
  ]
}"""


# =============================================================================
# Phase 2: Responder System Prompt
# =============================================================================
RESPONDER_SYSTEM_PROMPT = """You are the Voice of the Travel Agent AI.
Generate a helpful, polite, and proactive response message in Thai.

CRITICAL RULES:
1. Use Thai language ONLY.
2. READ THE ACTION_LOG: Acknowledge what was done (e.g., "รับทราบค่ะ ฉันได้อัปเดตข้อมูลเที่ยวบินให้แล้ว").
3. If UPDATE_REQ was performed, mention the specific details extracted (origin, destination, dates, guests).
4. If CALL_SEARCH was performed, mention that you found options and are ready to show them.
5. If options_pool exists, tell the user you have options ready for them to choose.
6. Check State for missing information and ask SPECIFIC questions (not generic).
7. Be proactive: If you have enough info, suggest next steps.
8. NEVER say "no information" if actions were taken.

Tone: Professional, friendly, helpful, proactive, and confident."""


class TravelAgent:
    """
    Production-Grade Travel Agent with Two-Pass ReAct Loop
    Robust error handling and logging
    """
    
    def __init__(
        self,
        storage: StorageInterface,
        llm_service: Optional[LLMService] = None
    ):
        """
        Initialize Travel Agent
        
        Args:
            storage: Storage interface implementation
            llm_service: Optional LLM service (creates new if None)
        """
        self.storage = storage
        self.llm = llm_service or LLMService()
        self.memory = MemoryService(self.llm)
        self.orchestrator = TravelOrchestrator()
        agent_monitor.log_activity("system", "system", "start", "TravelAgent instance created")
        logger.info("TravelAgent initialized with Brain/Memory support and TravelOrchestrator")
    
    async def run_turn(
        self,
        session_id: str,
        user_input: str,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None
    ) -> str:
        """
        Run one turn of conversation (main entry point)
        
        Args:
            session_id: Session identifier
            user_input: User's message
            status_callback: Optional async callback for status updates (status, message, step)
            
        Returns:
            Response message in Thai
        """
        try:
            # Load session
            session = await self.storage.get_session(session_id)
            if not session:
                logger.error(f"Failed to load session {session_id}")
                agent_monitor.log_activity(session_id, "unknown", "error", f"Failed to load session")
                raise AgentException(f"Failed to load session {session_id}")
            
            user_id = session.user_id
            agent_monitor.log_activity(session_id, user_id, "start", f"Processing message: {user_input[:50]}...")
            
            # Phase 0: Recall (Brain Memory)
            if status_callback:
                await status_callback("thinking", "กำลังระลึกความจำ...", "recall_start")
            
            user_memories = await self.memory.recall(session.user_id)
            memory_context = self.memory.format_memories_for_prompt(user_memories)
            
            # Phase 1: Controller Loop (Think & Act)
            if status_callback:
                await status_callback("thinking", "กำลังวางแผนทริป...", "controller_start")
                
            action_log = await self.run_controller(session, user_input, status_callback, memory_context)
            
            # Save state after Phase 1
            await self.storage.save_session(session)
            
            # Phase 2: Responder (Speak)
            if status_callback:
                await status_callback("speaking", "กำลังสรุปคำตอบ...", "responder_start")
                
            response_message = await self.generate_response(session, action_log, memory_context)
            
            # Phase 3: Consolidate (Learning)
            # Run in background to not block response
            import asyncio
            asyncio.create_task(self.memory.consolidate(session.user_id, user_input, response_message))
            
            # Final save
            await self.storage.save_session(session)
            
            return response_message
        
        except Exception as e:
            logger.error(f"Error in run_turn: {e}", exc_info=True)
            raise AgentException(f"Agent execution failed: {e}") from e
    
    async def run_controller(
        self,
        session: UserSession,
        user_input: str,
        status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
        memory_context: str = ""
    ) -> ActionLog:
        """
        Phase 1: Controller Loop
        Loop (max 3 times) to execute actions until ASK_USER
        CRITICAL: All actions wrapped in try/except to prevent crashes
        
        Args:
            session: UserSession with current state
            user_input: User's message
            status_callback: Optional async callback for status updates
            memory_context: Background information about user preferences
            
        Returns:
            ActionLog with all actions taken
        """
        action_log = ActionLog()
        max_iterations = settings.controller_max_iterations
        
        for iteration in range(max_iterations):
            logger.info(f"Controller Loop iteration {iteration + 1}/{max_iterations}", 
                       extra={"session_id": session.session_id, "user_id": session.user_id})
            
            if status_callback:
                await status_callback("thinking", f"กำลังตรวจสอบข้อมูล (รอบที่ {iteration + 1})...", f"controller_iter_{iteration + 1}")
            
            try:
                # Get current state as JSON
                state_json = json.dumps(session.trip_plan.model_dump(), ensure_ascii=False, indent=2)
                
                # Call Controller LLM
                try:
                    action = await self._call_controller_llm(state_json, user_input, action_log, memory_context)
                except Exception as e:
                    logger.error(f"Failed to call controller LLM: {e}")
                    action = None
                
                if not action:
                    logger.warning("Controller LLM failed to return an action, using default ASK_USER")
                    agent_monitor.log_activity(session.session_id, session.user_id, "warning", "LLM failed to return action")
                    action = ControllerAction(
                        thought="I failed to decide an action due to an error. I will ask the user for clarification.",
                        action=ActionType.ASK_USER,
                        payload={"missing_fields": []}
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
                action_log.add_action(
                    action.action.value,
                    action.payload,
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
                        has_ask_user = True
                    
                    elif act_type == ActionType.UPDATE_REQ:
                        if status_callback:
                            await status_callback("acting", "กำลังอัปเดตข้อมูลทริป...", "update_req")
                        # Add to parallel tasks if possible, but UPDATE usually needs to happen before SEARCH
                        # For safety, execute UPDATEs sequentially first, then SEARCHes in parallel
                        try:
                            await self._execute_update_req(session, payload, action_log)
                        except Exception as e:
                            logger.error(f"Error executing UPDATE_REQ: {e}", exc_info=True)
                    
                    elif act_type == ActionType.CALL_SEARCH:
                        # Collect search tasks for parallel execution
                        search_tasks.append(self._execute_call_search(session, payload, action_log))
                    
                    elif act_type == ActionType.SELECT_OPTION:
                        if status_callback:
                            await status_callback("selecting", "กำลังบันทึกตัวเลือก...", "select_option")
                        try:
                            await self._execute_select_option(session, payload, action_log)
                        except Exception as e:
                            logger.error(f"Error executing SELECT_OPTION: {e}", exc_info=True)

                # Execute all search tasks in parallel
                if search_tasks:
                    if status_callback:
                        await status_callback("searching", "กำลังค้นหาข้อมูล (Parallel)...", "call_search")
                    await asyncio.gather(*search_tasks, return_exceptions=True)
                
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
        
        return action_log
    
    async def _call_controller_llm(
        self,
        state_json: str,
        user_input: str,
        action_log: ActionLog,
        memory_context: str = ""
    ) -> Optional[ControllerAction]:
        """
        Call Controller LLM to get next action
        
        Args:
            state_json: Current state as JSON string
            user_input: User's message
            action_log: Previous actions taken
            memory_context: Long-term memory about the user
            
        Returns:
            ControllerAction or None
        """
        try:
            # Build prompt
            prompt_parts = [
                "=== USER LONG-TERM MEMORY (BRAIN) ===\n",
                memory_context,
                "\n=== CURRENT STATE (TRIP PLAN) ===\n",
                state_json,
                "\n=== LATEST USER INPUT ===\n",
                user_input
            ]
            
            # Add action log if available
            if action_log.actions:
                prompt_parts.extend([
                    "\n=== ACTIONS TAKEN IN THIS TURN ===\n",
                    json.dumps([a.model_dump() for a in action_log.actions[-3:]], ensure_ascii=False, indent=2)
                ])
            
            prompt_parts.append("\n=== INSTRUCTIONS ===\n")
            prompt_parts.append("1. EXTRACT ALL information from User Input (dates, locations, guests, preferences).")
            prompt_parts.append("2. OPTIMIZE SPEED: Use 'batch_actions' to perform multiple updates/searches in one turn.")
            prompt_parts.append("3. If user provides details for multiple slots, UPDATE ALL of them.")
            prompt_parts.append("4. If requirements are COMPLETE, CALL_SEARCH immediately.")
            prompt_parts.append("5. Output VALID JSON ONLY.")
            
            prompt = "\n".join(prompt_parts)
            
            # Call LLM with retries
            data = await self.llm.generate_json(
                prompt=prompt,
                system_prompt=CONTROLLER_SYSTEM_PROMPT,
                temperature=settings.controller_temperature
            )
            
            if not data or not isinstance(data, dict):
                logger.error(f"Invalid response from Controller LLM: {data}")
                return None
            
            # Check for missing keys and add defaults
            if "action" not in data:
                logger.warning("Controller LLM response missing 'action', defaulting to ASK_USER")
                data["action"] = "ASK_USER"
                data["thought"] = data.get("thought", "Missing action in response")
                data["payload"] = data.get("payload", {"missing_fields": []})

            # Validate and create ControllerAction
            action = ControllerAction(**data)
            return action
        
        except LLMException as e:
            logger.error(f"LLM error in controller: {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"Error calling Controller LLM: {e}", exc_info=True)
            return None
    
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
        
        if not slot_name:
            raise AgentException("UPDATE_REQ: Missing slot name")
        
        # Get segment
        segments = getattr(session.trip_plan, slot_name, [])
        if segment_index >= len(segments):
            # Create new segment if needed
            segment = Segment()
            segments.append(segment)
            segment_index = len(segments) - 1
        else:
            segment = segments[segment_index]
        
        # Normalize and enhance updates using LLM if needed
        enhanced_updates = await self._enhance_requirements(slot_name, updates, segment.requirements)
        
        # Update requirements (merge with existing)
        segment.requirements.update(enhanced_updates)
        
        # Convert city names to IATA codes for flights if needed
        if slot_name == "flights":
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
        """Enhance requirements using LLM for better extraction"""
        # For now, return updates as-is, but this can be enhanced with LLM extraction
        # if the updates are incomplete or ambiguous
        return updates
    
    def _is_iata_code(self, code: str) -> bool:
        """Check if string is likely an IATA code (3 uppercase letters)"""
        return isinstance(code, str) and len(code) == 3 and code.isupper() and code.isalpha()
    
    async def _city_to_iata(self, city_name: str) -> Optional[str]:
        """Convert city name to IATA code using TravelOrchestrator"""
        try:
            # Use orchestrator's geocoding and IATA finding
            loc_info = await self.orchestrator.get_coordinates(city_name)
            iata = await self.orchestrator.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            return iata
        except Exception as e:
            logger.warning(f"Failed to convert {city_name} to IATA: {e}")
            return None
    
    def _normalize_date(self, date_str: str) -> str:
        """Normalize date string to YYYY-MM-DD format"""
        from datetime import datetime
        try:
            # Try common Thai date formats
            if "ม.ค." in date_str or "มกราคม" in date_str:
                # Thai month format
                date_str = date_str.replace("ม.ค.", "January").replace("มกราคม", "January")
            elif "ก.พ." in date_str or "กุมภาพันธ์" in date_str:
                date_str = date_str.replace("ก.พ.", "February").replace("กุมภาพันธ์", "February")
            # Add more month conversions if needed
            
            # Try parsing
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return date_str  # Return as-is if can't parse
        except Exception:
            return date_str
    
    async def _execute_call_search(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog
    ):
        """Execute CALL_SEARCH action using TravelOrchestrator (Real API calls)"""
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        
        if not slot_name:
            raise AgentException("CALL_SEARCH: Missing slot name")
        
        # Get segment
        segments = getattr(session.trip_plan, slot_name, [])
        if segment_index >= len(segments):
            raise AgentException(f"CALL_SEARCH: Segment index {segment_index} out of range")
        
        segment = segments[segment_index]
        
        # Check if requirements are complete
        if not segment.needs_search():
            logger.info(f"CALL_SEARCH: Segment {slot_name}[{segment_index}] doesn't need search")
            return
        
        # Update status to searching
        segment.status = SegmentStatus.SEARCHING
        session.update_timestamp()
        
        try:
            req = segment.requirements
            
            # Build natural language query for TravelOrchestrator
            search_query = self._build_search_query(slot_name, req)
            
            logger.info(f"Searching {slot_name} with requirements: {req}")
            
            # Call TravelOrchestrator directly for better control and performance
            api_results = await self._call_search_direct(slot_name, req)
            
            # If direct call didn't work, fallback to smart_search
            if not api_results:
                logger.info(f"Direct search returned no results, trying smart_search...")
                search_request = TravelSearchRequest(
                    query=search_query,
                    user_id=session.user_id,
                    context={"slot": slot_name, "requirements": req}
                )
                results = await self.orchestrator.smart_search(search_request)
                
                # Map results from smart_search
                if slot_name == "flights" and results.flights:
                    api_results = results.flights
                elif slot_name == "accommodations" and results.hotels:
                    api_results = results.hotels
                elif slot_name == "ground_transport" and results.transfers:
                    api_results = results.transfers
            
            # Format results to options_pool
            real_results = []
            if api_results:
                if slot_name == "flights":
                    real_results = self._format_flight_options(api_results)
                elif slot_name == "accommodations":
                    real_results = self._format_hotel_options(api_results)
                elif slot_name == "ground_transport":
                    real_results = self._format_transfer_options(api_results)
            
            # If no results from API, try alternative search or provide helpful message
            if not real_results:
                logger.warning(f"No results found for {slot_name} with query: {search_query}")
                # Could try a broader search or ask user to refine criteria
                segment.status = SegmentStatus.PENDING
                action_log.add_action(
                    "CALL_SEARCH",
                    payload,
                    f"Searched {slot_name}[{segment_index}] but found 0 options. User may need to refine criteria."
                )
                return
            
            # Update segment with real results
            segment.options_pool = real_results
            segment.status = SegmentStatus.SELECTING
            
            action_log.add_action(
                "CALL_SEARCH",
                payload,
                f"Searched {slot_name}[{segment_index}] via API, found {len(real_results)} options"
            )
            session.update_timestamp()
        
        except Exception as e:
            logger.error(f"Error in CALL_SEARCH: {e}", exc_info=True)
            segment.status = SegmentStatus.PENDING
            # Don't raise - log and continue so agent can ask user
            action_log.add_action(
                "CALL_SEARCH",
                payload,
                f"Search failed: {str(e)}",
                success=False
            )
    
    def _build_search_query(self, slot_name: str, requirements: Dict[str, Any]) -> str:
        """Build natural language query from requirements for TravelOrchestrator"""
        if slot_name == "flights":
            origin = requirements.get("origin", "Bangkok")
            destination = requirements.get("destination", "Tokyo")
            date = requirements.get("departure_date") or requirements.get("date", "")
            adults = requirements.get("adults", 1)
            return f"flight from {origin} to {destination} on {date} for {adults} adults"
        
        elif slot_name == "accommodations":
            location = requirements.get("location") or requirements.get("destination", "Tokyo")
            check_in = requirements.get("check_in", "")
            check_out = requirements.get("check_out", "")
            guests = requirements.get("guests") or requirements.get("adults", 1)
            return f"hotel in {location} checkin {check_in} checkout {check_out} for {guests} guests"
        
        elif slot_name == "ground_transport":
            origin = requirements.get("origin", "")
            destination = requirements.get("destination", "")
            date = requirements.get("date", "")
            return f"transfer from {origin} to {destination} on {date}"
        
        return f"{slot_name} search"
    
    async def _call_search_direct(self, slot_name: str, requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Call TravelOrchestrator methods directly for better control"""
        try:
            if slot_name == "flights":
                origin = requirements.get("origin", "BKK")
                destination = requirements.get("destination", "NRT")
                date = requirements.get("departure_date") or requirements.get("date")
                adults = int(requirements.get("adults", 1))
                return await self.orchestrator.get_flights(origin, destination, date, adults)
            
            elif slot_name == "accommodations":
                location = requirements.get("location") or requirements.get("destination")
                city_code = requirements.get("city_code")
                check_in = requirements.get("check_in")
                check_out = requirements.get("check_out")
                guests = int(requirements.get("guests") or requirements.get("adults", 1))
                return await self.orchestrator.get_hotels(city_code, location, check_in, check_out, guests)
            
            elif slot_name == "ground_transport":
                origin = requirements.get("origin", "")
                destination = requirements.get("destination", "")
                date = requirements.get("date", "")
                # Use orchestrator's transfer method
                airport_code = requirements.get("airport_code", "BKK")
                address = requirements.get("address", destination)
                return await self.orchestrator.get_transfers(airport_code, address)
            
            return []
        except Exception as e:
            logger.error(f"Direct search failed for {slot_name}: {e}")
            return []
    
    def _format_flight_options(self, flights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus flight offers into options_pool format"""
        formatted = []
        for idx, flight in enumerate(flights[:10]):  # Limit to 10 options
            # Extract key info from Amadeus flight offer structure
            itineraries = flight.get("itineraries", [])
            if not itineraries:
                continue
            
            first_segment = itineraries[0].get("segments", [{}])[0]
            price = flight.get("price", {}).get("total", "0")
            currency = flight.get("price", {}).get("currency", "THB")
            
            formatted.append({
                "id": f"flight_{idx + 1}",
                "type": "flight",
                "name": f"{first_segment.get('departure', {}).get('iataCode', '')} → {first_segment.get('arrival', {}).get('iataCode', '')}",
                "price": float(price) if isinstance(price, str) else price,
                "currency": currency,
                "departure": first_segment.get("departure", {}).get("at", ""),
                "arrival": first_segment.get("arrival", {}).get("at", ""),
                "airline": first_segment.get("carrierCode", ""),
                "raw_data": flight  # Keep original for booking
            })
        return formatted
    
    def _format_hotel_options(self, hotels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus hotel offers into options_pool format"""
        formatted = []
        for idx, hotel in enumerate(hotels[:10]):  # Limit to 10 options
            hotel_data = hotel.get("hotel", {})
            offers = hotel.get("offers", [])
            if not offers:
                continue
            
            first_offer = offers[0]
            price = first_offer.get("price", {}).get("total", "0")
            currency = first_offer.get("price", {}).get("currency", "THB")
            
            formatted.append({
                "id": f"hotel_{idx + 1}",
                "type": "hotel",
                "name": hotel_data.get("name", "Unknown Hotel"),
                "price": float(price) if isinstance(price, str) else price,
                "currency": currency,
                "address": hotel_data.get("address", {}).get("lines", [""])[0],
                "rating": hotel_data.get("rating", 0),
                "raw_data": hotel  # Keep original for booking
            })
        return formatted
    
    def _format_transfer_options(self, transfers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Format Amadeus transfer offers into options_pool format"""
        formatted = []
        for idx, transfer in enumerate(transfers[:10]):  # Limit to 10 options
            vehicle = transfer.get("vehicle", {})
            price = transfer.get("price", {}).get("total", "0")
            currency = transfer.get("price", {}).get("currency", "THB")
            
            formatted.append({
                "id": f"transfer_{idx + 1}",
                "type": "transfer",
                "name": f"{vehicle.get('type', 'Transfer')} - {vehicle.get('category', 'Standard')}",
                "price": float(price) if isinstance(price, str) else price,
                "currency": currency,
                "vehicle_type": vehicle.get("type", ""),
                "capacity": vehicle.get("capacity", 0),
                "raw_data": transfer  # Keep original for booking
            })
        return formatted
    
    async def _execute_select_option(
        self,
        session: UserSession,
        payload: Dict[str, Any],
        action_log: ActionLog
    ):
        """Execute SELECT_OPTION action"""
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        option_index = payload.get("option_index", 0)
        
        if not slot_name:
            raise AgentException("SELECT_OPTION: Missing slot name")
        
        # Get segment
        segments = getattr(session.trip_plan, slot_name, [])
        if segment_index >= len(segments):
            raise AgentException(f"SELECT_OPTION: Segment index {segment_index} out of range")
        
        segment = segments[segment_index]
        
        # Check if option exists
        if option_index >= len(segment.options_pool):
            raise AgentException(f"SELECT_OPTION: Option index {option_index} out of range")
        
        # Select option
        segment.selected_option = segment.options_pool[option_index]
        segment.status = SegmentStatus.CONFIRMED
        
        action_log.add_action(
            "SELECT_OPTION",
            payload,
            f"Selected option {option_index} for {slot_name}[{segment_index}]"
        )
        session.update_timestamp()
    
    async def generate_response(
        self,
        session: UserSession,
        action_log: ActionLog,
        memory_context: str = ""
    ) -> str:
        """
        Phase 2: Generate response message in Thai
        
        Args:
            session: UserSession with current state
            action_log: Actions taken in Phase 1
            memory_context: Long-term memory about the user
            
        Returns:
            Response message in Thai
        """
        try:
            # Build prompt
            state_json = json.dumps(session.trip_plan.model_dump(), ensure_ascii=False, indent=2)
            action_log_json = json.dumps([a.model_dump() for a in action_log.actions], ensure_ascii=False, indent=2)
            
            prompt = f"""=== USER LONG-TERM MEMORY ===
{memory_context}

=== CURRENT STATE ===
{state_json}

=== ACTIONS TAKEN ===
{action_log_json}

=== INSTRUCTIONS ===
Generate a response message in Thai:
1. Summarize what was done (from action_log)
2. Check State for missing information
3. Ask next question if information is missing
4. If everything is complete, summarize the complete Trip Plan
5. Use USER MEMORY to personalize the response if relevant (e.g. if they like beach, mention it).

Respond in Thai text only (no JSON, no markdown)."""
            
            # Call LLM
            response_text = await self.llm.generate_content(
                prompt=prompt,
                system_prompt=RESPONDER_SYSTEM_PROMPT,
                temperature=settings.responder_temperature,
                max_tokens=2000
            )
            
            if not response_text or response_text.strip() == "":
                logger.warning("Responder LLM returned empty text, using fallback")
                agent_monitor.log_activity(session.session_id, session.user_id, "warning", "Responder returned empty text")
                return "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
                
            agent_monitor.log_activity(session.session_id, session.user_id, "response", "Final response generated", {"text_preview": response_text[:100]})
            return response_text
        
        except LLMException as e:
            logger.error(f"LLM error in responder: {e}", exc_info=True)
            # Safe fallback message
            return "ขออภัย ระบบกำลังใช้งานหนัก กรุณาลองใหม่อีกครั้งในสักครู่"
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            return "ขออภัย เกิดข้อผิดพลาดในการสร้างข้อความตอบกลับ กรุณาลองใหม่อีกครั้ง"
