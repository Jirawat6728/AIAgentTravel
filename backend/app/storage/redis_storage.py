"""เก็บเซสชันผู้ใช้ใน Redis (หน่วยความจำระยะสั้น) ตาม StorageInterface."""
import json
from typing import Optional
from app.storage.interface import StorageInterface
from app.storage.connection_manager import RedisConnectionManager
from app.models.session import UserSession
from app.models.database import SessionDocument
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class RedisStorage(StorageInterface):
    """
    Redis Storage for active sessions (Short-term memory)
    """
    
    def __init__(self):
        self.connection_manager = RedisConnectionManager.get_instance()
        self.ttl = settings.redis_ttl
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session from Redis
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return None  # Redis unavailable - cache miss
            data = await redis_client.get(f"session:{session_id}")
            
            if not data:
                return None
            
            # Deserialize JSON -> Dict -> SessionDocument -> UserSession
            session_dict = json.loads(data)
            # Use SessionDocument for consistent validation/conversion
            session_doc = SessionDocument(**session_dict)
            return session_doc.to_user_session()
            
        except Exception as e:
            # ✅ Redis is optional - only log as debug/warning, not error
            # Check if it's a connection error (Redis not running)
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session_id}")
            else:
                logger.warning(f"Redis get_session failed for {session_id}: {e}")
            # Don't raise, just return None (cache miss behavior)
            return None

    async def save_session(self, session: UserSession) -> bool:
        """
        Save session to Redis with TTL
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return False  # Redis unavailable - skip save
            
            # Convert UserSession -> SessionDocument -> Dict -> JSON
            session_doc = SessionDocument.from_user_session(session)
            # Use model_dump_json for Pydantic v2 or json() for v1
            data = session_doc.model_dump_json()
            
            key = f"session:{session.session_id}"
            await redis_client.set(key, data, ex=self.ttl)
            
            return True
        except Exception as e:
            # ✅ Redis is optional - only log as warning, not error
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session.session_id}")
            else:
                logger.warning(f"Redis save_session failed for {session.session_id}: {e}")
            return False

    async def clear_session_data(self, session_id: str) -> bool:
        """
        Clear session from Redis
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            await redis_client.delete(f"session:{session_id}")
            return True
        except Exception as e:
            # ✅ Redis is optional - only log as warning, not error
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session_id}")
            else:
                logger.warning(f"Redis clear_session_data failed for {session_id}: {e}")
            return False

    async def update_title(self, session_id: str, title: str) -> bool:
        """
        Update session title in Redis
        """
        try:
            session = await self.get_session(session_id)
            if session:
                session.title = title
                return await self.save_session(session)
            return False
        except Exception as e:
            # ✅ Redis is optional - only log as warning, not error
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session_id}")
            else:
                logger.warning(f"Redis update_title failed for {session_id}: {e}")
            return False

    async def save_message(self, session_id: str, message: dict) -> bool:
        """
        ✅ SECURITY: Save message with session_id as key (which includes user_id)
        """
        """
        Save message to Redis List (for quick access)
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return False  # Redis unavailable - skip save
            key = f"history:{session_id}"
            
            # Serialize message
            data = json.dumps(message, default=str)
            
            # Push to right (end) of list
            await redis_client.rpush(key, data)
            # Trim to keep only last 100 messages (prevent infinite growth)
            await redis_client.ltrim(key, -100, -1)
            # Set TTL same as session
            await redis_client.expire(key, self.ttl)
            
            return True
        except Exception as e:
            # ✅ Redis is optional - only log as warning, not error
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session_id}")
            else:
                logger.warning(f"Redis save_message failed for {session_id}: {e}")
            return False

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """
        ✅ SECURITY: Get history by exact session_id (which includes user_id)
        """
        """
        Get chat history from Redis
        """
        try:
            redis_client = await self.connection_manager.get_redis()
            if redis_client is None:
                return []  # Redis unavailable - return empty
            key = f"history:{session_id}"
            
            # Get list range (last N items)
            # Redis lrange: 0 is first, -1 is last
            # We want last 'limit' items
            start = -limit
            items = await redis_client.lrange(key, start, -1)
            
            messages = []
            for item in items:
                try:
                    messages.append(json.loads(item))
                except:
                    continue
            return messages
        except Exception as e:
            # ✅ Redis is optional - only log as debug/warning, not error
            error_str = str(e).lower()
            if "connect" in error_str or "timeout" in error_str or "10061" in error_str:
                logger.debug(f"Redis not available (expected in degraded mode): {session_id}")
            else:
                logger.warning(f"Redis get_chat_history failed for {session_id}: {e}")
            return []
