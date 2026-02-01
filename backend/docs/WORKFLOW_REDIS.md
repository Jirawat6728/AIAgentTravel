# Workflow (Redis) — การวางแผนถึงจอง

## ภาพรวม

หลังลบระบบ workflow เดิมแล้ว workflow ใหม่ใช้ **Redis** เป็นที่เก็บข้อมูลชั่วคราวของแต่ละ session: raw data จาก Amadeus, ตัวเลือกที่ normalize แล้ว, ช้อยที่ผู้ใช้เลือก และสถานะ workflow เมื่อจองสำเร็จหรือออกจาก flow จะเคลียร์ Redis ของ session นั้น

## ขั้นตอน (Steps)

| Step        | ความหมาย |
|------------|----------|
| `planning` | กำลังสร้างแผน (CREATE_ITINERARY) |
| `searching`| กำลังค้นหา Amadeus (CALL_SEARCH) |
| `selecting`| มีตัวเลือกให้เลือกใน PlanChoiceCard |
| `summary`  | เลือกครบแล้ว แสดง Trip Summary |
| `booking`  | กำลังจอง |
| `done`     | จองเสร็จ / ออกจาก flow (Redis ถูกเคลียร์) |

## การเก็บข้อมูลใน Redis

### 1. Raw data จาก Amadeus
- **Key**: `amadeus_raw:session:{session_id}:{slot_name}:{segment_index}`
- **เมื่อไหร่**: หลัง CALL_SEARCH แต่ละ slot (เที่ยวบิน/ที่พัก/การเดินทาง) ที่ได้ผลจาก Amadeus MCP
- **ใช้ทำอะไร**: ใช้จัดช้อยใหม่เมื่อผู้ใช้แก้ไข (โหลดจาก Redis มา normalize/จัดอีกครั้ง)

### 2. Options cache (ตัวเลือกที่ normalize แล้ว)
- **Key**: `options_cache:entry:{cache_key}`, `options_cache:session:{session_id}`
- **เมื่อไหร่**: หลัง normalize ผล Amadeus (หรือ cache hit จาก requirements เดิม)
- **ใช้ทำอะไร**: แสดงใน PlanChoiceCard แต่ละอัน (flight / hotel / transfer)

### 3. ช้อยที่เลือก (selected option)
- เก็บใน entry ของ options_cache ต่อ slot: `selected_option`, `selected_at`
- ใช้สำหรับ Trip Summary และการจอง

### 4. Workflow state
- **Key**: `workflow:state:{session_id}`
- **ค่า**: `{ step, slots_complete, created_at, updated_at }`
- **เมื่อไหร่**: อัปเดตหลัง CREATE_ITINERARY (planning), หลัง CALL_SEARCH (selecting), เมื่อพร้อมสรุป (summary)

## Flow การทำงาน

1. **CREATE_ITINERARY** → ตั้ง workflow step = `planning`
2. **CALL_SEARCH** (Amadeus) → เก็บ raw ลง Redis, normalize แล้วเก็บ options_cache, ตั้ง step = `selecting`
3. **แสดง PlanChoiceCard** → อ่านจาก segment.options_pool (ที่ sync กับ Redis/cache) จัดเป็น slot_choices + slot_intent ส่งไป frontend
4. **ผู้ใช้เลือกช้อย** → SELECT_OPTION → เก็บ selected ลง Redis (save_selected_option)
5. **เมื่อครบทุก slot** → แสดง Trip Summary, ตั้ง step = `summary`
6. **ผู้ใช้กดยืนยันการจอง** → `POST /api/booking/create` → จองเข้า My Bookings
7. **หลังจองสำเร็จ** → `clear_session_all(session_id)` + `clear_workflow(session_id)` เพื่อเคลียร์ options cache, raw Amadeus และ workflow state

## เมื่อผู้ใช้แก้ไข

- **แก้ไขแล้วค้นหาใหม่**: CALL_SEARCH ใหม่ → เก็บ raw ใหม่ใน Redis, options ใหม่ใน options_cache, แสดง PlanChoiceCard ตามเดิม
- **แก้ไขแค่เลือกช้อยอื่น**: ใช้ options ที่มีอยู่แล้วใน segment.options_pool / Redis ไม่ต้องค้นหาใหม่

## ไฟล์ที่เกี่ยวข้อง

- `app/services/workflow_state.py` — สถานะ workflow (get/set/clear)
- `app/services/options_cache.py` — options cache + raw Amadeus (save_raw_amadeus, get_raw_amadeus, clear_raw_amadeus, clear_session_all)
- `app/engine/agent.py` — CREATE_ITINERARY/CALL_SEARCH เก็บ raw + อัปเดต workflow step
- `app/api/chat.py` — get_agent_metadata สร้าง plan_choices/slot_choices จาก segment.options_pool + อัปเดต step summary
- `app/api/booking.py` — หลังจองสำเร็จ เคลียร์ Redis (clear_session_all + clear_workflow)
