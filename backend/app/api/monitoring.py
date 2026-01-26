"""
Monitoring API Endpoints
Provides access to cost tracking and workflow visualization for debugging and monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
from datetime import datetime

from app.engine.cost_tracker import cost_tracker
from app.engine.workflow_visualizer import workflow_visualizer
from app.storage.connection_manager import MongoConnectionManager
from app.models.session import UserSession
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


@router.get("/workflow/session/{session_id}")
async def get_session_workflow(
    session_id: str,
    detailed: bool = Query(default=False, description="Include detailed report")
) -> Dict[str, Any]:
    """
    Get workflow visualization for a session
    
    Args:
        session_id: Session identifier
        detailed: Include detailed ASCII report
        
    Returns:
        Workflow state and visualization
    """
    try:
        # Get session from database
        db = MongoConnectionManager.get_instance().get_database()
        session_data = db.sessions.find_one({"session_id": session_id})
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Convert to UserSession
        session = UserSession.from_dict(session_data)
        
        # Get workflow data
        workflow_dict = workflow_visualizer.export_to_dict(session.trip_plan)
        compact_status = workflow_visualizer.get_compact_status(session.trip_plan)
        progress_bar = workflow_visualizer.create_progress_bar(session.trip_plan)
        slot_summary = workflow_visualizer.get_slot_summary(session.trip_plan)
        
        result = {
            "ok": True,
            "session_id": session_id,
            "compact_status": compact_status,
            "progress_bar": progress_bar,
            "slot_summary": slot_summary,
            "workflow": workflow_dict
        }
        
        # Add detailed report if requested
        if detailed:
            ascii_report = workflow_visualizer.create_detailed_report(session.trip_plan)
            ascii_viz = workflow_visualizer.visualize(session.trip_plan)
            result["ascii_report"] = ascii_report
            result["ascii_visualization"] = ascii_viz
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflow/ascii/{session_id}")
async def get_workflow_ascii(session_id: str) -> Dict[str, Any]:
    """
    Get ASCII visualization of workflow (for terminal display)
    
    Args:
        session_id: Session identifier
        
    Returns:
        ASCII diagram as text
    """
    try:
        # Get session from database
        db = MongoConnectionManager.get_instance().get_database()
        session_data = db.sessions.find_one({"session_id": session_id})
        
        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Convert to UserSession
        session = UserSession.from_dict(session_data)
        
        # Get ASCII visualization
        ascii_viz = workflow_visualizer.visualize(session.trip_plan, include_details=True)
        
        return {
            "ok": True,
            "session_id": session_id,
            "visualization": ascii_viz
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ASCII workflow: {e}", exc_info=True)
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
