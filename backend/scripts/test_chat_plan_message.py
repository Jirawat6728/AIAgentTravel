"""
Test chat with trip plan message (BKK->Seoul, Flight/Hotel/Transfer, PlanChoiceCard).
Run: cd backend && .venv\\Scripts\\python scripts/test_chat_plan_message.py
"""
import asyncio
import os
import sys
import io

# Windows console: use UTF-8 for Thai output
if sys.platform == "win32":
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    except Exception:
        pass

# โหลด .env และ path ของ backend
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_BACKEND_DIR, ".env"))

# ข้อความทดสอบตามที่ผู้ใช้ขอ
TEST_MESSAGE = (
    "ช่วยวางแผนทริปจากกรุงเทพไปโซล วันที่ 2026-01-16 ถึง 2026-01-19 ให้หน่อย "
    "ดึงข้อมูล Flight, Hotel, Transfer มาแสดงใน PlanChoiceCard แบบไม่จำกัดจำนวน"
)


async def main():
    from app.models.session import UserSession
    from app.storage.hybrid_storage import HybridStorage
    from app.services.llm import LLMServiceWithMCP
    from app.engine.agent import TravelAgent

    user_id = "test_user"
    chat_id = "test_chat_plan_seoul"
    session_id = f"{user_id}::{chat_id}"

    print("=" * 60)
    print("Test: Trip plan BKK -> Seoul (Flight, Hotel, Transfer)")
    print("=" * 60)
    print(f"Message: {TEST_MESSAGE[:80]}...")
    print()

    storage = HybridStorage()
    session = await storage.get_session(session_id)
    if not session:
        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            trip_id=chat_id,
            chat_id=chat_id,
        )
        await storage.save_session(session)
        print(f"[OK] Created new session: {session_id}")
    else:
        print(f"[OK] Loaded existing session: {session_id}")

    llm = LLMServiceWithMCP()
    agent = TravelAgent(storage=storage, llm_service=llm, agent_personality="friendly")

    print("\n[Wait] Calling agent.run_turn (may take 30-90s)...\n")
    response_text = await agent.run_turn(session_id, TEST_MESSAGE, mode="normal")

    print("-" * 60)
    print("Agent response:")
    print("-" * 60)
    print(response_text or "(no text)")
    print()

    updated = await storage.get_session(session_id)
    if updated and updated.trip_plan:
        tp = updated.trip_plan
        print("-" * 60)
        print("Trip state (for PlanChoiceCard):")
        print("-" * 60)
        all_segments = []
        if getattr(tp, "travel", None):
            t = tp.travel
            if getattr(t, "flights", None):
                all_segments.extend(t.flights.all_segments())
            all_segments.extend(getattr(t, "ground_transport", None) or [])
        if getattr(tp, "accommodation", None):
            all_segments.extend(getattr(tp.accommodation, "segments", None) or [])
        for i, seg in enumerate(all_segments):
            slot_name = getattr(seg, "slot_name", None) or getattr(seg, "segment_id", f"Segment_{i}")
            opts = getattr(seg, "options_pool", None) or []
            sel = getattr(seg, "selected_option", None)
            print(f"  - {slot_name}: options_pool={len(opts)} items, selected_option={bool(sel)}")
        print()
    print("Test done.")


if __name__ == "__main__":
    asyncio.run(main())
