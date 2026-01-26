"""
Production-Grade LLM Service for Google Gemini
Features:
- Multi-model support (Flash, Pro, Ultra)
- Three specialized "brains": Controller, Responder, Intelligence
- Automatic model selection based on task complexity
- Robust error handling and retry logic
- Production-ready logging and monitoring
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import os
import json
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, retry_if_not_exception_type

# Import for quota error handling
try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:
    ResourceExhausted = Exception  # Fallback if not available

def retry_if_not_quota_error(exception):
    """Retry unless it's a quota error (which should fallback immediately)"""
    if isinstance(exception, ResourceExhausted):
        error_str = str(exception)
        if "quota" in error_str.lower() or "429" in error_str:
            return False  # Don't retry quota errors
    return True  # Retry other errors

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)


class ModelType(str, Enum):
    """Gemini model types"""
    FLASH = "flash"      # Fast, cost-effective (gemini-2.5-flash)
    PRO = "pro"          # Balanced (gemini-2.5-pro)
    ULTRA = "ultra"      # Maximum capability (gemini-2.5-pro)


class BrainType(str, Enum):
    """Three specialized brain types"""
    CONTROLLER = "controller"      # Decision-making brain (what to do next)
    RESPONDER = "responder"        # Communication brain (how to respond to user)
    INTELLIGENCE = "intelligence"  # Analysis brain (smart selection, reasoning)


