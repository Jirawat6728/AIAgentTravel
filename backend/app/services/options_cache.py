"""
Options Cache Service
เก็บตัวเลือกทั้งหมด (flights, transport, accommodation) เพื่อใช้ร่วมกับ AI และ TripSummary
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import hashlib
import json
from app.core.logging import get_logger
from app.storage.connection_manager import MongoConnectionManager

logger = get_logger(__name__)


class OptionsCacheService:
    """
    Cache service สำหรับเก็บตัวเลือกทั้งหมด:
    - ไฟท์บิน (ขาไป, ขากลับ)
    - พาหนะทุกชนิด (ขาไป, ขากลับ)
    - ที่พักทุกชนิด
    """
    
    def __init__(self):
        self.db = None
        self.cache_collection = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize MongoDB connection"""
        try:
            mongo_mgr = MongoConnectionManager.get_instance()
            self.db = mongo_mgr.get_database()
            self.cache_collection = self.db["options_cache"]
            self._create_indexes()
            logger.info("OptionsCacheService initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OptionsCacheService: {e}")
    
    def _create_indexes(self):
        """Create indexes for cache collection"""
        try:
            # Index for cache_key (unique)
            self.cache_collection.create_index("cache_key", unique=True)
            # Index for session_id and slot_name
            self.cache_collection.create_index([("session_id", 1), ("slot_name", 1)])
            # Index for expiry
            self.cache_collection.create_index("expires_at", expireAfterSeconds=0)
            logger.info("Options cache indexes created")
        except Exception as e:
            logger.warning(f"Failed to create cache indexes: {e}")
    
    def _generate_cache_key(
        self,
        session_id: str,
        slot_name: str,
        requirements: Dict[str, Any],
        segment_index: int = 0
    ) -> str:
        """
        Generate unique cache key from requirements
        
        Args:
            session_id: Session identifier
            slot_name: Slot name (flights_outbound, flights_inbound, ground_transport, accommodation)
            requirements: Segment requirements
            segment_index: Segment index within slot
            
        Returns:
            Unique cache key
        """
        # Normalize requirements for consistent key generation
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
        
        # Create hash from normalized requirements
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
        ttl_hours: int = 24
    ) -> bool:
        """
        Save options to cache
        
        Args:
            session_id: Session identifier
            slot_name: Slot name (flights_outbound, flights_inbound, ground_transport, accommodation)
            segment_index: Segment index
            requirements: Segment requirements
            options: List of options to cache
            ttl_hours: Time to live in hours (default 24 hours)
            
        Returns:
            True if saved successfully
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            cache_entry = {
                "cache_key": cache_key,
                "session_id": session_id,
                "slot_name": slot_name,
                "segment_index": segment_index,
                "requirements": requirements,
                "options": options,
                "options_count": len(options),
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "last_accessed": datetime.utcnow()
            }
            
            # ✅ Upsert cache entry (await async operation)
            await self.cache_collection.replace_one(
                {"cache_key": cache_key},
                cache_entry,
                upsert=True
            )
            
            logger.info(f"Cached {len(options)} options for {slot_name}[{segment_index}] in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save options to cache: {e}", exc_info=True)
            return False
    
    async def get_options(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get options from cache
        
        Args:
            session_id: Session identifier
            slot_name: Slot name
            segment_index: Segment index
            requirements: Segment requirements
            
        Returns:
            List of cached options or None if not found/expired
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            
            # ✅ Await the async find_one operation
            cache_entry = await self.cache_collection.find_one({"cache_key": cache_key})
            
            if not cache_entry:
                logger.debug(f"Cache miss for {cache_key}")
                return None
            
            # Check if expired
            if cache_entry.get("expires_at") and cache_entry["expires_at"] < datetime.utcnow():
                logger.debug(f"Cache expired for {cache_key}")
                # ✅ Delete expired entry (await async operation)
                await self.cache_collection.delete_one({"cache_key": cache_key})
                return None
            
            # ✅ Update last accessed time (await async operation)
            await self.cache_collection.update_one(
                {"cache_key": cache_key},
                {"$set": {"last_accessed": datetime.utcnow()}}
            )
            
            options = cache_entry.get("options", [])
            logger.info(f"Cache hit: Retrieved {len(options)} options for {slot_name}[{segment_index}]")
            return options
            
        except Exception as e:
            logger.error(f"Failed to get options from cache: {e}", exc_info=True)
            return None
    
    async def get_all_session_options(self, session_id: str) -> Dict[str, Any]:
        """
        Get all cached options for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dictionary with all cached options organized by slot
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            # ✅ Await async find operation and convert to list
            cursor = self.cache_collection.find({
                "session_id": session_id,
                "expires_at": {"$gt": datetime.utcnow()}
            }).sort("slot_name", 1)
            cache_entries = await cursor.to_list(length=1000)
            
            result = {
                "flights_outbound": [],
                "flights_inbound": [],
                "ground_transport": [],
                "accommodation": []
            }
            
            for entry in cache_entries:
                slot_name = entry.get("slot_name")
                segment_index = entry.get("segment_index", 0)
                options = entry.get("options", [])
                
                if slot_name in result:
                    # Ensure we have enough segments
                    while len(result[slot_name]) <= segment_index:
                        result[slot_name].append([])
                    result[slot_name][segment_index] = options
            
            # Remove empty segments
            for slot_name in result:
                result[slot_name] = [seg for seg in result[slot_name] if len(seg) > 0]
            
            total_options = sum(
                len(options) 
                for slot_options in result.values() 
                for options in slot_options
            )
            
            logger.info(f"Retrieved {total_options} total cached options for session {session_id}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get all session options: {e}", exc_info=True)
            return {
                "flights_outbound": [],
                "flights_inbound": [],
                "ground_transport": [],
                "accommodation": []
            }
    
    async def save_selected_option(
        self,
        session_id: str,
        slot_name: str,
        segment_index: int,
        requirements: Dict[str, Any],
        selected_option: Dict[str, Any]
    ) -> bool:
        """
        Save selected option to cache (for TripSummary)
        
        Args:
            session_id: Session identifier
            slot_name: Slot name
            segment_index: Segment index
            requirements: Segment requirements
            selected_option: Selected option data
            
        Returns:
            True if saved successfully
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            cache_key = self._generate_cache_key(session_id, slot_name, requirements, segment_index)
            
            # ✅ Update cache entry with selected option (await async operation)
            await self.cache_collection.update_one(
                {"cache_key": cache_key},
                {
                    "$set": {
                        "selected_option": selected_option,
                        "selected_at": datetime.utcnow(),
                        "last_accessed": datetime.utcnow()
                    }
                }
            )
            
            logger.info(f"Saved selected option for {slot_name}[{segment_index}] in session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save selected option: {e}", exc_info=True)
            return False
    
    async def validate_cache_data(self, session_id: str) -> Dict[str, Any]:
        """
        Validate cached data for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Validation result with status and issues
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            all_options = await self.get_all_session_options(session_id)
            issues = []
            warnings = []
            
            # Validate flights
            if all_options.get("flights_outbound"):
                for idx, options in enumerate(all_options["flights_outbound"]):
                    if not options:
                        warnings.append(f"flights_outbound[{idx}]: No options cached")
                    else:
                        for opt_idx, opt in enumerate(options):
                            if not opt.get("display_name") and not opt.get("name"):
                                issues.append(f"flights_outbound[{idx}][{opt_idx}]: Missing display_name")
                            if not opt.get("price_amount") and not opt.get("price_total"):
                                warnings.append(f"flights_outbound[{idx}][{opt_idx}]: Missing price")
            
            if all_options.get("flights_inbound"):
                for idx, options in enumerate(all_options["flights_inbound"]):
                    if not options:
                        warnings.append(f"flights_inbound[{idx}]: No options cached")
                    else:
                        for opt_idx, opt in enumerate(options):
                            if not opt.get("display_name") and not opt.get("name"):
                                issues.append(f"flights_inbound[{idx}][{opt_idx}]: Missing display_name")
                            if not opt.get("price_amount") and not opt.get("price_total"):
                                warnings.append(f"flights_inbound[{idx}][{opt_idx}]: Missing price")
            
            # Validate ground transport
            if all_options.get("ground_transport"):
                for idx, options in enumerate(all_options["ground_transport"]):
                    if not options:
                        warnings.append(f"ground_transport[{idx}]: No options cached")
            
            # Validate accommodation
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
            
            is_valid = len(issues) == 0
            
            return {
                "valid": is_valid,
                "issues": issues,
                "warnings": warnings,
                "summary": {
                    "flights_outbound": sum(len(opts) if opts is not None else 0 for opts in (all_options.get("flights_outbound") or [])),
                    "flights_inbound": sum(len(opts) if opts is not None else 0 for opts in (all_options.get("flights_inbound") or [])),
                    "ground_transport": sum(len(opts) if opts is not None else 0 for opts in (all_options.get("ground_transport") or [])),
                    "accommodation": sum(len(opts) if opts is not None else 0 for opts in (all_options.get("accommodation") or []))
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
        """
        Clear all cached options for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if cleared successfully
        """
        try:
            if self.cache_collection is None:
                self._initialize_db()
            
            result = self.cache_collection.delete_many({"session_id": session_id})
            logger.info(f"Cleared {result.deleted_count} cache entries for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear session cache: {e}", exc_info=True)
            return False


# Global instance
_options_cache_service = None

def get_options_cache() -> OptionsCacheService:
    """Get or create options cache service instance"""
    global _options_cache_service
    if _options_cache_service is None:
        _options_cache_service = OptionsCacheService()
    return _options_cache_service
