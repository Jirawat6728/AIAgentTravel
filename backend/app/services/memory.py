"""
AI Agent Brain & Memory Service
Handles long-term memory (Recall & Consolidate)
"""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from app.models.database import Memory, PyObjectId
from app.storage.mongodb_connection import MongoConnectionManager
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

    async def recall(self, user_id: str, limit: int = 10) -> List[Memory]:
        """
        Recall relevant memories for a user
        """
        try:
            cursor = self.collection.find({"user_id": user_id}).sort("importance", -1).limit(limit)
            memories_data = await cursor.to_list(length=limit)
            
            memories = []
            for m in memories_data:
                # Update last accessed
                await self.collection.update_one({"_id": m["_id"]}, {"$set": {"last_accessed": datetime.utcnow()}})
                memories.append(Memory(**m))
            
            return memories
        except Exception as e:
            logger.error(f"Error recalling memories for user {user_id}: {e}")
            return []

    async def consolidate(self, user_id: str, user_input: str, bot_response: str):
        """
        Phase 3: Consolidate - Identify new facts to remember
        """
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
            data = await self.llm.generate_json(prompt=prompt, temperature=0.3)
            new_memories = data.get("new_memories", [])
            
            for m_data in new_memories:
                memory = Memory(
                    user_id=user_id,
                    content=m_data["content"],
                    category=m_data["category"],
                    importance=m_data["importance"]
                )
                
                # Deduplicate: Don't save if very similar content exists (simple check)
                existing = await self.collection.find_one({
                    "user_id": user_id,
                    "content": {"$regex": memory.content[:10], "$options": "i"}
                })
                
                if not existing:
                    await self.collection.insert_one(memory.model_dump(by_alias=True, exclude={"id"}))
                    logger.info(f"New memory consolidated for user {user_id}: {memory.content}")
                    
        except Exception as e:
            logger.error(f"Error consolidating memories for user {user_id}: {e}")

    def format_memories_for_prompt(self, memories: List[Memory]) -> str:
        """
        Convert memories to a string format for LLM context
        """
        if not memories:
            return "No previous memories of this user."
            
        lines = []
        for i, m in enumerate(memories):
            lines.append(f"{i+1}. [{m.category}] {m.content}")
            
        return "\n".join(lines)