class ProductionLLMService:
    """
    Production-grade LLM service with three specialized brains
    
    Features:
    - Automatic model selection based on brain type and complexity
    - Manual model override support
    - Robust error handling with retry logic
    - Production-ready logging
    """
    
    # Model mapping
    # ✅ FIX: For v1beta API, use stable model names (gemini-2.5-* or gemini-1.5-* without version suffix)
    MODEL_MAP = {
        ModelType.FLASH: {
            "default": "gemini-2.5-flash",  # Stable model for v1beta API
            "preview": "gemini-3-flash-preview",
            "latest": "gemini-2.5-flash"  # Use stable model
        },
        ModelType.PRO: {
            "default": "gemini-2.5-pro",  # Stable model for v1beta API
            "preview": "gemini-3-pro-preview",
            "latest": "gemini-2.5-pro"  # Use stable model
        },
        ModelType.ULTRA: {
            "default": "gemini-2.5-pro",  # Fallback to pro if ultra not available
            "preview": "gemini-3-ultra-preview",
            "latest": "gemini-2.5-pro"  # Use stable model
        }
    }
    
    # Brain-specific model preferences
    BRAIN_MODEL_PREFERENCES = {
        BrainType.CONTROLLER: ModelType.PRO,      # Controller needs reasoning
        BrainType.RESPONDER: ModelType.FLASH,    # Responder can be fast
        BrainType.INTELLIGENCE: ModelType.PRO    # Intelligence needs analysis
    }
    
    # Brain-specific temperature settings
    BRAIN_TEMPERATURES = {
        BrainType.CONTROLLER: 0.3,      # Low temperature for consistent decisions
        BrainType.RESPONDER: 0.7,       # Higher temperature for natural responses
        BrainType.INTELLIGENCE: 0.4     # Balanced for analysis
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Production LLM Service
        
        Args:
            api_key: Gemini API key (defaults to settings)
        """
        self.api_key = api_key or settings.gemini_api_key
        
        if not self.api_key:
            raise LLMException("GEMINI_API_KEY is required")
        
        genai.configure(api_key=self.api_key)
        
        # Get model version from env (default: "preview" for latest models)
        self.model_version = os.getenv("GEMINI_MODEL_VERSION", "preview").lower()
        
        logger.info(f"ProductionLLMService initialized with API key: {self.api_key[:6]}...{self.api_key[-4:]}")
        logger.info(f"Model version: {self.model_version}")
    
    def get_model_name(
        self,
        model_type: ModelType,
        version: Optional[str] = None
    ) -> str:
        """
        Get actual Gemini model name
        
        Args:
            model_type: Model type (FLASH, PRO, ULTRA)
            version: Model version ("default", "preview", "latest") - defaults to self.model_version
            
        Returns:
            Gemini model name string
        """
        version = version or self.model_version
        model_map = self.MODEL_MAP.get(model_type, self.MODEL_MAP[ModelType.FLASH])
        return model_map.get(version, model_map["default"])
    
    def select_model_for_brain(
        self,
        brain_type: BrainType,
        complexity: Optional[str] = None,
        force_model: Optional[ModelType] = None
    ) -> tuple[str, ModelType]:
        """
        Select optimal model for a brain type
        
        Args:
            brain_type: Type of brain (CONTROLLER, RESPONDER, INTELLIGENCE)
            complexity: Optional complexity hint ("simple", "moderate", "complex")
            force_model: Force a specific model type (overrides auto-selection)
            
        Returns:
            Tuple of (model_name, model_type)
        """
        # Force model if specified
        if force_model:
            model_type = force_model
            logger.info(f"Model forced to {model_type.value} for {brain_type.value}")
        else:
            # Get preferred model for brain
            preferred_type = self.BRAIN_MODEL_PREFERENCES.get(brain_type, ModelType.FLASH)
            
            # Adjust based on complexity
            if complexity == "complex":
                # Upgrade to PRO for complex tasks
                if preferred_type == ModelType.FLASH:
                    model_type = ModelType.PRO
                else:
                    model_type = preferred_type
            elif complexity == "simple":
                # Downgrade to FLASH for simple tasks (save cost)
                model_type = ModelType.FLASH
            else:
                model_type = preferred_type
        
        model_name = self.get_model_name(model_type)
        logger.debug(f"Selected model for {brain_type.value}: {model_name} (type={model_type.value}, complexity={complexity})")
        
        return model_name, model_type
    
    @retry(
        retry=retry_if_exception_type((LLMException, Exception)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def generate(
        self,
        prompt: str,
        brain_type: BrainType,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: int = 2500,  # ✅ Increased from 2000 to 2500 to ensure complete city names are included
        response_format: str = "text"
    ) -> str:
        """
        Generate content using specified brain
        
        Args:
            prompt: User prompt
            brain_type: Type of brain to use
            system_prompt: Optional system instruction
            model_type: Force specific model type (overrides auto-selection)
            complexity: Complexity hint ("simple", "moderate", "complex")
            temperature: Override default temperature for brain
            max_tokens: Maximum output tokens
            response_format: Response format ("text" or "json")
            
        Returns:
            Generated text
        """
        # Select model
        model_name, selected_type = self.select_model_for_brain(
            brain_type=brain_type,
            complexity=complexity,
            force_model=model_type
        )
        
        # Get temperature (use brain default if not specified)
        if temperature is None:
            temperature = self.BRAIN_TEMPERATURES.get(brain_type, 0.7)
        
        try:
            # Configure generation
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # Safety settings (BLOCK_NONE for production flexibility)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            # Combine system prompt with user prompt (for compatibility)
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"
            
            # Create model
            model = genai.GenerativeModel(model_name=model_name)
            
            # Call in executor to avoid blocking
            loop = asyncio.get_running_loop()
            
            def _call_gemini():
                return model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            
            # Add timeout
            try:
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, _call_gemini),
                    timeout=settings.gemini_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error(f"LLM call timed out after {settings.gemini_timeout_seconds}s (brain={brain_type.value}, model={model_name})")
                raise LLMException("LLM call timed out")
            except ResourceExhausted as quota_error:
                # Catch quota error early and fallback immediately (don't retry with same model)
                error_str = str(quota_error)
                if "quota" in error_str.lower() or "429" in error_str:
                    logger.warning(f"Quota exceeded for {model_name}, falling back to default model version")
                    # Retry with default model version instead of preview
                    if self.model_version == "preview":
                        fallback_model_name = self.get_model_name(selected_type, version="default")
                        logger.info(f"Retrying with fallback model: {fallback_model_name}")
                        try:
                            # Retry with default model
                            model = genai.GenerativeModel(model_name=fallback_model_name)
                            def _call_gemini_fallback():
                                return model.generate_content(
                                    full_prompt,
                                    generation_config=generation_config,
                                    safety_settings=safety_settings
                                )
                            response = await asyncio.wait_for(
                                loop.run_in_executor(None, _call_gemini_fallback),
                                timeout=settings.gemini_timeout_seconds
                            )
                            text = self._extract_text(response, fallback_model_name)
                            logger.info(f"Successfully used fallback model: {fallback_model_name}")
                            return text
                        except Exception as fallback_error:
                            logger.error(f"Fallback model also failed: {fallback_error}")
                            # ✅ Final fallback: Try FLASH model if PRO model failed (FLASH usually has more quota)
                            if selected_type == ModelType.PRO:
                                try:
                                    flash_model_name = self.get_model_name(ModelType.FLASH, version="default")
                                    logger.info(f"Trying final fallback to FLASH model: {flash_model_name}")
                                    model = genai.GenerativeModel(model_name=flash_model_name)
                                    def _call_gemini_flash():
                                        return model.generate_content(
                                            full_prompt,
                                            generation_config=generation_config,
                                            safety_settings=safety_settings
                                        )
                                    response = await asyncio.wait_for(
                                        loop.run_in_executor(None, _call_gemini_flash),
                                        timeout=settings.gemini_timeout_seconds
                                    )
                                    text = self._extract_text(response, flash_model_name)
                                    logger.info(f"Successfully used FLASH fallback model: {flash_model_name}")
                                    return text
                                except Exception as flash_error:
                                    logger.error(f"FLASH fallback model also failed: {flash_error}")
                            raise LLMException(f"LLM call failed (quota exceeded and all fallbacks failed): {quota_error}") from quota_error
                    else:
                        raise LLMException(f"LLM call failed (quota exceeded): {quota_error}") from quota_error
                else:
                    raise LLMException(f"LLM call failed: {quota_error}") from quota_error
            
            # Extract text
            text = self._extract_text(response, model_name)
            
            if not text or not text.strip():
                logger.warning(f"Empty response from {brain_type.value} (model={model_name})")
                # ✅ FIX: Return fallback message instead of empty string
                text = "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
            return text
            
        except ResourceExhausted as quota_error:
            # Handle quota error that wasn't caught earlier (e.g., if wrapped)
            error_str = str(quota_error)
            if "quota" in error_str.lower() or "429" in error_str:
                logger.warning(f"Quota exceeded for {model_name} (outer catch), falling back to default model version")
                if self.model_version == "preview":
                    fallback_model_name = self.get_model_name(selected_type, version="default")
                    logger.info(f"Retrying with fallback model: {fallback_model_name}")
                    try:
                        model = genai.GenerativeModel(model_name=fallback_model_name)
                        loop = asyncio.get_running_loop()
                        def _call_gemini_fallback():
                            return model.generate_content(
                                full_prompt,
                                generation_config=generation_config,
                                safety_settings=safety_settings
                            )
                        response = await asyncio.wait_for(
                            loop.run_in_executor(None, _call_gemini_fallback),
                            timeout=settings.gemini_timeout_seconds
                        )
                        text = self._extract_text(response, fallback_model_name)
                        logger.info(f"Successfully used fallback model: {fallback_model_name}")
                        return text
                    except Exception as fallback_error:
                        logger.error(f"Fallback model also failed: {fallback_error}")
                        # ✅ Final fallback: Try FLASH model if PRO model failed (FLASH usually has more quota)
                        if selected_type == ModelType.PRO:
                            try:
                                flash_model_name = self.get_model_name(ModelType.FLASH, version="default")
                                logger.info(f"Trying final fallback to FLASH model: {flash_model_name}")
                                model = genai.GenerativeModel(model_name=flash_model_name)
                                loop = asyncio.get_running_loop()
                                def _call_gemini_flash():
                                    return model.generate_content(
                                        full_prompt,
                                        generation_config=generation_config,
                                        safety_settings=safety_settings
                                    )
                                response = await asyncio.wait_for(
                                    loop.run_in_executor(None, _call_gemini_flash),
                                    timeout=settings.gemini_timeout_seconds
                                )
                                text = self._extract_text(response, flash_model_name)
                                logger.info(f"Successfully used FLASH fallback model: {flash_model_name}")
                                return text
                            except Exception as flash_error:
                                logger.error(f"FLASH fallback model also failed: {flash_error}")
                        raise LLMException(f"LLM call failed (quota exceeded and all fallbacks failed): {quota_error}") from quota_error
                raise LLMException(f"LLM call failed (quota exceeded): {quota_error}") from quota_error
        except Exception as e:
            logger.error(f"LLM generation error in {brain_type.value}: {e}", exc_info=True)
            raise LLMException(f"LLM call failed: {e}") from e
    
    async def generate_json(
        self,
        prompt: str,
        brain_type: BrainType,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response
        
        Args:
            prompt: User prompt
            brain_type: Type of brain to use
            system_prompt: Optional system instruction
            model_type: Force specific model type
            complexity: Complexity hint
            temperature: Override temperature
            
        Returns:
            Parsed JSON dictionary
        """
        # Generate with higher max_tokens for JSON
        text = await self.generate(
            prompt=prompt,
            brain_type=brain_type,
            system_prompt=system_prompt,
            model_type=model_type,
            complexity=complexity,
            temperature=temperature,
            max_tokens=4000,
            response_format="json"
        )
        
        # Extract and parse JSON
        try:
            parsed = self._extract_json_from_text(text)
            if not parsed:
                logger.warning(f"Empty JSON from {brain_type.value}: {text[:200]}...")
                return {}
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {brain_type.value}: {e}")
            logger.error(f"Raw text: {text[:500]}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing JSON: {e}")
            return {}
    
    def _extract_text(self, response, model_name: str) -> str:
        """Extract text from Gemini response safely"""
        try:
            # Check for valid parts
            if hasattr(response, 'parts') and response.parts:
                text = response.text
                if text and text.strip():
                    return text
            
            # Check for text attribute
            if hasattr(response, 'text') and response.text:
                text = response.text
                if text and text.strip():
                    return text
            
            # Check finish reason
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                finish_reason = getattr(candidate, 'finish_reason', None)
                
                if finish_reason == 2:  # SAFETY
                    safety_ratings = getattr(candidate, 'safety_ratings', 'Unknown')
                    logger.warning(f"Response blocked by safety (model={model_name}): {safety_ratings}")
                    return "ขออภัยค่ะ ฉันไม่สามารถตอบคำถามนี้ได้เนื่องจากการตรวจสอบความปลอดภัย กรุณาลองถามใหม่อีกครั้งค่ะ"
                
                elif finish_reason == 3:  # MAX_TOKENS
                    logger.warning(f"Response truncated (model={model_name})")
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            text = candidate.content.parts[0].text
                            if text and text.strip():
                                return text
                
                elif finish_reason == 4:  # RECITATION
                    logger.warning(f"Response blocked due to recitation (model={model_name})")
                    return "ขอภัยค่ะ ฉันตรวจพบว่าคำตอบอาจจะคล้ายกับเนื้อหาที่มีลิขสิทธิ์ กรุณาลองถามด้วยวิธีอื่นค่ะ"
                
                elif finish_reason == 1:  # STOP (normal)
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            text = candidate.content.parts[0].text
                            if text and text.strip():
                                return text
                
                # Try to get text from candidate content directly
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        for part in candidate.content.parts:
                            if hasattr(part, 'text') and part.text:
                                text = part.text
                                if text and text.strip():
                                    return text
            
            logger.warning(f"Unexpected response structure (model={model_name})")
            # ✅ FIX: Return fallback message instead of empty string
            return "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
        except Exception as e:
            logger.error(f"Error extracting text: {e}", exc_info=True)
            # ✅ FIX: Return fallback message instead of empty string
            return "ขออภัยค่ะ เกิดข้อผิดพลาดในการดึงข้อมูลคำตอบ กรุณาลองใหม่อีกครั้งนะคะ"
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON object from text"""
        if not text:
            return None
        
        # Clean markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Find JSON object
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            return None
        
        json_str = text[start_idx:end_idx + 1]
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try cleanup
            try:
                json_str = json_str.replace('\n', ' ')
                return json.loads(json_str)
            except:
                pass
            
            # Try line by line
            for line in text.splitlines():
                try:
                    if line.strip().startswith('{') and line.strip().endswith('}'):
                        return json.loads(line.strip())
                except:
                    continue
            
            return None
    
    # =============================================================================
    # Convenience methods for each brain type
    # =============================================================================
    
    async def controller_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate controller decision (JSON)"""
        try:
            result = await self.generate_json(
                prompt=prompt,
                brain_type=BrainType.CONTROLLER,
                system_prompt=system_prompt,
                model_type=model_type,
                complexity=complexity
            )
            # ✅ CRITICAL: Ensure result is never None
            if not result or not isinstance(result, dict):
                logger.warning("Controller returned invalid JSON, using fallback")
                return {"error": "invalid_response", "action": "ASK_USER", "payload": {"message": "กรุณาลองใหม่อีกครั้ง"}}
            return result
        except LLMException as e:
            logger.error(f"Controller LLM error: {e}")
            # Return safe fallback action
            return {"error": "llm_error", "action": "ASK_USER", "payload": {"message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}}
        except Exception as e:
            logger.error(f"Unexpected error in controller_generate: {e}", exc_info=True)
            return {"error": "unexpected_error", "action": "ASK_USER", "payload": {"message": "เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง"}}
    
    async def responder_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None
    ) -> str:
        """Generate responder message (text)"""
        try:
            response_text = await self.generate(
                prompt=prompt,
                brain_type=BrainType.RESPONDER,
                system_prompt=system_prompt,
                model_type=model_type,
                complexity=complexity,
                max_tokens=2500  # ✅ Increased to ensure complete city names are included
            )
            # ✅ CRITICAL: Ensure response_text is never None or empty
            if not response_text or not response_text.strip():
                logger.warning("Responder returned empty text, using fallback")
                response_text = "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            return response_text
        except LLMException as e:
            logger.error(f"Responder LLM error: {e}")
            # Return user-friendly error message
            error_str = str(e).lower()
            # ✅ Handle quota exceeded errors
            if "429" in error_str or "quota" in error_str or "exceeded" in error_str:
                return (
                    "⚠️ ขออภัยค่ะ API quota หมดแล้วสำหรับวันนี้\n\n"
                    "Free tier limit: 20 requests/day per model\n\n"
                    "กรุณา:\n"
                    "1. รอจนกว่า quota จะ reset (ทุกวัน)\n"
                    "2. หรือ upgrade Google Cloud plan เพื่อเพิ่ม quota\n\n"
                    "หากต้องการใช้งานต่อทันที กรุณาติดต่อ support"
                )
            elif "api" in error_str and "key" in error_str:
                return "ขออภัยค่ะ ระบบไม่สามารถเชื่อมต่อกับ AI service ได้ กรุณาตรวจสอบ GEMINI_API_KEY ในไฟล์ .env"
            elif "timeout" in error_str:
                return "ขออภัยค่ะ ระบบใช้เวลาประมวลผลนานเกินไป กรุณาลองใหม่อีกครั้ง"
            else:
                return "ขออภัยค่ะ เกิดข้อผิดพลาดในการสร้างคำตอบ กรุณาลองใหม่อีกครั้ง"
        except Exception as e:
            logger.error(f"Unexpected error in responder_generate: {e}", exc_info=True)
            return "ขออภัยค่ะ ระบบไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
    
    async def intelligence_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate intelligence analysis (JSON)"""
        return await self.generate_json(
            prompt=prompt,
            brain_type=BrainType.INTELLIGENCE,
            system_prompt=system_prompt,
            model_type=model_type,
            complexity=complexity
        )


# Global singleton instance
_production_llm_service: Optional[ProductionLLMService] = None


def get_production_llm() -> ProductionLLMService:
    """Get or create global ProductionLLMService instance"""
    global _production_llm_service
    if _production_llm_service is None:
        _production_llm_service = ProductionLLMService()
    return _production_llm_service
