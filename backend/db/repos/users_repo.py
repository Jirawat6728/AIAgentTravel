from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class UsersRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.col = db["users"]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("google.sub", unique=True, sparse=True)
        await self.col.create_index("email", unique=True, sparse=True)
        await self.col.create_index("created_at")

    async def upsert_google_user(
        self,
        *,
        sub: str,
        email: str,
        name: Optional[str],
        picture: Optional[str],
        raw_claims: Dict[str, Any],
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)
        doc = {
            "email": email,
            "name": name,
            "picture": picture,
            "google": {"sub": sub, "claims": raw_claims},
            "updated_at": now,
        }
        res = await self.col.find_one_and_update(
            {"google.sub": sub},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return res

    async def get_by_id(self, user_id: Any) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"_id": user_id})

    async def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.col.find_one({"email": email})
