"""
สถานะ workflow การวางแผนทริป (Redis)
ติดตามขั้นตอน: planning → searching → selecting → summary → booking → done
เมื่อเสร็จสิ้น (done หรือจองสำเร็จ) ให้เคลียร์ Redis ของ session นั้น
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
from app.core.logging import get_logger
from app.storage.connection_manager import RedisConnectionManager

logger = get_logger(__name__)

KEY_PREFIX = "workflow:state:"
DEFAULT_TTL_SECONDS = 86400  # 24 hours


class WorkflowStep:
    """ขั้นตอน workflow"""
    PLANNING = "planning"
    SEARCHING = "searching"
    SELECTING = "selecting"
    SUMMARY = "summary"
    BOOKING = "booking"
    DONE = "done"


class WorkflowStateService:
    """
    เก็บ/อ่านสถานะ workflow ต่อ session ใน Redis
    - step: ขั้นตอนปัจจุบัน
    - slots_complete: { slot_name: bool } ว่าแต่ละ slot เลือกครบหรือยัง
    - created_at, updated_at
    """

    def __init__(self):
        self._redis_mgr = RedisConnectionManager.get_instance()
        logger.info("WorkflowStateService initialized (Redis)")

    def _key(self, session_id: str) -> str:
        return f"{KEY_PREFIX}{session_id}"

    async def _get_redis(self):
        return await self._redis_mgr.get_redis()

    async def get_workflow_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """อ่านสถานะ workflow ของ session"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return None
            raw = await redis_client.get(self._key(session_id))
            if not raw:
                return None
            data = json.loads(raw)
            return data
        except Exception as e:
            logger.warning(f"get_workflow_state failed: {e}")
            return None

    async def set_workflow_state(
        self,
        session_id: str,
        step: str,
        slots_complete: Optional[Dict[str, bool]] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> bool:
        """ตั้งค่าขั้นตอน workflow (และอัปเดต slots_complete ถ้าระบุ)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            key = self._key(session_id)
            now = datetime.utcnow().isoformat()
            existing = await self.get_workflow_state(session_id) or {}
            data = {
                "step": step,
                "slots_complete": slots_complete if slots_complete is not None else existing.get("slots_complete", {}),
                "updated_at": now,
                "created_at": existing.get("created_at", now),
            }
            await redis_client.set(key, json.dumps(data), ex=ttl_seconds)
            logger.info(f"Workflow state set: session={session_id}, step={step}")
            return True
        except Exception as e:
            logger.error(f"set_workflow_state failed: {e}", exc_info=True)
            return False

    async def clear_workflow(self, session_id: str) -> bool:
        """เคลียร์สถานะ workflow ของ session (เรียกเมื่อ workflow เสร็จหรือจองสำเร็จ)"""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            key = self._key(session_id)
            await redis_client.delete(key)
            logger.info(f"Workflow state cleared: session={session_id}")
            return True
        except Exception as e:
            logger.error(f"clear_workflow failed: {e}", exc_info=True)
            return False


_workflow_state_service: Optional[WorkflowStateService] = None


def get_workflow_state_service() -> WorkflowStateService:
    global _workflow_state_service
    if _workflow_state_service is None:
        _workflow_state_service = WorkflowStateService()
    return _workflow_state_service
