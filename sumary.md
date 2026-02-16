# 📋 เอกสารสรุปโปรเจกต์ AI Travel Agent

## 📌 ภาพรวมโปรเจกต์

**AI Travel Agent** เป็นแอปพลิเคชันวางแผนการเดินทางอัจฉริยะที่ใช้ AI (Gemini LLM) ในการช่วยผู้ใช้ค้นหาและจองเที่ยวบิน โรงแรม และบริการการเดินทางอื่นๆ ผ่านการสนทนาแบบธรรมชาติ

### ข้อมูลพื้นฐาน
- **ชื่อโปรเจกต์**: AI Travel Agent
- **เวอร์ชัน**: 2.1.0
- **สถาปัตยกรรม**: Two-Pass ReAct Loop + Multi-Model Intelligence
- **Frontend**: React + Vite (ภาษาไทย)
- **Backend**: FastAPI + Python
- **ฐานข้อมูล**: MongoDB (หลัก), Redis (เสริม)
- **Intelligence**: Weighted Sum Model + RL + Data Normalization
- **การค้นหา/จุดหมาย**: ใช้ผ่าน AI Agent ในแชท (ไม่มี search bar / shortcut หมวดหมู่บนโฮม)

---

## 🏗️ สถาปัตยกรรมระบบ

### โครงสร้างโปรเจกต์

```
AITravelAgent/
├── frontend/                           # React Frontend (ภาษาไทย)
│   ├── src/
│   │   ├── pages/         # หน้าหลัก (home, chat, auth, profile, bookings, search, explore, settings)
│   │   ├── components/    # UI (AppHeader, HomeHeader, PlanChoiceCard*, TripSummaryUI, SlotCards, NotificationPanel)
│   │   ├── config/        # firebase.js
│   │   └── utils/         # userDataManager, textCorrection
│   └── package.json
│
├── backend/               # FastAPI Backend
│   ├── app/
│   │   ├── api/          # chat, auth, travel, booking, notification, admin, mcp, monitoring, options_cache, amadeus_viewer, diagnostics
│   │   ├── core/         # config, logging, exceptions, security, resilience, redis_cache
│   │   ├── engine/       # Agent logic & Intelligence
│   │   │   ├── agent.py                   # Main agent logic
│   │   │   ├── workflow_manager.py        # SlotManager (segment access สำหรับ Amadeus)
│   │   │   ├── data_normalization.py     # Min-Max Normalization
│   │   │   ├── reinforcement_learning.py # RL Expected Return
│   │   │   └── cost_tracker.py            # Cost tracking
│   │   ├── models/       # database, trip_plan, session, actions
│   │   ├── services/     # travel_service, llm, email, sms, mcp_server, data_aggregator, options_cache, omise, ...
│   │   └── storage/      # mongodb_storage, hybrid_storage, redis_storage, connection_manager
│   └── main.py
│
└── sumary.md              # เอกสารสรุปโปรเจกต์ (ไฟล์นี้)
```

### สถาปัตยกรรม Backend

#### 1. **Two-Pass ReAct Loop**
- **Phase 1: Controller (Think & Act)**
  - วิเคราะห์สถานะและข้อมูลจากผู้ใช้
  - ตัดสินใจเลือก Action ถัดไป
  - Execute actions พร้อม error handling
  - Loop สูงสุด 3 ครั้งจนกว่าจะได้ ASK_USER

- **Phase 2: Responder (Speak)**
  - อ่าน action_log
  - สร้างข้อความตอบกลับภาษาไทย
  - รายงานสิ่งที่ทำไปแล้ว
  - ถามข้อมูลที่ยังขาด

#### 2. **Storage Layer**
- **MongoDB**: เก็บข้อมูลหลัก (users, conversations, bookings)
- **Redis**: ใช้ใน workflow Amadeus — เก็บ raw data จาก Amadeus ต่อ session, เก็บช้อยที่เลือก (selections), และสถานะ workflow; เคลียร์เมื่อจองเสร็จหรือออกจาก flow
- **Repository Pattern**: ง่ายต่อการย้ายฐานข้อมูล

#### 2.1 **Workflow (Redis) — ขั้นตอนการวางแผนถึงจอง**
- **ขั้นตอน (steps)**: `planning` → `searching` → `selecting` → `summary` → `booking` → `done`
- **เก็บ raw data จาก Amadeus ที่ Redis**: หลัง CALL_SEARCH แต่ละ slot (เที่ยวบิน/ที่พัก/การเดินทาง) บันทึก raw response ลง `amadeus_raw:session:{session_id}:{slot_name}:{segment_index}` เพื่อใช้จัดช้อยและแก้ไขภายหลัง
- **จัดช้อยด้วยข้อมูลจาก Redis**: ข้อมูลที่ normalize แล้วเก็บใน options_cache; ใช้แสดงใน **PlanChoiceCard** แต่ละอัน (flight / hotel / transfer) ตาม slot_intent
- **เก็บช้อยที่เลือกไว้ที่ Redis**: ใช้ `options_cache.save_selected_option()` เก็บ selection ต่อ slot
- **เมื่อครบทุก slot**: แสดง **Trip Summary** (current_plan) และอัปเดต workflow step เป็น `summary`
- **เมื่อผู้ใช้แก้ไข**: โหลดข้อมูลจาก Redis (raw หรือ cached options) มาจัดใหม่และแสดง PlanChoiceCard ตามเดิม
- **เมื่อครบ workflow และผู้ใช้กดยืนยันการจอง**: เรียก `POST /api/booking/create` → จองเข้า **My Bookings**
- **การติดตาม workflow**: สถานะเก็บใน Redis ที่ `workflow:state:{session_id}` (step, slots_complete, updated_at)
- **เคลียร์ Redis เมื่อเสร็จสิ้น**: หลังจองสำเร็จ เรียก `options_cache.clear_session_all(session_id)` และ `workflow_state.clear_workflow(session_id)` เพื่อลบ options cache, raw Amadeus และ workflow state ของ session นั้น

