from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

def _now() -> datetime:
    return datetime.now(timezone.utc)

class ChatRepo:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_or_create_trip(self, *, user_id: ObjectId, client_trip_id: str, title: Optional[str] = None) -> ObjectId:
        # client_trip_id: from frontend local storage
        doc = await self.db.trips.find_one({"user_id": user_id, "client_trip_id": client_trip_id})
        if doc:
            return doc["_id"]
        res = await self.db.trips.insert_one({
            "user_id": user_id,
            "client_trip_id": client_trip_id,
            "title": title,
            "created_at": _now(),
            "updated_at": _now(),
        })
        return res.inserted_id

    async def touch_trip(self, *, trip_id: ObjectId, title: Optional[str] = None) -> None:
        upd = {"updated_at": _now()}
        if title:
            upd["title"] = title
        await self.db.trips.update_one({"_id": trip_id}, {"$set": upd})

    async def get_or_create_thread(self, *, user_id: ObjectId, trip_id: ObjectId) -> ObjectId:
        doc = await self.db.threads.find_one({"user_id": user_id, "trip_id": trip_id})
        if doc:
            return doc["_id"]
        res = await self.db.threads.insert_one({
            "user_id": user_id,
            "trip_id": trip_id,
            "created_at": _now(),
            "updated_at": _now(),
        })
        return res.inserted_id

    async def save_message(
        self,
        *,
        user_id: ObjectId,
        trip_id: ObjectId,
        thread_id: ObjectId,
        role: str,
        text: str,
        meta: Optional[Dict[str, Any]] = None,
    ) -> ObjectId:
        res = await self.db.messages.insert_one({
            "user_id": user_id,
            "trip_id": trip_id,
            "thread_id": thread_id,
            "role": role,
            "text": text,
            "meta": meta or {},
            "created_at": _now(),
        })
        await self.db.threads.update_one({"_id": thread_id}, {"$set": {"updated_at": _now()}})
        await self.db.trips.update_one({"_id": trip_id}, {"$set": {"updated_at": _now()}})
        return res.inserted_id

    async def save_plan_snapshot(
        self,
        *,
        user_id: ObjectId,
        trip_id: ObjectId,
        thread_id: ObjectId,
        snapshot: Dict[str, Any],
    ) -> ObjectId:
        res = await self.db.plan_snapshots.insert_one({
            "user_id": user_id,
            "trip_id": trip_id,
            "thread_id": thread_id,
            "snapshot": snapshot,
            "created_at": _now(),
        })
        return res.inserted_id
