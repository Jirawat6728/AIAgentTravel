"""
Robust LLM Service with Retries using tenacity
Production-grade error handling
"""

from __future__ import annotations
from typing import Any, Dict, Optional
import asyncio
import json
import logging
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.exceptions import LLMException
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """
    Production-Grade LLM Service
    - Retries on invalid JSON (max 3 times using tenacity)
    - Strict timeouts
    - Safe fallback messages
    """
    
    def __init__(self):
        """Initialize LLM Service"""
        try:
            from google import genai
            if not settings.gemini_api_key:
                raise LLMException("GEMINI_API_KEY not set in environment")
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.model_name = settings.gemini_model_name
            self.timeout = settings.gemini_timeout_seconds
            self.max_retries = settings.gemini_max_retries
            
            # Mask API key for logging
            masked_key = f"{settings.gemini_api_key[:6]}...{settings.gemini_api_key[-4:]}" if len(settings.gemini_api_key) > 10 else "INVALID_KEY"
            logger.info(f"LLMService initialized with model: {self.model_name}, key: {masked_key}")
        except Exception as e:
            logger.error(f"Failed to initialize LLMService: {e}")
            raise LLMException(f"LLM initialization failed: {e}") from e
    
    async def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> str:
        """
        Generate content from LLM with retries and timeout
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            response_format: Optional response format (e.g., "application/json")
            
        Returns:
            Generated text
            
        Raises:
            LLMException: If generation fails after retries
        """
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            response = await asyncio.wait_for(
                self._call_llm_with_retry(full_prompt, temperature, max_tokens, response_format),
                timeout=self.timeout
            )
            
            text = self._extract_text(response)
            return text
        
        except asyncio.TimeoutError:
            logger.error("LLM call timed out")
            raise LLMException("LLM call timed out")
        except Exception as e:
            logger.error(f"LLM call failed: {e}", exc_info=True)
            raise LLMException(f"LLM call failed: {e}") from e
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMException, json.JSONDecodeError)),
        reraise=True
    )
    async def _call_llm_with_retry(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str]
    ) -> Any:
        """Call LLM with retry logic for JSON errors"""
        response = await self._call_llm(prompt, temperature, max_tokens, response_format)
        
        # Validate JSON if response_format is JSON
        if response_format == "application/json":
            text = self._extract_text(response)
            try:
                json.loads(text)
                logger.debug("LLM returned valid JSON")
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from LLM, will retry: {e}")
                raise LLMException("Invalid JSON from LLM") from e
        
        return response
    
    async def _call_llm(
        self,
        prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: Optional[str]
    ) -> Any:
        """Call LLM in thread pool to avoid blocking"""
        def _call():
            from google.genai import types
            
            # Disable safety filters to prevent blocking Thai responses
            safety_settings = [
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            ]
            
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                safety_settings=safety_settings
            )
            if response_format:
                config.response_mime_type = response_format
            
            return self.client.models.generate_content(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
                config=config
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    
    def _extract_text(self, response: Any) -> str:
        """Extract text from LLM response"""
        try:
            # Case 1: Response object has .text attribute (standard)
            if hasattr(response, 'text') and response.text is not None:
                return response.text.strip()
            
            # Case 2: Response has candidates (more granular)
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Check for blocking reasons
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason:
                    reason = str(candidate.finish_reason)
                    if "SAFETY" in reason:
                        logger.warning("LLM response blocked by safety filters")
                        return "ขออภัยค่ะ ข้อมูลที่คุณขอถูกจำกัดโดยระบบความปลอดภัย"
                    if "MAX_TOKENS" in reason:
                        logger.warning("LLM response cut off by max tokens")
                        # Try to get whatever text was generated before the cutoff
                        content = getattr(candidate, "content", None)
                        parts = getattr(content, "parts", None) or []
                        texts = [getattr(p, "text", "") for p in parts if getattr(p, "text", None)]
                        if texts:
                            return "\n".join(texts).strip() + "... (ข้อความยาวเกินกำหนด)"
                        return "ขออภัยค่ะ คำตอบมีความยาวมากเกินไป กรุณาลองถามให้กระชับขึ้นนะคะ"
                
                content = getattr(candidate, "content", None)
                parts = getattr(content, "parts", None) or []
                texts = []
                for p in parts:
                    t = getattr(p, "text", None)
                    if t:
                        texts.append(t)
                
                if texts:
                    return "\n".join(texts).strip()
            
            # Case 3: Avoid returning raw object string if it looks like the internal candidate list
            res_str = str(response).strip()
            if res_str and res_str != "None" and "candidates=[" not in res_str:
                return res_str
                
            return "ขออภัยค่ะ ระบบไม่สามารถประมวลผลคำตอบได้ในขณะนี้"
        except Exception as e:
            logger.error(f"Error extracting text from response: {e}")
            raise LLMException(f"Failed to extract text from LLM response: {e}") from e
    
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM with robust extraction
        """
        text = await self.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format="application/json"
        )
        
        try:
            # Simple case: direct JSON
            return json.loads(text)
        except json.JSONDecodeError:
            # Robust case: Extract JSON using markers
            logger.warning(f"Failed to parse direct JSON, trying extraction from: {text[:100]}...")
            try:
                import re
                # Find content between first { and last }
                match = re.search(r'(\{.*\})', text, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    return json.loads(json_str)
            except Exception as e:
                logger.error(f"JSON extraction failed: {e}")
            
            # If all fails, return a safe fallback instead of raising error
            logger.error(f"Could not extract JSON from response: {text[:200]}")
            return {}  # Return empty dict to prevent crash
