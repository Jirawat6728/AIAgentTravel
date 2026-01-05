# 🎯 Plan: ทำให้ Agent มีความแม่นยำเหมือน Agoda/Traveloka

## 📊 สถานะปัจจุบัน

### ✅ สิ่งที่มีอยู่แล้ว:
1. **Slot Extraction** - ใช้ Gemini + regex fallback (แม่นยำดีแล้ว)
2. **Search Results** - ใช้ Amadeus API (ข้อมูลจริง)
3. **Plan Choices Building** - มี 10 personas (ถูกสุด, เร็วสุด, สมดุล, etc.)
4. **UserProfileMemory** - มี class สำหรับเก็บ preferences
5. **Memory System** - Context, Session Store, Memory Policy

### ⚠️ สิ่งที่ยังขาด:
1. **Personalized Ranking** - Choices ไม่ได้เรียงตาม user preferences
2. **User Profile Integration** - UserProfileMemory ไม่ได้ใช้ในการ ranking
3. **Smart Scoring Algorithm** - ไม่มี scoring function ที่ใช้ preferences
4. **Validation Functions** - ยังไม่มี validation ที่ครอบคลุม

---

## 🚀 Action Plan

### Phase 1: เพิ่ม Personalized Scoring Algorithm ⭐ (Priority 1)

**เป้าหมาย:** สร้าง scoring function ที่ใช้ user preferences ในการให้คะแนน choices

**Files to modify:**
- `backend/core/plan_builder.py` - เพิ่ม `calculate_personalized_score()`
- `backend/core/plan_builder.py` - แก้ไข `build_persona_choices()` เพื่อรับ `user_profile`

**Implementation:**
```python
def calculate_personalized_score(
    choice: Dict[str, Any],
    user_profile: Dict[str, Any],
    travel_slots: Dict[str, Any]
) -> float:
    """
    Calculate personalized score for a choice based on user preferences.
    Lower score = better match (for sorting).
    """
    score = 0.0
    prefs = user_profile.get("preferences", {})
    
    # Flight preferences
    flight_prefs = prefs.get("flight_preferences", {})
    if flight_prefs.get("prefer_direct") and not choice.get("is_non_stop"):
        score += 5000  # Penalty for non-direct
    
    # Hotel preferences
    hotel_prefs = prefs.get("hotel_preferences", {})
    preferred_stars = hotel_prefs.get("preferred_stars")
    if preferred_stars:
        hotel = choice.get("hotel", {})
        # Check hotel stars and add penalty if mismatch
    
    # Budget preferences
    budget_range = prefs.get("budget_range")
    if budget_range:
        # Add penalty if price is outside preferred range
    
    # Travel style
    travel_style = prefs.get("travel_style")
    if travel_style == "budget":
        # Prefer cheaper options
        score += (choice.get("total_price") or 0) * 0.1
    elif travel_style == "luxury":
        # Prefer premium options
        # Add logic to prefer higher-end choices
    
    return score
```

---

### Phase 2: แก้ไข build_plan_choices_3 เพื่อใช้ Personalized Scoring

**Files to modify:**
- `backend/core/plan_builder.py` - แก้ไข `build_plan_choices_3()` signature
- `backend/core/orchestrator.py` - แก้ไข calls to `build_plan_choices_3()`

**Changes:**
1. เพิ่ม `user_id: Optional[str] = None` parameter
2. ดึง UserProfileMemory ถ้ามี user_id
3. ใช้ personalized score ในการเรียงลำดับ choices
4. Personalize personas ตาม user preferences

---

### Phase 3: ปรับปรุง build_persona_choices เพื่อใช้ User Profile

**Files to modify:**
- `backend/core/plan_builder.py` - แก้ไข `build_persona_choices()`

**Changes:**
1. เพิ่ม `user_profile: Optional[Dict[str, Any]] = None` parameter
2. ใช้ user preferences เพื่อเลือก personas ที่เหมาะสม
3. เรียงลำดับ personas ตาม user preferences (ถ้ามี)

---

### Phase 4: เพิ่ม Validation Functions (Optional)

**Files to create/modify:**
- `backend/utils/validation.py` - สร้างไฟล์ใหม่

**Functions to add:**
- `validate_date(date_str: str) -> bool`
- `validate_location(location: str) -> bool`
- `validate_numbers(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> bool`

---

## 📝 Implementation Steps

### Step 1: สร้าง Personalized Scoring Function
- [ ] เพิ่ม `calculate_personalized_score()` ใน `plan_builder.py`
- [ ] ทดสอบ function ด้วย test cases

### Step 2: แก้ไข build_plan_choices_3
- [ ] เพิ่ม `user_id` parameter
- [ ] ดึง UserProfileMemory
- [ ] ใช้ personalized score ในการเรียงลำดับ

### Step 3: แก้ไข build_persona_choices
- [ ] เพิ่ม `user_profile` parameter
- [ ] ใช้ preferences ในการเลือก personas

### Step 4: Update Orchestrator
- [ ] แก้ไข calls to `build_plan_choices_3()` ให้ส่ง `user_id`

### Step 5: Testing
- [ ] ทดสอบ personalized ranking
- [ ] ตรวจสอบว่า preferences ถูกใช้อย่างถูกต้อง

---

## 🎯 Expected Results

หลังจากทำเสร็จ:
1. ✅ Choices จะเรียงตาม user preferences
2. ✅ Personas จะถูกเลือกตาม preferences (เช่น ถ้า user ชอบ budget → แนะนำ "ถูกสุด" เป็นอันดับแรก)
3. ✅ ความแม่นยำเพิ่มขึ้น (choices ตรงกับสิ่งที่ user ต้องการมากขึ้น)
4. ✅ ประสบการณ์ผู้ใช้ดีขึ้น (เหมือน Agoda/Traveloka)

---

## 💡 Additional Improvements (Future)

1. **A/B Testing** - ทดสอบ algorithms ต่างๆ
2. **Machine Learning** - ใช้ ML model เพื่อ personalize
3. **Real-time Preferences** - เรียนรู้ preferences จาก real-time behavior
4. **Multi-factor Scoring** - เพิ่ม factors อื่นๆ (reviews, ratings, etc.)


