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
from app.core.redis_client import is_redis_available
from app.core.config import settings
from app.services.agent_monitor import agent_monitor

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


@router.get("/search-relaxed/summary")
async def get_search_relaxed_summary() -> Dict[str, Any]:
    """
    สรุป telemetry ของ relaxed search fallback เพื่อดูว่าปัญหา no-choice เกิดจากเงื่อนไขแบบใดบ่อยที่สุด
    """
    try:
        summary = agent_monitor.get_search_relaxed_summary()
        return {
            "ok": True,
            "timestamp": datetime.utcnow().isoformat(),
            "summary": summary,
        }
    except Exception as e:
        logger.error(f"Error getting search relaxed summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Redis Sync Endpoints (no-op — Redis removed, using MongoDB 100%)
# =============================================================================

@router.post("/sync/redis/session/{session_id}")
async def sync_session_from_redis(session_id: str) -> Dict[str, Any]:
    """
    No-op สำหรับโหมดปัจจุบัน:
    - แหล่งข้อมูลจริงอยู่ที่ MongoDB อยู่แล้ว
    - Redis ใช้เป็น cache/checkpointer เท่านั้น (ไม่ต้อง sync ย้อนกลับ)
    """
    return {
        "ok": True,
        "session_id": session_id,
        "message": "MongoDB is source of truth; Redis used only as cache/checkpointer",
    }


@router.post("/sync/redis/all")
async def sync_all_from_redis() -> Dict[str, Any]:
    """
    No-op: ไม่มีการดึงข้อมูลกลับจาก Redis
    ใช้สำหรับความเข้ากันได้กับเวอร์ชันก่อนหน้าเท่านั้น
    """
    return {
        "ok": True,
        "message": "MongoDB is source of truth; no reverse sync from Redis required",
        "stats": {},
    }


@router.get("/sync/redis/status")
async def get_sync_status() -> Dict[str, Any]:
    """
    รายงานสถานะ Redis ปัจจุบัน
    - redis_available: True ถ้า client พร้อมและเชื่อมต่อสำเร็จแล้ว
    - enabled_for_cache: True ถ้ามีการตั้งค่า REDIS_URL (ใช้ Redis คู่กับ in-process memory)
    """
    available = is_redis_available()
    return {
        "ok": True,
        "timestamp": datetime.utcnow().isoformat(),
        "status": {
            "redis_available": available,
            "enabled_for_cache": bool(settings.redis_url),
            "message": (
                "Redis connected (REDIS_URL set) and used together with in-process memory"
                if available and settings.redis_url
                else "Redis URL not set or unavailable; using in-process memory only"
            ),
        },
    }
