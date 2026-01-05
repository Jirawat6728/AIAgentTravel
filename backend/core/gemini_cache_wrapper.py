"""
Gemini Cache Wrapper - Wraps Gemini API calls with caching
Integrates with AgentBrain for intelligent caching
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, List
import logging

from core.config import get_gemini_client, GEMINI_MODEL_NAME
from utils.json_utils import get_text_from_parts

logger = logging.getLogger(__name__)


async def generate_content_with_cache(
    prompt: str,
    user_id: str,
    trip_id: str = "default",
    model: str = None,
    system_prompt: Optional[str] = None,
    config: Optional[Any] = None,
    cache_ttl: int = 3600,  # 1 hour default
    contents: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Optional[str]:
    """
    Generate content using Gemini API with caching via AgentBrain
    
    Args:
        prompt: User prompt (used if contents not provided)
        user_id: User ID for cache key
        trip_id: Trip ID for cache key
        model: Model name (defaults to GEMINI_MODEL_NAME)
        system_prompt: Optional system prompt
        config: Optional GenerateContentConfig
        cache_ttl: Cache TTL in seconds
        contents: Optional contents list (if provided, prompt is ignored)
        **kwargs: Additional parameters for cache key
    
    Returns:
        Generated text or None if failed
    """
    from core.agent_brain import get_agent_brain, ReasoningEngine
    
    brain = get_agent_brain(user_id, trip_id)
    
    # Build full prompt for cache key
    if contents:
        # Use contents for cache key
        full_prompt = str(contents)
    else:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    
    # Check cache first
    cached_response = brain.get_cached_api_response(
        prompt=full_prompt,
        model=model or GEMINI_MODEL_NAME,
        **kwargs
    )
    
    if cached_response is not None:
        logger.debug(f"Using cached Gemini response for user {user_id}")
        return cached_response
    
    # Check if we should skip API call (reasoning)
    user_msg = prompt if prompt else (contents[0].get("parts", [{}])[0].get("text", "") if contents else "")
    should_skip, reason = ReasoningEngine.should_skip_api_call(user_msg, {})
    if should_skip:
        logger.debug(f"Skipping Gemini API call: {reason}")
        return None
    
    try:
        # Call Gemini API
        client = get_gemini_client()
        if not client:
            logger.error("Gemini client not available")
            return None
        
        model_name = model or GEMINI_MODEL_NAME
        
        # Build contents
        if contents:
            api_contents = contents
        else:
            api_contents = []
            if system_prompt:
                api_contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            api_contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        # Use asyncio.to_thread for synchronous Gemini API
        if config:
            resp = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=api_contents,
                    config=config,
                )
            )
        else:
            resp = await asyncio.to_thread(
                lambda: client.models.generate_content(
                    model=model_name,
                    contents=api_contents,
                )
            )
        
        response_text = get_text_from_parts(resp)
        
        # Cache the response
        brain.cache_api_response(
            prompt=full_prompt,
            response=response_text,
            ttl=cache_ttl,
            model=model_name,
            **kwargs
        )
        
        return response_text
    except Exception as e:
        logger.error(f"Gemini API call failed: {e}", exc_info=True)
        return None


def generate_content_sync_with_cache(
    prompt: str,
    user_id: str,
    trip_id: str = "default",
    model: str = None,
    system_prompt: Optional[str] = None,
    config: Optional[Any] = None,
    cache_ttl: int = 3600,
    contents: Optional[List[Dict[str, Any]]] = None,
    **kwargs
) -> Optional[str]:
    """
    Synchronous version of generate_content_with_cache
    Use this for non-async contexts
    """
    from core.agent_brain import get_agent_brain, ReasoningEngine
    
    brain = get_agent_brain(user_id, trip_id)
    
    # Build full prompt for cache key
    if contents:
        full_prompt = str(contents)
    else:
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    
    # Check cache first
    cached_response = brain.get_cached_api_response(
        prompt=full_prompt,
        model=model or GEMINI_MODEL_NAME,
        **kwargs
    )
    
    if cached_response is not None:
        logger.debug(f"Using cached Gemini response (sync) for user {user_id}")
        return cached_response
    
    # Check reasoning
    user_msg = prompt if prompt else (contents[0].get("parts", [{}])[0].get("text", "") if contents else "")
    should_skip, reason = ReasoningEngine.should_skip_api_call(user_msg, {})
    if should_skip:
        logger.debug(f"Skipping Gemini API call (sync): {reason}")
        return None
    
    try:
        # Call Gemini API (synchronous)
        client = get_gemini_client()
        if not client:
            logger.error("Gemini client not available")
            return None
        
        model_name = model or GEMINI_MODEL_NAME
        
        # Build contents
        if contents:
            api_contents = contents
        else:
            api_contents = []
            if system_prompt:
                api_contents.append({"role": "user", "parts": [{"text": system_prompt}]})
            api_contents.append({"role": "user", "parts": [{"text": prompt}]})
        
        if config:
            resp = client.models.generate_content(
                model=model_name,
                contents=api_contents,
                config=config,
            )
        else:
            resp = client.models.generate_content(
                model=model_name,
                contents=api_contents,
            )
        
        response_text = get_text_from_parts(resp)
        
        # Cache the response
        brain.cache_api_response(
            prompt=full_prompt,
            response=response_text,
            ttl=cache_ttl,
            model=model_name,
            **kwargs
        )
        
        return response_text
    except Exception as e:
        logger.error(f"Gemini API call failed (sync): {e}", exc_info=True)
        return None

