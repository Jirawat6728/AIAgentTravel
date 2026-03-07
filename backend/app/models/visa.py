"""
โมเดลและฟังก์ชันสำหรับระบบวีซ่าหลายประเทศ/หลายประเภท (Multi-Visa)

ออกแบบตามแนวทาง:
- หนึ่งคนมีวีซ่าได้ไม่จำกัด (หลายประเทศ, หลายประเภทต่อประเทศ)
- วีซ่าผูกกับเลขพาสปอร์ต (linked_passport) — ต้องพกเล่มที่ลงวีซ่าไปด้วย
- Agent เช็ก: Visa-Free, Visa Type ตรงวัตถุประสงค์, Validity, Single/Multiple Entry
- status: Active | Expired
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


VISA_STATUS_ACTIVE = "Active"
VISA_STATUS_EXPIRED = "Expired"

ENTRIES_SINGLE = "Single"
ENTRIES_MULTIPLE = "Multiple"


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(str(s).strip()[:10], "%Y-%m-%d")
    except ValueError:
        return None


def compute_visa_status(entry: Dict[str, Any]) -> str:
    """คำนวณ status จาก expiry_date — หมดอายุแล้ว = Expired."""
    expiry = _parse_date(entry.get("expiry_date"))
    if not expiry:
        return entry.get("status") or VISA_STATUS_ACTIVE
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    if expiry.date() < today.date():
        return VISA_STATUS_EXPIRED
    return VISA_STATUS_ACTIVE


def get_active_visas(visa_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """คืนเฉพาะวีซ่าที่ยังใช้งานได้ (status Active, ยังไม่หมดอายุ)."""
    if not visa_records:
        return []
    result = []
    for v in visa_records:
        status = compute_visa_status(v)
        if status == VISA_STATUS_ACTIVE:
            out = dict(v)
            out["status"] = status
            result.append(out)
    return result


def get_visas_for_country(visa_records: List[Dict[str, Any]], country_code: str) -> List[Dict[str, Any]]:
    """คืนวีซ่าที่ตรงประเทศ (country_code) และยัง active."""
    active = get_active_visas(visa_records)
    code_upper = (country_code or "").strip().upper()
    if not code_upper:
        return []
    return [v for v in active if (v.get("country_code") or "").strip().upper() == code_upper]


def get_linked_passport_warning(visa_record: Dict[str, Any], user_passport_numbers: List[str]) -> Optional[str]:
    """
    ถ้าวีซ่าผูกกับเลขพาสปอร์ตที่ไม่อยู่ในรายการพาสปอร์ตปัจจุบันของ user (เช่น เล่มเก่าหมดอายุ)
    คืนข้อความเตือนให้พกเล่มเก่าที่มีวีซ่าไปด้วย
    """
    linked = (visa_record.get("linked_passport") or "").strip()
    if not linked:
        return None
    normalized = [p.strip().upper() for p in user_passport_numbers if p and str(p).strip()]
    if linked.upper() in normalized:
        return None
    return f"วีซ่านี้ลงในพาสปอร์ตเลข {linked} — กรุณาพกพาสปอร์ตเล่มนั้นไปด้วยเมื่อเดินทาง"


def legacy_to_visa_records(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """แปลงข้อมูลวีซ่าแบบเก่า (visa_type, visa_number, ...) เป็น array visa_records."""
    import uuid
    v_type = (doc.get("visa_type") or "").strip()
    v_number = (doc.get("visa_number") or "").strip()
    v_country = (doc.get("visa_issuing_country") or "").strip() or doc.get("visa_issuing_country")
    if not v_type and not v_number and not v_country:
        return []
    entry = {
        "id": str(uuid.uuid4()),
        "country_code": v_country or "",
        "visa_type": v_type or "OTHER",
        "visa_number": v_number or None,
        "issue_date": doc.get("visa_issue_date") or None,
        "expiry_date": doc.get("visa_expiry_date") or None,
        "entries": "Multiple" if (doc.get("visa_entry_type") or "").strip().upper() == "M" else "Single",
        "purpose": (doc.get("visa_purpose") or "T").strip() or "T",
        "linked_passport": (doc.get("passport_no") or "").strip() or None,
        "status": VISA_STATUS_ACTIVE,
    }
    entry["status"] = compute_visa_status(entry)
    return [entry]


def ensure_visa_records_from_doc(doc: Dict[str, Any], key: str = "visa_records") -> List[Dict[str, Any]]:
    """คืน visa_records ของ doc: ถ้ามีอยู่แล้วและเป็น list ไม่ว่าง คืนนั้น; ไม่มีหรือว่าง แต่มี legacy visa fields คืนจาก legacy_to_visa_records."""
    existing = doc.get(key)
    if isinstance(existing, list) and len(existing) > 0:
        return existing
    return legacy_to_visa_records(doc)
