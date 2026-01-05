"""
Slot Manager: Smart State Management for Slot Filling Flow
หัวใจสำคัญ: แยก Logic การควบคุม (State Management) ออกจาก NLU/LLM
ใช้ Code (Python) เป็นตัวเก็บข้อมูล ไม่ให้ LLM จำเอง
"""

from typing import Any, Dict, List, Optional
from datetime import date


class SlotManager:
    """
    Slot Manager: จัดการ state สำหรับ slot filling flow
    ใช้ Smart Merge เพื่อป้องกันข้อมูลหาย
    """
    
    def __init__(self, initial_state: Optional[Dict[str, Any]] = None):
        """
        Initialize SlotManager with initial state
        
        Args:
            initial_state: ข้อมูลเริ่มต้น (ถ้ามี)
        """
        # Required slots (ช่องว่างที่ต้องกรอก)
        self.state = {
            "origin": None,
            "destination": None,
            "start_date": None,
            "adults": None,
            "children": None,
            "return_date": None,
            "end_date": None,
            "days": None,
            "nights": None,
        }
        
        # Optional slots (ข้อมูลเสริม)
        self.optional_slots = {
            "area_preference": None,
            "cabin_class": None,
            "budget": None,
            "preferences": None,
        }
        
        # Merge initial state if provided
        if initial_state:
            self.update_state(initial_state)
        
        # Status tracking
        self.status = "collecting"  # collecting, confirming, completed
        self.missing_slots = []
        self._update_missing_slots()
    
    def _update_missing_slots(self):
        """อัปเดตรายการช่องว่างที่ยังขาด"""
        self.missing_slots = [
            key for key, value in self.state.items()
            if value is None and key in ["origin", "destination", "start_date", "adults"]
        ]
    
    def update_state(self, new_extracted_data: Dict[str, Any], preserve_existing: bool = True) -> Dict[str, Any]:
        """
        Smart Merge: อัปเดต state ด้วยข้อมูลใหม่ (รองรับการเปลี่ยนใจ)
        
        หลักการสำคัญ (Non-linear Conversation):
        - อัปเดตเฉพาะ key ที่มีค่าใหม่ (ไม่ใช่ None)
        - ถ้า preserve_existing=True จะไม่เขียนทับข้อมูลเก่าถ้ามีค่าแล้ว
        - ถ้า preserve_existing=False จะเขียนทับได้ (สำหรับกรณีแก้ไข/เปลี่ยนใจ)
        - Detect changes เพื่อให้ feedback กับผู้ใช้
        
        Args:
            new_extracted_data: ข้อมูลที่ LLM extract มา (เช่น {"destination": "Phuket"})
            preserve_existing: ถ้า True จะไม่เขียนทับข้อมูลเก่าถ้ามีค่าแล้ว
        
        Returns:
            Dict with:
            - updated_keys: List of keys that were updated
            - changes: List of change descriptions (for feedback)
            - is_correction: True if any existing value was overwritten
        """
        if not new_extracted_data:
            return {"updated_keys": [], "changes": [], "is_correction": False}
        
        updated_keys = []
        changes = []  # สำหรับ feedback กับผู้ใช้
        is_correction = False
        
        # Update required slots
        for key, value in new_extracted_data.items():
            if key in self.state:
                # Smart Merge: อัปเดตเฉพาะเมื่อมีค่าใหม่ (ไม่ใช่ None, "", หรือ empty)
                if value is not None and value != "":
                    old_value = self.state.get(key)
                    
                    # เช็คว่าเป็นการเปลี่ยนข้อมูลเดิมหรือไม่ (Correction)
                    if old_value is not None and old_value != value:
                        # การเปลี่ยนใจ: เขียนทับข้อมูลเดิม
                        if preserve_existing:
                            # ถ้า preserve_existing=True แต่มีการเปลี่ยนค่า แสดงว่าเป็นการแก้ไขชัดเจน
                            # ให้เขียนทับได้ (รองรับการเปลี่ยนใจ)
                            pass
                        
                        self.state[key] = value
                        updated_keys.append(key)
                        is_correction = True
                        
                        # สร้าง change description สำหรับ feedback
                        key_names = {
                            "origin": "ต้นทาง",
                            "destination": "ปลายทาง",
                            "start_date": "วันเดินทาง",
                            "return_date": "วันกลับ",
                            "end_date": "วันสิ้นสุด",
                            "adults": "จำนวนผู้ใหญ่",
                            "children": "จำนวนเด็ก",
                            "days": "จำนวนวัน",
                            "nights": "จำนวนคืน",
                        }
                        key_name = key_names.get(key, key)
                        changes.append(f"เปลี่ยน{key_name} จาก {old_value} เป็น {value}")
                    elif old_value is None:
                        # กรอกข้อมูลใหม่ (ยังไม่มีค่าเดิม)
                        self.state[key] = value
                        updated_keys.append(key)
                    elif not preserve_existing:
                        # Force overwrite (สำหรับกรณีแก้ไขชัดเจน)
                        self.state[key] = value
                        updated_keys.append(key)
        
        # Update optional slots
        for key, value in new_extracted_data.items():
            if key in self.optional_slots:
                if value is not None and value != "":
                    old_value = self.optional_slots.get(key)
                    if old_value is not None and old_value != value:
                        is_correction = True
                        changes.append(f"เปลี่ยน{key} จาก {old_value} เป็น {value}")
                    
                    if not preserve_existing or self.optional_slots[key] is None:
                        self.optional_slots[key] = value
                        if key not in updated_keys:
                            updated_keys.append(key)
        
        # Update missing slots
        self._update_missing_slots()
        
        return {
            "updated_keys": updated_keys,
            "changes": changes,
            "is_correction": is_correction
        }
    
    def get_state(self) -> Dict[str, Any]:
        """Get current state (required + optional slots)"""
        return {
            **self.state,
            **self.optional_slots
        }
    
    def get_required_state(self) -> Dict[str, Any]:
        """Get only required slots"""
        return dict(self.state)
    
    def get_missing_slots(self) -> List[str]:
        """Get list of missing required slots"""
        return self.missing_slots.copy()
    
    def is_complete(self) -> bool:
        """Check if all required slots are filled"""
        return len(self.missing_slots) == 0
    
    def get_next_question(self) -> Optional[str]:
        """
        Get next question to ask user based on missing slots
        Returns None if all slots are filled
        """
        if not self.missing_slots:
            return None
        
        # Priority order for questions
        question_map = {
            "destination": "คุณต้องการเดินทางไปที่ไหนครับ?",
            "origin": "คุณต้องการเดินทางจากที่ไหนครับ?",
            "start_date": "วางแผนเดินทางวันที่เท่าไหร่ครับ?",
            "adults": "มีผู้โดยสารกี่คนครับ? (ผู้ใหญ่)",
        }
        
        # Ask first missing slot
        first_missing = self.missing_slots[0]
        return question_map.get(first_missing, f"กรุณาระบุ {first_missing}")
    
    def clear_slot(self, key: str):
        """Clear a specific slot (for correction)"""
        if key in self.state:
            self.state[key] = None
        elif key in self.optional_slots:
            self.optional_slots[key] = None
        self._update_missing_slots()
    
    def reset(self):
        """Reset all slots"""
        for key in self.state:
            self.state[key] = None
        for key in self.optional_slots:
            self.optional_slots[key] = None
        self._update_missing_slots()
        self.status = "collecting"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for persistence"""
        return {
            "state": dict(self.state),
            "optional_slots": dict(self.optional_slots),
            "status": self.status,
            "missing_slots": self.missing_slots.copy(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlotManager":
        """Create SlotManager from dictionary (for restoration)"""
        manager = cls()
        if "state" in data:
            manager.state.update(data["state"])
        if "optional_slots" in data:
            manager.optional_slots.update(data["optional_slots"])
        if "status" in data:
            manager.status = data["status"]
        manager._update_missing_slots()
        return manager

