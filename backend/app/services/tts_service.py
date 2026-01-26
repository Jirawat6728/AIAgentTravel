"""
Text-to-Speech Service using Gemini TTS
Generates audio from text using Gemini 2.5 TTS models
"""

from __future__ import annotations
from typing import Optional
import base64
import httpx
from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)

class TTSService:
    """Text-to-Speech service using Gemini TTS API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise LLMException("GEMINI_API_KEY is required for TTS")
        
        # Use model from .env or default to TTS variant
        base_model = settings.gemini_flash_model
        self.tts_model = os.getenv("GEMINI_TTS_MODEL", f"{base_model}-tts").strip()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    async def generate_speech(
        self,
        text: str,
        voice_name: str = "Kore",
        language: str = "th",
        audio_format: str = "MP3"
    ) -> bytes:
        """
        Generate speech audio from text using Gemini TTS
        
        Args:
            text: Text to convert to speech
            voice_name: Voice name (Kore, Aoede, Callirrhoe)
            language: Language code (th for Thai)
            audio_format: Audio format (MP3, LINEAR16, OGG_OPUS, etc.)
        
        Returns:
            Audio data as bytes
        """
        try:
            # ✅ Try using Gemini Client API first (if available)
            try:
                from google import genai
                from google.genai import types
                
                client = genai.Client(api_key=self.api_key)
                
                response = client.models.generate_content(
                    model=self.tts_model,
                    contents=text,
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"],
                        speech_config=types.SpeechConfig(
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                    voice_name=voice_name
                                )
                            )
                        )
                    )
                )
                
                # Extract audio from response
                if response.candidates and len(response.candidates) > 0:
                    candidate = response.candidates[0]
                    if candidate.content and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'inline_data') and part.inline_data:
                                audio_base64 = part.inline_data.data
                                audio_bytes = base64.b64decode(audio_base64)
                                logger.info(f"Generated TTS audio via Client API: {len(audio_bytes)} bytes")
                                return audio_bytes
                
            except ImportError:
                logger.warning("google.genai.Client not available, using REST API")
            except Exception as e:
                logger.warning(f"Gemini Client API failed: {e}, falling back to REST API")
            
            # ✅ Fallback: Use REST API
            url = f"{self.base_url}/models/{self.tts_model}:generateContent"
            
            payload = {
                "contents": [{
                    "parts": [{"text": text}]
                }],
                "generationConfig": {
                    "responseModalities": ["AUDIO"],
                    "speechConfig": {
                        "voiceConfig": {
                            "prebuiltVoiceConfig": {
                                "voiceName": voice_name
                            }
                        },
                        "audioEncoding": audio_format
                    }
                }
            }
            
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                # Extract audio data from response
                if "candidates" in data and len(data["candidates"]) > 0:
                    candidate = data["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        for part in candidate["content"]["parts"]:
                            if "inlineData" in part and "data" in part["inlineData"]:
                                # Decode base64 audio data
                                audio_base64 = part["inlineData"]["data"]
                                audio_bytes = base64.b64decode(audio_base64)
                                logger.info(f"Generated TTS audio via REST API: {len(audio_bytes)} bytes for text length {len(text)}")
                                return audio_bytes
                
                raise LLMException("No audio data in Gemini TTS response")
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Gemini TTS API error: {e.response.status_code} - {e.response.text}")
            raise LLMException(f"Gemini TTS API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Error generating speech: {e}", exc_info=True)
            raise LLMException(f"Failed to generate speech: {str(e)}")
