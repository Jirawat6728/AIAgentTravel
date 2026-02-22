"""
Reinforcement Learning Service สำหรับ AI Travel Agent
เรียนรู้จากพฤติกรรมผู้ใช้จริง เก็บ Q-values ใน MongoDB per-user
ใช้ปรับปรุงการแนะนำและ auto-select ใน Agent Mode
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import json

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Reward constants
# ---------------------------------------------------------------------------
REWARD_SELECT_OPTION   =  0.3   # user เลือก option
REWARD_COMPLETE_BOOKING =  1.0  # จองสำเร็จ
REWARD_POSITIVE_FEEDBACK=  0.5  # feedback ดี
REWARD_REJECT_OPTION   = -0.2   # ปฏิเสธ option
REWARD_CANCEL_BOOKING  = -0.5   # ยกเลิกการจอง
REWARD_NEGATIVE_FEEDBACK= -0.3  # feedback แย่
REWARD_EDIT_SELECTION  = -0.1   # แก้ไขการเลือก


def _calc_reward(action_type: str, context: Optional[Dict] = None) -> float:
    ctx = context or {}
    if action_type in ("select_option",):
        return REWARD_SELECT_OPTION
    if action_type in ("book", "complete_booking"):
        return REWARD_COMPLETE_BOOKING
    if action_type == "positive_feedback":
        return REWARD_POSITIVE_FEEDBACK * ctx.get("feedback_score", 1.0)
    if action_type in ("reject", "reject_option"):
        return REWARD_REJECT_OPTION
    if action_type in ("cancel", "cancel_booking"):
        return REWARD_CANCEL_BOOKING
    if action_type == "negative_feedback":
        return REWARD_NEGATIVE_FEEDBACK * abs(ctx.get("feedback_score", 1.0))
    if action_type in ("edit", "edit_selection"):
        return REWARD_EDIT_SELECTION
    return 0.0


# ---------------------------------------------------------------------------
# MongoDB-backed RL Service (per-user Q-table)
# ---------------------------------------------------------------------------
class RLService:
    """
    Reinforcement Learning Service ที่เก็บ Q-values ใน MongoDB per-user.

    Q-table schema (collection: rl_qtable):
      user_id, slot_name, option_key, q_value, visit_count, last_updated

    Reward history schema (collection: rl_rewards):
      user_id, action_type, slot_name, option_key, reward, context, created_at
    """

    GAMMA = 0.9          # discount factor
    ALPHA = 0.3          # learning rate
    MAX_HISTORY = 500    # max reward records per user

    def __init__(self):
        self._db = None

    def _get_db(self):
        if self._db is None:
            from app.storage.connection_manager import ConnectionManager
            self._db = ConnectionManager.get_instance().get_mongo_database()
        return self._db

    # ------------------------------------------------------------------
    # Option key: fingerprint ที่ระบุ option อย่าง stable
    # ------------------------------------------------------------------
    @staticmethod
    def _option_key(slot_name: str, option: Any) -> str:
        """สร้าง key ที่ stable สำหรับ option หนึ่งๆ"""
        if isinstance(option, dict):
            # ใช้ flight_number หรือ hotel name หรือ display_name
            parts = [slot_name]
            for field in ("flight_number", "name", "display_name", "airline", "hotel_id", "id"):
                v = option.get(field)
                if v:
                    parts.append(str(v)[:40])
                    break
            price = option.get("price_amount") or option.get("price_total") or option.get("price", 0)
            parts.append(f"p{int(float(price or 0))}")
            return ":".join(parts)
        return f"{slot_name}:unknown"

    # ------------------------------------------------------------------
    # Record reward → MongoDB
    # ------------------------------------------------------------------
    async def record_reward(
        self,
        user_id: str,
        action_type: str,
        slot_name: str,
        option: Any = None,
        context: Optional[Dict] = None,
    ) -> None:
        """บันทึก reward และอัปเดต Q-value ใน MongoDB"""
        if not user_id:
            return
        reward = _calc_reward(action_type, context)
        option_key = self._option_key(slot_name, option) if option else f"{slot_name}:unknown"

        db = self._get_db()
        if db is None:
            logger.warning("RL: DB not available, skipping record_reward")
            return

        try:
            # 1. บันทึก reward history
            rewards_col = db["rl_rewards"]
            await rewards_col.insert_one({
                "user_id": user_id,
                "action_type": action_type,
                "slot_name": slot_name,
                "option_key": option_key,
                "reward": reward,
                "context": context or {},
                "created_at": datetime.utcnow().isoformat(),
            })

            # ตัด history เก่าออก (keep MAX_HISTORY ล่าสุด)
            count = await rewards_col.count_documents({"user_id": user_id})
            if count > self.MAX_HISTORY:
                oldest = await rewards_col.find(
                    {"user_id": user_id},
                    {"_id": 1}
                ).sort("created_at", 1).limit(count - self.MAX_HISTORY).to_list(length=count)
                ids = [d["_id"] for d in oldest]
                if ids:
                    await rewards_col.delete_many({"_id": {"$in": ids}})

            # 2. อัปเดต Q-value ด้วย Q-learning update rule:
            #    Q(s,a) ← Q(s,a) + α * (r + γ * max_Q_next - Q(s,a))
            #    เนื่องจาก travel booking เป็น episodic ไม่มี next state ที่ชัดเจน
            #    ใช้ simplified: Q ← Q + α * (r - Q)
            qtable_col = db["rl_qtable"]
            existing = await qtable_col.find_one({
                "user_id": user_id,
                "slot_name": slot_name,
                "option_key": option_key,
            })

            if existing:
                old_q = existing.get("q_value", 0.0)
                new_q = old_q + self.ALPHA * (reward - old_q)
                await qtable_col.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "q_value": round(new_q, 4),
                        "visit_count": existing.get("visit_count", 0) + 1,
                        "last_updated": datetime.utcnow().isoformat(),
                        "last_action": action_type,
                    }}
                )
            else:
                await qtable_col.insert_one({
                    "user_id": user_id,
                    "slot_name": slot_name,
                    "option_key": option_key,
                    "q_value": round(reward * self.ALPHA, 4),
                    "visit_count": 1,
                    "last_updated": datetime.utcnow().isoformat(),
                    "last_action": action_type,
                })

            logger.info(
                f"🧠 RL: user={user_id[:8]} action={action_type} "
                f"slot={slot_name} reward={reward:+.2f} key={option_key[:30]}"
            )

        except Exception as e:
            logger.warning(f"RL record_reward error: {e}")

    # ------------------------------------------------------------------
    # Get Q-scores for a list of options → ใช้ rank ใน Agent Mode
    # ------------------------------------------------------------------
    async def get_option_scores(
        self,
        user_id: str,
        slot_name: str,
        options: List[Any],
    ) -> List[float]:
        """
        คืน RL score สำหรับแต่ละ option (index ตรงกับ options list)
        score > 0 = user เคยชอบ option แบบนี้
        score < 0 = user เคยปฏิเสธ/ยกเลิก
        score = 0 = ไม่มีข้อมูล
        """
        if not user_id or not options:
            return [0.0] * len(options)

        db = self._get_db()
        if db is None:
            return [0.0] * len(options)

        try:
            keys = [self._option_key(slot_name, opt) for opt in options]
            qtable_col = db["rl_qtable"]
            docs = await qtable_col.find(
                {"user_id": user_id, "slot_name": slot_name, "option_key": {"$in": keys}}
            ).to_list(length=len(keys))

            q_map = {d["option_key"]: d["q_value"] for d in docs}
            return [q_map.get(k, 0.0) for k in keys]

        except Exception as e:
            logger.warning(f"RL get_option_scores error: {e}")
            return [0.0] * len(options)

    # ------------------------------------------------------------------
    # Build RL context string สำหรับ inject เข้า LLM prompt
    # ------------------------------------------------------------------
    async def build_rl_context(
        self,
        user_id: str,
        slot_name: str,
        options: List[Any],
    ) -> str:
        """
        สร้าง context string ที่บอก LLM ว่า user เคยชอบ/ไม่ชอบ option แบบไหน
        """
        if not user_id:
            return ""

        scores = await self.get_option_scores(user_id, slot_name, options)

        lines = []
        for i, (opt, score) in enumerate(zip(options, scores)):
            if abs(score) < 0.01:
                continue  # ไม่มีข้อมูล ข้ามไป
            label = "✅ user เคยชอบ/เลือก" if score > 0 else "❌ user เคยปฏิเสธ/ยกเลิก"
            name = ""
            if isinstance(opt, dict):
                name = opt.get("display_name") or opt.get("name") or opt.get("flight_number", f"option {i}")
            lines.append(f"  - Option {i} ({name}): {label} (score={score:+.3f})")

        if not lines:
            return ""

        return (
            "\n=== 🧠 RL USER PREFERENCE HISTORY ===\n"
            "Based on this user's past behavior:\n"
            + "\n".join(lines)
            + "\nUse this to BOOST options the user historically preferred and AVOID ones they rejected.\n"
        )

    # ------------------------------------------------------------------
    # Get user stats (สำหรับ debug / admin)
    # ------------------------------------------------------------------
    async def get_user_stats(self, user_id: str) -> Dict:
        db = self._get_db()
        if db is None:
            return {}
        try:
            rewards_col = db["rl_rewards"]
            qtable_col = db["rl_qtable"]
            total_rewards = await rewards_col.count_documents({"user_id": user_id})
            qtable_entries = await qtable_col.count_documents({"user_id": user_id})
            recent = await rewards_col.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(10).to_list(length=10)
            avg_reward = 0.0
            if recent:
                avg_reward = sum(r.get("reward", 0) for r in recent) / len(recent)
            return {
                "total_reward_records": total_rewards,
                "qtable_entries": qtable_entries,
                "recent_avg_reward": round(avg_reward, 3),
            }
        except Exception as e:
            logger.warning(f"RL get_user_stats error: {e}")
            return {}


# ---------------------------------------------------------------------------
# Backward-compat shim: keep get_rl_learner() working for old call sites
# ---------------------------------------------------------------------------
class _LegacyShim:
    """Thin wrapper ให้ old code ที่ call get_rl_learner().record_reward() ยังทำงานได้
    แต่ไม่ทำอะไร (ถูกแทนที่ด้วย RLService.record_reward ที่ async แล้ว)"""
    def record_reward(self, action_type, slot_name, option_index, context=None):
        logger.debug(f"RL legacy shim: {action_type} {slot_name}[{option_index}] — use RLService instead")


_legacy_shim = _LegacyShim()


def get_rl_learner() -> _LegacyShim:
    """Backward compat — returns shim. New code should use get_rl_service()."""
    return _legacy_shim


# Singleton RLService
_rl_service: Optional[RLService] = None


def get_rl_service() -> RLService:
    """Get singleton RLService instance"""
    global _rl_service
    if _rl_service is None:
        _rl_service = RLService()
    return _rl_service
