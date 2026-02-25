# AI Workflow — สรุปการทำงานของ Agent

## 1. จุดเข้า (Entry Point)

- **Frontend** ส่งข้อความผ่าน **POST /api/chat** (stream หรือ non-stream)
- **chat.py** สร้าง task `agent.run_turn(session_id, user_input, status_callback, mode)`
- ข้อความผู้ใช้บันทึกลง MongoDB (`conversations`) **ก่อน** เรียก `run_turn` (realtime save)

---

## 2. ภายใน `run_turn` (agent.py)

### Phase 0: Recall + Context

1. **Recall** — ดึงความจำระยะยาวของ user จาก `memories` (Brain)
2. **Sliding Window** — `memory.build_conversation_context(session_id, user_input)` ดึงประวัติแชทล่าสุดจาก `conversations` (มี compaction ถ้าเกินขนาด)
3. **User Profile** — ดึง context จากโปรไฟล์ผู้ใช้

### Phase 1 & 2: Controller + Responder

- ถ้า **ENABLE_LANGGRAPH_FULL_WORKFLOW=true** (default):
  - ใช้ **LangGraph** `run_full_workflow()` แทน loop ใน agent
  - Flow: **START → controller → execute → (controller | responder) → END**
- ถ้าเป็น false หรือ LangGraph ผิดพลาด:
  - ใช้ **run_controller()** (loop ใน agent.py) แล้วค่อย **generate_response()**

### Phase 3: Consolidate

- รัน **memory.consolidate()** ในพื้นหลัง (เรียนรู้ความจำใหม่จากคู่บทสนทนา)

### สุดท้าย

- บันทึก session (trip_plan, options, selected)
- ข้อความ bot บันทึกลง `conversations` หลังได้ response (ใน chat.py)

---

## 3. LangGraph Full Workflow (full_workflow_graph.py)

```
START → controller → execute → [ route ]
                                    ├─ has_ask_user หรือ iteration >= max → responder → END
                                    └─ ไม่ออก → controller (วนซ้ำ)
```

- **controller node**: เรียก `_call_controller_llm()` ได้ `ControllerAction` (คิด action ถัดไป)
- **execute node**: เรียก `agent.execute_controller_action()` ทำ action จริง
- **responder node**: เรียก `agent.generate_response()` สร้างข้อความตอบกลับ
- **max_iterations**: ใน graph ถูก cap ที่ **2** (ใน run_controller ใช้ได้ถึง 3 ตาม config)

### Action types (จาก Controller LLM)

| Action | ความหมาย |
|--------|----------|
| `UPDATE_REQ` | อัปเดตความต้องการทริป (วันที่, ต้นทาง, ปลายทาง, ฯลฯ) |
| `CALL_SEARCH` | เรียกค้นเที่ยวบิน/โรงแรม/รถ |
| `SELECT_OPTION` | เลือกตัวเลือกจาก options_pool (เที่ยวบิน/โรงแรมที่เลือก) |
| `CREATE_ITINERARY` | สร้างแผนการเดินทางใหม่ |
| `ASK_USER` | ขอให้ผู้ใช้ตัดสินใจหรือให้ข้อมูลเพิ่ม |
| `BATCH` | ทำหลาย action พร้อมกัน |

---

## 4. Controller LLM (_call_controller_llm)

- รับ: state (trip_plan แบบ strip options_pool), user_input, action_log, memory_context, user_profile_context, conversation_context, workflow_validation, ml_intent_hint, ml_validation_result
- ส่งไปยัง Gemini ให้คิด **action ถัดไป** (และ thought)
- มี **loop detection**: ถ้า action เดิมซ้ำเกิน threshold จะบังคับไป responder (ASK_USER)

---

## 5. Execute (execute_controller_action)

- **CREATE_ITINERARY** → สร้าง/อัปเดตแผน (เที่ยวบินขาไป/กลับ, ที่พัก, รถ)
- **UPDATE_REQ** → อัปเดต requirements ของ segment
- **CALL_SEARCH** → ค้น Amadeus (เที่ยวบิน/โรงแรม) ใส่ผลลง options_pool; ถ้า mode=agent จะ trigger auto-select หลังค้น
- **SELECT_OPTION** → เลือก option จาก options_pool ใส่ใน selected_option
- **ASK_USER** → ในโหมด normal หยุดแล้วไป responder; ในโหมด agent อาจ infer แผนจากข้อความแล้วสร้าง itinerary เอง

---

## 6. Responder (generate_response)

- รับ session, action_log, memory_context, user_profile_context, user_input
- ใช้ LLM สร้างข้อความตอบกลับภาษาไทยจาก action_log และ state ปัจจุบัน

---

## 7. โหมด (mode)

- **normal**: ผู้ใช้เลือกช้อยส์เอง; ASK_USER = แสดงตัวเลือกให้ user เลือก
- **agent**: AI เลือกช้อยส์และจองให้; หลัง CALL_SEARCH มี auto-select; มีขั้นตอน auto-book ถ้าครบ

---

## 8. สิ่งที่ควรตรวจ (Checklist)

| รายการ | ตำแหน่ง | หมายเหตุ |
|--------|---------|----------|
| บันทึกข้อความ user ก่อน run_turn | chat.py ~1154, ~1614 | save_message ก่อน create_task / run_turn |
| บันทึกข้อความ bot หลังได้ response | chat.py ~1406, ~1670 | หลัง task เสร็จ / หลัง run_turn |
| conversation_context ส่งเข้า controller | full_workflow_graph.py _controller_node, agent._call_controller_llm | ส่งใน state และ kwargs |
| Sliding window + compaction | memory.build_conversation_context | max_messages, max_chars, _compact_context |
| Loop detection ใน graph | full_workflow_graph.py _controller_node | action_history, loop_detection_threshold |
| Max iterations ใน graph | full_workflow_graph.py run_full_workflow | min(settings.controller_max_iterations, **2**) |
| Fallback เมื่อ LangGraph ล้ม | agent.run_turn | except → run_controller + generate_response |
| Agent mode auto-complete | agent._run_agent_mode_auto_complete | หลัง execute หรือหลัง run_full_workflow ถ้ามี options_to_select |

---

## 9. Config ที่เกี่ยวข้อง

- `ENABLE_LANGGRAPH_FULL_WORKFLOW` (default: true) — ใช้ LangGraph แทน controller loop
- `CONTROLLER_MAX_ITERATIONS` (default: 3) — ใช้เต็มใน run_controller; ใน LangGraph ถูก cap ที่ 2
