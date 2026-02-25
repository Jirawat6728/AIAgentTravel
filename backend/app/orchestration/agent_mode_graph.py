"""
LangGraph Agent Mode Orchestration

StateGraph สำหรับ Agent Mode: ควบคุม flow การ auto-select และ auto-book
เมื่อ ENABLE_LANGGRAPH_AGENT_MODE=true จะใช้ graph แทนการเรียก _auto_select_and_book โดยตรง
รองรับ Redis checkpointer สำหรับ resume ต่อ session (ต้องการ Redis Stack หรือ Redis 8+)
"""

from __future__ import annotations
from typing import Any, Dict, Optional, TypedDict

from app.core.logging import get_logger

logger = get_logger(__name__)

_has_langgraph = False
_has_redis_checkpoint = False
try:
    from langgraph.graph import END, START, StateGraph
    _has_langgraph = True
except ImportError:
    pass

try:
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver
    _has_redis_checkpoint = True
except ImportError:
    pass


class AgentModeState(TypedDict, total=False):
    """State สำหรับ Agent Mode graph"""
    session: Any
    action_log: Any
    agent: Any
    status_callback: Optional[Any]
    step: str
    error: Optional[str]
    booking_id: Optional[str]


async def _auto_complete_node(state: AgentModeState) -> Dict[str, Any]:
    """
    Node หลัก: เรียก _auto_select_and_book ซึ่งทำทั้ง
    1) เลือกตัวเลือกที่ดีที่สุดด้วย LLM
    2) จองทันทีเมื่อเลือกครบ
    """
    agent = state.get("agent")
    session = state.get("session")
    action_log = state.get("action_log")
    status_callback = state.get("status_callback")
    if not all([agent, session, action_log]):
        return {"step": "auto_complete", "error": "Missing agent/session/action_log"}
    try:
        await agent._auto_select_and_book(session, action_log, status_callback)
    except Exception as e:
        logger.error(f"Agent mode graph auto_complete: {e}", exc_info=True)
        return {"step": "auto_complete", "error": str(e)}
    return {"step": "auto_complete"}


def _build_agent_mode_graph(checkpointer: Any = None):
    """
    สร้าง LangGraph สำหรับ Agent Mode
    Flow: START -> auto_complete -> END
    """
    if not _has_langgraph:
        return None
    workflow = StateGraph(AgentModeState)
    workflow.add_node("auto_complete", _auto_complete_node)
    workflow.add_edge(START, "auto_complete")
    workflow.add_edge("auto_complete", END)
    return workflow.compile(checkpointer=checkpointer)


_agent_mode_graph = None
_redis_checkpointer = None
_checkpointer_unavailable = False


async def _get_redis_checkpointer():
    """
    สร้าง Redis checkpointer สำหรับ LangGraph (resume per session)
    คืน None ถ้าปิดใช้ หรือ Redis ไม่พร้อม (fallback เป็น graph แบบไม่มี checkpoint)
    """
    global _redis_checkpointer, _checkpointer_unavailable
    if _checkpointer_unavailable or _redis_checkpointer is not None:
        return _redis_checkpointer
    if not _has_redis_checkpoint:
        return None
    import os
    from app.core.config import settings
    if not getattr(settings, "enable_langgraph_checkpointer", True):
        return None
    redis_url = getattr(settings, "redis_url", None) or os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.debug("Redis checkpointer skipped: no REDIS_URL configured")
        _checkpointer_unavailable = True
        return None
    try:
        saver = AsyncRedisSaver.from_conn_string(redis_url)
        await saver.asetup()
        _redis_checkpointer = saver
        logger.info("Redis checkpointer initialized for Agent Mode (resume enabled)")
        return saver
    except Exception as e:
        logger.warning(
            "Redis checkpointer unavailable (use Redis Stack or Redis 8+ with RedisJSON/RediSearch): %s",
            e,
        )
        _checkpointer_unavailable = True
        return None


async def get_agent_mode_graph():
    """
    Get or create compiled agent mode graph (async เพื่อ setup Redis checkpointer)
    ถ้า ENABLE_LANGGRAPH_CHECKPOINTER=true และ Redis พร้อม จะ compile พร้อม checkpointer
    """
    global _agent_mode_graph
    if _agent_mode_graph is not None:
        return _agent_mode_graph
    if not _has_langgraph:
        return None
    checkpointer = await _get_redis_checkpointer()
    _agent_mode_graph = _build_agent_mode_graph(checkpointer=checkpointer)
    return _agent_mode_graph


def get_agent_mode_graph_sync():
    """Sync version - คืน graph ที่มีอยู่แล้ว หรือ build โดยไม่มี checkpointer"""
    global _agent_mode_graph
    if _agent_mode_graph is None and _has_langgraph:
        _agent_mode_graph = _build_agent_mode_graph(checkpointer=None)
    return _agent_mode_graph


async def run_agent_mode_via_graph(
    agent: Any,
    session: Any,
    action_log: Any,
    status_callback: Optional[Any] = None,
) -> bool:
    """
    รัน Agent Mode ผ่าน LangGraph
    ใช้ thread_id=session.session_id เพื่อให้ resume ได้ต่อ session
    คืน True ถ้าสำเร็จ, False ถ้า graph ไม่พร้อมหรือ error
    """
    graph = await get_agent_mode_graph()
    if graph is None:
        logger.debug("LangGraph not available, agent mode will use direct call")
        return False
    thread_id = getattr(session, "session_id", None) or "default"
    config: Dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    try:
        result = await graph.ainvoke(
            {
                "agent": agent,
                "session": session,
                "action_log": action_log,
                "status_callback": status_callback,
            },
            config=config,
        )
        if result is None:
            return False
        return result.get("error") is None
    except Exception as e:
        logger.warning(f"Agent mode graph invoke failed: {e}")
        return False
