"""
LangGraph Full Workflow: จัดการ flow ทั้งหมดแทน agent.run_controller loop

เมื่อ ENABLE_LANGGRAPH_FULL_WORKFLOW=true จะใช้ graph นี้แทนการรัน Controller Loop ใน agent.py
Flow: START -> controller -> execute -> (controller | responder) -> END
"""

from __future__ import annotations
import hashlib
import json
from typing import Any, Dict, List, Optional, TypedDict

from app.core.logging import get_logger
from app.core.config import settings
from app.core.constants import FALLBACK_RESPONSE_EMPTY
from app.models import ControllerAction, ActionLog, ActionType

logger = get_logger(__name__)

_has_langgraph = False
try:
    from langgraph.graph import END, START, StateGraph
    _has_langgraph = True
except ImportError:
    pass


class FullWorkflowState(TypedDict, total=False):
    """State สำหรับ full workflow graph"""
    agent: Any
    session: Any
    action_log: Any
    user_input: str
    mode: str
    status_callback: Optional[Any]
    memory_context: str
    user_profile_context: str
    conversation_context: str
    current_action: Optional[Any]
    has_ask_user: bool
    iteration: int
    max_iterations: int
    response_text: str
    workflow_state: Optional[Dict[str, Any]]
    ml_intent_hint: Optional[Dict[str, Any]]
    ml_validation_result: Optional[Dict[str, Any]]
    action_history: List[tuple]
    loop_detection_threshold: int


async def _controller_node(state: FullWorkflowState) -> Dict[str, Any]:
    """เรียก Controller LLM ได้ action ถัดไป"""
    agent = state.get("agent")
    session = state.get("session")
    action_log = state.get("action_log")
    user_input = state.get("user_input", "")
    mode = state.get("mode", "normal")
    memory_context = state.get("memory_context", "")
    user_profile_context = state.get("user_profile_context", "")
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)
    action_history: List[tuple] = list(state.get("action_history") or [])
    loop_detection_threshold = state.get("loop_detection_threshold", 2)

    out: Dict[str, Any] = {"iteration": iteration + 1}

    if iteration >= max_iterations:
        logger.info(f"[LangGraph] Max iterations {max_iterations} reached, going to responder")
        out["has_ask_user"] = True
        out["current_action"] = None
        return out

    if not all([agent, session, action_log]):
        out["has_ask_user"] = True
        out["current_action"] = None
        return out

    # Workflow state & ML hints (เหมือนใน run_controller)
    workflow_state = None
    ml_intent_hint = None
    ml_validation_result = None
    try:
        from app.services.workflow_state import get_workflow_state_service
        wf = get_workflow_state_service()
        workflow_state = await wf.get_workflow_state(session.session_id)
    except Exception as e:
        logger.debug(f"Workflow state: {e}")
    try:
        from app.services.ml_keyword_service import get_ml_keyword_service
        ml_svc = get_ml_keyword_service()
        ml_intent_hint = ml_svc.decode_keywords(user_input)
        extracted = agent._extract_trip_data_for_ml_validation(session.trip_plan)
        if extracted:
            ml_validation_result = ml_svc.validate_extracted_data(extracted)
    except Exception as e:
        logger.debug(f"ML keyword/validation: {e}")

    out["workflow_state"] = workflow_state
    out["ml_intent_hint"] = ml_intent_hint
    out["ml_validation_result"] = ml_validation_result

    from app.engine.agent import _strip_options_pool_for_controller
    stripped_state = _strip_options_pool_for_controller(session.trip_plan.model_dump())
    state_json = json.dumps(stripped_state, ensure_ascii=False, indent=2)

    conversation_context = state.get("conversation_context", "")

    action = await agent._call_controller_llm(
        state_json,
        user_input,
        action_log,
        memory_context=memory_context,
        user_profile_context=user_profile_context,
        mode=mode,
        session_id=session.session_id,
        user_id=session.user_id,
        workflow_validation=workflow_state,
        ml_intent_hint=ml_intent_hint,
        ml_validation_result=ml_validation_result,
        conversation_context=conversation_context,
    )

    if not action:
        action = ControllerAction(
            thought="I failed to decide an action. I will ask the user for clarification.",
            action=ActionType.ASK_USER,
            payload={},
        )

    # Loop detection
    action_type_str = action.action.value if hasattr(action.action, "value") else str(action.action)
    payload_hash = hashlib.md5(json.dumps(action.payload or {}, sort_keys=True).encode()).hexdigest()[:8]
    action_signature = (action_type_str, payload_hash)
    action_history.append(action_signature)
    count = sum(1 for s in action_history if s == action_signature)
    if count >= loop_detection_threshold:
        logger.warning(f"[LangGraph] Loop detected: {action_type_str} repeated {count} times")
        out["has_ask_user"] = True
        out["current_action"] = None
        out["action_history"] = action_history
        return out

    # Log action
    log_payload = (action.payload or {}).copy()
    if getattr(action, "batch_actions", None):
        log_payload["batch_actions"] = action.batch_actions
    action_log.add_action(action.action.value, log_payload, f"Iteration {iteration + 1}")

    out["current_action"] = action
    out["action_history"] = action_history
    return out


