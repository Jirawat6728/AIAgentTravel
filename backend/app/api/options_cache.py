"""
API endpoints for options cache
ให้ AI และ TripSummary ดึงข้อมูลจาก cache
"""

from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from app.services.options_cache import get_options_cache
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/api/options-cache", tags=["options-cache"])


@router.get("/session/{session_id}")
async def get_session_cache(session_id: str):
    """
    ดึงข้อมูล cache ทั้งหมดของ session
    
    Returns:
        Dictionary with all cached options organized by slot
    """
    try:
        options_cache = get_options_cache()
        all_options = await options_cache.get_all_session_options(session_id)
        
        return {
            "session_id": session_id,
            "options": all_options,
            "summary": {
                "flights_outbound": sum(len(opts) for opts in all_options.get("flights_outbound", [])),
                "flights_inbound": sum(len(opts) for opts in all_options.get("flights_inbound", [])),
                "ground_transport": sum(len(opts) for opts in all_options.get("ground_transport", [])),
                "accommodation": sum(len(opts) for opts in all_options.get("accommodation", []))
            }
        }
    except Exception as e:
        logger.error(f"Failed to get session cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get cache: {str(e)}")


@router.get("/session/{session_id}/validate")
async def validate_session_cache(session_id: str):
    """
    Validate cached data for a session
    
    Returns:
        Validation result with status and issues
    """
    try:
        options_cache = get_options_cache()
        validation_result = await options_cache.validate_cache_data(session_id)
        
        return {
            "session_id": session_id,
            **validation_result
        }
    except Exception as e:
        logger.error(f"Failed to validate session cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to validate cache: {str(e)}")


@router.delete("/session/{session_id}")
async def clear_session_cache(session_id: str):
    """
    Clear all cached options for a session
    """
    try:
        options_cache = get_options_cache()
        success = await options_cache.clear_session_cache(session_id)
        
        if success:
            return {"message": f"Cache cleared for session {session_id}", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to clear cache")
    except Exception as e:
        logger.error(f"Failed to clear session cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
