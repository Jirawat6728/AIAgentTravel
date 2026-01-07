# Location Service Documentation

โมดูล `location_service.py` เป็น Production-Grade Service ที่ผสานรวม Google Maps Geocoding API กับ Amadeus Travel API เพื่อให้ระบบสามารถค้นหาสถานที่ กิจกรรม และบริการรถรับส่งได้อย่างอัตโนมัติ

## Features

### 1. Geocoding Function
แปลงชื่อสถานที่ (เช่น "Eiffel Tower", "Grand Palace Bangkok") เป็นพิกัดละติจูด/ลองจิจูด และที่อยู่แบบทางการ

### 2. Amadeus Activities Integration
ค้นหากิจกรรมและทัวร์รอบสถานที่ที่ระบุ โดยใช้พิกัดจาก Google Maps

### 3. Amadeus Transfer Integration
ค้นหาตัวเลือกรถรับส่งระหว่างสองจุด โดยใช้ที่อยู่แบบทางการจาก Google Maps

### 4. Smart IATA Code Conversion
แปลงชื่อเมืองเป็น IATA Airport Code (เช่น Bangkok → BKK) โดยใช้ Amadeus Airport & City Search API

## Installation

### 1. Install Dependencies

```bash
pip install googlemaps==4.10.0
pip install amadeus==9.0.0
```

### 2. Configure Environment Variables

เพิ่มในไฟล์ `.env`:

```env
# Google Maps API Key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Amadeus API Credentials
AMADEUS_API_KEY=your_amadeus_api_key
AMADEUS_API_SECRET=your_amadeus_api_secret
AMADEUS_ENV=test  # or "production"
```

## Usage Examples

### Basic Geocoding

```python
from app.services.location_service import get_location_service

service = get_location_service()

# Geocode a place
location = await service.geocode("Eiffel Tower")
print(f"Coordinates: {location.lat}, {location.lng}")
print(f"Address: {location.formatted_address}")
```

### Search Activities Near Location

```python
# Geocode first
location = await service.geocode("Grand Palace Bangkok")

# Search activities within 5km radius
activities = await service.search_activities(
    location=location,
    radius=5000,  # meters
    max_results=10
)

for activity in activities:
    print(f"- {activity.name} (Rating: {activity.rating})")
```

### Search Transfer Options

```python
# Get transfer options between two places
start_loc, end_loc, transfers = await service.get_transfer_options(
    start_place="Suvarnabhumi Airport",
    end_place="Grand Palace Bangkok",
    date="2024-01-15"  # optional
)

print(f"From: {start_loc.formatted_address}")
print(f"To: {end_loc.formatted_address}")
for transfer in transfers:
    print(f"- {transfer.name} ({transfer.vehicle_type})")
```

### Convert City to IATA Code

```python
# Convert city name to IATA airport code
iata_code = await service.city_to_iata("Bangkok")
print(f"Bangkok → {iata_code}")  # Output: BKK
```

### Convenience Methods

```python
# One-call: Geocode + Search Activities
location, activities = await service.get_location_with_activities(
    place_name="Eiffel Tower",
    radius=5000,
    max_activities=10
)
```

## API Reference

### `LocationService.geocode(place_name: str, language: str = "th") -> LocationInfo`

แปลงชื่อสถานที่เป็นพิกัดและที่อยู่

**Parameters:**
- `place_name`: ชื่อสถานที่ (เช่น "Eiffel Tower")
- `language`: รหัสภาษา (default: "th")

**Returns:** `LocationInfo` object with:
- `lat`: ละติจูด
- `lng`: ลองจิจูด
- `formatted_address`: ที่อยู่แบบทางการ
- `place_id`: Google Place ID
- `city_name`: ชื่อเมือง
- `country_code`: รหัสประเทศ

**Raises:** `AgentException` if geocoding fails

### `LocationService.search_activities(location: LocationInfo, radius: int = 5000, max_results: int = 10) -> List[ActivityResult]`

ค้นหากิจกรรมรอบสถานที่

**Parameters:**
- `location`: LocationInfo object
- `radius`: รัศมีการค้นหา (เมตร, default: 5000)
- `max_results`: จำนวนผลลัพธ์สูงสุด (default: 10)

**Returns:** List of `ActivityResult` objects

### `LocationService.search_transfers(start_location: str, end_location: str, date: Optional[str] = None) -> List[TransferResult]`

ค้นหาตัวเลือกรถรับส่ง

**Parameters:**
- `start_location`: ที่อยู่จุดรับ
- `end_location`: ที่อยู่จุดส่ง
- `date`: วันที่ (YYYY-MM-DD, optional)

**Returns:** List of `TransferResult` objects

### `LocationService.city_to_iata(city_name: str) -> Optional[str]`

แปลงชื่อเมืองเป็น IATA Code

**Parameters:**
- `city_name`: ชื่อเมือง

**Returns:** IATA code (เช่น "BKK") หรือ None ถ้าไม่พบ

## Error Handling

โมดูลนี้ใช้ `AgentException` สำหรับ error handling:

```python
from app.core.exceptions import AgentException

try:
    location = await service.geocode("Invalid Place Name")
except AgentException as e:
    print(f"Error: {e}")
```

## Integration with Travel Agent

โมดูลนี้สามารถใช้ร่วมกับ Travel Agent Engine ได้:

```python
# In agent.py or similar
from app.services.location_service import get_location_service

location_service = get_location_service()

# When user mentions a place
location = await location_service.geocode(user_mentioned_place)
activities = await location_service.search_activities(location)

# Add activities to trip plan
```

## Production Considerations

1. **API Rate Limits**: Google Maps และ Amadeus มี rate limits ควรใช้ caching สำหรับคำขอที่ซ้ำกัน
2. **Error Handling**: ทุก method มี try-except และ return empty lists/None แทนการ crash
3. **Async Support**: ทุก method เป็น async เพื่อไม่ block FastAPI event loop
4. **Logging**: ใช้ structured logging พร้อม context (session_id, user_id)

## Testing

รันตัวอย่างการใช้งาน:

```bash
cd backend
python examples/location_service_example.py
```

## Notes

- Amadeus API methods อาจแตกต่างกันตาม SDK version โมดูลนี้รองรับหลาย methods และจะ fallback อัตโนมัติ
- Google Maps API ต้องเปิดใช้งาน Geocoding API ใน Google Cloud Console
- Amadeus API ต้องมี credentials ที่ถูกต้องและ environment (test/production) ที่เหมาะสม

