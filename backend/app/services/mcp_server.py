"""
Model Context Protocol (MCP) Server for AI Travel Agent
Provides tools for Amadeus API and Google Maps to LLM
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable
import json
import asyncio
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.core.config import settings
from app.core.exceptions import AmadeusException, AgentException
from app.services.travel_service import TravelOrchestrator
from app.services.google_maps_client import get_google_maps_client

logger = get_logger(__name__)

# MCP Configuration
MCP_MAX_RETRIES = 3
MCP_TIMEOUT_SECONDS = 15  # ✅ Optimized for 1.5-minute completion target
MCP_RETRY_DELAY = 2


# =============================================================================
# MCP Tool Definitions (Function Calling Schema for Gemini)
# =============================================================================

AMADEUS_TOOLS = [
    {
        "name": "search_flights",
        "description": "Search for flight offers using Amadeus API. Returns up to 10 flight options with prices, airlines, and schedules.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin airport IATA code (e.g., 'BKK') or city name (e.g., 'Bangkok')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination airport IATA code (e.g., 'NRT') or city name (e.g., 'Tokyo')"
                },
                "departure_date": {
                    "type": "string",
                    "description": "Departure date in YYYY-MM-DD format (e.g., '2025-02-15')"
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult passengers (default: 1)",
                    "default": 1
                },
                "return_date": {
                    "type": "string",
                    "description": "Optional return date for round-trip in YYYY-MM-DD format"
                }
            },
            "required": ["origin", "destination", "departure_date"]
        }
    },
    {
        "name": "search_hotels",
        "description": "Search for hotel offers using Amadeus API. Returns up to 10 hotel options with prices, ratings, and locations.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or IATA code (e.g., 'Tokyo' or 'TYO')"
                },
                "check_in": {
                    "type": "string",
                    "description": "Check-in date in YYYY-MM-DD format"
                },
                "check_out": {
                    "type": "string",
                    "description": "Check-out date in YYYY-MM-DD format"
                },
                "guests": {
                    "type": "integer",
                    "description": "Number of guests (default: 1)",
                    "default": 1
                }
            },
            "required": ["location", "check_in", "check_out"]
        }
    },
    {
        "name": "search_transfers",
        "description": "Search for ground transfer options (taxis, private cars, shuttles) using Amadeus API.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (airport code or address)"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination address or location name"
                },
                "date": {
                    "type": "string",
                    "description": "Transfer date in YYYY-MM-DD format"
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers (default: 1)",
                    "default": 1
                }
            },
            "required": ["origin", "destination", "date"]
        }
    },
    {
        "name": "search_transfers_by_geo",
        "description": "Search for transfers using exact GPS coordinates. More precise than address search. Use 'geocode_location' first to get coordinates.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_lat": {
                    "type": "number",
                    "description": "Start location latitude"
                },
                "start_lng": {
                    "type": "number",
                    "description": "Start location longitude"
                },
                "end_lat": {
                    "type": "number",
                    "description": "End location latitude"
                },
                "end_lng": {
                    "type": "number",
                    "description": "End location longitude"
                },
                "start_time": {
                    "type": "string",
                    "description": "Start date/time in YYYY-MM-DDTHH:MM:SS format (e.g., 2025-02-15T10:00:00)"
                },
                "passengers": {
                    "type": "integer",
                    "description": "Number of passengers (default: 1)",
                    "default": 1
                }
            },
            "required": ["start_lat", "start_lng", "end_lat", "end_lng", "start_time"]
        }
    },
    {
        "name": "search_activities",
        "description": "Search for tours, activities, and experiences using Amadeus API.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or location (e.g., 'Tokyo', 'Paris')"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in kilometers (default: 10)",
                    "default": 10
                }
            },
            "required": ["location"]
        }
    }
]

GOOGLE_MAPS_TOOLS = [
    {
        "name": "geocode_location",
        "description": "Convert a place name or address to geographic coordinates (latitude, longitude) using Google Maps API.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "Place name, address, or landmark (e.g., 'Eiffel Tower', 'Tokyo Station', '123 Main St, Bangkok')"
                }
            },
            "required": ["place_name"]
        }
    },
    {
        "name": "find_nearest_airport",
        "description": "Find the nearest airport IATA code for a given location using Google Maps and Amadeus APIs.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "City name or place (e.g., 'Chiang Mai', 'Phuket')"
                }
            },
            "required": ["location"]
        }
    },
    {
        "name": "search_nearby_places",
        "description": "Search for nearby places (attractions, restaurants, etc.) using Google Maps Places API. Returns top 5 results with name, place_id, rating, user_ratings_total, vicinity, and types.",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword (e.g., 'restaurant', 'tourist attraction', 'museum', 'hotel')"
                },
                "lat": {
                    "type": "number",
                    "description": "Latitude of the center point"
                },
                "lng": {
                    "type": "number",
                    "description": "Longitude of the center point"
                },
                "radius": {
                    "type": "integer",
                    "description": "Search radius in meters (default: 1000, max: 50000)",
                    "default": 1000
                }
            },
            "required": ["keyword", "lat", "lng"]
        }
    },
    {
        "name": "get_place_details",
        "description": "Get detailed information about a place using Google Maps API. Requires place_id from search_nearby_places or geocode_location. Returns formatted_address, opening_hours, photo_reference (1 photo), and review_summary (top 1 review).",
        "parameters": {
            "type": "object",
            "properties": {
                "place_id": {
                    "type": "string",
                    "description": "Google Place ID (obtained from search_nearby_places or geocode_location)"
                }
            },
            "required": ["place_id"]
        }
    },
    {
        "name": "plan_route",
        "description": "Plan a route from origin to destination using Google Maps Directions API. Returns detailed route information including distance, duration, and recommended transportation methods (flight, car, train, bus). Use this to determine which airports to use and optimal transportation methods.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (place name, address, or coordinates like 'lat,lng')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location (place name, address, or coordinates like 'lat,lng')"
                },
                "travel_mode": {
                    "type": "string",
                    "description": "Preferred travel mode: 'driving', 'walking', 'transit', 'bicycling'. Default is 'driving' for road routes. Use 'transit' to check train/bus availability.",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "default": "driving"
                }
            },
            "required": ["origin", "destination"]
        }
    },
    {
        "name": "compare_transport_modes",
        "description": "Compare different transport modes (driving, transit, walking) between two local places. Use this to decide whether to take a taxi, public transport, or walk between two local places. Returns duration, distance, and cost information for each available mode.",
        "parameters": {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "string",
                    "description": "Origin location (place name, address, or coordinates like 'lat,lng')"
                },
                "destination": {
                    "type": "string",
                    "description": "Destination location (place name, address, or coordinates like 'lat,lng')"
                }
            },
            "required": ["origin", "destination"]
        }
    }
]

# All tools combined
ALL_MCP_TOOLS = AMADEUS_TOOLS + GOOGLE_MAPS_TOOLS


# =============================================================================
# MCP Tool Executor
# =============================================================================

class MCPToolExecutor:
    """
    Production-Grade MCP Tool Executor
    Executes MCP tools (function calls) for LLM with robust error handling
    
    Features:
    - Retry logic with exponential backoff
    - Timeout protection
    - Input validation and sanitization
    - Graceful error handling
    - Comprehensive logging
    """
    
    def __init__(self):
        try:
            self.orchestrator = TravelOrchestrator()
            self.google_maps_client = get_google_maps_client()
            self.max_retries = MCP_MAX_RETRIES
            self.timeout = MCP_TIMEOUT_SECONDS
            logger.info(f"MCPToolExecutor initialized with TravelOrchestrator and GoogleMapsClient (retries={self.max_retries}, timeout={self.timeout}s)")
        except Exception as e:
            logger.error(f"Failed to initialize MCPToolExecutor: {e}", exc_info=True)
            raise
    
    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize tool parameters
        
        Args:
            tool_name: Tool name
            parameters: Raw parameters
            
        Returns:
            Validated and sanitized parameters
        """
        validated = {}
        
        # Get tool definition to check required fields
        tool_def = next((t for t in ALL_MCP_TOOLS if t["name"] == tool_name), None)
        if not tool_def:
            raise AgentException(f"Unknown tool: {tool_name}")
        
        required = tool_def["parameters"].get("required", [])
        properties = tool_def["parameters"].get("properties", {})
        
        # Validate required fields (with special handling for search_hotels location/location_name)
        for field in required:
            # ✅ Special case: search_hotels accepts either 'location' or 'location_name'
            if tool_name == "search_hotels" and field == "location":
                if "location" not in parameters and "location_name" not in parameters:
                    raise AgentException(f"Missing required parameter: 'location' or 'location_name'")
                # Use location_name if location is not provided
                validated[field] = parameters.get("location") or parameters.get("location_name")
            elif field not in parameters or parameters[field] is None:
                raise AgentException(f"Missing required parameter: {field}")
            else:
                validated[field] = parameters[field]
        
        # Validate optional fields with defaults
        for field, prop_def in properties.items():
            if field in parameters:
                validated[field] = parameters[field]
            elif "default" in prop_def:
                validated[field] = prop_def["default"]
        
        # Sanitize string inputs
        for key, value in validated.items():
            if isinstance(value, str):
                validated[key] = value.strip()[:500]  # Limit length
        
        return validated
    
    @retry(
        retry=retry_if_exception_type((AmadeusException, Exception)),
        stop=stop_after_attempt(MCP_MAX_RETRIES),
        wait=wait_exponential(multiplier=1, min=MCP_RETRY_DELAY, max=10)
    )
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters (with retry logic)
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters as dictionary
            
        Returns:
            Tool execution result as dictionary
        """
        try:
            logger.info(f"Executing MCP tool: {tool_name} with params: {parameters}")
            
            # Validate parameters
            validated_params = self._validate_parameters(tool_name, parameters)
            
            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    self._execute_tool_internal(tool_name, validated_params),
                    timeout=self.timeout
                )
                
                # Validate result
                if not isinstance(result, dict):
                    raise AgentException(f"Tool {tool_name} returned invalid result type")
                
                if "success" not in result:
                    result["success"] = True
                
                logger.info(f"MCP tool {tool_name} executed successfully")
                return result
                
            except asyncio.TimeoutError:
                logger.error(f"MCP tool {tool_name} timed out after {self.timeout}s")
                return {
                    "success": False,
                    "error": f"Tool execution timed out after {self.timeout} seconds",
                    "tool": tool_name
                }
        
        except Exception as e:
            # ✅ SAFETY FIRST: Catch ALL exceptions (including AgentException) and return graceful JSON
            # NEVER raise exceptions that crash the server - workflow must continue
            logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            return {
                "status": "error",
                "success": False,
                "message": "Tool execution failed, please ask user for more details",
                "error": str(e)[:200],  # Truncate error message
                "tool": tool_name
            }
    
    async def _execute_tool_internal(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Internal tool execution (without retry wrapper)"""
        # Route to appropriate handler
        if tool_name == "search_flights":
            return await self._search_flights(parameters)
        elif tool_name == "search_hotels":
            return await self._search_hotels(parameters)
        elif tool_name == "search_transfers":
            return await self._search_transfers(parameters)
        elif tool_name == "search_transfers_by_geo":
            return await self._search_transfers_by_geo(parameters)
        elif tool_name == "search_activities":
            return await self._search_activities(parameters)
        elif tool_name == "geocode_location":
            return await self._geocode_location(parameters)
        elif tool_name == "search_nearby_places":
            return await self._search_nearby_places(parameters)
        elif tool_name == "find_nearest_airport":
            return await self._find_nearest_airport(parameters)
        elif tool_name == "get_place_details":
            return await self._get_place_details(parameters)
        elif tool_name == "plan_route":
            return await self._plan_route(parameters)
        else:
            raise AgentException(f"Unknown tool: {tool_name}")
    
    # -------------------------------------------------------------------------
    # Amadeus Tools
    # -------------------------------------------------------------------------
    
    async def _search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights using Amadeus API"""
        origin = params.get("origin", "BKK")
        destination = params.get("destination", "NRT")
        departure_date = params.get("departure_date")
        adults = params.get("adults", 1)
        
        # ✅ Log search parameters for debugging
        logger.info(f"🔍 Searching flights: {origin} → {destination} on {departure_date} for {adults} adult(s)")
        
        try:
            results = await self.orchestrator.get_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                adults=adults
            )
            
            # ✅ Log raw results count
            logger.info(f"📊 Amadeus API returned {len(results) if results else 0} flight results")
            
            # ✅ Check for fallback results (from date range search)
            fallback_results = [r for r in results if r.get("_fallback_date")]
            if fallback_results:
                logger.info(f"📅 Found {len(fallback_results)} flights from fallback dates (original date: {departure_date})")
            
            if not results or len(results) == 0:
                # ✅ Check date range for better error message
                from datetime import datetime, timedelta
                try:
                    search_date = datetime.strptime(departure_date, "%Y-%m-%d")
                    today = datetime.now()
                    days_ahead = (search_date - today).days
                    max_days = 330  # ~11 months
                    
                    date_warning = ""
                    if days_ahead < 0:
                        date_warning = f"⚠️ Date is in the past ({-days_ahead} days ago)"
                    elif days_ahead > max_days:
                        date_warning = f"⚠️ Date is {days_ahead} days ahead (max: {max_days} days) - Amadeus may not have data"
                except Exception:
                    date_warning = ""
                
                logger.error(
                    f"❌ No flights found for {origin} → {destination} on {departure_date}\n"
                    f"   Search parameters: origin={origin}, destination={destination}, date={departure_date}, adults={adults}\n"
                    f"   {date_warning}\n"
                    f"   Possible reasons:\n"
                    f"   1. Date too far in future (Amadeus supports ~11 months ahead)\n"
                    f"   2. No flights available for this route/date\n"
                    f"   3. Date is too close (same-day booking may be limited)\n"
                    f"   4. IATA codes may be incorrect: {origin} or {destination}\n"
                    f"   5. Route not serviced by airlines in Amadeus database\n"
                    f"   6. Amadeus API may not have data for this route"
                )
                return {
                    "success": True,
                    "tool": "search_flights",
                    "results_count": 0,
                    "flights": [],
                    "message": f"No flights found for {origin} → {destination} on {departure_date}. {date_warning if date_warning else 'Please try different dates or check route availability.'}",
                    "search_params": {
                        "origin": origin,
                        "destination": destination,
                        "date": departure_date,
                        "adults": adults
                    },
                    "diagnostics": {
                        "date_warning": date_warning,
                        "suggestion": "Try dates within 11 months from today or check if route is available"
                    }
                }
            
            # ✅ Format results for LLM (limit to top 3 for faster processing, but include fallback results)
            formatted = []
            # Separate fallback and original results
            fallback_results = [r for r in results if r.get("_fallback_date")]
            original_results = [r for r in results if not r.get("_fallback_date")]
            
            # Prioritize original results, then add fallback results
            display_results = (original_results[:3] if len(original_results) >= 3 else original_results) + fallback_results[:2]
            
            for idx, flight in enumerate(display_results[:3]):  # ✅ Show up to 3 results (prioritize original date)
                itineraries = flight.get("itineraries", [])
                if not itineraries:
                    continue
                
                first_segment = itineraries[0].get("segments", [{}])[0]
                price = flight.get("price", {})
                
                formatted.append({
                    "option_number": idx + 1,
                    "airline": first_segment.get("carrierCode", ""),
                    "flight_number": first_segment.get("number", ""),
                    "departure": {
                        "airport": first_segment.get("departure", {}).get("iataCode", ""),
                        "time": first_segment.get("departure", {}).get("at", "")
                    },
                    "arrival": {
                        "airport": first_segment.get("arrival", {}).get("iataCode", ""),
                        "time": first_segment.get("arrival", {}).get("at", "")
                    },
                    "price": {
                        "total": price.get("total", "0"),
                        "currency": price.get("currency", "THB")
                    },
                    "duration": itineraries[0].get("duration", "")
                })
            
            logger.info(f"✅ Formatted {len(formatted)} flight options for display")
            
            return {
                "success": True,
                "tool": "search_flights",
                "results_count": len(formatted),
                "flights": formatted,
                "search_params": {
                    "origin": origin,
                    "destination": destination,
                    "date": departure_date,
                    "adults": adults
                }
            }
        except Exception as e:
            logger.error(f"❌ Error searching flights: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "search_flights",
                "error": f"Error searching flights: {str(e)}",
                "results_count": 0,
                "flights": [],
                "search_params": {
                    "origin": origin,
                    "destination": destination,
                    "date": departure_date,
                    "adults": adults
                }
            }
    
    async def _search_hotels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search hotels using Amadeus API with error handling"""
        try:
            # ✅ Support both 'location' and 'location_name' parameters
            location = params.get("location") or params.get("location_name", "Tokyo")
            check_in = params.get("check_in")
            check_out = params.get("check_out")
            guests = params.get("guests", 1)
            
            # Validate inputs
            if not location:
                raise AgentException("Location is required")
            if not check_in or not check_out:
                raise AgentException("Check-in and check-out dates are required")
            if guests < 1 or guests > 9:
                raise AgentException("Guests must be between 1 and 9")
            
            # Validate date range
            try:
                check_in_date = datetime.fromisoformat(check_in)
                check_out_date = datetime.fromisoformat(check_out)
                if check_out_date <= check_in_date:
                    raise AgentException("Check-out date must be after check-in date")
            except ValueError:
                raise AgentException("Invalid date format. Use YYYY-MM-DD")
            
            # ✅ Log search parameters for debugging
            logger.info(f"🔍 Searching hotels: {location} from {check_in} to {check_out} for {guests} guest(s)")
            
            results = await self.orchestrator.get_hotels(
                location_name=location,
                check_in=check_in,
                check_out=check_out,
                guests=guests
            )
            
            # ✅ Log raw results count
            logger.info(f"📊 Amadeus API returned {len(results) if results else 0} hotel results")
            
            # ✅ Validate date range before searching
            try:
                from datetime import datetime, timedelta
                check_in_dt = datetime.fromisoformat(check_in)
                check_out_dt = datetime.fromisoformat(check_out)
                today = datetime.now()
                days_ahead = (check_in_dt - today).days
                max_days = 330  # ~11 months
                
                if days_ahead < 0:
                    logger.warning(f"⚠️ Check-in date {check_in} is in the past ({-days_ahead} days ago)")
                elif days_ahead > max_days:
                    logger.warning(
                        f"⚠️ Check-in date {check_in} is {days_ahead} days ahead (max: {max_days} days). "
                        f"Amadeus may not have hotel data for dates this far in the future."
                    )
            except Exception:
                pass
            
            # ✅ FALLBACK: Try date range search if no results found
            if not results or len(results) == 0:
                logger.info(f"⚠️ No hotels found for {check_in} to {check_out}, trying fallback dates...")
                try:
                    from datetime import datetime, timedelta
                    check_in_dt = datetime.fromisoformat(check_in)
                    check_out_dt = datetime.fromisoformat(check_out)
                    nights = (check_out_dt - check_in_dt).days
                    
                    # Try ±1 day for check-in (keep same duration)
                    fallback_dates = [
                        ((check_in_dt + timedelta(days=-1)).strftime("%Y-%m-%d"), 
                         (check_out_dt + timedelta(days=-1)).strftime("%Y-%m-%d")),
                        ((check_in_dt + timedelta(days=1)).strftime("%Y-%m-%d"), 
                         (check_out_dt + timedelta(days=1)).strftime("%Y-%m-%d"))
                    ]
                    
                    # ✅ Parallel fallback searches (with timeout)
                    import asyncio
                    fallback_tasks = []
                    for fb_check_in, fb_check_out in fallback_dates[:1]:  # Limit to 1 fallback for speed
                        task = self.orchestrator.get_hotels(
                            location_name=location,
                            check_in=fb_check_in,
                            check_out=fb_check_out,
                            guests=guests
                        )
                        fallback_tasks.append((fb_check_in, fb_check_out, task))
                    
                    # ✅ Execute fallback searches with 5s timeout
                    try:
                        results_list = await asyncio.wait_for(
                            asyncio.gather(*[task for _, _, task in fallback_tasks], return_exceptions=True),
                            timeout=5.0
                        )
                        
                        # Collect results from fallback searches
                        for (fb_check_in, fb_check_out, _), result in zip(fallback_tasks, results_list):
                            if isinstance(result, Exception):
                                continue
                            if result and len(result) > 0:
                                logger.info(f"✅ Fallback success: Found {len(result)} hotels for {fb_check_in} to {fb_check_out}")
                                # Mark these as fallback results
                                for item in result:
                                    item["_fallback_check_in"] = fb_check_in
                                    item["_fallback_check_out"] = fb_check_out
                                    item["_original_check_in"] = check_in
                                    item["_original_check_out"] = check_out
                                results.extend(result[:3])  # Limit to top 3 from fallback
                                if len(results) >= 3:  # Stop if we have enough results
                                    break
                    except asyncio.TimeoutError:
                        logger.warning(f"⚠️ Fallback hotel searches timed out after 5s")
                except Exception as e:
                    logger.warning(f"⚠️ Fallback date search failed: {e}")
            
            if not results or len(results) == 0:
                # ✅ Check date range for better error message
                try:
                    from datetime import datetime
                    check_in_dt = datetime.fromisoformat(check_in)
                    today = datetime.now()
                    days_ahead = (check_in_dt - today).days
                    max_days = 330
                    
                    date_warning = ""
                    if days_ahead < 0:
                        date_warning = f"⚠️ Check-in date is in the past ({-days_ahead} days ago)"
                    elif days_ahead > max_days:
                        date_warning = f"⚠️ Check-in date is {days_ahead} days ahead (max: {max_days} days) - Amadeus may not have data"
                except Exception:
                    date_warning = ""
                
                logger.error(
                    f"❌ No hotels found in {location} for {check_in} to {check_out} (including fallback dates)\n"
                    f"   Search parameters: location={location}, check_in={check_in}, check_out={check_out}, guests={guests}\n"
                    f"   {date_warning}\n"
                    f"   Possible reasons:\n"
                    f"   1. Date too far in future (Amadeus supports ~11 months ahead)\n"
                    f"   2. No hotels available for this location/dates\n"
                    f"   3. Dates are too close (same-day booking may be limited)\n"
                    f"   4. Location name may be incorrect or too specific\n"
                    f"   5. Amadeus API may not have hotel data for this location"
                )
                return {
                    "success": True,
                    "tool": "search_hotels",
                    "results_count": 0,
                    "hotels": [],
                    "message": f"No hotels found in {location} for {check_in} to {check_out}. {date_warning if 'date_warning' in locals() and date_warning else 'Please try different dates or check location availability.'}",
                    "search_params": {
                        "location": location,
                        "check_in": check_in,
                        "check_out": check_out,
                        "guests": guests
                    },
                    "diagnostics": {
                        "date_warning": date_warning if 'date_warning' in locals() else "",
                        "suggestion": "Try dates within 11 months from today or check if location is available"
                    }
                }
        
            # ✅ Format results for LLM (limit to top 3 for faster processing, but include fallback results)
            formatted = []
            # Separate fallback and original results
            fallback_results = [r for r in results if r.get("_fallback_check_in")]
            original_results = [r for r in results if not r.get("_fallback_check_in")]
            
            # Prioritize original results, then add fallback results
            display_results = (original_results[:3] if len(original_results) >= 3 else original_results) + fallback_results[:2]
            
            for idx, hotel in enumerate(display_results[:3]):  # ✅ Show up to 3 results (prioritize original dates)
                try:
                    hotel_data = hotel.get("hotel", {})
                    offers = hotel.get("offers", [])
                    if not offers:
                        continue
                    
                    first_offer = offers[0]
                    price = first_offer.get("price", {})
                    
                    formatted.append({
                        "option_number": idx + 1,
                        "name": hotel_data.get("name", "Unknown Hotel"),
                        "rating": hotel_data.get("rating", 0),
                        "address": hotel_data.get("address", {}).get("lines", [""])[0] if hotel_data.get("address", {}).get("lines") else "",
                        "price": {
                            "total": price.get("total", "0"),
                            "currency": price.get("currency", "THB")
                        },
                        "room_type": first_offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard")
                    })
                except Exception as e:
                    logger.warning(f"Error formatting hotel {idx + 1}: {e}")
                    continue
            
            return {
                "success": True,
                "tool": "search_hotels",
                "results_count": len(formatted),
                "hotels": formatted,
                "search_params": {
                    "location": location,
                    "check_in": check_in,
                    "check_out": check_out,
                    "guests": guests
                }
            }
        except AmadeusException as e:
            logger.error(f"Amadeus API error in search_hotels: {e}")
            return {
                "success": False,
                "tool": "search_hotels",
                "error": f"Amadeus API error: {str(e)}",
                "search_params": params
            }
        except Exception as e:
            logger.error(f"Unexpected error in search_hotels: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "search_hotels",
                "error": f"Unexpected error: {str(e)}",
                "search_params": params
            }
    
    async def _search_transfers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search transfers using Amadeus API"""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        date = params.get("date", "")
        passengers = params.get("passengers", 1)
        
        # Determine if origin is an airport code; if not, try to resolve it instead of defaulting to BKK
        airport_code = None
        if isinstance(origin, str) and len(origin) == 3 and origin.isupper():
            airport_code = origin
        else:
            try:
                # Use coordinates -> nearest airport as fallback
                loc = await self.orchestrator.get_coordinates(origin)
                airport_code = await self.orchestrator.find_nearest_iata(loc["lat"], loc["lng"])
            except Exception as e:
                logger.error(f"Could not resolve transfer origin airport code from '{origin}': {e}")
                return {
                    "success": False,
                    "tool": "search_transfers",
                    "error": f"Could not resolve origin airport from '{origin}'"
                }
        
        results = await self.orchestrator.get_transfers(
            airport_code=airport_code,
            address=destination
        )
        
        # Format results for LLM
        formatted = []
        for idx, transfer in enumerate(results[:5]):  # Top 5 results
            vehicle = transfer.get("vehicle", {})
            price = transfer.get("price", {})
            
            formatted.append({
                "option_number": idx + 1,
                "vehicle_type": vehicle.get("type", "Car"),
                "category": vehicle.get("category", "Standard"),
                "capacity": vehicle.get("capacity", 0),
                "price": {
                    "total": price.get("total", "0"),
                    "currency": price.get("currency", "THB")
                }
            })
        
        return {
            "success": True,
            "tool": "search_transfers",
            "results_count": len(formatted),
            "transfers": formatted,
            "search_params": {
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers
            }
        }
    
    async def _search_transfers_by_geo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search transfers using exact geo coordinates"""
        start_lat = params.get("start_lat")
        start_lng = params.get("start_lng")
        end_lat = params.get("end_lat")
        end_lng = params.get("end_lng")
        start_time = params.get("start_time")
        passengers = params.get("passengers", 1)
        
        results = await self.orchestrator.get_transfers_by_geo(
            start_lat=start_lat,
            start_lng=start_lng,
            end_lat=end_lat,
            end_lng=end_lng,
            start_time=start_time,
            passengers=passengers
        )
        
        # Format results for LLM
        formatted = []
        for idx, transfer in enumerate(results[:5]):  # Top 5 results
            vehicle = transfer.get("vehicle", {})
            price = transfer.get("price", {})
            quotation = transfer.get("quotation", {})
            
            formatted.append({
                "option_number": idx + 1,
                "vehicle_type": vehicle.get("type", "Car"),
                "category": vehicle.get("category", "Standard"),
                "capacity": vehicle.get("capacity", 0),
                "price": {
                    "total": price.get("total", "0"),
                    "currency": price.get("currency", "THB")
                },
                "provider": transfer.get("transferType", "PRIVATE"),
                "duration": quotation.get("duration", "N/A"),
                "distance": quotation.get("distance", "N/A")
            })
        
        return {
            "success": True,
            "tool": "search_transfers_by_geo",
            "results_count": len(formatted),
            "transfers": formatted,
            "search_params": {
                "start_coords": f"{start_lat},{start_lng}",
                "end_coords": f"{end_lat},{end_lng}",
                "start_time": start_time,
                "passengers": passengers
            }
        }
    
    async def _search_activities(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search activities using Amadeus API"""
        location = params.get("location", "Tokyo")
        radius = params.get("radius", 10)
        
        # Get coordinates first
        try:
            loc_info = await self.orchestrator.get_coordinates(location)
            lat = loc_info["lat"]
            lng = loc_info["lng"]
        except Exception as e:
            logger.warning(f"Could not geocode {location}: {e}")
            # Use default Tokyo coordinates
            lat, lng = 35.6762, 139.6503
        
        results = await self.orchestrator.get_activities(lat, lng)
        
        # Format results for LLM
        formatted = []
        for idx, activity in enumerate(results[:3]):  # ✅ Reduced from 5 to 3 for faster completion
            price = activity.get("price", {})
            
            formatted.append({
                "option_number": idx + 1,
                "name": activity.get("name", "Activity"),
                "description": activity.get("shortDescription", "")[:200],  # Truncate
                "price": {
                    "amount": price.get("amount", "0"),
                    "currency": price.get("currencyCode", "THB")
                },
                "rating": activity.get("rating", 0),
                "pictures": activity.get("pictures", [])[:1]  # First picture only
            })
        
        return {
            "success": True,
            "tool": "search_activities",
            "results_count": len(formatted),
            "activities": formatted,
            "search_params": {
                "location": location,
                "radius": radius
            }
        }
    
    # -------------------------------------------------------------------------
    # Google Maps Tools
    # -------------------------------------------------------------------------
    
    async def _geocode_location(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Geocode a location using Google Maps API"""
        place_name = params.get("place_name", "")
        
        try:
            result = await self.google_maps_client.geocode_location(place_name)
            
            return {
                "success": True,
                "tool": "geocode_location",
                "location": {
                    "place_name": place_name,
                    "latitude": result["lat"],
                    "longitude": result["lng"],
                    "formatted_address": result["address"]
                }
            }
        except Exception as e:
            logger.error(f"Geocode location failed: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "geocode_location",
                "error": f"Could not geocode '{place_name}': {str(e)}"
            }
    
    async def _find_nearest_airport(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Find nearest airport IATA code"""
        location = params.get("location", "")
        
        try:
            loc_info = await self.orchestrator.get_coordinates(location)
            iata = await self.orchestrator.find_nearest_iata(loc_info["lat"], loc_info["lng"])
            
            return {
                "success": True,
                "tool": "find_nearest_airport",
                "location": location,
                "nearest_airport": {
                    "iata_code": iata,
                    "coordinates": {
                        "latitude": loc_info["lat"],
                        "longitude": loc_info["lng"]
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "tool": "find_nearest_airport",
                "error": f"Could not find airport for '{location}': {str(e)}"
            }
    
    async def _search_nearby_places(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for nearby places using Google Maps API"""
        keyword = params.get("keyword", "")
        lat = params.get("lat")
        lng = params.get("lng")
        radius = params.get("radius", 1000)
        
        try:
            results = await self.google_maps_client.search_nearby_places(
                keyword=keyword,
                lat=lat,
                lng=lng,
                radius=radius
            )
            
            return {
                "success": True,
                "tool": "search_nearby_places",
                "results_count": len(results),
                "places": results,
                "search_params": {
                    "keyword": keyword,
                    "location": f"{lat},{lng}",
                    "radius": radius
                }
            }
        except Exception as e:
            logger.error(f"Search nearby places failed: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "search_nearby_places",
                "error": f"Could not search nearby places: {str(e)}"
            }
    
    async def _get_place_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get place details using Google Maps API"""
        place_id = params.get("place_id", "")
        
        try:
            result = await self.google_maps_client.get_place_details(place_id)
            
            return {
                "success": True,
                "tool": "get_place_details",
                "place": {
                    "place_id": place_id,
                    "formatted_address": result["formatted_address"],
                    "opening_hours": result["opening_hours"],
                    "photo_reference": result["photo_reference"],
                    "review_summary": result["review_summary"],
                    "rating": result["rating"],
                    "user_ratings_total": result["user_ratings_total"]
                }
            }
        except Exception as e:
            logger.error(f"Get place details failed: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "get_place_details",
                "error": f"Could not get details for place_id '{place_id}': {str(e)}"
            }
    
    async def _plan_route(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a route using Google Maps Directions API"""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        travel_mode = params.get("travel_mode", "driving")
        
        try:
            # Geocode origin and destination
            origin_info = await self.orchestrator.get_coordinates(origin)
            dest_info = await self.orchestrator.get_coordinates(destination)
            
            # Calculate straight-line distance
            from math import radians, sin, cos, sqrt, atan2
            lat1, lon1 = radians(origin_info["lat"]), radians(origin_info["lng"])
            lat2, lon2 = radians(dest_info["lat"]), radians(dest_info["lng"])
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            distance_km = 6371 * c  # Earth radius in km
            
            # Determine recommended transportation methods
            recommended_transport = []
            if distance_km > 500:
                recommended_transport.append("flight")
            if distance_km < 100:
                recommended_transport.extend(["car", "bus"])
            if distance_km > 100 and distance_km < 500:
                recommended_transport.extend(["train", "bus", "car"])
            # Always check if water route is possible (islands, coastal)
            recommended_transport.append("boat")  # Can be filtered later
            
            # Find nearest airports for origin and destination
            origin_airport = None
            dest_airport = None
            try:
                origin_airport_iata = await self.orchestrator.find_nearest_iata(origin_info["lat"], origin_info["lng"])
                origin_airport = origin_airport_iata
            except:
                pass
            
            try:
                dest_airport_iata = await self.orchestrator.find_nearest_iata(dest_info["lat"], dest_info["lng"])
                dest_airport = dest_airport_iata
            except:
                pass
            
            # Use Google Maps Directions API if available
            route_info = None
            if self.orchestrator.gmaps:
                try:
                    loop = asyncio.get_event_loop()
                    directions_result = await loop.run_in_executor(
                        None,
                        lambda: self.orchestrator.gmaps.directions(
                            origin=f"{origin_info['lat']},{origin_info['lng']}",
                            destination=f"{dest_info['lat']},{dest_info['lng']}",
                            mode=travel_mode
                        )
                    )
                    
                    if directions_result:
                        route = directions_result[0]
                        leg = route["legs"][0]
                        route_info = {
                            "distance_text": leg["distance"]["text"],
                            "distance_meters": leg["distance"]["value"],
                            "duration_text": leg["duration"]["text"],
                            "duration_seconds": leg["duration"]["value"],
                            "steps": len(route["legs"][0].get("steps", [])),
                            "polyline": route["overview_polyline"]["points"] if "overview_polyline" in route else None
                        }
                except Exception as e:
                    logger.warning(f"Google Maps Directions API call failed: {e}")
            
            return {
                "success": True,
                "tool": "plan_route",
                "route": {
                    "origin": {
                        "location": origin,
                        "coordinates": {"latitude": origin_info["lat"], "longitude": origin_info["lng"]},
                        "nearest_airport": origin_airport
                    },
                    "destination": {
                        "location": destination,
                        "coordinates": {"latitude": dest_info["lat"], "longitude": dest_info["lng"]},
                        "nearest_airport": dest_airport
                    },
                    "distance_km": round(distance_km, 2),
                    "recommended_transportation": recommended_transport,
                    "route_details": route_info
                }
            }
        except Exception as e:
            return {
                "success": False,
                "tool": "plan_route",
                "error": f"Could not plan route: {str(e)}"
            }
    
    async def _compare_transport_modes(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Compare transport modes using Google Maps API"""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        
        try:
            route_options = await self.google_maps_client.get_route_options(origin, destination)
            
            return {
                "success": True,
                "tool": "compare_transport_modes",
                "route_options": route_options,
                "origin": origin,
                "destination": destination
            }
        except Exception as e:
            logger.error(f"Compare transport modes failed: {e}", exc_info=True)
            return {
                "success": False,
                "tool": "compare_transport_modes",
                "error": f"Could not compare transport modes: {str(e)}"
            }
    
    async def close(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'orchestrator') and self.orchestrator:
                await self.orchestrator.close()
            logger.info("MCPToolExecutor closed successfully")
        except Exception as e:
            logger.warning(f"Error closing MCPToolExecutor: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check for MCP service
        
        Returns:
            Health status dictionary
        """
        try:
            # Check if orchestrator is initialized
            has_orchestrator = hasattr(self, 'orchestrator') and self.orchestrator is not None
            
            return {
                "status": "healthy" if has_orchestrator else "degraded",
                "orchestrator": "initialized" if has_orchestrator else "not_initialized",
                "tools_count": len(ALL_MCP_TOOLS),
                "max_retries": self.max_retries,
                "timeout": self.timeout
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }


# Global instance
mcp_executor = MCPToolExecutor()

