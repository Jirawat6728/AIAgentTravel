"""
Planner Module - Level 3 Feature
Converts user message into goals, constraints, and missing information
Decides whether to proceed or ask one question
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


@dataclass
class PlannerOutput:
    """
    Output from Planner: structured representation of user intent
    """
    intent: str  # "search", "edit", "confirm", "collect_info"
    goals: List[str]  # What user wants to achieve
    constraints: Dict[str, Any]  # Hard constraints (dates, budget, etc.)
    missing_required: List[str]  # Required info that's missing
    missing_optional: List[str]  # Optional info that would help
    should_proceed: bool  # True = proceed to executor, False = ask question
    suggested_question: Optional[str] = None  # If should_proceed=False, what to ask
    suggested_chips: List[str] = None  # Suggested answer chips (3-5 options)
    
    def __post_init__(self):
        if self.suggested_chips is None:
            self.suggested_chips = []


class Planner:
    """
    Planner: Think before acting
    Converts user message into structured goals + constraints
    Uses LLM #1 to generate structured JSON output
    """
    
    @staticmethod
    async def plan(
        user_message: str,
        current_context: Dict[str, Any]
    ) -> PlannerOutput:
        """
        Plan the next action based on user message and context
        Uses LLM to generate structured JSON output
        
        Returns structured output with goals, constraints, and decision
        """
        try:
            # Try LLM-based planning first
            llm_result = await Planner._plan_with_llm(user_message, current_context)
            if llm_result:
                return llm_result
        except Exception as e:
            # Fallback to rule-based if LLM fails
            import logging
            logging.warning(f"LLM planning failed, using fallback: {e}")
        
        # Fallback to rule-based planning
        return Planner._plan_rule_based(user_message, current_context)
    
    @staticmethod
    async def _plan_with_llm(
        user_message: str,
        current_context: Dict[str, Any]
    ) -> Optional[PlannerOutput]:
        """
        Use LLM #1 to generate structured JSON planner output
        """
        from services.gemini_service import get_gemini_client, get_text_from_parts, GEMINI_MODEL_NAME
        from google.genai import types
        
        travel_slots = current_context.get("last_travel_slots") or {}
        current_plan = current_context.get("current_plan")
        agent_state = current_context.get("last_agent_state") or {}
        
        # Build prompt for LLM
        prompt = Planner._build_planner_prompt(user_message, travel_slots, current_plan, agent_state)
        
        # Call LLM (synchronous call, wrap in asyncio.to_thread)
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
        
        # Parse JSON from response
        planner_data = Planner._parse_llm_response(response)
        
        if planner_data:
            return PlannerOutput(
                intent=planner_data.get("intent", "search"),
                goals=planner_data.get("goals", []),
                constraints=planner_data.get("constraints", {}),
                missing_required=planner_data.get("missing_required", []),
                missing_optional=planner_data.get("missing_optional", []),
                should_proceed=planner_data.get("should_proceed", True),
                suggested_question=planner_data.get("suggested_question"),
                suggested_chips=planner_data.get("suggested_chips", [])
            )
        
        return None
    
    @staticmethod
    def _build_planner_prompt(
        user_message: str,
        travel_slots: Dict[str, Any],
        current_plan: Optional[Dict[str, Any]],
        agent_state: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM planner"""
        prompt = f"""คุณเป็น AI Planner ที่วิเคราะห์ข้อความผู้ใช้และสร้างแผนการทำงาน

ข้อความผู้ใช้: "{user_message}"

บริบทปัจจุบัน:
- Travel Slots: {json.dumps(travel_slots, ensure_ascii=False, indent=2)}
- มี Current Plan: {'ใช่' if current_plan else 'ไม่'}
- Agent State: {json.dumps(agent_state, ensure_ascii=False)}

ให้วิเคราะห์และคืนผลเป็น JSON ตามรูปแบบนี้:
{{
  "intent": "search|edit|confirm|collect_info",
  "goals": ["เป้าหมาย1", "เป้าหมาย2"],
  "constraints": {{"destination": "...", "departure_date": "...", ...}},
  "missing_required": ["destination", "departure_date", ...],
  "missing_optional": ["budget", "style", ...],
  "should_proceed": true/false,
  "suggested_question": "คำถามที่จะถาม (ถ้า should_proceed=false)",
  "suggested_chips": ["ตัวเลือก1", "ตัวเลือก2", ...]
}}

กฎ:
- ถ้าขาดข้อมูลจำเป็น (destination, departure_date, adults) → should_proceed=false
- ถ้ามีข้อมูลพอ → should_proceed=true
- suggested_chips ควรมี 3-5 ตัวเลือก

คืนผลเป็น JSON เท่านั้น:"""
        return prompt
    
    @staticmethod
    def _parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
        """Parse LLM JSON response"""
        try:
            # Try to extract JSON from response
            # Remove markdown code blocks if present
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
    def _plan_rule_based(user_message: str, current_context: Dict[str, Any]) -> PlannerOutput:
        """Fallback rule-based planning"""
        travel_slots = current_context.get("last_travel_slots") or {}
        current_plan = current_context.get("current_plan")
        agent_state = current_context.get("last_agent_state") or {}
        agent_step = agent_state.get("step", "")
        
        # Detect intent
        intent = Planner._detect_intent(user_message, current_plan, agent_step)
        
        # Extract goals and constraints
        goals = Planner._extract_goals(user_message, intent)
        constraints = Planner._extract_constraints(user_message, travel_slots, current_context)
        
        # Determine what's missing
        missing_required, missing_optional = Planner._check_missing_info(
            intent, travel_slots, constraints
        )
        
        # Decision: proceed or ask?
        should_proceed, question, chips = Planner._decide_next_action(
            intent, missing_required, missing_optional, current_context
        )
        
        return PlannerOutput(
            intent=intent,
            goals=goals,
            constraints=constraints,
            missing_required=missing_required,
            missing_optional=missing_optional,
            should_proceed=should_proceed,
            suggested_question=question,
            suggested_chips=chips or []
        )
    
    @staticmethod
    def _detect_intent(user_message: str, current_plan: Optional[Dict], agent_step: str) -> str:
        """Detect user intent from message and context"""
        msg_lower = user_message.lower()
        
        # Confirm/booking intent
        if any(kw in msg_lower for kw in ["ยืนยัน", "จอง", "confirm", "book"]):
            return "confirm"
        
        # Edit intent (if has current plan)
        if current_plan:
            if any(kw in msg_lower for kw in ["แก้", "เปลี่ยน", "edit", "change", "อัพเดท"]):
                return "edit"
            if any(kw in msg_lower for kw in ["ไฟลต์", "flight", "ที่พัก", "hotel", "รถ", "car"]):
                return "edit"  # Implicit edit
        
        # Search/search_again intent
        if any(kw in msg_lower for kw in ["หา", "search", "ใหม่", "new", "อีกครั้ง", "again"]):
            return "search"
        
        # Default: collect info or search
        if agent_step in ["asking_preferences", "collect"]:
            return "collect_info"
        
        return "search"
    
    @staticmethod
    def _extract_goals(user_message: str, intent: str) -> List[str]:
        """Extract goals from user message"""
        goals = []
        
        if intent == "search":
            goals.append("ค้นหาและสร้างแผนเที่ยว")
        elif intent == "edit":
            goals.append("แก้ไขแผนเที่ยวปัจจุบัน")
        elif intent == "confirm":
            goals.append("ยืนยันการจอง")
        else:
            goals.append("รวบรวมข้อมูลและวางแผน")
        
        return goals
    
    @staticmethod
    def _extract_constraints(
        user_message: str, 
        travel_slots: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract constraints from message and context"""
        constraints = {}
        
        # Merge existing slots as constraints
        if travel_slots:
            constraints.update({
                k: v for k, v in travel_slots.items() 
                if v is not None and v != ""
            })
        
        return constraints
    
    @staticmethod
    def _check_missing_info(
        intent: str,
        travel_slots: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> tuple[List[str], List[str]]:
        """Check what information is missing"""
        missing_required = []
        missing_optional = []
        
        # Required for search
        if intent in ["search", "collect_info"]:
            if not constraints.get("destination"):
                missing_required.append("destination")
            if not constraints.get("departure_date"):
                missing_required.append("departure_date")
            if not constraints.get("adults"):
                missing_required.append("adults")
        
        # Optional but helpful
        if not constraints.get("origin"):
            missing_optional.append("origin")
        if not constraints.get("nights") and intent != "flight_only":
            missing_optional.append("nights")
        if not constraints.get("style"):
            missing_optional.append("style")
        if not constraints.get("budget"):
            missing_optional.append("budget")
        
        return missing_required, missing_optional
    
    @staticmethod
    def _decide_next_action(
        intent: str,
        missing_required: List[str],
        missing_optional: List[str],
        context: Dict[str, Any]
    ) -> tuple[bool, Optional[str], Optional[List[str]]]:
        """
        Decide: proceed to executor or ask one question?
        Returns: (should_proceed, question, chips)
        """
        # If missing critical info, ask
        if len(missing_required) > 0:
            question, chips = Planner._generate_question(missing_required[0], context)
            return False, question, chips
        
        # If have required info, proceed (even if missing optional)
        if intent in ["search", "edit"]:
            return True, None, None
        
        # Default: proceed if we can
        return len(missing_required) == 0, None, None
    
    @staticmethod
    def _generate_question(missing_field: str, context: Dict[str, Any]) -> tuple[str, List[str]]:
        """Generate a natural question for missing field"""
        questions = {
            "destination": ("คุณอยากไปเที่ยวที่ไหนคะ? 🌍", ["ญี่ปุ่น", "เกาหลี", "ยุโรป", "อเมริกา", "ประเทศไทย"]),
            "departure_date": ("อยากไปวันที่เท่าไหร่คะ? 📅", ["พรุ่งนี้", "สัปดาห์หน้า", "เดือนหน้า", "ช่วงปีใหม่", "วันหยุดยาว"]),
            "adults": ("มีผู้ใหญ่กี่คนคะ? 👥", ["1", "2", "3-4", "5+"]),
            "origin": ("เดินทางจากไหนคะ? ✈️", ["กรุงเทพ", "เชียงใหม่", "ภูเก็ต", "อื่นๆ"]),
        }
        
        question, chips = questions.get(
            missing_field, 
            (f"กรุณาระบุ {missing_field} ค่ะ", [])
        )
        
        return question, chips[:5]  # Limit to 5 chips

