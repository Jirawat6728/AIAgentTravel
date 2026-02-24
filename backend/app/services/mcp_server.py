"""
เซิร์ฟเวอร์ MCP (Model Context Protocol) สำหรับ AI Travel Agent
ประสาน Amadeus MCP และ Google Maps MCP ให้ LLM เรียกใช้ tools แบบรวม
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
import asyncio

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

# Non-retryable exceptions: validation errors and unknown tool errors should not be retried
_NON_RETRYABLE = (AgentException,)


# =============================================================================
# MCP Tool Executor
# =============================================================================

class MCPToolExecutor:
    """
    Production-Grade MCP Tool Executor
    Executes MCP tools (function calls) for LLM with robust error handling

    Features:
    - Retry logic with exponential backoff (only for transient errors)
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
            # GoogleMapsMCP shares the same orchestrator — close() is guarded to avoid double-close
            self.google_maps_mcp = GoogleMapsMCP(self.google_maps_client, self.orchestrator)
            self.weather_mcp = WeatherMCP(self.orchestrator)
            self.max_retries = MCP_MAX_RETRIES
            self.timeout = MCP_TIMEOUT_SECONDS
            logger.info(
                f"MCPToolExecutor initialized (AmadeusMCP + GoogleMapsMCP + WeatherMCP, "
                f"retries={self.max_retries}, timeout={self.timeout}s)"
            )
        except Exception as e:
            logger.error(f"Failed to initialize MCPToolExecutor: {e}", exc_info=True)
            raise

    def _validate_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize tool parameters.
        Pass-through all parameters (including optional extras like children/infants)
        so that tool implementations can use them even if not in the schema.
        """
        # Get tool definition to check required fields
        tool_def = next((t for t in ALL_MCP_TOOLS if t["name"] == tool_name), None)
        if not tool_def:
            raise AgentException(f"Unknown tool: {tool_name}")

        required = tool_def["parameters"].get("required", [])
        properties = tool_def["parameters"].get("properties", {})

        validated: Dict[str, Any] = {}

        # ── Validate required fields ──────────────────────────────────────────
        for field in required:
            # Special case: search_hotels accepts 'location' or 'location_name'
            if tool_name == "search_hotels" and field == "location":
                val = parameters.get("location") or parameters.get("location_name")
                if not val:
                    raise AgentException("Missing required parameter: 'location' or 'location_name'")
                validated[field] = val

            # Special case: get_weather_forecast accepts place_name OR lat+lng
            elif tool_name == "get_weather_forecast" and field == "place_name":
                if parameters.get("place_name") or (
                    parameters.get("latitude") is not None and parameters.get("longitude") is not None
                ):
                    validated[field] = parameters.get("place_name") or ""
                else:
                    raise AgentException("Missing required parameter: place_name or (latitude and longitude)")

            # Special case: search_transfers_by_geo — accept both short and long names
            elif tool_name == "search_transfers_by_geo":
                alias_map = {
                    "start_lat": ["start_lat", "start_latitude"],
                    "start_lng": ["start_lng", "start_longitude"],
                    "end_lat":   ["end_lat",   "end_latitude"],
                    "end_lng":   ["end_lng",   "end_longitude"],
                    "start_time": ["start_time"],
                }
                if field in alias_map:
                    val = None
                    for alias in alias_map[field]:
                        if parameters.get(alias) is not None:
                            val = parameters[alias]
                            break
                    if val is None:
                        raise AgentException(f"Missing required parameter: {field}")
                    validated[field] = val
                elif field not in parameters or parameters[field] is None:
                    raise AgentException(f"Missing required parameter: {field}")
                else:
                    validated[field] = parameters[field]

            elif field not in parameters or parameters[field] is None:
                raise AgentException(f"Missing required parameter: {field}")
            else:
                validated[field] = parameters[field]

        # ── Copy schema-defined optional fields with defaults ─────────────────
        for field, prop_def in properties.items():
            if field not in validated:
                if field in parameters:
                    validated[field] = parameters[field]
                elif "default" in prop_def:
                    validated[field] = prop_def["default"]

        # ── Pass-through extra parameters not in schema (e.g. children, infants, non_stop) ──
        for key, value in parameters.items():
            if key not in validated:
                validated[key] = value

        # ── Sanitize string inputs ────────────────────────────────────────────
        for key, value in validated.items():
            if isinstance(value, str):
                validated[key] = value.strip()[:500]

        return validated

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool by name with given parameters.
        Retries up to MCP_MAX_RETRIES times for transient (non-validation) errors.
        Validation errors (AgentException) are returned immediately without retry.
        """
        logger.info(f"Executing MCP tool: {tool_name} with params: {parameters}")

        # Validate first — do NOT retry on validation failures
        try:
            validated_params = self._validate_parameters(tool_name, parameters)
        except AgentException as e:
            logger.warning(f"MCP tool {tool_name} validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
            }

        last_error: Optional[Exception] = None
        for attempt in range(1, MCP_MAX_RETRIES + 1):
            try:
                result = await asyncio.wait_for(
                    self._execute_tool_internal(tool_name, validated_params),
                    timeout=self.timeout,
                )

                if not isinstance(result, dict):
                    raise AgentException(f"Tool {tool_name} returned invalid result type: {type(result)}")

                if "success" not in result:
                    result["success"] = True

                logger.info(f"MCP tool {tool_name} executed successfully (attempt {attempt})")
                return result

            except asyncio.TimeoutError:
                logger.error(f"MCP tool {tool_name} timed out after {self.timeout}s (attempt {attempt})")
                # Timeout is transient — retry
                last_error = asyncio.TimeoutError(f"Tool execution timed out after {self.timeout} seconds")

            except _NON_RETRYABLE as e:
                # Validation / logic errors — do not retry
                logger.warning(f"MCP tool {tool_name} non-retryable error: {e}")
                return {"success": False, "error": str(e), "tool": tool_name}

            except Exception as e:
                logger.warning(f"MCP tool {tool_name} transient error (attempt {attempt}): {e}")
                last_error = e

            if attempt < MCP_MAX_RETRIES:
                await asyncio.sleep(MCP_RETRY_DELAY * attempt)

        logger.error(f"MCP tool {tool_name} failed after {MCP_MAX_RETRIES} attempts: {last_error}")
        return {
            "success": False,
            "error": str(last_error)[:200] if last_error else "Unknown error",
            "tool": tool_name,
        }

    async def _execute_tool_internal(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Internal tool execution: route to the appropriate MCP sub-executor."""
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
        """Cleanup resources. Orchestrator is shared — close only once via amadeus_mcp."""
        try:
            if hasattr(self, "amadeus_mcp") and self.amadeus_mcp:
                await self.amadeus_mcp.close()
            # GoogleMapsMCP shares the same orchestrator — skip its close() to avoid double-close
            if hasattr(self, "weather_mcp") and self.weather_mcp:
                await self.weather_mcp.close()
            logger.info("MCPToolExecutor closed successfully")
        except Exception as e:
            logger.warning(f"Error closing MCPToolExecutor: {e}")

    def health_check(self) -> Dict[str, Any]:
        """Health check for all MCP sub-services."""
        try:
            has_orchestrator = bool(getattr(self, "orchestrator", None))
            has_amadeus = bool(getattr(self, "amadeus_mcp", None))
            has_gmaps = bool(getattr(self, "google_maps_mcp", None))
            has_weather = bool(getattr(self, "weather_mcp", None))
            all_healthy = all([has_orchestrator, has_amadeus, has_gmaps, has_weather])
            return {
                "status": "healthy" if all_healthy else "degraded",
                "orchestrator": "initialized" if has_orchestrator else "missing",
                "amadeus_mcp": "initialized" if has_amadeus else "missing",
                "google_maps_mcp": "initialized" if has_gmaps else "missing",
                "weather_mcp": "initialized" if has_weather else "missing",
                "tools_count": len(ALL_MCP_TOOLS),
                "max_retries": self.max_retries,
                "timeout": self.timeout,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Global instance — lazy to avoid import-time failures when config is missing
_mcp_executor: Optional[MCPToolExecutor] = None


def get_mcp_executor() -> MCPToolExecutor:
    global _mcp_executor
    if _mcp_executor is None:
        _mcp_executor = MCPToolExecutor()
    return _mcp_executor


# Backward-compatible alias (instantiated lazily on first access)
class _LazyMCPExecutor:
    """Proxy that creates MCPToolExecutor on first use, not at import time."""
    _instance: Optional[MCPToolExecutor] = None

    def __getattr__(self, name: str):
        if self._instance is None:
            object.__setattr__(self, "_instance", MCPToolExecutor())
        return getattr(self._instance, name)


mcp_executor: Any = _LazyMCPExecutor()
