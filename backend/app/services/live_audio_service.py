"""
เซอร์วิส Gemini Live API สำหรับการสนทนาด้วยเสียงแบบเรียลไทม์
ให้การโต้ตอบด้วยเสียงแบบคล้ายมนุษย์ผ่านการประมวลผลเสียง
"""

from __future__ import annotations
from typing import Optional, AsyncIterator, Callable, Awaitable
import os
import asyncio
import base64
import json
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)

# ✅ Helper function to safely write debug logs
def _write_debug_log(data: dict):
    """Safely write debug log, creating directory if needed"""
    try:
        import os
        from pathlib import Path
        debug_log_dir = Path(__file__).parent.parent.parent / 'data' / 'logs' / 'debug'
        debug_log_dir.mkdir(parents=True, exist_ok=True)
        debug_log_path = debug_log_dir / 'live_audio_debug.log'
        with open(debug_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    except Exception:
        pass  # Silently ignore debug log errors

class LiveAudioService:
    """Real-time voice conversation service using Gemini Live API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise LLMException("GEMINI_API_KEY is required for Live Audio")
        
        # Use model from .env or default to native audio model
        base_model = settings.gemini_flash_model
        # For live audio, use native audio variant
        self.model_id = os.getenv("GEMINI_LIVE_AUDIO_MODEL", f"{base_model}-native-audio-preview-12-2025").strip()
        # Fallback to alternative model names if needed
        self.fallback_models = [
            f"{base_model}-native-audio",
            f"gemini-live-{base_model.replace('gemini-', '')}-native-audio"
        ]
    
    async def create_session(
        self,
        system_instruction: Optional[str] = None,
        conversation_history: Optional[list] = None
    ):
        """
        Create a new Live API session for real-time voice conversation
        
        Args:
            system_instruction: System prompt for the AI
            conversation_history: Previous conversation turns
        
        Returns:
            Session object for streaming audio
        """
        # #region agent log (Hypothesis A)
        import json
        _write_debug_log({
            "id": f"log_{int(__import__('time').time() * 1000)}_create_session_entry",
            "timestamp": int(__import__('time').time() * 1000),
            "location": "live_audio_service.py:33",
            "message": "create_session called",
            "data": {"model_id": self.model_id, "has_system_instruction": system_instruction is not None},
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "A"
        })
        # #endregion
        
        try:
            from google import genai
            from google.genai import types
            
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_import_success",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "live_audio_service.py:52",
                "message": "google.genai imported successfully",
                "data": {"has_client": True},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            
            client = genai.Client(api_key=self.api_key)
            
            # Build system instruction
            system_instruction_text = system_instruction or """คุณเป็น Travel Agent AI ที่พูดคุยด้วยเสียงแบบธรรมชาติ
- ใช้ภาษาไทยในการสนทนา
- พูดคุยแบบเป็นมิตร เป็นธรรมชาติ เหมือนมนุษย์
- ฟังน้ำเสียงและอารมณ์ของผู้ใช้
- ตอบสนองด้วยอารมณ์ที่เหมาะสม
- สามารถขัดจังหวะได้เมื่อผู้ใช้ต้องการพูด"""
            
            # ✅ FIX: Use dict config instead of types.GenerateContentConfig
            # Based on web search, Live API uses dict config
            config = {
                "response_modalities": ["AUDIO"],
                "system_instruction": system_instruction_text
            }
            
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_before_connect",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "live_audio_service.py:70",
                "message": "Before client.aio.live.connect",
                "data": {"model_id": self.model_id, "config_type": type(config).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            
            # ✅ FIX: client.aio.live.connect() returns an async context manager
            # We need to enter it manually since we can't use 'async with' in this function
            # The context manager must be entered and managed by the caller
            try:
                # Get the async context manager
                session_cm = client.aio.live.connect(
                    model=self.model_id,
                    config=config
                )
                
                # #region agent log (Hypothesis A)
                _write_debug_log({
                    "id": f"log_{int(__import__('time').time() * 1000)}_got_context_manager",
                    "timestamp": int(__import__('time').time() * 1000),
                    "location": "live_audio_service.py:85",
                    "message": "Got context manager from connect",
                    "data": {"session_cm_type": type(session_cm).__name__},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                # Enter the context manager to get the actual session
                session = await session_cm.__aenter__()
                
                # #region agent log (Hypothesis A)
                _write_debug_log({
                    "id": f"log_{int(__import__('time').time() * 1000)}_session_entered",
                    "timestamp": int(__import__('time').time() * 1000),
                    "location": "live_audio_service.py:95",
                    "message": "Session context entered successfully",
                    "data": {"session_type": type(session).__name__},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                # Store the context manager for cleanup
                session._cm = session_cm
                
                logger.info(f"Created Live API session with model: {self.model_id}")
                return session
            except Exception as e:
                # #region agent log (Hypothesis A)
                _write_debug_log({
                    "id": f"log_{int(__import__('time').time() * 1000)}_primary_model_failed",
                    "timestamp": int(__import__('time').time() * 1000),
                    "location": "live_audio_service.py:105",
                    "message": "Primary model failed",
                    "data": {"error": str(e), "error_type": type(e).__name__},
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "A"
                })
                # #endregion
                
                logger.warning(f"Failed to create session with {self.model_id}: {e}")
                # Try fallback models
                for fallback_model in self.fallback_models:
                    try:
                        session_cm = client.aio.live.connect(
                            model=fallback_model,
                            config=config
                        )
                        session = await session_cm.__aenter__()
                        session._cm = session_cm
                        logger.info(f"Created Live API session with fallback model: {fallback_model}")
                        return session
                    except Exception as fallback_error:
                        logger.warning(f"Fallback model {fallback_model} also failed: {fallback_error}")
                        continue
                
                raise LLMException(f"Failed to create Live API session with any model: {e}")
                
        except ImportError as import_err:
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_import_error",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "live_audio_service.py:130",
                "message": "Import error",
                "data": {"error": str(import_err)},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            raise LLMException("google.genai library not available. Install: pip install google-genai")
        except Exception as e:
            # #region agent log (Hypothesis A)
            _write_debug_log({
                "id": f"log_{int(__import__('time').time() * 1000)}_create_session_error",
                "timestamp": int(__import__('time').time() * 1000),
                "location": "live_audio_service.py:135",
                "message": "create_session error",
                "data": {"error": str(e), "error_type": type(e).__name__},
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A"
            })
            # #endregion
            logger.error(f"Error creating Live API session: {e}", exc_info=True)
            raise LLMException(f"Failed to create Live API session: {str(e)}")
    
    async def send_audio_chunk(
        self,
        session,
        audio_data: bytes,
        sample_rate: int = 16000
    ):
        """
        Send audio chunk to Live API session
        
        Args:
            session: Live API session
            audio_data: Raw PCM audio bytes (16-bit, little-endian, mono)
            sample_rate: Audio sample rate (default 16000 Hz)
        """
        try:
            from google.genai import types
            
            # ✅ FIX: Use send() method for streaming raw audio data
            # send() is for real-time streaming (audio bytes, video frames)
            await session.send(
                input={
                    "data": audio_data,
                    "mime_type": "audio/pcm"
                }
            )
            
        except Exception as e:
            logger.error(f"Error sending audio chunk: {e}", exc_info=True)
            raise
    
    async def send_text_message(
        self,
        session,
        text: str,
        turn_complete: bool = True
    ):
        """
        Send text message to Live API session (for initial message or text-only turns)
        
        Args:
            session: Live API session
            text: Text message
            turn_complete: Whether this turn is complete
        """
        try:
            from google.genai import types
            
            # ✅ FIX: Use send_client_content with types.Content and types.Part
            await session.send_client_content(
                turns=types.Content(
                    role="user",
                    parts=[types.Part(text=text)]
                )
            )
        except Exception as e:
            logger.error(f"Error sending text message: {e}", exc_info=True)
            raise
    
    async def receive_audio_stream(
        self,
        session,
        on_audio_chunk: Optional[Callable[[bytes], Awaitable[None]]] = None,
        on_text_chunk: Optional[Callable[[str], Awaitable[None]]] = None
    ) -> AsyncIterator[dict]:
        """
        Receive audio and text stream from Live API session
        
        Args:
            session: Live API session
            on_audio_chunk: Callback for audio chunks
            on_text_chunk: Callback for text chunks
        
        Yields:
            Dictionary with 'type' ('audio' or 'text') and 'data'
        """
        try:
            async for message in session.receive():
                # ── server_content: audio / text / turn_complete ──────
                if hasattr(message, 'server_content') and message.server_content:
                    sc = message.server_content

                    # model_turn → audio + text parts
                    if hasattr(sc, 'model_turn') and sc.model_turn:
                        model_turn = sc.model_turn
                        if hasattr(model_turn, 'parts') and model_turn.parts:
                            for part in model_turn.parts:
                                # Audio (inline_data)
                                if hasattr(part, 'inline_data') and part.inline_data:
                                    mime = getattr(part.inline_data, 'mime_type', '')
                                    if mime.startswith('audio/'):
                                        raw = part.inline_data.data
                                        # data อาจเป็น bytes หรือ base64 str
                                        if isinstance(raw, (bytes, bytearray)):
                                            audio_bytes = bytes(raw)
                                        else:
                                            audio_bytes = base64.b64decode(raw)
                                        if on_audio_chunk:
                                            await on_audio_chunk(audio_bytes)
                                        yield {"type": "audio", "data": audio_bytes, "mime_type": mime}

                                # Text
                                if hasattr(part, 'text') and part.text:
                                    if on_text_chunk:
                                        await on_text_chunk(part.text)
                                    yield {"type": "text", "data": part.text}

                    # turn_complete → แจ้ง frontend ว่า AI พูดจบแล้ว
                    if getattr(sc, 'turn_complete', False):
                        yield {"type": "turn_complete"}

                # ── interruption ──────────────────────────────────────
                if hasattr(message, 'interruption') and message.interruption:
                    yield {"type": "interruption", "data": message.interruption}

                # ── tool_call (future use) ────────────────────────────
                if hasattr(message, 'tool_call') and message.tool_call:
                    yield {"type": "tool_call", "data": message.tool_call}

        except Exception as e:
            logger.error(f"Error receiving audio stream: {e}", exc_info=True)
            raise
    
    async def close_session(self, session):
        """Close Live API session"""
        try:
            # ✅ FIX: Exit the context manager properly
            if hasattr(session, '_cm'):
                # Exit the context manager
                await session._cm.__aexit__(None, None, None)
            elif hasattr(session, 'close'):
                await session.close()
            elif hasattr(session, '__aexit__'):
                await session.__aexit__(None, None, None)
            logger.info("Live API session closed")
        except Exception as e:
            logger.warning(f"Error closing session: {e}")
