"""
Workflow Validator
ตรวจสอบลำดับขั้นตอนและ validate ข้อมูลทุกครั้ง - ห้ามข้ามขั้นตอน
"""

from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from app.core.logging import get_logger
from app.models.trip_plan import SegmentStatus, Segment, FlightGroup

logger = get_logger(__name__)


class WorkflowStep(str, Enum):
    """ลำดับขั้นตอนที่ถูกต้อง"""
    CREATE_ITINERARY = "create_itinerary"  # 1. สร้างทริป
    UPDATE_REQ = "update_req"  # 2. อัปเดตข้อมูล
    CALL_SEARCH = "call_search"  # 3. ค้นหา
    SELECTING = "selecting"  # 4. แสดงตัวเลือก
    SELECT_OPTION = "select_option"  # 5. เลือกตัวเลือก
    CONFIRMED = "confirmed"  # 6. ยืนยัน
    TRIP_SUMMARY = "trip_summary"  # 7. แสดงสรุป
    BOOKING = "booking"  # 8. จอง


class WorkflowValidator:
    """
    Validator สำหรับตรวจสอบลำดับขั้นตอนและ validate ข้อมูล
    ห้ามข้ามขั้นตอน - ต้องทำตามลำดับ
    """
    
    # ลำดับขั้นตอนที่ถูกต้อง
    STEP_ORDER = [
        WorkflowStep.CREATE_ITINERARY,
        WorkflowStep.UPDATE_REQ,
        WorkflowStep.CALL_SEARCH,
        WorkflowStep.SELECTING,
        WorkflowStep.SELECT_OPTION,
        WorkflowStep.CONFIRMED,
        WorkflowStep.TRIP_SUMMARY,
        WorkflowStep.BOOKING
    ]
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def validate_step_order(
        self,
        current_step: str,
        previous_step: Optional[str] = None,
        action: str = None
    ) -> Tuple[bool, Optional[str]]:
        """
        ตรวจสอบลำดับขั้นตอน - ห้ามข้ามขั้นตอน
        
        Args:
            current_step: ขั้นตอนปัจจุบัน
            previous_step: ขั้นตอนก่อนหน้า
            action: Action ที่กำลังทำ
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # แปลงเป็น WorkflowStep
            try:
                current = WorkflowStep(current_step.lower())
            except ValueError:
                # ถ้าไม่ใช่ enum ที่รู้จัก ให้อนุญาต (อาจเป็น custom step)
                return True, None
            
            # ถ้าไม่มี previous_step ให้อนุญาต (เริ่มต้นใหม่)
            if not previous_step:
                return True, None
            
            try:
                previous = WorkflowStep(previous_step.lower())
            except ValueError:
                # ถ้า previous_step ไม่ใช่ enum ที่รู้จัก ให้อนุญาต
                return True, None
            
            # ตรวจสอบลำดับ
            current_index = self.STEP_ORDER.index(current)
            previous_index = self.STEP_ORDER.index(previous)
            
            # ห้ามย้อนกลับ (ยกเว้น UPDATE_REQ ที่สามารถทำได้ทุกเมื่อ)
            if current_index < previous_index and current != WorkflowStep.UPDATE_REQ:
                error_msg = (
                    f"❌ ข้ามขั้นตอน: ไม่สามารถข้ามจาก '{previous.value}' ไป '{current.value}' "
                    f"ได้ ต้องทำตามลำดับ: {[s.value for s in self.STEP_ORDER]}"
                )
                self.logger.warning(error_msg)
                return False, error_msg
            
            # ห้ามข้ามขั้นตอน (ต้องทำทีละขั้น)
            if current_index > previous_index + 1 and current != WorkflowStep.UPDATE_REQ:
                skipped_steps = [
                    self.STEP_ORDER[i].value 
                    for i in range(previous_index + 1, current_index)
                ]
                error_msg = (
                    f"❌ ข้ามขั้นตอน: ข้ามขั้นตอน {', '.join(skipped_steps)} "
                    f"จาก '{previous.value}' ไป '{current.value}'"
                )
                self.logger.warning(error_msg)
                return False, error_msg
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error validating step order: {e}", exc_info=True)
            # ถ้าเกิด error ให้อนุญาต (fail-safe)
            return True, None
    
    def validate_segment_data(
        self,
        segment: Segment,
        slot_name: str,
        step: str
    ) -> Tuple[bool, List[str]]:
        """
        Validate ข้อมูลใน segment ตามขั้นตอน
        
        Args:
            segment: Segment ที่จะ validate
            slot_name: ชื่อ slot
            step: ขั้นตอนปัจจุบัน
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            # Validate ตามขั้นตอน
            if step == WorkflowStep.CREATE_ITINERARY.value:
                # ตรวจสอบ requirements พื้นฐาน
                req = segment.requirements
                if "flights" in slot_name:
                    if not req.get("origin"):
                        issues.append(f"{slot_name}: 缺少 origin (ต้นทาง)")
                    if not req.get("destination"):
                        issues.append(f"{slot_name}: 缺少 destination (ปลายทาง)")
                    if not req.get("departure_date") and not req.get("date"):
                        issues.append(f"{slot_name}: 缺少 departure_date (วันเดินทาง)")
                
                elif "accommodation" in slot_name:
                    if not req.get("location"):
                        issues.append(f"{slot_name}: 缺少 location (ที่ตั้ง)")
                    if not req.get("check_in"):
                        issues.append(f"{slot_name}: 缺少 check_in (วันเช็คอิน)")
                    if not req.get("check_out"):
                        issues.append(f"{slot_name}: 缺少 check_out (วันเช็คเอาท์)")
            
            elif step == WorkflowStep.CALL_SEARCH.value:
                # ตรวจสอบว่ามี requirements ครบก่อน search
                if not segment.needs_search():
                    if len(segment.options_pool) > 0:
                        issues.append(f"{slot_name}: มี options อยู่แล้ว ไม่ต้อง search ใหม่")
                    else:
                        issues.append(f"{slot_name}: requirements ยังไม่ครบ ไม่สามารถ search ได้")
            
            elif step == WorkflowStep.SELECTING.value:
                # ตรวจสอบว่ามี options_pool
                if len(segment.options_pool) == 0:
                    issues.append(f"{slot_name}: ไม่มี options ให้เลือก ต้อง search ก่อน")
            
            elif step == WorkflowStep.SELECT_OPTION.value:
                # ตรวจสอบว่ามี options_pool และ selected_option
                if len(segment.options_pool) == 0:
                    issues.append(f"{slot_name}: ไม่มี options ให้เลือก")
                if not segment.selected_option:
                    issues.append(f"{slot_name}: ยังไม่ได้เลือก option")
            
            elif step == WorkflowStep.CONFIRMED.value:
                # ตรวจสอบว่ามี selected_option
                if not segment.selected_option:
                    issues.append(f"{slot_name}: ยังไม่ได้เลือก option ไม่สามารถ confirm ได้")
                if segment.status != SegmentStatus.CONFIRMED:
                    issues.append(f"{slot_name}: status ยังไม่ใช่ CONFIRMED")
            
            # Validate ข้อมูลใน selected_option
            if segment.selected_option:
                selected = segment.selected_option
                if isinstance(selected, dict):
                    # ตรวจสอบ required fields
                    if not selected.get("display_name") and not selected.get("name"):
                        issues.append(f"{slot_name}: selected_option ไม่มี display_name หรือ name")
                    if not selected.get("price_amount") and not selected.get("price_total") and not selected.get("price"):
                        issues.append(f"{slot_name}: selected_option ไม่มีราคา")
            
            # Validate ข้อมูลใน options_pool
            for idx, option in enumerate(segment.options_pool):
                if isinstance(option, dict):
                    if not option.get("display_name") and not option.get("name"):
                        issues.append(f"{slot_name}[{idx}]: option ไม่มี display_name หรือ name")
                    # ราคาไม่บังคับใน options_pool (อาจมีบางตัวที่ไม่มีราคา)
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            self.logger.error(f"Error validating segment data: {e}", exc_info=True)
            return False, [f"Validation error: {str(e)}"]
    
    def validate_trip_plan_completeness(
        self,
        trip_plan: Any,
        required_slots: List[str] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate ความครบถ้วนของ trip plan
        
        Args:
            trip_plan: TripPlan object
            required_slots: List of required slots (e.g., ["flights_outbound", "accommodation"])
            
        Returns:
            (is_valid, list_of_issues)
        """
        issues = []
        
        try:
            if required_slots is None:
                required_slots = []
            
            # ตรวจสอบ flights
            if "flights_outbound" in required_slots or "flights" in str(required_slots):
                if not trip_plan.travel.flights.outbound:
                    issues.append("缺少 flights_outbound segments")
                else:
                    for idx, seg in enumerate(trip_plan.travel.flights.outbound):
                        if not seg.is_complete():
                            issues.append(f"flights_outbound[{idx}]: ยังไม่ complete")
            
            if "flights_inbound" in required_slots:
                if trip_plan.travel.trip_type == "round_trip":
                    if not trip_plan.travel.flights.inbound:
                        issues.append("缺少 flights_inbound segments (round_trip ต้องมี)")
                    else:
                        for idx, seg in enumerate(trip_plan.travel.flights.inbound):
                            if not seg.is_complete():
                                issues.append(f"flights_inbound[{idx}]: ยังไม่ complete")
            
            # ตรวจสอบ accommodation
            if "accommodation" in required_slots:
                if not trip_plan.accommodation.segments:
                    issues.append("缺少 accommodation segments")
                else:
                    for idx, seg in enumerate(trip_plan.accommodation.segments):
                        if not seg.is_complete():
                            issues.append(f"accommodation[{idx}]: ยังไม่ complete")
            
            # ตรวจสอบ ground_transport
            if "ground_transport" in required_slots:
                if not trip_plan.travel.ground_transport:
                    issues.append("缺少 ground_transport segments")
                else:
                    for idx, seg in enumerate(trip_plan.travel.ground_transport):
                        if not seg.is_complete():
                            issues.append(f"ground_transport[{idx}]: ยังไม่ complete")
            
            is_valid = len(issues) == 0
            return is_valid, issues
            
        except Exception as e:
            self.logger.error(f"Error validating trip plan completeness: {e}", exc_info=True)
            return False, [f"Validation error: {str(e)}"]
    
    def get_current_workflow_step(
        self,
        trip_plan: Any
    ) -> str:
        """
        ตรวจสอบว่าอยู่ขั้นตอนไหนของ workflow
        
        Returns:
            Current workflow step
        """
        try:
            # ตรวจสอบทุก segments
            all_segments = []
            
            # Flights
            if trip_plan.travel.flights.outbound:
                all_segments.extend([("flights_outbound", seg) for seg in trip_plan.travel.flights.outbound])
            if trip_plan.travel.flights.inbound:
                all_segments.extend([("flights_inbound", seg) for seg in trip_plan.travel.flights.inbound])
            
            # Accommodation
            if trip_plan.accommodation.segments:
                all_segments.extend([("accommodation", seg) for seg in trip_plan.accommodation.segments])
            
            # Ground transport
            if trip_plan.travel.ground_transport:
                all_segments.extend([("ground_transport", seg) for seg in trip_plan.travel.ground_transport])
            
            if not all_segments:
                return WorkflowStep.CREATE_ITINERARY.value
            
            # หาขั้นตอนที่ต่ำที่สุด (ยังไม่เสร็จ)
            step_priority = {
                SegmentStatus.PENDING: WorkflowStep.UPDATE_REQ.value,
                SegmentStatus.SEARCHING: WorkflowStep.CALL_SEARCH.value,
                SegmentStatus.SELECTING: WorkflowStep.SELECTING.value,
                SegmentStatus.CONFIRMED: WorkflowStep.CONFIRMED.value
            }
            
            min_step = WorkflowStep.CONFIRMED.value
            for slot_name, seg in all_segments:
                seg_step = step_priority.get(seg.status, WorkflowStep.UPDATE_REQ.value)
                seg_index = self.STEP_ORDER.index(WorkflowStep(seg_step))
                min_index = self.STEP_ORDER.index(WorkflowStep(min_step))
                if seg_index < min_index:
                    min_step = seg_step
            
            # ถ้าทุก segment เป็น CONFIRMED แล้ว ให้แสดง summary
            if all(seg.status == SegmentStatus.CONFIRMED for _, seg in all_segments):
                return WorkflowStep.TRIP_SUMMARY.value
            
            return min_step
            
        except Exception as e:
            self.logger.error(f"Error getting current workflow step: {e}", exc_info=True)
            return WorkflowStep.CREATE_ITINERARY.value
    
    def validate_action_allowed(
        self,
        action: str,
        current_step: str,
        trip_plan: Any
    ) -> Tuple[bool, Optional[str]]:
        """
        ตรวจสอบว่า action นี้ทำได้ในขั้นตอนปัจจุบันหรือไม่
        
        Args:
            action: Action ที่ต้องการทำ
            current_step: ขั้นตอนปัจจุบัน
            trip_plan: TripPlan object
            
        Returns:
            (is_allowed, error_message)
        """
        try:
            # Action ที่ทำได้ทุกเมื่อ
            always_allowed = ["CREATE_ITINERARY", "UPDATE_REQ", "ASK_USER"]
            if action in always_allowed:
                return True, None
            
            # ตรวจสอบตาม current_step
            if action == "CALL_SEARCH":
                # ต้องมี requirements ครบก่อน
                all_segments = []
                if trip_plan.travel.flights.outbound:
                    all_segments.extend(trip_plan.travel.flights.outbound)
                if trip_plan.travel.flights.inbound:
                    all_segments.extend(trip_plan.travel.flights.inbound)
                if trip_plan.accommodation.segments:
                    all_segments.extend(trip_plan.accommodation.segments)
                if trip_plan.travel.ground_transport:
                    all_segments.extend(trip_plan.travel.ground_transport)
                
                if not all_segments:
                    return False, "ยังไม่มี segments ต้อง CREATE_ITINERARY ก่อน"
            
            elif action == "SELECT_OPTION":
                # ต้องมี options_pool ก่อน
                if current_step not in [WorkflowStep.SELECTING.value, WorkflowStep.CALL_SEARCH.value]:
                    return False, f"ยังไม่ถึงขั้นตอน SELECTING (ปัจจุบัน: {current_step})"
            
            return True, None
            
        except Exception as e:
            self.logger.error(f"Error validating action: {e}", exc_info=True)
            return True, None  # Fail-safe: อนุญาตถ้าเกิด error


# Global instance
_workflow_validator = None

def get_workflow_validator() -> WorkflowValidator:
    """Get or create workflow validator instance"""
    global _workflow_validator
    if _workflow_validator is None:
        _workflow_validator = WorkflowValidator()
    return _workflow_validator
