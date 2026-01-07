"""
Admin and Debugging Router
Provides system status, logs, and service health checks
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, List
import os
import psutil
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.mongodb_connection import MongoConnectionManager
from app.services.llm import LLMService
from app.services.agent_monitor import agent_monitor

logger = get_logger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

START_TIME = time.time()

@router.get("/status")
async def get_system_status():
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
    if settings.amadeus_api_key and settings.amadeus_api_secret:
        amadeus_ok = True
        amadeus_details = f"Env: {settings.amadeus_env} (Ready)"
    
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
async def get_logs(lines: int = 100):
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
async def get_recent_sessions(limit: int = 10):
    """
    Get summary of recent sessions from MongoDB
    """
    try:
        db = MongoConnectionManager.get_instance().get_database()
        cursor = db.sessions.find().sort("last_updated", -1).limit(limit)
        sessions = []
        async for doc in cursor:
            # Clean up ObjectId for JSON
            doc["_id"] = str(doc["_id"])
            sessions.append(doc)
        return sessions
    except Exception as e:
        return {"error": str(e)}

@router.get("/workflows")
async def get_workflow_stats():
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
async def admin_stream(request: Request):
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
                    
                    # Amadeus Check
                    if not settings.amadeus_api_key or not settings.amadeus_api_secret:
                        service_cache["amadeus"] = {"status": "error", "message": "Credentials missing"}
                    else:
                        try:
                            # Try a simple auth token request
                            import httpx
                            auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token" if settings.amadeus_env == "test" else "https://api.amadeus.com/v1/security/oauth2/token"
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(
                                    auth_url,
                                    data={
                                        "grant_type": "client_credentials",
                                        "client_id": settings.amadeus_api_key,
                                        "client_secret": settings.amadeus_api_secret
                                    },
                                    timeout=5.0
                                )
                                if resp.status_code == 200:
                                    service_cache["amadeus"] = {"status": "ok", "message": f"Env: {settings.amadeus_env} (Authenticated)"}
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

