"""
MongoDB Storage Implementation
Production-grade async MongoDB storage with connection pooling
"""

from __future__ import annotations
from typing import Optional
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from app.storage.mongodb_connection import MongoConnectionManager
from app.storage.interface import StorageInterface
from app.models.session import UserSession
from app.models.database import SessionDocument, SESSION_INDEXES, USER_INDEXES, MEMORY_INDEXES
from app.core.config import settings
from app.core.exceptions import StorageException
from app.core.logging import get_logger

logger = get_logger(__name__)


class MongoStorage(StorageInterface):
    """
    MongoDB Storage Implementation
    Uses MongoConnectionManager for shared connection pool
    """
    
    def __init__(self):
        """
        Initialize MongoDB Storage
        """
        self.connection_manager = MongoConnectionManager.get_instance()
        self.database_name = self.connection_manager.database_name
        
        # Initialize references
        self.db = self.connection_manager.db
        self.sessions_collection = self.db["sessions"]
        self.users_collection = self.db["users"]
        self.memories_collection = self.db["memories"]
        
        logger.info(f"MongoStorage initialized with shared connection: database={self.database_name}")
    
    async def connect(self):
        """Setup indexes (Connection is managed by MongoConnectionManager)"""
        try:
            # Create indexes
            await self.sessions_collection.create_indexes(SESSION_INDEXES)
            await self.users_collection.create_indexes(USER_INDEXES)
            await self.memories_collection.create_indexes(MEMORY_INDEXES)
            
            logger.info("MongoDB indexes verified via shared connection")
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}", exc_info=True)
            raise StorageException(f"MongoDB index setup failed: {e}") from e
    
    async def disconnect(self):
        """Disconnect is managed globally"""
        pass
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session from MongoDB (async, non-blocking)
        Creates new session if doesn't exist
        """
        # Ensure collection is valid (handles re-init if manager was reset)
        if self.sessions_collection is None:
            self.db = self.connection_manager.get_database()
            self.sessions_collection = self.db["sessions"]

        try:
            # Find session with retry logic handled by Motor
            doc = await self.sessions_collection.find_one({"session_id": session_id})
            
            if not doc:
                logger.info(f"Session not found for {session_id}, creating new session")
                # Extract user_id from session_id (format: user_id::conversation_id)
                user_id = session_id.split("::")[0] if "::" in session_id else session_id
                session = UserSession(session_id=session_id, user_id=user_id)
                await self.save_session(session)
                return session
            
            # Convert document to UserSession
            session_doc = SessionDocument(**doc)
            session = session_doc.to_user_session()
            
            logger.debug(f"Loaded session {session_id} from MongoDB")
            return session
        
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to load session {session_id}: {e}") from e
    
    async def save_session(self, session: UserSession) -> bool:
        """
        Save session to MongoDB (async, non-blocking)
        
        Args:
            session: UserSession object to save
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If database operation fails
        """
        if self.sessions_collection is None:
            await self.connect()
        
        try:
            session.update_timestamp()
            session_doc = SessionDocument.from_user_session(session)
            
            # Convert to dict for MongoDB
            doc_dict = session_doc.model_dump(by_alias=True, exclude={"id"})
            
            # Upsert session
            await self.sessions_collection.update_one(
                {"session_id": session.session_id},
                {"$set": doc_dict},
                upsert=True
            )
            
            logger.debug(f"Saved session {session.session_id} to MongoDB")
            return True
        
        except DuplicateKeyError as e:
            logger.error(f"Duplicate key error saving session {session.session_id}: {e}")
            raise StorageException(f"Duplicate session_id: {session.session_id}") from e
        except Exception as e:
            logger.error(f"Error saving session {session.session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to save session {session.session_id}: {e}") from e
    
    async def update_title(self, session_id: str, title: str) -> bool:
        """
        Update session title (async, non-blocking)
        
        Args:
            session_id: Session identifier
            title: New title to set
            
        Returns:
            True if successful
            
        Raises:
            StorageException: If update fails
        """
        if self.sessions_collection is None:
            await self.connect()
        
        try:
            result = await self.sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "title": title,
                        "last_updated": datetime.utcnow()
                    }
                }
            )
            
            if result.matched_count == 0:
                logger.error(f"Session not found for title update: {session_id}")
                raise StorageException(f"Session not found: {session_id}")
            
            logger.info(f"Updated title for session {session_id}: {title}")
            return True
        
        except StorageException:
            raise
        except Exception as e:
            logger.error(f"Error updating title for session {session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to update title for session {session_id}: {e}") from e

