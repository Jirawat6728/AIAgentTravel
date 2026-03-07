# ออกแบบระบบหนังสือเดินทางหลายเล่ม (Multi-Passport)

## หลักการ (จาก Gemini / ข้อควรระวังสำหรับ Travel & Booking Agent)

- **1 คนมีได้หลายเล่ม** เนื่องจาก: หลายสัญชาติ (Dual/Multiple Citizenship), หลายประเภท (Ordinary / Official / Diplomatic), หรือเล่มที่สอง (Second Valid Passport)
- **แต่ละทริปใช้ได้แค่ 1 เล่ม** — ตอนจอง AI/ระบบต้องเลือกหรือให้ผู้ใช้เลือก
- **Validity:** เฉพาะเล่มที่ `status = active` และยังไม่หมดอายุ
- **6-Month Rule:** เตือนผู้ใช้ถ้าเหลืออายุไม่ถึง 6 เดือน (บางสายการบิน/ประเทศไม่อนุญาต)
- **Primary Passport:** ในโปรไฟล์มี flag เลือกเล่มที่ใช้บ่อยเป็นค่าเริ่มต้น ตอนจองตั๋วดึงเล่มนี้มาใช้

## โครงสร้างข้อมูล

### User / Family member

- **passports** (array of objects) — เก็บหลายเล่ม
- แต่ละ element:

```json
{
  "id": "uuid",
  "passport_no": "A12345678",
  "passport_type": "N",
  "passport_issue_date": "2020-01-15",
  "passport_expiry": "2030-01-14",
  "passport_issuing_country": "TH",
  "passport_given_names": "John",
  "passport_surname": "Doe",
  "nationality": "TH",
  "place_of_birth": "Bangkok",
  "status": "active",
  "is_primary": true
}
```

- **passport_type:** `N` = ทั่วไป, `O` = ราชการ, `D` = ทูต, `S` = บริการ
- **status:** `active` | `expired` | `cancelled`
- **is_primary:** เล่มที่ใช้เป็นค่าเริ่มต้นตอนจอง (ควรมีได้แค่ 1 เล่มต่อคน)

### Backward compatibility

- ข้อมูลเก่า (single `passport_no`, `passport_expiry`, ...) ถูกแปลงเป็น `passports: [ {...} ]` เมื่ออ่าน (legacy_to_passports / ensure_passports_from_doc)
- เมื่อบันทึก `passports` ระบบจะ sync ฟิลด์เล่มเดียว (passport_no, passport_expiry, ...) จาก **primary** เพื่อให้ code เดิมที่อ่านเล่มเดียวยังใช้ได้

## API

- **GET /api/auth/me**  
  - คืน `user.passports`, `user.primary_passport`, `user.passport_warnings`  
  - แต่ละ `user.family[i]` มี `passports`, `primary_passport`, `passport_warnings`  
  - ค่าเหล่านี้ถูก derive จาก legacy อัตโนมัติถ้ายังไม่มี `passports`

- **PUT /api/auth/profile**  
  - รองรับ `passports: [ {...}, ... ]`  
  - ถ้าส่งมา ระบบจะบันทึกและ sync ฟิลด์เล่มเดียวจาก primary

## ฟังก์ชันช่วย (backend/app/models/passport.py)

| ฟังก์ชัน | คำอธิบาย |
|----------|----------|
| `ensure_passports_from_doc(doc)` | คืน `passports` array; ถ้าไม่มีจะสร้างจาก legacy |
| `get_active_passports(passports)` | คืนเฉพาะเล่มที่ status active และยังไม่หมดอายุ |
| `get_primary_passport(passports)` | คืนเล่มที่ is_primary; ถ้าไม่มีคืนเล่มแรกที่ active |
| `expiry_warning_6_months(entry)` | คืนข้อความเตือนถ้าเหลืออายุ &lt; 6 เดือน |
| `compute_passport_status(entry)` | คืน "active" / "expired" / "cancelled" ตาม expiry และ status |

## Frontend (ที่ควรทำต่อ)

- หน้าโปรไฟล์: แสดงรายการ `passports` แก้ไข/เพิ่ม/ลบได้ ตั้งค่า "ใช้เป็นค่าเริ่มต้น" (is_primary) ได้
- แสดง `passport_warnings` (เหลืออายุไม่ถึง 6 เดือน / หมดอายุ)
- ผู้จองร่วม (family): รองรับ `passports` ต่อคนแบบเดียวกัน
- ตอนจอง: ดึง `primary_passport` ของผู้โดยสารมาใช้ หรือให้เลือกเล่มก่อนยืนยันจอง
