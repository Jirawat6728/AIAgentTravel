"""
Chat API Router
Production-grade endpoint with error handling and background tasks
"""

from fastapi import APIRouter, HTTPException, Header, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
import json
import asyncio
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from app.models import UserSession, TripPlan
from app.models.trip_plan import SegmentStatus
from app.engine.agent import TravelAgent
from app.services.title import generate_chat_title
from app.storage.mongodb_storage import MongoStorage
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.exceptions import AgentException, StorageException
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    """Request model for chat endpoint matching frontend"""
    message: str = Field(..., min_length=1, description="User's message")
    user_id: Optional[str] = None
    client_trip_id: Optional[str] = None
    trigger: Optional[str] = "user_message"


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    response: str = Field(..., description="Agent's response in Thai")
    session_id: str = Field(..., description="Session identifier")
    # Add other fields the frontend might expect from agent state
    agent_state: Optional[dict] = None
    plan_choices: Optional[list] = None
    slot_choices: Optional[list] = None
    slot_intent: Optional[str] = None
    current_plan: Optional[dict] = None
    travel_slots: Optional[dict] = None
    trip_title: Optional[str] = None


def get_agent_metadata(session: Optional[UserSession]):
    """Helper to extract metadata for frontend from session"""
    if not session:
        return {
            "plan_choices": [],
            "slot_choices": [],
            "slot_intent": None,
            "agent_state": {"step": "start"},
            "travel_slots": None
        }
    
    plan = session.trip_plan
    
    # A trip is only "complete" if at least one segment exists and all segments are confirmed
    has_any_segments = any(
        len(getattr(plan, slot)) > 0 
        for slot in ["flights", "accommodations", "ground_transport"]
    )
    is_complete = has_any_segments and plan.is_complete()
    
    # Check for slot choices (any segment in SELECTING status)
    slot_choices = []
    slot_intent = None
    
    # Priority order: flights, accommodations, ground_transport
    for slot_name in ["flights", "accommodations", "ground_transport"]:
        segments = getattr(plan, slot_name, [])
        for i, segment in enumerate(segments):
            if segment.status == SegmentStatus.SELECTING:
                slot_choices = segment.options_pool
                slot_intent = slot_name.rstrip('s') # flight, accommodation, ground_transport
                if slot_intent == "accommodation": slot_intent = "hotel"
                break
        if slot_intent: break

    return {
        "plan_choices": [], 
        "slot_choices": slot_choices,
        "slot_intent": slot_intent,
        "agent_state": {
            "step": "trip_summary" if is_complete else "planning",
            "slot_workflow": {
                "current_slot": slot_intent or ("summary" if is_complete else None)
            }
        },
        "travel_slots": {
            "flights": [s.model_dump() for s in plan.flights if s.selected_option],
            "accommodations": [s.model_dump() for s in plan.accommodations if s.selected_option],
            "ground_transport": [s.model_dump() for s in plan.ground_transport if s.selected_option],
        } if is_complete else None
    }


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID", description="Conversation identifier"),
):
    """
    SSE stream endpoint for chat
    """
    session_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    user_id = session_user_id or request.user_id or "anonymous"
    conv_id = x_conversation_id or request.client_trip_id
    
    if not conv_id:
        raise HTTPException(status_code=400, detail="X-Conversation-ID header or client_trip_id is required")
    
    session_id = f"{user_id}::{conv_id}"

    async def event_generator():
        set_logging_context(session_id=session_id, user_id=user_id)
        try:
            storage = MongoStorage()
            llm_with_mcp = LLMServiceWithMCP()
            agent = TravelAgent(storage, llm_service=llm_with_mcp)
            
            # Queue for bridging status updates from agent to SSE
            status_queue = asyncio.Queue()
            
            async def status_callback(status: str, message: str, step: str):
                await status_queue.put({
                    "status": status,
                    "message": message,
                    "step": step
                })

            # Start agent in background task
            task = asyncio.create_task(agent.run_turn(
                session_id=session_id,
                user_input=request.message,
                status_callback=status_callback
            ))
            
            # 1. Send initial status
            yield f"data: {json.dumps({'status': 'processing', 'message': 'กำลังเริ่มประมวลผล...', 'step': 'start'}, ensure_ascii=False)}\n\n"
            
            # 2. Bridge status updates from queue to SSE until task is done
            while not task.done() or not status_queue.empty():
                try:
                    # Try to get from queue with short timeout
                    status_data = await asyncio.wait_for(status_queue.get(), timeout=0.1)
                    yield f"data: {json.dumps(status_data, ensure_ascii=False)}\n\n"
                except asyncio.TimeoutError:
                    # Check for disconnect while waiting
                    if await fastapi_request.is_disconnected():
                        logger.info(f"Client disconnected during stream: session={session_id}")
                        task.cancel()
                        return
                    if task.done() and status_queue.empty():
                        break
                    continue
                except Exception as e:
                    logger.error(f"Queue error in stream: {e}")
                    break
            
            # 3. Get the final response from agent (task is already done)
            try:
                # Add overall timeout for the agent execution (e.g. 90 seconds)
                response_text = await asyncio.wait_for(task, timeout=90.0)
            except asyncio.TimeoutError:
                logger.error(f"Agent execution timed out: session={session_id}")
                yield f"data: {json.dumps({'status': 'error', 'message': 'ระบบใช้เวลาประมวลผลนานเกินไป กรุณาลองใหม่อีกครั้ง'}, ensure_ascii=False)}\n\n"
                return
            
            # 4. Get updated session for metadata
            updated_session = await storage.get_session(session_id)
            metadata = get_agent_metadata(updated_session)
            
            # 5. Send completion data
            final_data = {
                "response": response_text,
                "session_id": session_id,
                "trip_title": updated_session.title if updated_session else None,
                **metadata
            }
            
            yield f"data: {json.dumps({'status': 'completed', 'data': final_data}, ensure_ascii=False)}\n\n"
            
            # 6. Background tasks (Title generation)
            if updated_session and updated_session.title is None:
                background_tasks.add_task(run_title_generator, session_id, request.message, response_text)
                
        except Exception as e:
            logger.error(f"SSE Stream error for session {session_id}: {e}", exc_info=True)
            yield f"data: {json.dumps({'status': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            clear_logging_context()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    fastapi_request: Request,
    background_tasks: BackgroundTasks,
    x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-ID", description="Conversation identifier"),
):
    """
    Chat endpoint - Main entry point for Travel Agent
    Supports both Session Cookie and Headers for auth
    """
    # 1. Get user_id from Session Cookie first, then Body, then Header, then default
    session_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    user_id = session_user_id or request.user_id or "anonymous"
    
    # 2. Get conversation_id from Header or Body (client_trip_id)
    conv_id = x_conversation_id or request.client_trip_id
    if not conv_id:
        raise HTTPException(status_code=400, detail="X-Conversation-ID header or client_trip_id is required")
    
    session_id = f"{user_id}::{conv_id}"
    set_logging_context(session_id=session_id, user_id=user_id)
    
    try:
        # Validate input
        if not request.message.strip():
            raise HTTPException(status_code=400, detail="message is empty")
        
        logger.info(f"Processing chat request: message_length={len(request.message)}")
        
        # Instantiate storage and agent (with MCP support)
        storage = MongoStorage()
        llm_with_mcp = LLMServiceWithMCP()
        agent = TravelAgent(storage, llm_service=llm_with_mcp)
        
        # Get session to check if title exists
        session = await storage.get_session(session_id)
        needs_title = session.title is None
        
        # Run agent turn (this returns the response text)
        # Note: TravelAgent.run_turn should handle internal state updates
        response_text = await agent.run_turn(session_id, request.message)
        
        # Get the updated session for additional metadata
        updated_session = await storage.get_session(session_id)
        
        # Extract metadata for frontend
        metadata = get_agent_metadata(updated_session)
        
        # Schedule background title generation if needed (first turn only)
        if needs_title:
            logger.info(f"Scheduling background title generation for session {session_id}")
            background_tasks.add_task(
                run_title_generator,
                session_id,
                request.message,
                response_text
            )
        
        logger.info("Chat request completed successfully")
        
        # Build response with metadata from state
        return ChatResponse(
            response=response_text,
            session_id=session_id,
            trip_title=updated_session.title if updated_session else None,
            current_plan=updated_session.trip_plan.model_dump() if updated_session else None,
            **metadata
        )
    
    except HTTPException:
        raise
    except (AgentException, StorageException) as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        clear_logging_context()


