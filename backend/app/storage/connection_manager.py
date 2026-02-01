"""
ตัวจัดการการเชื่อมต่อแบบรวม
จัดการการเชื่อมต่อ MongoDB และ Redis แบบ singleton
"""

from __future__ import annotations
from typing import Optional
import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import redis.asyncio as redis
from redis import exceptions as redis_exceptions

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """
    Unified Connection Manager for MongoDB and Redis
    Singleton pattern for shared connection pools
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
        """Initialize connection manager"""
        # MongoDB
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._mongo_db: Optional[AsyncIOMotorDatabase] = None
        self.mongo_database_name: Optional[str] = None
        
        # Redis
        self._redis_client: Optional[redis.Redis] = None
    
    # =============================================================================
    # MongoDB Methods
    # =============================================================================
    
    def get_mongo_database(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database with auto-reconnect logic"""
        if self._mongo_client is None:
            self._init_mongo_connection()
        return self._mongo_db

    def get_database(self) -> AsyncIOMotorDatabase:
        """Alias for get_mongo_database for backward compatibility"""
        return self.get_mongo_database()
    
    def _init_mongo_connection(self):
        """Initialize MongoDB connection pool with robust timeouts"""
        connection_string = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.mongo_database_name = os.getenv("MONGODB_DATABASE", "travel_agent")
        
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
        """Get MongoDB client"""
        if self._mongo_client is None:
            self._init_mongo_connection()
        return self._mongo_client

    @property
    def client(self) -> AsyncIOMotorClient:
        """Alias for mongo_client for backward compatibility"""
        return self.mongo_client

    @property
    def mongo_db(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database"""
        if self._mongo_db is None:
            self._init_mongo_connection()
        return self._mongo_db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Alias for mongo_db for backward compatibility"""
        return self.mongo_db

    @property
    def database_name(self) -> str:
        """Alias for mongo_database_name for backward compatibility"""
        if self.mongo_database_name is None:
            self._init_mongo_connection()
        return self.mongo_database_name
    
    async def mongo_ping(self) -> bool:
        """Test MongoDB connection with short timeout"""
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
            # Try to reconnect
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
    
    # =============================================================================
    # Redis Methods
    # =============================================================================
    
    def _init_redis_connection(self):
        """Initialize Redis connection with robust pool settings"""
        try:
            self._redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True,
                max_connections=50,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
                retry_on_error=[redis_exceptions.ConnectionError, redis_exceptions.TimeoutError],
            )
            logger.info(f"Redis connection initialized: {settings.redis_host}:{settings.redis_port}")
        except Exception as e:
            logger.error(f"Failed to initialize Redis connection: {e}")
            raise
    
    async def get_redis(self) -> Optional[redis.Redis]:
        """Get Redis client with auto-reconnect (returns None if unavailable)"""
        # If Redis was marked as unavailable, don't keep trying
        if hasattr(self, '_redis_unavailable') and self._redis_unavailable:
            return None
        
        if self._redis_client is None:
            try:
                self._init_redis_connection()
            except Exception as e:
                logger.debug(f"Redis initialization failed: {e}")
                self._redis_unavailable = True
                return None
        
        # Test connection (with short timeout to avoid blocking)
        try:
            await asyncio.wait_for(self._redis_client.ping(), timeout=0.5)
            # Reset unavailable flag if connection works
            if hasattr(self, '_redis_unavailable'):
                self._redis_unavailable = False
        except Exception as e:
            # Only log warning on first failure, then mark as unavailable
            if not hasattr(self, '_redis_unavailable') or not self._redis_unavailable:
                logger.debug(f"Redis connection test failed: {e}")
                self._redis_unavailable = True
            return None
                
        return self._redis_client
    
    async def close_redis(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None
            logger.info("Redis connection closed")
    
    # =============================================================================
    # Unified Methods
    # =============================================================================
    
    async def close_all(self):
        """Close all connections"""
        await self.close_mongo()
        await self.close_redis()


# Backward compatibility aliases
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
    """Backward compatibility wrapper for Redis"""
    
    def __new__(cls):
        return ConnectionManager.get_instance()
    
    @classmethod
    def get_instance(cls):
        return ConnectionManager.get_instance()
    
    async def get_redis(self):
        return await ConnectionManager.get_instance().get_redis()
    
    async def close(self):
        await ConnectionManager.get_instance().close_redis()


# Global instances for backward compatibility
mongo_connection = MongoConnectionManager()
redis_connection = RedisConnectionManager()
