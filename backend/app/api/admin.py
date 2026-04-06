"""
เราเตอร์สำหรับผู้ดูแลระบบและการดีบัก
ให้สถานะระบบ, บันทึก, และตรวจสอบสุขภาพของบริการ
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import os
import psutil
import asyncio
import json
import time
import hashlib
import hmac
import secrets
import base64
from datetime import datetime
from pathlib import Path
from starlette.requests import Request

from app.core.config import settings
from app.core.logging import get_logger
from app.storage.connection_manager import MongoConnectionManager
from app.services.llm import LLMService
from app.services.agent_monitor import agent_monitor
from app.services.memory import MemoryService
from app.services.options_cache import get_options_cache

logger = get_logger(__name__)

# Cookie-based admin session (สำหรับหน้า login แทน Basic Auth popup)
ADMIN_SESSION_COOKIE = "admin_session"
ADMIN_SESSION_MAX_AGE = 86400 * 1  # 1 day


def _admin_session_secret() -> bytes:
    return (settings.admin_password or "admin-fallback").encode("utf-8")


def create_admin_session_token() -> str:
    """สร้าง signed token สำหรับ admin session cookie"""
    expiry = str(int(time.time()) + ADMIN_SESSION_MAX_AGE)
    payload = expiry + ":admin"
    sig = hmac.new(_admin_session_secret(), payload.encode(), "sha256").hexdigest()[:32]
    raw = f"{payload}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")


def verify_admin_session_token(token: str) -> bool:
    """ตรวจสอบ admin session token ว่าถูกต้องและยังไม่หมดอายุ"""
    if not token or not settings.admin_password:
        return False
    try:
        raw = base64.urlsafe_b64decode(token + "==")
        payload, sig = raw.decode().rsplit(".", 1)
        expected = hmac.new(_admin_session_secret(), payload.encode(), "sha256").hexdigest()[:32]
        if not secrets.compare_digest(sig, expected):
            return False
        expiry_str = payload.split(":")[0]
        return int(expiry_str) > int(time.time())
    except Exception:
        return False


def serialize_datetime(obj: Any) -> Any:
    """
    Recursively serialize datetime objects to ISO format strings
    Handles dicts, lists, and nested structures
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: serialize_datetime(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        # Handle objects with __dict__ (like Pydantic models)
        return serialize_datetime(obj.__dict__)
    else:
        return obj


def _clamp(value: float, min_v: float, max_v: float) -> float:
    return max(min_v, min(max_v, value))


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _trip_user_satisfaction_pct(trip: Dict[str, Any]) -> Optional[float]:
    """
    ความพึงพอใจผู้ใช้เป็นสเกล 0–100% ให้สอดคล้องกับ /api/chat/agent-feedback:
    ใช้ satisfaction_pct จาก DB ถ้ามี ไม่เช่นนั้นแปลงจากดาวรวม (1–5) เทียบ %
    """
    sp = _safe_float(trip.get("satisfaction_pct"))
    if sp is not None:
        return round(_clamp(sp, 0.0, 100.0), 1)
    stars = _safe_float(trip.get("user_stars"))
    if stars is not None:
        stars = _clamp(stars, 1.0, 5.0)
        return round((stars / 5.0) * 100.0, 1)
    return None


def _estimate_self_ai_score(trip: Dict[str, Any]) -> int:
    """
    ประเมินคะแนน AI อัตโนมัติเมื่อยังไม่มีคะแนนจริงจาก evaluator
    ใช้สัญญาณพื้นฐานจาก mode/source/status และดาวจากผู้ใช้ (ถ้ามี)
    """
    mode = str(trip.get("mode") or "").strip().lower()
    source = str(trip.get("source") or "").strip().lower()
    # booking_status: ดึงจาก trip โดยตรง; สำหรับ source=chat ให้ใช้ status ด้วย (บาง session มีสถานะ)
    booking_status = str(
        trip.get("booking_status") or trip.get("status") or ""
    ).strip().lower()
    user_sat_pct = _trip_user_satisfaction_pct(trip)

    baseline_by_mode = {
        "agent": 78.0,
        "ask": 72.0,
        "chat": 72.0,
        "booking": 76.0,
    }
    baseline = baseline_by_mode.get(mode, 74.0)
    if source == "booking":
        baseline = max(baseline, 76.0)

    if booking_status in {"confirmed", "completed", "paid", "success"}:
        baseline += 6.0
    elif booking_status in {"pending", "processing", "pending_payment"}:
        baseline += 2.0
    elif booking_status in {"failed", "cancelled", "rejected", "error"}:
        baseline -= 8.0

    if trip.get("auto_booked") is True:
        baseline += 3.0

    if user_sat_pct is not None:
        score = (baseline * 0.55) + (float(user_sat_pct) * 0.45)
    else:
        score = baseline

    return int(round(_clamp(score, 45.0, 98.0)))


router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBasic()
security_optional = HTTPBasic(auto_error=False)

START_TIME = time.time()


def get_admin_login_html(error: bool = False) -> str:
    """
    หน้า login ของ Admin (แทน Basic Auth popup ของเบราว์เซอร์)
    """
    err_block = (
        '<div class="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg mb-2">Invalid username or password.</div>'
        if error else ""
    )
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Login - AI Travel Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100 min-h-screen flex items-center justify-center font-sans">
    <div class="w-full max-w-md">
        <div class="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
            <div class="text-center mb-8">
                <h1 class="text-2xl font-bold text-slate-800">Admin Dashboard</h1>
                <p class="text-sm text-slate-500 mt-1">AI Travel Agent — เข้าสู่ระบบเพื่อจัดการระบบ</p>
            </div>
            <form method="post" action="/admin/login" class="space-y-5">
                {err_block}
                <div>
                    <label for="username" class="block text-sm font-medium text-slate-700 mb-1">Username</label>
                    <input type="text" id="username" name="username" required
                        class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="admin" autocomplete="username">
                </div>
                <div>
                    <label for="password" class="block text-sm font-medium text-slate-700 mb-1">Password</label>
                    <input type="password" id="password" name="password" required
                        class="w-full px-4 py-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                        placeholder="••••••••" autocomplete="current-password">
                </div>
                <button type="submit"
                    class="w-full py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2">
                    Sign in
                </button>
            </form>
            <p class="text-xs text-slate-400 mt-4 text-center">Authorization required by this site</p>
        </div>
    </div>
</body>
</html>"""


def get_admin_dashboard_html() -> str:
    """
    Return admin dashboard HTML (served from backend, แยกจาก frontend).
    ใช้เมื่อเปิด http://localhost:8000/admin — ข้อมูลดึงจาก /api/admin/*
    """
    return """<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DashBoard - AI Travel Agent</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans">
    <div class="max-w-6xl mx-auto px-4 py-6">
        <header class="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
                <h1 class="text-2xl font-bold text-gray-900">DashBoard</h1>
                <p class="text-sm text-gray-500">AI Travel Agent - Backend (แยกจาก Frontend)</p>
            </div>
            <button id="btnRefresh" onclick="refreshAll()" class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">🔄 โหลดใหม่ทั้งหมด</button>
        </header>

        <div id="error" class="hidden bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4"></div>

        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-lg font-bold text-gray-900 mb-4">🔌 Services Status</h2>
                <div id="services" class="space-y-2 text-sm">กำลังโหลด...</div>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h2 class="text-lg font-bold text-gray-900 mb-4">⚙️ Config & System</h2>
                <div id="config" class="space-y-1 text-sm">กำลังโหลด...</div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-indigo-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">📊 ตัวชี้วัดผลความแม่นยำ / การเรียนรู้ AI (ต่อ User)</h2>
                <button onclick="loadAILearningMetrics()" class="text-sm text-indigo-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6">
                <div id="aiLearningMetrics" class="text-sm space-y-4">กำลังโหลด...</div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-emerald-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">📈 คะแนน AI ต่อทริป + ความสามารถรวม + คะแนนเรียนรู้ต่อ User</h2>
                <button onclick="loadAIScores()" class="text-sm text-emerald-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6 space-y-6">
                <div id="aiScoresOverall" class="text-sm">กำลังโหลด...</div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">คะแนนเรียนรู้ของ AI ต่อ User</h3>
                    <div id="aiScoresPerUser" class="overflow-x-auto">—</div>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">คะแนน AI ในแต่ละทริป (ล่าสุด)</h3>
                    <div id="aiScoresTrips" class="overflow-x-auto text-sm">—</div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-sky-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">🧩 AI Trip Planning Flow — กระบวนการคิดและการเลือก Choice ต่อทริป</h2>
                <button onclick="loadAITripPlanningFlow()" class="text-sm text-sky-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6 space-y-4">
                <p class="text-sm text-gray-600">
                    แสดงภาพรวมว่าในแต่ละทริป AI วางแผนอย่างไร: รับ context อะไร, สร้าง candidate choices อะไรบ้าง, ให้คะแนน/จัดอันดับอย่างไร และเลือก choice สุดท้ายจากเหตุผลอะไร
                </p>
                <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div>
                        <h3 class="font-semibold text-gray-800 mb-2">สรุป Workflow ต่อทริป</h3>
                        <div id="tripPlanningFlowSummary" class="text-sm text-gray-700">กำลังโหลด...</div>
                    </div>
                    <div>
                        <h3 class="font-semibold text-gray-800 mb-2">ตัวอย่างลำดับขั้นตอน (ล่าสุด)</h3>
                        <div id="tripPlanningFlowSteps" class="text-sm max-h-64 overflow-y-auto bg-sky-50 border border-sky-100 rounded p-3">—</div>
                    </div>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">Decision per Choice</h3>
                    <div id="tripPlanningChoiceDetails" class="text-sm overflow-x-auto">—</div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-violet-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">📚 Learning Monitor — AI เรียนรู้พฤติกรรม/ความชอบ User อย่างไร</h2>
                <button onclick="loadLearningMonitor()" class="text-sm text-violet-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6 space-y-4">
                <p class="text-sm text-gray-600">แสดงให้เห็นว่า User ใหม่ ถูกเรียนรู้อย่างไร: อนุมานจากข้อความแรก (Inferred), Choice History, คะแนนดาว, RL</p>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">ต่อ User: ข้อมูลที่ AI รู้จัก</h3>
                    <div id="learningMonitorUsers" class="overflow-x-auto text-sm">กำลังโหลด...</div>
                </div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">ลำดับเหตุการณ์การเรียนรู้ (ล่าสุด)</h3>
                    <div id="learningMonitorEvents" class="overflow-x-auto text-sm max-h-64 overflow-y-auto">—</div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-amber-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">🧭 Search Relaxed Telemetry (No-Choice Fallback)</h2>
                <button onclick="loadSearchRelaxedSummary()" class="text-sm text-amber-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6 space-y-4">
                <p class="text-sm text-gray-600">สรุปสาเหตุ fallback ตอนค้นหาไม่เจอ เพื่อช่วย debug และปรับ tuning ของระบบค้นหา (Ask/Agent)</p>
                <div id="searchRelaxedSummary" class="text-sm">กำลังโหลด...</div>
                <div>
                    <h3 class="font-semibold text-gray-800 mb-2">เหตุผลที่เกิด relaxed search</h3>
                    <div id="searchRelaxedByReason" class="overflow-x-auto text-sm">—</div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6 border-l-4 border-cyan-500">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">🧠 AI รู้จัก User (%)</h2>
            </div>
            <div class="p-6 space-y-3">
                <p class="text-sm text-gray-600">วัดจาก <strong>User ที่ login อยู่</strong> ว่ามีบริบทพอให้ระบบพูดถึง user นี้มากน้อยแค่ไหน — อ่านคู่กับกล่อง &quot;วิธีคิด %&quot; ด้านล่าง</p>
                <details class="text-sm text-gray-700 bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <summary class="cursor-pointer font-semibold text-cyan-900">วิธีคิด % และข้อมูลที่ใช้ (อ่านก่อนตีความตัวเลข)</summary>
                    <div class="mt-3 space-y-2 text-xs leading-relaxed border-t border-gray-200 pt-3">
                        <p><strong>1) ข้อมูลดิบที่ดึงมา:</strong> ความจำจาก MongoDB <code class="bg-gray-100 px-1 rounded">memories</code> (ผ่าน MemoryService สูงสุด 15 รายการ), โปรไฟล์จาก <code class="bg-gray-100 px-1 rounded">users</code>, และ <code class="bg-gray-100 px-1 rounded">travel_preferences</code> ล่าสุดจาก <code class="bg-gray-100 px-1 rounded">sessions</code></p>
                        <p><strong>2) สวิตช์ มี/ไม่มี (บรรทัด &quot;ความจำ / โปรไฟล์ / ความชอบ&quot; ใต้คะแนน):</strong> ความจำ = ข้อความสรุปยาวพอ (มากกว่า 20 ตัวอักษร), โปรไฟล์ = มากกว่า 10 ตัวอักษร, ความชอบ = มี travel_preferences เมื่อแปลงเป็น string ยาวมากกว่า 10 ตัวอักษร</p>
                        <p><strong>3) คะแนนฐาน (กฎคงที่ ไม่ใช้ LLM):</strong> มีความจำ +35%, มีโปรไฟล์ +35%, มีความชอบ +30% — รวมสูงสุด 100% (ใช้เป็นค่า fallback และใช้ในตาราง Recent Sessions ทั้งคอลัมน์)</p>
                        <p><strong>4) คะแนนจาก LLM (การ์ดนี้เมื่อโหลดสำเร็จ):</strong> ส่งข้อความย่อจากข้อมูลข้างต้นให้โมเดลให้คะแนน 0–100 และเหตุผล — เป็นดัชนีเชิงภาษา ไม่ใช่สมการพิสูจน์ได้; ระบบสั่งให้อ้างอิงเฉพาะข้อความในบล็อกที่ส่ง ไม่ให้แต่งข้อเท็จจริงนอกบล็อก</p>
                        <p class="text-gray-500"><strong>หมายเหตุ:</strong> ตัวเลข % ไม่ได้วัดว่า &quot;รู้จักตัวจริงในชีวิต&quot; แต่วัดว่าในระบบมีหลักฐานดิจิทัลพอให้ AI สรุป/แนะนำต่อได้หรือไม่</p>
                    </div>
                </details>
                <div class="flex flex-wrap items-center gap-2">
                    <span id="familiarityLoggedInUser" class="text-sm text-gray-500">กำลังโหลด...</span>
                </div>
                <div id="familiarityResult" class="hidden mt-3 p-4 bg-cyan-50 border border-cyan-200 rounded-lg text-sm">
                    <div class="font-semibold text-cyan-900 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                        <span><span id="familiarityScore">0</span>%</span>
                        <span id="familiarityScoreBadge" class="text-xs font-normal px-2 py-0.5 rounded bg-cyan-200 text-cyan-950"></span>
                        <span>— ดัชนี &quot;รู้จัก user นี้ในระบบ&quot;</span>
                    </div>
                    <div id="familiarityReason" class="text-gray-700 mt-1">—</div>
                    <div id="familiarityFactors" class="text-gray-500 mt-1">—</div>
                    <div id="familiarityMethodology" class="hidden mt-3 text-xs text-gray-800 space-y-2 border border-cyan-100 rounded-lg p-3 bg-white"></div>
                    <div id="familiarityBreakdown" class="hidden mt-4 pt-3 border-t border-cyan-200">
                        <div class="font-semibold text-cyan-900 mb-2">📋 AI รู้จัก User นี้อย่างไรบ้าง</div>
                        <div class="space-y-2 text-xs">
                            <div class="break-words"><span class="font-medium text-gray-600">ความจำ:</span> <span id="breakdownMemory" class="text-gray-700">—</span></div>
                            <div class="break-words"><span class="font-medium text-gray-600">โปรไฟล์:</span> <span id="breakdownProfile" class="text-gray-700">—</span></div>
                            <div class="break-words"><span class="font-medium text-gray-600">ความชอบ (การเดินทาง):</span> <span id="breakdownPrefs" class="text-gray-700">—</span></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">Recent Sessions</h2>
                <button onclick="loadSessions()" class="text-sm text-blue-600 hover:underline">Refresh</button>
            </div>
            <div class="p-6 overflow-x-auto">
                <div id="sessions" class="text-sm">กำลังโหลด...</div>
            </div>
        </div>

        <!-- Amadeus Viewer Modal (ข้อมูลที่ดึงจาก Amadeus ต่อทริป) -->
        <div id="amadeusViewerModal" class="hidden fixed inset-0 z-50 overflow-y-auto bg-black bg-opacity-50" aria-modal="true">
            <div class="flex min-h-full items-center justify-center p-4">
                <div class="relative w-full max-w-4xl max-h-[90vh] bg-white rounded-lg shadow-xl flex flex-col">
                    <div class="px-6 py-4 border-b flex justify-between items-center">
                        <h3 class="text-lg font-bold text-gray-900">📊 Amadeus Viewer — ข้อมูลดึงจาก Amadeus (ทริปนี้เท่านั้น)</h3>
                        <button type="button" onclick="closeAmadeusViewer()" class="text-gray-500 hover:text-gray-700 text-2xl">&times;</button>
                    </div>
                    <div id="amadeusViewerContent" class="p-6 overflow-auto flex-1 text-sm"></div>
                </div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow mb-6">
            <div class="px-6 py-4 border-b flex justify-between items-center">
                <h2 class="text-lg font-bold text-gray-900">System Logs</h2>
                <div class="flex gap-2">
                    <input type="number" id="logLines" value="100" min="50" max="500" class="border rounded px-2 py-1 w-20 text-sm">
                    <button onclick="loadLogs()" class="px-3 py-1 bg-blue-600 text-white rounded text-sm">Load Logs</button>
                </div>
            </div>
            <div class="p-6 max-h-96 overflow-auto bg-gray-900 text-green-400 font-mono text-xs" id="logs">Click Load Logs</div>
        </div>
    </div>
    <script>
        const API = window.location.origin;
        const opts = { credentials: 'include' };
        let currentLoggedInUserId = null;
        let currentLoggedInName = null;

        async function loadCurrentUser() {
            const el = document.getElementById('familiarityLoggedInUser');
            if (!el) return;
            try {
                const r = await fetch(API + '/api/auth/me', opts);
                const d = await r.json();
                if (d.user && d.user.user_id) {
                    currentLoggedInUserId = d.user.user_id;
                    currentLoggedInName = (d.user.full_name || d.user.first_name || d.user.email || d.user.user_id) || '';
                    el.textContent = 'User ที่ login อยู่: ' + (currentLoggedInName || currentLoggedInUserId);
                    loadUserFamiliarity();
                } else {
                    currentLoggedInUserId = null;
                    currentLoggedInName = null;
                    el.textContent = 'ยังไม่ login — กรุณา login ในแอป (หน้าหลัก) ก่อน';
                }
            } catch (e) {
                el.textContent = 'โหลดไม่สำเร็จ: ' + e.message;
            }
        }

        function showErr(msg) {
            const el = document.getElementById('error');
            el.textContent = msg;
            el.classList.remove('hidden');
        }
        function clearErr() {
            document.getElementById('error').classList.add('hidden');
        }

        async function loadStatus() {
            try {
                const r = await fetch(API + '/api/admin/status', opts);
                if (!r.ok) { showErr('Status: ' + r.status); return; }
                const d = await r.json();
                clearErr();
                document.getElementById('services').innerHTML = Object.entries(d.services || {}).map(([k, v]) =>
                    '<div class="flex justify-between py-2 border-b"><span class="font-medium">' + k.replace('_',' ') + '</span>' +
                    '<span class="px-2 py-0.5 rounded text-xs ' + (v.status === 'ok' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800') + '">' + (v.status === 'ok' ? 'ONLINE' : 'OFFLINE') + '</span></div>' +
                    '<div class="text-gray-500 text-xs mb-1">' + (v.message || '') + '</div>'
                ).join('');
                const cfg = d.config || {};
                const sys = d.system || {};
                document.getElementById('config').innerHTML =
                    '<div class="py-1">Gemini: ' + (cfg.gemini_model || 'N/A') + '</div>' +
                    '<div class="py-1">Amadeus: ' + (cfg.amadeus_search_env || 'N/A') + ' / ' + (cfg.amadeus_booking_env || 'N/A') + '</div>' +
                    '<div class="py-1">Uptime: ' + (sys.uptime_seconds || 0) + 's | Memory: ' + (sys.memory_usage_mb || 0) + ' MB</div>';
            } catch (e) {
                showErr('Status: ' + e.message);
            }
        }

        async function loadSessions() {
            document.getElementById('sessions').textContent = 'Loading...';
            try {
                const r = await fetch(API + '/api/admin/sessions?limit=20', opts);
                if (!r.ok) { document.getElementById('sessions').textContent = 'Error ' + r.status; return; }
                const list = await r.json();
                if (!Array.isArray(list) || list.length === 0) {
                    document.getElementById('sessions').innerHTML = '<p class="text-gray-500">No sessions</p>';
                    return;
                }
                const userIds = [...new Set(list.map(s => s.user_id).filter(Boolean))];
                let familiarityMap = {};
                if (userIds.length > 0) {
                    try {
                        const fr = await fetch(API + '/api/admin/user-familiarity/batch?user_ids=' + userIds.map(encodeURIComponent).join(','), opts);
                        if (fr.ok) {
                            const batch = await fr.json();
                            (batch.items || []).forEach(it => { familiarityMap[it.user_id] = it; });
                        }
                    } catch (e) { console.warn('Familiarity batch failed', e); }
                }
                document.getElementById('sessions').innerHTML = '<table class="min-w-full" id="sessionsTable"><thead><tr class="border-b"><th class="text-left py-2">Session / Trip</th><th class="text-left py-2">User</th><th class="text-left py-2" title="คะแนนจากกฎคงที่เท่านั้น (ความจำ+35 โปรไฟล์+35 ความชอบ+30) ไม่เรียก LLM — ชี้เมาส์ที่หัวคอลัมน์นี้เพื่ออ่านคำอธิบาย">รู้จัก % <span class="text-gray-400 font-normal">(ฐาน)</span></th><th class="text-left py-2">Updated</th><th class="text-left py-2">Amadeus</th></tr></thead><tbody>' +
                    list.map(s => {
                        const uid = s.user_id || '';
                        const sid = s.session_id || s.trip_id || s._id || '';
                        const sidEsc = ('' + sid).replace(/"/g, '&quot;').replace(/</g, '&lt;');
                        const fam = familiarityMap[uid];
                        const pctTitle = fam && fam.score_note_th ? fam.score_note_th.replace(/"/g, '&quot;') : 'คะแนนฐานจากกฎคงที่ (ไม่ใช่ LLM)';
                        const pct = fam ? ('<span title="' + pctTitle + '">' + fam.score_percent + '%</span>') : '—';
                        const measureBtn = uid ? '<button type="button" onclick="loadUserFamiliarity(' + JSON.stringify(uid) + ')" class="text-cyan-600 hover:underline text-xs">วัดด้วย AI</button>' : '';
                        const amadeusBtn = sid ? '<button type="button" class="amadeus-viewer-btn px-2 py-1 text-xs bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 cursor-pointer" data-session-id="' + sidEsc + '">ดูข้อมูล Amadeus</button>' : '—';
                        return '<tr class="border-b"><td class="py-2">' + (s.title || sid) + '</td><td class="py-2 font-mono">' + uid + '</td><td class="py-2">' + pct + ' ' + measureBtn + '</td><td class="py-2 text-gray-500">' + (s.last_updated ? (s.last_updated + '').slice(0, 19).replace('T', ' ') : '') + '</td><td class="py-2">' + amadeusBtn + '</td></tr>';
                    }).join('') + '</tbody></table>';
                document.querySelectorAll('.amadeus-viewer-btn').forEach(btn => {
                    btn.addEventListener('click', function() { openAmadeusViewer(this.getAttribute('data-session-id') || ''); });
                });
            } catch (e) {
                document.getElementById('sessions').textContent = 'Error: ' + e.message;
            }
        }

        function closeAmadeusViewer() {
            document.getElementById('amadeusViewerModal').classList.add('hidden');
        }
        async function openAmadeusViewer(sessionId) {
            const modal = document.getElementById('amadeusViewerModal');
            const content = document.getElementById('amadeusViewerContent');
            modal.classList.remove('hidden');
            content.innerHTML = '<p class="text-gray-500">กำลังโหลด...</p>';
            try {
                const r = await fetch(API + '/api/admin/sessions/' + encodeURIComponent(sessionId) + '/amadeus-viewer', opts);
                if (!r.ok) { content.innerHTML = '<p class="text-red-600">โหลดไม่สำเร็จ: ' + r.status + '</p>'; return; }
                const d = await r.json();
                const sum = d.summary || {};
                const total = (sum.flights_outbound || 0) + (sum.flights_inbound || 0) + (sum.ground_transport || 0) + (sum.accommodation || 0);
                const scopeText = d.source_scope === 'trip' ? 'Trip aggregate fallback' : 'Session only';
                let html = '<div class="mb-3 p-3 bg-gray-50 rounded text-sm"><strong>Session:</strong> <code class="text-xs">' + (d.session_id || '') + '</code><span class="ml-2 inline-block px-2 py-0.5 rounded bg-indigo-100 text-indigo-700 text-xs">' + scopeText + '</span></div>';
                html += '<div class="mb-4 p-4 bg-white border border-gray-200 rounded-lg shadow-sm">';
                html += '<div class="flex items-center gap-2 mb-3"><span class="text-lg">📄</span><span class="font-bold text-gray-800">ตัวเลือก (' + total + ' รายการ)</span></div>';
                html += '<p class="text-sm text-gray-600 mb-3">ทริปนี้ดึงข้อมูลจาก Amadeus แบ่งเป็นหมวดดังนี้:</p>';
                html += '<ul class="list-disc list-inside space-y-1.5 text-sm text-gray-700">';
                html += '<li>✈️ <strong>เที่ยวบินขาออก:</strong> ' + (sum.flights_outbound || 0) + ' รายการ</li>';
                html += '<li>✈️ <strong>เที่ยวบินขากลับ:</strong> ' + (sum.flights_inbound || 0) + ' รายการ</li>';
                html += '<li>🏨 <strong>ที่พัก:</strong> ' + (sum.accommodation || 0) + ' รายการ</li>';
                html += '<li>🚗 <strong>รถรับส่ง:</strong> ' + (sum.ground_transport || 0) + ' รายการ</li>';
                html += '</ul>';
                html += '<p class="mt-3 text-sm text-gray-500">รวมทั้งหมด <strong>' + total + '</strong> รายการ</p>';
                html += '</div>';
                html += '<div class="mb-4 grid grid-cols-2 md:grid-cols-4 gap-2"><div class="p-2 bg-blue-50 rounded text-center"><span class="block font-semibold text-blue-800">' + (sum.flights_outbound || 0) + '</span><span class="text-xs text-blue-600">เที่ยวบินขาออก</span></div><div class="p-2 bg-blue-50 rounded text-center"><span class="block font-semibold text-blue-800">' + (sum.flights_inbound || 0) + '</span><span class="text-xs text-blue-600">เที่ยวบินขากลับ</span></div><div class="p-2 bg-amber-50 rounded text-center"><span class="block font-semibold text-amber-800">' + (sum.ground_transport || 0) + '</span><span class="text-xs text-amber-600">รถรับส่ง</span></div><div class="p-2 bg-green-50 rounded text-center"><span class="block font-semibold text-green-800">' + (sum.accommodation || 0) + '</span><span class="text-xs text-green-600">ที่พัก</span></div></div>';
                html += '<details class="mb-2"><summary class="font-semibold cursor-pointer text-gray-700">Options (ตัวเลือกที่แคชไว้ — คลิกขยาย)</summary><pre id="amadeusOptionsJson" class="mt-2 p-3 bg-gray-100 rounded overflow-x-auto text-xs max-h-64 overflow-y-auto"></pre></details>';
                html += '<details class="mt-4"><summary class="font-semibold cursor-pointer text-gray-700">Raw Amadeus (response ดิบจาก Amadeus ต่อ slot — คลิกขยาย)</summary><pre id="amadeusRawJson" class="mt-2 p-3 bg-gray-100 rounded overflow-x-auto text-xs max-h-96 overflow-y-auto"></pre></details>';
                content.innerHTML = html;
                document.getElementById('amadeusOptionsJson').textContent = JSON.stringify(d.options || {}, null, 2);
                document.getElementById('amadeusRawJson').textContent = Object.keys(d.raw_amadeus || {}).length ? JSON.stringify(d.raw_amadeus, null, 2) : '(ไม่มี raw data — ข้อมูลอาจหมดอายุหรือทริปนี้ยังไม่ได้ดึงจาก Amadeus)';
            } catch (e) {
                content.innerHTML = '<p class="text-red-600">Error: ' + e.message + '</p>';
            }
        }

        function escFamiliarityHtml(s) {
            return String(s == null ? '' : s)
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
        }

        async function loadUserFamiliarity(optionalUserId) {
            const uid = (optionalUserId && optionalUserId.trim()) ? optionalUserId.trim() : (currentLoggedInUserId || '').trim();
            if (!uid) {
                document.getElementById('familiarityResult').classList.add('hidden');
                if (!currentLoggedInUserId) alert('กรุณา login ในแอป (หน้าหลัก) ก่อน จึงจะวัดได้');
                return;
            }
            const resultEl = document.getElementById('familiarityResult');
            const scoreEl = document.getElementById('familiarityScore');
            const badgeEl = document.getElementById('familiarityScoreBadge');
            const reasonEl = document.getElementById('familiarityReason');
            const factorsEl = document.getElementById('familiarityFactors');
            const methEl = document.getElementById('familiarityMethodology');
            resultEl.classList.remove('hidden');
            scoreEl.textContent = '...';
            if (badgeEl) badgeEl.textContent = '';
            reasonEl.textContent = 'กำลังวัดด้วย AI...';
            factorsEl.textContent = '';
            if (methEl) { methEl.classList.add('hidden'); methEl.innerHTML = ''; }
            try {
                const r = await fetch(API + '/api/admin/user-familiarity?user_id=' + encodeURIComponent(uid), opts);
                if (!r.ok) { reasonEl.textContent = 'Error: ' + r.status; return; }
                const d = await r.json();
                scoreEl.textContent = d.score_percent != null ? d.score_percent : '—';
                if (badgeEl) {
                    if (d.source === 'ai') {
                        badgeEl.textContent = 'คะแนนจาก LLM';
                        badgeEl.className = 'text-xs font-normal px-2 py-0.5 rounded bg-violet-200 text-violet-950';
                    } else {
                        badgeEl.textContent = 'คะแนนฐาน (กฎคงที่)';
                        badgeEl.className = 'text-xs font-normal px-2 py-0.5 rounded bg-cyan-200 text-cyan-950';
                    }
                }
                reasonEl.textContent = d.reason || '—';
                const f = d.factors || {};
                factorsEl.textContent = 'ความจำ: ' + (f.has_memory ? 'มี' : 'ไม่มี') + ' | โปรไฟล์: ' + (f.has_profile ? 'มี' : 'ไม่มี') + ' | ความชอบ: ' + (f.has_preferences ? 'มี' : 'ไม่มี');
                const m = d.methodology || {};
                if (methEl && m.score_source_th) {
                    let mh = '<p><strong>แหล่งที่มาของตัวเลข %:</strong> ' + escFamiliarityHtml(m.score_source_th) + '</p>';
                    mh += '<p><strong>ความหมายของ % นี้:</strong> ' + escFamiliarityHtml(m.this_score_th) + '</p>';
                    if (d.source === 'ai' && d.heuristic_baseline_percent != null && m.baseline_compare_th) {
                        mh += '<p><strong>เทียบกับคะแนนฐาน:</strong> ' + escFamiliarityHtml(m.baseline_compare_th) + '</p>';
                    }
                    mh += '<p><strong>ข้อมูลที่ส่งเข้าประเมิน:</strong> ' + escFamiliarityHtml(m.data_pipeline_th) + '</p>';
                    mh += '<p><strong>เงื่อนไขสวิตช์ มี/ไม่มี:</strong> ' + escFamiliarityHtml(m.factor_gates_th) + '</p>';
                    mh += '<p><strong>สูตรคะแนนฐาน (fallback / ตาราง Sessions):</strong> ' + escFamiliarityHtml(m.base_rule_th) + '</p>';
                    mh += '<p class="text-gray-500">' + escFamiliarityHtml(m.batch_sessions_note_th) + '</p>';
                    methEl.innerHTML = mh;
                    methEl.classList.remove('hidden');
                }
                const breakdown = d.breakdown || {};
                const breakdownEl = document.getElementById('familiarityBreakdown');
                const memEl = document.getElementById('breakdownMemory');
                const profileEl = document.getElementById('breakdownProfile');
                const prefsEl = document.getElementById('breakdownPrefs');
                if (breakdownEl && memEl && profileEl && prefsEl) {
                    memEl.textContent = breakdown.memory_summary || '(ไม่มีข้อมูลความจำ)';
                    profileEl.textContent = breakdown.profile_summary || '(ไม่มีข้อมูลโปรไฟล์)';
                    prefsEl.textContent = breakdown.preferences_summary || '(ยังไม่มีความชอบการเดินทาง)';
                    breakdownEl.classList.remove('hidden');
                }
            } catch (e) {
                reasonEl.textContent = 'Error: ' + e.message;
            }
        }

        async function loadLogs() {
            const n = document.getElementById('logLines').value || 100;
            document.getElementById('logs').textContent = 'Loading...';
            try {
                const r = await fetch(API + '/api/admin/logs?lines=' + n, opts);
                if (!r.ok) { document.getElementById('logs').textContent = 'Error ' + r.status; return; }
                const d = await r.json();
                const lines = Array.isArray(d.content) ? d.content : (d.content ? [d.content] : [d.message || 'No logs']);
                document.getElementById('logs').innerHTML = lines.map(l => '<div class="whitespace-pre-wrap">' + (typeof l === 'string' ? l : JSON.stringify(l)) + '</div>').join('');
            } catch (e) {
                document.getElementById('logs').textContent = 'Error: ' + e.message;
            }
        }

        async function loadAILearningMetrics() {
            const el = document.getElementById('aiLearningMetrics');
            el.textContent = 'กำลังโหลด...';
            try {
                const r = await fetch(API + '/api/admin/ai-learning-metrics', opts);
                if (!r.ok) { el.innerHTML = '<p class="text-red-600">โหลดไม่สำเร็จ: ' + r.status + '</p>'; return; }
                const d = await r.json();
                if (d.error) { el.innerHTML = '<p class="text-amber-600">' + d.error + '</p>'; return; }
                const scores = d.scores || {};
                const rl = d.rl || {};
                const ch = d.choice_history || {};
                const mem = d.memory || {};
                const escNote = (s) => String(s == null ? '' : s)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');
                const noteBox = (label, text) => text
                    ? '<p class="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-md p-2 mt-2 leading-relaxed"><span class="font-semibold">' + label + '</span> ' + escNote(text) + '</p>'
                    : '';
                const scoreVal = (rl.score_normalized_0_1 ?? scores.rl_score_normalized ?? 0);
                const confVal = (rl.confidence_pct ?? scores.rl_confidence_pct ?? 0);
                const scorePct = Math.round(scoreVal * 100);
                const summaryHtml =
                    '<div class="mb-4 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">' +
                    '<h3 class="font-semibold text-indigo-900 mb-3">📈 คะแนนและความมั่นใจ (จาก ML/RL)</h3>' +
                    '<div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">' +
                    '<div><span class="text-gray-600">คะแนน RL (0–1)</span><br><span class="text-xl font-bold text-indigo-700">' + scoreVal + '</span></div>' +
                    '<div><span class="text-gray-600">คะแนน RL (%)</span><br><span class="text-xl font-bold text-indigo-700">' + scorePct + '%</span></div>' +
                    '<div><span class="text-gray-600">ความมั่นใจ (สัดส่วนบวก)</span><br><span class="text-xl font-bold text-indigo-700">' + confVal + '%</span></div>' +
                    '<div><span class="text-gray-600">ค่าเฉลี่ย reward (100 ล่าสุด)</span><br><span class="text-xl font-bold ' + ((rl.recent_avg_reward ?? 0) >= 0 ? 'text-indigo-700' : 'text-red-600') + '">' + (rl.recent_avg_reward != null ? (rl.recent_avg_reward >= 0 ? '+' : '') + Number(rl.recent_avg_reward).toFixed(3) : '0') + '</span></div>' +
                    '</div>' +
                    (scores.description ? '<p class="text-xs text-gray-500 mt-2">' + escNote(scores.description) + '</p>' : '') +
                    noteBox('📌 แหล่งข้อมูล:', scores.source_note) +
                    '</div>';
                el.innerHTML =
                    summaryHtml +
                    '<div class="grid grid-cols-1 md:grid-cols-3 gap-4">' +
                    '<div class="border border-gray-200 rounded-lg p-4 bg-gray-50">' +
                    '<h3 class="font-semibold text-gray-800 mb-2">🧠 Reinforcement Learning (RL)</h3>' +
                    '<p class="text-gray-600 text-xs mb-2">' + escNote(rl.description || '') + '</p>' +
                    '<ul class="space-y-1 text-gray-700">' +
                    '<li>ประวัติ reward: <strong>' + (rl.total_reward_records ?? 0) + '</strong> รายการ</li>' +
                    '<li>Q-table: <strong>' + (rl.total_q_entries ?? 0) + '</strong> รายการ</li>' +
                    '<li>User ที่มีข้อมูล RL: <strong>' + (rl.users_with_rewards ?? 0) + '</strong></li>' +
                    '<li>คะแนน RL (normalized 0–1): <strong>' + scoreVal + '</strong></li>' +
                    '<li>ความมั่นใจ (reward บวก): <strong>' + confVal + '%</strong></li>' +
                    '</ul>' +
                    noteBox('📌 แหล่งข้อมูล:', rl.source_note) +
                    '</div>' +
                    '<div class="border border-gray-200 rounded-lg p-4 bg-gray-50">' +
                    '<h3 class="font-semibold text-gray-800 mb-2">🎯 Choice History (Selection Preferences)</h3>' +
                    '<p class="text-gray-600 text-xs mb-2">' + escNote(ch.description || '') + '</p>' +
                    '<ul class="space-y-1 text-gray-700">' +
                    '<li>จำนวนการเลือกบันทึก: <strong>' + (ch.total_records ?? 0) + '</strong></li>' +
                    '<li>User ที่มีประวัติเลือก: <strong>' + (ch.users_with_choices ?? 0) + '</strong></li>' +
                    '</ul>' +
                    noteBox('📌 แหล่งข้อมูล:', ch.source_note) +
                    '</div>' +
                    '<div class="border border-gray-200 rounded-lg p-4 bg-gray-50">' +
                    '<h3 class="font-semibold text-gray-800 mb-2">💡 Memory (ความจำระยะยาว)</h3>' +
                    '<p class="text-gray-600 text-xs mb-2">' + escNote(mem.description || '') + '</p>' +
                    '<ul class="space-y-1 text-gray-700">' +
                    '<li>ความจำทั้งหมด: <strong>' + (mem.total_memories ?? 0) + '</strong></li>' +
                    '<li>User ที่มีความจำ: <strong>' + (mem.users_with_memories ?? 0) + '</strong></li>' +
                    '</ul>' +
                    noteBox('📌 แหล่งข้อมูล:', mem.source_note) +
                    '</div>' +
                    '</div>' +
                    '<p class="text-xs text-gray-500 mt-4 border-t border-gray-200 pt-3">หมายเหตุรวม: ตัวเลขทั้งหมดในบล็อกนี้เป็นสถิติจากฐานข้อมูล MongoDB ของแอปนี้เท่านั้น อัปเดตตามข้อมูลที่ backend บันทึกจริง ไม่ได้สะท้อนโมเดลภายนอกโดยตรง</p>';
            } catch (e) {
                el.innerHTML = '<p class="text-red-600">Error: ' + e.message + '</p>';
            }
        }

        async function loadAIScores() {
            const overallEl = document.getElementById('aiScoresOverall');
            const perUserEl = document.getElementById('aiScoresPerUser');
            const tripsEl = document.getElementById('aiScoresTrips');
            if (!overallEl || !perUserEl || !tripsEl) return;
            overallEl.textContent = 'กำลังโหลด...';
            perUserEl.innerHTML = '—';
            tripsEl.innerHTML = '—';
            try {
                const r = await fetch(API + '/api/admin/ai-scores?limit=300', opts);
                if (!r.ok) { overallEl.innerHTML = '<p class="text-red-600">โหลดไม่สำเร็จ: ' + r.status + '</p>'; return; }
                const d = await r.json();
                if (d.error) { overallEl.innerHTML = '<p class="text-amber-600">' + d.error + '</p>'; return; }
                const overall = d.overall || {};
                const perUser = d.per_user || [];
                const trips = d.trips || [];
                const esc = (v) => String(v == null ? '' : v)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');

                overallEl.innerHTML =
                    '<div class="p-4 bg-emerald-50 border border-emerald-200 rounded-lg">' +
                    '<div class="grid grid-cols-2 md:grid-cols-4 gap-4">' +
                    '<div><span class="text-gray-600 block">จำนวนทริปที่ประเมิน</span><span class="text-xl font-bold text-emerald-700">' + (overall.total_trips || 0) + '</span></div>' +
                    '<div><span class="text-gray-600 block">คะแนนความแม่นยำ AI เฉลี่ย</span>' +
                    (overall.avg_accuracy != null
                        ? '<span class="text-xl font-bold text-emerald-700">' + overall.avg_accuracy + ' / 100</span><span class="text-xs text-gray-500 block">คะแนนเต็ม 100</span>'
                        : '<span class="text-xl font-bold text-emerald-700">—</span>') +
                    '</div>' +
                    '<div title="สอดคล้องกับฟอร์มให้คะแนน: satisfaction_pct จากดาวรวม+หัวข้อย่อย หรือแปลงจากดาวรวม">' +
                    '<span class="text-gray-600 block">ความพึงพอใจผู้ใช้เฉลี่ย</span>' +
                    (overall.avg_user_satisfaction_pct != null
                        ? '<span class="text-xl font-bold text-emerald-700">' + overall.avg_user_satisfaction_pct + ' / 100</span><span class="text-xs text-gray-500 block">คะแนนเต็ม 100 (เฉลี่ยจากทริปที่มีคะแนน)</span>'
                        : '<span class="text-xl font-bold text-emerald-700">—</span>') +
                    (overall.avg_user_stars != null
                        ? '<span class="text-sm font-semibold text-emerald-800 block mt-1">' + overall.avg_user_stars + ' / 5</span><span class="text-xs text-gray-500 block">ดาวรวมเฉลี่ย · คะแนนเต็ม 5</span>'
                        : '') +
                    '</div>' +
                    '<div title="' + esc(overall.combined_score_formula || '') + '"><span class="text-gray-600 block">ความสามารถรวม (ภาพรวม)</span>' +
                    (overall.combined_score_pct != null
                        ? '<span class="text-xl font-bold text-emerald-700">' + overall.combined_score_pct + ' / 100</span><span class="text-xs text-gray-500 block">คะแนนเต็ม 100</span>'
                        : '<span class="text-xl font-bold text-emerald-700">—</span>') +
                    '</div>' +
                    '</div>' +
                    (overall.sum_user_stars != null && overall.max_user_stars_possible != null
                        ? '<p class="text-sm text-gray-800 mt-4 pt-3 border-t border-emerald-200">' +
                          '<span class="text-gray-600">คะแนนดาวรวมจาก User (สะสมทุกทริปที่ให้คะแนน): </span>' +
                          '<strong class="text-emerald-800">' + overall.sum_user_stars + '</strong> / <strong class="text-emerald-800">' + overall.max_user_stars_possible + '</strong>' +
                          '<span class="text-gray-500 text-xs"> · คะแนนเต็ม = 5 ดาว × ' + (overall.trips_with_user_stars || 0) + ' ทริป</span></p>'
                        : '') +
                    '</div>';

                perUserEl.innerHTML = perUser.length === 0
                    ? '<p class="text-gray-500">ยังไม่มีข้อมูลต่อผู้ใช้</p>'
                    : (
                        '<table class="min-w-full border text-xs"><thead><tr class="border-b bg-emerald-50">' +
                        '<th class="text-left py-2 px-2">User</th>' +
                        '<th class="text-left py-2 px-2">Trips</th>' +
                        '<th class="text-left py-2 px-2">AI Avg</th>' +
                        '<th class="text-left py-2 px-2">พึงพอใจ</th>' +
                        '<th class="text-left py-2 px-2">ดาวรวม (ได้/เต็ม)</th>' +
                        '<th class="text-left py-2 px-2">Combined</th>' +
                        '<th class="text-left py-2 px-2">RL Rewards</th>' +
                        '<th class="text-left py-2 px-2">Q-Entries</th>' +
                        '</tr></thead><tbody>' +
                        perUser.map(u =>
                            '<tr class="border-b hover:bg-gray-50">' +
                            '<td class="py-2 px-2 font-mono" title="' + esc(u.user_id) + '">' + esc(u.user_id || '') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.trip_count || 0) + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.avg_accuracy != null ? (u.avg_accuracy + ' / 100') : '—') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.avg_user_satisfaction_pct != null ? (u.avg_user_satisfaction_pct + ' / 100') : '—') + (u.avg_user_stars != null ? '<br><span class="text-gray-500 text-xs">เฉลี่ย ' + u.avg_user_stars + '/5 ★</span>' : '') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.sum_user_stars != null && u.max_user_stars_possible != null ? (u.sum_user_stars + ' / ' + u.max_user_stars_possible) : '—') + '</td>' +
                            '<td class="py-2 px-2 text-center font-semibold text-emerald-700">' + (u.combined_score_pct != null ? (u.combined_score_pct + ' / 100') : '—') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.rl_reward_records || 0) + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.rl_q_entries || 0) + '</td>' +
                            '</tr>'
                        ).join('') +
                        '</tbody></table>'
                    );

                const tripLimit = 60;
                const tripRows = trips.slice(0, tripLimit).map(t =>
                    '<tr class="border-b hover:bg-gray-50">' +
                    '<td class="py-2 px-2 font-mono text-xs" title="' + esc(t.session_id || '') + '">' + esc(t.session_id || '') + '</td>' +
                    '<td class="py-2 px-2 font-mono text-xs" title="' + esc(t.user_id || '') + '">' + esc(t.user_id || '') + '</td>' +
                    '<td class="py-2 px-2">' + esc(t.mode || t.source || '—') + '</td>' +
                    '<td class="py-2 px-2 text-center">' + (t.agent_accuracy_score != null ? (t.agent_accuracy_score + ' / 100') : '—') + '</td>' +
                    '<td class="py-2 px-2 text-center">' + (t.user_satisfaction_pct != null ? (t.user_satisfaction_pct + ' / 100') : '—') + (t.user_stars != null ? '<br><span class="text-gray-500 text-xs">' + t.user_stars + ' / 5 ★</span>' : '') + '</td>' +
                    '<td class="py-2 px-2 text-xs text-gray-600">' + esc(t.updated_at || '') + '</td>' +
                    '</tr>'
                ).join('');
                tripsEl.innerHTML = trips.length === 0
                    ? '<p class="text-gray-500">ยังไม่มีข้อมูลทริป</p>'
                    : (
                        '<table class="min-w-full border text-xs"><thead><tr class="border-b bg-gray-100">' +
                        '<th class="text-left py-2 px-2">Session/Trip</th>' +
                        '<th class="text-left py-2 px-2">User</th>' +
                        '<th class="text-left py-2 px-2">Mode</th>' +
                        '<th class="text-left py-2 px-2">AI Score</th>' +
                        '<th class="text-left py-2 px-2">พึงพอใจ (ได้/เต็ม)</th>' +
                        '<th class="text-left py-2 px-2">Updated</th>' +
                        '</tr></thead><tbody>' + tripRows + '</tbody></table>' +
                        (trips.length > tripLimit ? '<p class="text-xs text-gray-500 mt-2">แสดง ' + tripLimit + ' รายการล่าสุดจากทั้งหมด ' + trips.length + ' รายการ</p>' : '')
                    );
            } catch (e) {
                overallEl.innerHTML = '<p class="text-red-600">Error: ' + e.message + '</p>';
            }
        }

        async function loadLearningMonitor() {
            const usersEl = document.getElementById('learningMonitorUsers');
            const eventsEl = document.getElementById('learningMonitorEvents');
            if (!usersEl || !eventsEl) return;
            usersEl.textContent = 'กำลังโหลด...';
            eventsEl.textContent = '—';
            try {
                const r = await fetch(API + '/api/admin/learning-monitor?limit=50', opts);
                if (!r.ok) { usersEl.innerHTML = '<p class="text-red-600">โหลดไม่สำเร็จ: ' + r.status + '</p>'; return; }
                const d = await r.json();
                if (d.error) { usersEl.innerHTML = '<p class="text-amber-600">' + d.error + '</p>'; return; }
                const users = d.users_learning || [];
                const events = d.learning_events || [];
                usersEl.innerHTML = users.length === 0 ? '<p class="text-gray-500">ยังไม่มีข้อมูลการเรียนรู้</p>' :
                    '<table class="min-w-full border text-xs"><thead><tr class="border-b bg-violet-50">' +
                    '<th class="text-left py-2 px-2">User ID</th><th class="text-left py-2 px-2">รู้จัก</th><th class="text-left py-2 px-2">ความชอบ (RL/Text)</th><th class="text-left py-2 px-2">ML Feature</th><th class="text-left py-2 px-2">Choices</th><th class="text-left py-2 px-2">Last ความพึงพอใจ</th><th class="text-left py-2 px-2">RL</th><th class="text-left py-2 px-2">Q</th><th class="text-left py-2 px-2">FWL</th><th class="text-left py-2 px-2">Last activity</th></tr></thead><tbody>' +
                    users.map(u => {
                        const knownBadge = u.inferred_from_chat
                            ? '<span class="bg-green-100 text-green-700 rounded px-1">✅ รู้จัก</span>'
                            : (u.rl_q_entries > 0 ? '<span class="bg-blue-100 text-blue-700 rounded px-1">🧠 RL</span>' : '—');
                        const prefCell = u.travel_prefs_summary !== '—'
                            ? '<span title="' + u.travel_prefs_summary + '">' + u.travel_prefs_summary.slice(0, 40) + (u.travel_prefs_summary.length > 40 ? '…' : '') + '</span>'
                            : '—';
                        const fwlCell = u.fwl_summary
                            ? '<span class="text-indigo-700" title="ML Feature Weights">' + u.fwl_summary.slice(0, 40) + (u.fwl_summary.length > 40 ? '…' : '') + '</span>'
                            : (u.fwl_updates > 0 ? '<span class="text-gray-400">' + u.fwl_updates + ' updates</span>' : '—');
                        const fwlSlots = u.fwl_slots > 0
                            ? '<span class="bg-indigo-100 text-indigo-700 rounded px-1">' + u.fwl_slots + ' slot</span>'
                            : '—';
                        const starsCell = (u.last_user_satisfaction_pct != null || u.last_user_stars != null)
                            ? '<span class="text-amber-600 font-semibold">' +
                              (u.last_user_satisfaction_pct != null ? u.last_user_satisfaction_pct + '%' : '') +
                              (u.last_user_satisfaction_pct != null && u.last_user_stars != null ? ' · ' : '') +
                              (u.last_user_stars != null ? (u.last_user_stars + ' ★') : '') +
                              '</span>'
                            : '—';
                        return '<tr class="border-b hover:bg-gray-50">' +
                            '<td class="py-2 px-2 font-mono text-gray-600">' + (u.user_id || '').slice(0, 16) + '</td>' +
                            '<td class="py-2 px-2">' + knownBadge + '</td>' +
                            '<td class="py-2 px-2 max-w-xs">' + prefCell + '</td>' +
                            '<td class="py-2 px-2 max-w-xs">' + fwlCell + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.choice_count || 0) + '</td>' +
                            '<td class="py-2 px-2 text-center">' + starsCell + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (u.rl_reward_count || 0) + '</td>' +
                            '<td class="py-2 px-2 text-center font-semibold ' + (u.rl_q_entries > 0 ? 'text-blue-700' : 'text-gray-400') + '">' + (u.rl_q_entries || 0) + '</td>' +
                            '<td class="py-2 px-2 text-center">' + fwlSlots + '</td>' +
                            '<td class="py-2 px-2 text-gray-500">' + (u.last_activity ? (u.last_activity + '').slice(0, 19) : '—') + '</td>' +
                            '</tr>';
                    }).join('') +
                    '</tbody></table>';
                // name map สำหรับแสดงชื่อย่อของ user ในตาราง events
                const userNameMap = {};
                users.forEach(u => {
                    if (!u || !u.user_id) return;
                    const display =
                        u.user_name ||
                        u.email ||
                        (u.user_id || '').slice(0, 12);
                    userNameMap[u.user_id] = display;
                });

                const evLabels = {
                    'user_star_rating':   '⭐ ให้คะแนนดาว',
                    'select_option':      '✅ เลือกตัวเลือก',
                    'book':               '🎫 จองสำเร็จ',
                    'complete_booking':   '🎫 จองสำเร็จ',
                    'reject':             '❌ ปฏิเสธตัวเลือก',
                    'reject_option':      '❌ ปฏิเสธตัวเลือก',
                    'cancel':             '🚫 ยกเลิกการจอง',
                    'cancel_booking':     '🚫 ยกเลิกการจอง',
                    'positive_feedback':  '👍 Feedback บวก',
                    'negative_feedback':  '👎 Feedback ลบ',
                    'edit':               '✏️ แก้ไขการเลือก',
                    'edit_selection':     '✏️ แก้ไขการเลือก',
                };
                eventsEl.innerHTML = events.length === 0 ? '<p class="text-gray-500">ยังไม่มีเหตุการณ์</p>' :
                    '<table class="min-w-full border text-xs"><thead><tr class="border-b bg-gray-100"><th class="text-left py-1 px-2">เวลา</th><th class="text-left py-1 px-2">User</th><th class="text-left py-1 px-2">เหตุการณ์</th><th class="text-left py-1 px-2">รายละเอียด</th><th class="text-left py-1 px-2">Reward</th></tr></thead><tbody>' +
                    events.map(ev => { const rewardVal = ev.reward != null ? ev.reward : null; const rewardCell = rewardVal != null ? '<span class="' + (rewardVal >= 0 ? 'text-green-600' : 'text-red-600') + ' font-semibold">' + (rewardVal >= 0 ? '+' : '') + Number(rewardVal).toFixed(2) + '</span>' : '—'; const evName = userNameMap[ev.user_id] || (ev.user_id || '').slice(0, 12); return '<tr class="border-b"><td class="py-1 px-2 text-gray-500">' + (ev.created_at ? (ev.created_at + '').slice(0, 19) : '') + '</td><td class="py-1 px-2" title="' + (ev.user_id || '') + '">' + evName + '</td><td class="py-1 px-2">' + (evLabels[ev.event_type] || ev.event_type) + '</td><td class="py-1 px-2">' + (ev.detail || '') + '</td><td class="py-1 px-2">' + rewardCell + '</td></tr>'; }).join('') +
                    '</tbody></table>';
            } catch (e) {
                usersEl.innerHTML = '<p class="text-red-600">Error: ' + e.message + '</p>';
            }
        }

        async function loadSearchRelaxedSummary() {
            const summaryEl = document.getElementById('searchRelaxedSummary');
            const byReasonEl = document.getElementById('searchRelaxedByReason');
            if (!summaryEl || !byReasonEl) return;
            summaryEl.textContent = 'กำลังโหลด...';
            byReasonEl.innerHTML = '—';
            try {
                const r = await fetch(API + '/api/monitoring/search-relaxed/summary', opts);
                if (!r.ok) {
                    summaryEl.innerHTML = '<p class="text-red-600">โหลดไม่สำเร็จ: ' + r.status + '</p>';
                    return;
                }
                const d = await r.json();
                const s = d.summary || {};
                const totalRelaxed = s.total_relaxed || 0;
                const noResultAfterRelax = s.no_result_after_relax || 0;
                const windowSize = s.window_size || 0;
                const byReason = s.by_reason || {};

                summaryEl.innerHTML =
                    '<div class="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">' +
                    '<div><span class="text-gray-600 block">Relaxed Search ทั้งหมด</span><span class="text-xl font-bold text-amber-700">' + totalRelaxed + '</span></div>' +
                    '<div><span class="text-gray-600 block">ยังไม่เจอผลหลัง Relaxed</span><span class="text-xl font-bold text-amber-700">' + noResultAfterRelax + '</span></div>' +
                    '<div><span class="text-gray-600 block">ขนาดหน้าต่างข้อมูล</span><span class="text-xl font-bold text-amber-700">' + windowSize + ' events</span></div>' +
                    '</div>';

                const rows = Object.entries(byReason)
                    .sort((a, b) => (b[1] || 0) - (a[1] || 0))
                    .map(([reason, count]) =>
                        '<tr class="border-b"><td class="py-2 px-2 font-mono text-xs">' + reason + '</td><td class="py-2 px-2">' + count + '</td></tr>'
                    )
                    .join('');
                byReasonEl.innerHTML = rows
                    ? ('<table class="min-w-full border"><thead><tr class="border-b bg-amber-50"><th class="text-left py-2 px-2">Reason</th><th class="text-left py-2 px-2">Count</th></tr></thead><tbody>' + rows + '</tbody></table>')
                    : '<p class="text-gray-500">ยังไม่มีข้อมูล reason</p>';
            } catch (e) {
                summaryEl.innerHTML = '<p class="text-red-600">Error: ' + e.message + '</p>';
            }
        }

        async function loadAITripPlanningFlow() {
            const summaryEl = document.getElementById('tripPlanningFlowSummary');
            const stepsEl = document.getElementById('tripPlanningFlowSteps');
            const choiceEl = document.getElementById('tripPlanningChoiceDetails');
            if (!summaryEl || !stepsEl || !choiceEl) return;
            summaryEl.textContent = 'กำลังโหลด...';
            stepsEl.textContent = 'กำลังโหลด...';
            choiceEl.textContent = 'กำลังโหลด...';
            try {
                const r = await fetch(API + '/api/admin/ai-trip-planning-flow', opts);
                if (!r.ok) {
                    const msg = 'โหลดไม่สำเร็จ: ' + r.status;
                    summaryEl.innerHTML = '<p class="text-red-600">' + msg + '</p>';
                    stepsEl.textContent = msg;
                    choiceEl.textContent = msg;
                    return;
                }
                const d = await r.json();
                if (d.error) {
                    const msg = d.error || 'ไม่พบข้อมูล';
                    summaryEl.innerHTML = '<p class="text-amber-600">' + msg + '</p>';
                    stepsEl.textContent = msg;
                    choiceEl.textContent = msg;
                    return;
                }

                const meta = d.meta || {};
                const latest = d.latest || {};
                const choices = Array.isArray(d.choices) ? d.choices : (latest.choices || []);

                const esc = (v) => String(v == null ? '' : v)
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/"/g, '&quot;');

                summaryEl.innerHTML =
                    '<div class="space-y-2">' +
                    '<div class="text-sm text-gray-700">ทริปที่ใช้คำนวณ: <strong>' + (meta.total_trips || 0) + '</strong> ทริป • ตัวอย่างล่าสุดจาก session <code class="bg-gray-100 px-1 rounded">' + esc(latest.session_id || '-') + '</code></div>' +
                    (meta.common_pattern ? '<p class="text-xs text-gray-500">Pattern โดยรวม: ' + esc(meta.common_pattern) + '</p>' : '') +
                    '</div>';

                const steps = Array.isArray(latest.steps) ? latest.steps : [];
                stepsEl.innerHTML = steps.length === 0
                    ? '<p class="text-gray-500 text-sm">ยังไม่มี log กระบวนการละเอียด — ลองใช้งานระบบ Trip Planner แล้วกด Refresh อีกครั้ง</p>'
                    : (
                        '<ol class="list-decimal list-inside space-y-1 text-sm text-gray-800">' +
                        steps.map(s =>
                            '<li><span class="font-medium">' + esc(s.stage || s.name || 'ขั้นตอน') + ':</span> ' +
                            esc(s.description || s.detail || '') +
                            (s.score != null ? ' <span class="text-xs text-gray-500">(score: ' + esc(s.score) + ')</span>' : '') +
                            '</li>'
                        ).join('') +
                        '</ol>'
                    );

                choiceEl.innerHTML = choices.length === 0
                    ? '<p class="text-gray-500 text-sm">ยังไม่มีข้อมูล choice ต่อทริป</p>'
                    : (
                        '<table class="min-w-full border text-xs">' +
                        '<thead><tr class="border-b bg-sky-50">' +
                        '<th class="text-left py-2 px-2">Choice</th>' +
                        '<th class="text-left py-2 px-2">ประเภท</th>' +
                        '<th class="text-left py-2 px-2">Score / Rank</th>' +
                        '<th class="text-left py-2 px-2">เหตุผลที่เลือก</th>' +
                        '<th class="text-left py-2 px-2">ถูกเลือกหรือไม่</th>' +
                        '</tr></thead><tbody>' +
                        choices.map(c =>
                            '<tr class="border-b hover:bg-sky-50">' +
                            '<td class="py-2 px-2">' + esc(c.name || c.title || c.id || '-') + '</td>' +
                            '<td class="py-2 px-2">' + esc(c.type || c.category || '-') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + esc(c.score != null ? c.score : (c.rank != null ? ('#' + c.rank) : '-')) + '</td>' +
                            '<td class="py-2 px-2 text-xs text-gray-700">' + esc(c.reason || c.explanation || '-') + '</td>' +
                            '<td class="py-2 px-2 text-center">' + (c.selected ? '<span class="text-emerald-600 font-semibold">✅ ใช้จริง</span>' : '<span class="text-gray-400">—</span>') + '</td>' +
                            '</tr>'
                        ).join('') +
                        '</tbody></table>'
                    );
            } catch (e) {
                const msg = 'Error: ' + e.message;
                summaryEl.innerHTML = '<p class="text-red-600">' + msg + '</p>';
                stepsEl.textContent = msg;
                choiceEl.textContent = msg;
            }
        }

        function refreshAll() {
            const btn = document.getElementById('btnRefresh');
            if (btn) btn.disabled = true;
            Promise.all([loadStatus(), loadCurrentUser(), loadSessions(), loadAILearningMetrics(), loadAIScores(), loadLearningMonitor(), loadSearchRelaxedSummary(), loadAITripPlanningFlow()]).finally(() => { if (btn) btn.disabled = false; });
        }

        loadStatus();
        loadCurrentUser();
        loadSessions();
        loadAILearningMetrics();
        loadAIScores();
        loadLearningMonitor();
        loadSearchRelaxedSummary();
        loadAITripPlanningFlow();

        // ============================================================
        // Notification Simulator JS
        // ============================================================
        const SIM_SCENARIOS = [
            { id: 'flight_delayed',     label: '⏰ Flight Delay',       color: 'yellow' },
            { id: 'flight_cancelled',   label: '🚫 Flight Cancelled',   color: 'red'    },
            { id: 'flight_rescheduled', label: '🔄 Rescheduled',        color: 'blue'   },
            { id: 'trip_alert',         label: '⚠️ Trip Alert',         color: 'orange' },
            { id: 'checkin_flight',     label: '✈️ Check-in Flight',    color: 'sky'    },
            { id: 'checkin_hotel',      label: '🏨 Check-in Hotel',     color: 'teal'   },
            { id: 'payment_success',    label: '✅ Payment Success',    color: 'green'  },
            { id: 'payment_failed',     label: '❌ Payment Failed',     color: 'rose'   },
            { id: 'booking_created',    label: '🎫 Booking Created',    color: 'purple' },
            { id: 'custom',             label: '✏️ Custom',             color: 'gray'   },
        ];
        const COLOR_MAP = {
            yellow: 'border-yellow-400 bg-yellow-50 text-yellow-800 hover:bg-yellow-100',
            red:    'border-red-400 bg-red-50 text-red-800 hover:bg-red-100',
            blue:   'border-blue-400 bg-blue-50 text-blue-800 hover:bg-blue-100',
            orange: 'border-orange-400 bg-orange-50 text-orange-800 hover:bg-orange-100',
            sky:    'border-sky-400 bg-sky-50 text-sky-800 hover:bg-sky-100',
            teal:   'border-teal-400 bg-teal-50 text-teal-800 hover:bg-teal-100',
            green:  'border-green-400 bg-green-50 text-green-800 hover:bg-green-100',
            rose:   'border-rose-400 bg-rose-50 text-rose-800 hover:bg-rose-100',
            purple: 'border-purple-400 bg-purple-50 text-purple-800 hover:bg-purple-100',
            gray:   'border-gray-400 bg-gray-50 text-gray-800 hover:bg-gray-100',
        };
        let simSelectedScenario = '';

        function simRenderScenarios() {
            const grid = document.getElementById('simScenarioGrid');
            grid.innerHTML = SIM_SCENARIOS.map(s => {
                const cls = COLOR_MAP[s.color] || COLOR_MAP.gray;
                return `<button onclick="simSelectScenario('${s.id}')" id="simBtn_${s.id}"
                    class="sim-scenario-btn border-2 rounded-lg px-3 py-2 text-xs font-medium cursor-pointer transition-all ${cls}">
                    ${s.label}
                </button>`;
            }).join('');
        }

        function simSelectScenario(id) {
            simSelectedScenario = id;
            document.querySelectorAll('.sim-scenario-btn').forEach(b => b.classList.remove('ring-2','ring-offset-1','ring-gray-700'));
            const btn = document.getElementById('simBtn_' + id);
            if (btn) btn.classList.add('ring-2','ring-offset-1','ring-gray-700');
            document.getElementById('simDelayRow').classList.toggle('hidden', id !== 'flight_delayed');
            document.getElementById('simCustomRow').classList.toggle('hidden', id !== 'custom');
        }

        function simTab(tab) {
            document.getElementById('simPanelSingle').classList.toggle('hidden', tab !== 'single');
            document.getElementById('simPanelBroadcast').classList.toggle('hidden', tab !== 'broadcast');
            document.getElementById('simTabSingle').className = tab === 'single'
                ? 'px-4 py-1.5 rounded-full text-sm font-medium bg-orange-500 text-white'
                : 'px-4 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200';
            document.getElementById('simTabBroadcast').className = tab === 'broadcast'
                ? 'px-4 py-1.5 rounded-full text-sm font-medium bg-orange-500 text-white'
                : 'px-4 py-1.5 rounded-full text-sm font-medium bg-gray-100 text-gray-600 hover:bg-gray-200';
        }

        async function simLoadUsers() {
            const sel = document.getElementById('simUserId');
            sel.innerHTML = '<option>กำลังโหลด...</option>';
            try {
                const r = await fetch(API + '/api/admin/sim/users', opts);
                const d = await r.json();
                if (!d.ok || !d.users.length) { sel.innerHTML = '<option>ไม่พบ users</option>'; return; }
                sel.innerHTML = '<option value="">-- เลือก User --</option>' +
                    d.users.map(u => `<option value="${u.user_id}">${u.name || u.email} (${u.email})</option>`).join('');
            } catch (e) {
                sel.innerHTML = '<option>โหลดไม่สำเร็จ</option>';
            }
        }

        async function simLoadBookings() {
            const uid = document.getElementById('simUserId').value;
            const sel = document.getElementById('simBookingId');
            sel.innerHTML = '<option value="">-- ไม่ระบุ booking --</option>';
            if (!uid) return;
            try {
                const r = await fetch(API + '/api/admin/sim/bookings?user_id=' + encodeURIComponent(uid), opts);
                const d = await r.json();
                if (!d.ok || !d.bookings.length) return;
                d.bookings.forEach(b => {
                    const opt = document.createElement('option');
                    opt.value = b.booking_id;
                    opt.textContent = `#${b.booking_id.slice(0,8)} | ${b.route} | ${b.status}`;
                    sel.appendChild(opt);
                });
            } catch (e) {}
        }

        async function simTrigger() {
            const userId = document.getElementById('simUserId').value;
            if (!userId) { simShowResult('simResult', false, 'กรุณาเลือก User ก่อน'); return; }
            if (!simSelectedScenario) { simShowResult('simResult', false, 'กรุณาเลือกสถานการณ์ก่อน'); return; }
            const bookingId = document.getElementById('simBookingId').value || null;
            const delayMin = parseInt(document.getElementById('simDelayMin').value, 10) || 60;
            const body = {
                scenario: simSelectedScenario,
                user_id: userId,
                booking_id: bookingId,
                delay_minutes: delayMin,
            };
            if (simSelectedScenario === 'custom') {
                body.custom_title = document.getElementById('simCustomTitle').value.trim();
                body.custom_message = document.getElementById('simCustomMsg').value.trim();
                if (!body.custom_title || !body.custom_message) {
                    simShowResult('simResult', false, 'กรุณากรอกหัวข้อและข้อความสำหรับ Custom'); return;
                }
            }
            const btn = document.getElementById('btnSimTrigger');
            btn.disabled = true; btn.textContent = 'กำลังส่ง...';
            try {
                const r = await fetch(API + '/api/admin/sim/trigger', {
                    ...opts, method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body)
                });
                const d = await r.json();
                simShowResult('simResult', r.ok && d.ok, d.message || (r.ok ? 'ส่งสำเร็จ' : 'เกิดข้อผิดพลาด'));
            } catch (e) {
                simShowResult('simResult', false, 'Error: ' + e.message);
            }
            btn.disabled = false; btn.textContent = '🚀 ส่ง Notification';
        }

        async function simBroadcast() {
            const title = document.getElementById('bcTitle').value.trim();
            const message = document.getElementById('bcMessage').value.trim();
            const type = document.getElementById('bcType').value;
            if (!title || !message) { simShowResult('bcResult', false, 'กรุณากรอกหัวข้อและข้อความ'); return; }
            if (!confirm('ยืนยันส่ง broadcast ไปยังทุก user ในระบบ?')) return;
            const btn = document.getElementById('btnSimBroadcast');
            btn.disabled = true; btn.textContent = 'กำลังส่ง...';
            try {
                const r = await fetch(API + '/api/admin/sim/broadcast', {
                    ...opts, method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, message, type })
                });
                const d = await r.json();
                simShowResult('bcResult', r.ok && d.ok, d.message || (r.ok ? 'ส่งสำเร็จ' : 'เกิดข้อผิดพลาด'));
            } catch (e) {
                simShowResult('bcResult', false, 'Error: ' + e.message);
            }
            btn.disabled = false; btn.textContent = '📢 Broadcast ทุก User';
        }

        function simShowResult(elId, ok, msg) {
            const el = document.getElementById(elId);
            el.className = 'mt-3 p-3 rounded text-sm ' + (ok ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200');
            el.textContent = (ok ? '✅ ' : '❌ ') + msg;
            el.classList.remove('hidden');
            setTimeout(() => el.classList.add('hidden'), 8000);
        }

        simRenderScenarios();
    </script>
</body>
</html>"""

# 🔒 Admin Authentication Helper — รองรับทั้ง Cookie (จากหน้า login) และ Basic Auth
async def verify_admin_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security_optional),
) -> bool:
    """
    ยืนยันตัวตนแอดมิน: ตรวจสอบ cookie (admin_session) ก่อน ถ้าไม่มีหรือไม่ถูกต้องจึงใช้ Basic Auth
    """
    if not settings.admin_require_auth:
        return True
    if not settings.admin_password:
        logger.warning("Admin authentication required but ADMIN_PASSWORD not set. Allowing access.")
        return True
    # 1) Cookie จากหน้า login
    token = request.cookies.get(ADMIN_SESSION_COOKIE)
    if token and verify_admin_session_token(token):
        return True
    # 2) Basic Auth (สำหรับ API client หรือเบราว์เซอร์ที่ยังใช้ popup)
    if credentials:
        provided = credentials.password.encode("utf-8")
        expected = settings.admin_password.encode("utf-8")
        if secrets.compare_digest(provided, expected):
            logger.info(f"Admin authentication successful: {credentials.username}")
            return True
    logger.warning("Admin authentication failed (no valid cookie or Basic credentials)")
    raise HTTPException(
        status_code=401,
        detail="Invalid admin credentials",
        headers={"WWW-Authenticate": "Basic"},
    )

@router.get("/status")
async def get_system_status(_auth: bool = Depends(verify_admin_auth)):
    """
    Check status of all services and system resources
    """
    # 1. Mongo Status
    mongo_ok = False
    mongo_details = "Not connected"
    try:
        # MongoConnectionManager.get_instance() returns ConnectionManager instance
        # So we need to use mongo_ping() directly
        from app.storage.connection_manager import ConnectionManager
        mongo_manager = ConnectionManager.get_instance()
        mongo_ok = await mongo_manager.mongo_ping()
        if mongo_ok:
            # Try to get database info to confirm connection
            try:
                db = mongo_manager.get_mongo_database()
                # Quick check: count collections
                collections = await db.list_collection_names()
                mongo_details = f"Connected ({len(collections)} collections)"
            except Exception as db_err:
                mongo_details = f"Connected (ping OK, but DB access error: {str(db_err)[:50]})"
        else:
            mongo_details = "Ping failed - Connection timeout or server unreachable"
    except Exception as e:
        error_msg = str(e)
        # Truncate long error messages
        if len(error_msg) > 100:
            error_msg = error_msg[:100] + "..."
        mongo_details = f"Connection error: {error_msg}"

    # 2. Gemini Status
    gemini_ok = False
    gemini_details = "API Key missing"
    if settings.gemini_api_key:
        gemini_ok = True
        gemini_details = f"Model: {settings.gemini_model_name} (Ready)"

    # 3. Amadeus Status
    amadeus_ok = False
    amadeus_details = "API Key missing"
    # ✅ Check both search and booking keys for admin dashboard
    has_search_keys = settings.amadeus_search_api_key and settings.amadeus_search_api_secret
    has_booking_keys = settings.amadeus_booking_api_key and settings.amadeus_booking_api_secret
    if has_search_keys or has_booking_keys:
        amadeus_ok = True
        # ✅ Show separate keys status
        search_key_status = "✅" if has_search_keys else "❌"
        booking_key_status = "✅" if has_booking_keys else "❌"
        amadeus_details = f"Search: {settings.amadeus_search_env} ({search_key_status}) | Booking: {settings.amadeus_booking_env} ({booking_key_status})"
    
    # 4. Google Maps Status
    gmaps_ok = False
    gmaps_details = "API Key missing"
    if settings.google_maps_api_key:
        gmaps_ok = True
        gmaps_details = "Ready"
    
    # 5. Omise Status
    omise_ok = False
    omise_details = "API Keys missing"
    try:
        if not settings.omise_secret_key or not settings.omise_public_key:
            omise_details = "API Keys missing"
            logger.debug(f"Omise check: Secret key present: {bool(settings.omise_secret_key)}, Public key present: {bool(settings.omise_public_key)}")
        else:
            # Check if keys are valid format
            secret_valid = settings.omise_secret_key.startswith("skey_")
            public_valid = settings.omise_public_key.startswith("pkey_")
            is_test_mode = settings.omise_secret_key.startswith("skey_test_")
            
            logger.debug(f"Omise check: Secret valid: {secret_valid}, Public valid: {public_valid}, Test mode: {is_test_mode}")
            
            if secret_valid and public_valid:
                mode = "TEST" if is_test_mode else "LIVE"
                # Try to verify API connectivity
                try:
                    import httpx
                    logger.debug(f"Omise check: Attempting to connect to Omise API (mode: {mode})")
                    # Use longer timeout (10s) and asyncio.wait_for for better reliability
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        resp = await asyncio.wait_for(
                            client.get(
                                "https://api.omise.co/account",
                                auth=(settings.omise_secret_key, ""),
                                timeout=10.0
                            ),
                            timeout=10.0
                        )
                        logger.debug(f"Omise API response: Status {resp.status_code}")
                        if resp.status_code == 200:
                            account_data = resp.json()
                            email = account_data.get("email", "N/A")
                            omise_details = f"{mode} mode - Connected (Account: {email[:20]}...)"
                            omise_ok = True
                            logger.info(f"Omise status check: Successfully connected ({mode} mode, Account: {email[:20]}...)")
                        else:
                            error_text = resp.text[:100] if resp.text else f"HTTP {resp.status_code}"
                            omise_details = f"{mode} mode - Auth failed (HTTP {resp.status_code}): {error_text}"
                            omise_ok = False
                            logger.warning(f"Omise status check: Auth failed - HTTP {resp.status_code}, Response: {error_text}")
                except (httpx.TimeoutException, asyncio.TimeoutError):
                    omise_details = f"{mode} mode - Connection timeout (10s)"
                    omise_ok = False
                    logger.warning(f"Omise status check: Connection timeout (10s)")
                except httpx.RequestError as req_err:
                    omise_details = f"{mode} mode - Network error: {str(req_err)[:50]}"
                    omise_ok = False
                    logger.warning(f"Omise status check: Network error - {str(req_err)}")
                except Exception as omise_err:
                    omise_details = f"{mode} mode - Error: {str(omise_err)[:50]}"
                    omise_ok = False
                    logger.error(f"Omise status check: Unexpected error - {str(omise_err)}", exc_info=True)
            else:
                omise_details = f"Invalid key format (secret: {'valid' if secret_valid else 'invalid'}, public: {'valid' if public_valid else 'invalid'})"
                logger.warning(f"Omise status check: Invalid key format - secret_valid: {secret_valid}, public_valid: {public_valid}")
    except Exception as e:
        logger.error(f"Omise status check: Exception during check - {str(e)}", exc_info=True)
        omise_details = f"Check error: {str(e)[:50]}"
        omise_ok = False

    # 5. System Resources
    uptime = time.time() - START_TIME
    process = psutil.Process(os.getpid())
    
    return {
        "timestamp": datetime.now().isoformat(),
        "services": {
            "mongodb": {"status": "ok" if mongo_ok else "error", "message": mongo_details},
            "gemini": {"status": "ok" if gemini_ok else "error", "message": gemini_details},
            "amadeus": {"status": "ok" if amadeus_ok else "error", "message": amadeus_details},
            "google_maps": {"status": "ok" if gmaps_ok else "error", "message": gmaps_details},
            "omise": {"status": "ok" if omise_ok else "error", "message": omise_details}
        },
        "config": {
            "amadeus_safety_guard": settings.amadeus_env == "test",
            "amadeus_env": settings.amadeus_env,
            "amadeus_search_env": settings.amadeus_search_env,
            "amadeus_booking_env": settings.amadeus_booking_env,
            "gemini_model": settings.gemini_model_name
        },
        "system": {
            "uptime_seconds": int(uptime),
            "memory_usage_mb": int(process.memory_info().rss / 1024 / 1024),
            "cpu_usage_percent": process.cpu_percent(),
            "active_threads": process.num_threads()
        }
    }


@router.get("/ai-learning-metrics")
async def get_ai_learning_metrics(_auth: bool = Depends(verify_admin_auth)):
    """
    ตัวชี้วัดผลความแม่นยำและการเรียนรู้ AI ต่อผู้ใช้ (RL, Choice History, Memory)
    """
    try:
        from app.storage.connection_manager import ConnectionManager
        from app.services.selection_preferences import COLLECTION_CHOICE_HISTORY
        mongo_manager = ConnectionManager.get_instance()
        db = mongo_manager.get_mongo_database()
        if db is None:
            return {"error": "Database not available", "rl": {}, "choice_history": {}, "memory": {}, "scores": {}}
        rl_rewards = db["user_feedback_history"]
        rl_qtable = db["user_preference_scores"]
        choice_col = db[COLLECTION_CHOICE_HISTORY]
        memories_col = db["memories"]

        total_rewards = await rl_rewards.count_documents({})
        total_q = await rl_qtable.count_documents({})
        users_with_rewards = len(await rl_rewards.distinct("user_id"))
        users_with_q = len(await rl_qtable.distinct("user_id"))
        recent_rewards = await rl_rewards.find({}).sort("created_at", -1).limit(100).to_list(length=100)
        avg_reward = 0.0
        if recent_rewards:
            avg_reward = sum(r.get("reward", 0) for r in recent_rewards) / len(recent_rewards)
        positive_count = sum(1 for r in recent_rewards if r.get("reward", 0) > 0)
        reward_positive_ratio = (positive_count / len(recent_rewards) * 100) if recent_rewards else 0

        total_choices = await choice_col.count_documents({})
        users_with_choices = len(await choice_col.distinct("user_id"))

        total_memories = await memories_col.count_documents({})
        users_with_memories = len(await memories_col.distinct("user_id"))

        # คะแนนและความมั่นใจจาก RL (normalize reward ~[-0.5,1] → 0-1, ความมั่นใจ = สัดส่วน reward บวก)
        rl_score_normalized = round(max(0.0, min(1.0, (avg_reward + 0.5) / 1.5)), 3)
        rl_confidence_pct = round(reward_positive_ratio, 1)

        return {
            "scores": {
                "rl_score": round(avg_reward, 3),
                "rl_score_normalized": rl_score_normalized,
                "rl_confidence_pct": rl_confidence_pct,
                "description": "คะแนน RL จากค่าเฉลี่ย reward (100 ล่าสุด); ความมั่นใจ = สัดส่วนการเลือกที่เป็นบวก (%)",
                "source_note": "คำนวณจาก MongoDB collection user_feedback_history ทั้งระบบ — เรียงตามเวลาล่าสุด 100 รายการ แล้วหาค่าเฉลี่ย reward และสัดส่วน reward บวก (ไม่ได้ดึงจากบริการภายนอก)",
            },
            "rl": {
                "total_reward_records": total_rewards,
                "total_q_entries": total_q,
                "users_with_rewards": users_with_rewards,
                "users_with_q": users_with_q,
                "recent_avg_reward": round(avg_reward, 3),
                "recent_positive_ratio_pct": round(reward_positive_ratio, 1),
                "score_normalized_0_1": rl_score_normalized,
                "confidence_pct": rl_confidence_pct,
                "description": "Reinforcement Learning: ประวัติการเลือก/ปฏิเสธและ Q-values ต่อ user",
                "source_note": "MongoDB: user_feedback_history = บันทึก reward ต่อเหตุการณ์ (เลือก/ปฏิเสธ/feedback); user_preference_scores = Q-table / คะแนนความชอบต่อ state–action ที่ระบบอัปเดตจากพฤติกรรม",
            },
            "choice_history": {
                "total_records": total_choices,
                "users_with_choices": users_with_choices,
                "description": "ประวัติการเลือกตัวเลือก (flight/hotel/transport) สำหรับสรุปความชอบ",
                "source_note": "MongoDB: user_choice_history — บันทึกเมื่อผู้ใช้เลือกตัวเลือก (เที่ยวบิน/โรงแรม/ขนส่ง ฯลฯ) ในฟลโวที่ระบบบันทึกประวัติการเลือก",
            },
            "memory": {
                "total_memories": total_memories,
                "users_with_memories": users_with_memories,
                "description": "ความจำระยะยาวของ AI ต่อผู้ใช้ (memory consolidation)",
                "source_note": "MongoDB: memories — ข้อความ/ข้อเท็จจริงที่สรุปเก็บเป็น long-term memory ต่อ user_id (consolidation จากบทสนทนาและบริบทที่ระบบบันทึก)",
            },
        }
    except Exception as e:
        logger.warning(f"AI learning metrics failed: {e}", exc_info=True)
        return {"error": str(e), "rl": {}, "choice_history": {}, "memory": {}, "scores": {}}


@router.get("/ai-trip-planning-flow")
async def get_ai_trip_planning_flow(
    limit: int = 50,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    ภาพรวม workflow การวางแผนทริปของ AI แบบทริปต่อทริป

    - ดึงทริปล่าสุดจาก collection `sessions`
    - ผูกกับ workflow_history เพื่อดูลำดับ step (planning → searching → selecting → summary → booking → done)
    - สรุปลำดับ slot/segment ตาม TripPlan (flights_outbound / flights_inbound / accommodation / ground_transport)
    """
    try:
        from app.storage.connection_manager import ConnectionManager
        from app.services.workflow_history import get_workflow_history
        from app.models.trip_plan import TripPlan
        from app.engine.workflow_manager import get_slot_manager

        db = ConnectionManager.get_instance().get_mongo_database()
        if db is None:
            return {"error": "Database not available"}

        q: Dict[str, Any] = {}
        if session_id:
            q["session_id"] = session_id
        if user_id:
            q["user_id"] = user_id

        cursor = db.sessions.find(
            q,
            {"session_id": 1, "user_id": 1, "trip_plan": 1, "last_updated": 1},
        ).sort("last_updated", -1).limit(limit)

        slot_manager = get_slot_manager()
        trips: List[Dict[str, Any]] = []

        async for doc in cursor:
            sid = doc.get("session_id")
            uid = doc.get("user_id")
            raw_plan = doc.get("trip_plan") or {}

            trip_summary: Dict[str, Any] = {
                "session_id": sid,
                "user_id": uid,
                "updated_at": serialize_datetime(doc.get("last_updated")),
                "steps": [],
                "slots": [],
                "choices": [],
            }

            # 1) Workflow history → step sequence
            history_items = await get_workflow_history(session_id=sid, limit=50)
            if history_items:
                # เรียงเวลาเก่า → ใหม่
                ordered = list(reversed(history_items))
                step_seq: List[Dict[str, Any]] = []
                for idx, item in enumerate(ordered, start=1):
                    step_seq.append(
                        {
                            "index": idx,
                            "stage": item.get("to_step") or item.get("from_step") or "",
                            "from_step": item.get("from_step"),
                            "to_step": item.get("to_step"),
                            "at": item.get("ts") or item.get("at"),
                        }
                    )
                trip_summary["steps"] = step_seq

            # 2) TripPlan → slot/segment sequence
            try:
                if raw_plan:
                    plan = TripPlan.model_validate(raw_plan)
                    slot_rows = []
                    for slot_name, seg, idx in slot_manager.get_all_segments(plan):
                        status_val = getattr(seg, "status", None)
                        if hasattr(status_val, "value"):
                            status_str = status_val.value  # type: ignore[assignment]
                        else:
                            status_str = str(status_val) if status_val is not None else None
                        row = {
                            "slot": slot_name,
                            "segment_index": idx,
                            "status": status_str,
                            "has_options": bool(getattr(seg, "options_pool", [])),
                            "has_selected": bool(getattr(seg, "selected_option", None)),
                        }
                        slot_rows.append(row)
                    trip_summary["slots"] = slot_rows
            except Exception as plan_err:
                logger.debug(f"ai-trip-planning-flow: TripPlan parse failed for session {sid}: {plan_err}")

            trips.append(trip_summary)

        latest = trips[0] if trips else {}
        meta: Dict[str, Any] = {
            "total_trips": len(trips),
            "has_latest": bool(latest),
        }

        # สรุป pattern รวมแบบสั้น ๆ จากทุกทริป
        common_pattern = None
        if trips:
            step_counts: Dict[str, int] = {}
            for t in trips:
                for s in t.get("steps", []):
                    stage = (s.get("stage") or "").lower()
                    if not stage:
                        continue
                    step_counts[stage] = step_counts.get(stage, 0) + 1
            if step_counts:
                ordered = sorted(step_counts.items(), key=lambda x: -x[1])
                common_pattern = " → ".join(name for name, _ in ordered[:5])
        meta["common_pattern"] = common_pattern

        return {
            "meta": meta,
            "latest": latest,
            "trips": trips,
        }
    except Exception as e:
        logger.warning(f"ai-trip-planning-flow failed: {e}", exc_info=True)
        return {"error": str(e)}


@router.get("/ai-scores")
async def get_ai_scores(
    limit: int = 300,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    คะแนน AI ทั้งหมด: ประเมินจากแชท (sessions) + My Bookings (bookings) + trip_evaluations
    รวมความสามารถรวม (overall), คะแนนเรียนรู้ต่อ User
    """
    try:
        from app.storage.connection_manager import ConnectionManager
        from app.services.trip_evaluations import COLLECTION_NAME
        from app.engine.reinforcement_learning import get_rl_service

        db = ConnectionManager.get_instance().get_mongo_database()
        if db is None:
            return {"error": "Database not available", "trips": [], "overall": {}, "per_user": []}

        # 1) ทริปที่มีคะแนนประเมินแล้ว (trip_evaluations)
        col = db[COLLECTION_NAME]
        cursor = col.find({}).sort("updated_at", -1).limit(limit)
        eval_by_session: Dict[str, Dict[str, Any]] = {}
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            d = serialize_datetime(doc)
            sid = d.get("session_id") or ""
            eval_by_session[sid] = d

        # 2) แชท (sessions) — ทริปจากแชทที่ยังไม่มีแถวใน trip_evaluations ก็นับรวม
        session_cursor = db.sessions.find({}, {"session_id": 1, "user_id": 1, "last_updated": 1, "mode": 1}).sort("last_updated", -1).limit(limit)
        async for doc in session_cursor:
            sid = doc.get("session_id")
            if not sid or sid in eval_by_session:
                continue
            eval_by_session[sid] = {
                "session_id": sid,
                "user_id": doc.get("user_id") or "",
                "mode": doc.get("mode") or "chat",
                "agent_accuracy_score": None,
                "user_stars": None,
                "updated_at": serialize_datetime(doc.get("last_updated")) if doc.get("last_updated") else None,
                "source": "chat",
            }

        # 3) My Bookings — การจองจาก bookings
        booking_cursor = db["bookings"].find(
            {},
            {"booking_id": 1, "user_id": 1, "created_at": 1, "status": 1, "metadata.auto_booked": 1},
        ).sort("created_at", -1).limit(limit)
        async for doc in booking_cursor:
            bid = doc.get("booking_id") or str(doc.get("_id", ""))
            sid = "booking:" + str(bid)
            if sid in eval_by_session:
                continue
            metadata = doc.get("metadata") or {}
            eval_by_session[sid] = {
                "session_id": sid,
                "user_id": doc.get("user_id") or "",
                "mode": "booking",
                "agent_accuracy_score": None,
                "user_stars": None,
                "updated_at": serialize_datetime(doc.get("created_at")) if doc.get("created_at") else None,
                "source": "booking",
                "booking_status": doc.get("status"),
                "auto_booked": bool(metadata.get("auto_booked")),
            }

        # รวมเป็น list แล้วเรียงตาม updated_at ล่าสุด
        trips = list(eval_by_session.values())
        def _sort_key(t):
            u = t.get("updated_at")
            if u is None:
                return ""
            return u if isinstance(u, str) else str(u)
        trips.sort(key=_sort_key, reverse=True)
        trips = trips[:limit]

        # ถ้ายังไม่มีคะแนนความแม่นยำจาก evaluator ให้ AI ประเมินตนเองอัตโนมัติ
        for t in trips:
            if t.get("agent_accuracy_score") is None:
                t["agent_accuracy_score"] = _estimate_self_ai_score(t)
                t["ai_score_source"] = "self_estimated"
            else:
                t["ai_score_source"] = t.get("ai_score_source") or "evaluated"

        # ความพึงพอใจ % ต่อทริป (สอดคล้องกับ agent-feedback / satisfaction_pct)
        for t in trips:
            u_sat = _trip_user_satisfaction_pct(t)
            if u_sat is not None:
                t["user_satisfaction_pct"] = u_sat

        # Overall: คะแนนเฉลี่ยคิดจากแถวที่มีคะแนนเท่านั้น
        acc_list = [t["agent_accuracy_score"] for t in trips if t.get("agent_accuracy_score") is not None]
        stars_list = [t["user_stars"] for t in trips if t.get("user_stars") is not None]
        sat_list = [t["user_satisfaction_pct"] for t in trips if t.get("user_satisfaction_pct") is not None]
        avg_accuracy = round(sum(acc_list) / len(acc_list), 1) if acc_list else None
        avg_user_stars = round(sum(stars_list) / len(stars_list), 1) if stars_list else None
        avg_user_satisfaction_pct = round(sum(sat_list) / len(sat_list), 1) if sat_list else None
        n_star_trips = len(stars_list)
        sum_user_stars = round(sum(float(x) for x in stars_list), 1) if stars_list else None
        max_user_stars_possible = n_star_trips * 5 if n_star_trips else None
        # ความสามารถรวม: เฉลี่ย arithmetic ของ AI % กับความพึงพอใจ % (สเกลเดียวกัน)
        combined_pct = None
        if avg_accuracy is not None and avg_user_satisfaction_pct is not None:
            combined_pct = round((avg_accuracy + avg_user_satisfaction_pct) / 2, 0)
        elif avg_user_satisfaction_pct is not None:
            combined_pct = round(avg_user_satisfaction_pct, 0)
        elif avg_accuracy is not None:
            combined_pct = round(avg_accuracy, 0)
        overall = {
            "total_trips": len(trips),
            "trips_with_accuracy": len(acc_list),
            "trips_with_user_stars": len(stars_list),
            "trips_with_user_satisfaction": len(sat_list),
            "avg_accuracy": avg_accuracy,
            "avg_user_stars": avg_user_stars,
            "avg_user_satisfaction_pct": avg_user_satisfaction_pct,
            "sum_user_stars": sum_user_stars,
            "max_user_stars_possible": max_user_stars_possible,
            "combined_score_pct": combined_pct,
            "combined_score_formula": "ความสามารถรวม = (คะแนนความแม่นยำ AI % + ความพึงพอใจผู้ใช้ %) ÷ 2 — ความพึงพอใจใช้ satisfaction_pct (ดาวรวม+หัวข้อย่อย) หรือแปลงจากดาวรวม",
        }

        # Per-user: จากทริปรวม (แชท + บุ๊คกิ้ง + ประเมิน)
        user_agg: Dict[str, Any] = {}
        for t in trips:
            uid = t.get("user_id")
            if not uid:
                continue
            if uid not in user_agg:
                user_agg[uid] = {
                    "user_id": uid,
                    "trips": [],
                    "acc_sum": 0,
                    "acc_n": 0,
                    "stars_sum": 0,
                    "stars_n": 0,
                    "sat_sum": 0.0,
                    "sat_n": 0,
                }
            user_agg[uid]["trips"].append(t)
            if t.get("agent_accuracy_score") is not None:
                user_agg[uid]["acc_sum"] += t["agent_accuracy_score"]
                user_agg[uid]["acc_n"] += 1
            if t.get("user_stars") is not None:
                user_agg[uid]["stars_sum"] += t["user_stars"]
                user_agg[uid]["stars_n"] += 1
            if t.get("user_satisfaction_pct") is not None:
                user_agg[uid]["sat_sum"] += float(t["user_satisfaction_pct"])
                user_agg[uid]["sat_n"] += 1

        rl_svc = get_rl_service()
        per_user = []
        for uid, agg in user_agg.items():
            trip_count = len(agg["trips"])
            avg_acc = round(agg["acc_sum"] / agg["acc_n"], 1) if agg["acc_n"] else None
            avg_stars = round(agg["stars_sum"] / agg["stars_n"], 1) if agg["stars_n"] else None
            avg_sat = round(agg["sat_sum"] / agg["sat_n"], 1) if agg["sat_n"] else None
            combined = None
            if avg_acc is not None and avg_sat is not None:
                combined = round((avg_acc + avg_sat) / 2, 0)
            elif avg_sat is not None:
                combined = round(avg_sat, 0)
            elif avg_acc is not None:
                combined = round(avg_acc, 0)
            rl_stats = await rl_svc.get_user_stats(uid)
            stars_n = agg["stars_n"]
            stars_sum = agg["stars_sum"]
            per_user.append({
                "user_id": uid,
                "trip_count": trip_count,
                "avg_accuracy": avg_acc,
                "avg_user_stars": avg_stars,
                "avg_user_satisfaction_pct": avg_sat,
                "sum_user_stars": round(float(stars_sum), 1) if stars_n else None,
                "max_user_stars_possible": stars_n * 5 if stars_n else None,
                "combined_score_pct": combined,
                "rl_reward_records": rl_stats.get("total_reward_records", 0),
                "rl_q_entries": rl_stats.get("qtable_entries", 0),
                "rl_recent_avg_reward": rl_stats.get("recent_avg_reward"),
            })
        per_user.sort(key=lambda x: -x["trip_count"])

        return {
            "trips": trips,
            "overall": overall,
            "per_user": per_user,
        }
    except Exception as e:
        logger.warning(f"AI scores failed: {e}", exc_info=True)
        return {"error": str(e), "trips": [], "overall": {}, "per_user": []}


@router.get("/learning-monitor")
async def get_learning_monitor(
    limit: int = 50,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    Learning Monitor — แสดงให้ Dev เห็นว่า AI เรียนรู้พฤติกรรม/ความชอบของ User อย่างไร
    (User ใหม่ใช้ Ask 1 ครั้ง + Agent 1 ครั้ง → inferred prefs, choice history, stars, RL)
    """
    try:
        from app.storage.connection_manager import ConnectionManager
        from app.services.trip_evaluations import COLLECTION_NAME as TRIP_EVAL_COL
        from app.services.selection_preferences import COLLECTION_CHOICE_HISTORY

        db = ConnectionManager.get_instance().get_mongo_database()
        if db is None:
            return {"error": "Database not available", "users_learning": [], "learning_events": []}

        # รวบรวม user_id ที่มีกิจกรรมการเรียนรู้ (จาก sessions, trip_evaluations, choice_history, feedback_history)
        user_ids = set()
        for col_name in ["sessions", TRIP_EVAL_COL, COLLECTION_CHOICE_HISTORY, "user_feedback_history"]:
            col = db[col_name]
            cursor = col.find({}, {"user_id": 1, "session_id": 1}).limit(limit * 2)
            async for doc in cursor:
                uid_val = doc.get("user_id")
                if not uid_val and col_name == "sessions" and doc.get("session_id"):
                    sid = str(doc["session_id"])
                    if "::" in sid:
                        uid_val = sid.split("::")[0]
                if uid_val:
                    user_ids.add(uid_val)
        user_ids = list(user_ids)[:limit]

        users_learning = []
        for uid in user_ids:
            user_doc = await db["users"].find_one(
                {"user_id": uid},
                {"preferences": 1, "full_name": 1, "first_name": 1, "last_name": 1,
                 "first_name_th": 1, "last_name_th": 1, "email": 1},
            )
            # บุคคลอ่านชื่อ: ภาษาไทย → ไทย+อังกฤษ → email prefix → uidสั้น
            ud = user_doc or {}
            name_th = f"{ud.get('first_name_th', '')} {ud.get('last_name_th', '')}".strip()
            name_en = ud.get("full_name") or f"{ud.get('first_name', '')} {ud.get('last_name', '')}".strip()
            email = ud.get("email", "")
            display_name = (
                name_th
                or name_en
                or (email.split("@")[0] if email else "")
                or uid[:16]
            )
            prefs = ud.get("preferences") or {}
            travel = prefs.get("travelPreferences") or {}
            inferred = bool(prefs.get("inferred_from_chat"))
            prefs_summary = []
            if travel.get("budget_level"):
                prefs_summary.append(f"งบ:{travel['budget_level']}")
            if travel.get("travel_style"):
                prefs_summary.append(f"สไตล์:{travel['travel_style']}")
            if travel.get("preferred_destinations"):
                dests = travel["preferred_destinations"]
                if isinstance(dests, list):
                    prefs_summary.append("ปลายทาง:" + ",".join(dests[:3]))
                else:
                    prefs_summary.append("ปลายทาง:" + str(dests))
            if travel.get("prefer_direct_flight"):
                prefs_summary.append("บินตรง")
            if not prefs_summary and travel:
                # แสดงค่าอื่นที่ infer บันทึก (min_price, max_price, travelers ฯลฯ) เพื่อไม่ให้คอลัมน์ "ความชอบ" ว่าง
                if travel.get("min_price") is not None or travel.get("max_price") is not None:
                    prefs_summary.append(f"งบประมาณ:{travel.get('min_price', '?')}-{travel.get('max_price', '?')}")
                if travel.get("travelers"):
                    prefs_summary.append(f"{travel['travelers']} คน")
                if travel.get("has_children"):
                    prefs_summary.append("มีเด็ก")
                if not prefs_summary:
                    prefs_summary.append("มีข้อมูลความชอบ")

            choice_count = await db[COLLECTION_CHOICE_HISTORY].count_documents({"user_id": uid})
            trip_col = db[TRIP_EVAL_COL]
            last_trip = await trip_col.find_one(
                {"user_id": uid},
                {"user_stars": 1, "satisfaction_pct": 1, "agent_accuracy_score": 1, "updated_at": 1},
                sort=[("updated_at", -1)],
            )
            last_stars = last_trip.get("user_stars") if last_trip else None
            last_sat_pct = None
            if last_trip:
                last_sat_pct = _trip_user_satisfaction_pct(last_trip)
            last_activity = last_trip.get("updated_at") if last_trip else None
            if last_activity is None:
                last_session = await db["sessions"].find_one(
                    {"user_id": uid},
                    {"last_updated": 1},
                    sort=[("last_updated", -1)],
                )
                if last_session and last_session.get("last_updated"):
                    last_activity = last_session["last_updated"]

            reward_count = await db["user_feedback_history"].count_documents({"user_id": uid})
            q_count = await db["user_preference_scores"].count_documents({"user_id": uid})

            # ── ถ้ายังไม่มี prefs_summary ให้ดึงจาก Q-table (RL) รายการที่คะแนนสูงสุด ──
            if not prefs_summary and q_count > 0:
                try:
                    top_q = await db["user_preference_scores"].find(
                        {"user_id": uid, "q_value": {"$gt": 0}},
                        {"slot_name": 1, "option_key": 1, "q_value": 1},
                    ).sort("q_value", -1).limit(3).to_list(length=3)
                    for q in top_q:
                        slot = q.get("slot_name") or ""
                        key = q.get("option_key") or ""
                        qval = q.get("q_value", 0)
                        # ตัด slot: prefix และ key ให้สั้น
                        slot_short = slot.replace("flights_", "✈").replace("accommodation", "🏨").replace("ground_transport", "🚗")
                        key_short = key.split(":")[-1][:18] if ":" in key else key[:18]
                        prefs_summary.append(f"{slot_short} {key_short}({qval:+.2f})")
                    if prefs_summary:
                        inferred = True  # มีข้อมูล RL = AI รู้จัก
                except Exception as _qe:
                    logger.debug(f"Q-table pref lookup: {_qe}")

            # ── FWL: ดึง feature weights สรุปสั้นๆ ──────────────────────────────────
            fwl_slots = 0
            fwl_updates = 0
            fwl_summary = ""
            try:
                from app.engine.feature_learning import get_feature_learner
                fwl_docs = await get_feature_learner().get_user_weights_doc(uid)
                fwl_slots = len(fwl_docs)
                fwl_updates = sum(d.get("update_count", 0) for d in fwl_docs)
                # สรุปสั้นๆ: top positive weight per slot
                fwl_parts = []
                FEAT_EMOJI = {
                    "f_is_direct": "✈ตรง", "f_budget_airline": "LCC",
                    "f_price": "💰", "f_cabin": "🌟", "h_stars": "⭐",
                    "h_price": "🏨💰", "t_is_private": "🚗ส่วนตัว",
                }
                for doc in fwl_docs:
                    ws = doc.get("weights") or {}
                    if not ws:
                        continue
                    best = max(ws.items(), key=lambda x: x[1], default=(None, 0))
                    worst = min(ws.items(), key=lambda x: x[1], default=(None, 0))
                    slot_label = doc.get("slot_type", "")
                    if best[0] and best[1] > 0.15:
                        fwl_parts.append(f"{slot_label}:{FEAT_EMOJI.get(best[0], best[0])}(⮝{best[1]:+.1f})")
                    if worst[0] and worst[1] < -0.15:
                        fwl_parts.append(f"{slot_label}:{FEAT_EMOJI.get(worst[0], worst[0])}(⮛{worst[1]:+.1f})")
                fwl_summary = " ".join(fwl_parts[:4])
            except Exception as _fe:
                logger.debug(f"FWL summary for user {uid}: {_fe}")

            users_learning.append({
                "user_id": uid,
                "user_name": display_name,
                "inferred_from_chat": inferred,
                "travel_prefs_summary": " | ".join(prefs_summary) if prefs_summary else "—",
                "choice_count": choice_count,
                "last_user_stars": last_stars,
                "last_user_satisfaction_pct": last_sat_pct,
                "last_activity": serialize_datetime(last_activity) if last_activity else None,
                "rl_reward_count": reward_count,
                "rl_q_entries": q_count,
                "fwl_slots": fwl_slots,
                "fwl_updates": fwl_updates,
                "fwl_summary": fwl_summary,
            })

        # เรียงตาม last_activity ล่าสุด (มีกิจกรรมล่าสุดอยู่บน)
        users_learning.sort(
            key=lambda x: (x["last_activity"] or ""),
            reverse=True,
        )

        # Learning events: จาก user_feedback_history — ครอบคลุมทุก action type
        events = []
        ev_cursor = db["user_feedback_history"].find({}).sort("created_at", -1).limit(50)
        async for doc in ev_cursor:
            action = doc.get("action_type", "")
            ctx = doc.get("context") or {}
            slot = doc.get("slot_name") or ""
            reward = doc.get("reward")
            reward_str = f" (reward={reward:+.2f})" if isinstance(reward, (int, float)) else ""
            detail = ""
            if action == "user_star_rating":
                pct = ctx.get("satisfaction_pct")
                pct_s = f" ({pct}% รวมหัวข้อ)" if pct is not None else ""
                detail = f"ให้คะแนน {ctx.get('stars', '?')} ดาว{pct_s}{reward_str}"
            elif action == "select_option":
                detail = f"Slot: {slot}{reward_str}"
            elif action in ("book", "complete_booking"):
                detail = f"จองสำเร็จ Slot: {slot}{reward_str}"
            elif action in ("reject", "reject_option"):
                detail = f"ปฏิเสธตัวเลือก Slot: {slot}{reward_str}"
            elif action in ("cancel", "cancel_booking"):
                detail = f"ยกเลิกการจอง Slot: {slot}{reward_str}"
            elif action == "positive_feedback":
                detail = f"Feedback บวก Slot: {slot}{reward_str}"
            elif action == "negative_feedback":
                detail = f"Feedback ลบ Slot: {slot}{reward_str}"
            elif action in ("edit", "edit_selection"):
                detail = f"แก้ไขการเลือก Slot: {slot}{reward_str}"
            else:
                detail = f"Slot: {slot}{reward_str}" if slot else reward_str
            uid_short = doc.get("user_id", "")
            # ดึงชื่อ user จาก users_learning map
            ev_uid = uid_short
            events.append({
                "user_id": ev_uid,
                "event_type": action,
                "detail": detail,
                "reward": reward,
                "created_at": serialize_datetime(doc.get("created_at")),
            })
        events = serialize_datetime(events)

        return {
            "users_learning": users_learning,
            "learning_events": events,
        }
    except Exception as e:
        logger.warning(f"Learning monitor failed: {e}", exc_info=True)
        return {"error": str(e), "users_learning": [], "learning_events": []}


@router.get("/logs")
async def get_logs(lines: int = 100, _auth: bool = Depends(verify_admin_auth)):
    """
    Read the last N lines of the log file
    """
    if not settings.log_file:
        return {"message": "Log file not configured in settings"}
    
    log_path = Path(settings.log_file)
    if not log_path.exists():
        return {"message": f"Log file not found at {log_path}"}
    
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            # Read all lines and take last N
            all_lines = f.readlines()
            return {
                "filename": log_path.name,
                "total_lines": len(all_lines),
                "requested_lines": lines,
                "content": all_lines[-lines:]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read logs: {e}")


@router.get("/workflow-history")
async def get_workflow_history_debug(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    ดึงประวัติ workflow (planning → selecting → booking → done) สำหรับ debug/analytics
    กรองด้วย session_id หรือ user_id ได้
    """
    try:
        from app.services.workflow_history import get_workflow_history
        items = await get_workflow_history(session_id=session_id, user_id=user_id, limit=limit)
        return {"count": len(items), "items": items}
    except Exception as e:
        logger.warning(f"get_workflow_history failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions")
async def get_recent_sessions(
    limit: int = 10, 
    user_id: Optional[str] = None,
    _auth: bool = Depends(verify_admin_auth)
):
    """
    Get summary of recent sessions from MongoDB (direct database query)
    ✅ SECURITY: If user_id is provided, only return sessions for that user
    If user_id is not provided, return all sessions (admin only)
    ✅ DIRECT DB SYNC: This endpoint queries MongoDB directly, not from Redis
    """
    try:
        # Verify MongoDB connection first
        from app.storage.connection_manager import ConnectionManager
        mongo_manager = ConnectionManager.get_instance()
        mongo_ok = await mongo_manager.mongo_ping()
        if not mongo_ok:
            logger.error("MongoDB connection failed - cannot fetch sessions")
            raise HTTPException(
                status_code=503,
                detail="MongoDB is not available. Please check MongoDB connection."
            )
        
        db = mongo_manager.get_mongo_database()
        
        # ✅ SECURITY: If user_id is specified, only query that user's sessions
        query_filter = {}
        if user_id:
            query_filter["user_id"] = user_id
            logger.info(f"Admin query: Getting sessions for user_id={user_id}")
        else:
            logger.warning(f"Admin query: Getting ALL sessions (no user_id filter - admin access only)")
        
        # Query MongoDB directly (not from Redis)
        cursor = db.sessions.find(query_filter).sort("last_updated", -1).limit(limit)
        sessions = []
        async for doc in cursor:
            # ✅ SECURITY: Verify user_id matches if filter was applied
            if user_id:
                doc_user_id = doc.get("user_id")
                if doc_user_id != user_id:
                    logger.warning(f"Admin query found session with mismatched user_id: expected {user_id}, found {doc_user_id}, skipping")
                    continue
            
            # Clean up ObjectId for JSON
            doc["_id"] = str(doc["_id"])
            # ✅ PRIVACY: Remove sensitive trip_plan data from admin view (keep summary only)
            if "trip_plan" in doc:
                # Only include summary info, not full plan data
                trip_plan = doc["trip_plan"]
                doc["trip_plan_summary"] = {
                    "has_flights": bool(trip_plan.get("travel", {}).get("flights", {}).get("outbound") or trip_plan.get("travel", {}).get("flights", {}).get("inbound")),
                    "has_hotels": bool(trip_plan.get("accommodation", {}).get("segments")),
                    "has_transport": bool(trip_plan.get("travel", {}).get("ground_transport"))
                }
                # Remove full trip_plan to protect privacy and reduce payload size
                del doc["trip_plan"]
            
            # ✅ Serialize datetime objects to ISO strings
            doc = serialize_datetime(doc)
            sessions.append(doc)
        
        logger.info(f"Admin query: Retrieved {len(sessions)} sessions from MongoDB (limit={limit})")
        return sessions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin query error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch sessions from MongoDB: {str(e)}"
        )


@router.get("/sessions/{session_id}/amadeus-viewer")
async def get_session_amadeus_viewer(
    session_id: str,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    ดึงข้อมูลที่ได้จาก Amadeus สำหรับทริป (session) นั้นเท่านั้น
    คืนค่า: options (เที่ยวบิน/ที่พัก/รถรับส่ง ที่แคชไว้) และ raw_amadeus (response ดิบจาก Amadeus ต่อ slot)
    """
    try:
        from app.storage.connection_manager import ConnectionManager

        cache = get_options_cache()

        def _empty_options() -> Dict[str, Any]:
            return {
                "flights_outbound": [],
                "flights_inbound": [],
                "ground_transport": [],
                "accommodation": [],
            }

        def _merge_options(target: Dict[str, Any], incoming: Dict[str, Any]) -> None:
            for slot in ("flights_outbound", "flights_inbound", "ground_transport", "accommodation"):
                segments = incoming.get(slot) or []
                if not isinstance(segments, list):
                    continue
                for seg in segments:
                    if isinstance(seg, list) and seg:
                        target[slot].append(seg)

        def _count_slot(val: Any) -> int:
            if not val:
                return 0
            if isinstance(val, list):
                return sum(len(seg) if isinstance(seg, list) else 1 for seg in val)
            return 0

        options = _empty_options()
        raw_amadeus: Dict[str, Any] = {}
        resolved_session_ids: List[str] = []

        # 1) Try exact session_id first
        one_options = await cache.get_all_session_options(session_id)
        one_raw = await cache.get_raw_amadeus(session_id)
        _merge_options(options, one_options or {})
        if isinstance(one_raw, dict):
            raw_amadeus.update(one_raw)
        resolved_session_ids.append(session_id)

        def _total_count(data: Dict[str, Any]) -> int:
            return (
                _count_slot(data.get("flights_outbound"))
                + _count_slot(data.get("flights_inbound"))
                + _count_slot(data.get("ground_transport"))
                + _count_slot(data.get("accommodation"))
            )

        # 2) Fallback: if empty, aggregate by trip sessions (covers old rows that pass trip_id)
        source_scope = "session"
        if _total_count(options) == 0:
            db = ConnectionManager.get_instance().get_mongo_database()
            if db is not None:
                session_doc = await db.sessions.find_one(
                    {"$or": [{"session_id": session_id}, {"trip_id": session_id}, {"chat_id": session_id}]},
                    {"trip_id": 1, "user_id": 1, "chat_id": 1, "session_id": 1},
                )
                if session_doc:
                    trip_id = session_doc.get("trip_id") or (session_id if "::" not in session_id else None)
                    user_id = session_doc.get("user_id")
                    if trip_id and user_id:
                        cursor = db.sessions.find(
                            {"trip_id": trip_id, "user_id": user_id},
                            {"session_id": 1, "chat_id": 1},
                        ).sort("last_updated", -1).limit(50)
                        async for sdoc in cursor:
                            sid = sdoc.get("session_id")
                            if not sid and sdoc.get("chat_id"):
                                sid = f"{user_id}::{sdoc.get('chat_id')}"
                            if not sid or sid in resolved_session_ids:
                                continue
                            resolved_session_ids.append(sid)
                            s_options = await cache.get_all_session_options(sid)
                            s_raw = await cache.get_raw_amadeus(sid)
                            _merge_options(options, s_options or {})
                            if isinstance(s_raw, dict):
                                for k, v in s_raw.items():
                                    raw_amadeus[f"{sid}|{k}"] = v
                        if len(resolved_session_ids) > 1:
                            source_scope = "trip"

        summary = {
            "flights_outbound": _count_slot(options.get("flights_outbound")),
            "flights_inbound": _count_slot(options.get("flights_inbound")),
            "ground_transport": _count_slot(options.get("ground_transport")),
            "accommodation": _count_slot(options.get("accommodation")),
        }
        return {
            "session_id": session_id,
            "source_scope": source_scope,
            "resolved_session_ids": resolved_session_ids,
            "summary": summary,
            "options": serialize_datetime(options),
            "raw_amadeus": serialize_datetime(raw_amadeus),
        }
    except Exception as e:
        logger.error(f"Amadeus viewer for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# AI รู้จัก User (%) — วัดด้วย AI ว่า AI รู้จัก user มากน้อยแค่ไหน
# =============================================================================

async def _gather_user_context_for_familiarity(user_id: str) -> Dict[str, Any]:
    """รวบรวม memory, profile, travel_preferences สำหรับ user_id (ใช้ใน admin เท่านั้น)."""
    from app.storage.connection_manager import ConnectionManager
    db = ConnectionManager.get_instance().get_mongo_database()
    memory_context = ""
    user_profile_context = ""
    travel_preferences: Dict[str, Any] = {}
    try:
        memory_svc = MemoryService()
        memories = await memory_svc.recall(user_id, limit=15)
        memory_context = memory_svc.format_memories_for_prompt(memories) if memories else ""
    except Exception as e:
        logger.warning(f"Admin user-familiarity: memory recall failed for {user_id}: {e}")
    try:
        user_doc = await db["users"].find_one({"user_id": user_id})
        if user_doc:
            name = user_doc.get("full_name") or user_doc.get("name") or user_doc.get("first_name") or ""
            email = user_doc.get("email") or ""
            prefs = user_doc.get("preferences") or {}
            parts = []
            if name:
                parts.append(f"ชื่อ: {name}")
            if email:
                parts.append(f"Email: {email}")
            travel_prefs = prefs.get("travelPreferences") or {}
            if travel_prefs:
                travel_preferences = dict(travel_prefs)
                tp_parts = []
                if travel_prefs.get("budget_level"):
                    tp_parts.append(f"งบ: {travel_prefs['budget_level']}")
                if travel_prefs.get("travel_style"):
                    tp_parts.append(f"สไตล์: {travel_prefs['travel_style']}")
                if tp_parts:
                    parts.append("ความชอบการเดินทาง: " + " | ".join(tp_parts))
            if prefs.get("memory_summaries"):
                parts.append("ความชอบที่เรียนรู้: " + ", ".join((prefs.get("memory_summaries") or [])[:3]))
            user_profile_context = "; ".join(parts) if parts else ""
        # session-level travel_preferences (ล่าสุด)
        session_doc = await db["sessions"].find_one(
            {"user_id": user_id},
            sort=[("last_updated", -1)],
            projection={"travel_preferences": 1}
        )
        if session_doc and session_doc.get("travel_preferences"):
            travel_preferences = {**travel_preferences, **session_doc["travel_preferences"]}
    except Exception as e:
        logger.warning(f"Admin user-familiarity: profile/prefs failed for {user_id}: {e}")
    has_memory = bool(memory_context and len(memory_context.strip()) > 20)
    has_profile = bool(user_profile_context and len(user_profile_context.strip()) > 10)
    has_prefs = bool(travel_preferences and len(str(travel_preferences)) > 10)
    return {
        "memory_context": memory_context or "(ไม่มีความจำ)",
        "user_profile_context": user_profile_context or "(ไม่มีโปรไฟล์)",
        "travel_preferences": travel_preferences,
        "factors": {"has_memory": has_memory, "has_profile": has_profile, "has_preferences": has_prefs},
    }


def _heuristic_familiarity_score(factors: Dict[str, bool]) -> int:
    """คะแนนประมาณ 0–100 จาก factors (ไม่ใช้ AI): ความจำ +35, โปรไฟล์ +35, ความชอบ +30."""
    score = 0
    if factors.get("has_memory"):
        score += 35
    if factors.get("has_profile"):
        score += 35
    if factors.get("has_preferences"):
        score += 30
    return min(100, score)


def _familiarity_methodology_payload(
    source: str,
    score_percent: int,
    heuristic_baseline: int,
) -> Dict[str, str]:
    """คำอธิบายภาษาไทยว่า % มาจากไหน (ให้ผู้ดูแดชบอร์ดเข้าใจขอบเขตของตัวเลข)."""
    base_rule = (
        "คะแนนฐานแบบกฎคงที่ (ไม่ใช้ LLM): ถ้ามีความจำตามเงื่อนไข +35%, มีโปรไฟล์พอใช้ +35%, "
        "มีความชอบการเดินทาง/เซสชัน +30% — รวมสูงสุด 100%"
    )
    if source == "ai":
        return {
            "score_source_th": "โมเดล LLM (อ่านข้อความที่ย่อจากความจำ/โปรไฟล์/ความชอบ แล้วให้คะแนน 0–100)",
            "heuristic_baseline_percent": str(heuristic_baseline),
            "this_score_th": (
                f"ตัวเลข {score_percent}% มาจากคำตอบของ LLM (จำกัดช่วง 0–100 หลังรับค่า) "
                f"— เป็นดัชนีเชิงภาษาว่ามีบริบทพอให้พูดถึง user นี้หรือไม่ ไม่ใช่ค่าวัดพฤติกรรมจริงในโลกภายนอก"
            ),
            "baseline_compare_th": (
                f"คะแนนฐานจากกฎเดียวกับตาราง Sessions คือ {heuristic_baseline}% "
                "(ใช้เปรียบเทียบกับคะแนน LLM ไม่ได้นำมาผสมเป็นค่าสุดท้าย)"
            ),
            "data_pipeline_th": (
                "ข้อมูลที่ส่งให้ประเมิน: (1) MongoDB memories ผ่าน MemoryService.recall สูงสุด 15 รายการ "
                "(2) users — ชื่อ อีเมล preferences.travelPreferences และ memory_summaries บางส่วน "
                "(3) sessions ล่าสุด — travel_preferences"
            ),
            "factor_gates_th": (
                "เงื่อนไขสวิตช์มี/ไม่มี (สำหรับคะแนนฐานและแสดงในแดชบอร์ด): "
                "ความจำ = ข้อความสรุปความจำยาวมากกว่า 20 ตัวอักษร, "
                "โปรไฟล์ = ข้อความรวมโปรไฟล์ยาวมากกว่า 10 ตัวอักษร, "
                "ความชอบ = มี travel_preferences เมื่อแปลงเป็น string ยาวมากกว่า 10 ตัวอักษร"
            ),
            "batch_sessions_note_th": (
                "คอลัมน์ % ในตาราง Recent Sessions ใช้เฉพาะคะแนนฐานแบบกฎคงที่ (ไม่เรียก LLM) เพื่อความเร็ว — "
                "กด \"วัดด้วย AI\" เพื่อได้คะแนนแบบเดียวกับการ์ดนี้"
            ),
            "base_rule_th": base_rule,
        }
    return {
        "score_source_th": "กฎคงที่ในเซิร์ฟเวอร์ (heuristic) — ไม่เรียก LLM",
        "heuristic_baseline_percent": str(score_percent),
        "this_score_th": (
            f"ตัวเลข {score_percent}% คำนวณตาม {base_rule} เท่านั้น "
            "(สอดคล้องกับสวิตช์ ความจำ / โปรไฟล์ / ความชอบ ที่แสดงด้านบน)"
        ),
        "baseline_compare_th": "ในโหมดนี้ไม่มีคะแนนแยกจาก LLM — ค่าที่เห็นคือคะแนนฐานทั้งหมด",
        "data_pipeline_th": (
            "ข้อมูลที่ใช้ตัดสินใจสวิตช์และข้อความสรุป: memories (MemoryService), users, sessions.travel_preferences — "
            "เหมือนกรณีที่เรียก LLM แต่คะแนนตัวเลขมาจากกฎบวกคงที่เท่านั้น"
        ),
        "factor_gates_th": (
            "เงื่อนไขสวิตช์: ความจำยาวมากกว่า 20 ตัวอักษร, โปรไฟล์มากกว่า 10 ตัวอักษร, "
            "ความชอบ (string ของ travel_preferences) มากกว่า 10 ตัวอักษร"
        ),
        "batch_sessions_note_th": (
            "ตาราง Recent Sessions แสดง % แบบเดียวกับที่นี่ (heuristic) — กด \"วัดด้วย AI\" หากต้องการให้ LLM ประเมินเพิ่ม"
        ),
        "base_rule_th": base_rule,
    }


@router.get("/user-familiarity")
async def get_user_familiarity(
    user_id: Optional[str] = None,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    วัดว่า AI รู้จัก user นี้มากน้อยแค่ไหน (0–100%).
    ปกติ: LLM ให้คะแนนและเหตุผลจากข้อความที่ย่อจาก DB; ถ้า LLM ใช้ไม่ได้ใช้คะแนน heuristic (+35/+35/+30).
    คืนค่า methodology (คำอธิบายแหล่งที่มาและวิธีคิด %) ใน JSON.
    """
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="user_id is required")
    user_id = user_id.strip()
    try:
        ctx = await _gather_user_context_for_familiarity(user_id)
    except Exception as e:
        logger.error(f"Admin user-familiarity gather failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to gather user context: {e}")
    heuristic = _heuristic_familiarity_score(ctx["factors"])
    prompt = f"""คุณเป็นผู้ประเมินว่า AI รู้จัก user นี้มากน้อยแค่ไหน จากข้อมูลที่มีอยู่

=== ความจำระยะยาว (Memory) ===
{ctx["memory_context"][:2000]}

=== โปรไฟล์/ความชอบ (Profile) ===
{ctx["user_profile_context"][:1500]}

=== Travel preferences (จาก session/user) ===
{json.dumps(ctx["travel_preferences"], ensure_ascii=False)[:1000]}

ให้คะแนน 0–100 ว่า "AI รู้จัก user นี้มากน้อยแค่ไหน" (100 = รู้จักดีมาก มีข้อมูลเพียงพอให้วางแผน/แนะนำได้เอง)
กฎสำคัญ: อนุมานและเหตุผลต้องอิงเฉพาะข้อความในบล็อก Memory/Profile/Travel preferences ข้างบนเท่านั้น ห้ามแต่งข้อเท็จจริงที่ไม่ปรากฏในข้อความนั้น
ตอบเฉพาะ JSON เท่านั้น ไม่มี markdown ไม่มีคำอธิบายอื่น:
{{"score": <ตัวเลข 0-100>, "reason": "<ประโยคสั้นๆ ภาษาไทย อธิบายคะแนนโดยอ้างว่ามีข้อมูลประเภทใดจากบล็อกข้างบนบ้าง (เช่น ความจำ โปรไฟล์ ความชอบ)>"}}
"""
    try:
        llm = LLMService()
        raw = await llm.generate_content(
            prompt,
            temperature=0.3,
            max_tokens=300,
        )
        text = (raw or "").strip()
        if not text:
            return _user_familiarity_response(
                user_id, heuristic, "ไม่สามารถให้ AI วัดได้ ใช้คะแนนประมาณจากข้อมูล", ctx, "heuristic_fallback",
            )
        import re as _re
        original_text = text
        if "```" in text:
            parts = text.split("```")
            if len(parts) >= 3:
                text = parts[1].replace("json", "", 1).strip()
            else:
                text = parts[1].replace("json", "", 1).strip()
        json_match = _re.search(r'\{.*\}', text, _re.DOTALL)
        if json_match:
            text = json_match.group(0)
        data = None
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        if data is None:
            search_text = original_text
            score_match = _re.search(r'"?score"?\s*:\s*(\d+)', search_text)
            # รองรับ reason ที่อาจไม่ปิด quote (Unterminated string) — หยุดที่ " ตัวถัดไป หรือ newline
            reason_match = _re.search(r'"?reason"?\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', search_text)
            if not reason_match:
                reason_match = _re.search(r'"?reason"?\s*:\s*"([^"\n]*)', search_text)
            if score_match:
                try:
                    score_val = int(score_match.group(1))
                    reason_val = (reason_match.group(1) if reason_match else "—").strip() or "—"
                    # ตัดความยาวและเอา character ที่ทำให้ JSON เสียออก
                    if len(reason_val) > 200:
                        reason_val = reason_val[:200] + "…"
                    data = {"score": score_val, "reason": reason_val}
                except (ValueError, IndexError, AttributeError):
                    data = {"score": min(100, max(0, heuristic)), "reason": "ใช้คะแนนประมาณจากข้อมูล"}
            else:
                return _user_familiarity_response(
                    user_id, heuristic, "ใช้คะแนนประมาณจากข้อมูล", ctx, "heuristic_fallback",
                )
        try:
            score = max(0, min(100, int(data.get("score", heuristic))))
            reason = (data.get("reason") or "").strip() or "—"
            if len(reason) > 300:
                reason = reason[:300] + "…"
            return _user_familiarity_response(
                user_id, score, reason, ctx, "ai", heuristic_baseline=heuristic,
            )
        except (TypeError, ValueError, KeyError):
            pass
        return _user_familiarity_response(
            user_id, heuristic, "ใช้คะแนนประมาณจากข้อมูล", ctx, "heuristic_fallback",
        )
    except Exception as e:
        logger.warning(f"Admin user-familiarity LLM failed: {e}", exc_info=True)
        return _user_familiarity_response(
            user_id, heuristic, "ใช้คะแนนประมาณจากข้อมูล", ctx, "heuristic_fallback",
        )


def _user_familiarity_response(
    user_id: str,
    score_percent: int,
    reason: str,
    ctx: Dict[str, Any],
    source: str,
    heuristic_baseline: Optional[int] = None,
) -> Dict[str, Any]:
    """สร้าง response พร้อม breakdown สำหรับแสดงว่า AI รู้จัก user อย่างไร"""
    mem = (ctx.get("memory_context") or "").strip()
    profile = (ctx.get("user_profile_context") or "").strip()
    prefs = ctx.get("travel_preferences") or {}
    # สรุปสั้นๆ สำหรับแสดงใน Dashboard (ไม่ส่งข้อมูลเต็มเพื่อความปลอดภัย)
    memory_summary = ""
    if mem and mem != "(ไม่มีความจำ)":
        memory_summary = mem[:400] + ("…" if len(mem) > 400 else "")
    profile_summary = ""
    if profile and profile != "(ไม่มีโปรไฟล์)":
        profile_summary = profile[:400] + ("…" if len(profile) > 400 else "")
    prefs_parts = []
    if isinstance(prefs, dict):
        if prefs.get("budget_level"):
            prefs_parts.append(f"งบ: {prefs['budget_level']}")
        if prefs.get("travel_style"):
            prefs_parts.append(f"สไตล์: {prefs['travel_style']}")
        if prefs.get("preferred_destinations"):
            d = prefs["preferred_destinations"]
            prefs_parts.append("ปลายทาง: " + (", ".join(d[:5]) if isinstance(d, list) else str(d)))
        if prefs.get("prefer_direct_flight"):
            prefs_parts.append("ชอบบินตรง")
    preferences_summary = " | ".join(prefs_parts) if prefs_parts else ""
    hb = heuristic_baseline if heuristic_baseline is not None else score_percent
    methodology = _familiarity_methodology_payload(source, score_percent, hb)
    return {
        "user_id": user_id,
        "score_percent": score_percent,
        "reason": reason,
        "factors": ctx["factors"],
        "source": source,
        "heuristic_baseline_percent": hb,
        "methodology": methodology,
        "breakdown": {
            "memory_summary": memory_summary or None,
            "profile_summary": profile_summary or None,
            "preferences_summary": preferences_summary or None,
        },
    }


@router.get("/user-familiarity/batch")
async def get_user_familiarity_batch(
    user_ids: Optional[str] = None,
    _auth: bool = Depends(verify_admin_auth),
):
    """
    คืนค่าคะแนน "AI รู้จัก user" แบบ batch (ใช้ heuristic จาก factors ไม่เรียก AI เพื่อความเร็ว).
    ใช้แสดง % ในตาราง sessions. Query: user_ids=id1,id2,id3
    """
    ids = []
    if user_ids:
        ids = [x.strip() for x in user_ids.split(",") if x.strip()][:50]
    if not ids:
        return {"items": []}
    items = []
    for uid in ids:
        try:
            ctx = await _gather_user_context_for_familiarity(uid)
            score = _heuristic_familiarity_score(ctx["factors"])
            items.append({
                "user_id": uid,
                "score_percent": score,
                "factors": ctx["factors"],
                "source": "heuristic",
                "heuristic_baseline_percent": score,
                "score_note_th": (
                    "คะแนนนี้จากกฎคงที่เท่านั้น (ไม่เรียก LLM): มีความจำตามเงื่อนไข +35%, โปรไฟล์ +35%, "
                    "ความชอบการเดินทาง/เซสชัน +30% — ดูการ์ด \"AI รู้จัก User\" แล้วกดวัดด้วย AI สำหรับคะแนนจากโมเดล"
                ),
            })
        except Exception as e:
            logger.warning(f"Admin user-familiarity batch failed for {uid}: {e}")
            items.append({
                "user_id": uid,
                "score_percent": 0,
                "factors": {},
                "source": "error",
                "heuristic_baseline_percent": 0,
                "score_note_th": "โหลดข้อมูล user ไม่สำเร็จ — ไม่มีคะแนน",
            })
    return {"items": items}


# =============================================================================
# Notification Simulator Endpoints (Admin only)
# =============================================================================

@router.get("/sim/users")
async def sim_list_users(_auth: bool = Depends(verify_admin_auth)):
    """ดึงรายชื่อ users ทั้งหมด (สำหรับ simulator เลือก target user)"""
    try:
        from app.storage.connection_manager import ConnectionManager
        db = ConnectionManager.get_instance().get_mongo_database()
        cursor = db["users"].find({}, {"user_id": 1, "email": 1, "full_name": 1, "first_name": 1, "last_name": 1}).limit(100)
        users = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            name = doc.get("full_name") or f"{doc.get('first_name','')} {doc.get('last_name','')}".strip() or doc.get("email","")
            users.append({"user_id": doc["user_id"], "email": doc.get("email",""), "name": name})
        return {"ok": True, "users": users}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sim/bookings")
async def sim_list_bookings(user_id: Optional[str] = None, _auth: bool = Depends(verify_admin_auth)):
    """ดึงรายการ bookings (กรองด้วย user_id ถ้าระบุ)"""
    try:
        from app.storage.connection_manager import ConnectionManager
        db = ConnectionManager.get_instance().get_mongo_database()
        query = {"status": {"$in": ["paid", "confirmed", "pending_payment"]}}
        if user_id:
            query["user_id"] = user_id
        cursor = db["bookings"].find(query, {
            "booking_id": 1, "user_id": 1, "status": 1,
            "travel_slots": 1, "created_at": 1, "flight_status": 1
        }).sort("created_at", -1).limit(50)
        bookings = []
        async for doc in cursor:
            slots = doc.get("travel_slots") or {}
            origin = slots.get("origin_city") or slots.get("origin") or "?"
            dest = slots.get("destination_city") or slots.get("destination") or "?"
            bid = doc.get("booking_id") or str(doc["_id"])
            bookings.append({
                "booking_id": str(bid),
                "user_id": doc.get("user_id",""),
                "status": doc.get("status",""),
                "route": f"{origin} → {dest}",
                "flight_status": doc.get("flight_status",""),
                "created_at": doc.get("created_at",""),
            })
        return {"ok": True, "bookings": bookings}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SimScenarioRequest(BaseModel):
    scenario: str          # "flight_delayed" | "flight_cancelled" | "flight_rescheduled" | "trip_alert" | "checkin_flight" | "checkin_hotel" | "payment_success" | "payment_failed" | "booking_created" | "custom"
    user_id: str
    booking_id: Optional[str] = None
    delay_minutes: Optional[int] = 60
    custom_title: Optional[str] = None
    custom_message: Optional[str] = None


@router.post("/sim/trigger")
async def sim_trigger_scenario(body: SimScenarioRequest, _auth: bool = Depends(verify_admin_auth)):
    """
    จำลองสถานการณ์และส่ง notification ไปยัง user ที่เลือก
    Scenarios: flight_delayed, flight_cancelled, flight_rescheduled, trip_alert,
               checkin_flight, checkin_hotel, payment_success, payment_failed,
               booking_created, custom
    """
    from app.storage.connection_manager import ConnectionManager
    from app.services.notification_service import create_and_push_notification

    db = ConnectionManager.get_instance().get_mongo_database()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    SCENARIOS = {
        "flight_delayed": {
            "type": "flight_delayed",
            "title": "⏰ เที่ยวบินล่าช้า",
            "message": lambda b, d: f"เที่ยวบินในการจอง #{(b or '?')[:8]} ล่าช้าประมาณ {d} นาที กรุณาตรวจสอบที่เคาน์เตอร์สายการบิน",
        },
        "flight_cancelled": {
            "type": "flight_cancelled",
            "title": "🚫 เที่ยวบินถูกยกเลิก",
            "message": lambda b, d: f"เที่ยวบินในการจอง #{(b or '?')[:8]} ถูกยกเลิกโดยสายการบิน กรุณาติดต่อสายการบินหรือแก้ไขทริปของคุณ",
        },
        "flight_rescheduled": {
            "type": "flight_rescheduled",
            "title": "🔄 เที่ยวบินเปลี่ยนเวลา",
            "message": lambda b, d: f"เที่ยวบินในการจอง #{(b or '?')[:8]} มีการเปลี่ยนแปลงเวลา กรุณาตรวจสอบและแก้ไขทริปของคุณ",
        },
        "trip_alert": {
            "type": "trip_alert",
            "title": "⚠️ ทริปของคุณมีการเปลี่ยนแปลงมาก",
            "message": lambda b, d: f"ทริปในการจอง #{(b or '?')[:8]} มีการเปลี่ยนแปลงหลายรายการ กรุณาตรวจสอบและแก้ไขทริปเพื่อไม่ให้ทริปล่ม",
        },
        "checkin_flight": {
            "type": "checkin_reminder_flight",
            "title": "✈️ เตือนเช็คอินเครื่องบิน (24 ชั่วโมง)",
            "message": lambda b, d: f"เที่ยวบินในการจอง #{(b or '?')[:8]} ออกเดินทางใน 24 ชั่วโมง อย่าลืมเช็คอินออนไลน์!",
        },
        "checkin_hotel": {
            "type": "checkin_reminder_hotel",
            "title": "🏨 เตือนเช็คอินโรงแรมวันนี้",
            "message": lambda b, d: f"วันนี้คือวันเช็คอินโรงแรมในการจอง #{(b or '?')[:8]} เตรียมเอกสารและบัตรเครดิตให้พร้อม!",
        },
        "payment_success": {
            "type": "payment_success",
            "title": "✅ ชำระเงินสำเร็จ",
            "message": lambda b, d: f"ชำระเงินสำเร็จสำหรับการจอง #{(b or '?')[:8]} ขอบคุณที่ใช้บริการ",
        },
        "payment_failed": {
            "type": "payment_failed",
            "title": "❌ การชำระเงินล้มเหลว",
            "message": lambda b, d: f"การชำระเงินสำหรับการจอง #{(b or '?')[:8]} ไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
        },
        "booking_created": {
            "type": "booking_created",
            "title": "🎫 จองสำเร็จ",
            "message": lambda b, d: f"การจอง #{(b or '?')[:8]} ได้รับการสร้างแล้ว กรุณาชำระเงินเพื่อยืนยันการจอง",
        },
    }

    bid = body.booking_id or "DEMO00"
    delay = body.delay_minutes or 60

    if body.scenario == "custom":
        if not body.custom_title or not body.custom_message:
            raise HTTPException(status_code=400, detail="custom_title and custom_message required for custom scenario")
        notif_type = "trip_alert"
        title = body.custom_title
        message = body.custom_message
    elif body.scenario in SCENARIOS:
        cfg = SCENARIOS[body.scenario]
        notif_type = cfg["type"]
        title = cfg["title"]
        message = cfg["message"](bid, delay)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {body.scenario}. Valid: {list(SCENARIOS.keys()) + ['custom']}")

    # อัปเดต flight_status ใน booking ถ้าเป็น flight scenario
    if body.booking_id and body.scenario in ("flight_delayed", "flight_cancelled", "flight_rescheduled"):
        try:
            from bson import ObjectId
            bookings_col = db.get_collection("bookings")
            update_fields: Dict[str, Any] = {
                "flight_status": body.scenario.replace("flight_", ""),
                "updated_at": datetime.utcnow().isoformat(),
            }
            if body.scenario == "flight_delayed":
                update_fields["delay_minutes"] = delay
            # ลอง find ด้วย booking_id ก่อน
            booking = await bookings_col.find_one({"booking_id": body.booking_id})
            if not booking:
                try:
                    booking = await bookings_col.find_one({"_id": ObjectId(body.booking_id)})
                except Exception:
                    pass
            if booking:
                await bookings_col.update_one(
                    {"_id": booking["_id"]},
                    {"$set": update_fields}
                )
        except Exception as upd_err:
            logger.warning(f"[SimTrigger] Failed to update booking flight_status: {upd_err}")

    await create_and_push_notification(
        db=db,
        user_id=body.user_id,
        notif_type=notif_type,
        title=title,
        message=message,
        booking_id=body.booking_id or None,
        metadata={
            "simulated": True,
            "scenario": body.scenario,
            "delay_minutes": delay if body.scenario == "flight_delayed" else None,
        },
        check_preferences=False,  # force send เสมอสำหรับ simulation
    )

    logger.info(f"[Admin Sim] Triggered '{body.scenario}' for user={body.user_id} booking={body.booking_id}")
    return {"ok": True, "message": f"Scenario '{body.scenario}' triggered for user {body.user_id}"}


@router.post("/sim/broadcast")
async def sim_broadcast(body: dict, _auth: bool = Depends(verify_admin_auth)):
    """
    Broadcast notification ไปยัง users ทั้งหมด (หรือกลุ่มที่เลือก)
    body: { title, message, type, user_ids (optional list) }
    """
    from app.storage.connection_manager import ConnectionManager
    from app.services.notification_service import create_and_push_notification

    title = body.get("title", "").strip()
    message = body.get("message", "").strip()
    notif_type = body.get("type", "trip_alert")
    target_ids = body.get("user_ids") or []

    if not title or not message:
        raise HTTPException(status_code=400, detail="title and message are required")

    db = ConnectionManager.get_instance().get_mongo_database()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    # ถ้าไม่ระบุ user_ids ให้ดึงทั้งหมด
    if not target_ids:
        cursor = db["users"].find({}, {"user_id": 1})
        async for doc in cursor:
            uid = doc.get("user_id")
            if uid:
                target_ids.append(uid)

    sent = 0
    for uid in target_ids:
        try:
            await create_and_push_notification(
                db=db,
                user_id=uid,
                notif_type=notif_type,
                title=title,
                message=message,
                metadata={"simulated": True, "broadcast": True},
                check_preferences=False,
            )
            sent += 1
        except Exception as e:
            logger.warning(f"[SimBroadcast] Failed for user {uid}: {e}")

    return {"ok": True, "sent": sent, "message": f"Broadcast sent to {sent} users"}


@router.get("/stream")
async def admin_stream(request: Request, _auth: bool = Depends(verify_admin_auth)):
    """
    SSE stream for real-time system monitoring
    """
    async def event_generator():
        # Cache for expensive service checks
        last_service_check = 0
        last_sessions_refresh = 0
        last_logs_refresh = 0
        service_cache = {
            "gemini": {"status": "unknown", "message": "Initializing..."},
            "amadeus": {"status": "unknown", "message": "Initializing..."},
            "omise": {"status": "unknown", "message": "Initializing..."},
        }
        
        # Initialize Omise check immediately (don't wait for 10 seconds)
        try:
            if not settings.omise_secret_key or not settings.omise_public_key:
                service_cache["omise"] = {"status": "error", "message": "API Keys missing"}
                logger.debug(f"Omise SSE init: Keys missing - Secret: {bool(settings.omise_secret_key)}, Public: {bool(settings.omise_public_key)}")
            else:
                secret_valid = settings.omise_secret_key.startswith("skey_")
                public_valid = settings.omise_public_key.startswith("pkey_")
                is_test_mode = settings.omise_secret_key.startswith("skey_test_")
                
                logger.debug(f"Omise SSE init: Secret valid: {secret_valid}, Public valid: {public_valid}, Test mode: {is_test_mode}")
                
                if secret_valid and public_valid:
                    try:
                        import httpx
                        import asyncio
                        mode = "TEST" if is_test_mode else "LIVE"
                        logger.debug(f"Omise SSE init: Attempting API connection ({mode} mode)")
                        # Use asyncio.wait_for with longer timeout (10s) for better reliability
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await asyncio.wait_for(
                                client.get(
                                    "https://api.omise.co/account",
                                    auth=(settings.omise_secret_key, ""),
                                    timeout=10.0
                                ),
                                timeout=10.0
                            )
                            logger.debug(f"Omise SSE init: API response status {resp.status_code}")
                            if resp.status_code == 200:
                                account_data = resp.json()
                                email = account_data.get("email", "N/A")
                                service_cache["omise"] = {"status": "ok", "message": f"{mode} mode - Connected (Account: {email[:20]}...)"}
                                logger.info(f"Omise SSE init: Successfully connected ({mode} mode)")
                            else:
                                error_text = resp.text[:100] if resp.text else f"HTTP {resp.status_code}"
                                service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Auth failed (HTTP {resp.status_code}): {error_text}"}
                                logger.warning(f"Omise SSE init: Auth failed - HTTP {resp.status_code}")
                    except httpx.TimeoutException:
                        mode = "TEST" if is_test_mode else "LIVE"
                        service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Connection timeout (5s)"}
                        logger.warning(f"Omise SSE init: Connection timeout")
                    except httpx.RequestError as req_err:
                        mode = "TEST" if is_test_mode else "LIVE"
                        service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Network error: {str(req_err)[:50]}"}
                        logger.warning(f"Omise SSE init: Network error - {str(req_err)}")
                    except Exception as e:
                        mode = "TEST" if is_test_mode else "LIVE"
                        service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Error: {str(e)[:50]}"}
                        logger.error(f"Omise SSE init: Error - {str(e)}", exc_info=True)
                else:
                    service_cache["omise"] = {"status": "error", "message": f"Invalid key format (secret: {'valid' if secret_valid else 'invalid'}, public: {'valid' if public_valid else 'invalid'})"}
                    logger.warning(f"Omise SSE init: Invalid key format")
        except Exception as init_err:
            service_cache["omise"] = {"status": "error", "message": f"Initialization error: {str(init_err)[:50]}"}
            logger.error(f"Omise SSE init: Exception - {str(init_err)}", exc_info=True)
        
        while True:
            # If client disconnects, stop streaming
            if await request.is_disconnected():
                break

            try:
                # 1. Mongo Status (Always check, it's fast)
                from app.storage.connection_manager import ConnectionManager
                mongo_manager = ConnectionManager.get_instance()
                mongo_ok = await mongo_manager.mongo_ping()
                if mongo_ok:
                    try:
                        db = mongo_manager.get_mongo_database()
                        collections = await db.list_collection_names()
                        mongo_details = f"Connected ({len(collections)} collections)"
                    except Exception as db_err:
                        mongo_details = f"Connected (ping OK, DB error: {str(db_err)[:50]})"
                else:
                    mongo_details = "Disconnected (Ping failed)"

                # 2. Check other services periodically (every 60 seconds / 1 minute)
                # Note: Services status is expensive (API calls), so we check less frequently
                # Other data (system resources, sessions, logs) remain realtime
                current_time = time.time()
                if current_time - last_service_check > 60:  # Changed from 10 to 60 seconds
                    last_service_check = current_time
                    
                    # Gemini Check
                    if not settings.gemini_api_key:
                        service_cache["gemini"] = {"status": "error", "message": "API Key missing"}
                    else:
                        try:
                            # Use a lightweight call to verify key/connectivity
                            from google import genai
                            client = genai.Client(api_key=settings.gemini_api_key)
                            # Just list models to verify key
                            models = list(client.models.list(config={'page_size': 1}))
                            service_cache["gemini"] = {"status": "ok", "message": f"Model: {settings.gemini_model_name} (Active)"}
                        except Exception as e:
                            service_cache["gemini"] = {"status": "error", "message": f"API Error: {str(e)}"}
                    
                    # ✅ Amadeus Check (using search keys for testing)
                    if not settings.amadeus_search_api_key or not settings.amadeus_search_api_secret:
                        service_cache["amadeus"] = {"status": "error", "message": "Search API credentials missing"}
                    else:
                        try:
                            # Try a simple auth token request using search keys
                            import httpx
                            search_env = settings.amadeus_search_env.lower()
                            auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token" if search_env == "test" else "https://api.amadeus.com/v1/security/oauth2/token"
                            async with httpx.AsyncClient() as client:
                                resp = await client.post(
                                    auth_url,
                                    data={
                                        "grant_type": "client_credentials",
                                        "client_id": settings.amadeus_search_api_key,
                                        "client_secret": settings.amadeus_search_api_secret
                                    },
                                    timeout=5.0
                                )
                                if resp.status_code == 200:
                                    search_key_status = "✅"
                                    booking_key_status = "✅" if (settings.amadeus_booking_api_key and settings.amadeus_booking_api_secret) else "❌"
                                    service_cache["amadeus"] = {"status": "ok", "message": f"Search: {settings.amadeus_search_env} ({search_key_status}) | Booking: {settings.amadeus_booking_env} ({booking_key_status}) (Authenticated)"}
                                else:
                                    service_cache["amadeus"] = {"status": "error", "message": f"Auth failed: {resp.status_code}"}
                        except Exception as e:
                            service_cache["amadeus"] = {"status": "error", "message": f"Connection error: {str(e)}"}
                    
                    # ✅ Omise Check
                    try:
                        if not settings.omise_secret_key or not settings.omise_public_key:
                            service_cache["omise"] = {"status": "error", "message": "API Keys missing"}
                        else:
                            secret_valid = settings.omise_secret_key.startswith("skey_")
                            public_valid = settings.omise_public_key.startswith("pkey_")
                            is_test_mode = settings.omise_secret_key.startswith("skey_test_")
                            
                            if secret_valid and public_valid:
                                try:
                                    import httpx
                                    import asyncio
                                    async with httpx.AsyncClient(timeout=10.0) as client:
                                        resp = await asyncio.wait_for(
                                            client.get(
                                                "https://api.omise.co/account",
                                                auth=(settings.omise_secret_key, ""),
                                                timeout=10.0
                                            ),
                                            timeout=10.0
                                        )
                                        if resp.status_code == 200:
                                            account_data = resp.json()
                                            email = account_data.get("email", "N/A")
                                            mode = "TEST" if is_test_mode else "LIVE"
                                            service_cache["omise"] = {"status": "ok", "message": f"{mode} mode - Connected (Account: {email[:20]}...)"}
                                        else:
                                            mode = "TEST" if is_test_mode else "LIVE"
                                            error_text = resp.text[:100] if resp.text else f"HTTP {resp.status_code}"
                                            service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Auth failed (HTTP {resp.status_code}): {error_text}"}
                                except (httpx.TimeoutException, asyncio.TimeoutError):
                                    mode = "TEST" if is_test_mode else "LIVE"
                                    service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Connection timeout (10s)"}
                                except httpx.RequestError as req_err:
                                    mode = "TEST" if is_test_mode else "LIVE"
                                    service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Network error: {str(req_err)[:50]}"}
                                except Exception as e:
                                    mode = "TEST" if is_test_mode else "LIVE"
                                    service_cache["omise"] = {"status": "error", "message": f"{mode} mode - Error: {str(e)[:50]}"}
                            else:
                                service_cache["omise"] = {"status": "error", "message": f"Invalid key format (secret: {'valid' if secret_valid else 'invalid'}, public: {'valid' if public_valid else 'invalid'})"}
                    except Exception as omise_check_err:
                        logger.error(f"Omise status check error: {omise_check_err}", exc_info=True)
                        service_cache["omise"] = {"status": "error", "message": f"Check error: {str(omise_check_err)[:50]}"}

                # 3. System Resources
                uptime = time.time() - START_TIME
                process = psutil.Process(os.getpid())
                
                # Build status data
                # Services status (Gemini, Amadeus, Omise) is only updated when last_service_check > 60 seconds
                # This prevents expensive API calls on every update
                # MongoDB and Google Maps are fast checks, so they update in realtime
                # System resources, sessions, logs remain realtime
                status_data = {
                    "timestamp": datetime.now().isoformat(),
                    "services": {
                        "mongodb": {"status": "ok" if mongo_ok else "error", "message": mongo_details},
                        # Only send service status if it was recently checked (within 5 seconds of check) or it's time to check
                        "gemini": service_cache["gemini"],
                        "amadeus": service_cache["amadeus"],
                        "google_maps": {"status": "ok" if settings.google_maps_api_key else "error", "message": "Key present" if settings.google_maps_api_key else "Key missing"},
                        "omise": service_cache.get("omise", {"status": "unknown", "message": "Not checked yet"})
                    },
                    "agent_activities": agent_monitor.get_activities(),
                    "system": {
                        "uptime_seconds": int(uptime),
                        "memory_usage_mb": int(process.memory_info().rss / 1024 / 1024),
                        "cpu_usage_percent": psutil.cpu_percent(), # Global CPU
                        "process_cpu_percent": process.cpu_percent(), # Process CPU
                        "active_threads": process.num_threads()
                    },
                    "config": {
                        "amadeus_safety_guard": settings.amadeus_env == "test",
                        "amadeus_env": settings.amadeus_env,
                        "amadeus_search_env": settings.amadeus_search_env,
                        "amadeus_booking_env": settings.amadeus_booking_env,
                        "gemini_model": settings.gemini_model_name
                    }
                }
                
                # 4. Refresh sessions periodically (every 10 seconds)
                if current_time - last_sessions_refresh > 10:
                    last_sessions_refresh = current_time
                    try:
                        if mongo_ok:
                            db = mongo_manager.get_mongo_database()
                            cursor = db.sessions.find({}).sort("last_updated", -1).limit(50)
                            sessions = []
                            async for doc in cursor:
                                doc["_id"] = str(doc["_id"])
                                # Remove full trip_plan to reduce payload
                                if "trip_plan" in doc:
                                    trip_plan = doc["trip_plan"]
                                    doc["trip_plan_summary"] = {
                                        "has_flights": bool(trip_plan.get("travel", {}).get("flights", {}).get("outbound") or trip_plan.get("travel", {}).get("flights", {}).get("inbound")),
                                        "has_hotels": bool(trip_plan.get("accommodation", {}).get("segments")),
                                        "has_transport": bool(trip_plan.get("travel", {}).get("ground_transport"))
                                    }
                                    del doc["trip_plan"]
                                # ✅ Serialize datetime objects to ISO strings
                                doc = serialize_datetime(doc)
                                sessions.append(doc)
                            status_data["sessions"] = sessions
                    except Exception as sessions_err:
                        logger.warning(f"Failed to refresh sessions in SSE: {sessions_err}")
                
                # 5. Refresh logs periodically (every 5 seconds)
                if current_time - last_logs_refresh > 5:
                    last_logs_refresh = current_time
                    try:
                        if settings.log_file:
                            log_path = Path(settings.log_file)
                            if log_path.exists():
                                with open(log_path, "r", encoding="utf-8") as f:
                                    all_lines = f.readlines()
                                    status_data["logs"] = {
                                        "content": all_lines[-100:],  # Last 100 lines
                                        "total_lines": len(all_lines)
                                    }
                    except Exception as logs_err:
                        logger.warning(f"Failed to refresh logs in SSE: {logs_err}")

                # ✅ Serialize all datetime objects before JSON encoding
                serialized_data = serialize_datetime(status_data)
                yield f"data: {json.dumps(serialized_data, ensure_ascii=False, default=str)}\n\n"
                
                # Update every 2 seconds
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Admin stream error: {e}")
                # Don't yield error to keep the connection alive if possible, just log it
                await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

