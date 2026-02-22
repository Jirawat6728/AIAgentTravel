"""
สถานะ workflow การวางแผนทริป (Redis)
ติดตามขั้นตอน: planning → searching → selecting → summary → booking → done
เมื่อเสร็จสิ้น (done หรือจองสำเร็จ) ให้เคลียร์ Redis ของ session นั้น
รองรับ workflow_validation schema: current_step, is_complete, completeness_issues (สำหรับ frontend)
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime
from app.core.logging import get_logger
from app.storage.connection_manager import RedisConnectionManager

if TYPE_CHECKING:
    from app.models.trip_plan import TripPlan

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


def _compute_completeness_issues(trip_plan: Any, step: str) -> List[str]:
    """คำนวณ completeness_issues จาก trip_plan สำหรับ frontend"""
    issues: List[str] = []
    if not trip_plan or not hasattr(trip_plan, "travel") or not hasattr(trip_plan, "accommodation"):
        return issues
    try:
        from app.models.trip_plan import SegmentStatus
        # Check flights
        flights = getattr(trip_plan.travel, "flights", None)
        if flights:
            for i, seg in enumerate(flights.outbound or []):
                if seg.status != SegmentStatus.CONFIRMED and seg.requirements:
                    if not (seg.options_pool and len(seg.options_pool) > 0):
                        issues.append(f"เที่ยวบินขาออก: รอผลการค้นหาหรือเลือกตัวเลือก")
                    elif seg.status == SegmentStatus.SELECTING:
                        issues.append(f"เที่ยวบินขาออก: กรุณาเลือกตัวเลือก")
            for i, seg in enumerate(flights.inbound or []):
                if seg.status != SegmentStatus.CONFIRMED and seg.requirements:
                    if not (seg.options_pool and len(seg.options_pool) > 0):
                        issues.append(f"เที่ยวบินขากลับ: รอผลการค้นหาหรือเลือกตัวเลือก")
                    elif seg.status == SegmentStatus.SELECTING:
                        issues.append(f"เที่ยวบินขากลับ: กรุณาเลือกตัวเลือก")
        # Check accommodation
        for i, seg in enumerate(trip_plan.accommodation.segments or []):
            if seg.status != SegmentStatus.CONFIRMED and seg.requirements:
                if not (seg.options_pool and len(seg.options_pool) > 0):
                    issues.append(f"ที่พัก: รอผลการค้นหาหรือเลือกตัวเลือก")
                elif seg.status == SegmentStatus.SELECTING:
                    issues.append(f"ที่พัก: กรุณาเลือกตัวเลือก")
        # Check ground transport
        for i, seg in enumerate(trip_plan.travel.ground_transport or []):
            if seg.status != SegmentStatus.CONFIRMED and seg.requirements:
                if not (seg.options_pool and len(seg.options_pool) > 0):
                    issues.append(f"การเดินทางภาคพื้นดิน: รอผลการค้นหาหรือเลือกตัวเลือก")
                elif seg.status == SegmentStatus.SELECTING:
                    issues.append(f"การเดินทางภาคพื้นดิน: กรุณาเลือกตัวเลือก")
    except Exception as e:
        logger.debug(f"compute completeness_issues: {e}")
    return issues[:5]  # Limit to 5 issues


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
        """ตั้งค่าขั้นตอน workflow (และอัปเดต slots_complete ถ้าระบุ).
        ใช้ transition validation จาก workflow_graph ถ้ามี."""
        try:
            redis_client = await self._get_redis()
            if redis_client is None:
                return False
            existing = await self.get_workflow_state(session_id) or {}
            from_step = existing.get("step", "planning")
            try:
                from app.orchestration.workflow_graph import can_transition
                if not can_transition(from_step, step):
                    logger.debug(f"Workflow transition {from_step} -> {step} skipped (invalid), keeping {from_step}")
                    step = from_step
            except ImportError:
                pass
            key = self._key(session_id)
            now = datetime.utcnow().isoformat()
            data = {
                "step": step,
                "slots_complete": slots_complete if slots_complete is not None else existing.get("slots_complete", {}),
                "updated_at": now,
                "created_at": existing.get("created_at", now),
            }
            await redis_client.set(key, json.dumps(data), ex=ttl_seconds)
            logger.info(f"Workflow state set: session={session_id}, step={step}")
            # #region agent debug log (H5)
            try:
                _debug_path = r"c:\Users\Juins\Desktop\DEMO\AITravelAgent\.cursor\debug.log"
                with open(_debug_path, "a", encoding="utf-8") as _df:
                    _df.write(json.dumps({"id": f"log_wf_{session_id[:20]}", "timestamp": int(datetime.utcnow().timestamp() * 1000), "location": "workflow_state.py:set_workflow_state", "message": "Workflow step transition", "data": {"from_step": from_step, "to_step": step}, "runId": "run1", "hypothesisId": "H5"}, ensure_ascii=False) + "\n")
            except Exception:
                pass
            # #endregion
            # เก็บประวัติ workflow สำหรับ debug/analytics (ไม่ block)
            try:
                from app.services.workflow_history import append_workflow_event_fire_and_forget
                append_workflow_event_fire_and_forget(session_id, from_step, step)
            except Exception as hist_err:
                logger.debug(f"Workflow history append skip: {hist_err}")
            return True
        except Exception as e:
            logger.error(f"set_workflow_state failed: {e}", exc_info=True)
            return False

    async def get_workflow_validation(
        self,
        session_id: str,
        trip_plan: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """คืน workflow_validation schema สำหรับ frontend:
        current_step, step, is_complete, completeness_issues, slots_complete, updated_at"""
        raw = await self.get_workflow_state(session_id) or {}
        step = raw.get("step", "planning")
        slots_complete = raw.get("slots_complete", {})
        is_complete = False
        completeness_issues: List[str] = []

        if trip_plan and hasattr(trip_plan, "is_complete"):
            is_complete = trip_plan.is_complete()
            completeness_issues = _compute_completeness_issues(trip_plan, step)

        if step == "summary" or step == "booking" or step == "done":
            is_complete = True
            completeness_issues = []

        return {
            "step": step,
            "current_step": step,
            "is_complete": is_complete,
            "completeness_issues": completeness_issues,
            "slots_complete": slots_complete,
            "updated_at": raw.get("updated_at"),
            "created_at": raw.get("created_at"),
        }

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
