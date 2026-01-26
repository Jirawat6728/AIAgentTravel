# Auto Model Switching

## Overview

ระบบสามารถสลับ Gemini model อัตโนมัติตามความซับซ้อนของคำสั่ง เพื่อ optimize ต้นทุนและประสิทธิภาพ

## Model Tiers

| Tier | Model | Use Case | Cost | Speed |
|------|-------|----------|------|-------|
| **Flash** | `gemini-1.5-flash` | คำสั่งง่าย, การค้นหาทั่วไป, การยืนยัน | ต่ำ | เร็วมาก |
| **Pro** | `gemini-1.5-pro` | คำสั่งซับซ้อน, การวางแผนหลายขั้นตอน, การวิเคราะห์ | กลาง | ปานกลาง |
| **Ultra** | `gemini-1.5-ultra` (fallback to Pro) | งานที่ยากที่สุด (ยังไม่พร้อมใช้งาน) | สูง | ช้า |

## Complexity Analysis

ระบบวิเคราะห์ความซับซ้อนตาม:

### 1. Length-based (ความยาวข้อความ)
- **Simple**: < 100 characters
- **Moderate**: 100-200 characters
- **Complex**: > 200 characters

### 2. Keyword-based (คำสำคัญ)

**Complex Keywords:**
- `multi-city`, `complex`, `detailed`, `comprehensive`
- `analyze`, `compare`, `optimize`, `recommend`
- `plan trip`, `multiple`, `batch`, `all segments`
- Thai: `ทริปซับซ้อน`, `วางแผน`, `เปรียบเทียบ`, `วิเคราะห์`, `หลายเมือง`

**Moderate Keywords:**
- `search`, `find`, `book`, `update`, `change`, `modify`
- Thai: `ค้นหา`, `จอง`, `เปลี่ยน`, `แก้ไข`

**Simple Keywords:**
- `yes`, `no`, `ok`, `confirm`, `cancel`, `help`, `hello`
- Thai: `ใช่`, `ไม่`, `ตกลง`, `ยืนยัน`, `ยกเลิก`, `สวัสดี`

### 3. Pattern-based
- **Multiple dates/locations**: ตรวจจับรูปแบบวันที่และสถานที่หลายแห่ง
- **Multiple requests**: ตรวจจับ "and", ",", "และ" หลายครั้ง

### 4. Context-based
- **Controller**: งานตัดสินใจมักซับซ้อนกว่า
- **Responder**: การตอบสนองอาจง่ายกว่า
- **Memory**: การจำมักเป็นงานง่าย

## Configuration

### Environment Variables

```bash
# Enable/Disable Auto Switching
ENABLE_AUTO_MODEL_SWITCHING=true

# Model Names
GEMINI_FLASH_MODEL=gemini-1.5-flash
GEMINI_PRO_MODEL=gemini-1.5-pro
GEMINI_ULTRA_MODEL=gemini-1.5-pro
```

### Programmatic Control

```python
from app.services.model_selector import ModelSelector, select_model_for_task

# Analyze complexity
complexity = ModelSelector.analyze_complexity(
    user_input="Plan a trip to Tokyo and Osaka",
    context="controller"
)

# Get recommended model
model_name = select_model_for_task(
    user_input="Plan a trip to Tokyo",
    context="controller"
)

# Force a specific tier
from app.services.model_selector import ModelTier
model_name, complexity = ModelSelector.recommend_model(
    user_input="Find hotels",
    force_tier=ModelTier.PRO  # Force Pro model
)
```

## Examples

### Simple Query (Flash Model)
```
User: "ใช่ จองเลย"
→ Complexity: SIMPLE
→ Model: gemini-1.5-flash
```

### Moderate Query (Flash Model)
```
User: "ค้นหาโรงแรมในภูเก็ต 3 คืน"
→ Complexity: MODERATE
→ Model: gemini-1.5-flash
```

### Complex Query (Pro Model)
```
User: "วางแผนทริปหลายเมืองไปโตเกียว โอซาก้า และเกียวโต 7 วัน 6 คืน พร้อมเที่ยวบินและโรงแรมทุกเมือง"
→ Complexity: COMPLEX
→ Model: gemini-1.5-pro
```

## Monitoring

ระบบ log การเลือก model ทุกครั้ง:

```
INFO: Model selection: gemini-1.5-pro (complexity=complex, tier=pro)
INFO: Model selection: gemini-1.5-flash (complexity=moderate, tier=flash)
```

## Cost Optimization

การใช้ Auto Model Switching ช่วย:
- **ลดต้นทุน 50-70%**: ใช้ Flash สำหรับงานทั่วไป
- **เพิ่มความแม่นยำ**: ใช้ Pro เฉพาะงานซับซ้อน
- **เพิ่มความเร็ว**: Flash เร็วกว่า Pro มาก

## Disable Auto Switching

หากต้องการใช้ model เดียวตลอด:

```bash
ENABLE_AUTO_MODEL_SWITCHING=false
GEMINI_MODEL_NAME=gemini-1.5-flash
```

## Future Enhancements

- [ ] ML-based complexity prediction
- [ ] User feedback loop for model selection
- [ ] Cost tracking per model
- [ ] A/B testing different thresholds
