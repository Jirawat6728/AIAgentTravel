"""
Sessions Repository
Handles user session data access with full CRUD operations
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import motor.motor_asyncio
from bson import ObjectId


class SessionsRepo:
    """Repository for session operations with full CRUD support"""
    
    def __init__(self, db: motor.motor_asyncio.AsyncIOMotorDatabase):
        self.db = db
        self.collection = db.sessions
    
    async def ensure_indexes(self):
        """Create indexes for better query performance"""
        try:
            await self.collection.create_index("user_id")
            await self.collection.create_index("session_token", unique=True)
            await self.collection.create_index("expires_at")
            await self.collection.create_index([("user_id", 1), ("expires_at", 1)])
            # TTL index to auto-delete expired sessions
            await self.collection.create_index("expires_at", expireAfterSeconds=0)
        except Exception as e:
            import logging
            logging.warning(f"Failed to create indexes: {e}")
    
    # ===== CREATE =====
    async def create(
        self,
        user_id: str,
        session_token: str,
        expires_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a new session
        
        Args:
            user_id: User ID
            session_token: Session token (JWT or session ID)
            expires_at: Expiration datetime (default: 7 days from now)
            metadata: Optional session metadata
        
        Returns:
            Created session document with _id as string
        """
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(days=7)
        
        session_data = {
            "user_id": user_id,
            "session_token": session_token,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        if metadata:
            session_data["metadata"] = metadata
        
        result = await self.collection.insert_one(session_data)
        session_id = str(result.inserted_id)
        
        # Return created session
        session = await self.get_by_id(session_id)
        return session
    
    # ===== READ =====
    async def get_by_id(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by ID
        
        Args:
            session_id: Session ID (string)
        
        Returns:
            Session document or None if not found
        """
        try:
            session = await self.collection.find_one({"_id": ObjectId(session_id)})
            if session and "_id" in session:
                session["_id"] = str(session["_id"])
            return session
        except Exception:
            return None
    
    async def get_by_token(self, session_token: str) -> Optional[Dict[str, Any]]:
        """
        Get session by token
        
        Args:
            session_token: Session token
        
        Returns:
            Session document or None if not found
        """
        session = await self.collection.find_one({"session_token": session_token})
        if session and "_id" in session:
            session["_id"] = str(session["_id"])
        return session
    
    async def get_by_user(
        self,
        user_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get sessions by user ID
        
        Args:
            user_id: User ID
            limit: Maximum number of results (default: 10)
            skip: Number of results to skip (default: 0)
        
        Returns:
            List of session documents
        """
        cursor = self.collection.find({"user_id": user_id}).sort("created_at", -1).skip(skip).limit(limit)
        sessions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for session in sessions:
            if "_id" in session:
                session["_id"] = str(session["_id"])
        
        return sessions
    
    async def get_active_sessions(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get active (non-expired) sessions
        
        Args:
            user_id: Optional user ID filter
            limit: Maximum number of results (default: 100)
        
        Returns:
            List of active session documents
        """
        query = {"expires_at": {"$gt": datetime.utcnow()}}
        if user_id:
            query["user_id"] = user_id
        
        cursor = self.collection.find(query).sort("created_at", -1).limit(limit)
        sessions = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string
        for session in sessions:
            if "_id" in session:
                session["_id"] = str(session["_id"])
        
        return sessions
    
    async def count(
        self,
        user_id: Optional[str] = None,
        active_only: bool = False
    ) -> int:
        """
        Count sessions
        
        Args:
            user_id: Optional user ID filter
            active_only: If True, only count non-expired sessions
        
        Returns:
            Number of sessions matching the criteria
        """
        query = {}
        if user_id:
            query["user_id"] = user_id
        if active_only:
            query["expires_at"] = {"$gt": datetime.utcnow()}
        
        return await self.collection.count_documents(query)
    
    # ===== UPDATE =====
    async def update(
        self,
        session_id: str,
        updates: Dict[str, Any],
        partial: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Update a session
        
        Args:
            session_id: Session ID
            updates: Dictionary of fields to update
            partial: If True, use $set (partial update). If False, replace entire document.
        
        Returns:
            Updated session document or None if not found
        """
        try:
            # Add updated_at timestamp
            updates["updated_at"] = datetime.utcnow()
            
            if partial:
                result = await self.collection.update_one(
                    {"_id": ObjectId(session_id)},
                    {"$set": updates}
                )
            else:
                # Replace entire document
                updates["_id"] = ObjectId(session_id)
                result = await self.collection.replace_one(
                    {"_id": ObjectId(session_id)},
                    updates
                )
            
            if result.modified_count > 0:
                return await self.get_by_id(session_id)
            return None
        except Exception as e:
            import logging
            logging.error(f"Failed to update session {session_id}: {e}")
            return None
    
    async def extend_expiry(
        self,
        session_id: str,
        days: int = 7
    ) -> bool:
        """
        Extend session expiry
        
        Args:
            session_id: Session ID
            days: Number of days to extend (default: 7)
        
        Returns:
            True if updated successfully, False otherwise
        """
        new_expires_at = datetime.utcnow() + timedelta(days=days)
        result = await self.update(session_id, {"expires_at": new_expires_at})
        return result is not None
    
    # ===== DELETE =====
    async def delete(self, session_id: str) -> bool:
        """
        Delete a session
        
        Args:
            session_id: Session ID
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = await self.collection.delete_one({"_id": ObjectId(session_id)})
            return result.deleted_count > 0
        except Exception as e:
            import logging
            logging.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def delete_by_token(self, session_token: str) -> bool:
        """
        Delete a session by token
        
        Args:
            session_token: Session token
        
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            result = await self.collection.delete_one({"session_token": session_token})
            return result.deleted_count > 0
        except Exception as e:
            import logging
            logging.error(f"Failed to delete session by token: {e}")
            return False
    
    async def delete_by_user(self, user_id: str) -> int:
        """
        Delete all sessions for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Number of sessions deleted
        """
        result = await self.collection.delete_many({"user_id": user_id})
        return result.deleted_count
    
    async def delete_expired(self) -> int:
        """
        Delete all expired sessions
        
        Returns:
            Number of sessions deleted
        """
        result = await self.collection.delete_many({"expires_at": {"$lt": datetime.utcnow()}})
        return result.deleted_count

