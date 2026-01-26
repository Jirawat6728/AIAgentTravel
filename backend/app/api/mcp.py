"""
MCP (Model Context Protocol) API Endpoints
Exposes MCP tools as REST API for testing and external use
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from app.services.mcp_server import mcp_executor, ALL_MCP_TOOLS
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/mcp", tags=["MCP"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ToolExecutionRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool to execute")
    parameters: Dict[str, Any] = Field(..., description="Tool parameters")

class ToolExecutionResponse(BaseModel):
    success: bool
    tool: str
    result: Dict[str, Any]
    error: Optional[str] = None

class ToolListResponse(BaseModel):
    tools: List[Dict[str, Any]]
    count: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/tools", response_model=ToolListResponse)
async def list_tools():
    """
    List all available MCP tools
    """
    return {
        "tools": ALL_MCP_TOOLS,
        "count": len(ALL_MCP_TOOLS)
    }


@router.get("/health")
async def health_check():
    """
    Health check for MCP service
    """
    try:
        health = mcp_executor.health_check()
        status_code = 200 if health.get("status") == "healthy" else 503
        return health
    except Exception as e:
        logger.error(f"MCP health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.post("/execute", response_model=ToolExecutionResponse)
async def execute_tool(request: ToolExecutionRequest):
    """
    Execute a specific MCP tool
    
    Example:
    ```json
    {
      "tool_name": "search_flights",
      "parameters": {
        "origin": "BKK",
        "destination": "NRT",
        "departure_date": "2025-02-15",
        "adults": 2
      }
    }
    ```
    """
    try:
        result = await mcp_executor.execute_tool(
            tool_name=request.tool_name,
            parameters=request.parameters
        )
        
        # Check if execution was successful
        if not result.get("success", False):
            error_msg = result.get("error", "Unknown error")
            logger.warning(f"Tool {request.tool_name} returned error: {error_msg}")
            # Return 200 with error in response (not HTTP error)
            return {
                "success": False,
                "tool": request.tool_name,
                "result": result,
                "error": error_msg
            }
        
        return {
            "success": True,
            "tool": request.tool_name,
            "result": result,
            "error": None
        }
    
    except Exception as e:
        logger.error(f"Tool execution failed: {e}", exc_info=True)
        return {
            "success": False,
            "tool": request.tool_name,
            "result": {},
            "error": str(e)
        }


@router.post("/search/flights")
async def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    adults: int = 1,
    return_date: Optional[str] = None
):
    """
    Convenience endpoint for flight search
    """
    result = await mcp_executor.execute_tool(
        tool_name="search_flights",
        parameters={
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults,
            "return_date": return_date
        }
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))
    
    return result


@router.post("/search/hotels")
async def search_hotels(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 1
):
    """
    Convenience endpoint for hotel search
    """
    result = await mcp_executor.execute_tool(
        tool_name="search_hotels",
        parameters={
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests
        }
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))
    
    return result


@router.post("/search/transfers")
async def search_transfers(
    origin: str,
    destination: str,
    date: str,
    passengers: int = 1
):
    """
    Convenience endpoint for transfer search
    """
    result = await mcp_executor.execute_tool(
        tool_name="search_transfers",
        parameters={
            "origin": origin,
            "destination": destination,
            "date": date,
            "passengers": passengers
        }
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))
    
    return result


@router.post("/search/activities")
async def search_activities(
    location: str,
    radius: int = 10
):
    """
    Convenience endpoint for activity search
    """
    result = await mcp_executor.execute_tool(
        tool_name="search_activities",
        parameters={
            "location": location,
            "radius": radius
        }
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Search failed"))
    
    return result


@router.post("/geocode")
async def geocode_location(place_name: str):
    """
    Convenience endpoint for geocoding
    """
    result = await mcp_executor.execute_tool(
        tool_name="geocode_location",
        parameters={"place_name": place_name}
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Geocoding failed"))
    
    return result


@router.post("/airport")
async def find_nearest_airport(location: str):
    """
    Convenience endpoint for finding nearest airport
    """
    result = await mcp_executor.execute_tool(
        tool_name="find_nearest_airport",
        parameters={"location": location}
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Airport search failed"))
    
    return result

