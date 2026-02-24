"""
MongoDB-only storage (Redis ถูกลบออกแล้ว — ใช้ MongoDB 100%)
"""

from typing import Optional, Dict, Any
from app.storage.interface import StorageInterface
from app.storage.mongodb_storage import MongoStorage
from app.models.session import UserSession
from app.core.logging import get_logger

logger = get_logger(__name__)

class HybridStorage(StorageInterface):
    """
    MongoDB-only Storage (Redis removed)
    All reads and writes go directly to MongoDB.
    """
    
    def __init__(self):
        self.mongo = MongoStorage()
        # Keep .redis attribute as None so legacy code that checks
        # `hasattr(storage, 'redis')` doesn't crash
        self.redis = None
        
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        return await self.mongo.get_session(session_id)

    async def save_session(self, session: UserSession) -> bool:
        return bool(await self.mongo.save_session(session))

    async def clear_session_data(self, session_id: str) -> bool:
        return await self.mongo.clear_session_data(session_id)

    async def update_title(self, session_id: str, title: str) -> bool:
        return await self.mongo.update_title(session_id, title)

    async def save_message(self, session_id: str, message: dict) -> bool:
        result = await self.mongo.save_message(session_id, message)
        if not result:
            logger.error(f"Failed to save message to MongoDB for session {session_id}")
            return False
        return True

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        return await self.mongo.get_chat_history(session_id, limit)

    async def health_check(self) -> Dict[str, Any]:
        health_status: Dict[str, Any] = {
            "status": "healthy",
            "mongodb": {},
            "redis": {
                "status": "disabled",
                "message": "Redis removed — using MongoDB only"
            }
        }
        
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
        
        return health_status
