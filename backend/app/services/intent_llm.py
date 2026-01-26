"""
Intent-Based LLM Service
Uses Gemini models to analyze user intent and automatically call appropriate tools
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import json
import asyncio
from datetime import datetime

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException
from app.services.llm import LLMServiceWithMCP
from app.services.mcp_server import mcp_executor, ALL_MCP_TOOLS

logger = get_logger(__name__)


class IntentBasedLLM:
    """
    Intent-Based LLM Service
    Analyzes user input to determine intent and automatically calls appropriate tools
    """
    
    def __init__(self):
        """Initialize Intent-Based LLM with tool calling support"""
        try:
            self.llm = LLMServiceWithMCP()
            logger.info("IntentBasedLLM initialized with tool calling support")
        except Exception as e:
            logger.error(f"Failed to initialize IntentBasedLLM: {e}")
            raise LLMException(f"IntentBasedLLM initialization failed: {e}") from e
    
    async def analyze_intent_and_respond(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tool_calls: int = 5,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze user intent and automatically call appropriate tools
        
        Args:
            user_input: User's message
            system_prompt: Optional system prompt
            conversation_history: Optional conversation history
            max_tool_calls: Maximum number of tool calls
            temperature: Generation temperature
            
        Returns:
            Dictionary with:
            - 'text': Final response text
            - 'intent': Detected user intent
            - 'tools_called': List of tools that were called
            - 'tool_results': Results from tool calls
        """
        # Build enhanced system prompt for intent analysis and tool calling
        enhanced_system_prompt = f"""You are an intelligent Travel Agent AI that analyzes user intent and automatically uses tools to help users.

🎯 YOUR JOB:
1. Analyze user input to understand their intent (what they want to do)
2. Automatically call appropriate tools to fulfill their request
3. Provide helpful responses based on tool results

🧠 INTENT ANALYSIS:
Analyze the user's intent from their message:
- **Search Flights**: User wants to find flights (e.g., "หาตั๋วบิน", "fly to Tokyo", "flight Bangkok to Seoul")
- **Search Hotels**: User wants to find hotels (e.g., "หาที่พัก", "hotel in Phuket", "book a room")
- **Search Transfers**: User wants ground transport (e.g., "รถรับส่ง", "taxi", "transfer")
- **Get Location Info**: User wants location information (e.g., "where is", "distance to", "info about")
- **Plan Trip**: User wants to plan a full trip (e.g., "plan trip", "จัดทริป", "I want to go to")

🛠️ AVAILABLE TOOLS (MCP - Amadeus & Google Maps):

📊 AMADEUS TOOLS (Flight, Hotel, Transfer Search):
1. **search_flights** - Search for flights using Amadeus API
   - Parameters: origin (airport code/city), destination (airport code/city), departure_date (YYYY-MM-DD), adults (integer), return_date (optional)
   - Use when: User asks about flights, "หาตั๋วบิน", "fly to", "flight from X to Y"

2. **search_hotels** - Search for hotels using Amadeus API
   - Parameters: location (city/IATA code), check_in (YYYY-MM-DD), check_out (YYYY-MM-DD), guests (integer)
   - Use when: User asks about hotels, "หาที่พัก", "hotel in", "book room"

3. **search_transfers** - Search for ground transport (taxis, cars, shuttles)
   - Parameters: origin (airport/address), destination (address), date (YYYY-MM-DD), passengers (integer)
   - Use when: User asks about transfers, "รถรับส่ง", "taxi", "ground transport"

4. **search_transfers_by_geo** - Search transfers using GPS coordinates (more precise)
   - Parameters: start_lat, start_lng, end_lat, end_lng, start_time (YYYY-MM-DDTHH:MM:SS), passengers
   - Use when: You have exact coordinates from geocode_location tool

5. **search_activities** - Search for tours, activities, and experiences
   - Parameters: location (city), radius (km, default 10)
   - Use when: User asks about tours, "กิจกรรม", "tours", "things to do"

🗺️ GOOGLE MAPS TOOLS (Location & Geocoding):
1. **geocode_location** - Convert place name/address to coordinates (lat, lng)
   - Parameters: place_name (address/landmark, e.g., "Eiffel Tower", "Tokyo Station")
   - Use when: User mentions landmarks or addresses, need coordinates for maps/search

2. **find_nearest_airport** - Find nearest airport IATA code for a location
   - Parameters: location (city/place, e.g., "Chiang Mai", "Phuket")
   - Use when: User mentions city but needs airport code for flight search

3. **get_place_details** - Get detailed place information (address, rating, hours)
   - Parameters: place_name (business/place name)
   - Use when: User asks about place details, "info about", "where is", "details of"

📋 USAGE RULES:
1. If user asks about flights → Call **search_flights** automatically (use find_nearest_airport first if needed)
2. If user asks about hotels → Call **search_hotels** automatically
3. If user asks about transfers → Call **search_transfers** or **search_transfers_by_geo** automatically
4. If user mentions landmark/address → Call **geocode_location** first, then use coordinates for searches
5. If user mentions city for flights → Call **find_nearest_airport** to get airport code, then **search_flights**
6. If user wants to plan a trip → Call multiple tools as needed (flights + hotels + transfers + activities)
7. If user asks about location details → Call **get_place_details** automatically

💡 INTELLIGENCE:
- Extract travel details from natural language (dates, locations, guests)
- Infer missing information intelligently (default dates, origins, etc.)
- Combine multiple tool calls if needed (e.g., search flights AND hotels for a trip)
- Provide helpful explanations based on tool results

🌐 LANGUAGE:
- Respond in Thai if user writes in Thai
- Support both Thai and English naturally

{system_prompt or ""}

Remember: Automatically use tools when user asks for something. Don't just explain - DO IT!
"""
        
        # Build conversation context
        prompt = user_input
        if conversation_history:
            # Format history for context
            history_text = "\n".join([
                f"{'User' if msg.get('role') == 'user' else 'Assistant'}: {msg.get('content', '')}"
                for msg in conversation_history[-5:]  # Last 5 messages for context
            ])
            prompt = f"=== CONVERSATION HISTORY ===\n{history_text}\n\n=== CURRENT MESSAGE ===\n{user_input}"
        
        try:
            # Use generate_with_tools to automatically call tools
            result = await self.llm.generate_with_tools(
                prompt=prompt,
                system_prompt=enhanced_system_prompt,
                temperature=temperature,
                max_tool_calls=max_tool_calls,
                max_tokens=4000
            )
            
            # Extract intent from tool calls or analyze from response
            intent = self._extract_intent(user_input, result.get('tool_calls', []))
            
            return {
                'text': result.get('text', ''),
                'intent': intent,
                'tools_called': [tc.get('tool') for tc in result.get('tool_calls', [])],
                'tool_results': result.get('tool_calls', []),
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}", exc_info=True)
            return {
                'text': f'ขออภัยค่ะ เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)[:100]}',
                'intent': 'unknown',
                'tools_called': [],
                'tool_results': [],
                'success': False,
                'error': str(e)
            }
    
    def _extract_intent(self, user_input: str, tool_calls: List[Dict[str, Any]]) -> str:
        """
        Extract user intent from input and tool calls
        
        Args:
            user_input: User's message
            tool_calls: List of tool calls that were made
            
        Returns:
            Detected intent string
        """
        user_lower = user_input.lower()
        
        # Check tool calls first (most reliable)
        if tool_calls:
            tool_names = [tc.get('tool', '') for tc in tool_calls]
            if 'search_flights' in tool_names:
                return 'search_flights'
            elif 'search_hotels' in tool_names:
                return 'search_hotels'
            elif 'search_transfers' in tool_names:
                return 'search_transfers'
            elif 'get_location_info' in tool_names:
                return 'get_location_info'
        
        # Fallback to keyword analysis
        if any(keyword in user_lower for keyword in ['flight', 'บิน', 'ตั๋ว', 'เที่ยวบิน', 'airline', 'fly']):
            return 'search_flights'
        elif any(keyword in user_lower for keyword in ['hotel', 'ที่พัก', 'โรงแรม', 'accommodation', 'stay']):
            return 'search_hotels'
        elif any(keyword in user_lower for keyword in ['transfer', 'รถ', 'taxi', 'shuttle', 'transport']):
            return 'search_transfers'
        elif any(keyword in user_lower for keyword in ['location', 'ที่ไหน', 'where', 'distance', 'info']):
            return 'get_location_info'
        elif any(keyword in user_lower for keyword in ['plan', 'trip', 'ทริป', 'จัด', 'book', 'จอง']):
            return 'plan_trip'
        else:
            return 'general_query'
