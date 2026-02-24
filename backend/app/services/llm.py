"""
เซอร์วิส LLM สำหรับ Google Gemini
จัดการการเรียก API การลองใหม่ การจัดการข้อผิดพลาด และการประมวลผลคำตอบ
รองรับ MCP (Model Context Protocol) สำหรับ tool calling
รวม Production LLM (สามสมอง: Controller, Responder, Intelligence)
"""

from __future__ import annotations
from typing import Optional, Dict, Any, List, Literal
from enum import Enum
import json
import asyncio
import os
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)

# Use new google-genai SDK (v1+); fall back to deprecated google-generativeai if not available
_gemini_available = False
_use_new_sdk = False
genai = None
HarmCategory = None
HarmBlockThreshold = None

if settings.enable_gemini:
    try:
        import google.genai as genai  # type: ignore
        from google.genai import types as genai_types  # type: ignore
        _gemini_available = True
        _use_new_sdk = True
        logger.info("Using google-genai SDK (v1+)")
    except ImportError:
        try:
            import google.generativeai as genai  # type: ignore
            from google.generativeai.types import HarmCategory, HarmBlockThreshold  # type: ignore
            _gemini_available = True
            _use_new_sdk = False
            logger.warning("google-genai not found, falling back to deprecated google-generativeai")
        except ImportError:
            logger.warning("No Gemini SDK installed. Gemini support disabled.")

