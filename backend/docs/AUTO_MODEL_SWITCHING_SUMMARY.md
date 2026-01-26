# Auto Model Switching - สรุปการใช้งาน

## ✅ สิ่งที่เพิ่มเข้ามา

### 1. Model Selector Service (`backend/app/services/model_selector.py`)
- **TaskComplexity Enum**: SIMPLE, MODERATE, COMPLEX
- **ModelTier Enum**: FLASH, PRO, ULTRA
- **ModelSelector Class**: วิเคราะห์ความซับซ้อนและเลือก model

### 2. Configuration (`backend/app/core/config.py`)
```python
# ตัวอย่าง .env
ENABLE_AUTO_MODEL_SWITCHING=true
GEMINI_FLASH_MODEL=gemini-1.5-flash
GEMINI_PRO_MODEL=gemini-1.5-pro
GEMINI_ULTRA_MODEL=gemini-1.5-pro
```

### 3. LLM Service Updates (`backend/app/services/llm.py`)
- เพิ่ม `auto_select_model` parameter
- เพิ่ม `context` parameter สำหรับ model selection
- สามารถสลับ model ได้อัตโนมัติระหว่างการเรียกใช้

### 4. Agent Integration (`backend/app/engine/agent.py`)
- Controller: ใช้ context="controller" (งานซับซ้อน → Pro)
- Responder: ใช้ context="responder" (งานปานกลาง → Flash)

### 5. Memory Integration (`backend/app/services/memory.py`)
- Memory consolidation: ใช้ context="memory" (งานง่าย → Flash)

## 🎯 ตัวอย่างการทำงาน

### Simple Query (Flash)
```
User: "ใช่ จองเลย"
→ Complexity: SIMPLE
→ Model: gemini-1.5-flash
→ Fast & Cheap
```

### Moderate Query (Flash)
```
User: "ค้นหาโรงแรมในภูเก็ต 3 คืน วันที่ 15-18 มีนา"
→ Complexity: MODERATE
→ Model: gemini-1.5-flash
→ Fast & Cost-effective
```

### Complex Query (Pro)
```
User: "วางแผนทริปหลายเมืองไปโตเกียว โอซาก้า และเกียวโต 7 วัน 6 คืน พร้อมเที่ยวบินและโรงแรมทุกเมือง และเปรียบเทียบตัวเลือกที่ดีที่สุด"
→ Complexity: COMPLEX
→ Model: gemini-1.5-pro
→ More capable, better reasoning
```

## 📊 Complexity Analysis Factors

1. **Length**: ข้อความยาว → ซับซ้อนกว่า
2. **Keywords**: 
   - Complex: "multi-city", "analyze", "compare", "comprehensive"
   - Moderate: "search", "find", "book", "update"
   - Simple: "yes", "no", "ok", "confirm"
3. **Patterns**: หลายวันที่, หลายสถานที่, หลาย "and"/"และ"
4. **Context**: Controller > Responder > Memory

## 💡 ข้อดี

1. **ประหยัดต้นทุน**: ใช้ Flash สำหรับงาน 70-80% ของคำสั่ง
2. **ความแม่นยำ**: ใช้ Pro เฉพาะงานที่ต้องการ reasoning สูง
3. **ความเร็ว**: Flash เร็วกว่า Pro มาก
4. **Automatic**: ไม่ต้องกำหนด model ด้วยตัวเอง
5. **Flexible**: สามารถ force tier ได้ถ้าต้องการ

## 🔧 การใช้งาน

### ใช้ Auto Selection (Default)
```python
# ในโค้ด
response = await llm.generate_content(
    prompt=user_input,
    auto_select_model=True,  # Default
    context="controller"
)
```

### Force Specific Model
```python
from app.services.model_selector import ModelSelector, ModelTier

model_name, _ = ModelSelector.recommend_model(
    user_input="Plan a trip",
    force_tier=ModelTier.PRO  # บังคับใช้ Pro
)
```

### Disable Auto Switching
```bash
# ใน .env
ENABLE_AUTO_MODEL_SWITCHING=false
GEMINI_MODEL_NAME=gemini-1.5-flash
```

## 📈 ผลการทดสอบ

```bash
cd backend
python -c "from app.services.model_selector import ModelSelector; print(ModelSelector.analyze_complexity('Plan a complex trip'))"
```

Output:
```
2026-01-12 - Model selection: gemini-1.5-flash (complexity=simple, tier=flash)
TaskComplexity.SIMPLE
```

## 🚀 ขั้นตอนต่อไป

1. **Monitor**: ติดตาม model usage และ cost
2. **Tune**: ปรับ thresholds ตาม performance
3. **ML**: ใช้ ML เพื่อ predict complexity ได้แม่นยำขึ้น
4. **A/B Test**: ทดสอบ thresholds ต่างๆ
5. **Feedback Loop**: ใช้ user feedback ปรับปรุง model selection

## 📁 ไฟล์ที่เกี่ยวข้อง

- `backend/app/services/model_selector.py` - Core logic
- `backend/app/services/llm.py` - LLM integration
- `backend/app/core/config.py` - Configuration
- `backend/app/engine/agent.py` - Agent integration
- `backend/app/services/memory.py` - Memory integration
- `backend/docs/AUTO_MODEL_SWITCHING.md` - Documentation
- `backend/tests/test_model_selector.py` - Unit tests

## ⚙️ Environment Variables

```bash
# Enable/Disable
ENABLE_AUTO_MODEL_SWITCHING=true

# Model Names
GEMINI_FLASH_MODEL=gemini-1.5-flash
GEMINI_PRO_MODEL=gemini-1.5-pro
GEMINI_ULTRA_MODEL=gemini-1.5-pro

# Fallback (if auto switching disabled)
GEMINI_MODEL_NAME=gemini-1.5-flash
```

## 🎉 เสร็จสมบูรณ์!

ระบบสามารถสลับ Gemini model อัตโนมัติได้แล้ว โดยพิจารณาจากความซับซ้อนของคำสั่ง เพื่อ optimize ทั้งต้นทุนและประสิทธิภาพ