#### 3. **Service Layer**
- **LLM Service**: Gemini AI integration
- **Travel Service (TravelOrchestrator)**: Flight, Hotel, Transfer, Activities, Popular Destinations, Rentals (ที่พักให้เช่า) — ใช้ **httpx** เรียก Amadeus REST โดยตรง (ไม่มีไฟล์ `amadeus_client.py` แล้ว)
- **การเรียกใช้ Amadeus**: อยู่ใน `backend/app/services/travel_service.py` เท่านั้น — (1) OAuth2 token ผ่าน `_get_amadeus_token()` POST ไป `{base}/v1/security/oauth2/token` (2) ค้นหาข้อมูลผ่าน `_amadeus_get(url, token, params)` เช่น Flight `/v2/shopping/flight-offers`, Hotel `/v3/shopping/hotel-offers`, Transfer `/v1/shopping/transfer-offers`, Activities `/v1/shopping/activities`, Locations `/v1/reference-data/locations` (3) ใช้ env `AMADEUS_SEARCH_API_KEY`/`AMADEUS_SEARCH_API_SECRET` และ `AMADEUS_BOOKING_*` สำหรับจอง (sandbox เท่านั้น)
- **Google Maps Client**: Geocoding, Places, Routes
- **MCP Server**: Model Context Protocol tools — Amadeus + Google Maps + Weather (Open-Meteo): search_flights, search_hotels, search_transfers, search_activities, geocode, airport, get_weather_forecast
- **Memory Service**: User preferences และ history
- **Email/SMS Service**: ยืนยันอีเมล, OTP เบอร์โทร
- **Payment Service**: Omise integration

#### 4. **Intelligence Engine Layer**
- **OptionSelector**: Multi-model ensemble scoring (Weighted Sum + RL + ML + DL)
- **DataNormalizer**: Min-Max normalization สำหรับ fair comparison
- **ReinforcementLearner**: Expected Return และ Reward Function
- **EnhancedDataPreprocessor**: Outlier detection, missing imputation, feature engineering
- **OptionRankingModel**: Machine Learning (Random Forest, Gradient Boosting)
- **DeepRankingNetwork**: Deep Learning Neural Networks
- **SlotManager** (workflow_manager.py): จัดการ segment/slot สำหรับ Amadeus (flights, hotels, transfers) เท่านั้น

---

## 🎯 ฟีเจอร์หลัก

### 1. **การสนทนากับ AI**
- สนทนาแบบธรรมชาติภาษาไทย
- เข้าใจบริบทและประวัติการสนทนา
- แนะนำแผนการเดินทางอัตโนมัติ
- รองรับการแก้ไขและเปลี่ยนแปลงแผน

### 2. **การค้นหาบริการการเดินทาง**

#### ✈️ เที่ยวบิน (Flights)
- ค้นหาเที่ยวบินขาไป-ขากลับ
- รองรับ One-way และ Round-trip
- ตัวเลือกชั้นที่นั่ง (Economy, Premium Economy, Business, First)
- ตัวเลือกบินตรง (Direct/Non-stop)
- ราคาและรายละเอียดเที่ยวบิน

#### 🏨 โรงแรม (Hotels)
- ค้นหาโรงแรมตามจุดหมายปลายทาง
- ค้นหาใกล้สถานที่ท่องเที่ยว
- รองรับการค้นหาตามย่าน/พื้นที่
- ข้อมูลราคา, ภาพ, และรีวิว

#### 🚗 การขนส่งภาคพื้นดิน (Transfers)
- รถรับส่งสนามบิน
- การเดินทางระหว่างเมือง
- รองรับหลายจุดแวะ (Waypoints)

#### 🎯 กิจกรรม (Activities)
- ทัวร์และกิจกรรมท่องเที่ยว
- แนะนำสถานที่ท่องเที่ยว

#### 🏠 ที่พักให้เช่า (Rentals)
- ค้นหาที่พักให้เช่า (ใช้ข้อมูลจาก Hotel API แยก label เป็น rentals)

#### 📍 จุดหมายยอดนิยม (Popular Destinations)
- รายการจุดหมายยอดนิยม (โซล, โตเกียว, เกาะสมุย ฯลฯ) พร้อมช่วงวันที่และราคาโดยประมาณ
- ใช้ผ่าน AI Agent ในแชท หรือ `GET /api/travel/popular-destinations`

### 3. **Frontend & Navigation**
- **HomePage**: ภาษาไทย, ไม่มี search bar / category shortcuts / Popular Destinations (ความสามารถทั้งหมดใช้ผ่านแชทกับ AI Agent)
- **AppHeader**: แสดงเฉพาะ "การจองของฉัน" + การแจ้งเตือน + ผู้ใช้ (ลบแท็บ การเดินทาง, สำรวจ, เที่ยวบิน, โรงแรม, ที่พักให้เช่า ออกแล้ว)
- **PlanChoiceCard**: แยกเป็น PlanChoiceCardFlights, PlanChoiceCardHotels, PlanChoiceCardTransfer + PlanChoiceCard หลัก

### 4. **ระบบการจอง (Booking System)**
- สร้างการจองจากแผนที่เลือก
- ระบบชำระเงินผ่าน Omise
- ติดตามสถานะการจอง
- ประวัติการจอง

### 5. **ระบบผู้ใช้ (User System)**
- ลงทะเบียน/เข้าสู่ระบบ
- Google Sign-In / Firebase Authentication
- ยืนยันอีเมล (ส่งลิงก์ยืนยัน, เปลี่ยนอีเมลแล้วส่งยืนยันใหม่; ยกเว้น admin@example.com)
- ต้องยืนยันอีเมลก่อนจึงจองได้ (ถ้าระบบเปิดใช้)
- เปลี่ยนเบอร์โทรแล้วส่ง OTP
- จัดการโปรไฟล์
- ประวัติการเดินทาง

### 6. **ระบบแจ้งเตือน (Notifications)**
- แจ้งเตือนการจองใหม่
- อัปเดตสถานะการจอง
- การแจ้งเตือนอื่นๆ

---

## 🔧 เทคโนโลยีที่ใช้

### Frontend
- **React 18.3.1**: UI Framework
- **Vite 5.4.3**: Build tool
- **React Google Maps API**: แสดงแผนที่
- **Lottie React**: Animation
- **SweetAlert2**: Alert dialogs

