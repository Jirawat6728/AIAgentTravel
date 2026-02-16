"""
การจัดเก็บแบบไฮบริด
รวม Redis (ความเร็ว) และ MongoDB (ความคงอยู่ของข้อมูล)
"""

import asyncio
from typing import Optional, Dict, Any
from app.storage.interface import StorageInterface
from app.storage.redis_storage import RedisStorage
from app.storage.mongodb_storage import MongoStorage
from app.models.session import UserSession
from app.core.logging import get_logger

logger = get_logger(__name__)

class HybridStorage(StorageInterface):
    """
    Hybrid Storage:
    - Reads: Cache (Redis) -> DB (Mongo) -> Cache Populate
    - Writes: Cache (Redis) + DB (Mongo) [Parallel]
    - ✅ SAFETY: Transparent MongoDB fallback if Redis is down
    """
    
    def __init__(self):
        self.redis = RedisStorage()
        self.mongo = MongoStorage()
        self._redis_healthy = None  # Cache Redis health status
        
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session with Cache-Aside pattern
        ✅ SAFETY: Transparent MongoDB fallback if Redis is down
        """
        # ✅ SAFETY: Check Redis health first - if down, skip to MongoDB
        if self._redis_healthy is False:
            logger.debug(f"Redis is down, using MongoDB directly for session {session_id}")
            return await self.mongo.get_session(session_id)
        
        # 1. Try Cache (Redis)
        try:
            session = await self.redis.get_session(session_id)
            if session:
                logger.debug(f"Cache HIT for session {session_id}")
                self._redis_healthy = True  # Mark Redis as healthy
                return session
        except Exception as e:
            logger.warning(f"Cache read failed: {e}")
            self._redis_healthy = False  # Mark Redis as unhealthy

        # 2. Try DB (Mongo) - Transparent fallback
        logger.debug(f"Cache MISS for session {session_id}, checking DB")
        session = await self.mongo.get_session(session_id)
        
        # 3. Populate Cache if found in DB
        if session:
            try:
                # Fire and forget cache update
                asyncio.create_task(self.redis.save_session(session))
            except Exception as e:
                logger.warning(f"Cache population failed: {e}")
                
        return session

    async def save_session(self, session: UserSession) -> bool:
        """
        Save to both Cache and DB
        ✅ SAFETY: Transparent MongoDB fallback if Redis is down
        """
        # ✅ SAFETY: If Redis is down, use MongoDB only
        if self._redis_healthy is False:
            logger.debug(f"Redis is down, saving to MongoDB only for session {session.session_id}")
            return await self.mongo.save_session(session)
        
        # Run both writes in parallel for performance
        # If Redis fails, we still have Mongo. If Mongo fails, we have a problem (persistence).
        
        results = await asyncio.gather(
            self.redis.save_session(session),
            self.mongo.save_session(session),
            return_exceptions=True
        )
        
        redis_res, mongo_res = results
        
        # Check Redis result
        if isinstance(redis_res, Exception):
            logger.warning(f"Redis save failed with exception: {redis_res}")
            self._redis_healthy = False  # Mark Redis as unhealthy
        elif redis_res is False:
            logger.warning("Redis save failed (returned False)")
            self._redis_healthy = False  # Mark Redis as unhealthy
        else:
            self._redis_healthy = True  # Mark Redis as healthy
            
        # Check Mongo result
        if isinstance(mongo_res, Exception):
            logger.error(f"Mongo save failed with exception: {mongo_res}")
            return False
        elif mongo_res is False:
            logger.error("Mongo save failed (returned False)")
            return False
            
        # Return True only if Mongo succeeded (Primary Source of Truth)
        # Redis failure is acceptable (just performance hit)
        
        # ✅ Sync to long-term memory in background
        # Extract important information and consolidate to memories collection
        if mongo_res:
            try:
                from app.storage.redis_sync import redis_sync_service
                # Trigger sync to long-term memory in background
                asyncio.create_task(redis_sync_service.sync_session_with_history(session.session_id))
            except Exception as e:
                logger.debug(f"Background long-term memory sync trigger failed (non-critical): {e}")
        
        return bool(mongo_res)

    async def clear_session_data(self, session_id: str) -> bool:
        """
        Clear from both
        """
        results = await asyncio.gather(
            self.redis.clear_session_data(session_id),
            self.mongo.clear_session_data(session_id),
            return_exceptions=True
        )
        return True # Best effort

    async def update_title(self, session_id: str, title: str) -> bool:
        """
        Update title in both
        """
        results = await asyncio.gather(
            self.redis.update_title(session_id, title),
            self.mongo.update_title(session_id, title),
            return_exceptions=True
        )
        return True

    async def save_message(self, session_id: str, message: dict) -> bool:
        """
        Save message to both Redis (cache) and MongoDB (persistence)
        ✅ PRIORITY: MongoDB must succeed for data persistence
        """
        # 1. Save to MongoDB first (primary storage - must succeed)
        mongo_result = await self.mongo.save_message(session_id, message)
        
        if not mongo_result:
            logger.error(f"Failed to save message to MongoDB for session {session_id}")
            return False  # Return False if MongoDB save failed
        
        # 2. Save to Redis in background (cache - optional, but don't block)
        try:
            asyncio.create_task(self.redis.save_message(session_id, message))
        except Exception as e:
            logger.warning(f"Failed to queue Redis save for session {session_id}: {e}")
            # Don't fail if Redis save fails - MongoDB is the source of truth
        
        # ✅ Sync to long-term memory in background
        # Extract important conversation information and consolidate to memories collection
        try:
            from app.storage.redis_sync import redis_sync_service
            # Trigger sync to long-term memory in background
            asyncio.create_task(redis_sync_service.sync_chat_history_to_long_term_memory(session_id))
        except Exception as e:
            logger.debug(f"Background long-term memory sync trigger failed (non-critical): {e}")
        
        logger.debug(f"Message saved successfully to MongoDB for session {session_id}")
        return True

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """
        Get history: Try Redis first, then Mongo (primary source)
        ✅ PRIORITY: MongoDB is the source of truth for conversation history
        """
        # 1. Try Redis (cache) for speed
        try:
            redis_history = await self.redis.get_chat_history(session_id, limit)
            if redis_history and len(redis_history) > 0:
                logger.debug(f"Cache HIT for chat history: session {session_id}")
                # Also verify with MongoDB in background to ensure consistency
                asyncio.create_task(self._sync_history_from_mongo(session_id))
                return redis_history
        except Exception as e:
            logger.debug(f"Redis history read failed (expected if Redis unavailable): {e}")
            
        # 2. Fallback to MongoDB (primary source of truth)
        logger.debug(f"Cache MISS for chat history: session {session_id}, checking MongoDB")
        mongo_history = await self.mongo.get_chat_history(session_id, limit)
        
        # 3. Populate Redis cache in background (don't block)
        if mongo_history and len(mongo_history) > 0:
            try:
                # Populate Redis with recent messages for faster future access
                asyncio.create_task(self._populate_redis_history(session_id, mongo_history))
            except Exception as e:
                logger.debug(f"Failed to populate Redis cache: {e}")
            
        return mongo_history
    
    async def _sync_history_from_mongo(self, session_id: str):
        """
        Background task to sync history from MongoDB to ensure Redis is up-to-date
        """
        try:
            mongo_history = await self.mongo.get_chat_history(session_id, limit=100)
            if mongo_history:
                # Update Redis with latest from MongoDB
                for msg in mongo_history[-10:]:  # Only sync last 10 messages
                    await self.redis.save_message(session_id, msg)
        except Exception as e:
            logger.debug(f"Background sync from MongoDB failed: {e}")
    
    async def _populate_redis_history(self, session_id: str, messages: list[dict]):
        """
        Background task to populate Redis with messages from MongoDB
        """
        # ✅ SAFETY: Skip if Redis is down
        if self._redis_healthy is False:
            return
        
        try:
            for msg in messages[-20:]:  # Populate last 20 messages to Redis
                await self.redis.save_message(session_id, msg)
            self._redis_healthy = True  # Mark Redis as healthy if successful
        except Exception as e:
            logger.debug(f"Failed to populate Redis history: {e}")
            self._redis_healthy = False  # Mark Redis as unhealthy
    
    async def health_check(self) -> Dict[str, Any]:
        """
        ✅ Health check method to verify MongoDB and Redis connections
        
        Returns:
            Dictionary with health status:
            {
                "status": "healthy" | "degraded" | "unhealthy",
                "mongodb": {...},
                "redis": {...}
            }
        """
        health_status = {
            "status": "healthy",
            "mongodb": {},
            "redis": {}
        }
        
        # Check MongoDB
        try:
            mongo_health = await self.mongo.health_check()
            health_status["mongodb"] = mongo_health
            
            if mongo_health.get("status") != "healthy":
                health_status["status"] = "unhealthy"
        except Exception as e:
            logger.error(f"MongoDB health check error: {e}", exc_info=True)
            health_status["mongodb"] = {
                "status": "unhealthy",
                "message": f"Health check failed: {str(e)[:200]}"
            }
            health_status["status"] = "unhealthy"
        
        # Check Redis (optional)
        try:
            redis_client = await self.redis.redis_mgr.get_redis()
            if redis_client:
                await redis_client.ping()
                health_status["redis"] = {
                    "status": "healthy",
                    "message": "Redis connection verified"
                }
                self._redis_healthy = True
            else:
                health_status["redis"] = {
                    "status": "unavailable",
                    "message": "Redis not configured (optional service)"
                }
                self._redis_healthy = False
        except Exception as e:
            # Redis is optional - don't log as warning
            health_status["redis"] = {
                "status": "unavailable",
                "message": "Redis not available (optional service)"
            }
            self._redis_healthy = False
            
            # If MongoDB is healthy but Redis is down, status is "degraded"
            if health_status["mongodb"].get("status") == "healthy":
                health_status["status"] = "degraded"
        
        return health_status