async def _execute_node(state: FullWorkflowState) -> Dict[str, Any]:
    """Execute current_action ผ่าน agent.execute_controller_action"""
    agent = state.get("agent")
    session = state.get("session")
    action_log = state.get("action_log")
    user_input = state.get("user_input", "")
    mode = state.get("mode", "normal")
    status_callback = state.get("status_callback")
    current_action = state.get("current_action")
    ml_validation_result = state.get("ml_validation_result")

    has_ask_user = True
    if agent and session and action_log and current_action:
        try:
            has_ask_user = await agent.execute_controller_action(
                session,
                action_log,
                user_input,
                mode,
                status_callback,
                action=current_action,
                ml_validation_result=ml_validation_result,
            )
        except Exception as e:
            logger.error(f"[LangGraph] execute_controller_action: {e}", exc_info=True)
            action_log.add_action("ERROR", {}, str(e), success=False)

    return {"has_ask_user": has_ask_user}


async def _responder_node(state: FullWorkflowState) -> Dict[str, Any]:
    """สร้างข้อความตอบกลับผ่าน agent.generate_response"""
    agent = state.get("agent")
    session = state.get("session")
    action_log = state.get("action_log")
    user_input = state.get("user_input", "")
    mode = state.get("mode", "normal")
    memory_context = state.get("memory_context", "")
    user_profile_context = state.get("user_profile_context", "")

    response_text = ""
    if agent and session and action_log:
        try:
            response_text = await agent.generate_response(
                session,
                action_log,
                memory_context,
                user_profile_context,
                mode=mode,
                user_input=user_input,
            )
        except Exception as e:
            logger.error(f"[LangGraph] generate_response: {e}", exc_info=True)
            response_text = "ขออภัยค่ะ เกิดข้อผิดพลาดในการสร้างคำตอบ กรุณาลองใหม่อีกครั้งนะคะ"

    if not response_text or not response_text.strip():
        logger.warning(
            "Responder returned empty in LangGraph, using fallback",
            extra={"fallback_reason": "langgraph_responder_empty"},
        )
        response_text = FALLBACK_RESPONSE_EMPTY

    return {"response_text": response_text}


def _route_after_execute(state: FullWorkflowState) -> str:
    """หลัง execute: ไป controller ต่อหรือ responder"""
    has_ask_user = state.get("has_ask_user", True)
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)
    if has_ask_user or iteration >= max_iterations:
        return "responder"
    return "controller"


def build_full_workflow_graph():
    """สร้างและ compile LangGraph สำหรับ full workflow"""
    if not _has_langgraph:
        return None
    workflow = StateGraph(FullWorkflowState)
    workflow.add_node("controller", _controller_node)
    workflow.add_node("execute", _execute_node)
    workflow.add_node("responder", _responder_node)
    workflow.add_edge(START, "controller")
    workflow.add_edge("controller", "execute")
    workflow.add_conditional_edges("execute", _route_after_execute, {"controller": "controller", "responder": "responder"})
    workflow.add_edge("responder", END)
    return workflow.compile()


_full_workflow_graph = None


def get_full_workflow_graph():
    global _full_workflow_graph
    if _full_workflow_graph is None and _has_langgraph:
        _full_workflow_graph = build_full_workflow_graph()
    return _full_workflow_graph


async def run_full_workflow(
    agent: Any,
    session: Any,
    action_log: ActionLog,
    user_input: str,
    mode: str = "normal",
    status_callback: Optional[Any] = None,
    memory_context: str = "",
    user_profile_context: str = "",
    conversation_context: str = "",
) -> str:
    """
    รัน full workflow ผ่าน LangGraph (controller -> execute -> ... -> responder).
    คืน response_text สำหรับส่งกลับผู้ใช้
    """
    graph = get_full_workflow_graph()
    if graph is None:
        logger.warning("LangGraph not available, full workflow cannot run")
        return ""

    max_iterations = min(getattr(settings, "controller_max_iterations", 3), 2)
    initial_state: FullWorkflowState = {
        "agent": agent,
        "session": session,
        "action_log": action_log,
        "user_input": user_input,
        "mode": mode,
        "status_callback": status_callback,
        "memory_context": memory_context,
        "user_profile_context": user_profile_context,
        "conversation_context": conversation_context,
        "current_action": None,
        "has_ask_user": False,
        "iteration": 0,
        "max_iterations": max_iterations,
        "response_text": "",
        "workflow_state": None,
        "ml_intent_hint": None,
        "ml_validation_result": None,
        "action_history": [],
        "loop_detection_threshold": 2,
    }

    try:
        result = await graph.ainvoke(initial_state)
        response_text = (result or {}).get("response_text", "")
        if not response_text or not response_text.strip():
            logger.warning("Full workflow returned empty response", extra={"fallback_reason": "graph_empty"})
            return FALLBACK_RESPONSE_EMPTY
        return response_text
    except Exception as e:
        logger.error(f"Full workflow graph invoke failed: {e}", exc_info=True)
        return "ระบบเกิดขัดข้องเล็กน้อย กรุณาลองใหม่อีกครั้งนะคะ"
