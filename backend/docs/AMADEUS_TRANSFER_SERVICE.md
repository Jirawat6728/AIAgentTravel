# Amadeus Transfer Service Documentation

โมดูล `amadeus_client.py` และ `google_maps_client.py` เป็น Production-Grade Services สำหรับจัดการการค้นหาและจองบริการรถรับส่ง (Transfers) และกิจกรรมทางน้ำ (Water Activities) ผ่าน Amadeus API

## Features

### 1. Ground Transfer Search
- ค้นหาตัวเลือกรถรับส่ง: Private, Taxi, และ Airport Rail
- รองรับการค้นหาจาก IATA Airport Code ไปยังที่อยู่ปลายทาง
- จัดหมวดหมู่และจัดรูปแบบข้อมูลให้เป็นมาตรฐาน

### 2. Water Activities Search
- ค้นหากิจกรรมทางน้ำ (Boat Tours, Cruises, Ferries)
- กรองผลลัพธ์อัตโนมัติตามคำสำคัญ (boat, cruise, ferry, etc.)
- ใช้พิกัดละติจูด/ลองจิจูดเพื่อค้นหาในรัศมี่ที่กำหนด

### 3. Location Resolution
- แปลงที่อยู่หรือชื่อสถานที่เป็นพิกัดและข้อมูลที่จำเป็น
- ค้นหา IATA Airport Code ที่ใกล้ที่สุดอัตโนมัติ
- รองรับการทำงานร่วมกับ Amadeus Transfer API

## Installation

### Dependencies

```bash
pip install googlemaps==4.10.0
pip install amadeus==9.0.0
```

### Environment Variables

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

### 1. Get Location Information for Transfer

```python
from app.services.google_maps_client import get_location_for_transfer

# Get location info including IATA code
location_info = await get_location_for_transfer("Grand Palace Bangkok")

print(f"Address: {location_info['formatted_address']}")
print(f"Coordinates: {location_info['latitude']}, {location_info['longitude']}")
print(f"Nearest Airport: {location_info['airport_name']} ({location_info['iata_code']})")
```

### 2. Search Ground Transfers

```python
from app.services.amadeus_client import (
    get_amadeus_transfer_service,
    GroundTransferRequest
)
from datetime import datetime, timedelta

service = get_amadeus_transfer_service()

# Create request
request = GroundTransferRequest(
    start_location_code="BKK",  # IATA code
    end_address_line="Grand Palace, Bangkok",
    start_date_time=(datetime.now() + timedelta(days=1)).isoformat(),
    passengers=2
)

# Search transfers
response = await service.search_ground_transfers(request)

# Access categorized results
print(f"Private transfers: {len(response.private_transfers)}")
print(f"Taxi transfers: {len(response.taxi_transfers)}")
print(f"Rail transfers: {len(response.rail_transfers)}")

# Access individual options
for option in response.private_transfers:
    print(f"- {option.name} ({option.vehicle_type})")
    print(f"  Price: {option.price}")
```

### 3. Search Water Activities

```python
from app.services.amadeus_client import (
    get_amadeus_transfer_service,
    WaterActivityRequest
)

service = get_amadeus_transfer_service()

# Create request with coordinates
request = WaterActivityRequest(
    latitude=7.8804,  # Phuket
    longitude=98.3923,
    radius=10000  # 10km
)

# Search water activities
response = await service.search_water_activities(request)

print(f"Found {response.total_count} water activities")
for activity in response.activities:
    print(f"- {activity.name}")
    if activity.rating:
        print(f"  Rating: {activity.rating}/5")
```

### 4. Complete Workflow

```python
from app.services.google_maps_client import get_location_for_transfer
from app.services.amadeus_client import (
    get_amadeus_transfer_service,
    GroundTransferRequest,
    WaterActivityRequest
)
from datetime import datetime, timedelta

# Step 1: Get location information
location = await get_location_for_transfer("Eiffel Tower")

# Step 2: Search transfers (if airport code available)
if location.get('iata_code'):
    service = get_amadeus_transfer_service()
    transfer_request = GroundTransferRequest(
        start_location_code=location['iata_code'],
        end_address_line=location['formatted_address'],
        start_date_time=(datetime.now() + timedelta(days=1)).isoformat(),
        passengers=2
    )
    transfer_response = await service.search_ground_transfers(transfer_request)
    print(f"Transfer options: {transfer_response.total_count}")

# Step 3: Search water activities
activity_request = WaterActivityRequest(
    latitude=location['latitude'],
    longitude=location['longitude'],
    radius=5000
)
activity_response = await service.search_water_activities(activity_request)
print(f"Water activities: {activity_response.total_count}")
```