@router.post("/select_choice")
async def select_choice(request: dict, fastapi_request: Request):
    """
    Select a choice from the agent's proposed plan_choices or slot_choices
    """
    session_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    user_id = session_user_id or request.get("user_id") or "anonymous"
    conv_id = request.get("trip_id") or request.get("client_trip_id")
    choice_id = request.get("choice_id")
    
    if not conv_id or not choice_id:
        raise HTTPException(status_code=400, detail="trip_id and choice_id required")
        
    session_id = f"{user_id}::{conv_id}"
    set_logging_context(session_id=session_id, user_id=user_id)
    
    try:
        storage = MongoStorage()
        llm_with_mcp = LLMServiceWithMCP()
        agent = TravelAgent(storage, llm_service=llm_with_mcp)
        
        # Here we would normally call a specific method on the agent to select a choice
        # For now, let's treat it as a message like "I choose option X"
        response_text = await agent.run_turn(session_id, f"I choose option {choice_id}")
        
        updated_session = await storage.get_session(session_id)
        
        return {
            "ok": True,
            "response": response_text,
            "session_id": session_id,
            "trip_title": updated_session.title
        }
    except Exception as e:
        logger.error(f"Select choice error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        clear_logging_context()


@router.post("/reset")
async def reset_chat(request: dict, fastapi_request: Request):
    """
    Reset chat context for a trip
    """
    session_user_id = fastapi_request.cookies.get(settings.session_cookie_name)
    user_id = session_user_id or request.get("user_id") or "anonymous"
    conv_id = request.get("client_trip_id")
    
    if not conv_id:
        return {"ok": False, "error": "client_trip_id required"}
        
    session_id = f"{user_id}::{conv_id}"
    storage = MongoStorage()
    # Logic to reset session... 
    # For now we can just delete it or mark it as reset
    return {"ok": True}


async def run_title_generator(session_id: str, user_input: str, bot_response: str):
    """
    Background worker function for title generation
    Runs asynchronously after response is sent to user
    
    Args:
        session_id: Session identifier
        user_input: User's message
        bot_response: Bot's response
    """
    try:
        # Set logging context for background task
        set_logging_context(session_id=session_id, user_id=session_id.split("::")[0])
        
        logger.info(f"Starting background title generation for session {session_id}")
        
        # Generate title
        title = await generate_chat_title(user_input, bot_response)
        
        # Update session title
        storage = MongoStorage()
        await storage.update_title(session_id, title)
        
        logger.info(f"Title generated and saved for session {session_id}: {title}")
    
    except Exception as e:
        logger.error(f"Error in background title generation for session {session_id}: {e}", exc_info=True)
        # Don't raise - background task failures shouldn't affect user experience
    finally:
        clear_logging_context()
