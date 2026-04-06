"""
Redis client helper (optional).

ใช้เมื่อกำหนด REDIS_URL หรือ settings.redis_url แล้วเท่านั้น
- ถ้าเชื่อมต่อไม่ได้ จะ fallback เป็น None (ไม่ให้แครช)
- ใช้ร่วมกันทั้งแอปผ่าน singleton instance
"""

from __future__ import annotations

import os
from typing import Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

try:
    from redis.asyncio import Redis
except Exception:  # pragma: no cover - redis package อาจไม่พร้อมในบางสภาพแวดล้อม
    Redis = None  # type: ignore

_redis_client: Optional["Redis"] = None
_redis_available: bool = False
_init_attempted: bool = False


def _get_redis_url() -> str:
    """
    คืนค่า Redis URL จาก settings หรือ environment variable.
    """
    try:
        from app.core.config import settings

        url = getattr(settings, "redis_url", "") or os.getenv("REDIS_URL", "")
        return url.strip()
    except Exception:
        return os.getenv("REDIS_URL", "").strip()


async def get_redis() -> Optional["Redis"]:
    """
    คืน Redis client ถ้าพร้อมใช้งาน มิฉะนั้นคืน None
    - ไม่โยน exception ออกไปข้างนอก เพื่อลดผลกระทบต่อ flow หลัก
    """
    global _redis_client, _redis_available, _init_attempted

    if Redis is None:
        return None

    if _redis_client is not None:
        return _redis_client if _redis_available else None

    if _init_attempted:
        # เคยพยายามแล้วและล้มเหลว
        return None

    _init_attempted = True
    url = _get_redis_url()
    if not url:
        logger.info("Redis client disabled: no REDIS_URL / settings.redis_url configured")
        _redis_available = False
        return None

    try:
        client: "Redis" = Redis.from_url(url, encoding="utf-8", decode_responses=True)
        # ping ทดสอบการเชื่อมต่อ
        await client.ping()
        _redis_client = client
        _redis_available = True
        logger.info(f"Redis client initialized (url={url})")
        return _redis_client
    except Exception as e:
        logger.warning(f"Redis client initialization failed, fallback to in-memory only: {e}")
        _redis_client = None
        _redis_available = False
        return None


def is_redis_available() -> bool:
    """
    คืน True ถ้า Redis client ถูก initial แล้วและพร้อมใช้งาน.
    (ไม่ trigger การเชื่อมต่อใหม่)
    """
    return _redis_available and _redis_client is not None


async def close_redis() -> None:
    """
    ปิดการเชื่อมต่อ Redis ถ้ามี
    """
    global _redis_client, _redis_available, _init_attempted
    if _redis_client is not None:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
    _redis_client = None
    _redis_available = False
    _init_attempted = False

