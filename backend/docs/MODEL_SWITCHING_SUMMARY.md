# สรุปการสลับโมเดล Flash / Pro ตามความยากของคำสั่ง

**อัปเดต:** ปรับให้ Controller/Responder ใช้ความยากจากข้อความผู้ใช้ (ModelSelector) และให้ ProductionLLMService อ่านชื่อโมเดลจาก .env แล้ว

## 1. โฟลว์ที่ใช้อยู่ตอนนี้

มี **สองเส้นทาง** ที่เกี่ยวกับการเลือกโมเดล:

### ก. ProductionLLMService (เส้นทางหลัก – ใช้เมื่อ agent ทำงานปกติ)

- **ที่อยู่:** `app/services/llm.py` — คลาส `ProductionLLMService`
- **ใช้เมื่อ:** Agent เรียก `controller_generate`, `responder_generate`, `intelligence_generate`

**การเลือกโมเดล (select_model_for_brain):**

| Brain        | โมเดลพื้นฐาน (preferred) | เมื่อ complexity = "simple" | เมื่อ complexity = "moderate" | เมื่อ complexity = "complex" |
|-------------|---------------------------|----------------------------|------------------------------|------------------------------|
| CONTROLLER  | **PRO**                   | -                          | PRO                          | PRO                          |
| RESPONDER   | **FLASH**                 | FLASH                      | FLASH                        | **PRO**                      |
| INTELLIGENCE| **PRO**                   | FLASH                      | PRO                          | PRO                          |

- **ความหมาย:**  
  - **Controller** ใช้ Pro เสมอ (ไม่สลับตาม complexity)  
  - **Responder** สลับได้: simple → Flash, moderate → Flash, complex → Pro  
  - **Intelligence** ใช้ Pro เป็นหลัก; เฉพาะ simple ถึงใช้ Flash  

**ค่าที่ agent ส่งเข้าไป (อัปเดตแล้ว):**

- **Controller:**  
  - เรียก `ModelSelector.analyze_complexity(user_input, context="controller")` → ได้ "simple" / "moderate" / "complex"  
  - ถ้าโหมด Agent และได้ "simple" → บังคับเป็น "moderate"  
  - ส่งค่า complexity นี้เข้า `controller_generate`
- **Responder:**  
  - เรียก `ModelSelector.analyze_complexity(user_input, context="responder")`  
  - ถ้ามี agent_mode_actions และได้ "simple" → "moderate"; ได้ "moderate" → "complex"  
  - ส่งค่า complexity นี้เข้า `responder_generate`
- **Intelligence:**  
  - ส่ง `complexity = "complex"` ตายตัว (ไม่เปลี่ยน)  

**ชื่อโมเดลจริง:**  
- **อัปเดตแล้ว:** ProductionLLMService ใช้ `settings.gemini_flash_model` และ `settings.gemini_pro_model` (.env) ผ่าน `get_model_name()`  
- ถ้า .env ไม่มีค่า จะใช้ fallback `gemini-2.5-flash` / `gemini-2.5-pro`

---

### ข. ModelSelector + LLMService (เส้นทาง fallback / auto-switch ตามข้อความ)

- **ที่อยู่:**  
  - `app/services/model_selector.py` — `ModelSelector`, `analyze_complexity`, `select_model`, `recommend_model`  
  - `app/services/llm.py` — `LLMService.generate_content(..., auto_select_model=True, context=...)`
- **ใช้เมื่อ:**  
  - ใช้ `LLMService.generate_content()` (เช่น fallback เมื่อไม่มี ProductionLLMService)  
  - และเปิด **Auto Model Switching** แล้ว

**การทำงานของ ModelSelector:**

1. **analyze_complexity(user_input, context, task_type)**  
   - ดูความยาวข้อความ  
   - คำหลัก (complex / moderate / simple) ภาษา EN + TH  
   - รูปแบบวันที่ หลายวัน/หลายจุด  
   - context (เช่น "controller", "memory") และ task_type  
   - ส่งคืน: `TaskComplexity` = SIMPLE / MODERATE / COMPLEX  

