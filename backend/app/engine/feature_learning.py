"""
Feature Weight Learning (FWL) — ML-style Online Learning สำหรับ AI Travel Agent
เรียนรู้ว่า user ชอบ feature แบบไหน จาก feedback จริง (ดาว / เลือก / ปฏิเสธ)
ใช้ Online Logistic Regression (Gradient Descent ต่อ user) เก็บ weights ใน MongoDB

แยกเรียนรู้ตาม Mode:
  ASK mode  → user ตัดสินใจเอง → เรียนรู้ว่า user ชอบ feature อะไร
  AGENT mode → AI ตัดสินใจให้ → เรียนรู้ว่า AI เลือก feature ถูก/ผิดตาม feedback

Schema (collection: user_feature_weights):
  user_id, slot_type, mode, weights: {feature: float}, update_count, last_updated

Features ที่เรียนรู้:
  ✈ Flight: price_bucket, is_direct, duration_bucket, cabin_class, airline_budget
  🏨 Hotel:  hotel_stars, price_bucket
  🚗 Transport: is_private, price_bucket
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_FWL = "user_feature_weights"

# ─── Hyperparameters ───────────────────────────────────────────────────────────
LEARNING_RATE   = 0.15   # α — ขนาด gradient step
REGULARIZATION  = 0.01   # λ — L2 decay ป้องกัน overfitting
MAX_WEIGHT      = 3.0    # clamping สูงสุด
LABEL_MAP = {
    # Positive feedback → y = 1.0
    "select_option": 1.0,
    "book": 1.0,
    "complete_booking": 1.0,
    "positive_feedback": 1.0,
    "user_star_rating": None,   # คำนวณจาก stars
    # Negative feedback → y = 0.0
    "reject": 0.0,
    "reject_option": 0.0,
    "cancel": 0.0,
    "cancel_booking": 0.0,
    "negative_feedback": 0.0,
    "edit": 0.5,       # แก้ไข = กลางๆ
    "edit_selection": 0.5,
}


# ─── Feature Extraction ────────────────────────────────────────────────────────

def _price_bucket(price: Any) -> float:
    """แปลงราคา → 0-4 bucket (very low → very high) แล้ว normalize 0-1"""
    try:
        p = float(price or 0)
    except (TypeError, ValueError):
        return 0.5
    # Flight buckets: <3k, 3k-8k, 8k-15k, 15k-30k, >30k
    thresholds = [3000, 8000, 15000, 30000]
    bucket = sum(1 for t in thresholds if p >= t)
    return bucket / 4.0


def _hotel_price_bucket(price: Any) -> float:
    """ราคาโรงแรมต่อคืน → 0-4 bucket"""
    try:
        p = float(price or 0)
    except (TypeError, ValueError):
        return 0.5
    thresholds = [500, 1500, 3000, 6000]
    bucket = sum(1 for t in thresholds if p >= t)
    return bucket / 4.0


def _duration_bucket(minutes: Any) -> float:
    """ชั่วโมงบิน → 0-3 bucket"""
    try:
        m = float(minutes or 0)
    except (TypeError, ValueError):
        return 0.5
    if m < 90:
        return 0.0
    if m < 240:
        return 0.25
    if m < 480:
        return 0.5
    return 1.0


def _cabin_index(cabin: str) -> float:
    """Economy → 0.0, Business → 0.67, First → 1.0"""
    c = (cabin or "").lower()
    if "first" in c:
        return 1.0
    if "business" in c or "biz" in c:
        return 0.67
    if "premium" in c:
        return 0.33
    return 0.0


LOW_COST_AIRLINES = {
    "pg", "fd", "dd", "nok", "tg", "vy", "w6", "fr", "u2", "sg", "ak",
    "qz", "3k", "ib", "vz", "sl", "thai lion", "scoot", "airasia",
    "nok air", "thai vietjet", "vietjet", "lion", "cebu", "indigo",
}

def _is_budget_airline(airline: str) -> float:
    a = (airline or "").lower()
    if any(k in a for k in LOW_COST_AIRLINES):
        return 1.0
    return 0.0


def extract_features(option: Any, slot: str) -> Dict[str, float]:
    """
    แปลง option dict → feature dict (ทุก value อยู่ใน [0, 1])
    slot: 'flights_outbound' | 'flights_inbound' | 'accommodation' | 'ground_transport' | generic
    """
    if not isinstance(option, dict):
        return {}

    slot_lower = (slot or "").lower()
    feats: Dict[str, float] = {}

    if "flight" in slot_lower or "outbound" in slot_lower or "inbound" in slot_lower:
        # ✈ Flight features
        price = option.get("price_total") or option.get("price_amount") or option.get("price", 0)
        feats["f_price"] = _price_bucket(price)

        cabin = option.get("cabin_class") or ""
        if not cabin:
            segs = option.get("segments") or []
            if segs and isinstance(segs[0], dict):
                cabin = segs[0].get("cabin_class") or ""
        feats["f_cabin"] = _cabin_index(cabin)

        # Direct flight
        stops = option.get("stops")
        if stops is None:
            segs = option.get("segments") or []
            stops = max(0, len(segs) - 1) if segs else 0
        feats["f_is_direct"] = 1.0 if (stops == 0) else 0.0

        # Duration
        dur = option.get("total_duration_minutes") or option.get("duration_minutes") or 0
        if not dur:
            segs = option.get("segments") or []
            dur = sum(s.get("duration_minutes", 0) for s in segs if isinstance(s, dict))
        feats["f_duration"] = _duration_bucket(dur)

        # Airline budget
        airline = option.get("airline") or option.get("carrier") or ""
        if not airline:
            segs = option.get("segments") or []
            if segs and isinstance(segs[0], dict):
                airline = segs[0].get("airline") or segs[0].get("carrier") or ""
        feats["f_budget_airline"] = _is_budget_airline(airline)

    elif "accommodation" in slot_lower or "hotel" in slot_lower:
        # 🏨 Hotel features
        price = option.get("price_total") or option.get("price_per_night") or option.get("price", 0)
        feats["h_price"] = _hotel_price_bucket(price)

        stars = option.get("stars") or option.get("rating") or option.get("category") or 3
        try:
            feats["h_stars"] = min(1.0, max(0.0, (float(stars) - 1) / 4.0))
        except (TypeError, ValueError):
            feats["h_stars"] = 0.5

    elif "transport" in slot_lower or "ground" in slot_lower:
        # 🚗 Transport features
        price = option.get("price_total") or option.get("price", 0)
        feats["t_price"] = _price_bucket(price)

        transport_type = (option.get("type") or option.get("mode") or "").lower()
        feats["t_is_private"] = 1.0 if any(k in transport_type for k in ("private", "taxi", "sedan")) else 0.0

    return feats


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid"""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    e = math.exp(x)
    return e / (1.0 + e)


