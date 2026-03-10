"""
Selection Preferences Service — เรียนรู้จากประวัติการเลือก (Choice History) + RL
รวมกับ RL/ML เพื่อใช้ใน User Profile และ Agent Mode
"""

from __future__ import annotations
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import Counter

from app.core.logging import get_logger

logger = get_logger(__name__)

COLLECTION_CHOICE_HISTORY = "user_choice_history"
MAX_CHOICES_FOR_SUMMARY = 150
PRICE_BUCKET_LOW = 5000
PRICE_BUCKET_HIGH = 25000


def _get_db():
    from app.storage.connection_manager import ConnectionManager
    return ConnectionManager.get_instance().get_mongo_database()


async def _user_learn_from_choices(db, user_id: str) -> bool:
    """อ่านค่า preferences.learnFromMyChoices ของ user (default True)."""
    if not db or not user_id:
        return True
    try:
        user = await db["users"].find_one({"user_id": user_id}, {"preferences.learnFromMyChoices": 1})
        if not user:
            return True
        prefs = user.get("preferences") or {}
        return prefs.get("learnFromMyChoices", True)
    except Exception:
        return True


def _extract_from_option(slot_type: str, option_data: Any) -> Dict[str, Any]:
    """ดึง price, destination, origin, name จาก choice_data (flight/hotel/transport)."""
    out = {"price": None, "destination": None, "origin": None, "name": None, "slot_type": slot_type or "unknown"}
    if not isinstance(option_data, dict):
        return out
    # Flight
    flight = option_data.get("flight") or option_data
    if flight.get("segments") or flight.get("price_total") is not None or flight.get("price") is not None:
        segs = flight.get("segments") or []
        if segs:
            out["origin"] = segs[0].get("from") or segs[0].get("origin")
            out["destination"] = segs[-1].get("to") or segs[-1].get("destination")
        out["price"] = flight.get("price_total") or flight.get("price")
        out["name"] = flight.get("airline") or flight.get("carrier")
        return out
    # Hotel
    hotel = option_data.get("hotel") or option_data
    if hotel.get("hotelName") or hotel.get("name") or hotel.get("price_total") is not None:
        out["name"] = hotel.get("hotelName") or hotel.get("name")
        out["price"] = hotel.get("price_total") or hotel.get("price")
        out["destination"] = hotel.get("city") or hotel.get("destination") or hotel.get("area")
        return out
    # Transport
    transport = option_data.get("transport") or option_data
    if transport.get("type") or transport.get("mode") or transport.get("display_name"):
        out["name"] = transport.get("type") or transport.get("mode") or transport.get("display_name")
        out["price"] = transport.get("price_total") or transport.get("price")
        out["destination"] = transport.get("to") or transport.get("destination")
        out["origin"] = transport.get("from") or transport.get("origin")
        return out
    # Generic
    out["price"] = option_data.get("price_total") or option_data.get("price_amount") or option_data.get("price")
    out["name"] = option_data.get("display_name") or option_data.get("name") or option_data.get("airline")
    out["destination"] = option_data.get("destination") or option_data.get("to")
    out["origin"] = option_data.get("origin") or option_data.get("from")
    return out


async def record_choice(
    user_id: str,
    slot_name: str,
    option_data: Any,
    *,
    slot_type: Optional[str] = None,
) -> None:
    """
    บันทึกการเลือกตัวเลือกของผู้ใช้ (ใช้ร่วมกับ RL).
    จะบันทึกก็ต่อเมื่อ user มี preferences.learnFromMyChoices = True
    """
    if not user_id or user_id == "anonymous":
        return
    db = _get_db()
    if not db:
        return
    if not await _user_learn_from_choices(db, user_id):
        return
    slot = slot_type or slot_name
    extracted = _extract_from_option(slot, option_data)
    try:
        col = db[COLLECTION_CHOICE_HISTORY]
        doc = {
            "user_id": user_id,
            "slot_name": slot_name,
            "slot_type": slot,
            "price": extracted["price"],
            "destination": extracted["destination"],
            "origin": extracted["origin"],
            "name": extracted["name"],
            "created_at": datetime.utcnow(),
        }
        await col.insert_one(doc)
        # Keep per-user history bounded
        count = await col.count_documents({"user_id": user_id})
        if count > MAX_CHOICES_FOR_SUMMARY * 2:
            oldest = await col.find({"user_id": user_id}).sort("created_at", 1).limit(count - MAX_CHOICES_FOR_SUMMARY).to_list(length=count - MAX_CHOICES_FOR_SUMMARY)
            for d in oldest:
                await col.delete_one({"_id": d["_id"]})
    except Exception as e:
        logger.warning(f"SelectionPreferences record_choice error: {e}")


