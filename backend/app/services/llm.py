"""
LLM Service Wrapper for Google Gemini
Handles API calls, retries, error handling, and response processing
Supports optional MCP (Model Context Protocol) integration for tool calling
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List
import json
import asyncio
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)

# Optional Gemini import (disabled by default)
_gemini_available = False
if settings.enable_gemini:
    try:
        import google.generativeai as genai
        from google.generativeai.types import HarmCategory, HarmBlockThreshold
        _gemini_available = True
    except ImportError:
        logger.warning("Google Generative AI library not installed. Gemini support disabled.")

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Gemini Configuration (Primary)
        self.gemini_api_key = api_key or settings.gemini_api_key
        self.enable_gemini = settings.enable_gemini and _gemini_available
        self.model_name = model_name or settings.gemini_model_name
        
        if not _gemini_available:
            raise LLMException("Google Generative AI library not installed. Please install: pip install google-generativeai")
        
        # ✅ Enhanced API key validation
        if not self.gemini_api_key or not self.gemini_api_key.strip():
            error_msg = (
                "GEMINI_API_KEY is required but not found.\n"
                "Please set GEMINI_API_KEY in your .env file.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )
            logger.error(error_msg)
            raise LLMException(error_msg)
        
        # ✅ Validate API key format (basic check)
        if len(self.gemini_api_key.strip()) < 20:
            error_msg = (
                "GEMINI_API_KEY appears to be invalid (too short).\n"
                "Please check your API key in .env file.\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )
            logger.error(error_msg)
            raise LLMException(error_msg)
        
        if self.enable_gemini and self.gemini_api_key:
            try:
                genai.configure(api_key=self.gemini_api_key)
                logger.info(f"LLMService initialized with Gemini: model={self.model_name}, key={self.gemini_api_key[:6]}...{self.gemini_api_key[-4:]}")
            except Exception as config_error:
                error_msg = (
                    f"Failed to configure Gemini API: {config_error}\n"
                    "Please check:\n"
                    "1. GEMINI_API_KEY is correct in .env file\n"
                    "2. API key has proper permissions\n"
                    "3. Internet connection is available"
                )
                logger.error(error_msg)
                raise LLMException(error_msg)
        else:
            error_msg = (
                "Gemini is disabled or API key is missing.\n"
                "Please set in .env file:\n"
                "  ENABLE_GEMINI=true\n"
                "  GEMINI_API_KEY=your_api_key_here\n"
                "Get your API key from: https://makersuite.google.com/app/apikey"
            )
            logger.error(error_msg)
            raise LLMException(error_msg)

    async def generate_content(
        self, 
        prompt: str, 
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        response_format: str = "text/plain",
        auto_select_model: bool = True,
        context: Optional[str] = None
    ) -> str:
        """
        Generate content from LLM with robust error handling.
        Uses Gemini as the primary LLM provider.
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            response_format: Response format
            auto_select_model: Enable automatic model selection
            context: Optional context for model selection
        """
        if self.enable_gemini:
            return await self._generate_with_gemini(prompt, system_prompt, temperature, max_tokens, auto_select_model, context)
        else:
            raise LLMException("Gemini is not enabled. Please set ENABLE_GEMINI=true and GEMINI_API_KEY in your .env file.")

    async def _generate_with_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        auto_select_model: bool = True,
        context: Optional[str] = None
    ) -> str:
        """Generate content using Gemini API"""
        if not self.enable_gemini or not _gemini_available:
            raise LLMException("Gemini is disabled. Enable it in settings to use.")
        
        if not self.gemini_api_key:
            raise LLMException("Gemini API Key is missing")
        
        # 🤖 Auto Model Selection
        selected_model = self.model_name
        if auto_select_model and settings.enable_auto_model_switching:
            try:
                from app.services.model_selector import select_model_for_task
                selected_model = select_model_for_task(prompt, context=context)
                logger.debug(f"Auto-selected model: {selected_model} (context={context})")
            except Exception as e:
                logger.warning(f"Model auto-selection failed: {e}, using default: {self.model_name}")
                selected_model = self.model_name
        else:
            logger.debug(f"Using default model: {selected_model}")
        
        # ✅ FIX: Replace deprecated model names and validate
        if "-latest" in selected_model:
            selected_model = selected_model.replace("-latest", "")
            logger.warning(f"Replaced deprecated -latest suffix. Using model: {selected_model}")
        
        # ✅ FIX: Ensure model name is valid
        if not selected_model or selected_model.strip() == "":
            selected_model = "gemini-2.5-flash"  # Default fallback - use 2.5 version
            logger.warning(f"Model name was empty, using fallback: {selected_model}")
        
        # ✅ FIX: Convert deprecated model names to stable 2.5 versions
        # gemini-1.5-flash is deprecated, use gemini-2.5-flash instead
        model_name_mapping = {
            "gemini-1.5-flash": "gemini-2.5-flash",  # Deprecated -> stable 2.5
            "gemini-1.5-flash-001": "gemini-2.5-flash",  # Old versioned name -> 2.5
            "gemini-1.5-flash-002": "gemini-2.5-flash",  # Old versioned name -> 2.5
            "gemini-1.5-pro": "gemini-2.5-pro",      # Deprecated -> stable 2.5
            "gemini-1.5-pro-001": "gemini-2.5-pro",  # Old versioned name -> 2.5
        }
        if selected_model in model_name_mapping:
            mapped_model = model_name_mapping[selected_model]
            logger.info(f"Mapping deprecated model name to stable version: {selected_model} -> {mapped_model}")
            selected_model = mapped_model
        # Also check if model name contains "1.5" and replace with "2.5"
        elif "1.5" in selected_model:
            selected_model = selected_model.replace("1.5", "2.5")
            logger.info(f"Auto-updated deprecated 1.5 model to 2.5: {selected_model}")

        try:
            # Configure generation config
            generation_config = genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            )

            # Configure safety settings (BLOCK_NONE to prevent over-filtering)
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            # Combine system prompt with user prompt
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # ✅ FIX: Replace deprecated model names
            if "-latest" in selected_model:
                selected_model = selected_model.replace("-latest", "")
                logger.warning(f"Replaced deprecated -latest suffix. Using model: {selected_model}")
            
            # ✅ FIX: Ensure model name is valid - use from settings
            if not selected_model or selected_model.strip() == "":
                selected_model = settings.gemini_model_name  # Use from .env
                logger.warning(f"Model name was empty, using from settings: {selected_model}")

            model = genai.GenerativeModel(model_name=selected_model)

            # Run in executor to avoid blocking event loop
            loop = asyncio.get_running_loop()
            
            def _call_gemini():
                return model.generate_content(
                    full_prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings
                )
            
            # ✅ Optimized for 1.5-minute completion: Reduce LLM timeout to 20s
            timeout_seconds = min(settings.gemini_timeout_seconds, 20)  # ✅ Reduced from 30s to 20s
            try:
                logger.debug(f"Calling Gemini API: model={selected_model}, prompt_length={len(prompt)}, timeout={timeout_seconds}s")
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, _call_gemini),
                    timeout=timeout_seconds
                )
                logger.debug(f"Gemini API call completed: model={selected_model}")
            except asyncio.TimeoutError:
                logger.error(f"Gemini call timed out after {timeout_seconds}s for model {selected_model}")
                raise LLMException(f"Gemini call timed out after {timeout_seconds} seconds")
            except Exception as api_error:
                error_str = str(api_error).lower()
                error_msg_full = str(api_error)
                
                # ✅ Handle 429 Quota Exceeded errors specifically
                if "429" in error_str or "quota" in error_str or "exceeded" in error_str:
                    # Extract retry delay if available
                    retry_delay = 10  # Default 10 seconds
                    if "retry" in error_msg_full.lower():
                        try:
                            import re
                            retry_match = re.search(r'retry.*?(\d+(?:\.\d+)?)', error_msg_full, re.IGNORECASE)
                            if retry_match:
                                retry_delay = max(int(float(retry_match.group(1))), 10)  # At least 10 seconds
                        except:
                            pass
                    
                    error_msg = (
                        f"⚠️ Gemini API quota exceeded (429): {selected_model}\n\n"
                        f"Free tier limit: 20 requests/day per model\n"
                        f"Please wait {retry_delay} seconds before retrying, or:\n"
                        "1. Upgrade your Google Cloud plan to increase quota\n"
                        "2. Use a different Gemini model\n"
                        "3. Wait until quota resets (daily limit)\n\n"
                        f"Error details: {str(api_error)[:300]}\n"
                        "Learn more: https://ai.google.dev/gemini-api/docs/rate-limits"
                    )
                    logger.warning(error_msg)
                    # ✅ Create special exception for quota errors that includes retry delay
                    quota_exception = LLMException(error_msg)
                    quota_exception.retry_delay = retry_delay
                    quota_exception.is_quota_error = True
                    raise quota_exception
                elif "api" in error_str and "key" in error_str:
                    error_msg = (
                        f"Gemini API key error: {api_error}\n"
                        "Please check:\n"
                        "1. GEMINI_API_KEY is set correctly in .env file\n"
                        "2. API key is valid and not expired\n"
                        "3. API key has proper permissions\n"
                        "Get your API key from: https://makersuite.google.com/app/apikey"
                    )
                    logger.error(error_msg)
                    raise LLMException(error_msg)
                elif "404" in error_str or "not found" in error_str:
                    error_msg = (
                        f"Gemini model not found: {selected_model}\n"
                        f"Error: {api_error}\n"
                        "Please check model name in .env file (GEMINI_MODEL_NAME)"
                    )
                    logger.error(error_msg)
                    raise LLMException(error_msg)
                elif "403" in error_str or "permission" in error_str:
                    error_msg = (
                        f"Gemini API permission denied: {api_error}\n"
                        "Please check:\n"
                        "1. API key has proper permissions\n"
                        "2. API key is not restricted\n"
                        "3. Billing is enabled for your Google Cloud project"
                    )
                    logger.error(error_msg)
                    raise LLMException(error_msg)
                else:
                    logger.error(f"Gemini API error: {api_error}", exc_info=True)
                    raise LLMException(f"Gemini API error: {str(api_error)[:200]}")

            # Extract text and handle empty responses
            text = self._extract_text(response)
            
            if not text or not text.strip():
                logger.warning(f"Gemini returned empty text. prompt_length={len(prompt)}, model={selected_model}")
                # ✅ FIX: Return fallback message instead of empty string
                return "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"
            
            return text

        except LLMException:
            raise
        except Exception as e:
            logger.error(f"Gemini generation error: {e}", exc_info=True)
            raise LLMException(f"Gemini call failed: {str(e)[:200]}") from e

    def _extract_text(self, response) -> str:
        """Extract text from Gemini response safely"""
        try:
            # Check for valid parts (most common case)
            if hasattr(response, 'parts') and response.parts:
                return response.text
            
            # Check for text attribute directly
            if hasattr(response, 'text') and response.text:
                return response.text
            
            # Check finish reason (for error cases)
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # Handle different finish reasons
                # FINISH_REASON: UNSPECIFIED=0, STOP=1, SAFETY=2, MAX_TOKENS=3, RECITATION=4, OTHER=5
                finish_reason = getattr(candidate, 'finish_reason', None)
                
                if finish_reason == 2:  # ✅ SAFETY (was incorrectly 4)
                    safety_ratings = getattr(candidate, 'safety_ratings', 'Unknown')
                    logger.warning(f"Response blocked by safety filters. finish_reason={finish_reason}, ratings={safety_ratings}")
                    return "ขออภัยค่ะ ฉันไม่สามารถตอบคำถามนี้ได้เนื่องจากการตรวจสอบความปลอดภัย กรุณาลองถามใหม่อีกครั้งด้วยวิธีอื่นค่ะ"
                
                elif finish_reason == 3:  # MAX_TOKENS
                    logger.warning("Response truncated due to max tokens")
                    # Try to return what we have
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            return candidate.content.parts[0].text
                
                elif finish_reason == 4:  # RECITATION
                    logger.warning(f"Response blocked due to recitation")
                    return "ขอภัยค่ะ ฉันตรวจพบว่าคำตอบอาจจะคล้ายกับเนื้อหาที่มีลิขสิทธิ์ กรุณาลองถามด้วยวิธีอื่นค่ะ"
                
                elif finish_reason == 1:  # STOP (normal completion)
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts') and candidate.content.parts:
                            return candidate.content.parts[0].text
                
                # Try to get text from candidate content
                if hasattr(candidate, 'content') and candidate.content:
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        return candidate.content.parts[0].text

            # If we get here, something is wrong or empty
            finish_reason = 'Unknown'
            if hasattr(response, 'candidates') and response.candidates:
                finish_reason = getattr(response.candidates[0], 'finish_reason', 'Unknown')
            logger.warning(f"Unexpected response structure or empty content. Finish reason: {finish_reason}")
            # ✅ FIX: Return fallback message instead of empty string
            return "ขออภัยค่ะ ฉันไม่สามารถสร้างคำตอบได้ในขณะนี้ กรุณาลองใหม่อีกครั้งนะคะ"

        except (AttributeError, IndexError, KeyError) as e:
            logger.error(f"Error extracting text from response: {e}", exc_info=True)
            # Try a desperate fallback
            try:
                if hasattr(response, 'text'):
                    text = response.text
                    if text and text.strip():
                        return text
            except:
                pass
            # ✅ FIX: Return fallback message instead of empty string
            return "ขออภัยค่ะ เกิดข้อผิดพลาดในการดึงข้อมูลคำตอบ กรุณาลองใหม่อีกครั้งนะคะ"
        except Exception as e:
            logger.error(f"Unexpected error extracting text from response: {e}", exc_info=True)
            # ✅ FIX: Return fallback message instead of empty string
            return "ขออภัยค่ะ เกิดข้อผิดพลาดในการสร้างคำตอบ กรุณาลองใหม่อีกครั้งนะคะ"

    @retry(
        retry=retry_if_exception_type(json.JSONDecodeError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _call_llm_with_retry(self, *args, **kwargs) -> Dict[str, Any]:
        """Internal helper to retry JSON generation"""
        text = await self.generate_content(*args, **kwargs)
        # Use our robust extractor instead of direct json.loads
        parsed = self._extract_json_from_text(text)
        if parsed is None:
             raise json.JSONDecodeError("Could not extract JSON object", text, 0)
        return parsed

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        auto_select_model: bool = True,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON response from LLM with validation and robust extraction.
        ALWAYS returns a valid Dict, never raises (ensures run_turn always gets valid JSON).
        
        Args:
            prompt: User prompt
            system_prompt: System instruction
            temperature: Sampling temperature
            auto_select_model: Enable automatic model selection
            context: Optional context for model selection
            
        Returns:
            Always a valid Dict (may be empty if extraction fails)
        """
        try:
            # Increased max_tokens for JSON to prevent cutoff
            text = await self.generate_content(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                response_format="application/json",
                max_tokens=4000,
                auto_select_model=auto_select_model,  # 🤖 Pass through
                context=context  # 🤖 Pass through
            )
            
            # Attempt to extract and parse JSON, even if it's malformed or has extra text
            try:
                parsed_json = self._extract_json_from_text(text)
                if not parsed_json:
                    logger.warning(f"Extracted empty JSON from LLM response: {text[:200]}...")
                    return {"error": "empty_response", "message": "LLM returned empty JSON"}  # Always return valid dict
                return parsed_json
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON after extraction: {e}")
                logger.error(f"Raw Text causing error: {text[:500]}")  # Limit log length
                return {"error": "json_parse_failed", "message": f"Failed to parse JSON: {str(e)[:100]}"}  # Always return valid dict
            except Exception as e:
                logger.error(f"Unexpected error during JSON extraction: {e}", exc_info=True)
                return {"error": "extraction_failed", "message": str(e)[:100]}  # Always return valid dict
        except LLMException as e:
            # LLM errors (timeout, API error, etc.) - return error dict instead of raising
            logger.error(f"LLM error in generate_json: {e}")
            return {"error": "llm_error", "message": str(e)[:200]}  # Always return valid dict
        except Exception as e:
            # Any other unexpected error - return error dict instead of raising
            logger.error(f"Unexpected error in generate_json: {e}", exc_info=True)
            return {"error": "unexpected_error", "message": str(e)[:200]}  # Always return valid dict

    def _extract_json_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extracts the first valid JSON object from a string that might contain
        additional text before or after the JSON.
        """
        if not text:
            return None
            
        # Clean up common markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        # Find the first occurrence of '{' and the last occurrence of '}'
        start_idx = text.find('{')
        end_idx = text.rfind('}')

        if start_idx == -1 or end_idx == -1:
            return None # No JSON object found

        json_str = text[start_idx : end_idx + 1]
        
        # Attempt to parse the extracted string
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # If direct parse fails, try to repair common issues (e.g. newlines in strings)
            try:
                # Basic cleanup
                json_str = json_str.replace('\n', ' ')
                return json.loads(json_str)
            except:
                pass
                
            # If still fails, try to find a more robust way (e.g., by line)
            lines = text.splitlines()
            for line in lines:
                try:
                    if line.strip().startswith('{') and line.strip().endswith('}'):
                        return json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
            return None # No valid JSON found after robust attempts


# =============================================================================
# MCP (Model Context Protocol) Support
# =============================================================================

class LLMServiceWithMCP(LLMService):
    """
    Enhanced LLM Service with MCP Tool Support
    Uses Gemini for tool calling
    Extends LLMService for backward compatibility
    """
    
    def __init__(self):
        """Initialize LLM Service with MCP tools"""
        try:
            # Initialize base class first
            super().__init__()
            
            # Use Gemini for MCP tool calling
            if not _gemini_available:
                raise LLMException("Google Generative AI library not installed. Please install: pip install google-generativeai")
            
            try:
                from google import genai
                from google.genai import types
                
                if not settings.gemini_api_key:
                    raise LLMException("GEMINI_API_KEY not set in environment")
                
                self.mcp_client = genai.Client(api_key=settings.gemini_api_key)
                self.mcp_model_name = settings.gemini_model_name
                self.timeout = min(settings.gemini_timeout_seconds, 30)  # Strict 30s timeout
                
                # Convert MCP tools to Gemini function declarations
                from app.services.mcp_server import ALL_MCP_TOOLS
                self.tools = self._convert_mcp_to_gemini_tools(ALL_MCP_TOOLS)
                
                masked_key = f"{settings.gemini_api_key[:6]}...{settings.gemini_api_key[-4:]}" if len(settings.gemini_api_key) > 10 else "INVALID_KEY"
                logger.info(f"LLMServiceWithMCP initialized with Gemini + {len(ALL_MCP_TOOLS)} tools, model: {self.mcp_model_name}, key: {masked_key}")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini MCP support: {e}. Tool calling will not work.", exc_info=True)
                raise LLMException(f"Failed to initialize MCP support: {e}") from e
        
        except Exception as e:
            logger.error(f"Failed to initialize LLMServiceWithMCP: {e}")
            raise LLMException(f"LLM initialization failed: {e}") from e
    
    def _convert_mcp_to_gemini_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert MCP tool definitions to Gemini function declarations"""
        from google.genai import types
        
        gemini_tools = []
        for tool in mcp_tools:
            func_decl = types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        param_name: types.Schema(
                            type=self._convert_type(param_def.get("type", "string")),
                            description=param_def.get("description", "")
                        )
                        for param_name, param_def in tool["parameters"]["properties"].items()
                    },
                    required=tool["parameters"].get("required", [])
                )
            )
            gemini_tools.append(func_decl)
        
        return [types.Tool(function_declarations=gemini_tools)]
    
    def _convert_type(self, mcp_type: str) -> Any:
        """Convert MCP type to Gemini type"""
        from google.genai import types
        
        type_mapping = {
            "string": types.Type.STRING,
            "integer": types.Type.INTEGER,
            "number": types.Type.NUMBER,
            "boolean": types.Type.BOOLEAN,
            "object": types.Type.OBJECT,
            "array": types.Type.ARRAY
        }
        return type_mapping.get(mcp_type, types.Type.STRING)
    
    async def generate_with_tools(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        max_tool_calls: int = 5
    ) -> Dict[str, Any]:
        """
        Generate content with tool calling support
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            max_tool_calls: Maximum number of tool calls allowed in one turn
            
        Returns:
            Dictionary with 'text' (final response) and 'tool_calls' (list of executed tools)
        """
        from google.genai import types
        from app.services.mcp_server import mcp_executor
        
        conversation_history = [
            types.Content(
                role="user",
                parts=[types.Part(text=prompt)]
            )
        ]
        tool_call_history = []
        
        try:
            for iteration in range(max_tool_calls):
                logger.info(f"MCP iteration {iteration + 1}/{max_tool_calls}")
                
                try:
                    response = await asyncio.wait_for(
                        self._call_llm_with_tools(
                            contents=conversation_history, 
                            temperature=temperature, 
                            max_tokens=max_tokens,
                            system_prompt=system_prompt
                        ),
                        timeout=self.timeout  # Strict 30s timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"MCP iteration {iteration + 1} timed out after {self.timeout}s")
                    if iteration == 0:
                        # First iteration timeout is critical - return error instead of raising
                        return {
                            "text": f"ขออภัยค่ะ ระบบใช้เวลานานเกินไป ({self.timeout} วินาที) กรุณาลองใหม่อีกครั้ง",
                            "tool_calls": tool_call_history,
                            "error": "timeout_first_iteration"
                        }
                    # Otherwise, break and return what we have
                    break
                
                if not response or not hasattr(response, 'candidates') or not response.candidates:
                    logger.warning(f"No candidates in response (iteration {iteration + 1})")
                    break
                
                candidate = response.candidates[0]
                
                # Check for errors in candidate
                if hasattr(candidate, 'finish_reason') and candidate.finish_reason == 2:  # SAFETY
                    logger.warning("Response blocked by safety filters")
                    break
                
                model_content = candidate.content
                if not model_content:
                    logger.warning(f"Empty model content (iteration {iteration + 1})")
                    break
                
                conversation_history.append(model_content)
                
                if model_content and model_content.parts:
                    has_function_call = False
                    text_response = ""
                    function_responses = []
                    
                    for part in model_content.parts:
                        if hasattr(part, 'function_call') and part.function_call:
                            has_function_call = True
                            func_call = part.function_call
                            
                            logger.info(f"LLM requested tool: {func_call.name}")
                            
                            try:
                                # Execute tool with error handling (strict 30s timeout)
                                tool_result = await asyncio.wait_for(
                                    mcp_executor.execute_tool(
                                        tool_name=func_call.name,
                                        parameters=dict(func_call.args) if hasattr(func_call, 'args') else {}
                                    ),
                                    timeout=30  # Strict 30s timeout for tool execution
                                )
                                
                                # Check if tool execution was successful
                                if not isinstance(tool_result, dict):
                                    tool_result = {"success": False, "error": "Invalid tool result format"}
                                elif not tool_result.get("success", False):
                                    logger.warning(f"Tool {func_call.name} returned error: {tool_result.get('error', 'Unknown')}")
                                
                                tool_call_history.append({
                                    "tool": func_call.name,
                                    "parameters": dict(func_call.args) if hasattr(func_call, 'args') else {},
                                    "result": tool_result,
                                    "iteration": iteration + 1
                                })
                                
                                function_responses.append(
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name=func_call.name,
                                            response=tool_result
                                        )
                                    )
                                )
                            except asyncio.TimeoutError:
                                logger.error(f"Tool {func_call.name} execution timed out")
                                tool_result = {
                                    "success": False,
                                    "error": "Tool execution timed out",
                                    "tool": func_call.name
                                }
                                tool_call_history.append({
                                    "tool": func_call.name,
                                    "parameters": dict(func_call.args) if hasattr(func_call, 'args') else {},
                                    "result": tool_result,
                                    "iteration": iteration + 1
                                })
                                function_responses.append(
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name=func_call.name,
                                            response=tool_result
                                        )
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Tool {func_call.name} execution failed: {e}", exc_info=True)
                                tool_result = {
                                    "success": False,
                                    "error": f"Tool execution failed: {str(e)}",
                                    "tool": func_call.name
                                }
                                tool_call_history.append({
                                    "tool": func_call.name,
                                    "parameters": dict(func_call.args) if hasattr(func_call, 'args') else {},
                                    "result": tool_result,
                                    "iteration": iteration + 1
                                })
                                function_responses.append(
                                    types.Part(
                                        function_response=types.FunctionResponse(
                                            name=func_call.name,
                                            response=tool_result
                                        )
                                    )
                                )
                        elif hasattr(part, 'text') and part.text:
                            text_response += part.text
                    
                    if has_function_call:
                        conversation_history.append(
                            types.Content(
                                role="user",
                                parts=function_responses
                            )
                        )
                    else:
                        # No more function calls, return final response
                        return {
                            "text": text_response or "ขออภัยค่ะ ไม่สามารถสร้างคำตอบได้",
                            "tool_calls": tool_call_history
                        }
                else:
                    break
            
            # Max iterations reached
            logger.warning(f"Max tool call iterations ({max_tool_calls}) reached")
            return {
                "text": "ขออภัยค่ะ ระบบใช้เวลาในการค้นหานานเกินไป กรุณาลองใหม่อีกครั้ง",
                "tool_calls": tool_call_history,
                "warning": f"Reached max iterations ({max_tool_calls})"
            }
        
        except asyncio.TimeoutError:
            logger.error("LLM call with tools timed out")
            return {
                "text": "ขออภัยค่ะ ระบบใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง",
                "tool_calls": tool_call_history,
                "error": "timeout"
            }
        except Exception as e:
            logger.error(f"LLM call with tools failed: {e}", exc_info=True)
            return {
                "text": f"ขออภัยค่ะ เกิดข้อผิดพลาด: {str(e)[:100]}",
                "tool_calls": tool_call_history,
                "error": str(e)
            }
    
    async def _call_llm_with_tools(
        self,
        contents: List[Any],
        temperature: float,
        max_tokens: int,
        system_prompt: Optional[str] = None
    ) -> Any:
        """Call LLM with tools in thread pool"""
        def _call():
            from google.genai import types
            
            safety_settings = [
                types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="BLOCK_NONE"),
                types.SafetySetting(category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="BLOCK_NONE"),
            ]
            
            config = types.GenerateContentConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
                safety_settings=safety_settings,
                tools=self.tools,
                system_instruction=system_prompt
            )
            
            return self.mcp_client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
