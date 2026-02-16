"""
เซิร์ฟเวอร์ MCP (Model Context Protocol) สำหรับ AI Travel Agent
ประสาน Amadeus MCP และ Google Maps MCP ให้ LLM เรียกใช้ tools แบบรวม
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.core.exceptions import AmadeusException, AgentException
from app.services.travel_service import TravelOrchestrator
from app.services.google_maps_client import get_google_maps_client
from app.services.mcp_amadeus import AMADEUS_TOOLS, AmadeusMCP
from app.services.mcp_google_maps import GOOGLE_MAPS_TOOLS, GoogleMapsMCP
from app.services.mcp_weather import WEATHER_TOOLS, WeatherMCP

logger = get_logger(__name__)

# MCP Configuration
MCP_MAX_RETRIES = 3
MCP_TIMEOUT_SECONDS = 15
MCP_RETRY_DELAY = 2

# Re-export for backward compatibility
__all__ = ["AMADEUS_TOOLS", "GOOGLE_MAPS_TOOLS", "WEATHER_TOOLS", "ALL_MCP_TOOLS", "MCPToolExecutor", "mcp_executor"]

# All tools combined (Amadeus + Google Maps + Weather/Timezone)
ALL_MCP_TOOLS = AMADEUS_TOOLS + GOOGLE_MAPS_TOOLS + WEATHER_TOOLS


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
            self.amadeus_mcp = AmadeusMCP(self.orchestrator)
            self.google_maps_mcp = GoogleMapsMCP(self.google_maps_client, self.orchestrator)
            self.weather_mcp = WeatherMCP(self.orchestrator)
            self.max_retries = MCP_MAX_RETRIES
            self.timeout = MCP_TIMEOUT_SECONDS
            logger.info(
                f"MCPToolExecutor initialized (AmadeusMCP + GoogleMapsMCP + WeatherMCP, retries={self.max_retries}, timeout={self.timeout}s)"
            )
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
        
        # Validate required fields (with special handling for search_hotels, get_weather_forecast)
        for field in required:
            # ✅ Special case: search_hotels accepts either 'location' or 'location_name'
            if tool_name == "search_hotels" and field == "location":
                if "location" not in parameters and "location_name" not in parameters:
                    raise AgentException(f"Missing required parameter: 'location' or 'location_name'")
                validated[field] = parameters.get("location") or parameters.get("location_name")
            # ✅ Special case: get_weather_forecast accepts place_name OR (latitude + longitude)
            elif tool_name == "get_weather_forecast" and field == "place_name":
                if parameters.get("place_name") or (parameters.get("latitude") is not None and parameters.get("longitude") is not None):
                    validated[field] = parameters.get("place_name") or ""
                else:
                    raise AgentException("Missing required parameter: place_name or (latitude and longitude)")
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
        """Internal tool execution: route to Amadeus MCP or Google Maps MCP."""
        # Amadeus tools
        if tool_name == "search_flights":
            return await self.amadeus_mcp.search_flights(parameters)
        if tool_name == "search_hotels":
            return await self.amadeus_mcp.search_hotels(parameters)
        if tool_name == "search_transfers":
            return await self.amadeus_mcp.search_transfers(parameters)
        if tool_name == "search_transfers_by_geo":
            return await self.amadeus_mcp.search_transfers_by_geo(parameters)
        if tool_name == "search_activities":
            return await self.amadeus_mcp.search_activities(parameters)
        # Google Maps tools
        if tool_name == "geocode_location":
            return await self.google_maps_mcp.geocode_location(parameters)
        if tool_name == "find_nearest_airport":
            return await self.google_maps_mcp.find_nearest_airport(parameters)
        if tool_name == "search_nearby_places":
            return await self.google_maps_mcp.search_nearby_places(parameters)
        if tool_name == "get_place_details":
            return await self.google_maps_mcp.get_place_details(parameters)
        if tool_name == "plan_route":
            return await self.google_maps_mcp.plan_route(parameters)
        if tool_name == "plan_route_with_waypoints":
            return await self.google_maps_mcp.plan_route_with_waypoints(parameters)
        if tool_name == "compare_transport_modes":
            return await self.google_maps_mcp.compare_transport_modes(parameters)
        # Weather & Timezone
        if tool_name == "get_weather_forecast":
            return await self.weather_mcp.get_weather_forecast(parameters)
        if tool_name == "get_destination_timezone":
            return await self.weather_mcp.get_destination_timezone(parameters)
        raise AgentException(f"Unknown tool: {tool_name}")
    
    async def close(self):
        """Cleanup resources (Amadeus MCP + Google Maps MCP)."""
        try:
            if hasattr(self, "amadeus_mcp") and self.amadeus_mcp:
                await self.amadeus_mcp.close()
            if hasattr(self, "google_maps_mcp") and self.google_maps_mcp:
                await self.google_maps_mcp.close()
            if hasattr(self, "weather_mcp") and self.weather_mcp:
                await self.weather_mcp.close()
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

