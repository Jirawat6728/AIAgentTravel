"""
ทดสอบระบบวางแผนตั้งแต่ 0 (START FROM ZERO)
- Session เริ่มต้นแบบไม่มี segments (แผนว่าง)
- ส่งข้อความให้ AI ต้องทำ CREATE_ITINERARY ก่อน (ไม่ข้ามไป CALL_SEARCH)

รัน: cd backend && .venv\\Scripts\\python scripts/test_plan_from_zero.py
"""
import asyncio
import os
import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

# ข้อความทดสอบ "เริ่มจากศูนย์" — มีจุดหมาย+ระยะเวลา เพื่อให้ Controller ทำ CREATE_ITINERARY
TEST_MESSAGES = [
    "อยากไปภูเก็ต 3 วัน",
    "ช่วยวางแผนทริปไปเกาหลี 5 วันให้หน่อย",
]
DEFAULT_MESSAGE = TEST_MESSAGES[0]


def _count_segments(tp):
    """นับจำนวน segments ใน trip plan"""
    if not tp:
        return 0
    n = 0
    if getattr(tp, "travel", None):
        t = tp.travel
        if getattr(t, "flights", None):
            n += len(t.flights.outbound or []) + len(t.flights.inbound or [])
        n += len(getattr(t, "ground_transport", None) or [])
    if getattr(tp, "accommodation", None):
        n += len(getattr(tp.accommodation, "segments", None) or [])
    return n


async def main():
    from app.models.session import UserSession
    from app.storage.mongodb_storage import MongoStorage
    from app.services.llm import LLMServiceWithMCP
    from app.engine.agent import TravelAgent

    user_id = "test_user"
    chat_id = "test_plan_from_zero"
    session_id = f"{user_id}::{chat_id}"
    message = os.getenv("TEST_PLAN_MESSAGE", DEFAULT_MESSAGE)

    print("=" * 60)
    print("ทดสอบระบบวางแผนตั้งแต่ 0 (START FROM ZERO)")
    print("=" * 60)
    print(f"Session: {session_id}")
    print(f"ข้อความ: {message}")
    print()

    storage = MongoStorage()
    await storage.connect()

    # เริ่มจากแผนว่าง: ถ้ามี session อยู่แล้ว ให้ล้างข้อมูลแผน (เหลือแค่ session ว่าง)
    existing = await storage.get_session(session_id)
    if existing:
        cleared = await storage.clear_session_data(session_id)
        print(f"[OK] Cleared existing session (plan from zero): {cleared}")
    else:
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            trip_id=chat_id,
            chat_id=chat_id,
        )
        await storage.save_session(session)
        print(f"[OK] Created new empty session: {session_id}")

    # ตรวจว่าแผนว่างจริง
    after_reset = await storage.get_session(session_id)
    seg_count = _count_segments(after_reset.trip_plan if after_reset else None)
    print(f"[OK] Segments ก่อนส่งข้อความ: {seg_count} (ต้องเป็น 0)")
    print()

    llm = LLMServiceWithMCP()
    agent = TravelAgent(storage=storage, llm_service=llm, agent_personality="friendly")

    print("[Wait] เรียก agent.run_turn (อาจใช้เวลา 30–90 วินาที)...")
    print()
    response_text = await agent.run_turn(session_id, message, mode="normal")

    print("-" * 60)
    print("คำตอบจาก AI:")
    print("-" * 60)
    print(response_text or "(ไม่มีข้อความ)")
    print()

    updated = await storage.get_session(session_id)
    if updated and updated.trip_plan:
        tp = updated.trip_plan
        seg_count = _count_segments(tp)
        print("-" * 60)
        print("สถานะแผนหลัง CREATE_ITINERARY:")
        print("-" * 60)
        print(f"  จำนวน segments: {seg_count}")
        all_segments = []
        if getattr(tp, "travel", None):
            t = tp.travel
            if getattr(t, "flights", None):
                all_segments.extend(t.flights.outbound or [])
                all_segments.extend(t.flights.inbound or [])
            all_segments.extend(getattr(t, "ground_transport", None) or [])
        if getattr(tp, "accommodation", None):
            all_segments.extend(getattr(tp.accommodation, "segments", None) or [])
        for i, seg in enumerate(all_segments):
            slot_name = getattr(seg, "slot_name", None) or getattr(seg, "segment_id", f"Segment_{i}")
            opts = getattr(seg, "options_pool", None) or []
            sel = getattr(seg, "selected_option", None)
            print(f"  - {slot_name}: options={len(opts)}, selected={bool(sel)}")
        if seg_count > 0:
            print()
            print("[OK] ระบบวางแผนตั้งแต่ 0 ทำงานถูกต้อง: มี segments หลัง CREATE_ITINERARY")
        else:
            print()
            print("[WARN] ยังไม่มี segments — อาจเป็น ASK_USER หรือ Controller ยังไม่สร้างแผน")
    else:
        print("[WARN] ไม่มี trip_plan หลัง run_turn")

    print()
    print("ทดสอบเสร็จสิ้น.")


if __name__ == "__main__":
    asyncio.run(main())
