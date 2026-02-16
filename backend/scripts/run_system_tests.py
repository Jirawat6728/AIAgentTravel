"""
ทดสอบระบบ backend แบบรวดเร็ว (ไม่เชื่อม MongoDB/Redis จริง)
Run: cd backend && .venv\\Scripts\\python scripts/run_system_tests.py
"""
import sys
import os

# โหลด path ของ backend
_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

# โหลด .env
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND, ".env"))
except Exception:
    pass

def test_imports():
    """ทดสอบ import โมดูลหลัก"""
    errors = []
    # Config (ไม่ต้องเชื่อม DB)
    try:
        from app.core.config import settings
        assert hasattr(settings, "gemini_model_name")
        print("[OK] app.core.config")
    except Exception as e:
        errors.append(f"config: {e}")
        print(f"[FAIL] app.core.config: {e}")

    # MCP tools
    try:
        from app.services.mcp_server import ALL_MCP_TOOLS
        n = len(ALL_MCP_TOOLS)
        names = [t["name"] for t in ALL_MCP_TOOLS]
        assert n >= 1, "No MCP tools"
        print(f"[OK] MCP tools count={n}, sample: {names[:3]}")
    except Exception as e:
        errors.append(f"mcp_server: {e}")
        print(f"[FAIL] mcp_server: {e}")

    # Weather MCP
    try:
        from app.services.mcp_weather import WEATHER_TOOLS, WeatherMCP
        assert "get_weather_forecast" in [t["name"] for t in WEATHER_TOOLS]
        print("[OK] mcp_weather")
    except Exception as e:
        errors.append(f"mcp_weather: {e}")
        print(f"[FAIL] mcp_weather: {e}")

    # Chat API (map option) - import เฉพาะฟังก์ชัน
    try:
        from app.api import chat
        out = chat._map_option_for_frontend({"category": "flight", "price_amount": 100}, 0)
        assert "id" in out and out.get("category") == "flight"
        print("[OK] chat._map_option_for_frontend")
    except Exception as e:
        errors.append(f"chat: {e}")
        print(f"[FAIL] chat: {e}")

    # Agent intelligence (validator) - โมดูล agent ใหญ่อาจโหลดช้า
    try:
        from app.engine.agent import agent_intelligence
        ok, _ = agent_intelligence.validator.validate_guests(1)
        assert ok
        print("[OK] agent_intelligence.validator")
    except Exception as e:
        errors.append(f"agent: {e}")
        print(f"[FAIL] agent: {e}")

    return errors

def test_normalize_payload():
    """ทดสอบ normalize payload (ไม่ต้องมี session)"""
    try:
        from app.engine.agent import TravelAgent
        from app.storage.interface import StorageInterface
        # Mock storage ที่ไม่ทำอะไร
        class MockStorage(StorageInterface):
            async def get_session(self, sid): return None
            async def save_session(self, session): pass
            async def get_chat_history(self, session_id: str, limit: int = 50): return []
            async def save_message(self, session_id: str, message: dict): return True
            async def update_title(self, session_id: str, title: str): return True
        agent = TravelAgent(storage=MockStorage())
        payload = {"destination": "Bangkok", "guests": 99, "start_date": "2025-01-01", "end_date": "2024-12-31"}
        out = agent._normalize_create_itinerary_payload(payload)
        assert out.get("guests") == 9, "guests should be clamped to 9"
        assert out.get("end_date") != "2024-12-31", "end_date should be fixed when before start_date"
        print("[OK] _normalize_create_itinerary_payload (guests clamp, end_date fix)")
    except Exception as e:
        print(f"[FAIL] normalize payload: {e}")
        return [str(e)]
    return []

def main():
    print("=" * 50)
    print("Backend System Tests (quick)")
    print("=" * 50)
    err1 = test_imports()
    err2 = test_normalize_payload()
    errors = err1 + err2
    print("=" * 50)
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        sys.exit(1)
    print("ALL PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
