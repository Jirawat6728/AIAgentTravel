"""เก็บเซสชัน แชท และข้อมูลอื่นใน MongoDB ตาม StorageInterface."""
from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import DuplicateKeyError

from app.storage.connection_manager import MongoConnectionManager
from app.storage.interface import StorageInterface
from app.models.session import UserSession
from app.models.database import (
    SessionDocument,
    TripDocument,
    SESSION_INDEXES,
    USER_INDEXES,
    MEMORY_INDEXES,
    BOOKING_INDEXES,
    CONVERSATION_INDEXES,
    SAVED_CARDS_INDEXES,
    WORKFLOW_HISTORY_INDEXES,
    RL_QTABLE_INDEXES,
    RL_REWARDS_INDEXES,
    TRIP_INDEXES,
)
from app.core.config import settings
from app.core.exceptions import StorageException
from app.core.logging import get_logger
# ✅ Lazy import to avoid circular dependency with resilience.py
# from app.core.resilience import retry_with_backoff
from pymongo.errors import ServerSelectionTimeoutError, NetworkTimeout, AutoReconnect

logger = get_logger(__name__)

# Retryable MongoDB exceptions
RETRYABLE_MONGO_EXCEPTIONS = (
    ServerSelectionTimeoutError,
    NetworkTimeout,
    AutoReconnect,
    ConnectionError
)


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
        try:
            self.database_name = self.connection_manager.database_name
            # Initialize references (may fail if MongoDB not available)
            self.db = self.connection_manager.db
        except Exception as e:
            logger.warning(f"MongoDB connection not available during MongoStorage.__init__: {e}")
            self.database_name = None
            self.db = None
        
        # ✅ FIX: Only initialize collections if db is not None
        if self.db is not None:
            self.sessions_collection = self.db["sessions"]
            self.users_collection = self.db["users"]
            self.memories_collection = self.db["memories"]
            self.bookings_collection = self.db["bookings"]
            self.conversations_collection = self.db["conversations"]
            self.saved_cards_collection = self.db["user_saved_cards"]
            self.trips_collection = self.db["trips"]
        else:
            self.sessions_collection = None
            self.users_collection = None
            self.memories_collection = None
            self.bookings_collection = None
            self.conversations_collection = None
            self.saved_cards_collection = None
            self.trips_collection = None
        
        logger.info(f"MongoStorage initialized with shared connection: database={self.database_name}")
    
    async def connect(self):
        """Setup indexes (Connection is managed by MongoConnectionManager)"""
        # ✅ Ensure database connection is valid before attempting index creation
        try:
            # Test database connection first
            if self.db is None:
                self.db = self.connection_manager.get_database()
            # Verify connection with ping (db is not None at this point)
            if self.db is not None:
                await self.db.command('ping')
            else:
                raise StorageException("MongoDB database is None")
        except Exception as e:
            logger.error(f"MongoDB connection not available: {e}", exc_info=True)
            raise StorageException(f"MongoDB connection failed: {e}") from e
        
        # Re-initialize collection references if needed (in case db was recreated)
        if self.db is not None and (not hasattr(self, 'bookings_collection') or self.bookings_collection is None):
            self.sessions_collection = self.db["sessions"]
            self.users_collection = self.db["users"]
            self.memories_collection = self.db["memories"]
            self.bookings_collection = self.db["bookings"]
            self.conversations_collection = self.db["conversations"]
            self.saved_cards_collection = self.db["user_saved_cards"]
            self.trips_collection = self.db["trips"]
        
        try:
            # Create indexes for all collections
            # ✅ SECURITY: Indexes ensure fast queries and data isolation by user_id
            # Note: Index creation is best-effort - if it fails, log but don't fail completely
            # ✅ Create indexes with better error handling for conflicts
            from pymongo.errors import OperationFailure
            
            async def create_indexes_safe(collection, indexes, collection_name):
                """Create indexes with conflict handling"""
                try:
                    await collection.create_indexes(indexes)
                    logger.debug(f"✅ Created indexes for {collection_name}")
                except OperationFailure as e:
                    # Check if it's an index conflict (code 85)
                    if e.code == 85:
                        logger.debug(f"Index already exists for {collection_name} (different name): {e.details.get('errmsg', '')}")
                        # Try to drop and recreate if needed, or just continue
                        # MongoDB will use existing index even if name differs
                    else:
                        logger.warning(f"Failed to create {collection_name} indexes: {e}")
                except Exception as idx_e:
                    logger.warning(f"Failed to create {collection_name} indexes (continuing anyway): {idx_e}")
            
            await create_indexes_safe(self.sessions_collection, SESSION_INDEXES, "sessions")
            await create_indexes_safe(self.users_collection, USER_INDEXES, "users")
            await create_indexes_safe(self.memories_collection, MEMORY_INDEXES, "memories")
            await create_indexes_safe(self.bookings_collection, BOOKING_INDEXES, "bookings")
            await create_indexes_safe(self.conversations_collection, CONVERSATION_INDEXES, "conversations")
            if hasattr(self, "saved_cards_collection") and self.saved_cards_collection is not None:
                await create_indexes_safe(self.saved_cards_collection, SAVED_CARDS_INDEXES, "user_saved_cards")
            workflow_history_coll = self.db["workflow_history"]
            await create_indexes_safe(workflow_history_coll, WORKFLOW_HISTORY_INDEXES, "workflow_history")
            pref_scores_coll = self.db["user_preference_scores"]
            await create_indexes_safe(pref_scores_coll, RL_QTABLE_INDEXES, "user_preference_scores")
            feedback_coll = self.db["user_feedback_history"]
            await create_indexes_safe(feedback_coll, RL_REWARDS_INDEXES, "user_feedback_history")
            trips_coll = self.db["trips"]
            await create_indexes_safe(trips_coll, TRIP_INDEXES, "trips")

            logger.info("MongoDB indexes verified via shared connection (including user_id indexes for data isolation)")
        except Exception as e:
            logger.error(f"Failed to setup MongoDB indexes: {e}", exc_info=True)
            # Don't raise exception - allow connection to work even if indexes fail
            # Indexes can be created later, connection is more important
    
    async def disconnect(self):
        """Disconnect is managed globally"""
        pass
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get session from MongoDB (async, non-blocking)
        Creates new session if doesn't exist
        ✅ SECURITY: Only returns session if session_id matches exactly
        """
        # Ensure collection is valid (handles re-init if manager was reset)
        if self.sessions_collection is None:
            self.db = self.connection_manager.get_database()
            self.sessions_collection = self.db["sessions"]

        # ✅ SECURITY: Extract expected user_id from session_id (CRITICAL for privacy)
        expected_user_id = session_id.split("::")[0] if "::" in session_id else session_id
        
        try:
            # ✅ SECURITY: Query by session_id (session_id format: user_id::chat_id ensures user isolation)
            # Note: session_id itself contains user_id, providing natural isolation
            async def _find_session():
                return await self.sessions_collection.find_one({"session_id": session_id})
            
            # ✅ Lazy import to avoid circular dependency
            from app.core.resilience import retry_with_backoff
            doc = await retry_with_backoff(
                _find_session,
                max_retries=2,
                initial_delay=0.5,
                exceptions=RETRYABLE_MONGO_EXCEPTIONS
            )
            
            if not doc:
                logger.info(f"Session not found for {session_id}, creating new session")
                # Extract user_id from session_id (format: user_id::conversation_id)
                user_id = expected_user_id
                session = UserSession(session_id=session_id, user_id=user_id)
                await self.save_session(session)
                return session
            
            # ✅ SECURITY: CRITICAL - Verify user_id matches session_id to prevent data leakage
            doc_user_id = doc.get("user_id")
            if not doc_user_id:
                logger.error(f"🚨 SECURITY ALERT: Session {session_id} has no user_id field! This is a data integrity issue.")
                # Create new session with correct user_id instead of returning corrupted data
                user_id = expected_user_id
                session = UserSession(session_id=session_id, user_id=user_id)
                await self.save_session(session)
                return session
            
            if doc_user_id != expected_user_id:
                logger.error(f"🚨 SECURITY ALERT: Session {session_id} user_id mismatch - expected {expected_user_id}, found {doc_user_id}. Preventing data leakage by creating new session.")
                # Return new session instead of mismatched data to prevent data leakage
                user_id = expected_user_id
                session = UserSession(session_id=session_id, user_id=user_id)
                await self.save_session(session)
                return session
            
            # Convert document to UserSession
            session_doc = SessionDocument(**doc)
            session = session_doc.to_user_session()

            # ✅ Load trip_plan from trips collection (single source of truth)
            if session.trip_id:
                try:
                    from app.models.trip_plan import TripPlan
                    trip_doc = await self.get_trip(session.trip_id, session.user_id)
                    if trip_doc and trip_doc.get("trip_plan"):
                        session.trip_plan = TripPlan(**trip_doc["trip_plan"])
                        logger.debug(f"Loaded trip_plan from trips collection: trip_id={session.trip_id}")
                except Exception as trip_load_err:
                    logger.warning(f"Could not load trip_plan from trips collection, using embedded: {trip_load_err}")

            logger.debug(f"Loaded session {session_id} from MongoDB")
            return session
        
        except Exception as e:
            logger.error(f"Error loading session {session_id}: {e}", exc_info=True)
            raise StorageException(f"Failed to load session {session_id}: {e}") from e
    
    async def save_session(self, session: UserSession) -> bool:
        """
        Save session to MongoDB (async, non-blocking)
        ✅ SECURITY: Ensures user_id in session matches session_id format
        
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
            # ✅ SECURITY: Verify user_id matches session_id format
            expected_user_id = session.session_id.split("::")[0] if "::" in session.session_id else session.session_id
            if session.user_id != expected_user_id:
                logger.warning(f"Session user_id mismatch: session_id={session.session_id}, user_id={session.user_id}, expected={expected_user_id}")
                # Fix user_id to match session_id
                session.user_id = expected_user_id
            
            session.update_timestamp()
            
            # ✅ CRITICAL: Verify trip_plan exists and can be serialized before creating SessionDocument
            trip_plan_dict = None
            if hasattr(session, 'trip_plan') and session.trip_plan:
                try:
                    trip_plan_dict = session.trip_plan.model_dump()
                    
                    # Count confirmed segments with selected_option for logging
                    confirmed_count = 0
                    options_pool_count = 0
                    all_segments = (
                        trip_plan_dict.get("travel", {}).get("flights", {}).get("outbound", []) +
                        trip_plan_dict.get("travel", {}).get("flights", {}).get("inbound", []) +
                        trip_plan_dict.get("accommodation", {}).get("segments", []) +
                        trip_plan_dict.get("travel", {}).get("ground_transport", [])
                    )
                    for seg in all_segments:
                        if seg.get("status") == "confirmed" and seg.get("selected_option"):
                            confirmed_count += 1
                        if seg.get("options_pool") and len(seg.get("options_pool", [])) > 0:
                            options_pool_count += len(seg.get("options_pool", []))
                    
                    if confirmed_count > 0 or options_pool_count > 0:
                        logger.info(f"Session trip_plan data: {confirmed_count} confirmed segments with selected_option, {options_pool_count} options in pools: session_id={session.session_id}")
                except Exception as e:
                    logger.error(f"Error serializing trip_plan for session {session.session_id}: {e}", exc_info=True)
                    # Continue anyway - SessionDocument.from_user_session will handle it
            
            session_doc = SessionDocument.from_user_session(session)
            
            # Convert to dict for MongoDB
            doc_dict = session_doc.model_dump(by_alias=True, exclude={"id"})
            
            # ✅ SECURITY: Ensure user_id is set correctly in document
            doc_dict["user_id"] = expected_user_id
            
            # ✅ CRITICAL: Double-check trip_plan is in dict and contains all raw data
            # Verify that trip_plan includes options_pool and selected_option
            if "trip_plan" in doc_dict and doc_dict["trip_plan"]:
                # Verify that raw data (options_pool, selected_option) is present
                trip_plan_in_dict = doc_dict["trip_plan"]
                segments_to_check = (
                    trip_plan_in_dict.get("travel", {}).get("flights", {}).get("outbound", []) +
                    trip_plan_in_dict.get("travel", {}).get("flights", {}).get("inbound", []) +
                    trip_plan_in_dict.get("accommodation", {}).get("segments", []) +
                    trip_plan_in_dict.get("travel", {}).get("ground_transport", [])
                )
                
                has_raw_data = False
                for seg in segments_to_check:
                    if seg.get("options_pool") or seg.get("selected_option"):
                        has_raw_data = True
                        break
                
                if has_raw_data:
                    logger.debug(f"trip_plan contains raw data (options_pool/selected_option): session_id={session.session_id}")
            else:
                logger.warning(f"trip_plan missing in doc_dict for session {session.session_id}, attempting to add from session")
                if trip_plan_dict:
                    doc_dict["trip_plan"] = trip_plan_dict
                elif hasattr(session, 'trip_plan') and session.trip_plan:
                    try:
                        doc_dict["trip_plan"] = session.trip_plan.model_dump()
                        logger.info(f"Added trip_plan to doc_dict from session object: session_id={session.session_id}")
                    except Exception as e:
                        logger.error(f"Failed to add trip_plan to doc_dict: {e}", exc_info=True)
            
            # Upsert session
            result = await self.sessions_collection.update_one(
                {"session_id": session.session_id},
                {"$set": doc_dict},
                upsert=True
            )

            # ✅ Sync trip_plan to trips collection (source of truth for shared trips)
            if session.trip_id and trip_plan_dict:
                try:
                    await self.save_trip(
                        trip_id=session.trip_id,
                        user_id=expected_user_id,
                        trip_plan=trip_plan_dict,
                        title=session.title,
                    )
                except Exception as trip_sync_err:
                    logger.warning(f"Could not sync trip_plan to trips collection: {trip_sync_err}")

            if result.upserted_id or result.modified_count > 0:
                logger.debug(f"Saved session {session.session_id} to MongoDB with user_id={expected_user_id}, trip_plan included")
            else:
                logger.warning(f"Session save may have failed: session_id={session.session_id}, matched={result.matched_count}, modified={result.modified_count}")
            
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

    async def save_message(self, session_id: str, message: dict) -> bool:
        """
        Save a chat message to conversation history (idempotent).
        Uses content+role fingerprint to prevent duplicate messages from
        being pushed when the same request is retried or SSE reconnects.
        """
        if self.sessions_collection is None:
            await self.connect()
            
        try:
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow()
                
            conversations = self.db["conversations"]
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            
            existing_conv = await conversations.find_one({"session_id": session_id})
            if existing_conv:
                existing_user_id = existing_conv.get("user_id")
                if existing_user_id and existing_user_id != user_id:
                    logger.warning(f"Attempted to save message to conversation with mismatched user_id: session_id={session_id}")
                    return False

                # Idempotent guard: skip if an identical message was pushed recently
                existing_msgs = existing_conv.get("messages") or []
                if existing_msgs:
                    last = existing_msgs[-1]
                    same_role = last.get("role") == message.get("role")
                    same_text = (last.get("content") or "")[:200] == (message.get("content") or "")[:200]
                    if same_role and same_text:
                        logger.debug(f"Idempotent skip: duplicate message for session_id={session_id}")
                        return True
            
            update_op = {
                "$push": {"messages": message},
                "$setOnInsert": {
                    "session_id": session_id,
                    "user_id": user_id,
                    "created_at": datetime.utcnow()
                },
                "$set": {
                    "updated_at": datetime.utcnow()
                }
            }
            
            result = await conversations.update_one(
                {"session_id": session_id},
                update_op,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                logger.debug(f"Message saved to MongoDB: session_id={session_id}, user_id={user_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error saving message for {session_id}: {e}", exc_info=True)
            return False

    async def get_chat_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """
        Get chat history for a session
        ✅ SECURITY: Only returns history for the exact session_id AND user_id provided
        """
        if self.sessions_collection is None:
            await self.connect()
            
        try:
            conversations = self.db["conversations"]
            
            # ✅ SECURITY: Extract user_id from session_id (format: user_id::chat_id)
            user_id_from_session = session_id.split("::")[0] if "::" in session_id else None
            
            # ✅ SECURITY: Query by BOTH session_id AND user_id to prevent data leakage
            query_filter = {"session_id": session_id}
            if user_id_from_session:
                query_filter["user_id"] = user_id_from_session
            
            doc = await conversations.find_one(query_filter)
            
            if not doc or "messages" not in doc:
                return []
            
            # ✅ SECURITY: Double-check user_id matches (additional safety check)
            doc_user_id = doc.get("user_id")
            if user_id_from_session and doc_user_id and user_id_from_session != doc_user_id:
                logger.error(f"🚨 SECURITY ALERT: Session {session_id} user_id mismatch! session has {user_id_from_session}, doc has {doc_user_id}")
                return []  # Return empty to prevent data leakage
            
            messages = doc["messages"]
            # Return last N messages
            return messages[-limit:]
        except Exception as e:
            logger.error(f"Error getting history for {session_id}: {e}", exc_info=True)
            return []

    async def get_chat_history_by_chat_id(self, chat_id: str, user_id: str, limit: int = 50) -> list:
        """
        Fallback: ดึงประวัติจาก conversation ที่ session_id เก็บเป็นแค่ chat_id (รูปแบบเก่า)
        หรือ session_id จบด้วย ::chat_id — ใช้เมื่อ get_chat_history(session_id) ไม่เจอ
        """
        if self.sessions_collection is None:
            await self.connect()
        try:
            conversations = self.db["conversations"]
            # รูปแบบเก่า: session_id = chat_id อย่างเดียว และ user_id ตรง
            doc = await conversations.find_one({"session_id": chat_id, "user_id": user_id})
            if doc and doc.get("messages"):
                return doc["messages"][-limit:]
            # หรือ session_id จบด้วย ::chat_id (กรณีมี prefix อื่น)
            import re
            safe_chat_id = re.escape(chat_id)
            doc = await conversations.find_one(
                {"session_id": {"$regex": f"::{safe_chat_id}$"}, "user_id": user_id}
            )
            if doc and doc.get("messages"):
                return doc["messages"][-limit:]
            return []
        except Exception as e:
            logger.error(f"Error get_chat_history_by_chat_id chat_id={chat_id}: {e}", exc_info=True)
            return []

    async def clear_session_data(self, session_id: str) -> bool:
        """
        Clear session data (trip plan) from MongoDB
        """
        try:
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            new_session = UserSession(session_id=session_id, user_id=user_id)
            return await self.save_session(new_session)
        except Exception as e:
            logger.error(f"Error clearing session data: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """
        ✅ Health check method to verify MongoDB connection
        
        Returns:
            Dictionary with health status:
            {
                "status": "healthy" | "unhealthy" | "degraded",
                "message": str,
                "database": str,
                "collections": list
            }
        """
        from typing import Dict, Any
        
        try:
            # Ensure connection is valid
            if self.db is None:
                self.db = self.connection_manager.get_database()
            
            if self.db is None:
                return {
                    "status": "unhealthy",
                    "message": "MongoDB database is None",
                    "database": None,
                    "collections": []
                }
            
            # Test connection with ping
            await self.db.command('ping')
            
            # Get database name
            database_name = self.db.name
            
            # List collections (best-effort)
            collections = []
            try:
                collection_names = await self.db.list_collection_names()
                collections = collection_names[:10]  # Limit to 10 for response size
            except Exception as e:
                logger.warning(f"Failed to list collections: {e}")
            
            return {
                "status": "healthy",
                "message": "MongoDB connection verified",
                "database": database_name,
                "collections": collections
            }
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}", exc_info=True)
            return {
                "status": "unhealthy",
                "message": f"MongoDB connection failed: {str(e)[:200]}",
                "database": None,
                "collections": []
            }

    # =========================================================================
    # Trip CRUD — trips are the single source of truth for TripPlan
    # Multiple chats can share a trip by referencing the same trip_id.
    # =========================================================================

    async def _ensure_trips_collection(self):
        if self.trips_collection is None:
            if self.db is None:
                self.db = self.connection_manager.get_database()
            self.trips_collection = self.db["trips"]

    async def get_trip(self, trip_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Load a trip document.  Returns the raw dict (with trip_plan) or None."""
        await self._ensure_trips_collection()
        try:
            doc = await self.trips_collection.find_one({"trip_id": trip_id, "user_id": user_id})
            return doc
        except Exception as e:
            logger.error(f"get_trip error trip_id={trip_id}: {e}", exc_info=True)
            return None

    async def save_trip(
        self,
        trip_id: str,
        user_id: str,
        trip_plan: Dict[str, Any],
        title: Optional[str] = None,
        status: Optional[str] = None,
        booking_ids: Optional[list] = None,
    ) -> bool:
        """Upsert a trip document.  Creates if not present."""
        await self._ensure_trips_collection()
        try:
            now = datetime.utcnow()
            update: Dict[str, Any] = {
                "trip_id": trip_id,
                "user_id": user_id,
                "trip_plan": trip_plan,
                "last_updated": now,
            }
            if title is not None:
                update["title"] = title
            if status is not None:
                update["status"] = status
            if booking_ids is not None:
                update["booking_ids"] = booking_ids

            await self.trips_collection.update_one(
                {"trip_id": trip_id, "user_id": user_id},
                {"$set": update, "$setOnInsert": {"created_at": now}},
                upsert=True,
            )
            return True
        except Exception as e:
            logger.error(f"save_trip error trip_id={trip_id}: {e}", exc_info=True)
            return False

    async def create_trip(self, user_id: str, title: str = "ทริปใหม่") -> str:
        """Create a brand-new trip entity.  Returns the new trip_id."""
        import uuid
        trip_id = f"trip_{uuid.uuid4().hex[:16]}"
        await self.save_trip(trip_id, user_id, trip_plan={}, title=title, status="planning")
        return trip_id

    async def list_trips(self, user_id: str, limit: int = 50) -> list:
        """Return all trips for a user, sorted by last_updated desc.
        Falls back to sessions collection if trips collection is empty (migration path).
        """
        await self._ensure_trips_collection()
        try:
            cursor = self.trips_collection.find(
                {"user_id": user_id}
            ).sort("last_updated", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            # Migration fallback: if no trips yet, synthesise from sessions
            if not docs:
                docs = await self._synthesise_trips_from_sessions(user_id, limit)
            return docs
        except Exception as e:
            logger.error(f"list_trips error user_id={user_id}: {e}", exc_info=True)
            return []

    async def _synthesise_trips_from_sessions(self, user_id: str, limit: int) -> list:
        """One-time migration helper: build trip records from existing session data."""
        try:
            if self.sessions_collection is None:
                return []
            cursor = self.sessions_collection.find(
                {"user_id": user_id}
            ).sort("last_updated", -1).limit(limit)
            session_docs = await cursor.to_list(length=limit)
            trips = []
            for doc in session_docs:
                trip_id = doc.get("trip_id") or doc.get("chat_id") or doc.get("session_id", "").split("::")[-1]
                if not trip_id:
                    continue
                trips.append({
                    "trip_id": trip_id,
                    "user_id": user_id,
                    "title": doc.get("title") or "ทริปใหม่",
                    "status": "planning",
                    "booking_ids": [],
                    "trip_plan": doc.get("trip_plan", {}),
                    "created_at": doc.get("created_at"),
                    "last_updated": doc.get("last_updated"),
                    "_from_session": True,
                })
            return trips
        except Exception as e:
            logger.warning(f"_synthesise_trips_from_sessions: {e}")
            return []

    async def delete_trip(self, trip_id: str, user_id: str) -> bool:
        """Delete trip document.  Sessions that linked to it retain their history
        but their trip_id is cleared so they become independent."""
        await self._ensure_trips_collection()
        try:
            result = await self.trips_collection.delete_one({"trip_id": trip_id, "user_id": user_id})
            # Unlink sessions that were pointing at this trip
            if self.sessions_collection is not None:
                await self.sessions_collection.update_many(
                    {"trip_id": trip_id, "user_id": user_id},
                    {"$set": {"trip_id": None}},
                )
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"delete_trip error trip_id={trip_id}: {e}", exc_info=True)
            return False

    async def link_chat_to_trip(self, session_id: str, trip_id: str, user_id: str) -> bool:
        """Link an existing chat session to a different trip."""
        if self.sessions_collection is None:
            await self.connect()
        try:
            result = await self.sessions_collection.update_one(
                {"session_id": session_id, "user_id": user_id},
                {"$set": {"trip_id": trip_id}},
            )
            return result.matched_count > 0
        except Exception as e:
            logger.error(f"link_chat_to_trip error: {e}", exc_info=True)
            return False
