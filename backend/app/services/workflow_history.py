"""
เก็บประวัติ workflow (planning → selecting → booking) สำหรับ debug / analytics
เขียนลง MongoDB collection workflow_history ทุกครั้งที่มีการเปลี่ยน step
"""

from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.storage.connection_manager import MongoConnectionManager
from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_NAME = "workflow_history"


def _user_id_from_session(session_id: str) -> str:
    """Extract user_id from session_id (format: user_id::chat_id)."""
    if not session_id or "::" not in session_id:
        return session_id or "unknown"
    return session_id.split("::", 1)[0]


async def append_workflow_event(
    session_id: str,
    from_step: str,
    to_step: str,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    บันทึกการเปลี่ยนขั้น workflow ลง MongoDB (fire-and-forget ไม่ block)
    ใช้สำหรับ debug และ analytics เช่น planning → searching → selecting → summary → booking → done

    Args:
        session_id: session_id (user_id::chat_id)
        from_step: ขั้นก่อนหน้า
        to_step: ขั้นใหม่
        payload: ข้อมูลเพิ่ม (เช่น slot_name, mode, run_id)
    """
    doc = {
        "session_id": session_id,
        "user_id": _user_id_from_session(session_id),
        "from_step": from_step,
        "to_step": to_step,
        "at": datetime.utcnow().isoformat() + "Z",
        "ts": datetime.utcnow(),
    }
    if payload:
        # Only store JSON-serializable, small payload (no large objects)
        safe = {}
        for k, v in (payload or {}).items():
            if isinstance(v, (str, int, float, bool, type(None))):
                safe[k] = v
            elif isinstance(v, (list, dict)) and len(str(v)) < 500:
                safe[k] = v
        if safe:
            doc["payload"] = safe

    try:
        db = MongoConnectionManager.get_instance().get_database()
        coll = db.get_collection(COLLECTION_NAME)
        await coll.insert_one(doc)
        logger.debug(f"Workflow history: {session_id} {from_step} -> {to_step}")
        return True
    except Exception as e:
        logger.warning(f"Workflow history append failed: {e}")
        return False


def append_workflow_event_fire_and_forget(
    session_id: str,
    from_step: str,
    to_step: str,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    """
    บันทึกประวัติ workflow แบบไม่รอผล (ไม่ block request)
    เรียกจาก set_workflow_state ได้โดยไม่กระทบ latency
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            append_workflow_event(session_id, from_step, to_step, payload)
        )
    except Exception as e:
        logger.debug(f"Workflow history fire-and-forget skip: {e}")


async def get_workflow_history(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    from_ts: Optional[datetime] = None,
    to_ts: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    ดึงประวัติ workflow สำหรับ debug/analytics
    กรองได้ตาม session_id หรือ user_id และช่วงเวลา
    """
    try:
        db = MongoConnectionManager.get_instance().get_database()
        coll = db.get_collection(COLLECTION_NAME)
        q = {}
        if session_id:
            q["session_id"] = session_id
        if user_id:
            q["user_id"] = user_id
        if from_ts:
            q.setdefault("ts", {})["$gte"] = from_ts
        if to_ts:
            q.setdefault("ts", {})["$lte"] = to_ts
        cursor = coll.find(q).sort("ts", -1).limit(limit)
        out = []
        async for d in cursor:
            d["_id"] = str(d["_id"])
            if "ts" in d and hasattr(d["ts"], "isoformat"):
                d["ts"] = d["ts"].isoformat() + "Z"
            out.append(d)
        return out
    except Exception as e:
        logger.warning(f"get_workflow_history failed: {e}")
        return []
