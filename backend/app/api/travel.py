"""
Unified Travel API Router
Exposes the Smart Search endpoint for natural language travel queries.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.services.travel_service import orchestrator, TravelSearchRequest, UnifiedTravelResponse
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.exceptions import AmadeusException, AgentException

logger = get_logger(__name__)

router = APIRouter(prefix="/api/travel", tags=["travel"])

@router.post("/smart-search", response_model=UnifiedTravelResponse)
async def smart_search(request: TravelSearchRequest):
    """
    One Endpoint for All: Detects intent and aggregates travel data
    - Input: Natural language query (e.g., "จองตั๋วบินไปโตเกียว")
    - Output: Aggregated data (Flights, Hotels, Activities, Transfers)
    """
    set_logging_context(user_id=request.user_id)
    try:
        logger.info(f"Smart Search request: {request.query}")
        result = await orchestrator.smart_search(request)
        return result
    except (AmadeusException, AgentException) as e:
        logger.error(f"Travel service error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in smart search: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        clear_logging_context()

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup httpx client on shutdown"""
    await orchestrator.close()