def _dot(weights: Dict[str, float], feats: Dict[str, float]) -> float:
    return sum(weights.get(k, 0.0) * v for k, v in feats.items())


def _label_from_action(action_type: str, context: Optional[Dict] = None) -> Optional[float]:
    """คืน label y ∈ [0, 1] หรือ None ถ้าข้ามการอัปเดต"""
    if action_type == "user_star_rating":
        stars = (context or {}).get("stars", 3)
        try:
            return (float(stars) - 1) / 4.0   # 1★→0.0, 5★→1.0
        except (TypeError, ValueError):
            return None
    return LABEL_MAP.get(action_type)


# ─── Feature Weight Learner ────────────────────────────────────────────────────

class FeatureWeightLearner:
    """
    Online Logistic Regression ต่อ user per slot_type.
    เมื่อ user ให้ feedback → อัปเดต weights ทันที (no batch, no retraining).

    Score(option) = sigmoid(w · features)  ∈ [0, 1]
    """

    def _get_db(self):
        from app.storage.connection_manager import ConnectionManager
        return ConnectionManager.get_instance().get_mongo_database()

    # ── Load / Save weights ──────────────────────────────────────────────────

    async def _load_weights(self, user_id: str, slot_type: str, mode: str = "") -> Dict[str, float]:
        db = self._get_db()
        if db is None:
            return {}
        try:
            query = {"user_id": user_id, "slot_type": slot_type}
            if mode:
                query["mode"] = mode
            doc = await db[COLLECTION_FWL].find_one(query)
            return dict(doc.get("weights", {})) if doc else {}
        except Exception as e:
            logger.debug(f"FWL load_weights error: {e}")
            return {}

    async def _save_weights(
        self,
        user_id: str,
        slot_type: str,
        weights: Dict[str, float],
        update_count: int,
        mode: str = "",
    ) -> None:
        db = self._get_db()
        if db is None:
            return
        try:
            from datetime import datetime
            query = {"user_id": user_id, "slot_type": slot_type}
            if mode:
                query["mode"] = mode
            await db[COLLECTION_FWL].update_one(
                query,
                {"$set": {
                    "weights": weights,
                    "update_count": update_count,
                    "mode": mode or "any",
                    "last_updated": datetime.utcnow().isoformat(),
                }},
                upsert=True,
            )
        except Exception as e:
            logger.debug(f"FWL save_weights error: {e}")

    # ── Update (Online Gradient Descent) ──────────────────────────────────────

    async def update(
        self,
        user_id: str,
        slot_name: str,
        option: Any,
        action_type: str,
        context: Optional[Dict] = None,
        session_mode: str = "",
    ) -> None:
        """อัปเดต weights เมื่อ user ให้ feedback
        session_mode: 'ask' | 'agent' | 'chat' | 'booking' | '' (any)
        ASK = user ตัดสินใจเอง, AGENT = AI ตัดสินใจ
        """
        if not user_id:
            return
        y = _label_from_action(action_type, context)
        if y is None:
            return

        feats = extract_features(option, slot_name)
        if not feats:
            return

        slot_type = _normalize_slot(slot_name)
        # แยก mode key: ask/agent เรียนรู้แยกกัน; chat/booking/'' รวมเป็น 'any'
        mode_key = session_mode.lower().strip() if session_mode.lower().strip() in ("ask", "agent") else "any"
        db = self._get_db()
        if db is None:
            return

        try:
            query = {"user_id": user_id, "slot_type": slot_type, "mode": mode_key}
            doc = await db[COLLECTION_FWL].find_one(query)
            weights = dict(doc.get("weights", {})) if doc else {}
            update_count = (doc.get("update_count", 0) if doc else 0) + 1

            # prediction
            y_hat = _sigmoid(_dot(weights, feats))
            error = y - y_hat

            # gradient update with L2 regularization
            for feat, x in feats.items():
                grad = error * x - REGULARIZATION * weights.get(feat, 0.0)
                new_w = weights.get(feat, 0.0) + LEARNING_RATE * grad
                weights[feat] = max(-MAX_WEIGHT, min(MAX_WEIGHT, new_w))

            await self._save_weights(user_id, slot_type, weights, update_count, mode=mode_key)
            logger.info(
                f"\U0001f52c FWL update: user={user_id[:8]} slot={slot_type} mode={mode_key} "
                f"action={action_type} y={y:.2f} \u0177={y_hat:.2f} error={error:+.2f}"
            )
        except Exception as e:
            logger.warning(f"FWL update error: {e}")

    # ── Score options ──────────────────────────────────────────────────────────

    async def score_options(
        self,
        user_id: str,
        slot_name: str,
        options: List[Any],
        session_mode: str = "",
    ) -> List[float]:
        """
        คืน FWL score [0, 1] ต่อแต่ละ option.
        0.5 = ไม่มีข้อมูล (neutral).
        ผสม weights จากทั้ง mode เฉพาะ (ask/agent) และ 'any' เพื่อความครอบคลุม.
        """
        if not user_id or not options:
            return [0.5] * len(options)

        slot_type = _normalize_slot(slot_name)
        mode_key = session_mode.lower().strip() if session_mode.lower().strip() in ("ask", "agent") else "any"

        # โหลด weights: ใช้ mode-specific ก่อน fallback ไป 'any'
        weights = await self._load_weights(user_id, slot_type, mode_key)
        if not weights and mode_key != "any":
            weights = await self._load_weights(user_id, slot_type, "any")
        if not weights:
            return [0.5] * len(options)

        scores = []
        for opt in options:
            feats = extract_features(opt, slot_name)
            if not feats:
                scores.append(0.5)
            else:
                raw = _dot(weights, feats)
                scores.append(round(_sigmoid(raw), 4))
        return scores

    # ── Human-readable preference summary ─────────────────────────────────────

    async def get_preference_summary(self, user_id: str) -> str:
        """สร้างสรุปความชอบที่ AI เรียนรู้ได้ (สำหรับ LLM context)"""
        db = self._get_db()
        if db is None:
            return ""
        try:
            cursor = db[COLLECTION_FWL].find({"user_id": user_id})
            docs = await cursor.to_list(length=10)
            if not docs:
                return ""

            lines = []
            for doc in docs:
                slot = doc.get("slot_type", "")
                weights = doc.get("weights") or {}
                if not weights:
                    continue
                # top positive / negative
                sorted_w = sorted(weights.items(), key=lambda x: x[1], reverse=True)
                positives = [(k, v) for k, v in sorted_w if v > 0.1][:3]
                negatives = [(k, v) for k, v in sorted_w if v < -0.1][:2]
                if positives or negatives:
                    desc = f"[{slot}] ชอบ: " + ", ".join(f"{_feat_label(k)}({v:+.2f})" for k, v in positives)
                    if negatives:
                        desc += " | ไม่ชอบ: " + ", ".join(f"{_feat_label(k)}({v:+.2f})" for k, v in negatives)
                    lines.append(desc)

            if not lines:
                return ""
            return (
                "\n=== 🔬 ML Feature Preference (เรียนรู้จาก feedback) ===\n"
                + "\n".join(lines)
                + "\nใช้ข้อมูลนี้เพื่อเลือกตัวเลือกที่ตรงกับ feature ที่ user ชอบ\n"
            )
        except Exception as e:
            logger.debug(f"FWL preference_summary error: {e}")
            return ""

    async def get_user_weights_doc(self, user_id: str) -> List[Dict]:
        """ดึง weights ทั้งหมดของ user (สำหรับ admin dashboard)"""
        db = self._get_db()
        if db is None:
            return []
        try:
            cursor = db[COLLECTION_FWL].find({"user_id": user_id}, {"_id": 0})
            return await cursor.to_list(length=20)
        except Exception:
            return []


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _normalize_slot(slot_name: str) -> str:
    """Normalize slot name → เป็น grouping key"""
    s = (slot_name or "").lower()
    if "flight" in s or "outbound" in s or "inbound" in s:
        return "flight"
    if "hotel" in s or "accommodation" in s:
        return "hotel"
    if "transport" in s or "ground" in s:
        return "transport"
    return s or "general"


_FEAT_LABELS: Dict[str, str] = {
    "f_price": "ราคาสูง",
    "f_cabin": "ชั้นธุรกิจ",
    "f_is_direct": "บินตรง",
    "f_duration": "เที่ยวบินยาว",
    "f_budget_airline": "สายการบิน LCC",
    "h_stars": "โรงแรมระดับสูง",
    "h_price": "ที่พักราคาสูง",
    "t_price": "รถราคาสูง",
    "t_is_private": "รถส่วนตัว",
}


def _feat_label(feat_key: str) -> str:
    return _FEAT_LABELS.get(feat_key, feat_key)


# ─── Singleton ────────────────────────────────────────────────────────────────

_fwl_instance: Optional[FeatureWeightLearner] = None


def get_feature_learner() -> FeatureWeightLearner:
    """Get singleton FeatureWeightLearner"""
    global _fwl_instance
    if _fwl_instance is None:
        _fwl_instance = FeatureWeightLearner()
    return _fwl_instance
