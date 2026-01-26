"""
Admin and Debugging Router
Provides system status, logs, and service health checks
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from typing import Dict, Any, List, Optional
import os
import psutil
import asyncio
import json
import time
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.connection_manager import MongoConnectionManager
from app.services.llm import LLMService
from app.services.agent_monitor import agent_monitor

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBasic()

START_TIME = time.time()

# 🔒 Admin Authentication Helper
def verify_admin_auth(credentials: HTTPBasicCredentials = Depends(security)) -> bool:
    """
    Verify admin password authentication
    In production, use ADMIN_PASSWORD env var
    """
    if not settings.admin_require_auth:
        return True  # Auth disabled
    
    if not settings.admin_password:
        logger.warning("Admin authentication required but ADMIN_PASSWORD not set. Allowing access.")
        return True  # Allow if password not set (warning only)
    
    # Compare password (using constant-time comparison to prevent timing attacks)
    provided = credentials.password.encode('utf-8')
    expected = settings.admin_password.encode('utf-8')
    
    # Use secrets.compare_digest for constant-time comparison
    if not secrets.compare_digest(provided, expected):
        logger.warning(f"Admin authentication failed from {credentials.username}")
        raise HTTPException(
            status_code=401,
            detail="Invalid admin credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    logger.info(f"Admin authentication successful: {credentials.username}")
    return True

@router.get("/status")
async def get_system_status(_auth: bool = Depends(verify_admin_auth)):
    """
    Check status of all services and system resources
    """
    # 1. Mongo Status
    mongo_ok = False
    mongo_details = "Not connected"
    try:
        mongo_ok = await MongoConnectionManager.get_instance().ping()
        mongo_details = "Connected" if mongo_ok else "Ping failed"
    except Exception as e:
        mongo_details = str(e)

    # 2. Gemini Status
    gemini_ok = False
    gemini_details = "API Key missing"
    if settings.gemini_api_key:
        gemini_ok = True
        gemini_details = f"Model: {settings.gemini_model_name} (Ready)"

    # 3. Amadeus Status
    amadeus_ok = False
    amadeus_details = "API Key missing"
    # ✅ Check both search and booking keys for admin dashboard
    has_search_keys = settings.amadeus_search_api_key and settings.amadeus_search_api_secret
    has_booking_keys = settings.amadeus_booking_api_key and settings.amadeus_booking_api_secret
    if has_search_keys or has_booking_keys:
        amadeus_ok = True
        # ✅ Show separate keys status
        search_key_status = "✅" if has_search_keys else "❌"
        booking_key_status = "✅" if has_booking_keys else "❌"
        amadeus_details = f"Search: {settings.amadeus_search_env} ({search_key_status}) | Booking: {settings.amadeus_booking_env} ({booking_key_status})"
    
    # 4. Google Maps Status
    gmaps_ok = False
    gmaps_details = "API Key missing"
    if settings.google_maps_api_key:
        gmaps_ok = True
        gmaps_details = "Ready"

    # 5. System Resources
    uptime = time.time() - START_TIME
    process = psutil.Process(os.getpid())
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "mongodb": {"status": "ok" if mongo_ok else "error", "message": mongo_details},
            "gemini": {"status": "ok" if gemini_ok else "error", "message": gemini_details},
            "amadeus": {"status": "ok" if amadeus_ok else "error", "message": amadeus_details},
            "google_maps": {"status": "ok" if gmaps_ok else "error", "message": gmaps_details}
        },
        "config": {
            "amadeus_safety_guard": settings.amadeus_env == "test",
            "amadeus_env": settings.amadeus_env,
            "amadeus_search_env": settings.amadeus_search_env,
            "amadeus_booking_env": settings.amadeus_booking_env,
            "gemini_model": settings.gemini_model_name
        },
        "system": {
            "uptime_seconds": int(uptime),
            "memory_usage_mb": int(process.memory_info().rss / 1024 / 1024),
            "cpu_usage_percent": process.cpu_percent(),
            "active_threads": process.num_threads()
        }
    }

@router.get("/logs")
async def get_logs(lines: int = 100, _auth: bool = Depends(verify_admin_auth)):
    """
    Read the last N lines of the log file
    """
    if not settings.log_file:
        return {"message": "Log file not configured in settings"}
    
    log_path = Path(settings.log_file)
    if not log_path.exists():
        return {"message": f"Log file not found at {log_path}"}
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            # Read all lines and take last N
            all_lines = f.readlines()
            return {
                "filename": log_path.name,
                "total_lines": len(all_lines),
                "requested_lines": lines,
                "content": all_lines[-lines:]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")

@router.get("/sessions")
async def get_recent_sessions(
    limit: int = 10, 
    user_id: Optional[str] = None,
    _auth: bool = Depends(verify_admin_auth)
):
    """
    Get summary of recent sessions from MongoDB
    ✅ SECURITY: If user_id is provided, only return sessions for that user
    If user_id is not provided, return all sessions (admin only)
    """
    try:
        db = MongoConnectionManager.get_instance().get_database()
        
        # ✅ SECURITY: If user_id is specified, only query that user's sessions
        query_filter = {}
        if user_id:
            query_filter["user_id"] = user_id
            logger.info(f"Admin query: Getting sessions for user_id={user_id}")
        else:
            logger.warning(f"Admin query: Getting ALL sessions (no user_id filter - admin access only)")
        
        cursor = db.sessions.find(query_filter).sort("last_updated", -1).limit(limit)
        sessions = []
        async for doc in cursor:
            # ✅ SECURITY: Verify user_id matches if filter was applied
            if user_id:
                doc_user_id = doc.get("user_id")
                if doc_user_id != user_id:
                    logger.warning(f"Admin query found session with mismatched user_id: expected {user_id}, found {doc_user_id}, skipping")
                    continue
            
            # Clean up ObjectId for JSON
            doc["_id"] = str(doc["_id"])
            # ✅ PRIVACY: Remove sensitive trip_plan data from admin view
            if "trip_plan" in doc:
                # Only include summary info, not full plan data
                doc["trip_plan_summary"] = {
                    "has_flights": bool(doc["trip_plan"].get("travel", {}).get("flights", {}).get("outbound")),
                    "has_hotels": bool(doc["trip_plan"].get("accommodation", {}).get("segments")),
                    "has_transport": bool(doc["trip_plan"].get("travel", {}).get("ground_transport"))
                }
                # Remove full trip_plan to protect privacy
                del doc["trip_plan"]
            
            sessions.append(doc)
        return sessions
    except Exception as e:
        logger.error(f"Admin query error: {e}", exc_info=True)
        return {"error": str(e)}

@router.get("/workflows")
async def get_workflow_stats(_auth: bool = Depends(verify_admin_auth)):
    """
    Stats about the agent workflows (if tracked)
    """
    # This could be expanded later to track specific agent turn counts
    return {
        "architecture": "Two-Pass ReAct (Controller -> Responder)",
        "max_controller_iterations": settings.controller_max_iterations,
        "current_sessions_tracked": "Feature coming soon"
    }

@router.get("/stream")
async def admin_stream(request: Request, _auth: bool = Depends(verify_admin_auth)):
    """
    SSE stream for real-time system monitoring
    """
    async def event_generator():
        # Cache for expensive service checks
        last_service_check = 0
        service_cache = {
            "gemini": {"status": "unknown", "message": "Initializing..."},
            "amadeus": {"status": "unknown", "message": "Initializing..."},
        }
        
        while True:
            # If client disconnects, stop streaming
            if await request.is_disconnected():
                break

            try:
                # 1. Mongo Status (Always check, it's fast)
                mongo_ok = await MongoConnectionManager.get_instance().ping()
                mongo_details = "Connected" if mongo_ok else "Disconnected (Ping failed)"

                # 2. Check other services periodically (every 10 seconds)
                current_time = time.time()
                if current_time - last_service_check > 10:
                    last_service_check = current_time
                    
                    # Gemini Check
                    if not settings.gemini_api_key:
                        service_cache["gemini"] = {"status": "error", "message": "API Key missing"}
                    else:
                        try:
                            # Use a lightweight call to verify key/connectivity
                            from google import genai
                            client = genai.Client(api_key=settings.gemini_api_key)
                            # Just list models to verify key
                            models = list(client.models.list(config={'page_size': 1}))
                            service_cache["gemini"] = {"status": "ok", "message": f"Model: {settings.gemini_model_name} (Active)"}
                        except Exception as e:
                            service_cache["gemini"] = {"status": "error", "message": f"API Error: {str(e)}"}
                    
                    # ✅ Amadeus Check (using search keys for testing)
                    if not settings.amadeus_search_api_key or not settings.amadeus_search_api_secret:
                        service_cache["amadeus"] = {"status": "error", "message": "Search API credentials missing"}
                    else:
                        try:
                            # Try a simple auth token request using search keys
                            import httpx
                            search_env = settings.amadeus_search_env.lower()
                            auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token" if search_env == "test" else "https://api.amadeus.com/v1/security/oauth2/token"
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(
                                    auth_url,
                                    data={
                                        "grant_type": "client_credentials",
                                        "client_id": settings.amadeus_search_api_key,
                                        "client_secret": settings.amadeus_search_api_secret
                                    },
                                    timeout=5.0
                                )
                                if resp.status_code == 200:
                                    search_key_status = "✅"
                                    booking_key_status = "✅" if (settings.amadeus_booking_api_key and settings.amadeus_booking_api_secret) else "❌"
                                    service_cache["amadeus"] = {"status": "ok", "message": f"Search: {settings.amadeus_search_env} ({search_key_status}) | Booking: {settings.amadeus_booking_env} ({booking_key_status}) (Authenticated)"}
                                else:
                                    service_cache["amadeus"] = {"status": "error", "message": f"Auth failed: {resp.status_code}"}
                        except Exception as e:
                            service_cache["amadeus"] = {"status": "error", "message": f"Connection error: {str(e)}"}

                # 3. System Resources
                uptime = time.time() - START_TIME
                process = psutil.Process(os.getpid())
                
                status_data = {
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "mongodb": {"status": "ok" if mongo_ok else "error", "message": mongo_details},
                        "gemini": service_cache["gemini"],
                        "amadeus": service_cache["amadeus"],
                        "google_maps": {"status": "ok" if settings.google_maps_api_key else "error", "message": "Key present" if settings.google_maps_api_key else "Key missing"}
                    },
                    "agent_activities": agent_monitor.get_activities(),
                    "system": {
                        "uptime_seconds": int(uptime),
                        "memory_usage_mb": int(process.memory_info().rss / 1024 / 1024),
                        "cpu_usage_percent": psutil.cpu_percent(), # Global CPU
                        "process_cpu_percent": process.cpu_percent(), # Process CPU
                        "active_threads": process.num_threads()
                    },
                    "config": {
                        "amadeus_safety_guard": settings.amadeus_env == "test",
                        "amadeus_env": settings.amadeus_env,
                        "amadeus_search_env": settings.amadeus_search_env,
                        "amadeus_booking_env": settings.amadeus_booking_env,
                        "gemini_model": settings.gemini_model_name
                    }
                }

                yield f"data: {json.dumps(status_data, ensure_ascii=False)}\n\n"
                
                # Update every 2 seconds
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Admin stream error: {e}")
                # Don't yield error to keep the connection alive if possible, just log it
                await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

