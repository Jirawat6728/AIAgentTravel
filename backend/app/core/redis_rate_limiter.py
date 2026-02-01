"""
ตัวจำกัดอัตรา (Rate Limiter) แบบ Redis
จำกัดอัตราการเรียกแบบกระจายด้วย Redis สำหรับการ deploy หลาย instance
"""

import time
from typing import Tuple, Optional
from app.storage.connection_manager import RedisConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm
    Works across multiple server instances (distributed rate limiting)
    Falls back to in-memory rate limiting if Redis is unavailable
    """
    
    def __init__(
        self, 
        max_requests: int = 100, 
        window_seconds: int = 60,
        fallback_to_memory: bool = True
    ):
        """
        Args:
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            fallback_to_memory: Fall back to in-memory limiter if Redis unavailable
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.fallback_to_memory = fallback_to_memory
        self.key_prefix = "ratelimit:"
        
        # Fallback in-memory rate limiter
        if fallback_to_memory:
            from collections import defaultdict
            self._memory_requests: dict = defaultdict(list)
    
    def _make_key(self, identifier: str) -> str:
        """Create Redis key for rate limit"""
        return f"{self.key_prefix}{identifier}"
    
    async def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        Check if request is allowed using Redis sliding window
        
        Args:
            identifier: Unique identifier (e.g., IP address, user_id)
            
        Returns:
            (is_allowed, remaining_requests)
        """
        try:
            redis_client = await RedisConnectionManager.get_instance().get_redis()
            
            if redis_client is None:
                # Redis unavailable - use fallback
                if self.fallback_to_memory:
                    return self._is_allowed_memory(identifier)
                else:
                    # If no fallback, allow request (fail open)
                    logger.debug(f"Redis unavailable, allowing request for {identifier}")
                    return True, self.max_requests
            
            # Use Redis for distributed rate limiting
            key = self._make_key(identifier)
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Use Redis sorted set for sliding window
            # Score = timestamp, Member = request_id (we use timestamp as member)
            pipe = redis_client.pipeline()
            
            # Remove old entries outside window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current requests in window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration on the key
            pipe.expire(key, self.window_seconds + 1)
            
            # Execute pipeline
            results = await pipe.execute()
            current_count = results[1]  # Count after cleanup
            
            # Check if limit exceeded
            if current_count >= self.max_requests:
                logger.warning(
                    f"Rate limit exceeded for {identifier}: "
                    f"{current_count}/{self.max_requests}"
                )
                return False, 0
            
            remaining = self.max_requests - current_count
            return True, remaining
            
        except Exception as e:
            logger.debug(f"Redis rate limiter error for {identifier}: {e}")
            
            # Fallback to memory if enabled
            if self.fallback_to_memory:
                return self._is_allowed_memory(identifier)
            else:
                # Fail open - allow request
                logger.warning(f"Rate limiter error, allowing request: {e}")
                return True, self.max_requests
    
    def _is_allowed_memory(self, identifier: str) -> Tuple[bool, int]:
        """
        Fallback in-memory rate limiting
        (Same logic as original RateLimiter class)
        """
        current_time = time.time()
        
        # Clean old requests outside window
        if identifier in self._memory_requests:
            self._memory_requests[identifier] = [
                req_time for req_time in self._memory_requests[identifier]
                if current_time - req_time < self.window_seconds
            ]
        
        # Check if limit exceeded
        request_count = len(self._memory_requests[identifier])
        
        if request_count >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded (memory) for {identifier}: "
                f"{request_count}/{self.max_requests}"
            )
            return False, 0
        
        # Add current request
        self._memory_requests[identifier].append(current_time)
        
        remaining = self.max_requests - len(self._memory_requests[identifier])
        return True, remaining
    
    async def reset(self, identifier: Optional[str] = None) -> bool:
        """
        Reset rate limit for identifier or all
        
        Args:
            identifier: Identifier to reset (None = reset all)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await RedisConnectionManager.get_instance().get_redis()
            
            if redis_client is None:
                # Reset memory fallback
                if self.fallback_to_memory:
                    if identifier:
                        self._memory_requests.pop(identifier, None)
                    else:
                        self._memory_requests.clear()
                return True
            
            if identifier:
                key = self._make_key(identifier)
                await redis_client.delete(key)
            else:
                # Delete all rate limit keys (use pattern)
                pattern = f"{self.key_prefix}*"
                async for key in redis_client.scan_iter(match=pattern):
                    await redis_client.delete(key)
            
            # Also reset memory fallback
            if self.fallback_to_memory:
                if identifier:
                    self._memory_requests.pop(identifier, None)
                else:
                    self._memory_requests.clear()
            
            return True
            
        except Exception as e:
            logger.warning(f"Failed to reset rate limit: {e}")
            return False
    
    async def get_remaining(self, identifier: str) -> int:
        """
        Get remaining requests for identifier
        
        Args:
            identifier: Unique identifier
            
        Returns:
            Number of remaining requests
        """
        try:
            redis_client = await RedisConnectionManager.get_instance().get_redis()
            
            if redis_client is None:
                # Use memory fallback
                if self.fallback_to_memory:
                    current_time = time.time()
                    if identifier in self._memory_requests:
                        self._memory_requests[identifier] = [
                            req_time for req_time in self._memory_requests[identifier]
                            if current_time - req_time < self.window_seconds
                        ]
                    count = len(self._memory_requests.get(identifier, []))
                    return max(0, self.max_requests - count)
                return self.max_requests
            
            key = self._make_key(identifier)
            current_time = time.time()
            window_start = current_time - self.window_seconds
            
            # Count requests in window
            count = await redis_client.zcount(key, window_start, current_time)
            return max(0, self.max_requests - count)
            
        except Exception as e:
            logger.debug(f"Failed to get remaining requests: {e}")
            return self.max_requests  # Fail open