async def get_selection_preferences_summary(user_id: str) -> str:
    """
    สรุปความชอบจากการเลือก (Choice History) + สถิติจาก RL
    ใช้ใน User Profile และ Agent Mode selection prompt.
    คืนค่าว่างถ้า learnFromMyChoices = False หรือไม่มีข้อมูล
    """
    if not user_id or user_id == "anonymous":
        return ""
    db = _get_db()
    if not db:
        return ""
    if not await _user_learn_from_choices(db, user_id):
        return ""

    parts: List[str] = []
    try:
        col = db[COLLECTION_CHOICE_HISTORY]
        cursor = col.find({"user_id": user_id}).sort("created_at", -1).limit(MAX_CHOICES_FOR_SUMMARY)
        choices = await cursor.to_list(length=MAX_CHOICES_FOR_SUMMARY)
        if not choices:
            # User ใหม่: ยังไม่มี choice history — ใช้ความพึงพอใจจากคะแนนดาว (trip_evaluations / RL) เพื่อให้ AI รู้จักพฤติกรรมจากแค่ 1–2 ทริป
            satisfaction_line = await _last_satisfaction_line(db, user_id)
            if satisfaction_line:
                parts.append(satisfaction_line)
            rl_part = await _rl_aggregate_summary(db, user_id)
            if rl_part:
                parts.append(rl_part)
            return "\n".join(parts) if parts else ""

        def _num(v):
            if v is None: return None
            try: return float(v)
            except (TypeError, ValueError): return None
        prices = [_num(c["price"]) for c in choices if _num(c.get("price")) is not None]
        destinations = [str(c["destination"]).strip() for c in choices if c.get("destination")]
        origins = [str(c["origin"]).strip() for c in choices if c.get("origin")]
        names = [str(c["name"]).strip() for c in choices if c.get("name")]

        if prices:
            med = sorted(prices)[len(prices) // 2]
            if med <= PRICE_BUCKET_LOW:
                parts.append(f"ช่วงราคาที่เลือกบ่อย: ประหยัด (ประมาณ ≤{PRICE_BUCKET_LOW:,} บาท)")
            elif med <= PRICE_BUCKET_HIGH:
                parts.append(f"ช่วงราคาที่เลือกบ่อย: กลาง (ประมาณ {PRICE_BUCKET_LOW:,}-{PRICE_BUCKET_HIGH:,} บาท)")
            else:
                parts.append(f"ช่วงราคาที่เลือกบ่อย: สูง (ประมาณ >{PRICE_BUCKET_HIGH:,} บาท)")

        for label, counter in [
            ("จุดหมายที่ไปบ่อย", Counter(destinations).most_common(5)),
            ("ต้นทางที่ใช้บ่อย", Counter(origins).most_common(5)),
            ("สายการบิน/ที่พัก/ประเภทที่เลือกบ่อย", Counter(names).most_common(5)),
        ]:
            top = [t for t, _ in counter if t]
            if top:
                parts.append(f"{label}: {', '.join(top)}")

        rl_part = await _rl_aggregate_summary(db, user_id)
        if rl_part:
            parts.append(rl_part)
        # ความพึงพอใจล่าสุดจากคะแนนดาว (ทั้ง User ใหม่และเก่า)
        satisfaction_line = await _last_satisfaction_line(db, user_id)
        if satisfaction_line:
            parts.append(satisfaction_line)
    except Exception as e:
        logger.warning(f"SelectionPreferences get_selection_preferences_summary error: {e}")

    return "\n".join(parts) if parts else ""


async def _last_satisfaction_line(db, user_id: str) -> str:
    """ความพึงพอใจล่าสุดจาก User (คะแนนดาว) — ใช้เมื่อยังมี choice น้อย เพื่อให้ AI รู้จักพฤติกรรมจาก 1–2 ทริป"""
    try:
        from app.services.trip_evaluations import COLLECTION_NAME
        col = db[COLLECTION_NAME]
        if not col:
            return ""
        doc = await col.find_one(
            {"user_id": user_id, "user_stars": {"$exists": True, "$ne": None}},
            {"user_stars": 1},
            sort=[("updated_at", -1)],
        )
        if doc and doc.get("user_stars") is not None:
            stars = doc["user_stars"]
            return f"ความพึงพอใจล่าสุดจาก User (คะแนนดาว): {stars} ดาว — ใช้เป็นสัญญาณว่าผู้ใช้ชอบระดับไหน"
        return ""
    except Exception:
        return ""


async def _rl_aggregate_summary(db, user_id: str) -> str:
    """สรุปจาก RL: slot ที่ user เลือกบ่อย / ปฏิเสธบ่อย (จาก user_feedback_history + user_preference_scores)."""
    try:
        rewards_col = db["user_feedback_history"]
        qtable_col = db["user_preference_scores"]
        recent = await rewards_col.find({"user_id": user_id}).sort("created_at", -1).limit(200).to_list(length=200)
        q_entries = await qtable_col.find({"user_id": user_id}).to_list(length=500)
        selected_slots = [r["slot_name"] for r in recent if r.get("action_type") == "select_option"]
        if not selected_slots and not q_entries:
            return ""
        lines = []
        if selected_slots:
            slot_counts = Counter(selected_slots)
            top_slots = slot_counts.most_common(3)
            slot_labels = {"flights_outbound": "เที่ยวบินขาไป", "flights_inbound": "เที่ยวบินขากลับ", "accommodation": "ที่พัก", "ground_transport": "การเดินทาง"}
            names = [slot_labels.get(s, s) for s, _ in top_slots]
            if names:
                lines.append(f"RL: ผู้ใช้เคยเลือกตัวเลือกในหมวด {', '.join(names)} บ่อย")
        high_q = [q for q in q_entries if (q.get("q_value") or 0) > 0.1]
        if high_q and not lines:
            lines.append("RL: มีประวัติชอบตัวเลือกที่เคยเลือกในอดีต — ควรให้ความสำคัญกับ RL scores ใน prompt")
        return " ".join(lines) if lines else ""
    except Exception:
        return ""
