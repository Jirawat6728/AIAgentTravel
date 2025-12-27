from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId


class SessionsRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["sessions"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("user_id")
        await self.col.create_index("expires_at")
        await self.col.create_index("revoked")

    async def create(self, *, user_id: Any, ttl_days: int = 7, user_agent: str | None = None) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "user_id": user_id,
            "created_at": now,
            "expires_at": now + timedelta(days=ttl_days),
            "revoked": False,
            "user_agent": user_agent,
        }
        r = await self.col.insert_one(doc)
        doc["_id"] = r.inserted_id
        return doc

    async def revoke(self, session_id: str) -> None:
        try:
            _id = ObjectId(session_id)
        except Exception:
            return
        await self.col.update_one({"_id": _id}, {"$set": {"revoked": True}})

    async def get_active(self, session_id: str) -> Optional[Dict[str, Any]]:
        try:
            _id = ObjectId(session_id)
        except Exception:
            return None
        now = datetime.now(timezone.utc)
        return await self.col.find_one(
            {"_id": _id, "revoked": False, "expires_at": {"$gt": now}}
        )
