"""
Endpoint API การตรวจสอบระบบ
ให้เข้าถึงการติดตามต้นทุน (Amadeus-only, ไม่มี workflow)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime

from app.engine.cost_tracker import cost_tracker
from app.storage.connection_manager import MongoConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/cost/session/{session_id}")
async def get_session_cost(session_id: str) -> Dict[str, Any]:
    """
    Get cost summary for a specific session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Cost summary with breakdown
    """
    try:
        summary = cost_tracker.get_session_summary(session_id)
        
        if not summary:
            return {
                "ok": False,
                "message": "No cost data found for this session",
                "session_id": session_id
            }
        
        return {
            "ok": True,
            "session_id": session_id,
            "cost_summary": summary.to_dict()
        }
    except Exception as e:
        logger.error(f"Error getting session cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/all")
async def get_all_costs(
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="Max sessions to return")
) -> Dict[str, Any]:
    """
    Get cost data for all sessions
    
    Args:
        limit: Maximum number of sessions to return
        
    Returns:
        All cost data
    """
    try:
        export_data = cost_tracker.export_to_dict()
        
        # Limit sessions if requested
        if "sessions" in export_data and len(export_data["sessions"]) > limit:
            export_data["sessions"] = sorted(
                export_data["sessions"],
                key=lambda x: x.get("last_updated", ""),
                reverse=True
            )[:limit]
            export_data["note"] = f"Showing latest {limit} sessions"
        
        return {
            "ok": True,
            "timestamp": datetime.utcnow().isoformat(),
            "data": export_data
        }
    except Exception as e:
        logger.error(f"Error getting all costs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cost/breakdown/{session_id}")
async def get_cost_breakdown(session_id: str) -> Dict[str, Any]:
    """
    Get cost breakdown by brain type for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Cost breakdown by brain type
    """
    try:
        breakdown = cost_tracker.get_cost_by_brain_type(session_id)
        
        if not breakdown:
            return {
                "ok": False,
                "message": "No cost data found for this session",
                "session_id": session_id
            }
        
        return {
            "ok": True,
            "session_id": session_id,
            "breakdown": breakdown,
            "total_usd": sum(breakdown.values()),
            "total_thb": sum(breakdown.values()) * 35
        }
    except Exception as e:
        logger.error(f"Error getting cost breakdown: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cost/reset/{session_id}")
async def reset_session_cost(session_id: str) -> Dict[str, Any]:
    """
    Reset cost tracking for a session
    
    Args:
        session_id: Session identifier
        
    Returns:
        Success message
    """
    try:
        cost_tracker.reset_session(session_id)
        
        return {
            "ok": True,
            "message": f"Cost tracking reset for session {session_id}"
        }
    except Exception as e:
        logger.error(f"Error resetting cost: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def monitoring_health() -> Dict[str, Any]:
    """Health check for monitoring endpoints"""
    try:
        total_sessions = len(cost_tracker.get_all_sessions())
        
        return {
            "ok": True,
            "service": "monitoring",
            "timestamp": datetime.utcnow().isoformat(),
            "stats": {
                "tracked_sessions": total_sessions
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Redis Sync Endpoints (no-op — Redis removed, using MongoDB 100%)
# =============================================================================

@router.post("/sync/redis/session/{session_id}")
async def sync_session_from_redis(session_id: str) -> Dict[str, Any]:
    """No-op: Redis removed — data is already in MongoDB."""
    return {"ok": True, "session_id": session_id, "message": "MongoDB-only mode: no sync needed"}


@router.post("/sync/redis/all")
async def sync_all_from_redis() -> Dict[str, Any]:
    """No-op: Redis removed — data is already in MongoDB."""
    return {"ok": True, "message": "MongoDB-only mode: no sync needed", "stats": {}}


@router.get("/sync/redis/status")
async def get_sync_status() -> Dict[str, Any]:
    """No-op: Redis removed."""
    return {
        "ok": True,
        "timestamp": datetime.utcnow().isoformat(),
        "status": {"redis_available": False, "redis_removed": True, "message": "Redis removed — using MongoDB only"}
    }
