from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional, List

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PlanRepo:
    """Store plan snapshots from the chat (plan_choices/current_plan/summary).

    Collection: plan_snapshots
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def add_snapshot(
        self,
        *,
        user_id: ObjectId,
        trip_id: ObjectId,
        thread_id: ObjectId,
        travel_slots: Dict[str, Any],
        trip_title: Optional[str],
        plan_choices: List[Dict[str, Any]],
        current_plan: Optional[Dict[str, Any]],
        summary_text: Optional[str] = None,
        amadeus_debug: Optional[Dict[str, Any]] = None,
    ) -> ObjectId:
        doc = {
            "user_id": user_id,
            "trip_id": trip_id,
            "thread_id": thread_id,
            "travel_slots": travel_slots,
            "trip_title": trip_title,
            "plan_choices": plan_choices,
            "current_plan": current_plan,
            "summary_text": summary_text,
            "amadeus_debug": amadeus_debug or {},
            "created_at": _now(),
        }
        res = await self.db.plan_snapshots.insert_one(doc)
        return res.inserted_id
