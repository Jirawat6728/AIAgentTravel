"""
Reinforcement Learning Service สำหรับ AI Travel Agent
เรียนรู้จากพฤติกรรมผู้ใช้จริง เก็บ Q-values ใน MongoDB per-user
ใช้ปรับปรุงการแนะนำและ auto-select ใน Agent Mode
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import asyncio

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Reward constants (normalized to [-1, +1]) ตามแนวคิด binary/graded feedback
# ในงาน RL สำหรับ recommender / travel planning (เช่น TravelAgent, DeepTravel ฯลฯ)
# ---------------------------------------------------------------------------
# เหตุการณ์ระดับ "สำเร็จ / ล้มเหลว" ของทริป
REWARD_COMPLETE_BOOKING  =  1.0   # booking สำเร็จ → success reward สูงสุด
REWARD_CANCEL_BOOKING    = -1.0   # ยกเลิกการจอง → failure ที่แรงสุด

# เหตุการณ์ระหว่างทาง (shaping rewards) – ค่าบวก/ลบขนาดเล็ก
REWARD_SELECT_OPTION     =  0.2   # user เลือก option หนึ่ง → สัญญาณบวกเล็กน้อย
REWARD_REJECT_OPTION     = -0.2   # user ปฏิเสธ option → สัญญาณลบเล็กน้อย
REWARD_EDIT_SELECTION    = -0.1   # user แก้ไขการเลือก → บอกว่าต้องปรับเล็กน้อย

# Feedback โดยตรงจากผู้ใช้ (text feedback / ปุ่ม like/dislike)
REWARD_POSITIVE_FEEDBACK =  0.5   # feedback เชิงบวก → บวกปานกลาง
REWARD_NEGATIVE_FEEDBACK = -0.5   # feedback เชิงลบ → ลบปานกลาง


# คะแนนดาวจาก User (1–5) → map เป็นสเกลเชิงเส้น [-1, +1]
# ใช้แนวคิด rating-based reward ในงาน RL recommender
STAR_REWARD = {
    1: -1.0,
    2: -0.5,
    3:  0.0,
    4:  0.5,
    5:  1.0,
}


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
    if action_type == "user_star_rating":
        stars = ctx.get("stars", 3)
        return STAR_REWARD.get(int(stars), 0.0)
    return 0.0


# ---------------------------------------------------------------------------
# MongoDB-backed RL Service (per-user Q-table)
# ---------------------------------------------------------------------------
class RLService:
    """
    Reinforcement Learning Service ที่เก็บ Q-values ใน MongoDB per-user.

    Q-table schema (collection: user_preference_scores):
      user_id, slot_name, option_key, q_value, visit_count, last_updated

    Reward history schema (collection: user_feedback_history):
      user_id, action_type, slot_name, option_key, reward, context, created_at
    """

    GAMMA = 0.9          # discount factor
    ALPHA = 0.3          # learning rate
    MAX_HISTORY = 500    # max reward records per user

    def __init__(self):
        pass

    def _get_db(self):
        # ไม่ cache handle เพื่อป้องกัน stale reference หลัง ConnectionManager reconnect
        from app.storage.connection_manager import ConnectionManager
        return ConnectionManager.get_instance().get_mongo_database()

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
        session_mode: str = "",
    ) -> None:
        """บันทึก reward และอัปเดต Q-value ใน MongoDB
        session_mode: 'ask' | 'agent' | 'chat' | 'booking' | '' — ใช้แยก FWL weights
        """
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
            rewards_col = db["user_feedback_history"]
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
            qtable_col = db["user_preference_scores"]
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
                # New entry: apply same update rule from Q=0 → Q = 0 + α*(r - 0) = α*r
                initial_q = self.ALPHA * reward
                await qtable_col.insert_one({
                    "user_id": user_id,
                    "slot_name": slot_name,
                    "option_key": option_key,
                    "q_value": round(initial_q, 4),
                    "visit_count": 1,
                    "last_updated": datetime.utcnow().isoformat(),
                    "last_action": action_type,
                })

            logger.info(
                f"🧠 RL: user={user_id[:8]} action={action_type} "
                f"slot={slot_name} reward={reward:+.2f} key={option_key[:30]}"
            )

            # ── ML Feature Weight Learning (FWL) ─────────────────────────────
            # อัปเดต feature weights ต่อ user ทันที (Online Gradient Descent)
            # แยก ask/agent เพื่อเรียนรู้พฤติกรรมแต่ละ mode แยกกัน
            if option is not None:
                try:
                    from app.engine.feature_learning import get_feature_learner
                    await get_feature_learner().update(
                        user_id=user_id,
                        slot_name=slot_name,
                        option=option,
                        action_type=action_type,
                        context=context,
                        session_mode=session_mode,
                    )
                except Exception as fwl_err:
                    logger.debug(f"FWL update (non-critical): {fwl_err}")

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
        session_mode: str = "",
    ) -> List[float]:
        """
        คืน combined RL+FWL score สำหรับแต่ละ option (index ตรงกับ options list)
        session_mode: 'ask' | 'agent' — ใช้ FWL weights ที่เรียนรู้จาก mode นั้น
        """
        if not user_id or not options:
            return [0.0] * len(options)

        db = self._get_db()
        if db is None:
            return [0.0] * len(options)

        try:
            keys = [self._option_key(slot_name, opt) for opt in options]
            qtable_col = db["user_preference_scores"]
            docs = await qtable_col.find(
                {"user_id": user_id, "slot_name": slot_name, "option_key": {"$in": keys}}
            ).to_list(length=len(keys))

            q_map = {d["option_key"]: d["q_value"] for d in docs}
            rl_scores = [q_map.get(k, 0.0) for k in keys]

            # ── Blend RL Q-score + FWL score ────────────────────────────────
            # combined = 0.6 * rl_score_normalized + 0.4 * (fwl_score - 0.5)*2
            # → ถ้าไม่มี FWL data (0.5) ไม่รบกวน RL score
            try:
                from app.engine.feature_learning import get_feature_learner
                fwl_scores = await get_feature_learner().score_options(
                    user_id, slot_name, options, session_mode=session_mode
                )
            except Exception:
                fwl_scores = [0.5] * len(options)

            combined = []
            for rl, fwl in zip(rl_scores, fwl_scores):
                fwl_delta = (fwl - 0.5) * 2.0   # re-center: 0.5→0, 1.0→+1, 0.0→-1
                blended = rl * 0.6 + fwl_delta * 0.4
                combined.append(round(blended, 4))
            return combined

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
        รวมความพึงพอใจจากคะแนนดาว (trip_evaluations) เพื่อให้ AI ปรับปรุงการเลือกให้ตรงใจ User มากขึ้น
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

        # คะแนนดาวจาก User ในทริปล่าสุด — ให้ AI ประเมินตัวเองและเลือกให้ตรงใจมากขึ้น
        satisfaction_block = ""
        try:
            from app.services.trip_evaluations import get_user_recent_satisfaction
            sat = await get_user_recent_satisfaction(user_id, limit=5)
            if sat and sat.get("avg_stars") is not None:
                satisfaction_block = (
                    "\n=== 📊 USER SATISFACTION (จากคะแนนดาวในทริปล่าสุด) ===\n"
                    f"ค่าเฉลี่ยคะแนนที่ User ให้: {sat['avg_stars']} ดาว (จาก {sat['count']} ทริปล่าสุด)\n"
                    "Use this to maintain or improve selection quality so the user stays satisfied.\n"
                )
        except Exception:
            pass

        if not lines and not satisfaction_block:
            return ""

        pref_block = ""
        if lines:
            pref_block = (
                "\n=== 🧠 RL USER PREFERENCE HISTORY ===\n"
                "Based on this user's past behavior:\n"
                + "\n".join(lines)
                + "\nUse this to BOOST options the user historically preferred and AVOID ones they rejected.\n"
            )

        # ── ML Feature Preference (FWL) ─────────────────────────────────────
        fwl_block = ""
        try:
            from app.engine.feature_learning import get_feature_learner
            fwl_block = await get_feature_learner().get_preference_summary(user_id)
        except Exception:
            pass

        return pref_block + satisfaction_block + fwl_block

    # ------------------------------------------------------------------
    # Get user stats (สำหรับ debug / admin)
    # ------------------------------------------------------------------
    async def get_user_stats(self, user_id: str) -> Dict:
        db = self._get_db()
        if db is None:
            return {}
        try:
            rewards_col = db["user_feedback_history"]
            qtable_col = db["user_preference_scores"]
            total_rewards = await rewards_col.count_documents({"user_id": user_id})
            qtable_entries = await qtable_col.count_documents({"user_id": user_id})
            recent = await rewards_col.find(
                {"user_id": user_id}
            ).sort("created_at", -1).limit(10).to_list(length=10)
            avg_reward = 0.0
            if recent:
                avg_reward = sum(r.get("reward", 0) for r in recent) / len(recent)

            # FWL stats
            fwl_slots = 0
            fwl_total_updates = 0
            try:
                from app.engine.feature_learning import get_feature_learner, COLLECTION_FWL
                fwl_docs = await get_feature_learner().get_user_weights_doc(user_id)
                fwl_slots = len(fwl_docs)
                fwl_total_updates = sum(d.get("update_count", 0) for d in fwl_docs)
            except Exception:
                pass

            return {
                "total_reward_records": total_rewards,
                "qtable_entries": qtable_entries,
                "recent_avg_reward": round(avg_reward, 3),
                "fwl_slots_learned": fwl_slots,
                "fwl_total_updates": fwl_total_updates,
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


def _option_payload(opt: Any) -> Optional[Dict[str, Any]]:
    """แปลง selected_option จาก Segment / dict เป็น dict สำหรับ RL/FWL"""
    if opt is None:
        return None
    if isinstance(opt, dict):
        return dict(opt)
    if hasattr(opt, "model_dump"):
        try:
            return opt.model_dump(mode="python")
        except Exception:
            return None
    return None


def _iter_session_star_rating_targets(session: Any) -> List[Tuple[str, Any]]:
    """
    รวบรวม (slot_name, segment) ที่มี selected_option จาก trip_plan ของเซสชัน
    """
    out: List[Tuple[str, Any]] = []
    tp = getattr(session, "trip_plan", None)
    if tp is None:
        return out
    try:
        travel = getattr(tp, "travel", None)
        if travel is not None:
            fg = getattr(travel, "flights", None)
            if fg is not None:
                for seg in getattr(fg, "outbound", None) or []:
                    out.append(("flights_outbound", seg))
                for seg in getattr(fg, "inbound", None) or []:
                    out.append(("flights_inbound", seg))
            for seg in getattr(travel, "ground_transport", None) or []:
                out.append(("ground_transport", seg))
        acc = getattr(tp, "accommodation", None)
        if acc is not None:
            for seg in getattr(acc, "segments", None) or []:
                out.append(("accommodation", seg))
    except Exception as e:
        logger.debug(f"iter_session_star_rating_targets: {e}")
    return out


async def record_user_star_rating_with_selected_options(
    rl_svc: RLService,
    user_id: str,
    session_id: str,
    stars: int,
    satisfaction_pct: float,
    criteria_ratings: Optional[Dict[str, Any]] = None,
    mode: str = "",
) -> int:
    """
    บันทึกคะแนนดาวไปที่แต่ละตัวเลือกที่เลือกจริงใน trip_plan (เที่ยวบิน / ที่พัก / รถ)
    → อัปเดต Q-table ต่อ option_key + เรียก FWL (Online gradient) ต่อฟีเจอร์ของ option นั้น

    คืนจำนวน option ที่อัปเดตสำเร็จ (0 = ไม่มีข้อมูลในเซสชัน — ให้ caller ใช้แบบหยาบ agent_booking)
    """
    if not user_id or not session_id:
        return 0
    session_mode = mode.lower().strip() if mode and mode.lower().strip() in ("ask", "agent") else "agent"
    ctx: Dict[str, Any] = {
        "stars": stars,
        "session_id": session_id,
        "satisfaction_pct": satisfaction_pct,
    }
    if criteria_ratings:
        ctx["criteria_ratings"] = criteria_ratings

    try:
        from app.storage.mongodb_storage import MongoStorage

        storage = MongoStorage()
        await storage.connect()
        session = await storage.get_session(session_id)
    except Exception as e:
        logger.warning(f"record_user_star_rating_with_selected_options: load session failed: {e}")
        return 0

    if session is None:
        return 0

    targets = _iter_session_star_rating_targets(session)
    tasks = []
    for slot_name, seg in targets:
        od = _option_payload(getattr(seg, "selected_option", None))
        if not od:
            continue
        tasks.append(
            rl_svc.record_reward(
                user_id=user_id,
                action_type="user_star_rating",
                slot_name=slot_name,
                option=od,
                context=dict(ctx),
                session_mode=session_mode,
            )
        )
    if not tasks:
        return 0
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = sum(1 for r in results if isinstance(r, Exception))
    if errors:
        logger.warning(
            f"record_user_star_rating_with_selected_options: {errors}/{len(tasks)} segment updates raised errors"
        )
    return len(tasks) - errors


async def apply_personalized_recommendation_to_options(
    user_id: str,
    slot_name: str,
    options: List[Dict[str, Any]],
    *,
    session_mode: str = "ask",
) -> List[Dict[str, Any]]:
    """
    Re-rank options_pool by weighted_score + RL/FWL (same blend as Agent Mode),
    then mark exactly one option as recommended + tag แนะนำ.
    Used after CALL_SEARCH so PlanChoiceCard reflects personalized ranking for the user.
    """
    if not options:
        return options
    if not user_id or user_id == "anonymous":
        return options

    try:
        rl_svc = get_rl_service()
        pool = list(options)
        rl_scores = await rl_svc.get_option_scores(user_id, slot_name, pool, session_mode=session_mode)
        for i, opt in enumerate(pool):
            ws = float(opt.get("weighted_score", 0.5))
            q = float(rl_scores[i]) if i < len(rl_scores) else 0.0
            rl_bonus = (q + 1.0) / 2.0 * 0.20
            opt["_final_score"] = round(ws + rl_bonus, 4)

        pool.sort(key=lambda x: -x.get("_final_score", 0.0))

        for opt in pool:
            opt["recommended"] = False
            tags = opt.get("tags")
            if isinstance(tags, list):
                opt["tags"] = [t for t in tags if t != "แนะนำ"]

        top = pool[0]
        top["recommended"] = True
        if not isinstance(top.get("tags"), list):
            top["tags"] = []
        if "แนะนำ" not in top["tags"]:
            top["tags"].append("แนะนำ")

        return pool
    except Exception as e:
        logger.warning(f"apply_personalized_recommendation_to_options: {e}")
        return options