### Backend
- **FastAPI 0.115.5**: Web framework
- **Uvicorn 0.30.6**: ASGI server
- **Pydantic 2.8.2**: Data validation
- **Motor 3.6.0**: MongoDB async driver
- **PyMongo 4.9**: MongoDB driver
- **Redis 7.1.0**: Caching layer
- **Google Generative AI 0.6.0+**: Gemini LLM
- **Amadeus 9.0.0**: Travel data API
- **Google Maps 4.10.0**: Location services
- **Omise 0.10.0**: Payment gateway
- **httpx 0.27.2**: Async HTTP client
- **Tenacity 9.0.0**: Retry logic
- **Passlib 1.7.4**: Password hashing
- **psutil 5.9.8**: System monitoring
- **Firebase Admin 6.5.0+**: Firebase Authentication
- **NumPy 1.24.0+**: Numerical computing
- **scikit-learn 1.3.0+**: Machine Learning algorithms
- **Pandas 2.0.0+**: Data manipulation and analysis
- **TensorFlow 2.13.0+**: Deep Learning framework

### Database
- **MongoDB**: ฐานข้อมูลหลัก
- **Redis**: Cache และ session (optional)

---

## 📡 API Endpoints

### Chat API (7 endpoints)
- `POST /api/chat` - ส่งข้อความและรับการตอบกลับ
- `POST /api/chat/stream` - Streaming chat responses (SSE)
- `GET /api/chat/history/{client_trip_id}` - ดึงประวัติการสนทนา
- `GET /api/chat/sessions` - รายการ sessions ทั้งหมด
- `POST /api/chat/select_choice` - เลือกตัวเลือก (flight/hotel/etc.)
- `POST /api/chat/reset` - รีเซ็ต chat session
- `POST /api/chat/tts` - Text-to-Speech

### Auth API (10+ endpoints)
- `POST /api/auth/register` - ลงทะเบียน
- `POST /api/auth/login` - เข้าสู่ระบบ
- `POST /api/auth/logout` - ออกจากระบบ
- `GET /api/auth/me` - ข้อมูลผู้ใช้ปัจจุบัน
- `PUT /api/auth/profile` - อัปเดตโปรไฟล์
- `POST /api/auth/google` - Google OAuth Sign-In
- `POST /api/auth/firebase` - Firebase Authentication
- `POST /api/auth/send-verification-email` - ส่งอีเมลยืนยัน
- `POST /api/auth/verify-email` - ยืนยันอีเมล (token จากลิงก์ในอีเมล หรือ query)
- `POST /api/auth/send-phone-otp` - ส่ง OTP ไปเบอร์โทร (เมื่อเปลี่ยนเบอร์)
- `POST /api/auth/verify-phone-otp` - ยืนยัน OTP เพื่ออัปเดตเบอร์โทร
- `GET /api/auth/reset-password/{email}` - ขอรีเซ็ตรหัสผ่าน
- `POST /api/auth/reset-password` - รีเซ็ตรหัสผ่านด้วย token
- `POST /api/auth/dev-login` - Dev login (testing only)

### Travel API (2 endpoints)
- `POST /api/travel/smart-search` - ค้นหาบริการการเดินทาง (flights, hotels, rentals, transfers, activities, popular_destinations) ตาม intent จากข้อความ
- `GET /api/travel/popular-destinations` - จุดหมายยอดนิยม (optional: lat, lng)

### Booking API (11 endpoints)
- `POST /api/booking/create` - สร้างการจอง
- `GET /api/booking/list` - รายการการจอง (with Redis cache)
- `POST /api/booking/payment` - เริ่มต้นการชำระเงิน
- `POST /api/booking/create-charge` - สร้าง Omise charge
- `GET /api/booking/payment-page/{booking_id}` - หน้าชำระเงิน
- `GET /api/booking/payment-config` - ข้อมูล config การชำระเงิน
- `POST /api/booking/cancel` - ยกเลิกการจอง
- `PUT /api/booking/update` - อัปเดตการจอง
- `PATCH /api/booking/update` - อัปเดตการจองแบบ partial
- `POST /api/booking/test-omise` - ทดสอบ Omise connection
- `GET /api/booking/test-omise` - ตรวจสอบ Omise status

