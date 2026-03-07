# ออกแบบระบบวีซ่า (Multi-Visa) สำหรับ AI Travel Agent

## หลักการ (ตัวปราบเซียน)

- **หนึ่งคนมีวีซ่าได้ไม่จำกัด** — หลายประเทศพร้อมกัน, หลายประเภทต่อประเทศ (เช่น ท่องเที่ยว + ธุรกิจ ของอเมริกาในเล่มเดียวกัน)
- **วีซ่าผูกกับเลขพาสปอร์ต (linked_passport)** — วีซ่าส่วนใหญ่ลงในเล่มที่ใช้สมัคร; ถ้าเปลี่ยนเล่มใหม่ ต้องพกเล่มเก่าที่มีวีซ่าไปด้วย
- **Agent ต้องเช็ก:** Visa-Free หรือไม่, Visa Type ตรงวัตถุประสงค์ไหม, Validity (ยังไม่หมดอายุ), Single/Multiple Entry

## โครงสร้างข้อมูล

### User document (MongoDB)

- **visa_records** (array of objects) — เก็บหลายวีซ่า
- แต่ละ element:

```json
{
  "id": "uuid",
  "country_code": "USA",
  "visa_type": "B1/B2",
  "visa_number": "optional",
  "issue_date": "2020-01-15",
  "expiry_date": "2030-12-31",
  "entries": "Multiple",
  "purpose": "T",
  "linked_passport": "AA1234567",
  "status": "Active"
}
```

- **country_code:** ประเทศปลายทาง/ประเทศที่ออกวีซ่า (ISO เช่น USA, GBR, CHN)
- **visa_type:** ประเภทวีซ่า (B1/B2, L, Schengen, TOURIST, eVisa ฯลฯ)
- **entries:** `Single` | `Multiple`
- **purpose:** T=ท่องเที่ยว, B=ธุรกิจ, S=ศึกษา, W=ทำงาน, TR=ผ่านทาง, O=อื่นๆ
- **linked_passport:** เลขพาสปอร์ตเล่มที่ใช้สมัคร/ลงวีซ่า — ต้องตรงกับ passports ในระบบ
- **status:** `Active` | `Expired` (คำนวณจาก expiry_date)

### Backward compatibility

- ข้อมูลเก่า (visa_type, visa_number, visa_expiry_date, ...) ถูกแปลงเป็น `visa_records: [ {...} ]` เมื่ออ่าน (legacy_to_visa_records / ensure_visa_records_from_doc)
- เมื่อบันทึก `visa_records` ระบบจะ sync ฟิลด์เล่มเดียว (visa_type, visa_expiry_date, ...) จาก **วีซ่าแรกที่ active** เพื่อให้ code เดิมที่อ่านเล่มเดียวยังใช้ได้

## API

- **GET /api/auth/me**
  - คืน `user.visa_records`, `user.visa_warnings`
  - visa_warnings: เตือนกรณี linked_passport ไม่ตรงกับพาสปอร์ตปัจจุบัน (ให้พกเล่มเก่าไปด้วย)

- **PUT /api/auth/profile**
  - รองรับ `visa_records: [ {...}, ... ]`
  - ถ้าส่งมา ระบบจะบันทึกและ sync ฟิลด์ legacy จาก first active visa

## ฟังก์ชันช่วย (backend/app/models/visa.py)

| ฟังก์ชัน | คำอธิบาย |
|----------|----------|
| ensure_visa_records_from_doc(doc) | คืน visa_records; ถ้าไม่มีจะสร้างจาก legacy |
| get_active_visas(visa_records) | คืนเฉพาะรายการที่ยังไม่หมดอายุ (status Active) |
| get_visas_for_country(visa_records, country_code) | คืนวีซ่าที่ตรงประเทศและยัง active |
| compute_visa_status(entry) | คืน "Active" / "Expired" ตาม expiry_date |
| get_linked_passport_warning(visa_record, user_passport_numbers) | คืนข้อความเตือนถ้าวีซ่าผูกกับเล่มที่ไม่อยู่ในรายการปัจจุบัน |

## Workflow เมื่อนายหน้า AI เจอเรื่องวีซ่า

1. **Requirement Check:** AI เช็กสัญชาติผู้ใช้ + ประเทศปลายทาง → ต้องใช้วีซ่าหรือไม่ (Visa-Free หรือไม่)
2. **Internal Search:** AI ค้นหาใน `visa_records` ของผู้ใช้ (และเช็ก linked_passport กับ passports)
3. **Action Logic:**
   - **มีวีซ่าที่ใช้ได้:** "คุณมีวีซ่า [ประเทศ] แบบ [ประเภท] ที่ยังไม่หมดอายุ ผมจะดำเนินการจองต่อนะครับ" (+ เตือนพกเล่มพาสปอร์ตที่ลงวีซ่าถ้า linked_passport ไม่ใช่เล่มปัจจุบัน)
   - **ไม่มี / หมดอายุ:** "ประเทศนี้ต้องใช้วีซ่าครับ ยังไม่พบข้อมูลวีซ่าที่ใช้งานได้ของคุณ ต้องการให้ส่งลิสต์เอกสารที่ต้องเตรียม หรือแนะนำเอเจนซี่ทำวีซ่าไหมครับ?"

## Frontend (หน้าโปรไฟล์)

- หมวด "ข้อมูลวีซ่า": แสดงรายการ visa_records (การ์ดต่อรายการ), ปุ่มเพิ่ม/แก้ไข/ลบ
- ฟอร์มเพิ่ม/แก้: ประเทศปลายทาง (country_code), ประเภท (visa_type), วันหมดอายุ (expiry_date), การเข้าประเทศ (Single/Multiple), **ผูกกับพาสปอร์ต** (dropdown จาก user.passports), เลขวีซ่า/วันออก/วัตถุประสงค์ (ถ้ามี)
- แสดง status / หมดอายุ และ visa_warnings (linked_passport)
- Validate ทุกช่องที่กรอกก่อนบันทึก
