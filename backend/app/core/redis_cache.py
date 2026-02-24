"""
In-memory cache (Redis ถูกลบออกแล้ว)
แคชประสิทธิภาพสำหรับคำตอบ API ผลการค้นหา และข้อมูลอื่น
"""

import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, Callable
from datetime import datetime, timedelta
from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TTL = 3600  # 1 hour

# In-memory store: key -> (value, expires_at)
_cache_store: Dict[str, tuple] = {}


class RedisCache:
    """
    In-memory caching service (Redis removed)
    API-compatible replacement — same method signatures.
    """

    def __init__(self, default_ttl: int = DEFAULT_TTL):
        self.default_ttl = default_ttl
        self.key_prefix = "cache:"

    def _make_key(self, key: str) -> str:
        return f"{self.key_prefix}{key}"

    def _hash_key(self, data: Any) -> str:
        if isinstance(data, str):
            key_str = data
        else:
            key_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        cache_key = self._make_key(key)
        entry = _cache_store.get(cache_key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and datetime.utcnow() > expires_at:
            _cache_store.pop(cache_key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            cache_key = self._make_key(key)
            cache_ttl = ttl if ttl is not None else self.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=cache_ttl) if cache_ttl else None
            _cache_store[cache_key] = (value, expires_at)
            return True
        except Exception as e:
            logger.debug(f"Memory cache set failed for {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        cache_key = self._make_key(key)
        _cache_store.pop(cache_key, None)
        return True

    async def exists(self, key: str) -> bool:
        cache_key = self._make_key(key)
        entry = _cache_store.get(cache_key)
        if entry is None:
            return False
        _, expires_at = entry
        if expires_at and datetime.utcnow() > expires_at:
            _cache_store.pop(cache_key, None)
            return False
        return True

    async def clear_pattern(self, pattern: str) -> int:
        # Simple prefix/suffix matching (pattern uses * as wildcard)
        prefix = pattern.replace("*", "")
        keys_to_delete = [k for k in _cache_store if prefix in k]
        for k in keys_to_delete:
            _cache_store.pop(k, None)
        return len(keys_to_delete)

    async def get_or_set(self, key: str, fetch_func: Callable, ttl: Optional[int] = None) -> Any:
        cached = await self.get(key)
        if cached is not None:
            return cached
        if asyncio.iscoroutinefunction(fetch_func):
            value = await fetch_func()
        else:
            value = fetch_func()
        await self.set(key, value, ttl)
        return value


# Global cache instance
cache = RedisCache()
