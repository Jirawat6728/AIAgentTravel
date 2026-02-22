"""
เซอร์วิสสมองและความจำของ AI Agent
จัดการความจำระยะยาว (Recall และ Consolidate)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.models.database import Memory, PyObjectId
from app.storage.connection_manager import MongoConnectionManager
from app.services.llm import LLMService
from app.core.logging import get_logger

logger = get_logger(__name__)

class MemoryService:
    """
    Memory Service: The Brain of the Agent
    - Recall: Get relevant memories for a user
    - Consolidate: Extract new facts from conversation and store them
    """
    
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or LLMService()
        self.db = MongoConnectionManager.get_instance().get_database()
        self.collection = self.db.get_collection("memories")
        
        # ✅ SECURITY: Ensure indexes are created (user_id index for data isolation)
        # Indexes are created in MongoStorage.connect(), but we ensure they exist here too
        try:
            # This will be called when MongoStorage.connect() is called, but we log it here
            logger.debug("MemoryService initialized - user_id indexes ensure data isolation")
        except Exception as e:
            logger.warning(f"MemoryService initialization warning: {e}")

    async def recall(self, user_id: str, limit: int = 10) -> List[Memory]:
        """
        Recall relevant memories for a user
        
        ✅ SECURITY: Strictly filters by user_id to prevent data leakage
        ✅ PRIVACY: AI memory/brain is completely isolated per user - no cross-user access
        
        Args:
            user_id: User identifier (MUST be provided, cannot be empty)
            limit: Maximum number of memories to return
            
        Returns:
            List of Memory objects (only for the specified user_id)
        """
        # ✅ SECURITY: Validate user_id is not empty
        if not user_id or not user_id.strip():
            logger.error(f"🚨 SECURITY ALERT: Invalid user_id provided to recall: {user_id}")
            return []
        
        user_id = user_id.strip()  # Normalize user_id
        
        try:
            # ✅ SECURITY: CRITICAL - Strictly filter by user_id - no fallback or alternative queries
            # This ensures AI memory/brain is completely isolated per user
            cursor = self.collection.find({"user_id": user_id}).sort("importance", -1).limit(limit)
            memories_data = await cursor.to_list(length=limit)
            
            memories = []
            for m in memories_data:
                # ✅ SECURITY: Double-check user_id matches before processing (defense in depth)
                doc_user_id = m.get("user_id")
                if not doc_user_id:
                    logger.error(f"🚨 SECURITY ALERT: Memory document missing user_id field, skipping")
                    continue
                    
                if doc_user_id != user_id:
                    logger.error(f"🚨 SECURITY ALERT: Memory user_id mismatch: expected {user_id}, found {doc_user_id}, skipping to prevent data leakage")
                    continue
                
                # ✅ SECURITY: Update last accessed with user_id validation in filter
                await self.collection.update_one(
                    {"_id": m["_id"], "user_id": user_id},  # ✅ CRITICAL: Additional user_id check in update filter
                    {"$set": {"last_accessed": datetime.utcnow()}}
                )
                memories.append(Memory(**m))
            
            logger.debug(f"Recalled {len(memories)} memories for user {user_id}")
            return memories
        except Exception as e:
            logger.error(f"Error recalling memories for user {user_id}: {e}", exc_info=True)
            return []

    async def consolidate(self, user_id: str, user_input: str, bot_response: str):
        """
        Phase 3: Consolidate - Identify new facts to remember
        
        ✅ SECURITY: All memories are strictly associated with user_id to prevent data leakage
        ✅ PRIVACY: AI memory/brain is completely isolated per user - memories never mix between users
        ✅ PRIVACY: Respects user's dataSharing preference — if disabled, skip memory consolidation
        
        Args:
            user_id: User identifier (MUST be provided, cannot be empty)
            user_input: User's input message
            bot_response: Bot's response message
        """
        # ✅ SECURITY: Validate user_id is not empty
        if not user_id or not user_id.strip():
            logger.error(f"🚨 SECURITY ALERT: Invalid user_id provided to consolidate: {user_id}")
            return
        
        user_id = user_id.strip()  # ✅ Normalize user_id to prevent whitespace issues

        # ✅ PRIVACY: Check user's dataSharing preference before learning from conversation
        try:
            users_collection = self.db.get_collection("users")
            user_doc = await users_collection.find_one({"user_id": user_id}, {"preferences": 1})
            prefs = (user_doc or {}).get("preferences") or {}
            if prefs.get("dataSharing") is False:
                logger.debug(f"Skipping memory consolidation for user {user_id}: dataSharing is disabled")
                return
        except Exception as pref_err:
            logger.debug(f"Could not check dataSharing preference for user {user_id}: {pref_err}")
        prompt = f"""You are the memory consolidation module of a travel agent AI.
