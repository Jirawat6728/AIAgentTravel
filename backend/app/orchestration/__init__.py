"""
LangChain Orchestration Layer for AITravelAgent

ใช้ LangChain (LCEL) เป็น orchestration layer สำหรับ:
- ChatGoogleGenerativeAI (Gemini) แทนการเรียก Google API โดยตรง
- LCEL chains สำหรับ Controller, Responder, Intelligence brains
- Workflow state machine (workflow_graph) สำหรับ planning → searching → selecting → summary → booking → done

เปิดใช้: ENABLE_LANGCHAIN_ORCHESTRATION=true ใน .env
"""

from app.orchestration.langchain_llm import LangChainProductionLLM
from app.orchestration.agent_mode_graph import (
    get_agent_mode_graph,
    get_agent_mode_graph_sync,
    run_agent_mode_via_graph,
)
from app.orchestration.workflow_graph import (
    can_transition,
    get_next_step_for_action,
    VALID_TRANSITIONS,
    WORKFLOW_STEPS,
)
from app.orchestration.full_workflow_graph import (
    get_full_workflow_graph,
    run_full_workflow,
)

__all__ = [
    "LangChainProductionLLM",
    "get_agent_mode_graph",
    "get_agent_mode_graph_sync",
    "run_agent_mode_via_graph",
    "can_transition",
    "get_next_step_for_action",
    "VALID_TRANSITIONS",
    "WORKFLOW_STEPS",
    "get_full_workflow_graph",
    "run_full_workflow",
]
