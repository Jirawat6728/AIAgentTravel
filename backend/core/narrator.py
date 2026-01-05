"""
Narrator Module - Level 3 Feature
Creates natural, structured responses for users
Separates "thinking" from "speaking"
Uses LLM #2 to generate natural language responses
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import json


@dataclass
class NarratorOutput:
    """
    Output from Narrator: natural language response
    """
    message: str  # Natural language response
    reasoning: Optional[str] = None  # Why this choice (for reasoning light)
    next_actions: List[str] = None  # Clear next action suggestions
    memory_suggestions: List[Dict[str, Any]] = None  # What should be remembered
    
    def __post_init__(self):
        if self.next_actions is None:
            self.next_actions = []
        if self.memory_suggestions is None:
            self.memory_suggestions = []


class Narrator:
    """
    Narrator: Tell the story naturally
    Converts structured data into natural responses
    Uses LLM #2 to generate natural language
    """
    
    @staticmethod
    async def narrate(
        planner_output: Any,  # PlannerOutput
        executor_output: Any,  # ExecutorOutput
        context: Dict[str, Any]
    ) -> NarratorOutput:
        """
        Create natural response from planner and executor outputs
        Uses LLM #2 to generate natural language
        """
        try:
            # Try LLM-based narration first
            llm_result = await Narrator._narrate_with_llm(planner_output, executor_output, context)
            if llm_result:
                return llm_result
        except Exception as e:
            # Fallback to rule-based if LLM fails
            import logging
            logging.warning(f"LLM narration failed, using fallback: {e}")
        
        # Fallback to rule-based narration
        return Narrator._narrate_rule_based(planner_output, executor_output, context)
    
    @staticmethod
    async def _narrate_with_llm(
        planner_output: Any,
        executor_output: Any,
        context: Dict[str, Any]
    ) -> Optional[NarratorOutput]:
        """
        Use LLM #2 to generate natural language response
        """
        from services.gemini_service import get_gemini_client, get_text_from_parts, GEMINI_MODEL_NAME
        from google.genai import types
        
        # Build prompt for LLM narrator
        prompt = Narrator._build_narrator_prompt(planner_output, executor_output, context)
        
        # Call LLM (synchronous call, wrap in asyncio.to_thread if needed)
        try:
            import asyncio
            resp = await asyncio.to_thread(
                lambda: get_gemini_client().models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=[{"role": "user", "parts": [{"text": prompt}]}],
                )
            )
            response = get_text_from_parts(resp)
        except Exception:
            return None
        
        # Parse response
        narrator_data = Narrator._parse_llm_response(response)
        
        if narrator_data:
            return NarratorOutput(
                message=narrator_data.get("message", ""),
                reasoning=narrator_data.get("reasoning"),
                next_actions=narrator_data.get("next_actions", []),
                memory_suggestions=narrator_data.get("memory_suggestions", [])
            )
        
        return None
    
    @staticmethod
    def _build_narrator_prompt(
        planner_output: Any,
        executor_output: Any,
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM narrator"""
        prompt = f"""คุณเป็น AI Narrator ที่สร้างข้อความตอบกลับผู้ใช้ให้เป็นธรรมชาติ
        
Planner Output:
- Intent: {planner_output.intent}
- Goals: {planner_output.goals}
- Constraints: {json.dumps(planner_output.constraints, ensure_ascii=False)}

Executor Output:
- Success: {executor_output.success}
- Plan Choices Count: {len(executor_output.plan_choices)}
- Errors: {executor_output.errors}

ให้สร้างข้อความตอบกลับที่เป็นธรรมชาติ พูดไทยแบบไม่ทางการเกิน พร้อมข้อความแนะนำ

คืนผลเป็น JSON:
{{
  "message": "ข้อความตอบกลับที่เป็นธรรมชาติ",
  "reasoning": "อธิบายเหตุผลการเลือก (สั้น ๆ)",
  "next_actions": ["ตัวเลือก1", "ตัวเลือก2", ...],
  "memory_suggestions": [{{"type": "preference", "key": "...", "value": "..."}}]
}}

คืนผลเป็น JSON เท่านั้น:"""
        return prompt
    
    @staticmethod
    def _parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response"""
        try:
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            return json.loads(response)
        except Exception:
            return None
    
    @staticmethod
    def _narrate_rule_based(
        planner_output: Any,
        executor_output: Any,
        context: Dict[str, Any]
    ) -> NarratorOutput:
        """Fallback rule-based narration"""
        # If we need to ask a question
        if not planner_output.should_proceed and planner_output.suggested_question:
            return Narrator._create_question_response(planner_output, context)
        
        # If we have results to present
        if executor_output.success and executor_output.plan_choices:
            return Narrator._create_results_response(planner_output, executor_output, context)
        
        # If we have errors
        if not executor_output.success:
            return Narrator._create_error_response(executor_output, context)
        
        # Default response
        return NarratorOutput(
            message="กำลังดำเนินการให้คุณค่ะ...",
            next_actions=["รอสักครู่"],
            memory_suggestions=[]
        )
    
    @staticmethod
    def _create_question_response(planner_output: Any, context: Dict[str, Any]) -> NarratorOutput:
        """Create response when we need to ask a question"""
        message = planner_output.suggested_question or "กรุณาระบุข้อมูลเพิ่มเติมค่ะ"
        
        # Add chips as suggestions
        next_actions = planner_output.suggested_chips or []
        
        return NarratorOutput(
            message=message,
            reasoning=None,
            next_actions=next_actions,
            memory_suggestions=[]
        )
    
    @staticmethod
    def _create_results_response(
        planner_output: Any,
        executor_output: Any,
        context: Dict[str, Any]
    ) -> NarratorOutput:
        """Create response when presenting results"""
        choices_count = len(executor_output.plan_choices)
        search_results = executor_output.search_results
        
        flights_n = len((search_results.get("flights") or {}).get("data") or [])
        hotels_n = len((search_results.get("hotels") or {}).get("data") or [])
        
        from core.config import AMADEUS_SEARCH_ENV
        
        message = (
            f"ฉันหาได้แล้วค่ะ (Amadeus {('Production' if AMADEUS_SEARCH_ENV=='production' else 'Sandbox')})\n"
            f"- ไฟลต์: {flights_n} รายการ\n"
            f"- โรงแรม: {hotels_n} รายการ\n\n"
            f"นี่คือ {choices_count} ช้อยส์แบบละเอียด (เรียงตามราคาถูกก่อน) "
            f"(กดการ์ดหรือพิมพ์ \"เลือกช้อยส์ X\" เพื่อเลือก/แก้ทีละส่วนได้เลยค่ะ)"
        )
        
        # Generate reasoning (why this choice)
        reasoning = Narrator._generate_reasoning(executor_output.plan_choices)
        
        # Generate next actions
        next_actions = ["เลือกช้อยส์ 1", "ขอไฟลต์เช้ากว่านี้", "ขอที่พักถูกลง", "ขยับวัน +1"]
        
        # Memory suggestions (what preferences to remember)
        memory_suggestions = Narrator._suggest_memory_updates(planner_output, context)
        
        return NarratorOutput(
            message=message,
            reasoning=reasoning,
            next_actions=next_actions,
            memory_suggestions=memory_suggestions
        )
    
    @staticmethod
    def _create_error_response(executor_output: Any, context: Dict[str, Any]) -> NarratorOutput:
        """Create response for errors"""
        error_msg = "เกิดข้อผิดพลาดในการค้นหาค่ะ"
        if executor_output.errors:
            error_msg += f"\n{executor_output.errors[0]}"
        
        return NarratorOutput(
            message=error_msg,
            reasoning=None,
            next_actions=["ลองใหม่", "ขยับวัน +1", "เปลี่ยนเมือง"],
            memory_suggestions=[]
        )
    
    @staticmethod
    def _generate_reasoning(plan_choices: List[Dict[str, Any]]) -> Optional[str]:
        """Generate reasoning explanation"""
        if not plan_choices:
            return None
        
        # Simple reasoning based on first choice
        first_choice = plan_choices[0]
        reasons = []
        
        if first_choice.get("recommended"):
            reasons.append("แนะนำ")
        if first_choice.get("is_non_stop"):
            reasons.append("บินตรง")
        if first_choice.get("total_price"):
            price = first_choice.get("total_price")
            if price and price < 150000:  # Example threshold
                reasons.append("ราคาดี")
        
        if reasons:
            return f"เลือกตัวนี้เพราะ: {' / '.join(reasons)}"
        
        return None
    
    @staticmethod
    def _suggest_memory_updates(planner_output: Any, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Suggest what should be remembered"""
        suggestions = []
        
        constraints = planner_output.constraints
        
        # Suggest remembering preferences
        if constraints.get("style"):
            suggestions.append({
                "type": "preference",
                "key": "travel_style",
                "value": constraints.get("style"),
                "description": "สไตล์การเที่ยว"
            })
        
        if constraints.get("budget"):
            suggestions.append({
                "type": "preference",
                "key": "budget_range",
                "value": constraints.get("budget"),
                "description": "ช่วงงบประมาณ"
            })
        
        return suggestions