## API Reference

### `get_location_for_transfer(address_string: str, language: str = "th") -> Dict[str, Any]`

แปลงที่อยู่หรือชื่อสถานที่เป็นข้อมูลที่จำเป็นสำหรับ Transfer

**Parameters:**
- `address_string`: ที่อยู่หรือชื่อสถานที่
- `language`: รหัสภาษา (default: "th")

**Returns:** Dictionary with:
- `latitude`: float
- `longitude`: float
- `formatted_address`: str
- `iata_code`: str (nearest airport IATA code)
- `airport_name`: str
- `airport_distance`: float (meters)
- `place_id`: str
- `city_name`: str
- `country_code`: str

### `AmadeusTransferService.search_ground_transfers(request: GroundTransferRequest) -> TransferSearchResponse`

ค้นหาตัวเลือกรถรับส่ง

**Parameters:**
- `request`: GroundTransferRequest with:
  - `start_location_code`: IATA airport code (e.g., "BKK")
  - `end_address_line`: Destination address
  - `start_date_time`: ISO 8601 datetime string
  - `passengers`: Number of passengers (1-9)

**Returns:** TransferSearchResponse with:
- `options`: All transfer options
- `private_transfers`: Private transfer options
- `taxi_transfers`: Taxi options
- `rail_transfers`: Airport rail options
- `total_count`: Total number of options

### `AmadeusTransferService.search_water_activities(request: WaterActivityRequest) -> WaterActivityResponse`

ค้นหากิจกรรมทางน้ำ

**Parameters:**
- `request`: WaterActivityRequest with:
  - `latitude`: Latitude
  - `longitude`: Longitude
  - `radius`: Search radius in meters (100-50000)

**Returns:** WaterActivityResponse with:
- `activities`: List of water activities
- `total_count`: Total number of activities

## Data Models

### TransferOption
- `id`: Transfer option ID
- `type`: "PRIVATE", "TAXI", "RAIL", or "SHARED"
- `name`: Transfer name
- `vehicle_type`: Vehicle type (e.g., "SEDAN", "SUV")
- `price`: Pricing information dict
- `currency`: Currency code
- `duration`: Estimated duration
- `distance`: Distance in kilometers
- `provider`: Service provider name

### WaterActivity
- `id`: Activity ID
- `name`: Activity name
- `description`: Activity description
- `category`: "WATER"
- `price`: Pricing information
- `rating`: Rating (0-5)
- `location`: Location coordinates

## Error Handling

### AmadeusException

```python
from app.core.exceptions import AmadeusException

try:
    response = await service.search_ground_transfers(request)
except AmadeusException as e:
    print(f"Amadeus API error: {e}")
```

### Common Error Codes

- **400 Bad Request**: Invalid parameters (e.g., invalid IATA code, date format)
- **401 Unauthorized**: Invalid API credentials
- **404 Not Found**: No transfer options found

## Production Considerations

1. **API Rate Limits**: Amadeus และ Google Maps มี rate limits ควรใช้ caching
2. **Error Handling**: ทุก method มี try-except และ return empty responses แทนการ crash
3. **Async Support**: ทุก method เป็น async เพื่อไม่ block FastAPI event loop
4. **Logging**: ใช้ structured logging พร้อม context
5. **Rail Detection**: ระบบจะตรวจจับ "RAIL" ใน vehicle type อัตโนมัติ

## Testing

รันตัวอย่างการใช้งาน:

```bash
cd backend
python examples/amadeus_transfer_example.py
```

## Integration with Travel Agent

```python
# In agent.py or similar
from app.services.google_maps_client import get_location_for_transfer
from app.services.amadeus_client import (
    get_amadeus_transfer_service,
    GroundTransferRequest
)

# When user requests transfer
location = await get_location_for_transfer(user_destination)
service = get_amadeus_transfer_service()

request = GroundTransferRequest(
    start_location_code=location['iata_code'],
    end_address_line=location['formatted_address'],
    start_date_time=transfer_datetime,
    passengers=num_passengers
)

transfers = await service.search_ground_transfers(request)
# Add to trip plan
```

## Notes

- Amadeus Transfer API ต้องใช้ IATA Airport Code สำหรับจุดเริ่มต้น
- Google Maps API ต้องเปิดใช้งาน Geocoding และ Places API
- Water activities จะถูกกรองอัตโนมัติตามคำสำคัญ (boat, cruise, ferry, etc.)
- Rail transfers จะถูกตรวจจับจาก vehicle type ที่มีคำว่า "RAIL", "TRAIN", หรือ "METRO"

