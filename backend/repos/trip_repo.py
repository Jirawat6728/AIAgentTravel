from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TripRepo:
    """Trip / thread persistence.

    Collections:
      - trips: one per "trip planning" concept
      - threads: chat threads under a trip
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def create_trip(
        self,
        *,
        user_id: ObjectId,
        title: Optional[str],
        travel_slots: Dict[str, Any],
    ) -> ObjectId:
        doc = {
            "user_id": user_id,
            "title": title,
            "status": "active",  # active|archived
            "travel_slots": travel_slots,
            "created_at": _now(),
            "updated_at": _now(),
        }
        res = await self.db.trips.insert_one(doc)
        return res.inserted_id

    async def update_trip(
        self,
        *,
        trip_id: ObjectId,
        title: Optional[str],
        travel_slots: Dict[str, Any],
    ) -> None:
        await self.db.trips.update_one(
            {"_id": trip_id},
            {"$set": {"updated_at": _now(), "title": title, "travel_slots": travel_slots}},
        )

    async def get_latest_active_trip(self, *, user_id: ObjectId) -> Optional[Dict[str, Any]]:
        return await self.db.trips.find_one({"user_id": user_id, "status": "active"}, sort=[("updated_at", -1)])

    async def ensure_active_trip(
        self,
        *,
        user_id: ObjectId,
        title: Optional[str],
        travel_slots: Dict[str, Any],
        reuse_window_minutes: int = 90,
    ) -> ObjectId:
        """Reuse an active trip if it's updated recently; otherwise create new."""
        latest = await self.get_latest_active_trip(user_id=user_id)
        if latest:
            # If updated_at is within window -> reuse
            ua = latest.get("updated_at")
            try:
                if isinstance(ua, datetime):
                    age = (_now() - ua).total_seconds() / 60.0
                    if age <= reuse_window_minutes:
                        await self.update_trip(trip_id=latest["_id"], title=title, travel_slots=travel_slots)
                        return latest["_id"]
            except Exception:
                pass
        trip_id = await self.create_trip(user_id=user_id, title=title, travel_slots=travel_slots)
        return trip_id

    async def create_thread(self, *, trip_id: ObjectId, user_id: ObjectId) -> ObjectId:
        doc = {
            "trip_id": trip_id,
            "user_id": user_id,
            "created_at": _now(),
            "updated_at": _now(),
        }
        res = await self.db.threads.insert_one(doc)
        return res.inserted_id

    async def get_latest_thread(self, *, trip_id: ObjectId) -> Optional[Dict[str, Any]]:
        return await self.db.threads.find_one({"trip_id": trip_id}, sort=[("updated_at", -1)])

    async def ensure_thread(self, *, trip_id: ObjectId, user_id: ObjectId) -> ObjectId:
        t = await self.get_latest_thread(trip_id=trip_id)
        if t:
            await self.db.threads.update_one({"_id": t["_id"]}, {"$set": {"updated_at": _now()}})
            return t["_id"]
        return await self.create_thread(trip_id=trip_id, user_id=user_id)
