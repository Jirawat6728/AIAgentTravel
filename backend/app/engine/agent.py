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
from app.services.llm import LLMService
from app.services.llm_production import get_production_llm, BrainType, ModelType
from app.services.memory import MemoryService
from app.services.travel_service import TravelOrchestrator, TravelSearchRequest
from app.services.data_aggregator import aggregator, StandardizedItem, ItemCategory
from app.core.exceptions import AgentException, LLMException
from app.core.logging import get_logger
from app.core.config import settings
from app.services.agent_monitor import agent_monitor
from app.engine.workflow_manager import WorkflowManager, OptionSelector
from app.engine.slot_manager import SlotManager
from app.engine.cost_tracker import cost_tracker, CostTracker
from app.engine.workflow_visualizer import workflow_visualizer, WorkflowVisualizer
from app.services.options_cache import get_options_cache
from app.engine.workflow_validator import get_workflow_validator, WorkflowStep
from app.services.mcp_server import MCPToolExecutor
# Agent Intelligence classes will be defined at the end of this file

logger = get_logger(__name__)

# ✅ Helper function to safely write debug logs
def _write_debug_log(data: dict):
    """Safely write debug log, creating directory if needed"""
    try:
        import os
        debug_log_path = r'c:\Users\Juins\Desktop\DEMO\AITravelAgent\.cursor\debug.log'
        debug_log_dir = os.path.dirname(debug_log_path)
        os.makedirs(debug_log_dir, exist_ok=True)
        with open(debug_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception:
        pass  # Silently ignore debug log errors

CONTROLLER_SYSTEM_PROMPT = """You are the "Brain" of a Travel Agent - Enhanced with AI Intelligence.
Your ONLY job is to decide the NEXT ACTION based on the User Input and Current State.
You DO NOT speak to the user. You output JSON ONLY.

🧠 INTELLIGENCE FEATURES:
- Smart Date Understanding: "พรุ่งนี้", "สงกรานต์", "สัปดาห์หน้า", "20 มกราคม 2568" (Buddhist Era) are automatically parsed
- Location Intelligence: Landmarks (e.g., "Siam Paragon") are resolved to cities
- Budget Advisory: Realistic budget estimates and warnings are provided
- Validation: Dates, guests, and budgets are validated automatically
- Flight Preferences: Understands cabin classes and flight types:
  * "ชั้นประหยัดพรีเมี่ยม" / "premium economy" / "พรีเมี่ยม" → cabin_class: "PREMIUM_ECONOMY"
  * "ชั้นประหยัด" / "economy" → cabin_class: "ECONOMY"
  * "ชั้นธุรกิจ" / "business" → cabin_class: "BUSINESS"
  * "บินตรง" / "direct" / "nonstop" / "ไม่ต่อเครื่อง" → direct_flight: true, non_stop: true

🔄 ENHANCED WORKFLOW (Based on AmadeusViewerPage Pattern - Step-by-Step Travel Planning):

**STEP 1: Keyword Extraction (Similar to /api/amadeus-viewer/extract-info)**
Extract key information from user input using LLM intelligence:
   - **Origin** (ต้นทาง): City, landmark, or address (e.g., "Bangkok", "Siam Paragon")
   - **Destination** (ปลายทาง): City, landmark, or address (e.g., "Seoul", "Myeongdong")
   - **Dates**: start_date, end_date (support formats: "20 มกราคม 2568", "2025-01-20", "พรุ่งนี้")
   - **Waypoints** (จุดแวะ): Places to visit along the route (e.g., "Kyoto", "Osaka") - can be multiple
   - **Attractions/Tourist Spots** (สถานที่ท่องเที่ยว): Specific POIs/landmarks - IMPORTANT for hotel search accuracy
     * Examples: "Gyeongbokgung", "N Seoul Tower", "วัดพระแก้ว", "Eiffel Tower", "Myeongdong", "Kiyomizu-dera"
     * Store in accommodation.requirements["attractions"] or ["near_attractions"]
   - **Hotel Area** (ย่านโรงแรม): Specific neighborhood/area for hotel search (e.g., "Shinjuku", "Shibuya")
   - **Preferences**: cabin class, direct flight, budget, guests, etc.

**STEP 2: Route Planning (Google Maps MCP - Like AmadeusViewerPage MapDisplay)**
Use "plan_route" MCP tool to determine:
   - **Origin → Destination route**: Calculate real Google Maps production route
   - **Nearest Airports**: Find nearest airport IATA codes for origin and destination
     * Marker A = Origin Airport (e.g., BKK/Suvarnabhumi)
     * Marker B = Destination Airport (e.g., ICN/Incheon)
   - **Route details**: Distance (km), duration, route type (ground/flight)
   - **Waypoints processing**: If waypoints provided, plan route: Origin → Waypoint1 → Waypoint2 → Destination
   - **Ground routes**: Calculate origin → origin_airport and destination_airport → destination using Google Maps Directions

**STEP 3: Transportation Decision (Based on Route Planning)**
Determine transportation methods based on route analysis:
   - **Flight** (เครื่องบิน): Distance >500km, airports available, or international routes
   - **Car** (รถยนต์): Distance <500km, road trip, or flexible timing
   - **Train** (รถไฟ): City-to-city routes 100-500km, high-speed rail available
   - **Bus** (รถบัส): Economical short-medium routes <300km
   - **Boat** (เรือ): Island destinations, coastal routes, or ferry routes

**STEP 4: Amadeus MCP Search (Concurrent - Like /api/amadeus-viewer/search)**
After determining transportation, search Amadeus MCP tools concurrently:
   - **Flights** (via "search_flights"): If flight recommended, search both outbound and inbound
   - **Hotels** (via "search_hotels"): 
     * Use destination + attractions for location (e.g., "Seoul, Myeongdong")
     * Or use hotel_area if specified
     * Search near attractions/tourist spots for better accuracy
   - **Transfers** (via "search_transfers" or "search_transfers_by_geo"):
     * Origin → Origin Airport (if flight)
     * Destination Airport → Destination (if flight)
     * Between waypoints (if multi-city)
   - **Activities** (via "search_activities"): Optional, if user mentions activities/tours

**STEP 5: Option Organization (Prioritize by Category)**
After receiving raw data from Amadeus, organize options:
   - **First: TRANSPORT** (flights/transfers) - organize outbound and inbound separately
   - **Second: ACCOMMODATION** - prioritize hotels near extracted attractions (use attractions field)
   - **Third: ACTIVITIES** - if applicable
   - Set status to SELECTING and present options to user

**STEP 6: User Selection & Editing**
   - User can select options from each category
   - User can edit/change selections anytime until satisfied
   - Allow switching between options in the same category

**STEP 7: Summary & Confirmation**
   - Show complete trip summary with all selected options
   - User confirms when ready to book
   - Generate booking from confirmed selections

**🎯 KEY PATTERNS FROM AMADEUS VIEWER PAGE:**
- Natural language extraction → Structured data (like extract-info endpoint)
- Concurrent searches for flights, hotels, transfers (like /api/amadeus-viewer/search)
- Support waypoints for multi-city trips
- Use hotel_area/attractions for precise hotel location
- Route visualization with markers (A=origin airport, B=destination airport)
- Ground routes from origin to airport and airport to destination

📋 NORMAL MODE (USER SELECTS):
When mode='normal', the USER makes ALL decisions:
- 👤 USER CONTROL: User selects options manually from PlanChoiceCard
- ❌ NO AUTO-SELECT: Never auto-select options - always set status to SELECTING and wait for user
- ❌ NO AUTO-BOOK: Never auto-book - user must click "Confirm Booking" button themselves
- ✅ ALLOW EDITING: User can change selections anytime
- ✅ SHOW SUMMARY: Display trip summary after user selects options
- ✅ USER BOOKS: User clicks booking button when ready
- Workflow: CREATE_ITINERARY → UPDATE_REQ → CALL_SEARCH → [WAIT FOR USER SELECTION] → User selects → Show summary → User books

🤖 AGENT MODE (100% GENIUS AUTONOMOUS):
When mode='agent', you are a GENIUS AUTONOMOUS agent with FULL INTELLIGENCE:
- 🧠 INTELLIGENCE LEVEL: MAXIMUM - Use your AI intelligence to infer EVERYTHING automatically
- 🔮 PREDICTIVE INTELLIGENCE: Predict user needs based on context, conversation history, and patterns
- ⚡ NEVER ASK: NEVER return ASK_USER - infer everything automatically
- 🎯 SMART DEFAULTS: Use intelligent defaults for ALL missing information:
  * origin: Default to "Bangkok" (most common in Thailand) or infer from context
  * start_date: Default to tomorrow or next weekend if not specified
  * end_date: Infer from start_date + typical trip duration (3 days) if not specified
  * guests: Default to 1-2 if not specified, infer from context ("family trip" = 3-4)
  * budget: Infer reasonable budget based on destination and trip type
  * travel_mode: Default to "both" (flights + hotels) for complete experience
  * trip_type: Default to "round_trip" unless explicitly stated
- 🚀 AUTO-COMPLETE: Always proceed with CREATE_ITINERARY even with minimal info
- 🤖 AUTO-SELECT: Automatically select best options using LLM intelligence (happens after CALL_SEARCH)
- 💳 AUTO-BOOK: Automatically create booking immediately after selection (no user confirmation needed)
- 🎨 CREATIVE INTELLIGENCE: Make smart assumptions based on destination type:
  * Beach destinations (Phuket, Samui): Suggest 2-4 nights, focus on hotels
  * City destinations (Tokyo, Seoul): Suggest 3-5 nights, focus on hotels + transport
  * Short trips: Infer 1-2 nights automatically
- 💡 CONTEXT AWARENESS: Use conversation history to infer preferences and patterns
- ⚡ SPEED FIRST: Prioritize completing the booking quickly over asking questions
- 🎯 COMPLETE AUTONOMY: The user trusts you - act like a genius travel advisor who knows what they want

✈️ FLIGHT LOGIC & AIRPORT ARRIVAL (CRITICAL):
- If the trip involves a flight to a destination (e.g., Bangkok -> Phuket):
  1. The first ground location MUST be the destination airport (e.g., Phuket International Airport).
  2. You MUST include a transfer from the airport to the first hotel or activity.
  3. Do NOT start the itinerary directly at the hotel/activity without landing at the airport first.
  4. Ensure the sequence is: Origin -> Flight -> Destination Airport -> Transfer -> Hotel/Activity.

📅 DATE INTELLIGENCE:
- If user says "3 วัน" (3 days), "2 คืน" (2 nights), etc., ALWAYS pass the "days" field:
  - "3 วัน" (stay for 3 days) → "days": 3
  - "2 คืน" (stay for 2 nights) → "days": 2
  - CRITICAL: DO NOT calculate end_date yourself! Just pass "days": X and the system will calculate automatically
  - Example: start_date="2026-01-30", "days": 3 → system calculates end_date="2026-02-02" (NOT 2026-02-01)
- For multi-day trips, ALWAYS set trip_type="round_trip" and provide "days" field (NOT end_date)
- Example: "อยากไปสมุย 3 วัน" with start_date="2025-01-30" → payload: {"start_date": "2025-01-30", "days": 3}, trip_type="round_trip"

Current Date: 2025-01-08

Trip Plan Structure:
- travel:
  - mode: "flight_only" | "car_only" | "both"
  - trip_type: "one_way" | "round_trip" (default: round_trip)
  - flights: 
    - outbound: [List of Segments]
    - inbound: [List of Segments]
  - ground_transport: [List of Segments]
- accommodation:
  - segments: [List of Segments]

Segment Statuses: PENDING, SEARCHING, SELECTING, CONFIRMED

Available Actions:
1. CREATE_ITINERARY: Use this for NEW trip requests. Automatically creates slots/segments.
   Payload: { "destination": str, "start_date": str, "end_date": str (optional for one_way), "travel_mode": "flight_only"|"car_only"|"both", "trip_type": "one_way"|"round_trip" (default round_trip), "guests": int, "origin": str (optional), "budget": int (optional), "focus": ["flights", "hotels", "transfers"] (optional) }
   NOTE: For multi-city trips, provide cities separated by ' and ' or ' และ ' in "destination" (e.g., "Kyoto and Osaka"). Accommodation will be split automatically.
2. UPDATE_REQ: Extract details from user input to update requirements of EXISTING segments.
   Payload: { "slot": "flights_outbound" | "flights_inbound" | "ground_transport" | "accommodation", "segment_index": int, "updates": dict, "clear_existing": bool }
   Flight updates can include:
   - "cabin_class": "ECONOMY" | "PREMIUM_ECONOMY" | "BUSINESS" | "FIRST"
   - "direct_flight": true | false (for non-stop flights only)
   - "preferences": "direct" | "nonstop" | "no_connections" (Thai: "บินตรง", "ไม่ต่อเครื่อง")
   Hotel/Accommodation updates can include:
   - "location": str (city name or address)
   - "attractions": List[str] or str (tourist spots/landmarks - use these as keywords for more accurate hotel search near attractions)
   - "near_attractions": List[str] or str (alternative field name for attractions)
3. CALL_SEARCH: If a segment has ALL required fields and NO options, search for it.
   Payload: { "slot": "flights_outbound" | "flights_inbound" | "ground_transport" | "accommodation", "segment_index": int }
4. SELECT_OPTION: If user selects an option.
   Payload: { "slot": "flights_outbound" | "flights_inbound" | "ground_transport" | "accommodation", "segment_index": int, "option_index": int }
   IMPORTANT: option_index is 0-based. If user says "เลือกช้อยส์ 1" (display number 1), use option_index=0. "เลือกช้อยส์ 2" = option_index=1, etc.
5. ASK_USER: If information is missing.
6. BATCH: To perform multiple actions in one turn.

RULES:
- OUTPUT MUST BE VALID JSON ONLY. NO MARKDOWN. NO EXPLANATION.
- PRIORITIZE "CREATE_ITINERARY" for high-level trip requests.
  - If user says "Plan a trip", use default focus (all).
  - If user says "Find flights", use focus=["flights"].
  - If user says "Find hotel", use focus=["hotels"].
- PRIORITIZE "BATCH" for subsequent updates.
- If user changes CRITICAL details (Date, Location), use UPDATE_REQ. This AUTOMATICALLY clears old options and triggers re-search.
- If user explicitly asks to "search again" or "find new options" WITHOUT changing details, use UPDATE_REQ with "clear_existing": true and empty updates.
- If requirements are complete for a slot and NO options exist, TRIGGER CALL_SEARCH.

=== FEW-SHOT EXAMPLES (LEARN FROM THESE) ===

Scenario 1: Full Trip Planning
User: "Plan a family trip to Phuket for 3 days, 2 nights during Songkran (April 13-15). 2 adults, 1 child. Need everything."
Output:
{
  "thought": "User wants a full trip to Phuket during Songkran. I will create a full itinerary with round trip flights.",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Phuket",
    "start_date": "2025-04-13",
    "end_date": "2025-04-15",
    "travel_mode": "both",
    "trip_type": "round_trip",
    "guests": 3,
    "origin": "Bangkok",
    "focus": ["flights", "hotels", "transfers"]
  }
}

Scenario 1b: Multi-Day Trip (Days Mentioned)
User: "อยากไปสมุย 3 วัน"
Output:
{
  "thought": "User wants a 3-day trip to Samui. I will pass 'days': 3 to let the system calculate end_date automatically (start_date + 3 days).",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Samui",
    "start_date": "2025-01-30",
    "travel_mode": "both",
    "trip_type": "round_trip",
    "guests": 1,
    "origin": "Bangkok",
    "focus": ["flights", "hotels", "transfers"],
    "days": 3
  }
}
CRITICAL: DO NOT calculate end_date yourself! Just pass "days": 3 and let the system calculate it automatically.
This ensures correct calculation: start_date="2025-01-30" + 3 days = end_date="2025-02-02" (NOT "2025-02-01")

Scenario 2: Flight Only (One Way)
User: "Find a one-way flight to Chiang Mai on Feb 20."
Output:
{
  "thought": "User specifically asked for one-way flights.",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Chiang Mai",
    "start_date": "2025-02-20",
    "travel_mode": "flight_only",
    "trip_type": "one_way",
    "guests": 1,
    "origin": "Bangkok",
    "focus": ["flights"]
  }
}

Scenario 3: Hotel Only
User: "Book a hotel in Tokyo near Shinjuku for tonight."
Output:
{
  "thought": "User needs a hotel in a specific area (Shinjuku, Tokyo) for tonight.",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Shinjuku, Tokyo",
    "start_date": "2025-01-08",
    "end_date": "2025-01-09",
    "travel_mode": "both",
    "guests": 1,
    "focus": ["hotels"]
  }
}

Scenario 4: Modifying Dates (Re-search)
User: "Actually, can we move the trip to next week? Feb 27 instead."
Output:
{
  "thought": "User wants to change the date. I must update requirements and clear existing options to trigger a new search.",
  "action": "BATCH",
  "batch_actions": [
    {
      "action": "UPDATE_REQ",
      "payload": { "slot": "flights", "segment_index": 0, "updates": { "departure_date": "2025-02-27" }, "clear_existing": true }
    },
    {
      "action": "UPDATE_REQ",
      "payload": { "slot": "flights", "segment_index": 1, "updates": { "departure_date": "2025-03-01" }, "clear_existing": true }
    },
    {
      "action": "UPDATE_REQ",
      "payload": { "slot": "accommodations", "segment_index": 0, "updates": { "check_in": "2025-02-27", "check_out": "2025-03-01" }, "clear_existing": true }
    }
  ]
}

Scenario 5: Adding Requirements
User: "I want a hotel with a swimming pool and free breakfast."
Output:
{
  "thought": "User added hotel preferences. I will update the accommodation requirements.",
  "action": "UPDATE_REQ",
  "payload": {
    "slot": "accommodations",
    "segment_index": 0,
    "updates": { "amenities": "swimming pool, breakfast" },
    "clear_existing": true
  }
}

Scenario 6: Selecting an Option
User: "I like the first flight option." or "เลือกช้อยส์ 1"
Output:
{
  "thought": "User selected option 1 (display number 1 = index 0).",
  "action": "SELECT_OPTION",
  "payload": {
    "slot": "flights_outbound",
    "segment_index": 0,
    "option_index": 0
  }
}
Note: User says "เลือกช้อยส์ 1" means option_index=0 (1-based display → 0-based index). "เลือกช้อยส์ 2" = option_index=1, etc.

Scenario 7: Road Trip with Budget
User: "Plan a trip from Siam Paragon to Laem Phromthep. No flights, I want to go by car. Budget under 10000 THB."
Output:
{
  "thought": "User wants a road trip (car_only) from a specific landmark to another. Budget constrained.",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Laem Phromthep",
    "origin": "Siam Paragon",
    "start_date": "2025-01-09",
    "travel_mode": "car_only",
    "guests": 1,
    "budget": 10000,
    "focus": ["hotels", "transfers"]
  }
}

Example JSON Output (Specific Search):
{
  "thought": "User wants to find flights to Tokyo only.",
  "action": "CREATE_ITINERARY",
  "payload": {
    "destination": "Tokyo",
    "start_date": "2025-05-01",
    "end_date": "2025-05-05",
    "travel_mode": "flight_only",
    "guests": 2,
    "origin": "Bangkok",
    "focus": ["flights"]
  }
}
"""

RESPONDER_SYSTEM_PROMPT = """You are the Voice of the Travel Agent AI.
Generate a helpful, polite, and proactive response message in Thai.

CRITICAL RULES:
1. Use Thai language ONLY.
2. READ THE ACTION_LOG: Acknowledge what was done.
3. **ALWAYS USE COMPLETE CITY NAMES**: When mentioning origin or destination cities, ALWAYS use the FULL name:
   - ✅ "กรุงเทพฯ - ภูเก็ต" (NOT "กรุงเทพฯ - ภู")
   - ✅ "กรุงเทพฯ - เชียงใหม่" (NOT "กรุงเทพฯ - เชียง")
   - ✅ "กรุงเทพฯ - สมุย" (NOT "กรุงเทพฯ - สมุ")
   - ✅ "กรุงเทพฯ - โตเกียว" (NOT "กรุงเทพฯ - โต")
   - NEVER truncate or abbreviate city names in your response
4. If UPDATE_REQ was performed, mention the specific details extracted.
5. If CALL_SEARCH was performed:
   - Mention options found.
   - 📋 NORMAL MODE: If options_pool exists, tell user to choose from PlanChoiceCard ("กรุณาเลือกตัวเลือกที่ต้องการจากรายการด้านล่างค่ะ").
   - 🤖 AGENT MODE: If options_pool exists, say "กำลังเลือกตัวเลือกที่ดีที่สุดให้อัตโนมัติ..." (don't ask user to choose).
   - If NO options found for a slot (e.g. flights), STATE CLEARLY that you searched but found nothing.
   - **IMPORTANT**: If NO results and the date is very close (today/tomorrow) or passed, SUGGEST changing the date ("ลองเลื่อนวันเดินทางไหมคะ") because flights/hotels might be full or closed.
   - However, ALSO mention that same-day booking is allowed if available ("แต่ถ้ายังมีว่าง ก็สามารถจองภายในวันได้ค่ะ").
5. CHECK DATA COMPLETENESS:
   - Before summarizing the trip as "Ready" or "Complete", check if ALL requested slots (Flights, Hotels) are CONFIRMED.
   - If ANY slot is missing or pending (e.g. Flight not found), DO NOT imply the trip is fully booked/ready.
   - Instead, say: "I have confirmed [Item A], but for [Item B], I need [Action/Input]."
6. Be proactive: Suggest next steps.
7. NEVER say "no information" if actions were taken.

📋 NORMAL MODE RULES (USER SELECTS):
- ✅ If options_pool exists, say: "พบ X ตัวเลือก - กรุณาเลือกตัวเลือกที่ต้องการจากรายการด้านล่างค่ะ"
- ✅ If user selects option, say: "ได้เลือก [item] แล้ว - สามารถแก้ไขได้หากต้องการ"
- ✅ If all options selected, say: "พร้อมจองแล้ว - กรุณากดปุ่ม 'Confirm Booking' เพื่อดำเนินการจอง"
- ✅ Always remind user they can edit selections: "สามารถแก้ไขตัวเลือกได้ตลอดเวลาค่ะ"
- ❌ NEVER auto-select or auto-book - user must do it manually
- ✅ Show trip summary after user selects options

📋 NORMAL MODE RULES (USER SELECTS):
- ✅ If options_pool exists, say: "พบ X ตัวเลือก - กรุณาเลือกตัวเลือกที่ต้องการจากรายการด้านล่างค่ะ"
- ✅ If user selects option, say: "ได้เลือก [item] แล้ว - สามารถแก้ไขได้หากต้องการ"
- ✅ If all options selected, say: "พร้อมจองแล้ว - กรุณากดปุ่ม 'Confirm Booking' เพื่อดำเนินการจอง"
- ✅ Always remind user they can edit: "สามารถแก้ไขตัวเลือกได้ตลอดเวลาค่ะ"
- ✅ Show trip summary after user selects options
- ❌ NEVER auto-select or auto-book - user must do it manually

🤖 AGENT MODE RULES (100% AUTONOMOUS - NEVER ASK):
- ❌ NEVER ask user to select options - Agent Mode selects automatically
- ❌ NEVER say "กรุณาเลือก" or "ต้องการให้เลือก" - Agent does it automatically
- ❌ NEVER ask "ต้องการให้จองเลยไหม" - Agent books automatically
- ❌ NEVER ask "บอกดิฉันได้เลย" or any question - Agent infers everything automatically
- ✅ If you see AGENT_SMART_SELECT actions, say: "ดิฉันได้เลือก [item] ให้แล้ว (AI มั่นใจ X%)"
- ✅ If you see AUTO_BOOK actions, say: "✅ จองเสร็จแล้วนะ ไปจ่ายตังด้วย! รายละเอียดอยู่ใน My Bookings"
- ✅ If options_pool exists but no selected_option yet, say: "กำลังเลือกตัวเลือกที่ดีที่สุดให้อัตโนมัติ..."
- ✅ If selected_option exists, say: "ได้เลือก [item] แล้ว" (don't ask for confirmation)
- ✅ If Agent Mode is active, ALWAYS emphasize autonomy: "ดิฉันได้ดำเนินการให้อัตโนมัติแล้วค่ะ"
- ✅ If booking status is "confirmed", mention that booking is already confirmed and ready
- ✅ Focus on WHAT WAS DONE, not what needs to be done

🚫 CRITICAL: In Agent Mode, NEVER end with questions like:
- "คุณต้องการให้เลือก..."
- "กรุณาเลือก..."
- "ต้องการให้จองเลยไหม..."
- "บอกดิฉันได้เลย..."
- "ต้องการข้อมูลเพิ่มเติม..."

✅ Instead, say:
- "ดิฉันได้เลือกให้แล้ว"
- "กำลังจองให้อัตโนมัติ..."
- "จองเสร็จแล้ว"

🛠️ ADMIN FEATURES - AMADEUS VIEWER:
- 📊 Amadeus Viewer is an ADMIN-ONLY page for comprehensive travel data exploration
- 🌍 Features:
  * Natural language input to extract travel details (origin, destination, dates, waypoints, hotel area)
  * Searches for round-trip flights, hotels, transfers (car, bus, train, boat), and points of interest along the route
  * Displays Google Maps with routing and markers (origin=blue, destination=red, hotel=green, checkpoints=yellow)
  * Shows results in Google Flights-style layout with detailed flight information (duration, connections, CO2 emissions, airline names)
  * Displays return flights, accommodation options, all transfer types, and places of interest
- 🎯 When to mention Amadeus Viewer:
  * If user is admin and asks for detailed search/exploration of travel options
  * If user wants to see comprehensive data without booking
  * If user wants to see map visualization of routes and multiple options
  * Example: "คุณสามารถใช้ Amadeus Viewer (Admin) เพื่อดูข้อมูลการเดินทางแบบละเอียด พร้อมแผนที่และตัวเลือกมากมายได้ค่ะ"
- ❌ Do NOT mention Amadeus Viewer to non-admin users

Tone: Professional, friendly, helpful, proactive, confident, and AUTONOMOUS."""


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
        # ✅ Intent-Based LLM Service with tool calling (Gemini)
        try:
            from app.services.intent_llm import IntentBasedLLM
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
        # ✅ Initialize Workflow Manager, Slot Manager, Cost Tracker, and Visualizer
        self.workflow_manager = WorkflowManager()
        self.slot_manager = SlotManager()
        self.cost_tracker = cost_tracker
        self.visualizer = workflow_visualizer
        self.workflow_validator = get_workflow_validator()
        # ✅ Initialize MCP Tool Executor for Google Maps and Amadeus
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
        logger.info("TravelAgent initialized with Brain/Memory support, TravelOrchestrator, Workflow Management, and MCP Tools")
    
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
            
            # Phase 1: Controller Loop (Think & Act)
            if status_callback:
                mode_text = "โหมด Agent" if mode == "agent" else "โหมดปกติ"
                await status_callback("thinking", f"กำลังวางแผนทริป ({mode_text})...", "controller_start")
                
            action_log = await self.run_controller(session, user_input, status_callback, memory_context, user_profile_context, mode=mode)
            
            # Save state after Phase 1
            await self.storage.save_session(session)
            
            # Phase 2: Responder (Speak)
            if status_callback:
                await status_callback("speaking", "🤖 Agent กำลังสรุปคำตอบ...", "responder_start")
                
            response_message = await self.generate_response(session, action_log, memory_context, user_profile_context, mode=mode)
            
            # ✅ CRITICAL: Ensure response_message is never None or empty
            if not response_message or not response_message.strip():
                logger.error(f"generate_response returned empty message for session {session.session_id}")
                response_message = "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
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
            
            if context_parts:
                return "\n".join(["=== USER PROFILE ==="] + context_parts)
            
            return ""
        except Exception as e:
            logger.warning(f"Failed to get user profile context for {user_id}: {e}")
            return ""
    
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
        # ✅ OPTIMIZED FOR 1.5-MINUTE COMPLETION: Reduce iterations to 2 for faster response
        max_iterations = min(settings.controller_max_iterations, 2)  # ✅ Reduced from 3 to 2 for 1.5-minute target
        
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
        
        # 🆕 WORKFLOW VISUALIZATION: Log initial state
        try:
            initial_viz = self.visualizer.get_compact_status(session.trip_plan)
            logger.info(f"[WORKFLOW] Initial: {initial_viz}")
        except Exception as e:
            logger.warning(f"Failed to visualize initial workflow: {e}")
        
        for iteration in range(max_iterations):
            # ✅ SAFETY: If we've reached the limit, force stop
            if iteration >= max_iterations:
                logger.warning(
                    f"[CONTROLLER] Forced stop at iteration {iteration + 1} (limit: {max_iterations})",
                    extra={"session_id": session.session_id, "user_id": session.user_id}
                )
                break
            logger.info(f"Controller Loop iteration {iteration + 1}/{max_iterations}", 
                       extra={"session_id": session.session_id, "user_id": session.user_id})
            
            if status_callback:
                await status_callback("thinking", f"🤖 Agent กำลังวิเคราะห์และวางแผนทริป...", f"controller_iter_{iteration + 1}")
            
            try:
                # Get current state as JSON
                state_json = json.dumps(session.trip_plan.model_dump(), ensure_ascii=False, indent=2)
                
                # Call Controller LLM (with session info for cost tracking)
                try:
                    action = await self._call_controller_llm(
                        state_json, 
                        user_input, 
                        action_log, 
                        memory_context, 
                        user_profile_context, 
                        mode=mode,
                        session_id=session.session_id,
                        user_id=session.user_id
                    )
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
                                        "guests": payload.get("guests") or 2,
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
                    
                    # ✅ Validate search results
                    for result in results:
                        if isinstance(result, Exception):
                            logger.error(f"Search task failed: {result}")
                    
                    # ✅ Validate segment states after search
                    for slot_name, segment, idx in self.slot_manager.get_all_segments(session.trip_plan):
                        self.slot_manager.ensure_segment_state(segment, slot_name)
                    
                    # ✅ Agent Mode: Auto-select and auto-book immediately after search completes
                    if mode == "agent":
                        if status_callback:
                            await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด...", "agent_auto_select_immediate")
                        
                        logger.info("Agent Mode: Search completed, immediately auto-selecting options...")
                        await self._auto_select_and_book(session, action_log, status_callback)
                        
                        # Save session after auto-select to persist state
                        await self.storage.save_session(session)
                
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
            
            if has_options_to_select:
                if status_callback:
                    await status_callback("acting", "🤖 Agent กำลังเลือกช้อยส์ที่ดีที่สุด (รอบสุดท้าย)...", "agent_auto_select_final")
                
                # ✅ Validate workflow before auto-select
                workflow_state = self.workflow_manager.analyze_workflow(session.trip_plan)
                logger.info(f"Agent Mode: Final auto-select check - Workflow stage={workflow_state.stage.value}, progress={workflow_state.progress_percentage:.1f}%")
                
                await self._auto_select_and_book(session, action_log, status_callback)
                
                # ✅ Validate workflow after auto-select
                workflow_state_after = self.workflow_manager.analyze_workflow(session.trip_plan)
                logger.info(f"Agent Mode: After final auto-select, stage={workflow_state_after.stage.value}, progress={workflow_state_after.progress_percentage:.1f}%")
                
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
        
        # 🆕 FINAL WORKFLOW VISUALIZATION: Log final state
        try:
            final_viz = self.visualizer.get_compact_status(session.trip_plan)
            progress_bar = self.visualizer.create_progress_bar(session.trip_plan)
            logger.info(f"[WORKFLOW] Final: {final_viz}")
            logger.info(f"[WORKFLOW] Progress: {progress_bar}")
            
            # Log to agent monitor
            agent_monitor.log_activity(
                session.session_id,
                session.user_id,
                "workflow",
                f"Workflow completed: {final_viz}",
                self.visualizer.export_to_dict(session.trip_plan)
            )
        except Exception as e:
            logger.warning(f"Failed to visualize final workflow: {e}")
        
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
    
    async def _call_controller_llm(
        self,
        state_json: str,
        user_input: str,
        action_log: ActionLog,
        memory_context: str = "",
        user_profile_context: str = "",
        mode: str = "normal",  # ✅ Pass mode to LLM
        session_id: str = "unknown",  # 🆕 For cost tracking
        user_id: str = "unknown"  # 🆕 For cost tracking
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
            current_date = datetime.now().strftime("%Y-%m-%d")
            system_prompt_with_date = CONTROLLER_SYSTEM_PROMPT.replace("Current Date: 2025-01-08", f"Current Date: {current_date}")
            
            prompt_parts = [
                user_profile_context if user_profile_context else "",
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
   - Missing guests? Default to 1-2 (infer from "family" = 3-4, "couple" = 2)
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
   - If user says "ไปภูเก็ต" → CREATE_ITINERARY with: destination="Phuket", start_date=tomorrow, end_date=tomorrow+3, guests=2, origin="Bangkok", travel_mode="both"
   - If user says "ญี่ปุ่น" → CREATE_ITINERARY with: destination="Tokyo", start_date=next_weekend, end_date=next_weekend+5, guests=2, origin="Bangkok", travel_mode="both"
   - If user says "เกาหลี 5 วัน" → CREATE_ITINERARY with: destination="Seoul", start_date=tomorrow, end_date=tomorrow+5, guests=2, origin="Bangkok", travel_mode="both"

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
                prompt_parts.append("   - Guests: Not specified → 2 (default couple/friends)")
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
            start_time = asyncio.get_event_loop().time()
            if self.production_llm:
                # Determine complexity
                complexity = "complex" if mode == "agent" else "moderate"
                data = await self.production_llm.controller_generate(
                    prompt=prompt,
                    system_prompt=system_prompt_with_date,
                    complexity=complexity
                )
                model_used = "gemini-2.5-pro"  # Default model for controller
                
                # #region agent log
                import json as json_module
                _write_debug_log({"sessionId":"debug-session","hypothesisId":"B,C","location":"agent.py:1240","message":"After production_llm.controller_generate","data":{"model_used":model_used,"data_type":str(type(data)),"has_thought":"thought" in data if isinstance(data, dict) else False,"has_action":"action" in data if isinstance(data, dict) else False,"data_keys":list(data.keys()) if isinstance(data, dict) else None},"timestamp":__import__('time').time()*1000})
                # #endregion
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
                end_time = asyncio.get_event_loop().time()
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
            
            # #region agent log
            import json as json_module
            _write_debug_log({"sessionId":"debug-session","hypothesisId":"A","location":"agent.py:1257","message":"Raw LLM data received","data":{"data_type":str(type(data)),"data_exists":data is not None,"is_dict":isinstance(data, dict),"has_thought":"thought" in data if isinstance(data, dict) else False,"has_action":"action" in data if isinstance(data, dict) else False,"data_preview":str(data)[:500] if data else None},"timestamp":__import__('time').time()*1000})
            # #endregion
            
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
                            "guests": 2,
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
            
            # #region agent log
            _write_debug_log({"sessionId":"debug-session","hypothesisId":"A,D","location":"agent.py:1284","message":"Before self-correction check","data":{"has_action":"action" in data,"has_thought":"thought" in data,"keys":list(data.keys()),"action_value":data.get("action"),"thought_value":data.get("thought")},"timestamp":__import__('time').time()*1000})
            # #endregion
            
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
                        "guests": 2,
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

            # #region agent log
            _write_debug_log({"sessionId":"debug-session","hypothesisId":"A","location":"agent.py:1309","message":"Right before ControllerAction validation","data":{"has_thought":"thought" in data,"thought_value":data.get("thought"),"has_action":"action" in data,"action_value":data.get("action"),"all_keys":list(data.keys()),"data_dump":str(data)[:300]},"timestamp":__import__('time').time()*1000})
            # #endregion

            # Validate and create ControllerAction
            action = ControllerAction(**data)
            
            # ✅ Agent Mode: ALWAYS override ASK_USER - never ask user in Agent Mode
            if mode == "agent" and action.action == "ASK_USER":
                logger.info("Agent Mode: Overriding ASK_USER - Agent Mode never asks user, inferring everything automatically")
                # Always create itinerary with intelligent defaults
                action = ControllerAction(
                    thought="Agent Mode: Overriding ASK_USER - inferring all missing information automatically",
                    action="CREATE_ITINERARY",
                    payload={
                        "destination": user_input or "Bangkok",  # Parse from input or default
                        "start_date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),  # Tomorrow
                        "end_date": (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d"),  # 3 nights
                        "guests": 2,  # Default
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
                        "guests": 2,
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
                        "guests": 2,
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
        
        Args:
            user_input: Original user input for fallback extraction
        """
        # ✅ Validate workflow step
        current_step = self.workflow_validator.get_current_workflow_step(session.trip_plan)
        is_allowed, error_msg = self.workflow_validator.validate_action_allowed(
            "CREATE_ITINERARY",
            current_step,
            session.trip_plan
        )
        if not is_allowed and error_msg:
            logger.warning(f"CREATE_ITINERARY validation failed: {error_msg}")
            action_log.add_action("VALIDATION_ERROR", {"action": "CREATE_ITINERARY", "error": error_msg}, error_msg)
        destination = payload.get("destination")
        start_date = payload.get("start_date")
        end_date = payload.get("end_date")
        travel_mode_str = payload.get("travel_mode", "both").lower()
        guests = payload.get("guests", 1)
        origin = payload.get("origin", "Bangkok") # Default to BKK if not specified
        budget = payload.get("budget") # Total budget
        focus = payload.get("focus", ["flights", "hotels", "transfers"]) # Default to all
        
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
        
        # ✅ STEP 2: Route Planning using Google Maps MCP
        route_plan = None
        origin_airport_iata = None
        dest_airport_iata = None
        recommended_transport = []
        
        if self.mcp_executor and origin and destination:
            try:
                logger.info(f"🗺️ Planning route from {origin} to {destination} using Google Maps...")
                # ✅ Add timeout for route planning (10s max for 1.5-minute completion)
                route_result = await asyncio.wait_for(
                    self.mcp_executor.execute_tool(
                        "plan_route",
                        {
                            "origin": origin,
                            "destination": destination,
                            "travel_mode": "driving"  # Default, can be changed based on distance
                        }
                    ),
                    timeout=10.0  # ✅ Route planning timeout: 10s max
                )
                
                if route_result.get("success") and route_result.get("route"):
                    route_plan = route_result["route"]
                    origin_airport_iata = route_plan.get("origin", {}).get("nearest_airport")
                    dest_airport_iata = route_plan.get("destination", {}).get("nearest_airport")
                    recommended_transport = route_plan.get("recommended_transportation", [])
                    distance_km = route_plan.get("distance_km", 0)
                    
                    logger.info(f"✅ Route planned: {distance_km} km, Origin Airport: {origin_airport_iata}, Dest Airport: {dest_airport_iata}")
                    logger.info(f"✅ Recommended transport: {recommended_transport}")
                    
                    # ✅ Use airport IATA codes if found
                    if origin_airport_iata:
                        flight_origin = origin_airport_iata
                        logger.info(f"✅ Using origin airport IATA: {flight_origin}")
                    if dest_airport_iata:
                        flight_destination = dest_airport_iata
                        logger.info(f"✅ Using destination airport IATA: {flight_destination}")
                    
                    # ✅ Store route plan in action_log for reference
                    action_log.add_action(
                        "ROUTE_PLANNING",
                        {"origin": origin, "destination": destination},
                        f"Route planned: {distance_km} km, airports: {origin_airport_iata}→{dest_airport_iata}, transport: {recommended_transport}"
                    )
                else:
                    logger.warning(f"Route planning failed or returned no route: {route_result}")
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ Route planning timed out after 10s - continuing without route plan")
                # Continue without route plan - fallback to original logic
            except Exception as e:
                logger.warning(f"Route planning error (non-fatal): {e}", exc_info=True)
                # Continue without route plan - fallback to original logic
        
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
                "adults": guests
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
            session.trip_plan.travel.flights.outbound.append(outbound)
            
            # Return (Default behavior: Always add return flight unless explicitly one_way OR no end_date)
            if trip_type == "round_trip" and end_date:
                return_flight = Segment()
                return_flight.requirements = {
                    "origin": flight_dest_code,  # Use airport IATA from route planning
                    "destination": flight_origin_code,  # Use airport IATA from route planning
                    "departure_date": self._normalize_date(end_date),
                    "adults": guests
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
                session.trip_plan.travel.flights.inbound.append(return_flight)

        # 2. Setup Accommodation (only if in focus)
        if "hotels" in focus:
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
                                "guests": guests
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
                            "guests": guests
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
                        "guests": guests
                    }
                    session.trip_plan.accommodation.segments.append(acc_segment)
        
        # 3. Setup Ground Transport (if in focus)
        if "transfers" in focus:
            if travel_mode == TravelMode.BOTH:
                # Airport Transfer (Arrival)
                transfer_arr = Segment()
                transfer_arr.requirements = {
                    "origin": f"{destination} Airport",
                    "destination": "Hotel in " + destination,
                    "date": self._normalize_date(start_date),
                    "passengers": guests
                }
                if budget:
                    transfer_arr.requirements["max_price"] = budget
                session.trip_plan.travel.ground_transport.append(transfer_arr)
                
                # Airport Transfer (Departure) - Only if round_trip or end_date exists
                if trip_type == "round_trip" and end_date:
                    transfer_dep = Segment()
                    transfer_dep.requirements = {
                        "origin": "Hotel in " + destination,
                        "destination": f"{destination} Airport",
                        "date": self._normalize_date(end_date),
                        "passengers": guests
                    }
                    if budget:
                        transfer_dep.requirements["max_price"] = budget
                    session.trip_plan.travel.ground_transport.append(transfer_dep)
                    
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
        if "flights" in focus and travel_mode in [TravelMode.FLIGHT_ONLY, TravelMode.BOTH]:
            for seg in session.trip_plan.travel.flights.all_segments:
                if "origin" in seg.requirements:
                    iata = await self._city_to_iata(seg.requirements["origin"])
                    if iata: seg.requirements["origin"] = iata
                if "destination" in seg.requirements:
                    iata = await self._city_to_iata(seg.requirements["destination"])
                    if iata: seg.requirements["destination"] = iata

        action_log.add_action(
            "CREATE_ITINERARY",
            payload,
            f"Created plan with focus {focus}: {len(session.trip_plan.travel.flights.all_segments)} flights, {len(session.trip_plan.accommodation.segments)} hotels."
        )
        session.update_timestamp()

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
            "date", "departure_date", "check_in", "check_out"
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
        
        # ✅ Validate segment data after update
        current_step = self.workflow_validator.get_current_workflow_step(session.trip_plan)
        is_valid, issues = self.workflow_validator.validate_segment_data(
            segment,
            slot_name,
            WorkflowStep.UPDATE_REQ.value
        )
        if not is_valid:
            logger.warning(f"UPDATE_REQ validation issues for {slot_name}[{segment_index}]: {issues}")
            action_log.add_action("VALIDATION_WARNING", payload, f"Validation issues: {', '.join(issues)}")
        
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
        """Execute CALL_SEARCH action using DataAggregator (Unified Data Layer)"""
        slot_name = payload.get("slot")
        segment_index = payload.get("segment_index", 0)
        
        if not slot_name:
            raise AgentException("CALL_SEARCH: Missing slot name")
        
        # ✅ Validate workflow step and action
        current_step = self.workflow_validator.get_current_workflow_step(session.trip_plan)
        is_allowed, error_msg = self.workflow_validator.validate_action_allowed(
            "CALL_SEARCH",
            current_step,
            session.trip_plan
        )
        if not is_allowed and error_msg:
            logger.warning(f"CALL_SEARCH validation failed: {error_msg}")
            action_log.add_action("VALIDATION_ERROR", {"action": "CALL_SEARCH", "error": error_msg}, error_msg)
            raise AgentException(f"CALL_SEARCH validation failed: {error_msg}")
        
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
        
        # Check if requirements are complete
        if not segment.needs_search():
            logger.info(f"CALL_SEARCH: Segment {slot_name}[{segment_index}] doesn't need search")
            return
        
        # Update status to searching
        segment.status = SegmentStatus.SEARCHING
        session.update_timestamp()
        
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
                                mcp_result = await self.mcp_executor.execute_tool(
                                    "search_flights",
                                    {
                                        "origin": req.get("origin"),
                                        "destination": req.get("destination"),
                                        "departure_date": req.get("departure_date") or req.get("date"),
                                        "adults": req.get("adults") or req.get("guests", 1),
                                        "children": req.get("children", 0),
                                        "infants": req.get("infants", 0),
                                        "return_date": req.get("return_date") if "inbound" not in slot_name else None
                                    }
                                )
                                
                                if mcp_result.get("success") and mcp_result.get("flights"):
                                    mcp_results = mcp_result["flights"]
                                    logger.info(f"✅ Amadeus MCP returned {len(mcp_results)} flight options")
                            
                            elif "accommodation" in slot_name or "hotel" in slot_name:
                                # Use Amadeus MCP search_hotels
                                logger.info(f"🔍 Using Amadeus MCP search_hotels for {slot_name}[{segment_index}]")
                                location = req.get("location") or req.get("destination")
                                mcp_result = await self.mcp_executor.execute_tool(
                                    "search_hotels",
                                    {
                                        "location_name": location,
                                        "check_in": req.get("check_in"),
                                        "check_out": req.get("check_out"),
                                        "guests": req.get("guests") or req.get("adults", 1),
                                        "adults": req.get("adults") or req.get("guests", 1),
                                        "children": req.get("children", 0),
                                        "radius": req.get("radius", 5)
                                    }
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
                                            "start_latitude": origin_coords.get("latitude"),
                                            "start_longitude": origin_coords.get("longitude"),
                                            "end_latitude": dest_coords.get("latitude"),
                                            "end_longitude": dest_coords.get("longitude"),
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
                    except: pass

                action_log.add_action(
                    "CALL_SEARCH",
                    payload,
                    f"Searched {slot_name}[{segment_index}] but found 0 options.{date_hint}"
                )
                return
            
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
            
            # ✅ Validate segment data after search
            is_valid, issues = self.workflow_validator.validate_segment_data(
                segment,
                slot_name,
                WorkflowStep.SELECTING.value
            )
            if not is_valid:
                logger.warning(f"CALL_SEARCH validation issues for {slot_name}[{segment_index}]: {issues}")
                action_log.add_action("VALIDATION_WARNING", payload, f"Validation issues: {', '.join(issues)}")
            
            # ✅ Validate state after search
            self.slot_manager.ensure_segment_state(segment, slot_name)
            
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
        
        # Validate segment state
        is_valid, issues = self.slot_manager.validate_segment(segment, slot_name)
        if not is_valid:
            logger.warning(f"Segment validation issues: {issues}")
            # Try to auto-fix
            self.slot_manager.ensure_segment_state(segment, slot_name)
        
        # Check if option exists
        if not segment.options_pool or len(segment.options_pool) == 0:
            raise AgentException(f"SELECT_OPTION: No options available for {slot_name}[{segment_index}]")
        
        if option_index < 0 or option_index >= len(segment.options_pool):
            raise AgentException(
                f"SELECT_OPTION: Option index {option_index} out of range "
                f"(has {len(segment.options_pool)} options)"
            )
        
        # ✅ Validate workflow step and action
        current_step = self.workflow_validator.get_current_workflow_step(session.trip_plan)
        is_allowed, error_msg = self.workflow_validator.validate_action_allowed(
            "SELECT_OPTION",
            current_step,
            session.trip_plan
        )
        if not is_allowed and error_msg:
            logger.warning(f"SELECT_OPTION validation failed: {error_msg}")
            action_log.add_action("VALIDATION_ERROR", {"action": "SELECT_OPTION", "error": error_msg}, error_msg)
            raise AgentException(f"SELECT_OPTION validation failed: {error_msg}")
        
        # ✅ Use SlotManager to set selection
        self.slot_manager.set_segment_selected(segment, slot_name, option_index)
        
        # ✅ Validate segment data after selection
        is_valid, issues = self.workflow_validator.validate_segment_data(
            segment,
            slot_name,
            WorkflowStep.SELECT_OPTION.value
        )
        if not is_valid:
            logger.warning(f"SELECT_OPTION validation issues for {slot_name}[{segment_index}]: {issues}")
            action_log.add_action("VALIDATION_WARNING", payload, f"Validation issues: {', '.join(issues)}")
        
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
        
        action_log.add_action(
            "SELECT_OPTION",
            {**payload, "option_summary": option_summary},
            f"Selected option {option_index} for {slot_name}[{segment_index}]: {option_summary.get('name', 'N/A')}"
        )
        
        # ✅ FIX: After selecting transport, trigger search for accommodation if needed
        # Check if this is a transport selection (ground_transport, transport, or transfer)
        is_transport_selection = slot_name in ["ground_transport", "transport", "transfer"]
        
        # #region agent log
        _write_debug_log({
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "G",
            "location": "agent.py:2299",
            "message": "SELECT_OPTION executed - checking if transport",
            "data": {
                "slot_name": slot_name,
                "is_transport_selection": is_transport_selection,
                "segment_status": str(segment.status),
                "accommodation_segments_count": len(session.trip_plan.accommodation.segments)
            },
            "timestamp": int(datetime.now().timestamp() * 1000)
        })
        # #endregion
        
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
                    
                    # #region agent log
                    _write_debug_log({
                        "sessionId": "debug-session",
                        "runId": "run1",
                        "hypothesisId": "G",
                        "location": "agent.py:2310",
                        "message": "Auto-triggering accommodation search",
                        "data": {
                            "accommodation_index": acc_idx,
                            "accommodation_status": str(acc_seg.status),
                            "accommodation_needs_search": acc_seg.needs_search()
                        },
                        "timestamp": int(datetime.now().timestamp() * 1000)
                    })
                    # #endregion
                    
                    # Execute search immediately
                    try:
                        await self._execute_call_search(
                            session,
                            {"slot": "accommodation", "segment_index": acc_idx},
                            action_log
                        )
                        
                        # #region agent log
                        _write_debug_log({
                            "sessionId": "debug-session",
                            "runId": "run1",
                            "hypothesisId": "G",
                            "location": "agent.py:2325",
                            "message": "Accommodation search completed",
                            "data": {
                                "accommodation_index": acc_idx,
                                "accommodation_status_after": str(acc_seg.status),
                                "options_count": len(acc_seg.options_pool) if acc_seg.options_pool else 0
                            },
                            "timestamp": int(datetime.now().timestamp() * 1000)
                        })
                        # #endregion
                    except Exception as e:
                        logger.error(f"Error auto-triggering accommodation search: {e}", exc_info=True)
        
        session.update_timestamp()
    
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
        """
        try:
            # ✅ Use SlotManager to get all segments with stable access
            all_segments_managed = self.slot_manager.get_all_segments(session.trip_plan)
            
            # Filter to only segments with options that need selection
            segments_to_select = [
                (slot_name, segment, idx)
                for slot_name, segment, idx in all_segments_managed
                if segment.options_pool and not segment.selected_option
            ]
            
            if not segments_to_select:
                logger.info("Agent Mode: No segments with options to auto-select - segments may already be selected, continuing to booking check")
                # ✅ Continue to booking check even if no segments to select (might already be selected)
            
            # ✅ Process segments in priority order (outbound → inbound → accommodation → transport)
            from app.engine.slot_manager import SlotType
            
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
            for slot_name, segment, segment_index in sorted_segments:
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
                
                # Build LLM prompt for smart selection
                options_json = json.dumps([opt.model_dump() if hasattr(opt, 'model_dump') else opt for opt in segment.options_pool], ensure_ascii=False, indent=2)
                
                selection_prompt = f"""You are an expert travel advisor. Analyze these options and select the BEST one.

=== USER PREFERENCES ===
{memory_summary or "No specific preferences recorded"}

=== REQUIREMENTS ===
{json.dumps(segment.requirements, ensure_ascii=False)}

=== AVAILABLE OPTIONS ===
{options_json}

=== SELECTION CRITERIA ===
1. **Value**: Best price/quality ratio
2. **Convenience**: Shortest duration, fewest stops, best locations
3. **Reviews**: Higher ratings preferred
4. **User Preferences**: Match user's past preferences if available
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
                    self.slot_manager.set_segment_selected(segment, slot_name, best_option_index)
                    
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
                except Exception as e:
                    logger.error(f"Failed to set selection for {slot_name}[{segment_index}]: {e}")
                    raise
            
            # Check if all required segments have selected options (ready to book immediately)
            all_flights = session.trip_plan.travel.flights.outbound + session.trip_plan.travel.flights.inbound
            all_accommodations = session.trip_plan.accommodation.segments
            
            # ✅ Agent Mode: Book immediately when options are selected (don't wait for CONFIRMED status)
            has_selected_flight = any(seg.selected_option is not None for seg in all_flights)
            has_selected_hotel = any(seg.selected_option is not None for seg in all_accommodations)
            
            # Also check confirmed status as fallback
            has_confirmed_flight = any(seg.status == SegmentStatus.CONFIRMED for seg in all_flights)
            has_confirmed_hotel = any(seg.status == SegmentStatus.CONFIRMED for seg in all_accommodations)
            
            logger.info(f"Agent Mode: Booking check - flights: {len(all_flights)} (selected: {sum(1 for s in all_flights if s.selected_option is not None)}, confirmed: {sum(1 for s in all_flights if s.status == SegmentStatus.CONFIRMED)}), hotels: {len(all_accommodations)} (selected: {sum(1 for s in all_accommodations if s.selected_option is not None)}, confirmed: {sum(1 for s in all_accommodations if s.status == SegmentStatus.CONFIRMED)})")
            
            # ✅ Auto-book immediately if we have at least flight OR hotel with selected_option (Agent Mode books instantly)
            if has_selected_flight or has_selected_hotel or has_confirmed_flight or has_confirmed_hotel:
                logger.info(f"Agent Mode: Ready to auto-book immediately! has_selected_flight={has_selected_flight}, has_selected_hotel={has_selected_hotel}, has_confirmed_flight={has_confirmed_flight}, has_confirmed_hotel={has_confirmed_hotel}")
                
                # ✅ Check if booking already exists to prevent duplicates
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
                        if check_response.ok:
                            check_data = check_response.json()
                            if check_data.get("ok") and check_data.get("bookings"):
                                # Check if there's already a booking for this trip
                                existing_booking = next(
                                    (b for b in check_data.get("bookings", []) 
                                     if b.get("trip_id") == (session.trip_id or session.session_id) 
                                     and b.get("status") in ["pending_payment", "confirmed"]),
                                    None
                                )
                                if existing_booking:
                                    logger.info(f"Agent Mode: Booking already exists: {existing_booking.get('booking_id')}, skipping duplicate booking")
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
                        # ✅ Calculate total price from segments with selected_option (immediate booking)
                        total_price = 0.0
                        currency = "THB"
                        price_details = []
                        
                        for seg in all_flights + all_accommodations:
                            # ✅ Book immediately if segment has selected_option (don't wait for CONFIRMED status)
                            if seg.selected_option:
                                option = seg.selected_option
                                price = option.get("price_amount") or option.get("price_total") or option.get("price", 0)
                                if isinstance(price, (int, float)):
                                    total_price += float(price)
                                    # เพิ่มรายละเอียดราคา
                                    if seg in all_flights:
                                        flight_num = option.get("flight_number") or option.get("display_name", "").split()[0] if option.get("display_name") else "เที่ยวบิน"
                                        price_details.append(f"{flight_num}: {int(price):,} บาท")
                                    elif seg in all_accommodations:
                                        hotel_name = option.get("display_name") or option.get("name", "ที่พัก")
                                        price_details.append(f"{hotel_name}: {int(price):,} บาท")
                                if option.get("currency"):
                                    currency = option.get("currency")
                        
                        # ✅ แสดงรายละเอียดราคารวม
                        if status_callback and price_details:
                            price_summary = " + ".join(price_details) + f" = {int(total_price):,} บาท"
                            await status_callback("booking", f"💰 ราคารวม: {price_summary}", "agent_auto_book_price")
                        
                        if status_callback:
                            await status_callback("booking", "🤖 Agent กำลังจองทริปทันที...", "agent_auto_book")
                        
                        # Create booking via HTTP request to booking API
                        # Use settings or default to localhost
                        booking_url = f"{getattr(settings, 'api_base_url', 'http://localhost:8000')}/api/booking/create"
                        booking_payload = {
                            "trip_id": session.trip_id or session.session_id,
                            "chat_id": session.chat_id,
                            "user_id": session.user_id,
                            "plan": session.trip_plan.model_dump(),
                            "travel_slots": {
                                # ✅ Include segments with selected_option immediately (Agent Mode books instantly)
                                "flights": [s.model_dump() for s in all_flights if s.selected_option is not None],
                                "accommodations": [s.model_dump() for s in all_accommodations if s.selected_option is not None],
                                "ground_transport": [s.model_dump() for s in session.trip_plan.travel.ground_transport if s.selected_option is not None]
                            },
                            "total_price": total_price,
                            "currency": currency,
                            "mode": "agent",  # ✅ Mark as agent mode
                            "auto_booked": True  # ✅ Mark as auto-booked
                        }
                        
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(booking_url, json=booking_payload)
                            response.raise_for_status()
                            booking_result = response.json()
                        
                        booking_id = booking_result.get("booking_id")
                        booking_status = booking_result.get("status", "pending_payment")  # ✅ Status is pending_payment (needs payment)
                        
                        logger.info(f"Agent Mode: Auto-booked successfully (instant booking): {booking_id} (status: {booking_status})")
                        
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
                        
                        # ✅ Save session after booking to ensure state is persisted
                        await self.storage.save_session(session)
                    except Exception as e:
                        logger.error(f"Agent Mode: Failed to auto-book: {e}", exc_info=True)
                        action_log.add_action(
                            "AUTO_BOOK_ERROR",
                            {"error": str(e)},
                            "Agent Mode: Failed to auto-book",
                            success=False
                        )
            
        except Exception as e:
            logger.error(f"Agent Mode: Error in auto-select-and-book: {e}", exc_info=True)
            action_log.add_action(
                "AUTO_SELECT_ERROR",
                {"error": str(e)},
                "Agent Mode: Failed to auto-select options",
                success=False
            )
    
    async def generate_response(
        self,
        session: UserSession,
        action_log: ActionLog,
        memory_context: str = "",
        user_profile_context: str = "",
        mode: str = "normal"  # ✅ Pass mode to responder
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
            state_json = json.dumps(session.trip_plan.model_dump(), ensure_ascii=False, indent=2)
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
                        system_prompt=RESPONDER_SYSTEM_PROMPT,
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
                    # Determine complexity (simple for most responses, complex if Agent Mode)
                    complexity = "complex" if agent_mode_actions else "simple"
                    start_time = asyncio.get_event_loop().time()
                    try:
                        logger.info(f"Calling production_llm.responder_generate: complexity={complexity}, prompt_length={len(prompt)}")
                        response_text = await self.production_llm.responder_generate(
                            prompt=prompt,
                            system_prompt=RESPONDER_SYSTEM_PROMPT,
                            complexity=complexity
                        )
                        logger.info(f"Production LLM response generated: length={len(response_text) if response_text else 0}, is_none={response_text is None}, is_empty={not response_text.strip() if response_text else True}")
                        
                        # 🆕 COST TRACKING: Track Responder LLM call
                        try:
                            end_time = asyncio.get_event_loop().time()
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
                
                # Fallback to old LLM service if production LLM failed or not available
                if response_text is None:
                    logger.info(f"Falling back to basic LLM service: production_llm={self.production_llm is not None}, llm={self.llm is not None}")
                    try:
                        response_text = await self.llm.generate_content(
                            prompt=prompt,
                            system_prompt=RESPONDER_SYSTEM_PROMPT,
                            temperature=settings.responder_temperature,
                            max_tokens=2500,  # ✅ Increased from 2000 to 2500 to ensure complete city names are included
                            auto_select_model=True,
                            context="responder"
                        )
                        logger.info(f"Basic LLM response generated: length={len(response_text) if response_text else 0}, is_none={response_text is None}, is_empty={not response_text.strip() if response_text else True}")
                    except LLMException as llm_error:
                        logger.error(f"Basic LLM failed with LLMException: {llm_error}")
                        error_str = str(llm_error).lower()
                        # ✅ Handle quota exceeded errors with retry delay
                        if hasattr(llm_error, 'is_quota_error') and llm_error.is_quota_error:
                            retry_delay = getattr(llm_error, 'retry_delay', 10)
                            logger.warning(f"Quota exceeded, waiting {retry_delay} seconds before retry...")
                            await asyncio.sleep(min(retry_delay, 60))  # Cap at 60 seconds
                            # Retry once after waiting
                            try:
                                logger.info("Retrying after quota wait period...")
                                response_text = await self.llm.generate_content(
                                    prompt=prompt,
                                    system_prompt=RESPONDER_SYSTEM_PROMPT,
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
                        response_text = "ขออภัยค่ะ ระบบไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
            if not response_text or response_text.strip() == "":
                logger.warning("Responder LLM returned empty text, using fallback")
                agent_monitor.log_activity(session.session_id, session.user_id, "warning", "Responder returned empty text")
                response_text = "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
            # ✅ CRITICAL: Final check before returning
            if not response_text or not response_text.strip():
                logger.error(f"Response text is still empty after fallback: session={session.session_id}")
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
        if guests < 1 or guests > 20:
            issues.append(f"จำนวนผู้เดินทางผิดปกติ: {guests}")
        
        budget = plan_data.get("budget")
        if budget and budget > 0:
            nights = 1
            if start and end:
                try:
                    nights = (datetime.fromisoformat(end) - datetime.fromisoformat(start)).days
                except:
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
            except:
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
