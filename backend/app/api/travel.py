"""
เราเตอร์ API การเดินทางแบบรวม
เปิด Smart Search และจุดหมายยอดนิยมให้ AI Agent (ไม่ต้องใช้ frontend)
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from typing import Optional
from app.services.travel_service import (
    orchestrator,
    TravelSearchRequest,
    UnifiedTravelResponse,
)
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.exceptions import AmadeusException, AgentException

logger = get_logger(__name__)

router = APIRouter(prefix="/api/travel", tags=["travel"])


@router.post("/smart-search", response_model=UnifiedTravelResponse)
async def smart_search(request: TravelSearchRequest):
    """
    One Endpoint for All: Detects intent and aggregates travel data.
    Request: {query: string, user_id?: string, context?: object}. Use natural-language query only.
    Output: intent, flights, hotels, rentals, transfers, activities, popular_destinations, summary.
    Supports: เที่ยวบิน, โรงแรม, ที่พักให้เช่า, transfer, กิจกรรม, จุดหมายยอดนิยม.
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


@router.get("/popular-destinations")
async def popular_destinations(
    lat: Optional[float] = Query(None, description="User latitude for context"),
    lng: Optional[float] = Query(None, description="User longitude for context"),
):
    """
    จุดหมายยอดนิยม (Popular Destinations) for AI Agent.
    Returns curated destinations (e.g. Seoul, Tokyo, Koh Samui) with sample dates and descriptions.
    No frontend required - data only.
    """
    set_logging_context(user_id="anonymous")
    try:
        result = await orchestrator.get_popular_destinations(user_lat=lat, user_lng=lng)
        return {"popular_destinations": result, "count": len(result)}
    except Exception as e:
        logger.error(f"Popular destinations error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="An internal server error occurred.")
    finally:
        clear_logging_context()


@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup httpx client on shutdown"""
    await orchestrator.close()
