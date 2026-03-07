"""
โมเดลและฟังก์ชันสำหรับข้อมูลหนังสือเดินทางหลายเล่ม (Multi-Passport)

ออกแบบตามแนวทาง:
- 1 คนสามารถมีได้หลายเล่ม (หลายสัญชาติ / ประเภทต่างกัน / เล่มที่สอง)
- แต่ละทริปใช้ได้แค่ 1 เล่ม
- Validity: เฉพาะ status=active และยังไม่หมดอายุ
- 6-Month Rule: เตือนถ้าเหลืออายุไม่ถึง 6 เดือน
- Primary: เลือกเล่มที่ใช้บ่อยเป็นค่าเริ่มต้นตอนจอง
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field


# ประเภทหนังสือเดินทาง (ประเทศเดียวอาจมีหลายประเภท)
PASSPORT_TYPE_ORDINARY = "N"      # สีน้ำตาล - ทั่วไป
PASSPORT_TYPE_OFFICIAL = "O"      # สีน้ำเงิน - ราชการ
PASSPORT_TYPE_DIPLOMATIC = "D"    # สีแดง - ทูต
PASSPORT_TYPE_SERVICE = "S"       # บริการ

PASSPORT_STATUS_ACTIVE = "active"
PASSPORT_STATUS_EXPIRED = "expired"
PASSPORT_STATUS_CANCELLED = "cancelled"


class PassportEntry(BaseModel):
    """ข้อมูลหนังสือเดินทาง 1 เล่ม (ใช้ใน array passports ของ user หรือ family member)."""
    model_config = {"extra": "allow"}

    id: str = Field(..., description="Unique id (uuid) สำหรับอ้างอิง")
    passport_no: str = Field(..., min_length=6, description="เลขหนังสือเดินทาง")
    passport_type: str = Field(default="N", description="N=ทั่วไป, O=ราชการ, D=ทูต, S=บริการ")
    passport_issue_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    passport_expiry: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    passport_issuing_country: Optional[str] = Field(default=None, description="ISO country code")
    passport_given_names: Optional[str] = Field(default=None, description="ชื่อตามเล่ม (อังกฤษ)")
    passport_surname: Optional[str] = Field(default=None, description="นามสกุลตามเล่ม (อังกฤษ)")
    nationality: Optional[str] = Field(default=None, description="สัญชาติ (ISO)")
    place_of_birth: Optional[str] = Field(default=None, description="สถานที่เกิด")
    status: str = Field(default="active", description="active | expired | cancelled")
    is_primary: bool = Field(default=False, description="เล่มที่ใช้เป็นค่าเริ่มต้นตอนจอง")


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
    except ValueError:
        return None


def compute_passport_status(entry: Dict[str, Any]) -> str:
    """
    คำนวณ status จาก expiry และ status ที่เก็บไว้
    - cancelled อยู่แล้ว → cancelled
    - expiry < today → expired
    - อื่น ๆ → active
    """
    if (entry.get("status") or "").strip().lower() == PASSPORT_STATUS_CANCELLED:
        return PASSPORT_STATUS_CANCELLED
    expiry = _parse_date(entry.get("passport_expiry"))
    if not expiry:
        return entry.get("status") or PASSPORT_STATUS_ACTIVE
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if expiry.date() < today.date():
        return PASSPORT_STATUS_EXPIRED
    return PASSPORT_STATUS_ACTIVE


def get_active_passports(passports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """คืนเฉพาะเล่มที่ใช้งานได้ (status active และยังไม่หมดอายุ)."""
    if not passports:
        return []
    result = []
    for p in passports:
        status = compute_passport_status(p)
        if status == PASSPORT_STATUS_ACTIVE:
            out = dict(p)
            out["status"] = status
            result.append(out)
    return result


def get_primary_passport(passports: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """คืนเล่มที่ตั้งเป็น primary; ถ้าไม่มี คืนเล่มแรกที่ active."""
    active = get_active_passports(passports)
    if not active:
        return None
    for p in active:
        if p.get("is_primary"):
            return p
    return active[0]


def expiry_warning_6_months(entry: Dict[str, Any]) -> Optional[str]:
    """
    ถ้าเล่มนี้เหลืออายุไม่ถึง 6 เดือน คืนข้อความเตือน; ไม่เช่นนั้นคืน None.
    """
    expiry = _parse_date(entry.get("passport_expiry"))
    if not expiry:
        return None
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    six_months = today + timedelta(days=180)
    if expiry.date() < today.date():
        return "หนังสือเดินทางเล่มนี้หมดอายุแล้ว"
    if expiry.date() < six_months.date():
        return "หนังสือเดินทางเล่มนี้เหลืออายุไม่ถึง 6 เดือน — บางสายการบิน/ประเทศอาจไม่อนุญาตให้เดินทาง"
    return None


def legacy_to_passports(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    แปลงข้อมูลเล่มเดียวแบบเก่า (passport_no, passport_expiry, ...) เป็น array passports.
    ไม่แก้ doc; คืน list ที่พร้อมใช้ (มี id, status, is_primary).
    """
    import uuid
    no = (doc.get("passport_no") or "").strip()
    if not no:
        return []
    entry = {
        "id": str(uuid.uuid4()),
        "passport_no": no,
        "passport_type": doc.get("passport_type") or "N",
        "passport_issue_date": doc.get("passport_issue_date") or None,
        "passport_expiry": doc.get("passport_expiry") or None,
        "passport_issuing_country": doc.get("passport_issuing_country") or None,
        "passport_given_names": doc.get("passport_given_names") or None,
        "passport_surname": doc.get("passport_surname") or None,
        "nationality": doc.get("nationality") or None,
        "place_of_birth": doc.get("place_of_birth") or None,
        "status": PASSPORT_STATUS_ACTIVE,
        "is_primary": True,
    }
    status = compute_passport_status(entry)
    entry["status"] = status
    return [entry]


def ensure_passports_from_doc(doc: Dict[str, Any], key: str = "passports") -> List[Dict[str, Any]]:
    """
    คืน passports array ของ doc: ถ้ามี key อยู่แล้วและเป็น list ไม่ว่าง คืนนั้น;
    ถ้าไม่มีหรือว่าง แต่มี passport_no แบบเก่า คืนจาก legacy_to_passports.
    """
    existing = doc.get(key)
    if isinstance(existing, list) and len(existing) > 0:
        return existing
    return legacy_to_passports(doc)
