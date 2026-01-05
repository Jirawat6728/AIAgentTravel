"""
Router Agent: ตัวแยกทาง (Intent Classification)
หน้าที่เดียว: ฟังแล้วชี้ทาง (ห้ามตอบเนื้อหา)

หลักการ:
1. Router มีหน้าที่แค่ classify intent เท่านั้น
2. ใช้ System Prompt ที่แคบและชัดเจน
3. ใช้ Few-Shot Prompting
4. ใช้ Structured Output (JSON)
"""

from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field
import json
import logging

from core.config import get_gemini_client, GEMINI_MODEL_NAME
from google.genai import types
from utils.json_utils import get_text_from_parts, safe_extract_json


class RouterIntent(BaseModel):
    """
    Router Output Schema
    ใช้ Pydantic เพื่อควบคุม output ให้เป็น JSON structure ที่ชัดเจน
    """
    intent: Literal[
        "search_flight",
        "search_hotel", 
        "search_car",
        "search_trip",  # Full trip (flight + hotel + car)
        "edit_flight",
        "edit_hotel",
        "edit_car",
        "cancel_booking",
        "payment",
        "general_chat",
        "greeting",
        "help",
        "none"
    ] = Field(..., description="The category of the user's request")
    
    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0"
    )
    
    reason: Optional[str] = Field(
        default=None,
        description="Brief reason for the classification (for debugging)"
    )