2. **select_model(complexity)**  
   - COMPLEX → **Pro**  
   - MODERATE / SIMPLE → **Flash**  

3. **get_model_name(tier)**  
   - อ่านชื่อโมเดลจาก **settings** (config):  
     - `settings.gemini_flash_model`  
     - `settings.gemini_pro_model`  
   - ดังนั้นชื่อโมเดลจะตาม `.env`  

**สถานะการเปิดใช้:**  
- ใน `config.py`: `enable_auto_model_switching` มาจาก env `ENABLE_AUTO_MODEL_SWITCHING`  
- ค่าเริ่มต้น = **false**  
- ดังนั้นโดยค่าเริ่มต้น **ModelSelector จะไม่ถูกใช้** ในเส้นทางหลัก (agent ใช้ ProductionLLMService ซึ่งไม่เรียก ModelSelector)

---

## 2. สรุปสั้นๆ

- **การสลับ Flash/Pro ตามความยากของคำสั่ง**  
  - **มีอยู่แล้ว** ใน ModelSelector (วิเคราะห์จากข้อความ + context + task_type → SIMPLE/MODERATE/COMPLEX → Flash/Pro)  
  - แต่เส้นทางหลักของแชทใช้ **ProductionLLMService** ซึ่ง **ไม่ได้ใช้ ModelSelector**  
  - ProductionLLMService ใช้แค่ค่า `complexity` ที่ agent กำหนดจากโหมด (Agent/Normal) และประเภท action (Responder: simple/complex) **ไม่ได้วิเคราะห์จากข้อความผู้ใช้**  

- **ชื่อโมเดล Flash/Pro**  
  - **ModelSelector / config:** ใช้จาก `.env` (`GEMINI_FLASH_MODEL`, `GEMINI_PRO_MODEL`)  
  - **ProductionLLMService:** ใช้จาก `MODEL_MAP` ในโค้ด ไม่ได้อ่านจาก settings  

---

## 3. แนวทางถ้าต้องการให้สลับตามความยากของคำสั่งจริงๆ

1. **ให้ Controller / Responder ใช้ความยากจากข้อความผู้ใช้**  
   - ก่อนเรียก `controller_generate` / `responder_generate` เรียก  
     `ModelSelector.analyze_complexity(user_input, context="controller" หรือ "responder", task_type=...)`  
   - แปลงผลเป็น "simple" / "moderate" / "complex" แล้วส่งเป็น `complexity` เข้า `controller_generate` / `responder_generate`  
   - จะได้การสลับ Flash/Pro ตามความยากของคำสั่งจริง (ใน ProductionLLMService)

2. **เปิด Auto Model Switching สำหรับเส้นทาง fallback**  
   - ตั้ง `ENABLE_AUTO_MODEL_SWITCHING=true` ใน `.env`  
   - เฉพาะเส้นทางที่เรียก `LLMService.generate_content(..., auto_select_model=True, context=...)` ถึงจะใช้ ModelSelector

3. **ให้ ProductionLLMService ใช้ชื่อโมเดลจาก .env**  
   - แทนที่การอ่านจาก `MODEL_MAP` ในโค้ด ให้ใช้ `settings.gemini_flash_model` และ `settings.gemini_pro_model` สำหรับ Flash และ Pro ตาม tier ที่เลือก  
   - จะได้ควบคุมโมเดลจาก `.env` ได้ทั้งสองเส้นทาง

ไฟล์ที่เกี่ยวข้องโดยตรง:
- `app/core/config.py` — `enable_auto_model_switching`, `gemini_flash_model`, `gemini_pro_model`
- `app/services/model_selector.py` — การวิเคราะห์ความยากและเลือก tier
- `app/services/llm.py` — ProductionLLMService (select_model_for_brain, MODEL_MAP), LLMService.generate_content
- `app/engine/agent.py` — การส่ง complexity เข้า controller_generate / responder_generate
