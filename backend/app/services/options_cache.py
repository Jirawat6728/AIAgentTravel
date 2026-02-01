"""
เซอร์วิสแคชตัวเลือก (Redis)
เก็บตัวเลือกทั้งหมด (เที่ยวบิน การเดินทาง ที่พัก) ใน Redis สำหรับ AI และ TripSummary
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
from app.core.logging import get_logger
from app.core.config import settings
from app.storage.connection_manager import RedisConnectionManager

logger = get_logger(__name__)

# Redis key prefixes
KEY_PREFIX_ENTRY = "options_cache:entry:"
KEY_PREFIX_SESSION = "options_cache:session:"
KEY_AMADEUS_RAW_PREFIX = "amadeus_raw:session:"
KEY_AMADEUS_RAW_INDEX = "amadeus_raw:index:"
DEFAULT_TTL_HOURS = 24
DEFAULT_TTL_RAW_HOURS = 24


def _serialize_dt(dt: datetime) -> str:
    """Serialize datetime to ISO string for JSON storage."""
    return dt.isoformat() if dt else None


def _deserialize_dt(s: Optional[str]) -> Optional[datetime]:
    """Deserialize ISO string to datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class OptionsCacheService:
    """
    Cache service เก็บตัวเลือกใน Redis:
    - ไฟท์บิน (ขาไป, ขากลับ)
    - พาหนะทุกชนิด (ขาไป, ขากลับ)
    - ที่พักทุกชนิด
    """

    def __init__(self):
        self._redis_mgr = RedisConnectionManager.get_instance()
        logger.info("OptionsCacheService initialized (Redis backend)")

    async def _get_redis(self):
        """Get Redis client (async). Returns None if Redis unavailable."""
        return await self._redis_mgr.get_redis()

    def _generate_cache_key(
        self,
        session_id: str,
        slot_name: str,
        requirements: Dict[str, Any],
        segment_index: int = 0
    ) -> str:
        """Generate unique cache key from requirements."""
        normalized = {
            "origin": requirements.get("origin", ""),
            "destination": requirements.get("destination", ""),
            "departure_date": requirements.get("departure_date") or requirements.get("date", ""),
            "check_in": requirements.get("check_in", ""),
            "check_out": requirements.get("check_out", ""),
            "location": requirements.get("location", ""),
            "guests": requirements.get("guests") or requirements.get("adults", 1),
            "adults": requirements.get("adults", 1),
            "children": requirements.get("children", 0),
        }
        key_data = f"{session_id}:{slot_name}:{segment_index}:{json.dumps(normalized, sort_keys=True)}"
        key_hash = hashlib.md5(key_data.encode()).hexdigest()
        return f"{slot_name}:{segment_index}:{key_hash}"

    def _entry_key(self, cache_key: str) -> str:
        return f"{KEY_PREFIX_ENTRY}{cache_key}"

    def _session_key(self, session_id: str) -> str:
        return f"{KEY_PREFIX_SESSION}{session_id}"

    async def save_options(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
        options: List[Dict[str, Any]],
        ttl_hours: int = DEFAULT_TTL_HOURS
    ) -> bool:
        """Save options to Redis cache."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.warning("Redis unavailable, cannot save options")
                return False

            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            now = datetime.utcnow()
            expires_at = now + timedelta(hours=ttl_hours)
            ttl_seconds = ttl_hours * 3600

            cache_entry = {
                "cache_key": cache_key,
                "session_id": session_id,
                "slot_name": slot_name,
                "segment_index": segment_index,
                "requirements": requirements,
                "options": options,
                "options_count": len(options),
                "created_at": _serialize_dt(now),
                "expires_at": _serialize_dt(expires_at),
                "last_accessed": _serialize_dt(now),
            }

            entry_key = self._entry_key(cache_key)
            session_key = self._session_key(session_id)

            pipe = redis_client.pipeline()
            pipe.set(entry_key, json.dumps(cache_entry, default=str), ex=ttl_seconds)
            pipe.sadd(session_key, cache_key)
            pipe.execute()

            logger.info(f"Cached {len(options)} options for {slot_name}[{segment_index}] in session {session_id} (Redis)")
            return True

        except Exception as e:
            logger.error(f"Failed to save options to Redis: {e}", exc_info=True)
            return False

    async def get_options(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Get options from Redis cache."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return None

            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            entry_key = self._entry_key(cache_key)

            raw = await redis_client.get(entry_key)
            if not raw:
                logger.debug(f"Cache miss for {cache_key}")
                return None

            cache_entry = json.loads(raw)
            expires_at = _deserialize_dt(cache_entry.get("expires_at"))
            if expires_at and expires_at < datetime.utcnow():
                logger.debug(f"Cache expired for {cache_key}")
                await redis_client.delete(entry_key)
                session_key = self._session_key(session_id)
                await redis_client.srem(session_key, cache_key)
                return None

            # Refresh last_accessed and optionally extend TTL
            cache_entry["last_accessed"] = _serialize_dt(datetime.utcnow())
            ttl = await redis_client.ttl(entry_key)
            if ttl > 0:
                await redis_client.set(entry_key, json.dumps(cache_entry, default=str), ex=ttl)

            options = cache_entry.get("options", [])
            logger.info(f"Cache hit: Retrieved {len(options)} options for {slot_name}[{segment_index}] (Redis)")
            return options

        except Exception as e:
            logger.error(f"Failed to get options from Redis: {e}", exc_info=True)
            return None

    async def get_all_session_options(self, session_id: str) -> Dict[str, Any]:
        """Get all cached options for a session from Redis."""
        result = {
            "flights_outbound": [],
            "flights_inbound": [],
            "ground_transport": [],
            "accommodation": []
        }
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return result

            session_key = self._session_key(session_id)
            cache_keys = await redis_client.smembers(session_key)
            if not cache_keys:
                return result

            for cache_key in cache_keys:
                entry_key = self._entry_key(cache_key)
                raw = await redis_client.get(entry_key)
                if not raw:
                    await redis_client.srem(session_key, cache_key)
                    continue
                try:
                    entry = json.loads(raw)
                except json.JSONDecodeError:
                    await redis_client.delete(entry_key)
                    await redis_client.srem(session_key, cache_key)
                    continue
                expires_at = _deserialize_dt(entry.get("expires_at"))
                if expires_at and expires_at < datetime.utcnow():
                    await redis_client.delete(entry_key)
                    await redis_client.srem(session_key, cache_key)
                    continue
                slot_name = entry.get("slot_name")
                segment_index = entry.get("segment_index", 0)
                options = entry.get("options", [])
                if slot_name in result:
                    while len(result[slot_name]) <= segment_index:
                        result[slot_name].append([])
                    result[slot_name][segment_index] = options

            for slot_name in list(result.keys()):
                result[slot_name] = [seg for seg in result[slot_name] if len(seg) > 0]

            total_options = sum(
                len(options)
                for slot_options in result.values()
                for options in slot_options
            )
            logger.info(f"Retrieved {total_options} total cached options for session {session_id} (Redis)")
            return result

        except Exception as e:
            logger.error(f"Failed to get all session options from Redis: {e}", exc_info=True)
            return result

    async def save_selected_option(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
        selected_option: Dict[str, Any]
    ) -> bool:
        """Save selected option to Redis cache (for TripSummary)."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False

            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            entry_key = self._entry_key(cache_key)
            raw = await redis_client.get(entry_key)
            if not raw:
                logger.warning(f"Cannot save selected option: cache entry not found for {cache_key}")
                return False

            cache_entry = json.loads(raw)
            cache_entry["selected_option"] = selected_option
            cache_entry["selected_at"] = _serialize_dt(datetime.utcnow())
            cache_entry["last_accessed"] = _serialize_dt(datetime.utcnow())
            ttl = await redis_client.ttl(entry_key)
            if ttl <= 0:
                ttl = DEFAULT_TTL_HOURS * 3600
            await redis_client.set(entry_key, json.dumps(cache_entry, default=str), ex=ttl)

            logger.info(f"Saved selected option for {slot_name}[{segment_index}] in session {session_id} (Redis)")
            return True

        except Exception as e:
            logger.error(f"Failed to save selected option to Redis: {e}", exc_info=True)
            return False

    async def validate_cache_data(self, session_id: str) -> Dict[str, Any]:
        """Validate cached data for a session (reads from Redis)."""
        try:
            all_options = await self.get_all_session_options(session_id)
            issues = []
            warnings = []

            for slot_name in ("flights_outbound", "flights_inbound"):
                if all_options.get(slot_name):
                    for idx, options in enumerate(all_options[slot_name]):
                        if not options:
                            warnings.append(f"{slot_name}[{idx}]: No options cached")
                        else:
                            for opt_idx, opt in enumerate(options):
                                if not opt.get("display_name") and not opt.get("name"):
                                    issues.append(f"{slot_name}[{idx}][{opt_idx}]: Missing display_name")
                                if not opt.get("price_amount") and not opt.get("price_total"):
                                    warnings.append(f"{slot_name}[{idx}][{opt_idx}]: Missing price")

            if all_options.get("ground_transport"):
                for idx, options in enumerate(all_options["ground_transport"]):
                    if not options:
                        warnings.append(f"ground_transport[{idx}]: No options cached")

            if all_options.get("accommodation"):
                for idx, options in enumerate(all_options["accommodation"]):
                    if not options:
                        warnings.append(f"accommodation[{idx}]: No options cached")
                    else:
                        for opt_idx, opt in enumerate(options):
                            if not opt.get("display_name") and not opt.get("name"):
                                issues.append(f"accommodation[{idx}][{opt_idx}]: Missing display_name")
                            if not opt.get("price_amount") and not opt.get("price_total"):
                                warnings.append(f"accommodation[{idx}][{opt_idx}]: Missing price")

            return {
                "valid": len(issues) == 0,
                "issues": issues,
                "warnings": warnings,
                "summary": {
                    "flights_outbound": sum(len(opts) if opts else 0 for opts in (all_options.get("flights_outbound") or [])),
                    "flights_inbound": sum(len(opts) if opts else 0 for opts in (all_options.get("flights_inbound") or [])),
                    "ground_transport": sum(len(opts) if opts else 0 for opts in (all_options.get("ground_transport") or [])),
                    "accommodation": sum(len(opts) if opts else 0 for opts in (all_options.get("accommodation") or [])),
                }
            }
        except Exception as e:
            logger.error(f"Failed to validate cache data: {e}", exc_info=True)
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "warnings": [],
                "summary": {}
            }

    async def clear_session_cache(self, session_id: str) -> bool:
        """Clear all cached options for a session in Redis."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                logger.warning("Redis unavailable, cannot clear session cache")
                return False

            session_key = self._session_key(session_id)
            cache_keys = await redis_client.smembers(session_key)
            deleted = 0
            for cache_key in cache_keys:
                entry_key = self._entry_key(cache_key)
                await redis_client.delete(entry_key)
                deleted += 1
            await redis_client.delete(session_key)
            logger.info(f"Cleared {deleted} cache entries for session {session_id} (Redis)")
            return True

        except Exception as e:
            logger.error(f"Failed to clear session cache in Redis: {e}", exc_info=True)
            return False

    # ---------- Amadeus raw data (เก็บ raw response จาก Amadeus ไว้จัดช้อย / แก้ไข) ----------

    def _raw_key(self, session_id: str, slot_name: str, segment_index: int) -> str:
        return f"{KEY_AMADEUS_RAW_PREFIX}{session_id}:{slot_name}:{segment_index}"

    def _raw_index_key(self, session_id: str) -> str:
        return f"{KEY_AMADEUS_RAW_INDEX}{session_id}"

    async def save_raw_amadeus(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        raw_response: Any,
        ttl_hours: int = DEFAULT_TTL_RAW_HOURS,
    ) -> bool:
        """เก็บ raw response จาก Amadeus ต่อ slot ไว้ที่ Redis (สำหรับจัดช้อย / แก้ไข)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            rk = self._raw_key(session_id, slot_name, segment_index)
            idx_key = self._raw_index_key(session_id)
            ttl = ttl_hours * 3600
            pipe = redis_client.pipeline()
            pipe.set(rk, json.dumps(raw_response, default=str), ex=ttl)
            pipe.sadd(idx_key, rk)
            pipe.execute()
            logger.info(f"Saved raw Amadeus for {session_id} {slot_name}[{segment_index}] (Redis)")
            return True
        except Exception as e:
            logger.error(f"save_raw_amadeus failed: {e}", exc_info=True)
            return False

    async def get_raw_amadeus(
        self,
        session_id: str,
        slot_name: Optional[str] = None,
        segment_index: Optional[int] = None,
    ) -> Any:
        """อ่าน raw Amadeus ของ session (ทั้งหมด หรือต่อ slot)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return {} if slot_name is None else None
            idx_key = self._raw_index_key(session_id)
            keys = await redis_client.smembers(idx_key)
            if not keys:
                return {} if slot_name is None else None
            out = {}
            for k in keys:
                k_str = k.decode() if isinstance(k, bytes) else k
                if not k_str.startswith(KEY_AMADEUS_RAW_PREFIX):
                    continue
                rest = k_str[len(KEY_AMADEUS_RAW_PREFIX):]
                parts = rest.rsplit(":", 2)
                if len(parts) != 3:
                    continue
                sid, sname, segidx_str = parts[0], parts[1], parts[2]
                if sid != session_id:
                    continue
                try:
                    segidx = int(segidx_str)
                except ValueError:
                    continue
                if slot_name is not None and sname != slot_name:
                    continue
                if segment_index is not None and segidx != segment_index:
                    continue
                raw = await redis_client.get(k_str)
                if raw:
                    try:
                        out[f"{sname}:{segidx}"] = json.loads(raw)
                    except json.JSONDecodeError:
                        out[f"{sname}:{segidx}"] = raw
            if slot_name is not None and segment_index is not None and out:
                return out.get(f"{slot_name}:{segment_index}")
            return out
        except Exception as e:
            logger.warning(f"get_raw_amadeus failed: {e}")
            return {} if slot_name is None else None

    async def clear_raw_amadeus(self, session_id: str) -> bool:
        """เคลียร์ raw Amadeus ของ session (เรียกเมื่อ workflow เสร็จ/จองสำเร็จ)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            idx_key = self._raw_index_key(session_id)
            keys = await redis_client.smembers(idx_key)
            for k in keys:
                k_str = k.decode() if isinstance(k, bytes) else k
                await redis_client.delete(k_str)
            await redis_client.delete(idx_key)
            logger.info(f"Cleared raw Amadeus for session {session_id} (Redis)")
            return True
        except Exception as e:
            logger.error(f"clear_raw_amadeus failed: {e}", exc_info=True)
            return False

    async def clear_session_all(self, session_id: str) -> bool:
        """เคลียร์ options cache + raw Amadeus ของ session (ใช้เมื่อ workflow done/จองสำเร็จ)"""
        ok1 = await self.clear_session_cache(session_id)
        ok2 = await self.clear_raw_amadeus(session_id)
        return ok1 and ok2


# Global instance
_options_cache_service: Optional[OptionsCacheService] = None


def get_options_cache() -> OptionsCacheService:
    """Get or create options cache service instance (Redis backend)."""
    global _options_cache_service
    if _options_cache_service is None:
        _options_cache_service = OptionsCacheService()
    return _options_cache_service
