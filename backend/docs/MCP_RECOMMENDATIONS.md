# MCP เพิ่มเติมเพื่อความแม่นยำขั้นสุดในการวางแผน

เอกสารนี้รวบรวม MCP (Model Context Protocol) ที่แนะนำสำหรับการวางแผนท่องเที่ยว เพื่อเพิ่มความแม่นยำของข้อมูลและประสบการณ์ผู้ใช้

---

## MCP ที่ใช้อยู่แล้วในโปรเจกต์

| MCP | เครื่องมือหลัก | ใช้สำหรับ |
|-----|----------------|-----------|
| **Amadeus MCP** | search_flights, search_hotels, search_transfers, search_activities | เที่ยวบิน ที่พัก รถรับส่ง กิจกรรม |
| **Google Maps MCP** | geocode_location, find_nearest_airport, plan_route, plan_route_with_waypoints, search_nearby_places, get_place_details, compare_transport_modes | พิกัด สนามบิน เส้นทาง จุดแวะ ที่พักใกล้จุดสนใจ |
| **Weather MCP** (Open-Meteo) | get_weather_forecast, get_destination_timezone | สภาพอากาศปลายทาง เวลาท้องถิ่น |

---

## MCP แนะนำเพิ่มเติม (สำหรับอนาคต / integration)

### 1. Expedia Travel Recommendations MCP
- **ที่มา**: [ExpediaGroup/expedia-travel-recommendations-mcp](https://github.com/ExpediaGroup/expedia-travel-recommendations-mcp)
- **ฟีเจอร์**: Hotel, Flight, Activity, Car rental recommendations
- **โปรโตคอล**: stdio, streamable-http (POST /expedia/hotels, /flights, /activities, /cars)
- **ข้อกำหนด**: Python 3.11+, `EXPEDIA_API_KEY`
- **ประโยชน์**: ทางเลือก/เสริม Amadeus สำหรับที่พักและเที่ยวบิน จากแหล่งข้อมูลอีกแห่ง

### 2. Xweather MCP Server
- **ที่มา**: [Xweather MCP Server](https://www.xweather.com/docs/mcp-server)
- **ฟีเจอร์**: สภาพอากาศอดีต/ปัจจุบัน/อนาคต แบบ conversational
- **ประโยชน์**: ข้อมูลสภาพอากาศเชิงพาณิชย์ แม่นยำสูง สำหรับทริปสำคัญ

### 3. Time MCP Server
- **ที่มา**: [MCP Repository - Time](https://mcprepository.com/modelcontextprotocol/time)
- **เครื่องมือ**: get_current_time(timezone), convert_time(datetime, from_tz, to_tz)
- **ฟีเจอร์**: แปลงเวลา IANA timezone (America/New_York, Asia/Bangkok ฯลฯ)
- **ประโยชน์**: แสดงเวลาเที่ยวบิน/เช็คอินเป็นเวลาท้องถิ่นปลายทาง (โปรเจกต์มี get_destination_timezone อยู่แล้ว)

### 4. Open-Meteo (ใช้แล้วในโปรเจกต์)
- **API**: https://api.open-meteo.com (ฟรี ไม่ต้องใช้ API key)
- **ใช้ใน**: Weather MCP – get_weather_forecast, get_destination_timezone
- **ประโยชน์**: สภาพอากาศและ timezone ปลายทาง สำหรับแนะนำการจัดกระเป๋าและช่วงเวลาเดินทาง

### 5. Weather MCP (open-weather / community)
- **ที่มา**: [open-weather](https://www.open-mcp.org/servers/open-weather), [weather-mcp](https://github.com/weather-mcp/weather-mcp)
- **ฟีเจอร์**: พยากรณ์อากาศ, การแจ้งเตือน, คุณภาพอากาศ (บางตัวไม่ต้องใช้ API key)
- **ประโยชน์**: ทางเลือกหรือเสริม Open-Meteo

### 6. Currency / Exchange Rate MCP (แนวคิด)
- **ฟีเจอร์**: อัตราแลกเปลี่ยน (THB ↔ สกุลปลายทาง) สำหรับแสดงราคาเป็นบาท
- **ประโยชน์**: แสดงราคาที่พัก/กิจกรรมเป็นบาทเมื่อปลายทางใช้สกุลอื่น

### 7. Visa / Travel Requirements MCP (แนวคิด)
- **ฟีเจอร์**: ข้อกำหนดวีซ่า สุขภาพ การเข้าเมือง ตามประเทศต้นทาง–ปลายทาง
- **ประโยชน์**: เตือนและแนะนำก่อนจอง (โปรเจกต์มี visa_warning ใน flight card อยู่แล้ว)

---

## สรุปการใช้งานใน Agent

- **วางแผนเส้นทาง**: Google Maps MCP (plan_route, plan_route_with_waypoints)
- **ค้นหาเที่ยวบิน/ที่พัก/รถรับส่ง**: Amadeus MCP
- **ความแม่นยำสถานที่**: Google Maps MCP (geocode, find_nearest_airport, search_nearby_places)
- **สภาพอากาศปลายทาง**: Weather MCP (get_weather_forecast)
- **เวลาท้องถิ่นปลายทาง**: Weather MCP (get_destination_timezone)

การเพิ่ม MCP ภายนอก (เช่น Expedia, Xweather) สามารถทำได้โดยรัน MCP server แยกและเชื่อมต่อผ่าน stdio หรือ streamable-http ตามมาตรฐาน MCP.
