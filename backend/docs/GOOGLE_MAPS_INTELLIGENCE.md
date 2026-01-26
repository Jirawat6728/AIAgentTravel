# 🗺️ Google Maps Intelligence Integration

## Overview
ระบบ Google Maps Intelligence ที่เพิ่มความสามารถให้ Agent ค้นหาและแนะนำสถานที่รอบๆ landmark หรือพื้นที่ที่ผู้ใช้สนใจ

---

## 🎯 ความสามารถหลัก

### 1. **Nearby Hotel Search** - ค้นหาโรงแรมรอบๆ Landmark
ค้นหาโรงแรมที่อยู่ใกล้กับ landmark หรือสถานที่เฉพาะ พร้อมข้อมูลรีวิวและระดับราคา

```python
hotels = await LocationIntelligence.find_hotels_near_landmark(
    landmark_name="Siam Paragon",
    radius=2000,  # 2 km
    max_results=10
)

# ผลลัพธ์:
# [
#   {
#     "name": "InterContinental Bangkok",
#     "rating": 4.7,
#     "user_ratings_total": 6268,
#     "vicinity": "991 Ploenchit Road",
#     "price_level": 4,  # $$$$ (expensive)
#     "place_id": "ChIJ..."
#   },
#   ...
# ]
```

---

### 2. **Nearby Search** - ค้นหาสถานที่ตามประเภท
ค้นหาสถานที่ประเภทต่างๆ รอบๆ location ที่ระบุ

```python
# ค้นหาร้านอาหาร
restaurants = await LocationIntelligence.search_nearby_google(
    location_name="Grand Palace Bangkok",
    place_type="restaurant",
    radius=1000  # 1 km
)

# ค้นหาสถานที่ท่องเที่ยว
attractions = await LocationIntelligence.search_nearby_google(
    location_name="Siam Paragon",
    place_type="tourist_attraction",
    radius=3000  # 3 km
)

# ค้นหาห้างสรรพสินค้า
malls = await LocationIntelligence.search_nearby_google(
    location_name="Asok BTS",
    place_type="shopping_mall",
    radius=1500  # 1.5 km
)
```

