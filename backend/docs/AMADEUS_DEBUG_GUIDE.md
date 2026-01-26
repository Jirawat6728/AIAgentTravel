# Amadeus API Debugging Guide

## ปัญหาที่พบบ่อย: ไม่พบข้อมูล (No Results Found)

### สาเหตุหลัก

1. **วันที่ห่างเกินไป (Date Too Far in Future)**
   - Amadeus API รองรับการค้นหาสูงสุด **~11 เดือน** (330 วัน) จากวันปัจจุบัน
   - หากวันที่ห่างเกินไป Amadeus อาจไม่มีข้อมูล
   - **ตัวอย่าง:** วันที่ 5-8 กุมภาพันธ์ 2026 (ห่างจากปัจจุบัน ~10 วัน) - ควรมีข้อมูล

2. **IATA Codes ไม่ถูกต้อง**
   - Origin/Destination อาจไม่ resolve เป็น IATA code ที่ถูกต้อง
   - ตรวจสอบ logs: `📍 IATA Resolution: 'origin' → 'origin_code'`

3. **Route ไม่มีบริการ**
   - เส้นทางนั้นอาจไม่มีเที่ยวบิน/โรงแรมใน Amadeus database
   - ตรวจสอบว่า route มีการให้บริการจริง

4. **API Response Structure**
   - Amadeus อาจ return empty `data: []` แม้ status code เป็น 200
   - ตรวจสอบ `meta.count` ใน response

### การตรวจสอบ

#### 1. ตรวจสอบ Logs

```bash
# ดู logs สำหรับ Amadeus search
grep "Amadeus Flight Search" logs/app.log
grep "No flights found" logs/app.log
grep "IATA Resolution" logs/app.log
```

#### 2. ตรวจสอบ Date Range

```python
from datetime import datetime
search_date = datetime.strptime("2026-02-05", "%Y-%m-%d")
today = datetime.now()
days_ahead = (search_date - today).days
max_days = 330  # ~11 months

if days_ahead > max_days:
    print(f"⚠️ Date is {days_ahead} days ahead (max: {max_days})")
```

#### 3. ตรวจสอบ IATA Codes

- ดู logs: `📍 IATA Resolution: 'Bangkok' → 'BKK'`
- หากเป็น `None` หรือ `FAILED` → ปัญหาที่ geocoding/IATA resolution

#### 4. ตรวจสอบ Amadeus API Response

```python
# ตรวจสอบ response structure
response = resp.json()
print(f"Status: {resp.status_code}")
print(f"Keys: {list(response.keys())}")
print(f"Meta: {response.get('meta', {})}")
print(f"Data count: {len(response.get('data', []))}")
print(f"Warnings: {response.get('warnings', [])}")
print(f"Errors: {response.get('errors', [])}")
```

### การแก้ไขที่ทำแล้ว

1. ✅ **Date Validation**
   - เพิ่มการตรวจสอบวันที่ก่อน search
   - Warning หากวันที่ห่างเกิน 330 วัน
   - Log วันที่ในอดีต

2. ✅ **Enhanced Error Messages**
   - แสดงสาเหตุที่เป็นไปได้เมื่อไม่พบข้อมูล
   - รวม date warning ใน error message
   - แสดง diagnostics information

3. ✅ **Response Structure Validation**
   - ตรวจสอบว่า response เป็น dict
   - ตรวจสอบ `warnings` และ `errors` ใน response
   - Log `meta.count` สำหรับ debugging

4. ✅ **Better Logging**
   - Log IATA code resolution
   - Log search parameters
   - Log fallback attempts
   - Log full response structure (debug level)

### Fallback Mechanisms

1. **Date Fallback**
   - Flights: ลอง ±1, ±2 วัน
   - Hotels: ลอง ±1 วัน (check-in/check-out)

2. **Location Fallback**
   - Hotels: ลอง cityCode → geocode → airport IATA
   - Flights: ลอง IATA → geocode → airport search

3. **Cabin Class Fallback**
   - หากไม่พบด้วย cabin_class ที่ระบุ → ลอง search โดยไม่ระบุ cabin_class

### วิธี Debug

#### Step 1: ตรวจสอบ Logs
```bash
# ดู Amadeus search logs
tail -f logs/app.log | grep -i "amadeus\|flight\|hotel"
```

#### Step 2: ตรวจสอบ Date
- วันที่อยู่ในช่วง 0-330 วันจากวันนี้หรือไม่?
- วันที่อยู่ในอดีตหรือไม่?

#### Step 3: ตรวจสอบ IATA Codes
- Origin/Destination resolve เป็น IATA code หรือไม่?
- IATA codes ถูกต้องหรือไม่? (3 ตัวอักษร, uppercase)

#### Step 4: ตรวจสอบ API Response
- Status code = 200?
- `data` array มีข้อมูลหรือไม่?
- มี `warnings` หรือ `errors` หรือไม่?

#### Step 5: Test ด้วย Amadeus Test API
```bash
# Test flight search
curl -X GET "https://test.api.amadeus.com/v2/shopping/flight-offers?originLocationCode=BKK&destinationLocationCode=HKT&departureDate=2026-02-05&adults=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Recommendations

1. **สำหรับวันที่ห่างเกินไป:**
   - แนะนำให้ผู้ใช้ลองวันที่ใกล้กว่านี้
   - หรือรอให้ Amadeus มีข้อมูล (มักจะ update ทุก 1-2 สัปดาห์)

2. **สำหรับ IATA resolution failures:**
   - ตรวจสอบ Google Maps API key
   - ตรวจสอบว่า location name ถูกต้อง
   - ลองใช้ IATA code โดยตรงแทน city name

3. **สำหรับ empty results:**
   - ตรวจสอบว่า route มีการให้บริการจริง
   - ลอง search ด้วยวันที่อื่น
   - ตรวจสอบ Amadeus API status

### Related Files

- `backend/app/services/travel_service.py` - Main Amadeus integration
- `backend/app/services/mcp_server.py` - MCP tools for Amadeus
- `backend/app/services/data_aggregator.py` - Data normalization
- `backend/app/services/location_service.py` - IATA code resolution
