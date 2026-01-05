"""
Proactive Flow System - Level 2 Feature
Implements proactive suggestions and anticipatory actions
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional


class ProactiveSuggestions:
    """
    Generates proactive suggestions based on context
    """
    
    @staticmethod
    def get_suggestions(ctx: Dict[str, Any], current_state: Dict[str, Any]) -> List[str]:
        """
        Generate proactive suggestions based on current context and state
        """
        suggestions = []
        
        # Check if user has incomplete slots
        travel_slots = ctx.get("last_travel_slots") or {}
        current_plan = ctx.get("current_plan")
        plan_choices = ctx.get("last_plan_choices") or []
        agent_state = current_state.get("agent_state") or {}
        agent_step = agent_state.get("step", "")
        
        # Suggest missing information
        if not travel_slots.get("destination"):
            suggestions.append("บอกสถานที่ที่อยากไป")
        elif not travel_slots.get("origin"):
            suggestions.append("บอกจุดเริ่มต้น")
        elif not travel_slots.get("departure_date"):
            suggestions.append("บอกวันเดินทาง")
        
        # Suggest actions based on state
        if agent_step == "3_choices_ready" and plan_choices:
            suggestions.extend([
                "เลือกช้อยส์ 1",
                "ขอไฟลต์เช้ากว่านี้",
                "ขอที่พักถูกลง",
            ])
        
        if current_plan and agent_step == "choice_selected":
            suggestions.extend([
                "ยืนยันจอง",
                "แก้ไขไฟลต์",
                "แก้ไขที่พัก",
            ])
        
        # Proactive suggestions for common next steps
        if travel_slots.get("destination") and not plan_choices:
            suggestions.append("ขยับวัน +1")
        
        return suggestions[:5]  # Limit to 5 suggestions
    
    @staticmethod
    def should_suggest_alternative(ctx: Dict[str, Any]) -> bool:
        """
        Determine if agent should proactively suggest alternatives
        """
        plan_choices = ctx.get("last_plan_choices") or []
        current_plan = ctx.get("current_plan")
        
        # Suggest if user has choices but hasn't selected
        if plan_choices and not current_plan:
            return True
        
        return False
    
    @staticmethod
    def get_proactive_message(ctx: Dict[str, Any], current_state: Dict[str, Any]) -> Optional[str]:
        """
        Generate proactive message to guide user
        Returns None if no proactive message needed
        """
        travel_slots = ctx.get("last_travel_slots") or {}
        plan_choices = ctx.get("last_plan_choices") or []
        current_plan = ctx.get("current_plan")
        
        # Proactive message for missing critical info
        if not travel_slots.get("destination"):
            return "💡 บอกสถานที่ที่อยากไปได้เลยค่ะ เช่น 'ไปเที่ยวเกาหลี' หรือ 'เที่ยวญี่ปุ่น'"
        
        if not travel_slots.get("departure_date") and travel_slots.get("destination"):
            return "💡 อยากไปวันที่เท่าไหร่คะ? บอกได้เลย เช่น 'ไปวันที่ 15 มกราคม'"
        
        # Proactive message for unselected choices
        if plan_choices and len(plan_choices) > 0 and not current_plan:
            return f"💡 มี {len(plan_choices)} ช้อยส์ให้เลือก กดการ์ดเพื่อดูรายละเอียดและเลือกได้เลยค่ะ"
        
        return None

