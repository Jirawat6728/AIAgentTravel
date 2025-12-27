from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MessageRepo:
    """Store chat messages (user/assistant) plus payload context.

    Collection: messages
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def add_message(
        self,
        *,
        user_id: ObjectId,
        trip_id: ObjectId,
        thread_id: ObjectId,
        role: str,  # "user" | "assistant" | "system"
        text: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ObjectId:
        doc = {
            "user_id": user_id,
            "trip_id": trip_id,
            "thread_id": thread_id,
            "role": role,
            "text": text,
            "payload": payload or {},
            "created_at": _now(),
        }
        res = await self.db.messages.insert_one(doc)
        return res.inserted_id
