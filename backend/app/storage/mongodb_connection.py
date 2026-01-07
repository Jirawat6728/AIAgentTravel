"""
MongoDB Connection Manager
Singleton pattern for MongoDB connection
"""

from __future__ import annotations
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
import os
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


class MongoConnectionManager:
    """
    Singleton MongoDB Connection Manager
    Manages single connection pool for the application
    """
    
    _instance: Optional['MongoConnectionManager'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def get_instance(cls) -> 'MongoConnectionManager':
        if cls._instance is None:
            cls._instance = MongoConnectionManager()
        return cls._instance

    def get_database(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database with auto-reconnect logic"""
        if self._client is None:
            self._init_connection()
        return self._db

    def _init_connection(self):
        """Initialize connection pool with robust timeouts"""
        connection_string = os.getenv(
            "MONGODB_URI",
            "mongodb://localhost:27017"
        )
        self.database_name = os.getenv(
            "MONGODB_DATABASE",
            "travel_agent"
        )
        
        # Use a single client with pool (Motor/PyMongo handles re-connections automatically)
        # Added specific timeouts to detect disconnects faster
        self._client = AsyncIOMotorClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000,
            heartbeatFrequencyMS=10000,
            retryWrites=True
        )
        self._db = self._client[self.database_name]
        logger.info(f"MongoDB Connection Pool initialized: database={self.database_name}")

    def __init__(self):
        if self._client is None:
            self._init_connection()
    
    @property
    def client(self) -> AsyncIOMotorClient:
        """Get MongoDB client"""
        if self._client is None:
            self.__init__()
        return self._client
    
    @property
    def db(self) -> AsyncIOMotorDatabase:
        """Get MongoDB database"""
        if self._db is None:
            self.__init__()
        return self._db
    
    async def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")
    
    async def ping(self):
        """Test MongoDB connection with short timeout"""
        try:
            # Use a very short timeout to detect disconnects quickly for the dashboard
            await asyncio.wait_for(
                self.client.admin.command('ping'),
                timeout=1.0
            )
            return True
        except Exception as e:
            logger.error(f"MongoDB ping failed: {str(e)}")
            return False


# Global connection instance
# (Maintaining for backward compatibility if needed, but get_instance() is preferred)
mongo_connection = MongoConnectionManager()