#### เชื่อมต่อ Omise (Payment Gateway)
1. **ตั้งค่า Backend** — ใน `backend/.env` ใส่คีย์จาก [Omise Dashboard](https://dashboard.omise.co/):
   - `OMISE_SECRET_KEY=skey_test_xxx` (หรือ `skey_live_xxx` สำหรับ production)
   - `OMISE_PUBLIC_KEY=pkey_test_xxx` (หรือ `pkey_live_xxx`)
   - (ถ้า deploy แยก) `FRONTEND_URL=https://your-frontend-domain.com` เพื่อให้ CORS อนุญาต origin นี้
2. **Frontend** — ใช้ `VITE_API_BASE_URL` ชี้ไปที่ Backend (เช่น `http://localhost:8000`) เพื่อเรียก `GET /api/booking/payment-config` และ `POST /api/booking/create-charge`
3. **Flow การชำระเงิน**: หน้า Payment โหลด Omise.js จาก CDN → เรียก Backend `payment-config` เอา public key → ผู้ใช้กรอกบัตร → สร้าง token ด้วย `Omise.createToken('card', card)` → ส่ง token ไป Backend `create-charge` → Backend เรียก Omise API สร้าง charge
4. **ทดสอบการเชื่อมต่อ**:
   - `GET /api/booking/test-omise` — ดูสถานะคีย์และเชื่อมต่อ Omise API
   - `POST /api/booking/test-omise` — สร้าง test payment link (ใช้บัตรทดสอบ เช่น 4242424242424242)

### Admin API (5 endpoints)
- `GET /api/admin/status` - System status และ health
- `GET /api/admin/sessions` - รายการ sessions ทั้งหมด
- `GET /api/admin/logs` - System logs
- (ลบ GET /api/admin/workflows แล้ว — ใช้ workflow tracking ตาม session แทน)
- `GET /api/admin/stream` - Server-Sent Events สำหรับ realtime monitoring

### Monitoring API (8 endpoints)
- `GET /api/monitoring/health` - Health check
- `GET /api/monitoring/cost/session/{session_id}` - ค่าใช้จ่าย per session
- `GET /api/monitoring/cost/all` - ค่าใช้จ่ายทั้งหมด
- `GET /api/monitoring/cost/breakdown/{session_id}` - รายละเอียดค่าใช้จ่าย
- `POST /api/monitoring/cost/reset/{session_id}` - รีเซ็ตค่าใช้จ่าย
- `POST /api/monitoring/sync/redis/session/{session_id}` - Sync session ไป Redis
- `POST /api/monitoring/sync/redis/all` - Sync all sessions ไป Redis
- `GET /api/monitoring/sync/redis/status` - Redis sync status

### MCP API (10 endpoints)
- `GET /api/mcp/tools` - รายการ tools ทั้งหมด
- `GET /api/mcp/health` - MCP health check
- `POST /api/mcp/execute` - Execute MCP tool
- `POST /api/mcp/search/flights` - ค้นหาเที่ยวบิน
- `POST /api/mcp/search/hotels` - ค้นหาโรงแรม
- `POST /api/mcp/search/transfers` - ค้นหาการขนส่ง
- `POST /api/mcp/search/activities` - ค้นหากิจกรรม
- `POST /api/mcp/geocode` - Geocoding
- `POST /api/mcp/airport` - ค้นหาข้อมูลสนามบิน
- Weather: สภาพอากาศปลายทางผ่าน MCP tool `get_weather_forecast` (Open-Meteo)

### Notification API (4 endpoints)
- `GET /api/notification/list` - รายการแจ้งเตือน
- `GET /api/notification/count` - จำนวนแจ้งเตือนที่ยังไม่อ่าน
- `POST /api/notification/mark-read` - ทำเครื่องหมายว่าอ่านแล้ว
- `POST /api/notification/mark-all-read` - ทำเครื่องหมายทั้งหมดว่าอ่านแล้ว

### Options Cache API (3 endpoints)
- `GET /api/options-cache/session/{session_id}` - ดึง cached options
- `GET /api/options-cache/session/{session_id}/validate` - Validate cache
- `DELETE /api/options-cache/session/{session_id}` - ลบ cache

### Amadeus Viewer API (2 endpoints)
- `POST /api/amadeus-viewer/extract-info` - แยกข้อมูลจาก Amadeus response
- `POST /api/amadeus-viewer/search` - ค้นหาผ่าน Amadeus API

### Diagnostics API (2 endpoints)
- `GET /api/diagnostics/search-status` - สถานะการค้นหา
- `GET /api/diagnostics/test-search` - ทดสอบการค้นหา

### สรุป API Endpoints
**รวมมากกว่า 65 endpoints** จากโมดูล chat, auth, travel, booking, notification, admin, mcp, monitoring, options_cache, amadeus_viewer, diagnostics

---

## 🧠 AI Intelligence Features

### 1. **Smart Date Understanding**
- เข้าใจวันที่ภาษาไทย: "พรุ่งนี้", "สงกรานต์", "สัปดาห์หน้า"
- รองรับปีพุทธศักราช: "20 มกราคม 2568"
- คำนวณวันที่อัตโนมัติจาก "3 วัน", "2 คืน"

### 2. **Location Intelligence**
- แปลงสถานที่สำคัญเป็นเมือง: "Siam Paragon" → "Bangkok"
- ค้นหาโรงแรมใกล้สถานที่ท่องเที่ยว
- รองรับหลายจุดแวะ (Waypoints)
- Google Maps integration สำหรับ geocoding และ routing

### 3. **Budget Advisory**
- แนะนำงบประมาณที่สมเหตุสมผล
- เตือนเมื่องบประมาณต่ำเกินไป
- คำนวณราคารวมอัตโนมัติ

### 4. **Flight Preferences**
- เข้าใจชั้นที่นั่ง: "ชั้นประหยัดพรีเมี่ยม", "business"
- เข้าใจประเภทเที่ยวบิน: "บินตรง", "direct", "nonstop"
- รองรับการค้นหาแบบ multi-city

### 5. **Advanced Option Selection Intelligence**

#### 5.1 **Weighted Sum Model (สมการ 1)**
- สมการ: `S_i = Σ (from j=1 to n) w_j * f_j(x_{ij})`
- พิจารณาหลายปัจจัยพร้อมกัน: Recommended (40%), Price (30%), Rating (20%), Convenience (5%), User Preferences (3%), Destination Type (1%), Time Constraints (1%)
- ระบบจะเลือกตัวเลือกที่มีค่า S_i สูงสุดเป็นคำแนะนำหลัก

#### 5.2 **Data Normalization (Min-Max)**
- สมการ: `x_ij' = (x_ij - min(x_j)) / (max(x_j) - min(x_j))`
- Normalize ข้อมูลที่มีหน่วยต่างกัน (บาท, คะแนนรีวิว, ระยะทาง) ให้อยู่ในช่วง [0, 1]
- Fair comparison across different criteria

#### 5.3 **Reinforcement Learning (RL)**
- Expected Return Formula: `Rt = E[ Σ_{k=0}^{T-t} γ^k r_{t+k+1} | S_t ]`
- Reward Function: บันทึก reward จาก user interactions (select, book, reject, feedback)
- เรียนรู้จากประวัติการเลือกของผู้ใช้
- เพิ่ม RL bonus (0-10 points, 10% of total score)

#### 5.4 **Enhanced Data Preprocessing**
- **Outlier Detection**: IQR และ Z-Score methods
- **Outlier Handling**: Clip, Remove, Median, Mean replacement
- **Missing Value Imputation**: Mean, Median, Mode strategies
- **Categorical Encoding**: Label และ One-Hot encoding
- **Feature Engineering**: price_per_rating, price_per_hour, rating_per_review, engineered_total_score
- **Feature Standardization**: Z-score และ Min-Max scaling

#### 5.5 **Machine Learning (ML)**
- **Option Ranking Model**: Random Forest / Gradient Boosting สำหรับ ranking
- **Preference Predictor**: Gradient Boosting สำหรับ user preferences
- **Price Predictor**: Linear Regression สำหรับ price prediction
- ML bonus: 0-15 points (15% of total score)

#### 5.6 **Deep Learning (Neural Networks)**
- **Deep Ranking Network**: 
  - Architecture: 8 → 64 → 32 → 16 → 1 (ReLU + Dropout)
  - เรียนรู้ pattern ที่ซับซ้อนในการ ranking
- **Deep Preference Network**:
  - Architecture: 10 → 128 → 64 → 32 → 1
  - เรียนรู้ user preferences แบบ multi-factor
- DL bonus: 0-15 points (15% of total score)

#### 5.7 **Multi-Model Ensemble Scoring**
- Final Score = Weighted Sum Score + RL Bonus + ML Bonus + DL Bonus
- Combined intelligence from multiple sources
- Adaptive learning over time

### 6. **Agent Modes**

#### Normal Mode (ผู้ใช้เลือกเอง)
- ผู้ใช้เลือกตัวเลือกเอง
- ไม่ auto-select
- ผู้ใช้ต้องกดจองเอง
- แสดงตัวเลือกหลายรายการให้เลือก

#### Agent Mode (อัตโนมัติ 100%)
- AI เลือกตัวเลือกที่ดีที่สุดอัตโนมัติ (ใช้ ML/DL + Weighted Sum + RL)
- Auto-book ทันทีหลังเลือก
- ใช้ค่าเริ่มต้นอัจฉริยะสำหรับข้อมูลที่ขาด
- Detailed logging สำหรับ debugging
- Race condition prevention
- Duplicate booking prevention
- Retry logic with exponential backoff

### 7. **Performance Optimizations**
- **Redis Caching**: Cache bookings list (TTL: 30s)
- **Query Timeout**: MongoDB queries มี timeout 5 วินาที
- **Concurrent Search**: ค้นหา flights, hotels พร้อมกัน
- **Connection Pooling**: ใช้ connection manager สำหรับ MongoDB และ Redis

### 8. **Error Recovery**
- Auto-retry สำหรับ external API calls
- Fallback mechanisms เมื่อ service ล้มเหลว
- Graceful degradation (ทำงานต่อได้แม้ Redis ไม่พร้อม)
- Comprehensive error logging

### 9. **Intelligent Trip Planning**
- **Destination Type Detection**: จำแนกประเภทจุดหมายปลายทาง (beach, city, cultural, mountain)
- **Optimal Nights Suggestion**: แนะนำจำนวนคืนที่เหมาะสมตามประเภทจุดหมาย
- **Smart Date Inference**: คำนวณวันที่อัตโนมัติจาก context
- **Logical Ordering**: จัดลำดับการเดินทางอย่างมีเหตุผล (flights ก่อน transfers)

---

## 💾 ข้อมูลที่เก็บ

### Backend (MongoDB)

#### Collections หลัก:
1. **users**: ข้อมูลผู้ใช้
2. **conversations**: ประวัติการสนทนา
3. **bookings**: การจอง
4. **notifications**: การแจ้งเตือน

#### Conversation Structure:
```javascript
{
  "_id": ObjectId,
  "session_id": "user_id::chat_id",
  "user_id": "user_id",
  "created_at": ISODate,
  "updated_at": ISODate,
  "messages": [
    {
      "role": "user" | "assistant",
      "content": "ข้อความ",
      "timestamp": ISODate,
      "metadata": {
        // ข้อมูลสำหรับแสดง UI (อ้างอิงจาก Redis + trip_plan)
        "current_plan": {...},
        "travel_slots": {...},
        "agent_state": {...}
      }
    }
  ]
}
```

### Backend (Redis) — Workflow Amadeus

- **Raw data จาก Amadeus** (`session:{session_id}:amadeus_raw`): เก็บผลค้นหา flights, hotels, transfers ต่อ session สำหรับจัดช้อยและแก้ไขซ้ำโดยไม่เรียก Amadeus ใหม่
- **ช้อยที่เลือก** (`session:{session_id}:selections`): เก็บ flight/hotel/transfer ที่ผู้ใช้เลือก ใช้แสดง Trip Summary และส่งจอง
- **สถานะ workflow** (ใน key เดียวหรือแยก): planning / selecting / summary / booking — ใช้ติดตามขั้นตอนและตัดสินใจเคลียร์ Redis เมื่อจองเสร็จ

### Frontend (localStorage)

#### ข้อมูลที่เก็บ:
- `is_logged_in`: สถานะการเข้าสู่ระบบ
- `user_data`: ข้อมูลผู้ใช้
- `ai_travel_trips_v1`: ข้อมูลทริปและการสนทนา
- `ai_travel_active_trip_id_v1`: ID ทริปที่กำลังใช้งาน
- `app_view`: หน้าปัจจุบัน

---

## 🔄 Workflow การทำงาน (Amadeus + Redis + PlanChoiceCard)

หลังลบระบบ workflow เดิมแล้ว ใช้ workflow ใหม่ดังนี้: เก็บ raw data จาก Amadeus ใน Redis → Gemini Agent จัดช้อย → แสดงใน PlanChoiceCard → เก็บช้อยที่เลือกใน Redis → สรุป Trip Summary → ยืนยันจองเข้า My Bookings → เคลียร์ Redis เมื่อเสร็จ

---

### 1. **ภาพรวม Workflow**

```
User Input (แชท)
    ↓
Controller (Gemini) → สร้าง/อัปเดตแผน (CREATE_ITINERARY / UPDATE_REQ)
    ↓
CALL_SEARCH → ดึงข้อมูลจาก Amadeus (flights, hotels, transfers)
    ↓
เก็บ Raw Data ทั้งหมดใน Redis (per session)
    ↓
Gemini Agent จัดช้อย (จัดเรียง/จัดกลุ่มจาก raw data)
    ↓
ส่งช้อยไป Frontend → แสดงใน PlanChoiceCard แต่ละอัน (เที่ยวบิน / โรงแรม / การเดินทาง)
    ↓
ผู้ใช้เลือกช้อย → เก็บช้อยที่เลือกใน Redis
    ↓
เมื่อครบทุก slot → สรุป Trip Summary
    ↓
เมื่อผู้ใช้แก้ไข → เอาข้อมูลใน Redis ที่ดึงมาแล้วมาจัดใหม่ (ไม่ดึง Amadeus ซ้ำ ถ้าไม่จำเป็น) → ทำแบบเดิม
    ↓
เมื่อ workflow เสร็จและผู้ใช้กดยืนยันการจอง → จองเข้า My Bookings
    ↓
เมื่อกระบวนการจองเสร็จสิ้น → เคลียร์ Redis (raw data + selections ของ session นั้น)
```

---

### 2. **Redis: เก็บ Raw Data และช้อยที่เลือก**

| ข้อมูลใน Redis | รูปแบบ | ใช้เมื่อ |
|----------------|--------|----------|
| **Raw data จาก Amadeus** | เก็บผลค้นหา flights, hotels, transfers ต่อ session (key เช่น `session:{session_id}:amadeus_raw`) | ดึงครั้งเดียวต่อ search → ใช้สำหรับจัดช้อยและแก้ไขซ้ำโดยไม่เรียก Amadeus ใหม่ |
| **ช้อยที่เลือก (selections)** | เก็บ flight/hotel/transfer ที่ผู้ใช้เลือกต่อ session (key เช่น `session:{session_id}:selections`) | แสดง Trip Summary และส่งต่อจอง |
| **สถานะ workflow** | เก็บ step ปัจจุบัน (planning / selecting / summary / booking) | ติดตาม workflow และตัดสินใจเมื่อไหร่แสดง PlanChoiceCard / Summary / ปุ่มจอง |

- **TTL**: ตั้งค่า expiry ต่อ session (เช่น 24 ชม.) เพื่อไม่ให้ Redis ค้าง
- **เคลียร์ Redis**: เมื่อจองเข้า My Bookings เสร็จแล้ว (หรือผู้ใช้ออกจาก flow) → ลบ key ของ session นั้น (raw data + selections + workflow state)

---

### 3. **Gemini Agent จัดช้อย**

- อ่าน **raw data จาก Redis** (ผล Amadeus ที่เก็บไว้)
- จัดเรียง/จัดกลุ่ม/จัดช้อย (ranking, filtering, แนะนำ) ตาม context การสนทนาและความต้องการผู้ใช้
- ส่งออกเป็นโครงสร้างสำหรับ **PlanChoiceCard**: แยกตาม category (flights, hotels, transfers) แต่ละอันมี list ของตัวเลือก (id, title, price, details, raw_data อ้างอิง)

---

### 4. **PlanChoiceCard แต่ละอัน**

- **PlanChoiceCardFlights**: แสดงช้อยเที่ยวบินจากข้อมูลที่ Agent จัดแล้ว
- **PlanChoiceCardHotels**: แสดงช้อยโรงแรมจากข้อมูลที่ Agent จัดแล้ว
- **PlanChoiceCardTransfer**: แสดงช้อยการเดินทาง/รถรับส่งจากข้อมูลที่ Agent จัดแล้ว

แต่ละการ์ดรับข้อมูลจาก backend (ที่ดึงจาก Redis + จัดโดย Gemini) และเมื่อผู้ใช้กดเลือก → ส่ง choice กลับไปเก็บใน Redis (selections)

---

### 5. **การติดตาม Workflow**

- เก็บ **สถานะ workflow** ใน Redis (และ/หรือใน session/trip_plan ใน MongoDB) เช่น:
  - `planning` — กำลังสร้าง/แก้แผน
  - `searching` — กำลังค้นหา Amadeus
  - `selecting` — กำลังแสดง PlanChoiceCard ให้เลือก
  - `summary` — ครบแล้ว แสดง Trip Summary
  - `booking` — กำลังจอง / จองเสร็จแล้ว
- ใช้สถานะนี้เพื่อ:
  - แสดง UI ให้ตรงขั้นตอน (PlanChoiceCard vs Summary vs ปุ่มยืนยันจอง)
  - รู้ว่าเมื่อไหร่ “ครบ” แล้วจึงแสดง Summary และเปิดปุ่มยืนยันจอง
  - รู้ว่าเมื่อไหร่จองเสร็จแล้ว จึง **เคลียร์ Redis** ของ session นั้น

---

### 6. **เมื่อแก้ไขแผน**

- ถ้าผู้ใช้แก้ไข (เปลี่ยนวัน/จุดหมาย/จำนวนคน ฯลฯ):
  - ถ้า **ยังใช้ชุดค้นหาเดิมได้** (เช่น แค่เปลี่ยน choice) → ใช้ **raw data ใน Redis** ที่มีอยู่ → Gemini Agent จัดช้อยใหม่ → อัปเดต PlanChoiceCard / Summary
  - ถ้า **ต้องค้นหาใหม่** (เช่น เปลี่ยนวันเดินทาง) → CALL_SEARCH ใหม่ → เก็บ raw data ชุดใหม่ใน Redis → จัดช้อยใหม่ → แสดง PlanChoiceCard ใหม่
- ช้อยที่เลือกที่ยังใช้ได้ (เช่น ยังไม่เกี่ยวกับส่วนที่แก้) ยังอ้างอิงจาก Redis ได้

---

### 7. **เมื่อครบ workflow และยืนยันจอง**

1. ครบทุก slot (flight, hotel, transfer ตามแผน) → แสดง **Trip Summary**
2. ผู้ใช้กด **ยืนยันการจอง** → Backend อ่าน **selections จาก Redis** (และ raw data ถ้าต้องการ) → สร้างการจองเข้า **My Bookings**
3. หลังจองสำเร็จ (และชำระเงินถ้ามี) → **เคลียร์ Redis** สำหรับ session นั้น:
   - ลบ raw data (`session:{session_id}:amadeus_raw`)
   - ลบ selections (`session:{session_id}:selections`)
   - ลบ/อัปเดต workflow state ของ session นั้น

---

### 8. **สรุปขั้นตอนหลัก (สั้น)**

1. **ดึงจาก Amadeus** → เก็บ **raw data ทั้งหมดใน Redis**
2. **Gemini Agent** → อ่าน raw data จาก Redis → **จัดช้อย** → ส่งไปแสดงใน **PlanChoiceCard แต่ละอัน**
3. **ผู้ใช้เลือก** → เก็บ **ช้อยที่เลือกใน Redis**
4. **ครบแล้ว** → แสดง **Trip Summary**
5. **แก้ไข** → ใช้ข้อมูลใน Redis จัดใหม่ (หรือค้นใหม่แล้วเก็บใน Redis แล้วจัดใหม่)
6. **ยืนยันจอง** → จองเข้า **My Bookings**
7. **ติดตาม workflow** และเมื่อ **เสร็จสิ้นกระบวนการ** → **เคลียร์ Redis** ของ session นั้น

---

## 🛠️ การติดตั้งและรัน

### Prerequisites
- Python 3.12+
- Node.js 18+
- MongoDB
- Redis (optional)

### Backend Setup

```bash
cd backend

# สร้าง virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# ติดตั้ง dependencies
pip install -r requirements.txt

# Note: ML/DL libraries (scikit-learn, pandas, tensorflow) จะติดตั้งอัตโนมัติ
# สำหรับ TensorFlow: ใช้ CPU version (tensorflow) หรือ GPU version (tensorflow-gpu)

# สร้างไฟล์ .env
cp env.example .env
# แก้ไข .env และใส่ API keys

# รัน server
python main.py
# หรือ
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend

# ติดตั้ง dependencies
npm install

# สร้างไฟล์ .env
# VITE_API_BASE_URL=http://localhost:8000
# VITE_GOOGLE_CLIENT_ID=your_google_client_id

# รัน dev server
npm run dev
```

### Environment Variables

#### Backend (.env)
```env
# Gemini AI
GEMINI_API_KEY=your_key
GEMINI_MODEL_NAME=gemini-1.5-flash
ENABLE_GEMINI=true

# Amadeus
AMADEUS_API_KEY=your_key
AMADEUS_API_SECRET=your_secret

# Google Maps
GOOGLE_MAPS_API_KEY=your_key

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id

# Firebase Authentication
FIREBASE_CREDENTIALS_PATH=/path/to/service-account-key.json
# OR
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_API_KEY=your-api-key
FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com

# Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=travel_agent
REDIS_URL=redis://localhost:6379

# Payment
OMISE_PUBLIC_KEY=your_key
OMISE_SECRET_KEY=your_secret

# Security
SECRET_KEY=your_secret_key
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=your_admin_password
```

#### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=your_google_client_id

# Firebase Configuration (optional)
VITE_FIREBASE_ENABLED=true
VITE_FIREBASE_API_KEY=your-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
```

---

## 🔒 Security Features

### 1. **Authentication & Authorization**
- Session-based authentication
- Google OAuth 2.0
- Password hashing (bcrypt)
- Session cookies with secure flags

### 2. **Rate Limiting**
- Chat API: 30 requests/minute
- Payment API: 10 requests/minute
- General API: 60 requests/minute

### 3. **Input Validation**
- Pydantic models สำหรับ validation
- SQL injection protection
- XSS protection

### 4. **Error Handling**
- Global exception handlers
- Structured error responses
- ไม่เปิดเผยข้อมูล sensitive ใน error messages

---

## 📊 Monitoring & Logging

### Logging
- Structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR
- Log files: `backend/data/logs/`

### Health Monitoring
- Health check endpoint: `/health`
- MongoDB connection monitoring
- Redis connection monitoring (optional)
- Auto-recovery mechanisms

### Metrics
- Request counts
- Error rates
- Response times
- LLM usage costs

---

## 🧪 Testing

### Manual Testing
- Health check: `GET /health`
- Chat endpoint: `POST /api/chat`
- Authentication flow

### Test Scripts
- `backend/scripts/test_privacy_manual.py`
- `backend/scripts/verify_database.py`
- `backend/scripts/run_system_tests.py` - ทดสอบระบบ backend แบบรวดเร็ว (config, MCP tools, chat._map_option_for_frontend, agent_intelligence.validator, _normalize_create_itinerary_payload); ไม่ต้องเชื่อม MongoDB/Redis จริง. รัน: `cd backend && .venv\Scripts\python scripts/run_system_tests.py`

---

## 📚 เอกสารเพิ่มเติม

### Backend Documentation
- `backend/docs/README.md` - สถาปัตยกรรมหลัก
- `backend/docs/README_MCP.md` - MCP Integration
- `backend/docs/MCP_INTEGRATION.md` - MCP Guide
- `backend/docs/DATABASE_DESIGN.md` - Database Schema
- `backend/docs/AGENT_INTELLIGENCE.md` - AI Features
- `backend/docs/GOOGLE_MAPS_INTELLIGENCE.md` - Maps Features
- `backend/docs/LOCATION_SERVICE.md` - Location Service
- `backend/docs/AMADEUS_TRANSFER_SERVICE.md` - Transfer Service
- `backend/docs/AUTO_MODEL_SWITCHING.md` - Model Selection
- `backend/docs/CRASH_PREVENTION.md` - Error Handling

### Intelligence & ML/DL Documentation
- `WEIGHTED_SUM_MODEL_REPORT.md` - Weighted Sum Model implementation
- `RL_AND_NORMALIZATION_REPORT.md` - Reinforcement Learning & Data Normalization
- `ML_DL_PREPROCESSING_REPORT.md` - Machine Learning, Deep Learning & Preprocessing
- `FIREBASE_AUTHENTICATION_REPORT.md` - Firebase Authentication integration
- `CRUD_STABILITY_REPORT.md` - CRUD operations stability improvements
- `AGENT_MODE_STABILITY_REPORT.md` - Agent Mode stability enhancements
- `WORKFLOW_STABILITY_REPORT.md` - Workflow bug fixes
- `INTELLIGENT_PLANNING_REPORT.md` - Intelligent planning enhancements

### Frontend Documentation
- `CONVERSATION_HISTORY_DOCUMENTATION.md` - ข้อมูลที่เก็บในประวัติ

### Testing Documentation
- `testsprite_tests/testsprite-mcp-test-report.md` - Test report พร้อม analysis
- `testsprite_tests/tmp/code_summary.json` - Codebase summary

### Scripts
- `backend/scripts/mock_data.py` - Generate mock data for testing
  - Usage: `python -m scripts.mock_data <user_id> [num_sessions]`
- `backend/scripts/run_system_tests.py` - ทดสอบระบบ backend (quick system tests)
  - Usage: `cd backend && .venv\Scripts\python scripts/run_system_tests.py`

---

## 🚀 Deployment

### Production Checklist
- [ ] ตั้งค่า environment variables
- [ ] ตั้งค่า MongoDB production
- [ ] ตั้งค่า Redis (optional)
- [ ] ตั้งค่า SSL/TLS
- [ ] ตั้งค่า CORS origins
- [ ] ตั้งค่า rate limiting
- [ ] ตั้งค่า logging
- [ ] ตั้งค่า monitoring
- [ ] Backup strategy

### Docker (Optional)
- `backend/Dockerfile` - Backend container
- `backend/docker-compose.yml` - Full stack

---

## 🐛 Troubleshooting

### ปัญหาที่พบบ่อย

1. **MongoDB Connection Failed**
   - ตรวจสอบ MongoDB กำลังรัน
   - ตรวจสอบ MONGODB_URI ใน .env

2. **Gemini API Error**
   - ตรวจสอบ GEMINI_API_KEY
   - ตรวจสอบ quota และ rate limits

3. **Amadeus API Error**
   - ตรวจสอบ API keys
   - ตรวจสอบ API quota

4. **CORS Error**
   - ตรวจสอบ CORS origins ใน main.py
   - ตรวจสอบ frontend URL

5. **Payment Error**
   - ตรวจสอบ Omise keys
   - ตรวจสอบ test mode vs production mode

---

## 📝 Changelog

### Version 2.1.0 (อัปเดตล่าสุด)
- **Frontend**: หน้า HomePage เป็นภาษาไทย; ลบ search bar, category shortcuts, Popular Destinations ออกจากโฮม (ใช้ผ่าน AI Agent ในแชท)
- **AppHeader**: แสดงเฉพาะ "การจองของฉัน" (ลบแท็บ การเดินทาง, สำรวจ, เที่ยวบิน, โรงแรม, ที่พักให้เช่า)
- **Travel API**: เพิ่ม `GET /api/travel/popular-destinations`; smart-search รองรับ rentals, popular_destinations
- **Auth**: ยืนยันอีเมล (ส่งอีเมลยืนยัน, เปลี่ยนอีเมลส่งยืนยันใหม่); รองรับทุกเมล (ยกเว้น admin@example.com); ต้องยืนยันอีเมลก่อนจอง (ถ้าเปิดใช้); เปลี่ยนเบอร์โทรส่ง OTP และ verify-phone-otp — implement ใน backend แล้ว (`auth.py`, `email_service`, `sms_service`)
- **Cleanup**: ลบไฟล์ที่ไม่ได้ใช้ — `frontend/src/App.css`, `backend/app/services/amadeus_client.py` (ใช้ TravelOrchestrator ใน travel_service แทน)
- **App.jsx**: ไม่ส่ง nav callbacks (Flights/Hotels/Rentals) ไปที่ HomePage

### Version 2.0.0
- Two-Pass ReAct Architecture
- MCP Integration
- MongoDB Storage
- Payment Integration
- Notification System
- Enhanced AI Intelligence

---

## 👥 Contributors

- Development Team

---

## 📄 License

(ระบุ license ตามที่โปรเจกต์กำหนด)

---

## 📞 Support

สำหรับคำถามหรือปัญหา:
- ตรวจสอบเอกสารใน `backend/docs/`
- ตรวจสอบ logs ใน `backend/data/logs/`
- Health check: `GET /health`

---

## 🧪 Testing & Quality Assurance

### Backend Testing (TestSprite)
- **Test Coverage**: 10 test cases (63 endpoints ทั้งหมด)
- **Pass Rate**: 30% (3/10 passed)
- **Test Areas**:
  - ✅ Chat API reset
  - ✅ User registration
  - ✅ Booking creation
  - ❌ Authentication flows (requires test user setup)
  - ❌ Chat endpoints (timeout issues)

### Test Reports
- `testsprite_tests/testsprite-mcp-test-report.md` - Detailed test results
- `testsprite_tests/testsprite_backend_test_plan.json` - Test plan
- `testsprite_tests/standard_prd.json` - Product requirements

### Known Issues
1. **Authentication**: Tests need proper test user setup
2. **Timeouts**: AI-powered endpoints ต้องใช้เวลานาน (>30s)
3. **OAuth Testing**: ต้องใช้ valid Google ID tokens

---

## 🚨 Recent Updates & Improvements

### Performance Enhancements (Jan 2026)
- ✅ เพิ่ม Redis caching สำหรับ bookings list (TTL: 30s)
- ✅ ลบ debug queries ที่ไม่จำเป็นออก
- ✅ เพิ่ม timeout protection สำหรับ MongoDB queries (5s)
- ✅ ปรับปรุง error handling ใน frontend
- ✅ AbortController สำหรับ fetch requests (10s timeout)

### Admin Dashboard
- ✅ Realtime monitoring ด้วย Server-Sent Events (SSE)
- ✅ Services status auto-sync ทุก 1 นาที
- ✅ Manual refresh สำหรับข้อมูลอื่นๆ
- ✅ Session debug viewer พร้อม raw data display
- ✅ PlanChoiceCard preview สำหรับ debugging

### Agent Mode Improvements
- ✅ Detailed logging สำหรับ auto-selection process
- ✅ ปรับปรุง booking payload structure
- ✅ Error handling สำหรับ booking API calls
- ✅ Validation checks ก่อนสร้าง booking

### Mock Data Scripts
- ✅ `backend/scripts/mock_data.py` - สร้าง test data
- ✅ รองรับ pending_payment bookings
- ✅ สร้าง realistic trip plans พร้อม options

### Backend System Tests (Jan 2026)
- ✅ `backend/scripts/run_system_tests.py` - ทดสอบระบบ backend แบบรวดเร็ว (ไม่เชื่อม MongoDB/Redis จริง)
- ✅ ครอบคลุม: app.core.config, MCP tools (14 tools: Amadeus + Google Maps + Weather), chat._map_option_for_frontend, agent_intelligence.validator, _normalize_create_itinerary_payload (guests clamp, end_date fix)
- ✅ รันผ่านทั้งหมด (ALL PASSED)

---

**อัปเดตล่าสุด**: ตามสภาพโค้ดปัจจุบัน — Frontend ภาษาไทย; Nav เฉพาะ "การจองของฉัน"; Travel API มี popular-destinations และ smart-search (rentals, popular_destinations); Auth มีส่งอีเมลยืนยัน, verify-email, ส่ง OTP เบอร์โทร และ verify-phone-otp (implement ใน backend แล้ว); ลบไฟล์ไม่ใช้ (App.css, amadeus_client.py). MCP มี Weather (Open-Meteo) สำหรับสภาพอากาศปลายทาง. Backend system tests: `run_system_tests.py` ผ่านทั้งหมด (config, MCP 14 tools, chat, agent validator, normalize payload).
