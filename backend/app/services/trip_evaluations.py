"""
Trip Evaluations Service — เก็บคะแนนวัดผล AI ต่อทริป
รวม: คะแนนความแม่นยำ ML/RL (agent_accuracy_score) + คะแนนดาวจาก User (user_stars)
ใช้สำหรับให้ AI ประเมินตัวเองและปรับปรุงความสามารถ (เรียนรู้จาก feedback)
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from datetime import datetime

from app.core.logging import get_logger
from app.storage.connection_manager import ConnectionManager

logger = get_logger(__name__)

COLLECTION_NAME = "trip_evaluations"


def _get_db():
    try:
        return ConnectionManager.get_instance().get_mongo_database()
    except Exception:
        return None


async def upsert_trip_evaluation(
    session_id: str,
    user_id: str,
    chat_id: Optional[str] = None,
    mode: Optional[str] = None,
    agent_accuracy_score: Optional[int] = None,
    user_stars: Optional[int] = None,
) -> bool:
    """
    บันทึกหรืออัปเดตการประเมินทริป (คะแนน AI + คะแนน User)
    - เรียกเมื่อ Agent Mode จองสำเร็จ (agent_accuracy_score)
    - เรียกเมื่อ User กดส่งคะแนนดาว (user_stars)
    """
    if not session_id or not user_id:
        return False
    db = _get_db()
    if db is None:
        logger.warning("Trip evaluations: DB not available")
        return False
    try:
        col = db[COLLECTION_NAME]
        now = datetime.utcnow().isoformat()
        doc = await col.find_one({"session_id": session_id})
        update_fields = {"updated_at": now}
        if chat_id is not None:
            update_fields["chat_id"] = chat_id
        if mode is not None:
            update_fields["mode"] = mode
        if agent_accuracy_score is not None:
            update_fields["agent_accuracy_score"] = agent_accuracy_score
        if user_stars is not None:
            update_fields["user_stars"] = user_stars

        if doc:
            await col.update_one(
                {"session_id": session_id},
                {"$set": update_fields},
            )
            logger.info(f"Trip evaluation updated: session_id={session_id[:20]}... accuracy={agent_accuracy_score} stars={user_stars}")
        else:
            await col.insert_one({
                "session_id": session_id,
                "user_id": user_id,
                "chat_id": chat_id or session_id.split("::")[-1] if "::" in session_id else None,
                "mode": mode or "agent",
                "agent_accuracy_score": agent_accuracy_score,
                "user_stars": user_stars,
                "created_at": now,
                "updated_at": now,
            })
            logger.info(f"Trip evaluation created: session_id={session_id[:20]}... accuracy={agent_accuracy_score} stars={user_stars}")
        return True
    except Exception as e:
        logger.warning(f"Trip evaluation upsert error: {e}")
        return False


async def get_user_recent_satisfaction(user_id: str, limit: int = 5) -> Optional[Dict[str, Any]]:
    """
    คืนค่าเฉลี่ยคะแนนดาวจาก User ในทริปล่าสุด (ใช้ใน RL context ให้ AI ปรับปรุงการเลือก)
    """
    if not user_id:
        return None
    db = _get_db()
    if db is None:
        return None
    try:
        col = db[COLLECTION_NAME]
        cursor = col.find(
            {"user_id": user_id, "user_stars": {"$exists": True, "$ne": None}},
            {"user_stars": 1, "agent_accuracy_score": 1},
        ).sort("updated_at", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        if not docs:
            return None
        stars_list = [d["user_stars"] for d in docs if d.get("user_stars") is not None]
        if not stars_list:
            return None
        avg_stars = sum(stars_list) / len(stars_list)
        return {
            "avg_stars": round(avg_stars, 1),
            "count": len(stars_list),
            "recent_stars": stars_list[:3],
        }
    except Exception as e:
        logger.debug(f"get_user_recent_satisfaction error: {e}")
        return None
