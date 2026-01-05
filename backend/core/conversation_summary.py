"""
Conversation Summary Module - Level 3 Feature
Auto-summarizes conversations every N messages
Reduces tokens and maintains context for long conversations
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import json


class ConversationSummarizer:
    """
    Conversation Summary: Auto-summarize conversations
    Stores summary every N messages to reduce token usage
    """
    
    SUMMARY_INTERVAL = 10  # Summarize every 10 messages
    
    @staticmethod
    async def should_summarize(
        message_count: int,
        last_summary_at: Optional[int] = None
    ) -> bool:
        """
        Determine if conversation should be summarized
        """
        if message_count < ConversationSummarizer.SUMMARY_INTERVAL:
            return False
        
        # Check if we've summarized recently
        if last_summary_at:
            messages_since_summary = message_count - last_summary_at
            return messages_since_summary >= ConversationSummarizer.SUMMARY_INTERVAL
        
        return True
    
    @staticmethod
    async def create_summary(
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create conversation summary using LLM
        Returns structured summary of what was agreed upon
        """
        # Import here to avoid circular dependency
        from services.gemini_service import get_gemini_client, get_text_from_parts, GEMINI_MODEL_NAME
        from google.genai import types
        
        # Extract recent messages for summarization
        recent_messages = messages[-ConversationSummarizer.SUMMARY_INTERVAL:]
        
        # Build summary prompt
        prompt = ConversationSummarizer._build_summary_prompt(recent_messages, context)
        
        try:
            # Call LLM to generate summary
            resp = get_gemini_client().models.generate_content(
                model=GEMINI_MODEL_NAME,
                contents=[{"role": "user", "parts": [{"text": prompt}]}],
            )
            summary_text = get_text_from_parts(resp)
            
            # Parse summary into structured format
            summary = ConversationSummarizer._parse_summary(summary_text, context)
            
            return {
                "summary_text": summary_text,
                "agreed_upon": summary.get("agreed_upon", {}),
                "preferences": summary.get("preferences", {}),
                "next_steps": summary.get("next_steps", []),
                "created_at": datetime.utcnow().isoformat(),
                "message_count": len(messages)
            }
        except Exception as e:
            # Fallback: create simple summary from context
            return ConversationSummarizer._create_fallback_summary(context)
    
    @staticmethod
    def _build_summary_prompt(
        messages: List[Dict[str, Any]],
        context: Dict[str, Any]
    ) -> str:
        """Build prompt for LLM to generate summary"""
        # Extract travel slots as context
        travel_slots = context.get("last_travel_slots") or {}
        
        prompt = f"""สรุปการสนทนาล่าสุด (สุดย่อ 50-100 คำ):

ข้อมูลที่ตกลงกันแล้ว:
- ต้นทาง: {travel_slots.get('origin', 'ยังไม่ระบุ')}
- ปลายทาง: {travel_slots.get('destination', 'ยังไม่ระบุ')}
- วันเดินทาง: {travel_slots.get('departure_date', 'ยังไม่ระบุ')}
- จำนวนคืน: {travel_slots.get('nights', 'ยังไม่ระบุ')}
- ผู้โดยสาร: {travel_slots.get('adults', 'ยังไม่ระบุ')} ผู้ใหญ่

ข้อความล่าสุด:
"""
        # Add recent messages
        for msg in messages[-5:]:  # Last 5 messages
            role = "ผู้ใช้" if msg.get("type") == "user" else "ระบบ"
            text = msg.get("text", "")[:100]  # Limit length
            prompt += f"\n{role}: {text}"
        
        prompt += "\n\nสรุปสิ่งที่ตกลงกันแล้ว และสิ่งที่ยังต้องทำต่อ (สั้น 50-100 คำ):"
        
        return prompt
    
    @staticmethod
    def _parse_summary(summary_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LLM summary into structured format"""
        # Simple parsing - could be enhanced with structured output
        return {
            "agreed_upon": context.get("last_travel_slots", {}),
            "preferences": {},
            "next_steps": []
        }
    
    @staticmethod
    def _create_fallback_summary(context: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback summary when LLM fails"""
        travel_slots = context.get("last_travel_slots", {})
        
        return {
            "summary_text": f"การสนทนาเกี่ยวกับทริปไป {travel_slots.get('destination', 'ไม่ระบุ')}",
            "agreed_upon": travel_slots,
            "preferences": {},
            "next_steps": [],
            "created_at": datetime.utcnow().isoformat(),
            "message_count": 0
        }

