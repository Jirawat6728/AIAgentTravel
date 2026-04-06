"""
เซอร์วิสแคชตัวเลือก (in-memory — Redis ถูกลบออกแล้ว)
เก็บตัวเลือกทั้งหมด (เที่ยวบิน การเดินทาง ที่พัก) ใน memory สำหรับ AI และ TripSummary
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
from app.core.logging import get_logger
from app.core.redis_client import get_redis, is_redis_available
from app.core.config import settings

logger = get_logger(__name__)

DEFAULT_TTL_HOURS = 24
DEFAULT_TTL_RAW_HOURS = 24

# In-memory stores (fallback)
# options_store: cache_key -> cache_entry dict
_options_store: Dict[str, Dict[str, Any]] = {}
# session_index: session_id -> set of cache_keys
_session_index: Dict[str, set] = {}
# raw_store: "{session_id}:{slot_name}:{segment_index}" -> raw data
_raw_store: Dict[str, Any] = {}


def _serialize_dt(dt: datetime) -> Optional[str]:
    return dt.isoformat() if dt else None


def _deserialize_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


class OptionsCacheService:
    """
    Cache service เก็บตัวเลือกใน memory (Redis removed):
    - ไฟท์บิน (ขาไป, ขากลับ)
    - พาหนะทุกชนิด (ขาไป, ขากลับ)
    - ที่พักทุกชนิด
    """

    def __init__(self):
        if settings.redis_url:
            logger.info("OptionsCacheService initialized (Redis + in-memory fallback)")
        else:
            logger.info("OptionsCacheService initialized (in-memory only)")

    def _generate_cache_key(
        self,
        session_id: str,
        slot_name: str,
        requirements: Dict[str, Any],
        segment_index: int = 0,
    ) -> str:
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

    async def save_options(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
        options: List[Dict[str, Any]],
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> bool:
        cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl_hours)

        entry = {
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

        ok = False

        # Redis path (ใช้เมื่อมี REDIS_URL และ Redis พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    await redis.set(
                        f"options:{cache_key}",
                        json.dumps(entry, ensure_ascii=False, default=str),
                        ex=int(ttl_hours * 3600),
                    )
                    await redis.sadd(f"options:sessions:{session_id}", cache_key)
                    await redis.expire(f"options:sessions:{session_id}", int(ttl_hours * 3600))
                    ok = True
            except Exception as e:
                logger.warning(f"Failed to save options to Redis cache: {e}")

        # In-memory fallback
        try:
            _options_store[cache_key] = entry

            if session_id not in _session_index:
                _session_index[session_id] = set()
            _session_index[session_id].add(cache_key)

            logger.info(
                f"Cached {len(options)} options for {slot_name}[{segment_index}] in session {session_id} "
                f"({'Redis' if ok else 'memory'})"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save options to memory cache: {e}", exc_info=True)
            return ok

    async def get_options(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
    ) -> Optional[List[Dict[str, Any]]]:
        cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)

        # Redis path (ใช้เมื่อมี REDIS_URL และ Redis พร้อม)
        if is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    raw = await redis.get(f"options:{cache_key}")
                    if raw:
                        entry = json.loads(raw)
                        options = entry.get("options", [])
                        await redis.hset(
                            f"options:meta:{cache_key}",
                            mapping={"last_accessed": _serialize_dt(datetime.utcnow()) or ""},
                        )
                        logger.info(
                            f"Cache hit: Retrieved {len(options)} options for {slot_name}[{segment_index}] (Redis)"
                        )
                        return options
            except Exception as e:
                logger.warning(f"Failed to get options from Redis cache: {e}")

        # In-memory fallback
        try:
            entry = _options_store.get(cache_key)
            if not entry:
                logger.debug(f"Cache miss for {cache_key}")
                return None

            expires_at = _deserialize_dt(entry.get("expires_at"))
            if expires_at and expires_at < datetime.utcnow():
                logger.debug(f"Cache expired for {cache_key}")
                _options_store.pop(cache_key, None)
                if session_id in _session_index:
                    _session_index[session_id].discard(cache_key)
                return None

            entry["last_accessed"] = _serialize_dt(datetime.utcnow())
            options = entry.get("options", [])
            logger.info(
                f"Cache hit: Retrieved {len(options)} options for {slot_name}[{segment_index}] (memory)"
            )
            return options
        except Exception as e:
            logger.error(f"Failed to get options from memory cache: {e}", exc_info=True)
            return None

    async def get_all_session_options(self, session_id: str) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "flights_outbound": [],
            "flights_inbound": [],
            "ground_transport": [],
            "accommodation": [],
        }
        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    cache_keys = await redis.smembers(f"options:sessions:{session_id}")
                    now = datetime.utcnow()
                    for cache_key in cache_keys or []:
                        raw = await redis.get(f"options:{cache_key}")
                        if not raw:
                            continue
                        entry = json.loads(raw)
                        expires_at = _deserialize_dt(entry.get("expires_at"))
                        if expires_at and expires_at < now:
                            await redis.delete(f"options:{cache_key}")
                            await redis.srem(f"options:sessions:{session_id}", cache_key)
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
                    logger.info(
                        f"Retrieved {total_options} total cached options for session {session_id} (Redis)"
                    )
                    return result
            except Exception as e:
                logger.warning(f"Failed to get all session options from Redis cache: {e}")

        # In-memory fallback
        try:
            cache_keys = list(_session_index.get(session_id, set()))
            now = datetime.utcnow()
            for cache_key in cache_keys:
                entry = _options_store.get(cache_key)
                if not entry:
                    _session_index.get(session_id, set()).discard(cache_key)
                    continue
                expires_at = _deserialize_dt(entry.get("expires_at"))
                if expires_at and expires_at < now:
                    _options_store.pop(cache_key, None)
                    _session_index.get(session_id, set()).discard(cache_key)
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
            logger.info(f"Retrieved {total_options} total cached options for session {session_id} (memory)")
            return result
        except Exception as e:
            logger.error(f"Failed to get all session options from memory cache: {e}", exc_info=True)
            return result

    async def save_selected_option(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
        selected_option: Dict[str, Any],
    ) -> bool:
        cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)

        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    raw = await redis.get(f"options:{cache_key}")
                    if not raw:
                        logger.warning(f"Cannot save selected option: Redis cache entry not found for {cache_key}")
                    else:
                        entry = json.loads(raw)
                        entry["selected_option"] = selected_option
                        entry["selected_at"] = _serialize_dt(datetime.utcnow())
                        entry["last_accessed"] = _serialize_dt(datetime.utcnow())
                        await redis.set(
                            f"options:{cache_key}",
                            json.dumps(entry, ensure_ascii=False, default=str),
                        )
                        logger.info(
                            f"Saved selected option for {slot_name}[{segment_index}] in session {session_id} (Redis)"
                        )
            except Exception as e:
                logger.warning(f"Failed to save selected option to Redis cache: {e}")

        # In-memory fallback
        try:
            entry = _options_store.get(cache_key)
            if not entry:
                logger.warning(f"Cannot save selected option: cache entry not found for {cache_key}")
                return False
            entry["selected_option"] = selected_option
            entry["selected_at"] = _serialize_dt(datetime.utcnow())
            entry["last_accessed"] = _serialize_dt(datetime.utcnow())
            logger.info(
                f"Saved selected option for {slot_name}[{segment_index}] in session {session_id} (memory)"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save selected option to memory cache: {e}", exc_info=True)
            return False

    async def validate_cache_data(self, session_id: str) -> Dict[str, Any]:
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
                },
            }
        except Exception as e:
            logger.error(f"Failed to validate cache data: {e}", exc_info=True)
            return {"valid": False, "issues": [f"Validation error: {str(e)}"], "warnings": [], "summary": {}}

    async def clear_session_cache(self, session_id: str) -> bool:
        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    cache_keys = await redis.smembers(f"options:sessions:{session_id}")
                    keys_to_delete = [f"options:{k}" for k in cache_keys or []]
                    if keys_to_delete:
                        await redis.delete(*keys_to_delete)
                    await redis.delete(f"options:sessions:{session_id}")
                    logger.info(
                        f"Cleared {len(cache_keys or [])} Redis cache entries for session {session_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to clear Redis session cache: {e}")

        # In-memory fallback
        try:
            cache_keys = list(_session_index.pop(session_id, set()))
            for cache_key in cache_keys:
                _options_store.pop(cache_key, None)
            logger.info(f"Cleared {len(cache_keys)} cache entries for session {session_id} (memory)")
            return True
        except Exception as e:
            logger.error(f"Failed to clear session cache in memory: {e}", exc_info=True)
            return False

    # ---------- Amadeus raw data ----------

    def _raw_key(self, session_id: str, slot_name: str, segment_index: int) -> str:
        return f"{session_id}:{slot_name}:{segment_index}"

    async def save_raw_amadeus(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        raw_response: Any,
        ttl_hours: int = DEFAULT_TTL_RAW_HOURS,
    ) -> bool:
        rk = self._raw_key(session_id, slot_name, segment_index)

        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    await redis.set(
                        f"options:raw:{rk}",
                        json.dumps(raw_response, ensure_ascii=False, default=str),
                        ex=int(ttl_hours * 3600),
                    )
                    logger.info(f"Saved raw Amadeus for {session_id} {slot_name}[{segment_index}] (Redis)")
            except Exception as e:
                logger.warning(f"save_raw_amadeus Redis failed: {e}")

        # In-memory fallback
        try:
            _raw_store[rk] = raw_response
            logger.info(f"Saved raw Amadeus for {session_id} {slot_name}[{segment_index}] (memory)")
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
        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    if slot_name is not None and segment_index is not None:
                        rk = self._raw_key(session_id, slot_name, segment_index)
                        raw = await redis.get(f"options:raw:{rk}")
                        return json.loads(raw) if raw else None
                    # Return all for session
                    out: Dict[str, Any] = {}
                    pattern = f"options:raw:{session_id}:*"
                    cursor = "0"
                    while True:
                        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                        for full_key in keys or []:
                            raw = await redis.get(full_key)
                            if not raw:
                                continue
                            payload = json.loads(raw)
                            # key format: options:raw:{session_id}:{slot_name}:{segment}
                            parts = full_key.split("options:raw:", 1)[-1].split(":")
                            if len(parts) >= 3:
                                _, sname, segidx_str = parts[0], parts[1], parts[2]
                                if slot_name is None or sname == slot_name:
                                    out[f"{sname}:{segidx_str}"] = payload
                        if cursor == "0":
                            break
                    return out
            except Exception as e:
                logger.warning(f"get_raw_amadeus Redis failed: {e}")

        # In-memory fallback
        try:
            if slot_name is not None and segment_index is not None:
                rk = self._raw_key(session_id, slot_name, segment_index)
                return _raw_store.get(rk)
            # Return all for session
            out = {}
            for k, v in _raw_store.items():
                if k.startswith(f"{session_id}:"):
                    rest = k[len(session_id) + 1:]
                    parts = rest.rsplit(":", 1)
                    if len(parts) == 2:
                        sname, segidx_str = parts
                        if slot_name is None or sname == slot_name:
                            out[f"{sname}:{segidx_str}"] = v
            return out
        except Exception as e:
            logger.warning(f"get_raw_amadeus failed: {e}")
            return {} if slot_name is None else None

    async def clear_raw_amadeus(self, session_id: str) -> bool:
        # Redis path
        if settings.enable_redis_cache and is_redis_available():
            try:
                redis = await get_redis()
                if redis is not None:
                    pattern = f"options:raw:{session_id}:*"
                    cursor = "0"
                    keys_to_delete: List[str] = []
                    while True:
                        cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
                        for k in keys or []:
                            keys_to_delete.append(k)
                        if cursor == "0":
                            break
                    if keys_to_delete:
                        await redis.delete(*keys_to_delete)
                    logger.info(f"Cleared {len(keys_to_delete)} raw Amadeus entries for session {session_id} (Redis)")
            except Exception as e:
                logger.warning(f"clear_raw_amadeus Redis failed: {e}")

        # In-memory fallback
        try:
            keys_to_delete = [k for k in _raw_store if k.startswith(f"{session_id}:")]
            for k in keys_to_delete:
                _raw_store.pop(k, None)
            logger.info(f"Cleared raw Amadeus for session {session_id} (memory)")
            return True
        except Exception as e:
            logger.error(f"clear_raw_amadeus failed: {e}", exc_info=True)
            return False

    async def clear_session_all(self, session_id: str) -> bool:
        ok1 = await self.clear_session_cache(session_id)
        ok2 = await self.clear_raw_amadeus(session_id)
        return ok1 and ok2


# Global instance
_options_cache_service: Optional[OptionsCacheService] = None


def get_options_cache() -> OptionsCacheService:
    """Get or create options cache service instance (in-memory backend)."""
    global _options_cache_service
    if _options_cache_service is None:
        _options_cache_service = OptionsCacheService()
    return _options_cache_service
