"""
Model Context Protocol (MCP) Server for AI Travel Agent
Provides tools for Amadeus API and Google Maps to LLM
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Callable
import json
import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.core.config import settings
from app.core.exceptions import AmadeusException, AgentException
from app.services.travel_service import TravelOrchestrator

logger = get_logger(__name__)


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
        "name": "get_place_details",
        "description": "Get detailed information about a place including address, rating, and opening hours using Google Maps API.",
        "parameters": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "Place name or business name"
                }
            },
            "required": ["place_name"]
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
    Executes MCP tools (function calls) for LLM
    Integrates with TravelOrchestrator for actual API calls
    """
    
    def __init__(self):
        self.orchestrator = TravelOrchestrator()
        logger.info("MCPToolExecutor initialized with TravelOrchestrator")
    
    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters as dictionary
            
        Returns:
            Tool execution result as dictionary
        """
        try:
            logger.info(f"Executing MCP tool: {tool_name} with params: {parameters}")
            
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
            elif tool_name == "find_nearest_airport":
                return await self._find_nearest_airport(parameters)
            elif tool_name == "get_place_details":
                return await self._get_place_details(parameters)
            else:
                raise AgentException(f"Unknown tool: {tool_name}")
        
        except Exception as e:
            logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }
    
    # -------------------------------------------------------------------------
    # Amadeus Tools
    # -------------------------------------------------------------------------
    
    async def _search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights using Amadeus API"""
        origin = params.get("origin", "BKK")
        destination = params.get("destination", "NRT")
        departure_date = params.get("departure_date")
        adults = params.get("adults", 1)
        
        results = await self.orchestrator.get_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            adults=adults
        )
        
        # Format results for LLM
        formatted = []
        for idx, flight in enumerate(results[:5]):  # Top 5 results
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
    
    async def _search_hotels(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search hotels using Amadeus API"""
        location = params.get("location", "Tokyo")
        check_in = params.get("check_in")
        check_out = params.get("check_out")
        guests = params.get("guests", 1)
        
        results = await self.orchestrator.get_hotels(
            location_name=location,
            check_in=check_in,
            check_out=check_out,
            guests=guests
        )
        
        # Format results for LLM
        formatted = []
        for idx, hotel in enumerate(results[:5]):  # Top 5 results
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
                "address": hotel_data.get("address", {}).get("lines", [""])[0],
                "price": {
                    "total": price.get("total", "0"),
                    "currency": price.get("currency", "THB")
                },
                "room_type": first_offer.get("room", {}).get("typeEstimated", {}).get("category", "Standard")
            })
        
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
    
    async def _search_transfers(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search transfers using Amadeus API"""
        origin = params.get("origin", "")
        destination = params.get("destination", "")
        date = params.get("date", "")
        passengers = params.get("passengers", 1)
        
        # Determine if origin is an airport code
        airport_code = origin if len(origin) == 3 and origin.isupper() else "BKK"
        
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
        for idx, activity in enumerate(results[:5]):  # Top 5 results
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
            loc_info = await self.orchestrator.get_coordinates(place_name)
            
            return {
                "success": True,
                "tool": "geocode_location",
                "location": {
                    "place_name": place_name,
                    "latitude": loc_info["lat"],
                    "longitude": loc_info["lng"],
                    "formatted_address": loc_info["address"],
                    "city": loc_info["city"]
                }
            }
        except Exception as e:
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
    
    async def _get_place_details(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get place details using Google Maps API"""
        place_name = params.get("place_name", "")
        
        try:
            # Use geocoding as a basic place details lookup
            loc_info = await self.orchestrator.get_coordinates(place_name)
            
            return {
                "success": True,
                "tool": "get_place_details",
                "place": {
                    "name": place_name,
                    "address": loc_info["address"],
                    "city": loc_info["city"],
                    "coordinates": {
                        "latitude": loc_info["lat"],
                        "longitude": loc_info["lng"]
                    }
                }
            }
        except Exception as e:
            return {
                "success": False,
                "tool": "get_place_details",
                "error": f"Could not get details for '{place_name}': {str(e)}"
            }
    
    async def close(self):
        """Cleanup resources"""
        await self.orchestrator.close()


# Global instance
mcp_executor = MCPToolExecutor()

