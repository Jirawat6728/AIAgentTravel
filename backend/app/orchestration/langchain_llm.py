"""
LangChain-based Production LLM for AITravelAgent Orchestration

ใช้ ChatGoogleGenerativeAI + LCEL (LangChain Expression Language) แทนการเรียก Gemini โดยตรง
Implement interface เดียวกับ ProductionLLMService เพื่อให้ TravelAgent ใช้งานได้ทันที
"""

from __future__ import annotations
import json
from typing import Any, Dict, Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.core.exceptions import LLMException
from app.services.llm import BrainType, ModelType

logger = get_logger(__name__)

# Optional LangChain imports - fail gracefully if not installed
_langchain_available = False
try:
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, SystemMessage
    _langchain_available = True
except ImportError as e:
    logger.warning(f"LangChain not available: {e}. Install: pip install langchain langchain-google-genai langchain-core")


def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """Extract JSON object from LLM text output."""
    if not text or not text.strip():
        return None
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx == -1 or end_idx == -1:
        return None
    json_str = text[start_idx : end_idx + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        try:
            return json.loads(json_str.replace("\n", " "))
        except Exception:
            pass
    return None


class LangChainProductionLLM:
    """
    LangChain-based Production LLM — drop-in replacement for ProductionLLMService.
    
    Uses LCEL chains:
    - controller_chain: prompt | llm | parse_json
    - responder_chain: prompt | llm | StrOutputParser
    - intelligence_chain: prompt | llm | parse_json
    """

    BRAIN_TEMPERATURE = {
        BrainType.CONTROLLER: 0.3,
        BrainType.RESPONDER: 0.7,
        BrainType.INTELLIGENCE: 0.4,
    }

    def __init__(self, api_key: Optional[str] = None):
        if not _langchain_available:
            raise LLMException(
                "LangChain orchestration requires: pip install langchain langchain-google-genai langchain-core"
            )
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key or not self.api_key.strip():
            raise LLMException("GEMINI_API_KEY is required for LangChain orchestration")

        # ✅ อ่านค่า model จาก settings ตอน __init__ (ไม่ใช่ class-level) เพื่อให้ได้ค่าจาก .env จริง
        flash_model = getattr(settings, "gemini_flash_model", None) or "gemini-2.5-flash"
        pro_model = getattr(settings, "gemini_pro_model", None) or "gemini-2.5-pro"

        # ✅ langchain-google-genai v4+ ไม่รองรับ convert_system_message_to_human แล้ว
        # ✅ ตั้ง request_timeout ให้สูงพอ (Pro model ใช้เวลานาน)
        _llm_timeout = int(getattr(settings, "llm_timeout", None) or 120)
        _llm_kwargs = dict(
            google_api_key=self.api_key,
            request_timeout=_llm_timeout,
            max_retries=2,
        )

        self._llm_controller = ChatGoogleGenerativeAI(
            model=pro_model,
            temperature=self.BRAIN_TEMPERATURE[BrainType.CONTROLLER],
            **_llm_kwargs,
        )
        self._llm_responder = ChatGoogleGenerativeAI(
            model=flash_model,
            temperature=self.BRAIN_TEMPERATURE[BrainType.RESPONDER],
            **_llm_kwargs,
        )
        self._llm_intelligence = ChatGoogleGenerativeAI(
            model=pro_model,
            temperature=self.BRAIN_TEMPERATURE[BrainType.INTELLIGENCE],
            **_llm_kwargs,
        )
        # LCEL chains
        self._controller_chain = (
            ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}"),
                ("human", "{prompt}"),
            ])
            | self._llm_controller
            | StrOutputParser()
        )
        self._responder_chain = (
            ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}"),
                ("human", "{prompt}"),
            ])
            | self._llm_responder
            | StrOutputParser()
        )
        self._intelligence_chain = (
            ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}"),
                ("human", "{prompt}"),
            ])
            | self._llm_intelligence
            | StrOutputParser()
        )
        logger.info(
            f"LangChainProductionLLM initialized (Controller/Intelligence={pro_model}, "
            f"Responder={flash_model})"
        )

    async def controller_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate controller decision (JSON) via LCEL chain."""
        try:
            sys = system_prompt or "You are the Brain of a Travel Agent. Output JSON only."
            result = await self._controller_chain.ainvoke({
                "system_prompt": sys,
                "prompt": prompt,
            })
            parsed = _extract_json_from_text(result)
            if not parsed or not isinstance(parsed, dict):
                logger.warning("LangChain Controller returned invalid JSON, using fallback")
                return {"error": "invalid_response", "action": "ASK_USER", "payload": {"message": "กรุณาลองใหม่อีกครั้ง"}}
            return parsed
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"LangChain controller_generate error: {e}", exc_info=True)
            raise LLMException(f"LangChain controller failed: {e}") from e

    async def responder_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None,
    ) -> str:
        """Generate responder message (text) via LCEL chain."""
        try:
            sys = system_prompt or "You are the voice of a friendly Travel Agent. Respond in Thai."
            result = await self._responder_chain.ainvoke({
                "system_prompt": sys,
                "prompt": prompt,
            })
            if not result or not str(result).strip():
                raise LLMException("LangChain responder returned empty response")
            return str(result).strip()
        except LLMException:
            raise
        except Exception as e:
            logger.error(f"LangChain responder_generate error: {e}", exc_info=True)
            raise LLMException(f"LangChain responder failed: {e}") from e

    async def intelligence_generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model_type: Optional[ModelType] = None,
        complexity: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate intelligence analysis (JSON) via LCEL chain."""
        try:
            sys = system_prompt or "You are the Intelligence brain. Output JSON only."
            result = await self._intelligence_chain.ainvoke({
                "system_prompt": sys,
                "prompt": prompt,
            })
            parsed = _extract_json_from_text(result)
            return parsed if isinstance(parsed, dict) else {}
        except Exception as e:
            logger.error(f"LangChain intelligence_generate error: {e}", exc_info=True)
            return {}
