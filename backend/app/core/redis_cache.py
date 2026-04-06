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
from app.core.redis_client import get_redis, is_redis_available
from app.core.config import settings

logger = get_logger(__name__)

DEFAULT_TTL = 3600  # 1 hour

# In-memory store: key -> (value, expires_at)
_cache_store: Dict[str, tuple] = {}


class RedisCache:
    """
    Caching service:
    - ใช้ Redis อัตโนมัติเมื่อมี REDIS_URL และ Redis พร้อมใช้งาน
    - Fallback เป็น in-memory เสมอถ้า Redis ใช้ไม่ได้หรือยังไม่พร้อม
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

        # Redis path (ใช้เมื่อมี REDIS_URL และ client พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    raw = await redis.get(cache_key)
                    if raw is None:
                        return None
                    return json.loads(raw)
            except Exception as e:
                logger.debug(f"Redis cache get failed for {cache_key}: {e}")

        # In-memory fallback
        entry = _cache_store.get(cache_key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at and datetime.utcnow() > expires_at:
            _cache_store.pop(cache_key, None)
            return None
        return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        cache_key = self._make_key(key)
        cache_ttl = ttl if ttl is not None else self.default_ttl

        ok = False

        # Redis path (ใช้เมื่อมี REDIS_URL และ client พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    payload = json.dumps(value, default=str, ensure_ascii=False)
                    if cache_ttl:
                        await redis.set(cache_key, payload, ex=cache_ttl)
                    else:
                        await redis.set(cache_key, payload)
                    ok = True
            except Exception as e:
                logger.debug(f"Redis cache set failed for {cache_key}: {e}")

        # In-memory fallback (เสมอ)
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=cache_ttl) if cache_ttl else None
            _cache_store[cache_key] = (value, expires_at)
            ok = True or ok
        except Exception as e:
            logger.debug(f"Memory cache set failed for {cache_key}: {e}")

        return ok

    async def delete(self, key: str) -> bool:
        cache_key = self._make_key(key)

        # Redis path (ใช้เมื่อมี REDIS_URL และ client พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    await redis.delete(cache_key)
            except Exception as e:
                logger.debug(f"Redis cache delete failed for {cache_key}: {e}")

        _cache_store.pop(cache_key, None)
        return True

    async def exists(self, key: str) -> bool:
        cache_key = self._make_key(key)

        # Redis path (ใช้เมื่อมี REDIS_URL และ client พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    exists = await redis.exists(cache_key)
                    if exists:
                        return True
            except Exception as e:
                logger.debug(f"Redis cache exists failed for {cache_key}: {e}")

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
        deleted = 0

        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    # ใช้ scan เพื่อเลี่ยง block server
                    cursor = "0"
                    pattern_key = f"{self.key_prefix}{prefix}*"
                    while True:
                        cursor, keys = await redis.scan(cursor=cursor, match=pattern_key, count=100)
                        if keys:
                            await redis.delete(*keys)
                            deleted += len(keys)
                        if cursor == "0":
                            break
            except Exception as e:
                logger.debug(f"Redis clear_pattern failed for {pattern}: {e}")

        keys_to_delete = [k for k in _cache_store if prefix in k]
        for k in keys_to_delete:
            _cache_store.pop(k, None)
        deleted += len(keys_to_delete)
        return deleted

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
