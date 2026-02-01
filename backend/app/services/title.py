"""
เซอร์วิสสร้างหัวข้อแชท
สร้างหัวข้อแชทจากจุดเริ่มต้นการสนทนา
"""

from __future__ import annotations
from typing import Optional
import re

from app.services.llm import LLMService
from app.core.logging import get_logger
from app.core.exceptions import LLMException

logger = get_logger(__name__)


async def generate_chat_title(user_input: str, bot_response: str) -> str:
    """
    Generate a short, catchy title from conversation start
    
    Args:
        user_input: User's first message
        bot_response: Bot's first response
        
    Returns:
        Cleaned title string (max 5 words, Thai language)
    """
    try:
        # Initialize LLM service
        llm_service = LLMService()
        
        # Build prompt
        prompt = f"""Summarize this conversation start into a short, catchy title (max 5 words, Thai language).

Input: {user_input}
Response: {bot_response}

Output JUST the title, no explanation, no quotes, no markdown."""
        
        # Call LLM with lower temperature for consistency
        title_text = await llm_service.generate_content(
            prompt=prompt,
            system_prompt="You are a title generator. Output only the title, nothing else.",
            temperature=0.5,
            max_tokens=20  # Short title only
        )
        
        # Clean the title
        title = _clean_title(title_text)
        
        logger.info(f"Generated title: {title}")
        return title
    
    except LLMException as e:
        logger.error(f"LLM error generating title: {e}", exc_info=True)
        # Fallback: use first few words of user input
        fallback = _create_fallback_title(user_input)
        logger.info(f"Using fallback title: {fallback}")
        return fallback
    except Exception as e:
        logger.error(f"Error generating title: {e}", exc_info=True)
        # Fallback: use first few words of user input
        fallback = _create_fallback_title(user_input)
        logger.info(f"Using fallback title: {fallback}")
        return fallback


def _clean_title(title: str) -> str:
    """
    Clean and normalize title
    
    Args:
        title: Raw title from LLM
        
    Returns:
        Cleaned title string
    """
    if not title:
        return "การสนทนาใหม่"
    
    # Remove quotes, markdown, extra whitespace
    title = title.strip()
    title = re.sub(r'^["\']|["\']$', '', title)  # Remove surrounding quotes
    title = re.sub(r'^#+\s*', '', title)  # Remove markdown headers
    title = re.sub(r'\*\*|__', '', title)  # Remove markdown bold
    title = re.sub(r'\s+', ' ', title)  # Normalize whitespace
    
    # Limit to 5 words
    words = title.split()
    if len(words) > 5:
        title = ' '.join(words[:5])
    
    # Ensure minimum length
    if len(title) < 3:
        return "การสนทนาใหม่"
    
    return title


def _create_fallback_title(user_input: str) -> str:
    """
    Create fallback title from user input
    
    Args:
        user_input: User's message
        
    Returns:
        Fallback title
    """
    if not user_input:
        return "การสนทนาใหม่"
    
    # Take first 5 words
    words = user_input.split()
    if len(words) > 5:
        title = ' '.join(words[:5])
    else:
        title = user_input
    
    # Add ellipsis if truncated
    if len(words) > 5:
        title += "..."
    
    return title

