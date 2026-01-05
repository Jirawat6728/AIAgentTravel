"""
Agent Brain - Cognitive System for Gemini Agent
Provides: Memory, Reasoning, Planning, Caching, and Algorithm Logic
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Cache configuration
CACHE_TTL_SECONDS = 3600  # 1 hour default cache
REASONING_CACHE_TTL = 1800  # 30 minutes for reasoning results
PLANNING_CACHE_TTL = 3600  # 1 hour for planning results


class CacheEntry:
    """Single cache entry with metadata"""
    
    def __init__(self, value: Any, ttl: int = CACHE_TTL_SECONDS, metadata: Optional[Dict[str, Any]] = None):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.expires_at = self.created_at + ttl
        self.access_count = 0
        self.last_accessed = self.created_at
        self.metadata = metadata or {}
    
    def is_expired(self) -> bool:
        return time.time() > self.expires_at
    
    def access(self) -> Any:
        """Access the cached value and update statistics"""
        self.access_count += 1
        self.last_accessed = time.time()
        return self.value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "metadata": self.metadata,
        }


class AgentBrain:
    """
    Agent Brain - Central cognitive system
    
    Features:
    - API Call Caching (Gemini, Amadeus)
    - Reasoning Cache (decision results)
    - Planning Cache (plan outputs)
    - Memory Management
    - Algorithm Logic
    """
    
    def __init__(self, user_id: str, trip_id: str = "default"):
        self.user_id = user_id
        self.trip_id = trip_id
        self.session_key = f"{user_id}:{trip_id}"
        
        # Caches
        self._api_cache: Dict[str, CacheEntry] = {}  # Gemini API responses
        self._reasoning_cache: Dict[str, CacheEntry] = {}  # Reasoning results
        self._planning_cache: Dict[str, CacheEntry] = {}  # Planning results
        self._semantic_cache: Dict[str, CacheEntry] = {}  # Semantic similarity cache
        
        # Statistics
        self._stats = {
            "api_calls_saved": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_queries": 0,
        }
    
    @staticmethod
    def _generate_cache_key(prefix: str, data: Any) -> str:
        """Generate deterministic cache key from data"""
        if isinstance(data, dict):
            # Sort dict keys for consistent hashing
            data_str = json.dumps(data, sort_keys=True)
        elif isinstance(data, (list, tuple)):
            data_str = json.dumps(data, sort_keys=True)
        else:
            data_str = str(data)
        
        hash_obj = hashlib.md5(data_str.encode())
        return f"{prefix}:{hash_obj.hexdigest()}"
    
    def get_cached_api_response(self, prompt: str, model: str = None, **kwargs) -> Optional[Any]:
        """Get cached Gemini API response"""
        cache_key = self._generate_cache_key(
            f"api:{model or 'default'}",
            {"prompt": prompt, **kwargs}
        )
        
        self._stats["total_queries"] += 1
        
        entry = self._api_cache.get(cache_key)
        if entry and not entry.is_expired():
            self._stats["cache_hits"] += 1
            self._stats["api_calls_saved"] += 1
            logger.debug(f"Cache HIT for API call: {cache_key[:16]}...")
            return entry.access()
        
        self._stats["cache_misses"] += 1
        logger.debug(f"Cache MISS for API call: {cache_key[:16]}...")
        return None
    
    def cache_api_response(self, prompt: str, response: Any, ttl: int = CACHE_TTL_SECONDS, model: str = None, **kwargs):
        """Cache Gemini API response"""
        cache_key = self._generate_cache_key(
            f"api:{model or 'default'}",
            {"prompt": prompt, **kwargs}
        )
        
        self._api_cache[cache_key] = CacheEntry(response, ttl=ttl, metadata={
            "model": model,
            "prompt_preview": prompt[:100],
            **kwargs
        })
        
        # Cleanup expired entries periodically
        if len(self._api_cache) > 1000:
            self._cleanup_expired(self._api_cache)
    
    def get_cached_reasoning(self, query: str, context: Dict[str, Any]) -> Optional[Any]:
        """Get cached reasoning result"""
        cache_key = self._generate_cache_key(
            "reasoning",
            {"query": query, "context_hash": hash(str(sorted(context.items())))}
        )
        
        entry = self._reasoning_cache.get(cache_key)
        if entry and not entry.is_expired():
            return entry.access()
        
        return None
    
    def cache_reasoning(self, query: str, context: Dict[str, Any], result: Any):
        """Cache reasoning result"""
        cache_key = self._generate_cache_key(
            "reasoning",
            {"query": query, "context_hash": hash(str(sorted(context.items())))}
        )
        
        self._reasoning_cache[cache_key] = CacheEntry(
            result,
            ttl=REASONING_CACHE_TTL,
            metadata={"query_preview": query[:100]}
        )
    
    def get_cached_planning(self, user_message: str, context: Dict[str, Any]) -> Optional[Any]:
        """Get cached planning result"""
        cache_key = self._generate_cache_key(
            "planning",
            {"message": user_message, "context_hash": hash(str(sorted(context.items())))}
        )
        
        entry = self._planning_cache.get(cache_key)
        if entry and not entry.is_expired():
            return entry.access()
        
        return None
    
    def cache_planning(self, user_message: str, context: Dict[str, Any], result: Any):
        """Cache planning result"""
        cache_key = self._generate_cache_key(
            "planning",
            {"message": user_message, "context_hash": hash(str(sorted(context.items())))}
        )
        
        self._planning_cache[cache_key] = CacheEntry(
            result,
            ttl=PLANNING_CACHE_TTL,
            metadata={"message_preview": user_message[:100]}
        )
    
    def _cleanup_expired(self, cache: Dict[str, CacheEntry]):
        """Remove expired entries from cache"""
        expired_keys = [
            key for key, entry in cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            del cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    def cleanup_all_expired(self):
        """Cleanup all expired cache entries"""
        self._cleanup_expired(self._api_cache)
        self._cleanup_expired(self._reasoning_cache)
        self._cleanup_expired(self._planning_cache)
        self._cleanup_expired(self._semantic_cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = (
            self._stats["cache_hits"] / self._stats["total_queries"]
            if self._stats["total_queries"] > 0
            else 0.0
        )
        
        return {
            **self._stats,
            "hit_rate": hit_rate,
            "cache_sizes": {
                "api_cache": len(self._api_cache),
                "reasoning_cache": len(self._reasoning_cache),
                "planning_cache": len(self._planning_cache),
                "semantic_cache": len(self._semantic_cache),
            },
        }
    
    def clear_cache(self, cache_type: Optional[str] = None):
        """Clear cache (all or specific type)"""
        if cache_type == "api" or cache_type is None:
            self._api_cache.clear()
        if cache_type == "reasoning" or cache_type is None:
            self._reasoning_cache.clear()
        if cache_type == "planning" or cache_type is None:
            self._planning_cache.clear()
        if cache_type == "semantic" or cache_type is None:
            self._semantic_cache.clear()
        
        logger.info(f"Cleared cache: {cache_type or 'all'}")


class ReasoningEngine:
    """
    Reasoning Engine - Think before acting
    Analyzes context and determines best course of action
    """
    
    @staticmethod
    def should_skip_api_call(user_message: str, context: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Determine if we should skip API call based on reasoning
        
        Returns: (should_skip, reason)
        """
        # Check if message is too short or unclear
        if len(user_message.strip()) < 3:
            return True, "Message too short"
        
        # Check if we have recent similar context
        last_plan = context.get("current_plan")
        last_slots = context.get("last_travel_slots") or {}
        
        # If user is just asking questions (not requesting action)
        question_words = ["อะไร", "คือ", "คืออะไร", "ยังไง", "อย่างไร", "what", "what is", "how", "why"]
        if any(user_message.lower().startswith(q) for q in question_words):
            # Could use cached response if available
            return False, None  # Still need to process, but might use cache
        
        return False, None
    
    @staticmethod
    def analyze_intent(user_message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user intent without calling API"""
        intent_analysis = {
            "intent": "unknown",
            "confidence": 0.0,
            "requires_api": True,
            "reasoning": "",
        }
        
        message_lower = user_message.lower()
        
        # Simple rule-based intent detection (can be enhanced with ML)
        if any(word in message_lower for word in ["จอง", "book", "ยืนยัน", "confirm"]):
            intent_analysis["intent"] = "booking"
            intent_analysis["confidence"] = 0.8
        elif any(word in message_lower for word in ["แก้", "edit", "เปลี่ยน", "change", "เปลี่ยน"]):
            intent_analysis["intent"] = "edit"
            intent_analysis["confidence"] = 0.8
        elif any(word in message_lower for word in ["หา", "search", "ดู", "ดู", "show"]):
            intent_analysis["intent"] = "search"
            intent_analysis["confidence"] = 0.7
        elif any(word in message_lower for word in ["ลบ", "delete", "remove"]):
            intent_analysis["intent"] = "delete"
            intent_analysis["confidence"] = 0.9
        
        return intent_analysis
    
    @staticmethod
    def optimize_prompt(prompt: str, context: Dict[str, Any]) -> str:
        """Optimize prompt based on context to reduce token usage"""
        # Remove redundant context if already known
        # This is a simple implementation - can be enhanced
        
        # If we have recent similar context, we can shorten the prompt
        if context.get("last_agent_state"):
            # Add brief context hint instead of full context
            prompt = f"[Context: {context.get('last_agent_state', {}).get('intent', 'unknown')}]\n{prompt}"
        
        return prompt


# Global brain instances (per user session)
_brains: Dict[str, AgentBrain] = {}


def get_agent_brain(user_id: str, trip_id: str = "default") -> AgentBrain:
    """Get or create AgentBrain for user session"""
    session_key = f"{user_id}:{trip_id}"
    
    if session_key not in _brains:
        _brains[session_key] = AgentBrain(user_id, trip_id)
    
    # Cleanup expired cache periodically
    brain = _brains[session_key]
    if brain._stats["total_queries"] % 100 == 0:
        brain.cleanup_all_expired()
    
    return brain


def clear_agent_brain(user_id: str, trip_id: str = "default"):
    """Clear agent brain for session"""
    session_key = f"{user_id}:{trip_id}"
    if session_key in _brains:
        del _brains[session_key]


