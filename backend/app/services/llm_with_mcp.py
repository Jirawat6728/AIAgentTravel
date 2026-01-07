"""
LLM Service with Model Context Protocol (MCP) Integration
Enables Gemini to call Amadeus and Google Maps tools directly
"""

from __future__ import annotations
from typing import Any, Dict, Optional, List
import asyncio
import json
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

from app.core.config import settings
from app.core.exceptions import LLMException
from app.core.logging import get_logger
from app.services.mcp_server import ALL_MCP_TOOLS, mcp_executor

logger = get_logger(__name__)


class LLMServiceWithMCP:
    """
    Enhanced LLM Service with MCP Tool Support
    Allows Gemini to call external APIs via function calling
    """
    
    def __init__(self):
        """Initialize LLM Service with MCP tools"""
        try:
            from google import genai
            from google.genai import types
            
            if not settings.gemini_api_key:
                raise LLMException("GEMINI_API_KEY not set in environment")
            
            self.client = genai.Client(api_key=settings.gemini_api_key)
            self.model_name = settings.gemini_model_name
            self.timeout = settings.gemini_timeout_seconds
            
            # Convert MCP tools to Gemini function declarations
            self.tools = self._convert_mcp_to_gemini_tools(ALL_MCP_TOOLS)
            
            # Mask API key for logging
            masked_key = f"{settings.gemini_api_key[:6]}...{settings.gemini_api_key[-4:]}" if len(settings.gemini_api_key) > 10 else "INVALID_KEY"
            logger.info(f"LLMServiceWithMCP initialized with {len(ALL_MCP_TOOLS)} tools, model: {self.model_name}, key: {masked_key}")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLMServiceWithMCP: {e}")
            raise LLMException(f"LLM initialization failed: {e}") from e
    
    def _convert_mcp_to_gemini_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Any]:
        """Convert MCP tool definitions to Gemini function declarations"""
        from google.genai import types
        
        gemini_tools = []
        for tool in mcp_tools:
            # Convert MCP schema to Gemini FunctionDeclaration
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
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        conversation_history = [full_prompt]
        tool_call_history = []
        
        try:
            for iteration in range(max_tool_calls):
                logger.info(f"MCP iteration {iteration + 1}/{max_tool_calls}")
                
                # Call LLM with tools
                response = await asyncio.wait_for(
                    self._call_llm_with_tools(conversation_history, temperature, max_tokens),
                    timeout=self.timeout
                )
                
                # Check if LLM wants to call a function
                if not response.candidates:
                    logger.warning("No candidates in response")
                    break
                
                candidate = response.candidates[0]
                
                # Check for function calls
                if candidate.content and candidate.content.parts:
                    has_function_call = False
                    text_response = ""
                    
                    for part in candidate.content.parts:
                        # Check if this part is a function call
                        if hasattr(part, 'function_call') and part.function_call:
                            has_function_call = True
                            func_call = part.function_call
                            
                            logger.info(f"LLM requested tool: {func_call.name}")
                            
                            # Execute the tool
                            tool_result = await mcp_executor.execute_tool(
                                tool_name=func_call.name,
                                parameters=dict(func_call.args)
                            )
                            
                            tool_call_history.append({
                                "tool": func_call.name,
                                "parameters": dict(func_call.args),
                                "result": tool_result
                            })
                            
                            # Add function result to conversation
                            conversation_history.append({
                                "role": "function",
                                "name": func_call.name,
                                "content": json.dumps(tool_result, ensure_ascii=False)
                            })
                        
                        # Check if this part is text
                        elif hasattr(part, 'text') and part.text:
                            text_response += part.text
                    
                    # If no function call, we have the final response
                    if not has_function_call:
                        return {
                            "text": text_response,
                            "tool_calls": tool_call_history
                        }
                else:
                    # No content, break
                    break
            
            # Max iterations reached, return what we have
            logger.warning(f"Max tool call iterations ({max_tool_calls}) reached")
            return {
                "text": "ขออภัยค่ะ ระบบใช้เวลาในการค้นหานานเกินไป กรุณาลองใหม่อีกครั้ง",
                "tool_calls": tool_call_history
            }
        
        except asyncio.TimeoutError:
            logger.error("LLM call with tools timed out")
            raise LLMException("LLM call timed out")
        except Exception as e:
            logger.error(f"LLM call with tools failed: {e}", exc_info=True)
            raise LLMException(f"LLM call failed: {e}") from e
    
    async def _call_llm_with_tools(
        self,
        messages: List[Any],
        temperature: float,
        max_tokens: int
    ) -> Any:
        """Call LLM with tools in thread pool"""
        def _call():
            from google.genai import types
            
            # Disable safety filters
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
                tools=self.tools  # Enable function calling
            )
            
            # Convert messages to proper format
            if isinstance(messages, list) and len(messages) > 0:
                if isinstance(messages[0], str):
                    # Simple string prompt
                    prompt = messages[0]
                else:
                    # Conversation history (not fully supported yet in this simple version)
                    prompt = str(messages[-1])
            else:
                prompt = str(messages)
            
            return self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _call)
    
    async def generate_content(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        response_format: Optional[str] = None
    ) -> str:
        """
        Generate content without tools (for backward compatibility)
        """
        from app.services.llm import LLMService
        
        # Fallback to regular LLM service
        regular_llm = LLMService()
        return await regular_llm.generate_content(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format
        )

