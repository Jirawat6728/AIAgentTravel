"""
เซอร์วิสแคช Redis
แคชประสิทธิภาพสูงสำหรับคำตอบ API ผลการค้นหา และข้อมูลอื่น
"""

import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, Callable
from app.storage.connection_manager import RedisConnectionManager
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisCache:
    """
    Redis-based caching service for API responses and other data
    """
    
    def __init__(self, default_ttl: int = None):
        """
        Initialize Redis cache
        
        Args:
            default_ttl: Default TTL in seconds (defaults to settings.redis_ttl)
        """
        self.connection_manager = RedisConnectionManager.get_instance()
        self.default_ttl = default_ttl or settings.redis_ttl
        self.key_prefix = "cache:"
    
    def _make_key(self, key: str) -> str:
        """Create cache key with prefix"""
        return f"{self.key_prefix}{key}"
    
    def _hash_key(self, data: Any) -> str:
        """Create hash key from data"""
        if isinstance(data, str):
            key_str = data
        else:
            key_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return None  # Redis unavailable - cache miss
            
            cache_key = self._make_key(key)
            data = await redis_client.get(cache_key)
            
            if data is None:
                return None
            
            # Deserialize JSON
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                logger.warning(f"Failed to deserialize cache value for key: {key}")
                return None
                
        except Exception as e:
            logger.debug(f"Redis cache get failed for {key}: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: TTL in seconds (defaults to default_ttl)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return False  # Redis unavailable - skip cache
            
            cache_key = self._make_key(key)
            cache_ttl = ttl if ttl is not None else self.default_ttl
            
            # Serialize to JSON
            try:
                data = json.dumps(value, default=str)
            except (TypeError, ValueError) as e:
                logger.warning(f"Failed to serialize cache value for key {key}: {e}")
                return False
            
            await redis_client.set(cache_key, data, ex=cache_ttl)
            return True
            
        except Exception as e:
            logger.debug(f"Redis cache set failed for {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache
        
        Args:
            key: Cache key
            
        Returns:
            True if successful, False otherwise
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return False  # Redis unavailable
            
            cache_key = self._make_key(key)
            await redis_client.delete(cache_key)
            return True
            
        except Exception as e:
            logger.debug(f"Redis cache delete failed for {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in cache
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return False  # Redis unavailable
            
            cache_key = self._make_key(key)
            result = await redis_client.exists(cache_key)
            return result > 0
            
        except Exception as e:
            logger.debug(f"Redis cache exists check failed for {key}: {e}")
            return False
    
    async def clear_pattern(self, pattern: str) -> int:
        """
        Clear all keys matching pattern
        
        Args:
            pattern: Redis key pattern (e.g., "cache:search:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return 0  # Redis unavailable
            
            # Use SCAN to find matching keys (safer than KEYS for production)
            deleted_count = 0
            async for key in redis_client.scan_iter(match=pattern):
                await redis_client.delete(key)
                deleted_count += 1
            
            return deleted_count
            
        except Exception as e:
            logger.warning(f"Redis cache clear_pattern failed for {pattern}: {e}")
            return 0
    
    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl: Optional[int] = None
    ) -> Any:
        """
        Get value from cache, or fetch and cache if not found
        
        Args:
            key: Cache key
            fetch_func: Async function to fetch value if not in cache
            ttl: TTL in seconds (defaults to default_ttl)
            
        Returns:
            Cached or fetched value
        """
        # Try to get from cache
        cached = await self.get(key)
        if cached is not None:
            return cached
        
        # Fetch from source
        if asyncio.iscoroutinefunction(fetch_func):
            value = await fetch_func()
        else:
            value = fetch_func()
        
        # Cache the value
        await self.set(key, value, ttl)
        
        return value


# Global cache instance
cache = RedisCache()
