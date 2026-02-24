"""
Memory Sync Service (MongoDB-only)
ซิงค์ข้อมูลจาก MongoDB ไปยัง long-term memory (memories collection)
Redis ถูกลบออกแล้ว — ใช้ MongoDB 100%
"""

import asyncio
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.services.memory import MemoryService
from app.models.session import UserSession
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisSyncService:
    """
    Memory Sync Service (renamed kept for backward compatibility)
    Syncs important trip/chat data from MongoDB to long-term memories collection.
    Redis is no longer used.
    """
    
    def __init__(self):
        self.memory_service = MemoryService()
        self.is_running = False
    
    async def sync_session_to_long_term_memory(self, session_id: str) -> bool:
        """
        Extract important information from a session (MongoDB) and sync to long-term memory.
        """
        try:
            from app.storage.mongodb_storage import MongoStorage
            mongo = MongoStorage()
            session = await mongo.get_session(session_id)
            
            if not session:
                logger.debug(f"Session {session_id} not found in MongoDB")
                return False
            
            user_id = session.user_id
            trip_summary = self._extract_trip_summary(session)
            
            if trip_summary:
                await self._consolidate_trip_to_memory(user_id, session_id, trip_summary)
                logger.debug(f"Synced session {session_id} to long-term memory for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error syncing session {session_id} to long-term memory: {e}")
            return False
    
    def _extract_trip_summary(self, session: UserSession) -> Optional[str]:
        try:
            trip_plan = session.trip_plan
            if not trip_plan:
                return None
            
            summary_parts = []
            
            travel = trip_plan.travel if hasattr(trip_plan, 'travel') else {}
            flights = travel.get('flights', {}) if isinstance(travel, dict) else {}
            
            outbound = flights.get('outbound', []) if isinstance(flights, dict) else []
            inbound = flights.get('inbound', []) if isinstance(flights, dict) else []
            
            if outbound or inbound:
                summary_parts.append("การเดินทาง: มีการค้นหาเที่ยวบิน")
                for segment in (outbound + inbound):
                    if isinstance(segment, dict):
                        selected = segment.get('selected_option')
                        if selected:
                            summary_parts.append(
                                f"เลือกเที่ยวบิน: {selected.get('airline', '')} "
                                f"จาก {selected.get('origin', '')} ไป {selected.get('destination', '')}"
                            )
            
            accommodation = trip_plan.accommodation if hasattr(trip_plan, 'accommodation') else {}
            segments = accommodation.get('segments', []) if isinstance(accommodation, dict) else []
            
            if segments:
                summary_parts.append("ที่พัก: มีการค้นหาที่พัก")
                for segment in segments:
                    if isinstance(segment, dict):
                        selected = segment.get('selected_option')
                        if selected:
                            summary_parts.append(
                                f"เลือกที่พัก: {selected.get('name', '')} ที่ {selected.get('location', '')}"
                            )
            
            ground_transport = travel.get('ground_transport', []) if isinstance(travel, dict) else []
            if ground_transport:
                summary_parts.append("การขนส่ง: มีการค้นหาการขนส่งภาคพื้นดิน")
            
            return " | ".join(summary_parts) if summary_parts else None
            
        except Exception as e:
            logger.debug(f"Error extracting trip summary: {e}")
            return None
    
    async def _consolidate_trip_to_memory(self, user_id: str, session_id: str, trip_summary: str):
        try:
            user_input = f"ข้อมูลการเดินทาง: {trip_summary}"
            bot_response = f"ผู้ใช้ได้วางแผนการเดินทางใน session {session_id}"
            await self.memory_service.consolidate(user_id, user_input, bot_response)
        except Exception as e:
            logger.warning(f"Error consolidating trip to memory: {e}")
    
    async def sync_chat_history_to_long_term_memory(self, session_id: str) -> bool:
        """
        Extract important information from MongoDB chat history and sync to long-term memory.
        """
        try:
            from app.storage.mongodb_storage import MongoStorage
            mongo = MongoStorage()
            messages = await mongo.get_chat_history(session_id, limit=100)
            
            if not messages:
                logger.debug(f"No history found in MongoDB for {session_id}")
                return False
            
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            
            for i in range(0, len(messages) - 1, 2):
                try:
                    user_msg = messages[i]
                    bot_msg = messages[i + 1] if i + 1 < len(messages) else None
                    
                    if (
                        user_msg.get("role") == "user"
                        and bot_msg
                        and bot_msg.get("role") == "assistant"
                    ):
                        user_input = user_msg.get("content", "")
                        bot_response = bot_msg.get("content", "")
                        
                        if user_input and bot_response:
                            await self.memory_service.consolidate(user_id, user_input, bot_response)
                            
                except Exception as e:
                    logger.debug(f"Error processing message pair for consolidation: {e}")
                    continue
            
            logger.debug(f"Synced chat history from {session_id} to long-term memory for user {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Error syncing chat history to long-term memory for {session_id}: {e}")
            return False
    
    async def sync_session_with_history(self, session_id: str) -> Dict[str, bool]:
        results = {
            "session": False,
            "history": False
        }
        results["session"] = await self.sync_session_to_long_term_memory(session_id)
        results["history"] = await self.sync_chat_history_to_long_term_memory(session_id)
        return results
    
    async def sync_all_to_long_term_memory(self) -> Dict[str, Any]:
        """Sync all sessions from MongoDB to long-term memory."""
        stats: Dict[str, Any] = {
            "total_sessions": 0,
            "synced_sessions": 0,
            "failed_sessions": 0,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None
        }
        
        try:
            from app.storage.mongodb_storage import MongoStorage
            mongo = MongoStorage()
            
            # Get all session IDs from MongoDB
            db = mongo.db
            cursor = db["sessions"].find({}, {"session_id": 1})
            session_ids = [doc["session_id"] async for doc in cursor if "session_id" in doc]
            
            stats["total_sessions"] = len(session_ids)
            logger.info(f"Found {len(session_ids)} sessions to sync from MongoDB")
            
            for session_id in session_ids:
                if await self.sync_session_to_long_term_memory(session_id):
                    stats["synced_sessions"] += 1
                else:
                    stats["failed_sessions"] += 1
            
            stats["end_time"] = datetime.utcnow().isoformat()
            logger.info(
                f"Memory sync completed: {stats['synced_sessions']}/{stats['total_sessions']} sessions"
            )
            
        except Exception as e:
            logger.error(f"Error during bulk sync: {e}", exc_info=True)
            stats["end_time"] = datetime.utcnow().isoformat()
            stats["error"] = str(e)
        
        return stats
    
    async def get_sync_status(self) -> Dict[str, Any]:
        try:
            from app.storage.mongodb_storage import MongoStorage
            mongo = MongoStorage()
            db = mongo.db
            session_count = await db["sessions"].count_documents({})
            
            return {
                "redis_available": False,
                "redis_removed": True,
                "storage_backend": "mongodb",
                "is_running": self.is_running,
                "mongodb_sessions": session_count,
                "mongodb_available": db is not None
            }
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "redis_available": False,
                "redis_removed": True,
                "storage_backend": "mongodb",
                "is_running": self.is_running,
                "error": str(e)
            }
    
    # Kept for backward compatibility — no-ops since Redis is gone
    async def start_background_sync(self, interval_seconds: Optional[int] = None):
        logger.info("Background Redis sync disabled (Redis removed — using MongoDB only)")
    
    def stop_background_sync(self):
        logger.info("Background Redis sync disabled (Redis removed — using MongoDB only)")


# Global instance (name kept for backward compatibility)
redis_sync_service = RedisSyncService()