class LLMService:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        # Gemini Configuration (Primary)
        self.gemini_api_key = api_key or settings.gemini_api_key
        self.enable_gemini = settings.enable_gemini and _gemini_available
        self.model_name = model_name or settings.gemini_model_name

        # Shared Gemini client — created once and reused for all calls
        self._gemini_client = None

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
                if _use_new_sdk:
                    # New google-genai SDK: create shared client once
                    self._gemini_client = genai.Client(api_key=self.gemini_api_key)
                    logger.info(f"LLMService initialized with google-genai SDK: model={self.model_name}, key={self.gemini_api_key[:6]}...{self.gemini_api_key[-4:]}")
                else:
                    # Legacy google-generativeai SDK: needs global configure()
                    genai.configure(api_key=self.gemini_api_key)
                    logger.info(f"LLMService initialized with google-generativeai SDK: model={self.model_name}, key={self.gemini_api_key[:6]}...{self.gemini_api_key[-4:]}")
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

        # Fallback model chain: primary → flash → flash-8b
        _FALLBACK_CHAIN = [selected_model, "gemini-2.5-flash", "gemini-2.0-flash-lite"]
        _seen: set = set()
        fallback_models = [m for m in _FALLBACK_CHAIN if not (m in _seen or _seen.add(m))]

        last_exc: Optional[Exception] = None
        for model_attempt, current_model in enumerate(fallback_models):
            # Max 3 retries per model for transient errors (429/5xx)
            for retry_attempt in range(3):
                try:
                    full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

                    # Ensure model name is valid
                    if not current_model or current_model.strip() == "":
                        current_model = settings.gemini_model_name
                    if "-latest" in current_model:
                        current_model = current_model.replace("-latest", "")

                    timeout_seconds = max(settings.gemini_timeout_seconds, 30)
                    logger.debug(f"Gemini call: model={current_model} attempt={model_attempt+1}/{len(fallback_models)} retry={retry_attempt+1}/3 timeout={timeout_seconds}s")

                    if _use_new_sdk:
                        # ── New google-genai SDK (v1+) — reuse shared client ──
                        _client = self._gemini_client
                        config = genai_types.GenerateContentConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                        loop = asyncio.get_running_loop()
                        def _call_new(_c=_client, _m=current_model, _p=full_prompt, _cfg=config):
                            return _c.models.generate_content(
                                model=_m,
                                contents=_p,
                                config=_cfg,
                            )
                        raw = await asyncio.wait_for(
                            loop.run_in_executor(None, _call_new),
                            timeout=timeout_seconds,
                        )
                        text = raw.text if hasattr(raw, "text") else self._extract_text(raw)
                    else:
                        # ── Legacy google-generativeai SDK ──────────────────────
                        generation_config = genai.types.GenerationConfig(
                            temperature=temperature,
                            max_output_tokens=max_tokens,
                        )
                        safety_settings = {
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        }
                        model = genai.GenerativeModel(model_name=current_model)
                        loop = asyncio.get_running_loop()
                        def _call_gemini():
                            return model.generate_content(
                                full_prompt,
                                generation_config=generation_config,
                                safety_settings=safety_settings,
                            )
                        raw = await asyncio.wait_for(
                            loop.run_in_executor(None, _call_gemini),
                            timeout=timeout_seconds,
                        )
                        text = self._extract_text(raw)

                    text = self._extract_text(raw) if not _use_new_sdk else text
                    if not text or not text.strip():
                        logger.warning(f"Gemini returned empty text. model={current_model}")
                        last_exc = LLMException(f"Gemini returned empty text (model={current_model})")
                        break  # Try next fallback model
                    return text

                except asyncio.TimeoutError:
                    last_exc = LLMException(f"Gemini timed out after {timeout_seconds}s (model={current_model})")
                    logger.warning(f"Gemini timeout: model={current_model} retry={retry_attempt+1}/3")
                    # Timeout → try next model immediately (no sleep)
                    break

                except LLMException as llm_err:
                    last_exc = llm_err
                    error_str = str(llm_err).lower()
                    is_quota = "429" in error_str or "quota" in error_str or "exceeded" in error_str
                    is_server_err = "500" in error_str or "503" in error_str or "502" in error_str

                    if is_quota or is_server_err:
                        # Transient: sleep with exponential backoff then retry
                        wait = 2.0 * (2 ** retry_attempt)  # 2s, 4s, 8s
                        logger.warning(f"Gemini transient error ({('quota' if is_quota else 'server')}): model={current_model} retry={retry_attempt+1}/3 wait={wait:.0f}s")
                        await asyncio.sleep(wait)
                        continue  # retry same model
                    else:
                        # Permanent error (404, 403, API key) → try next model
                        logger.warning(f"Gemini permanent error: model={current_model} → trying fallback. err={str(llm_err)[:100]}")
                        break

                except Exception as e:
                    last_exc = e
                    error_str = str(e).lower()
                    is_transient = any(x in error_str for x in ["429", "quota", "500", "503", "502", "exceeded", "resource exhausted"])
                    if is_transient:
                        wait = 2.0 * (2 ** retry_attempt)
                        logger.warning(f"Gemini transient exception: model={current_model} retry={retry_attempt+1}/3 wait={wait:.0f}s err={str(e)[:100]}")
                        await asyncio.sleep(wait)
                        continue
                    else:
                        logger.error(f"Gemini API error: model={current_model} err={e}", exc_info=True)
                        break
            else:
                # All retries exhausted for this model → try next
                logger.warning(f"All retries exhausted for model={current_model}, trying next fallback")
                continue

        # All models and retries failed
        logger.error(f"All Gemini fallback models failed. last_err={last_exc}")
        raise LLMException(f"Gemini call failed after all fallbacks: {str(last_exc)[:200]}") from (last_exc if isinstance(last_exc, Exception) else None)

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
            raise LLMException(f"Gemini returned unexpected/empty response structure. finish_reason={finish_reason}")

        except LLMException:
            raise
        except (AttributeError, IndexError, KeyError) as e:
            logger.error(f"Error extracting text from response: {e}", exc_info=True)
            # Try a desperate fallback before raising
            try:
                if hasattr(response, 'text'):
                    text = response.text
                    if text and text.strip():
                        return text
            except Exception:
                pass
            raise LLMException(f"Failed to extract text from Gemini response: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error extracting text from response: {e}", exc_info=True)
            raise LLMException(f"Unexpected error extracting Gemini response: {e}") from e

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
            except Exception:
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
                if not settings.gemini_api_key:
                    raise LLMException("GEMINI_API_KEY not set in environment")

                # Reuse the shared client created by LLMService.__init__
                self.mcp_client = self._gemini_client
                self.mcp_model_name = settings.gemini_model_name
                self.timeout = max(settings.gemini_timeout_seconds, 30)  # At least 30s for tool calls

                # Convert MCP tools to Gemini function declarations
                from app.services.mcp_server import ALL_MCP_TOOLS
                self.tools = self._convert_mcp_to_gemini_tools(ALL_MCP_TOOLS)

                masked_key = f"{settings.gemini_api_key[:6]}...{settings.gemini_api_key[-4:]}" if len(settings.gemini_api_key) > 10 else "INVALID_KEY"
                logger.info(f"LLMServiceWithMCP initialized with Gemini + {len(ALL_MCP_TOOLS)} tools, model: {self.mcp_model_name}, key: {masked_key}")
            except LLMException:
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Gemini MCP support: {e}. Tool calling will not work.", exc_info=True)
                raise LLMException(f"Failed to initialize MCP support: {e}") from e
        
        except Exception as e:
            logger.error(f"Failed to initialize LLMServiceWithMCP: {e}")
            raise LLMException(f"LLM initialization failed: {e}") from e
    
    def _convert_mcp_to_gemini_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert MCP tool definitions to Gemini function declarations.
        Gemini requires: ARRAY params must have 'items'; OBJECT params must have non-empty 'properties';
        parameter descriptions must be non-empty for valid request.
        """
        from google.genai import types
        
        gemini_tools = []
        for tool in mcp_tools:
            props = tool["parameters"].get("properties", {})
            required = tool["parameters"].get("required", [])
            required = [r for r in required if r in props]
            properties = {}
            for param_name, param_def in props.items():
                schema = self._param_def_to_schema(param_def)
                if schema is not None:
                    properties[param_name] = schema
            if not properties:
                logger.warning(f"MCP tool '{tool['name']}' has no valid properties after schema conversion — skipping tool registration")
                continue
            func_decl = types.FunctionDeclaration(
                name=tool["name"],
                description=(tool.get("description") or "Tool.").strip() or "Tool.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=properties,
                    required=required
                )
            )
            gemini_tools.append(func_decl)
        
        return [types.Tool(function_declarations=gemini_tools)]
    
    def _param_def_to_schema(self, param_def: Dict[str, Any]) -> Optional[Any]:
        """Build a Gemini Schema for one parameter. Handles ARRAY (items required) and avoids invalid OBJECT."""
        from google.genai import types
        
        raw_type = (param_def.get("type") or "string").lower()
        desc = (param_def.get("description") or "Parameter.").strip() or "Parameter."
        if raw_type == "array":
            items_def = param_def.get("items") or {}
            item_type = (items_def.get("type") or "string").lower()
            items_schema = types.Schema(
                type=self._convert_type(item_type),
                description=items_def.get("description") or "Item"
            )
            return types.Schema(
                type=types.Type.ARRAY,
                description=desc,
                items=items_schema
            )
        if raw_type == "object":
            return types.Schema(type=types.Type.STRING, description=desc + " (JSON string)")
        return types.Schema(
            type=self._convert_type(raw_type),
            description=desc
        )
    
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
                        # Gemini expects function responses with role="tool"
                        conversation_history.append(
                            types.Content(
                                role="tool",
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
        
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, _call)


# =============================================================================
# Intent-Based LLM Service (Merged from intent_llm.py)
# =============================================================================

class IntentBasedLLM:
    """
    Intent-Based LLM Service
    Analyzes user input to determine intent and automatically calls appropriate tools
    """
    
    def __init__(self):
        """Initialize Intent-Based LLM with tool calling support"""
        try:
            self.llm = LLMServiceWithMCP()
            logger.info("IntentBasedLLM initialized with tool calling support")
        except Exception as e:
            logger.error(f"Failed to initialize IntentBasedLLM: {e}")
            raise LLMException(f"IntentBasedLLM initialization failed: {e}") from e
    
    async def analyze_intent_and_respond(
        self,
        user_input: str,
        system_prompt: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tool_calls: int = 5,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Analyze user intent and automatically call appropriate tools
        
        Args:
            user_input: User's message
            system_prompt: Optional system prompt
            conversation_history: Optional conversation history
            max_tool_calls: Maximum number of tool calls
            temperature: Generation temperature
            
        Returns:
            Dictionary with:
            - 'text': Final response text
            - 'intent': Detected user intent
            - 'tools_called': List of tools that were called
            - 'tool_results': Results from tool calls
        """
        # Import MCP tools dynamically
        try:
            from app.services.mcp_server import ALL_MCP_TOOLS
        except ImportError:
            ALL_MCP_TOOLS = []
        
        # Build enhanced system prompt for intent analysis and tool calling
        enhanced_system_prompt = f"""You are an intelligent Travel Agent AI that analyzes user intent and automatically uses tools to help users.

🎯 YOUR JOB:
1. Analyze user input to understand their intent (what they want to do)
2. Automatically call appropriate tools to fulfill their request
3. Provide helpful responses based on tool results

🧠 INTENT ANALYSIS:
Analyze the user's intent from their message:
- **Search Flights**: User wants to find flights (e.g., "หาตั๋วบิน", "fly to Tokyo", "flight Bangkok to Seoul")
- **Search Hotels**: User wants to find hotels (e.g., "หาที่พัก", "hotel in Phuket", "book a room")
- **Search Transfers**: User wants ground transport (e.g., "รถรับส่ง", "taxi", "transfer")
- **Get Location Info**: User wants location information (e.g., "where is", "distance to", "info about")
- **Plan Trip**: User wants to plan a full trip (e.g., "plan trip", "จัดทริป", "I want to go to")

🛠️ AVAILABLE TOOLS (MCP - Amadeus & Google Maps):
Use the available MCP tools to fulfill user requests automatically.

📋 USAGE RULES:
1. If user asks about flights → Call **search_flights** automatically
2. If user asks about hotels → Call **search_hotels** automatically
3. If user asks about transfers → Call **search_transfers** automatically
4. If user mentions landmark/address → Call **geocode_location** first
5. If user mentions city for flights → Call **find_nearest_airport** to get airport code
6. If user wants to plan a trip → Call multiple tools as needed
7. If user asks about location details → Call **get_place_details** automatically

💡 INTELLIGENCE:
- Extract travel details from natural language (dates, locations, guests)
- Infer missing information intelligently (default dates, origins, etc.)
- Combine multiple tool calls if needed
- Provide helpful explanations based on tool results

🌐 LANGUAGE:
- Respond in Thai if user writes in Thai
- Support both Thai and English naturally

{system_prompt or ""}

Remember: Automatically use tools when user asks for something. Don't just explain - DO IT!
"""
        
        # Build conversation context
        prompt = user_input
        if conversation_history:
            # Format history for context
            history_text = "\n".join([
                f"{'User' if msg.get('role') == 'user' else 'Assistant'}: {msg.get('content', '')}"
                for msg in conversation_history[-5:]  # Last 5 messages for context
            ])
            prompt = f"=== CONVERSATION HISTORY ===\n{history_text}\n\n=== CURRENT MESSAGE ===\n{user_input}"
        
        try:
            # Use generate_with_tools to automatically call tools
            result = await self.llm.generate_with_tools(
                prompt=prompt,
                system_prompt=enhanced_system_prompt,
                temperature=temperature,
                max_tool_calls=max_tool_calls,
                max_tokens=4000
            )
            
            # Extract intent from tool calls or analyze from response
            intent = self._extract_intent(user_input, result.get('tool_calls', []))
            
            return {
                'text': result.get('text', ''),
                'intent': intent,
                'tools_called': [tc.get('tool') for tc in result.get('tool_calls', [])],
                'tool_results': result.get('tool_calls', []),
                'success': True
            }
        
        except Exception as e:
            logger.error(f"Intent analysis failed: {e}", exc_info=True)
            return {
                'text': f'ขออภัยค่ะ เกิดข้อผิดพลาดในการวิเคราะห์: {str(e)[:100]}',
                'intent': 'unknown',
                'tools_called': [],
                'tool_results': [],
                'success': False,
                'error': str(e)
            }
    
    def _extract_intent(self, user_input: str, tool_calls: List[Dict[str, Any]]) -> str:
        """
        Extract user intent from input and tool calls
        
        Args:
            user_input: User's message
            tool_calls: List of tool calls that were made
            
        Returns:
            Detected intent string
        """
        user_lower = user_input.lower()
        
        # Check tool calls first (most reliable)
        if tool_calls:
            tool_names = [tc.get('tool', '') for tc in tool_calls]
            if 'search_flights' in tool_names:
                return 'search_flights'
            elif 'search_hotels' in tool_names:
                return 'search_hotels'
            elif 'search_transfers' in tool_names:
                return 'search_transfers'
            elif 'get_location_info' in tool_names:
                return 'get_location_info'
        
        # Fallback to keyword analysis
        if any(keyword in user_lower for keyword in ['flight', 'บิน', 'ตั๋ว', 'เที่ยวบิน', 'airline', 'fly']):
            return 'search_flights'
        elif any(keyword in user_lower for keyword in ['hotel', 'ที่พัก', 'โรงแรม', 'accommodation', 'stay']):
            return 'search_hotels'
        elif any(keyword in user_lower for keyword in ['transfer', 'รถ', 'taxi', 'shuttle', 'transport']):
            return 'search_transfers'
        elif any(keyword in user_lower for keyword in ['location', 'ที่ไหน', 'where', 'distance', 'info']):
            return 'get_location_info'
        elif any(keyword in user_lower for keyword in ['plan', 'trip', 'ทริป', 'จัด', 'book', 'จอง']):
            return 'plan_trip'
        else:
            return 'general_query'