class RouterAgent:
    """
    Router Agent: ตัวแยกทาง
    มีหน้าที่เดียวคือ classify intent จาก user message
    ห้ามตอบเนื้อหา ห้ามทำอะไรอื่น
    """
    
    SYSTEM_PROMPT = """คุณเป็น Router Agent สำหรับแอปท่องเที่ยว
หน้าที่ของคุณ: วิเคราะห์ข้อความผู้ใช้และจำแนกเป็น intent หนึ่งในรายการด้านล่าง

Intents ที่มี:
1. "search_flight": เมื่อผู้ใช้พูดถึงการบิน, สนามบิน, สายการบิน, เที่ยวบิน, ไฟลต์
2. "search_hotel": เมื่อผู้ใช้พูดถึงที่พัก, โรงแรม, ห้องพัก, การพักคืน
3. "search_car": เมื่อผู้ใช้พูดถึงรถเช่า, การขับรถ, การรับรถ
4. "search_trip": เมื่อผู้ใช้พูดถึงทริป, การเที่ยว, วางแผนทริป (รวมหลายอย่าง)
5. "edit_flight": เมื่อผู้ใช้พูดถึงการแก้ไขไฟลต์, เปลี่ยนไฟลต์, แก้ไขเที่ยวบิน
6. "edit_hotel": เมื่อผู้ใช้พูดถึงการแก้ไขที่พัก, เปลี่ยนที่พัก, แก้ไขโรงแรม
7. "edit_car": เมื่อผู้ใช้พูดถึงการแก้ไขรถเช่า, เปลี่ยนรถ
8. "cancel_booking": เมื่อผู้ใช้พูดถึงการยกเลิกการจอง, ยกเลิกทริป
9. "payment": เมื่อผู้ใช้พูดถึงการชำระเงิน, จ่ายเงิน, ยืนยันจอง
10. "general_chat": เมื่อผู้ใช้พูดคุยทั่วไป, ถามเรื่องอื่นที่ไม่เกี่ยวกับการจอง
11. "greeting": เมื่อผู้ใช้ทักทาย, สวัสดี, หวัดดี
12. "help": เมื่อผู้ใช้ขอความช่วยเหลือ, ถามวิธีใช้
13. "none": เมื่อไม่สามารถจำแนกได้ชัดเจน

กฎสำคัญ:
- ห้ามตอบเนื้อหาของผู้ใช้
- ห้ามให้คำแนะนำ
- ห้ามอธิบาย
- แค่ classify intent เท่านั้น
- ตอบเป็น JSON เท่านั้น

Output Format: JSON only
{
  "intent": "search_flight",
  "confidence": 0.9,
  "reason": "User mentioned flying to destination"
}

Examples (Few-Shot Learning):
User: "อยากไปเชียงใหม่พรุ่งนี้"
Output: {"intent": "search_trip", "confidence": 0.95, "reason": "User wants to plan a trip with destination and date"}

User: "หาที่พักแถวสยามให้หน่อย"
Output: {"intent": "search_hotel", "confidence": 0.9, "reason": "User is looking for accommodation"}

User: "จองตั๋วไปญี่ปุ่นให้หน่อย"
Output: {"intent": "search_flight", "confidence": 0.95, "reason": "User wants to book a flight"}

User: "สวัสดีครับ หิวข้าวหรือยัง"
Output: {"intent": "general_chat", "confidence": 0.8, "reason": "Greeting and casual conversation"}

User: "หารถเช่าขับที่ภูเก็ต"
Output: {"intent": "search_car", "confidence": 0.9, "reason": "User wants to rent a car"}

User: "แก้ไขไฟลต์ segment 1"
Output: {"intent": "edit_flight", "confidence": 0.95, "reason": "User wants to edit a flight segment"}

User: "แก้ไขที่พัก"
Output: {"intent": "edit_hotel", "confidence": 0.9, "reason": "User wants to edit hotel"}

User: "ยกเลิกการจอง"
Output: {"intent": "cancel_booking", "confidence": 0.95, "reason": "User wants to cancel booking"}

User: "จ่ายเงิน"
Output: {"intent": "payment", "confidence": 0.9, "reason": "User wants to pay"}

User: "สวัสดี"
Output: {"intent": "greeting", "confidence": 0.95, "reason": "Simple greeting"}

User: "ช่วยหน่อย"
Output: {"intent": "help", "confidence": 0.85, "reason": "User asking for help"}

User: "ไปเที่ยว"
Output: {"intent": "search_trip", "confidence": 0.8, "reason": "Vague travel request"}

User: "บินจากกรุงเทพไปโอซาก้า 26 ธ.ค. 3 คืน ผู้ใหญ่ 3"
Output: {"intent": "search_trip", "confidence": 0.95, "reason": "Complete trip planning request with flight, dates, and passengers"}
"""
    
    @staticmethod
    async def route(user_message: str, context: Optional[dict] = None) -> RouterIntent:
        """
        Route user message to appropriate intent
        
        Args:
            user_message: ข้อความจากผู้ใช้
            context: Optional context (เช่น มี current_plan หรือไม่)
        
        Returns:
            RouterIntent: Intent classification result
        """
        if not user_message or not user_message.strip():
            return RouterIntent(intent="none", confidence=0.0, reason="Empty message")
        
        # Build prompt with context if available
        prompt = user_message.strip()
        
        # Add context hints if available
        if context:
            context_hints = []
            if context.get("current_plan"):
                context_hints.append("Note: User has an active trip plan")
            if context.get("slot_workflow"):
                context_hints.append("Note: User is in slot selection workflow")
            
            if context_hints:
                prompt = f"{prompt}\n\nContext: {'; '.join(context_hints)}"
        
        try:
            # Call Gemini with structured output
            # Use asyncio.to_thread to run synchronous Gemini call
            import asyncio
            
            def _call_gemini_sync():
                client = get_gemini_client()
                if not client:
                    raise RuntimeError("Gemini client not configured")
                
                resp = client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=[
                        {"role": "user", "parts": [{"text": RouterAgent.SYSTEM_PROMPT}]},
                        {"role": "user", "parts": [{"text": prompt}]},
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.1,  # Low temperature for consistent classification
                        max_output_tokens=200,
                    ),
                )
                return get_text_from_parts(resp)
            
            response_text = await asyncio.to_thread(_call_gemini_sync)
            
            # Parse JSON response
            # Try to extract JSON from response
            response_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse JSON
            try:
                data = json.loads(response_text)
                return RouterIntent(**data)
            except json.JSONDecodeError:
                # Try to extract JSON object from text
                import re
                json_match = re.search(r'\{[^}]+\}', response_text)
                if json_match:
                    data = json.loads(json_match.group())
                    return RouterIntent(**data)
                else:
                    # Fallback: try to infer intent from keywords
                    logging.warning(f"Failed to parse Router response as JSON: {response_text}")
                    return RouterAgent._fallback_classify(user_message)
        
        except Exception as e:
            logging.error(f"Router Agent error: {e}")
            return RouterAgent._fallback_classify(user_message)
    
    @staticmethod
    def _fallback_classify(user_message: str) -> RouterIntent:
        """
        Fallback classification using keyword matching
        ใช้เมื่อ LLM ไม่สามารถ parse ได้
        """
        msg_lower = user_message.lower()
        
        # Keyword patterns
        if any(kw in msg_lower for kw in ["บิน", "ไฟลต์", "เที่ยวบิน", "flight", "airline", "สนามบิน"]):
            return RouterIntent(intent="search_flight", confidence=0.7, reason="Keyword: flight")
        elif any(kw in msg_lower for kw in ["ที่พัก", "โรงแรม", "hotel", "accommodation", "ห้องพัก"]):
            return RouterIntent(intent="search_hotel", confidence=0.7, reason="Keyword: hotel")
        elif any(kw in msg_lower for kw in ["รถเช่า", "rental", "car", "ขับรถ"]):
            return RouterIntent(intent="search_car", confidence=0.7, reason="Keyword: car")
        elif any(kw in msg_lower for kw in ["แก้ไขไฟลต์", "แก้ไฟลต์", "เปลี่ยนไฟลต์", "edit flight"]):
            return RouterIntent(intent="edit_flight", confidence=0.7, reason="Keyword: edit flight")
        elif any(kw in msg_lower for kw in ["แก้ไขที่พัก", "แก้ที่พัก", "เปลี่ยนที่พัก", "edit hotel"]):
            return RouterIntent(intent="edit_hotel", confidence=0.7, reason="Keyword: edit hotel")
        elif any(kw in msg_lower for kw in ["ยกเลิก", "cancel", "ลบการจอง"]):
            return RouterIntent(intent="cancel_booking", confidence=0.7, reason="Keyword: cancel")
        elif any(kw in msg_lower for kw in ["จ่ายเงิน", "ชำระเงิน", "payment", "pay"]):
            return RouterIntent(intent="payment", confidence=0.7, reason="Keyword: payment")
        elif any(kw in msg_lower for kw in ["สวัสดี", "หวัดดี", "hello", "hi"]):
            return RouterIntent(intent="greeting", confidence=0.7, reason="Keyword: greeting")
        elif any(kw in msg_lower for kw in ["ช่วย", "help", "วิธีใช้"]):
            return RouterIntent(intent="help", confidence=0.7, reason="Keyword: help")
        elif any(kw in msg_lower for kw in ["ไป", "เที่ยว", "ทริป", "trip", "travel"]):
            return RouterIntent(intent="search_trip", confidence=0.6, reason="Keyword: trip")
        else:
            return RouterIntent(intent="general_chat", confidence=0.5, reason="No clear intent matched")

