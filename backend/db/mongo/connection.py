"""
MongoDB connection module
Handles MongoDB connection and provides database access
"""

from __future__ import annotations
from typing import Optional
import motor.motor_asyncio
from core.config import MONGODB_URL, MONGODB_DB_NAME

# Global MongoDB client
_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None


async def connect_to_mongo():
    """Connect to MongoDB"""
    global _client, _db
    
    if not MONGODB_URL:
        import logging
        logging.warning("MONGODB_URL not configured, skipping MongoDB connection")
        # ✅ Don't raise error, just skip - system can work without MongoDB
        return
    
    try:
        _client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
        _db = _client[MONGODB_DB_NAME or "travel_agent"]
        
        # Test connection
        await _client.admin.command('ping')
        
        import logging
        logging.info(f"Connected to MongoDB: {MONGODB_DB_NAME}")
    except Exception as e:
        import logging
        logging.warning(f"Failed to connect to MongoDB: {e} - continuing without MongoDB")
        # ✅ Don't raise error, just set to None - system can work without MongoDB
        _client = None
        _db = None


async def close_mongo():
    """Close MongoDB connection"""
    global _client, _db
    
    if _client:
        _client.close()
        _client = None
        _db = None
        
        import logging
        logging.info("MongoDB connection closed")


def get_db() -> Optional[motor.motor_asyncio.AsyncIOMotorDatabase]:
    """
    Get MongoDB database instance
    Returns None if not connected
    """
    return _db