**รองรับ place_type:**
- `"lodging"` - โรงแรม
- `"restaurant"` - ร้านอาหาร
- `"tourist_attraction"` - สถานที่ท่องเที่ยว
- `"shopping_mall"` - ห้างสรรพสินค้า
- `"cafe"` - คาเฟ่
- `"bar"` - บาร์
- `"spa"` - สปา
- และอื่นๆ ตาม [Google Places API Types](https://developers.google.com/maps/documentation/places/web-service/supported_types)

---

### 3. **Place Details** - ข้อมูลละเอียดของสถานที่
ดึงข้อมูลเต็มของสถานที่โดยใช้ Google Place ID

```python
details = await LocationIntelligence.get_place_details_google(
    place_id="ChIJgUSJZM2e4jAREnHS1rSuWRk"
)

# ผลลัพธ์:
# {
#   "name": "Siam Discovery",
#   "formatted_address": "194 Rama I Rd, Bangkok 10330",
#   "formatted_phone_number": "02 658 1000",
#   "website": "https://www.siamdiscovery.co.th/",
#   "rating": 4.4,
#   "user_ratings_total": 19310,
#   "opening_hours": {
#     "open_now": True,
#     "weekday_text": [...]
#   },
#   "reviews": [...],
#   "photos": [...]
# }
```

---

### 4. **Area Recommendations** - คำแนะนำแบบครบวงจร
ค้นหาสถานที่ทุกประเภทรอบๆ พื้นที่ในคราวเดียว (parallel search)

```python
recommendations = await LocationIntelligence.get_area_recommendations(
    location_name="Siam Paragon",
    radius=3000  # 3 km
)

# ผลลัพธ์:
# {
#   "hotels": [top 5 hotels],
#   "restaurants": [top 5 restaurants],
#   "attractions": [top 5 attractions],
#   "shopping": [top 5 shopping malls]
# }
```

---

## 🔗 Integration with Agent

### ใช้ใน Agent สำหรับ:

#### 1. **Hotel Search Near Landmarks**
```python
# ใน _execute_call_search() สำหรับ accommodation
if segment.requirements.get("location") == "Siam Paragon":
    # ใช้ Google Maps แทน Amadeus
    hotels = await agent_intelligence.location_intel.find_hotels_near_landmark(
        landmark_name="Siam Paragon",
        radius=2000
    )
```

#### 2. **Proactive Recommendations**
```python
# ใน generate_response() เพิ่มคำแนะนำ
if destination == "Siam Paragon":
    recommendations = await agent_intelligence.location_intel.get_area_recommendations(
        location_name="Siam Paragon",
        radius=2000
    )
    
    # แนะนำร้านอาหารใกล้เคียง
    if recommendations["restaurants"]:
        response += "\n\n💡 ร้านอาหารแนะนำใกล้เคียง:\n"
        for rest in recommendations["restaurants"][:3]:
            response += f"- {rest['name']} ({rest['rating']}⭐)\n"
```

#### 3. **Enhanced Location Context**
```python
# ใน _execute_create_itinerary()
if dest_info.get("is_landmark"):
    # ดึงข้อมูลพื้นที่รอบๆ landmark
    area_info = await agent_intelligence.location_intel.get_area_recommendations(
        location_name=dest_info["landmark_name"],
        radius=2000
    )
    
    # บันทึกไว้ใน session metadata สำหรับใช้ภายหลัง
    session.metadata["area_recommendations"] = area_info
```

---

## 📊 ข้อมูลที่ได้จาก Google Maps

### ข้อมูลพื้นฐาน (Nearby Search)
- ✅ `name` - ชื่อสถานที่
- ✅ `rating` - คะแนนเฉลี่ย (0-5)
- ✅ `user_ratings_total` - จำนวนรีวิว
- ✅ `vicinity` - ที่อยู่แบบสั้น
- ✅ `place_id` - Google Place ID (สำหรับดึงข้อมูลเพิ่ม)
- ✅ `types` - ประเภทสถานที่
- ✅ `geometry` - พิกัด (lat, lng)
- ✅ `price_level` - ระดับราคา (0-4)
- ✅ `opening_hours.open_now` - เปิดอยู่หรือไม่

### ข้อมูลละเอียด (Place Details)
- ✅ `formatted_address` - ที่อยู่เต็ม
- ✅ `formatted_phone_number` - เบอร์โทรศัพท์
- ✅ `website` - เว็บไซต์
- ✅ `opening_hours.weekday_text` - เวลาเปิด-ปิดแต่ละวัน
- ✅ `reviews` - รีวิวจากผู้ใช้
- ✅ `photos` - รูปภาพ (photo references)
- ✅ `url` - Google Maps URL

---

## 🎯 Use Cases

### Use Case 1: จองโรงแรมใกล้ Landmark
```
User: "หาโรงแรมใกล้สยามพารากอน"

Agent:
1. ตรวจจับ: "สยามพารากอน" = landmark
2. เรียก: find_hotels_near_landmark("Siam Paragon", radius=2000)
3. แสดงผล: โรงแรม 10 แห่งใกล้สยามพารากอน พร้อมคะแนนรีวิว
```

### Use Case 2: แนะนำร้านอาหารในพื้นที่
```
User: "แนะนำร้านอาหารใกล้วัดพระแก้ว"

Agent:
1. เรียก: search_nearby_google("Grand Palace", "restaurant", 1000)
2. แสดงผล: ร้านอาหาร 5 ร้านที่ได้คะแนนสูงสุด
```

### Use Case 3: สำรวจพื้นที่ก่อนเดินทาง
```
User: "บอกหน่อยว่ารอบๆ Asok มีอะไรบ้าง"

Agent:
1. เรียก: get_area_recommendations("Asok BTS", radius=2000)
2. แสดงผล:
   - โรงแรม 5 แห่ง
   - ร้านอาหาร 5 ร้าน
   - สถานที่ท่องเที่ยว 5 แห่ง
   - ห้างสรรพสินค้า 5 แห่ง
```

---

## ⚙️ Configuration

### ต้องการ Google Maps API Key
```python
# ใน .env หรือ config
GOOGLE_MAPS_API_KEY=your_api_key_here
```

### เปิดใช้งาน APIs ที่จำเป็น:
1. **Geocoding API** - แปลงชื่อสถานที่เป็นพิกัด
2. **Places API (Nearby Search)** - ค้นหาสถานที่รอบๆ
3. **Places API (Place Details)** - ดึงข้อมูลละเอียด

---

## 🚀 Performance & Optimization

### Caching Strategy
- ✅ Geocoding results ถูก cache ใน memory
- ✅ Nearby search results cache 5 นาที (แนะนำ)
- ✅ Place details cache 1 ชั่วโมง (แนะนำ)

### Parallel Search
```python
# ค้นหาหลายประเภทพร้อมกัน (ใช้ asyncio.gather)
tasks = [
    search_nearby_google(location, "lodging", radius),
    search_nearby_google(location, "restaurant", radius),
    search_nearby_google(location, "tourist_attraction", radius),
]
hotels, restaurants, attractions = await asyncio.gather(*tasks)
```

### Rate Limiting
- Google Maps API มี rate limit
- แนะนำ: จำกัดการเรียก API ไม่เกิน 10 requests/second
- ใช้ caching เพื่อลด API calls

---

## 📝 Example Integration

### ตัวอย่างการใช้ใน Agent

```python
# ใน agent.py - _execute_call_search()
async def _execute_call_search(self, session, payload, action_log):
    slot_name = payload.get("slot")
    segment = self._get_segment(session, slot_name, segment_index)
    
    if slot_name == "accommodation":
        location = segment.requirements.get("location")
        
        # ตรวจสอบว่าเป็น landmark หรือไม่
        loc_info = LocationIntelligence.resolve_location(location, "hotel")
        
        if loc_info.get("is_landmark"):
            # ใช้ Google Maps สำหรับ landmark
            logger.info(f"Using Google Maps for landmark: {location}")
            hotels = await LocationIntelligence.find_hotels_near_landmark(
                landmark_name=location,
                radius=2000,
                max_results=10
            )
            
            # แปลงเป็น StandardizedItem format
            segment.options_pool = self._convert_google_hotels_to_options(hotels)
        else:
            # ใช้ Amadeus สำหรับเมืองปกติ
            results = await aggregator.search_and_normalize(
                request_type="hotel",
                location=location,
                ...
            )
            segment.options_pool = results
```

---

## 🎉 Benefits

| Feature | Before | After |
|---------|--------|-------|
| **Landmark Hotels** | ไม่สามารถค้นหาได้แม่นยำ | ค้นหาได้แม่นยำภายใน 2km |
| **Area Context** | ไม่มีข้อมูลรอบๆ | มีข้อมูลครบ (โรงแรม, ร้านอาหาร, ฯลฯ) |
| **User Reviews** | ไม่มี | มีคะแนนและรีวิวจาก Google |
| **Real-time Data** | Static | Real-time จาก Google Maps |
| **Recommendations** | Generic | Context-aware และแม่นยำ |

---

**Created by:** Google Maps Intelligence Integration  
**Date:** January 10, 2026  
**Version:** 1.0.0
