"""
เซอร์วิสซิงค์ Redis ไป MongoDB
ซิงค์ข้อมูลจาก Redis (ความจำระยะสั้น) ไป MongoDB (ความจำระยะยาว/คอลเลกชัน memories)
ดึงข้อมูลสำคัญจากเซสชันและการสนทนา แล้วรวมเข้าความจำระยะยาว
"""

import asyncio
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.storage.connection_manager import RedisConnectionManager
from app.services.memory import MemoryService
from app.models.session import UserSession
from app.models.database import SessionDocument
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class RedisSyncService:
    """
    Service to sync data from Redis to MongoDB
    Ensures data persistence even if Redis data expires
    """
    
    def __init__(self):
        self.redis_mgr = RedisConnectionManager.get_instance()
        self.memory_service = MemoryService()  # Use MemoryService for long-term memory
        self.sync_interval = int(settings.redis_ttl * 0.5)  # Sync at 50% of TTL
        self.is_running = False
    
    async def sync_session_to_long_term_memory(self, session_id: str) -> bool:
        """
        Extract important information from session and sync to long-term memory (memories collection)
        
        Args:
            session_id: Session ID to sync
            
        Returns:
            True if synced successfully, False otherwise
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            if redis_client is None:
                logger.debug(f"Redis unavailable, skipping sync for {session_id}")
                return False
            
            # Get session from Redis
            data = await redis_client.get(f"session:{session_id}")
            if not data:
                logger.debug(f"Session {session_id} not found in Redis")
                return False
            
            # Deserialize and convert to UserSession
            session_dict = json.loads(data)
            session_doc = SessionDocument(**session_dict)
            session = session_doc.to_user_session()
            
            # Extract user_id
            user_id = session.user_id
            
            # Extract important information from trip_plan for long-term memory
            # This will be consolidated by MemoryService
            trip_summary = self._extract_trip_summary(session)
            
            if trip_summary:
                # Use MemoryService to consolidate important trip information
                # This will extract preferences and facts from the trip plan
                await self._consolidate_trip_to_memory(user_id, session_id, trip_summary)
                logger.debug(f"Synced session {session_id} to long-term memory for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"Error syncing session {session_id} to long-term memory: {e}")
            return False
    
    def _extract_trip_summary(self, session: UserSession) -> Optional[str]:
        """
        Extract important trip information as text summary for memory consolidation
        
        Args:
            session: UserSession object
            
        Returns:
            Trip summary text or None
        """
        try:
            trip_plan = session.trip_plan
            if not trip_plan:
                return None
            
            summary_parts = []
            
            # Extract flight preferences
            travel = trip_plan.travel if hasattr(trip_plan, 'travel') else {}
            flights = travel.get('flights', {}) if isinstance(travel, dict) else {}
            
            outbound = flights.get('outbound', []) if isinstance(flights, dict) else []
            inbound = flights.get('inbound', []) if isinstance(flights, dict) else []
            
            if outbound or inbound:
                summary_parts.append("การเดินทาง: มีการค้นหาเที่ยวบิน")
                # Extract preferences from selected options
                for segment in (outbound + inbound):
                    if isinstance(segment, dict):
                        selected = segment.get('selected_option')
                        if selected:
                            summary_parts.append(f"เลือกเที่ยวบิน: {selected.get('airline', '')} จาก {selected.get('origin', '')} ไป {selected.get('destination', '')}")
            
            # Extract accommodation preferences
            accommodation = trip_plan.accommodation if hasattr(trip_plan, 'accommodation') else {}
            segments = accommodation.get('segments', []) if isinstance(accommodation, dict) else []
            
            if segments:
                summary_parts.append("ที่พัก: มีการค้นหาที่พัก")
                for segment in segments:
                    if isinstance(segment, dict):
                        selected = segment.get('selected_option')
                        if selected:
                            summary_parts.append(f"เลือกที่พัก: {selected.get('name', '')} ที่ {selected.get('location', '')}")
            
            # Extract ground transport
            ground_transport = travel.get('ground_transport', []) if isinstance(travel, dict) else []
            if ground_transport:
                summary_parts.append("การขนส่ง: มีการค้นหาการขนส่งภาคพื้นดิน")
            
            if summary_parts:
                return " | ".join(summary_parts)
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting trip summary: {e}")
            return None
    
    async def _consolidate_trip_to_memory(self, user_id: str, session_id: str, trip_summary: str):
        """
        Consolidate trip information to long-term memory using MemoryService
        
        Args:
            user_id: User ID
            session_id: Session ID
            trip_summary: Trip summary text
        """
        try:
            # Create a consolidation prompt from trip summary
            # MemoryService will extract important facts and preferences
            user_input = f"ข้อมูลการเดินทาง: {trip_summary}"
            bot_response = f"ผู้ใช้ได้วางแผนการเดินทางใน session {session_id}"
            
            # Use MemoryService to consolidate (this will extract and save to memories collection)
            await self.memory_service.consolidate(user_id, user_input, bot_response)
            
        except Exception as e:
            logger.warning(f"Error consolidating trip to memory: {e}")
    
    async def sync_chat_history_to_long_term_memory(self, session_id: str) -> bool:
        """
        Extract important information from chat history and sync to long-term memory (memories collection)
        
        Args:
            session_id: Session ID to sync history for
            
        Returns:
            True if synced successfully, False otherwise
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            if redis_client is None:
                logger.debug(f"Redis unavailable, skipping history sync for {session_id}")
                return False
            
            # Get history from Redis
            key = f"history:{session_id}"
            items = await redis_client.lrange(key, 0, -1)
            
            if not items:
                logger.debug(f"No history found in Redis for {session_id}")
                return False
            
            # Parse messages
            messages = []
            for item in items:
                try:
                    messages.append(json.loads(item))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message in history for {session_id}")
                    continue
            
            if not messages:
                return False
            
            # Extract user_id from first message or session_id
            user_id = session_id.split("::")[0] if "::" in session_id else session_id
            
            # Extract important conversation pairs for memory consolidation
            # Process messages in pairs (user input, bot response)
            for i in range(0, len(messages) - 1, 2):
                try:
                    user_msg = messages[i]
                    bot_msg = messages[i + 1] if i + 1 < len(messages) else None
                    
                    if user_msg.get("role") == "user" and bot_msg and bot_msg.get("role") == "assistant":
                        user_input = user_msg.get("content", "")
                        bot_response = bot_msg.get("content", "")
                        
                        if user_input and bot_response:
                            # Use MemoryService to consolidate (extracts and saves to memories collection)
                            await self.memory_service.consolidate(user_id, user_input, bot_response)
                            
                except Exception as e:
                    logger.debug(f"Error processing message pair for consolidation: {e}")
                    continue
            
            logger.debug(f"Synced chat history from {session_id} to long-term memory for user {user_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Error syncing chat history to long-term memory for {session_id}: {e}")
            return False
    
    async def sync_all_to_long_term_memory(self) -> Dict[str, Any]:
        """
        Sync all sessions from Redis to long-term memory (memories collection)
        
        Returns:
            Dictionary with sync statistics
        """
        stats = {
            "total_sessions": 0,
            "synced_sessions": 0,
            "failed_sessions": 0,
            "total_messages": 0,
            "synced_messages": 0,
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None
        }
        
        try:
            redis_client = await self.redis_mgr.get_redis()
            if redis_client is None:
                logger.info("Redis unavailable, skipping bulk sync")
                stats["end_time"] = datetime.utcnow().isoformat()
                return stats
            
            # Find all session keys
            session_keys = []
            async for key in redis_client.scan_iter(match="session:*"):
                session_keys.append(key)
            
            stats["total_sessions"] = len(session_keys)
            logger.info(f"Found {len(session_keys)} sessions to sync")
            
            # Sync each session to long-term memory
            for key in session_keys:
                session_id = key.replace("session:", "")
                
                # Sync session data to long-term memory
                if await self.sync_session_to_long_term_memory(session_id):
                    stats["synced_sessions"] += 1
                else:
                    stats["failed_sessions"] += 1
                
                # Sync chat history to long-term memory
                history_key = f"history:{session_id}"
                items = await redis_client.lrange(history_key, 0, -1)
                if items:
                    stats["total_messages"] += len(items)
                    if await self.sync_chat_history_to_long_term_memory(session_id):
                        stats["synced_messages"] += len(items)
            
            stats["end_time"] = datetime.utcnow().isoformat()
            logger.info(
                f"Long-term memory sync completed: {stats['synced_sessions']}/{stats['total_sessions']} sessions, "
                f"{stats['synced_messages']}/{stats['total_messages']} messages consolidated to memories collection"
            )
            
        except Exception as e:
            logger.error(f"Error during bulk sync: {e}", exc_info=True)
            stats["end_time"] = datetime.utcnow().isoformat()
            stats["error"] = str(e)
        
        return stats
    
    async def sync_session_with_history(self, session_id: str) -> Dict[str, bool]:
        """
        Sync both session data and chat history to long-term memory
        
        Args:
            session_id: Session ID to sync
            
        Returns:
            Dictionary with sync results
        """
        results = {
            "session": False,
            "history": False
        }
        
        # Sync session to long-term memory
        results["session"] = await self.sync_session_to_long_term_memory(session_id)
        
        # Sync history to long-term memory
        results["history"] = await self.sync_chat_history_to_long_term_memory(session_id)
        
        return results
    
    async def start_background_sync(self, interval_seconds: Optional[int] = None):
        """
        Start background sync task that runs periodically
        
        Args:
            interval_seconds: Sync interval in seconds (defaults to sync_interval)
        """
        if self.is_running:
            logger.warning("Background sync already running")
            return
        
        self.is_running = True
        interval = interval_seconds or self.sync_interval
        
        logger.info(f"Starting background Redis sync (interval: {interval}s)")
        
        while self.is_running:
            try:
                await asyncio.sleep(interval)
                if self.is_running:
                    logger.info("Running scheduled Redis sync to long-term memory...")
                    stats = await self.sync_all_to_long_term_memory()
                    logger.info(f"Background long-term memory sync completed: {stats}")
            except asyncio.CancelledError:
                logger.info("Background sync cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background sync: {e}", exc_info=True)
                # Continue running even if one sync fails
                await asyncio.sleep(60)  # Wait 1 minute before retry
    
    def stop_background_sync(self):
        """Stop background sync task"""
        if self.is_running:
            logger.info("Stopping background Redis sync")
            self.is_running = False
        else:
            logger.warning("Background sync not running")
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync service status
        
        Returns:
            Dictionary with status information
        """
        try:
            redis_client = await self.redis_mgr.get_redis()
            redis_available = redis_client is not None
            
            if redis_available:
                # Count sessions and messages in Redis
                session_count = 0
                message_count = 0
                async for key in redis_client.scan_iter(match="session:*"):
                    session_count += 1
                    session_id = key.replace("session:", "")
                    history_key = f"history:{session_id}"
                    items = await redis_client.lrange(history_key, 0, -1)
                    message_count += len(items)
            else:
                session_count = 0
                message_count = 0
            
            return {
                "redis_available": redis_available,
                "is_running": self.is_running,
                "sync_interval": self.sync_interval,
                "redis_sessions": session_count,
                "redis_messages": message_count,
                "mongodb_available": self.mongo_storage.db is not None
            }
        except Exception as e:
            logger.error(f"Error getting sync status: {e}")
            return {
                "redis_available": False,
                "is_running": self.is_running,
                "error": str(e)
            }


# Global sync service instance
redis_sync_service = RedisSyncService()