# =============================================================================
# Production LLM (three brains: Controller, Responder, Intelligence)
# =============================================================================

class ModelType(str, Enum):
    """Gemini model types (Flash and Pro only)"""
    FLASH = "flash"      # Fast, cost-effective (gemini-2.5-flash)
    PRO = "pro"          # Balanced (gemini-2.5-pro)


class BrainType(str, Enum):
    """Three specialized brain types"""
    CONTROLLER = "controller"      # Decision-making brain (what to do next)
    RESPONDER = "responder"        # Communication brain (how to respond to user)
    INTELLIGENCE = "intelligence"  # Analysis brain (smart selection, reasoning)


_production_llm_service = None  # LangChainProductionLLM or None (ใช้ LCEL เท่านั้น)


def get_production_llm():
    """Get or create global Production LLM instance. ใช้ LangChain (LCEL) เท่านั้น"""
    global _production_llm_service
    if _production_llm_service is None:
        if getattr(settings, "enable_langchain_orchestration", True):
            try:
                from app.orchestration.langchain_llm import LangChainProductionLLM
                _production_llm_service = LangChainProductionLLM()
                logger.info("Using LangChain orchestration (LCEL) for Production LLM")
            except Exception as e:
                logger.warning(f"LangChain orchestration failed: {e}, production_llm will be None")
                _production_llm_service = None
        else:
            _production_llm_service = None
    return _production_llm_service