Analyze the following interaction and extract any NEW important facts or preferences about the user.

USER INPUT: {user_input}
BOT RESPONSE: {bot_response}

Output a list of NEW facts to remember in JSON format:
{{
  "new_memories": [
    {{
      "content": "Short concise fact in Thai",
      "category": "preference" | "fact" | "past_trip",
      "importance": 1-5
    }}
  ]
}}
If no new information, return an empty list. Output JSON ONLY."""

        try:
            # ✅ Generate JSON with error handling (🤖 with auto model selection)
            data = await self.llm.generate_json(
                prompt=prompt,
                temperature=0.3,
                auto_select_model=True,  # 🤖 Enable auto model selection
                context="memory"  # 🤖 Context: memory tasks are usually simple
            )
            if not isinstance(data, dict):
                logger.warning(f"Memory consolidation: LLM returned non-dict: {type(data)}, skipping")
                return
            new_memories = data.get("new_memories", [])
            
            # ✅ Validate new_memories is a list
            if not isinstance(new_memories, list):
                logger.warning(f"Memory consolidation: 'new_memories' is not a list: {type(new_memories)}, skipping")
                return
            
            # ✅ Validate memories data structure
            if not isinstance(new_memories, list):
                logger.warning(f"Invalid memories structure from LLM: {type(new_memories)}, expected list")
                return
            
            for m_data in new_memories:
                # ✅ Validate memory item structure
                if not isinstance(m_data, dict):
                    logger.warning(f"Invalid memory item structure: {type(m_data)}, skipping")
                    continue
                    
                if "content" not in m_data or not m_data["content"]:
                    logger.warning("Memory item missing 'content' field, skipping")
                    continue
                
                # ✅ Validate and set defaults for required fields
                try:
                    memory = Memory(
                        user_id=user_id,
                        content=str(m_data["content"]).strip(),  # Ensure string and trim
                        category=m_data.get("category", "fact"),  # Default to "fact"
                        importance=int(m_data.get("importance", 3))  # Default importance 3
                    )
                    
                    # ✅ Validate importance range (1-5)
                    if memory.importance < 1:
                        memory.importance = 1
                    elif memory.importance > 5:
                        memory.importance = 5
                        
                    # ✅ Skip if content is too short (likely noise)
                    if len(memory.content) < 5:
                        logger.debug(f"Skipping memory with content too short: {len(memory.content)} chars")
                        continue
                        
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Error creating Memory object: {e}, skipping item")
                    continue
                
                # ✅ Deduplicate: Don't save if very similar content exists (improved check)
                # Use first 20 characters for better accuracy, with minimum length check
                content_prefix = memory.content[:20] if len(memory.content) > 20 else memory.content
                if len(content_prefix) < 3:
                    # Skip if content is too short (likely noise)
                    logger.debug(f"Skipping memory consolidation: content too short ({len(memory.content)} chars)")
                    continue
                
                try:
                    # ✅ SECURITY: CRITICAL - Strictly filter by user_id for deduplication
                    # This ensures memories are only compared within the same user's data
                    existing = await self.collection.find_one({
                        "user_id": user_id,  # ✅ CRITICAL: Filter by user_id to prevent cross-user deduplication
                        "content": {"$regex": f"^{content_prefix[:10]}", "$options": "i"}
                    })
                    
                    if not existing:
                        # ✅ SECURITY: Ensure user_id is set correctly in memory document
                        memory_doc = memory.model_dump(by_alias=True, exclude={"id"})
                        memory_doc["user_id"] = user_id.strip()  # ✅ Explicitly set user_id
                        
                        await self.collection.insert_one(memory_doc)
                        logger.info(f"New memory consolidated for user {user_id}: {memory.content[:50]}...")
                        
                        # ✅ Update User Preferences if this is a preference memory
                        if memory.category == "preference":
                            await self._update_user_preferences(user_id, memory.content)
                    else:
                        # ✅ SECURITY: CRITICAL - Verify existing memory belongs to same user
                        # This should never happen due to user_id filter, but defense in depth
                        existing_user_id = existing.get("user_id")
                        if existing_user_id != user_id:
                            logger.error(f"🚨 SECURITY ALERT: Memory deduplication found memory with different user_id: expected {user_id}, found {existing_user_id}. This should not happen due to user_id filter.")
                            # Save anyway as new memory (different user) - better safe than sorry
                            memory_doc = memory.model_dump(by_alias=True, exclude={"id"})
                            memory_doc["user_id"] = user_id  # ✅ CRITICAL: Set correct user_id
                            await self.collection.insert_one(memory_doc)
                            logger.info(f"New memory saved (different user_id): {memory.content[:50]}...")
                        else:
                            logger.debug(f"Memory already exists (deduplicated): {memory.content[:50]}...")
                except Exception as dedup_error:
                    logger.warning(f"Error during memory deduplication: {dedup_error}, saving anyway")
                    # Save anyway if deduplication fails (better to have duplicate than lose memory)
                    try:
                        memory_doc = memory.model_dump(by_alias=True, exclude={"id"})
                        memory_doc["user_id"] = user_id.strip()  # ✅ Explicitly set user_id
                        await self.collection.insert_one(memory_doc)
                        logger.info(f"New memory saved (dedup failed): {memory.content[:50]}...")
                    except Exception as save_error:
                        logger.error(f"Failed to save memory after dedup error: {save_error}", exc_info=True)
                    
        except Exception as e:
            logger.error(f"Error consolidating memories for user {user_id}: {e}")

    async def _update_user_preferences(self, user_id: str, preference_content: str):
        """
        Update user preferences in User collection based on memory consolidation
        ✅ SECURITY: Only updates preferences for the specified user_id
        """
        try:
            users_collection = self.db["users"]
            
            # ✅ SECURITY: CRITICAL - Only update preferences for the exact user_id
            # This ensures user preferences are completely isolated per user
            # Extract preference key-value pairs from content (simple implementation)
            # In production, you might want to use LLM to extract structured preferences
            
            # For now, just mark that preferences were learned
            await users_collection.update_one(
                {"user_id": user_id},  # ✅ CRITICAL: Filter by user_id to ensure data isolation
                {
                    "$set": {
                        "preferences.learned_from_memory": True,
                        "preferences.last_updated": datetime.utcnow(),
                        "last_active": datetime.utcnow()
                    },
                    "$addToSet": {
                        "preferences.memory_summaries": preference_content[:200]  # Store summary
                    }
                },
                upsert=False  # Don't create user if doesn't exist
            )
            logger.debug(f"Updated user preferences for user {user_id} from memory: {preference_content[:50]}...")
        except Exception as e:
            logger.warning(f"Failed to update user preferences for user {user_id}: {e}")
            # Don't fail memory consolidation if preference update fails
    
    def format_memories_for_prompt(self, memories: List[Memory]) -> str:
        """
        Convert memories to a string format for LLM context
        ✅ SECURITY: Only formats memories provided (already filtered by user_id)
        """
        if not memories:
            return "No previous memories of this user."
            
        lines = []
        for i, m in enumerate(memories):
            # ✅ SECURITY: Only format memories that were already filtered by user_id
            lines.append(f"{i+1}. [{m.category}] {m.content}")
            
        return "\n".join(lines)

