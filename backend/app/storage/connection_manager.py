"""
ตัวจัดการการเชื่อมต่อแบบ singleton
จัดการการเชื่อมต่อ MongoDB (Redis ถูกลบออกแล้ว — ใช้ MongoDB 100%)
"""

from __future__ import annotations
from typing import Optional
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    MongoDB Connection Manager — Singleton pattern for shared connection pool.
    Redis has been removed; all storage uses MongoDB directly.
    """

    _instance: Optional['ConnectionManager'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> 'ConnectionManager':
        if cls._instance is None:
            cls._instance = ConnectionManager()
        return cls._instance

    def __init__(self):
        """Initialize connection manager (only once due to singleton)"""
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._mongo_db: Optional[AsyncIOMotorDatabase] = None
        self.mongo_database_name: Optional[str] = None
        # Kept for legacy code that checks `storage.redis`
        self.redis = None

    # =============================================================================
    # MongoDB Methods
    # =============================================================================

    def get_mongo_database(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database with auto-init"""
        if self._mongo_client is None:
            self._init_mongo_connection()
        return self._mongo_db

    def get_database(self) -> AsyncIOMotorDatabase:
        """Alias for get_mongo_database (backward compatibility)"""
        return self.get_mongo_database()

    def _init_mongo_connection(self):
        """Initialize MongoDB connection pool"""
        connection_string = os.getenv("MONGO_URI") or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.mongo_database_name = os.getenv("MONGO_DB_NAME") or os.getenv("MONGODB_DATABASE", "travel_agent")

        self._mongo_client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            socketTimeoutMS=20000,
            heartbeatFrequencyMS=10000,
            retryWrites=True,
            retryReads=True,
            maxPoolSize=50,
            minPoolSize=5,
            maxIdleTimeMS=30000,
            waitQueueTimeoutMS=10000,
        )
        self._mongo_db = self._mongo_client[self.mongo_database_name]
        logger.info(f"MongoDB Connection Pool initialized: database={self.mongo_database_name}")

    @property
    def mongo_client(self) -> AsyncIOMotorClient:
        if self._mongo_client is None:
            self._init_mongo_connection()
        return self._mongo_client

    @property
    def client(self) -> AsyncIOMotorClient:
        """Alias for mongo_client (backward compatibility)"""
        return self.mongo_client

    @property
    def mongo_db(self) -> AsyncIOMotorDatabase:
        if self._mongo_db is None:
            self._init_mongo_connection()
        return self._mongo_db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Alias for mongo_db (backward compatibility)"""
        return self.mongo_db

    @property
    def database_name(self) -> str:
        if self.mongo_database_name is None:
            self._init_mongo_connection()
        return self.mongo_database_name

    async def mongo_ping(self) -> bool:
        """Test MongoDB connection"""
        try:
            if self._mongo_client is None:
                return False
            await asyncio.wait_for(
                self.mongo_client.admin.command('ping'),
                timeout=1.0
            )
            return True
        except Exception as e:
            logger.warning(f"MongoDB ping failed: {str(e)}")
            try:
                self._init_mongo_connection()
                await asyncio.wait_for(
                    self.mongo_client.admin.command('ping'),
                    timeout=1.0
                )
                logger.info("MongoDB reconnected successfully")
                return True
            except Exception as reconnect_error:
                logger.error(f"MongoDB reconnection failed: {reconnect_error}")
                return False

    async def close_mongo(self):
        """Close MongoDB connection"""
        if self._mongo_client:
            self._mongo_client.close()
            self._mongo_client = None
            self._mongo_db = None
            logger.info("MongoDB connection closed")

    # Redis stub — kept so legacy callers don't crash
    async def get_redis(self):
        """Redis removed — always returns None"""
        return None

    async def close_redis(self):
        """Redis removed — no-op"""
        pass

    async def close_all(self):
        """Close all connections"""
        await self.close_mongo()


# =============================================================================
# Backward compatibility aliases
# =============================================================================

class MongoConnectionManager:
    """Backward compatibility wrapper for MongoDB"""

    def __new__(cls):
        return ConnectionManager.get_instance()

    @classmethod
    def get_instance(cls):
        return ConnectionManager.get_instance()

    def get_database(self):
        return ConnectionManager.get_instance().get_mongo_database()

    @property
    def client(self):
        return ConnectionManager.get_instance().mongo_client

    @property
    def db(self):
        return ConnectionManager.get_instance().mongo_db

    @property
    def database_name(self):
        return ConnectionManager.get_instance().mongo_database_name

    async def close(self):
        await ConnectionManager.get_instance().close_mongo()

    async def ping(self):
        return await ConnectionManager.get_instance().mongo_ping()


class RedisConnectionManager:
    """Backward compatibility stub — Redis removed"""

    def __new__(cls):
        return ConnectionManager.get_instance()

    @classmethod
    def get_instance(cls):
        return ConnectionManager.get_instance()

    async def get_redis(self):
        return None

    async def close(self):
        pass


# Global instances for backward compatibility
mongo_connection = MongoConnectionManager()
redis_connection = RedisConnectionManager()
