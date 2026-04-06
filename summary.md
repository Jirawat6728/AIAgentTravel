# AI Travel Agent — Project Summary (ฉบับละเอียด)

> **Version**: 1.3.0 | **Architecture**: Two-Pass ReAct + LangGraph | **Last Updated**: 17 March 2026

---

## 1. ภาพรวมระบบ

AI Travel Agent เป็นแอปพลิเคชันวางแผนการเดินทางแบบครบวงจร ผู้ใช้สนทนาเป็นภาษาไทยหรืออังกฤษกับ AI เพื่อค้นหาเที่ยวบิน โรงแรม และการเดินทาง จากนั้น AI จะจัดการเลือก จอง และชำระเงินให้อัตโนมัติ

### โหมดการทำงาน
| โหมด | คำอธิบาย |
|------|-----------|
| **โหมดถาม (Ask Mode)** | AI แนะนำตัวเลือก ผู้ใช้เลือกเอง |
| **Agent Mode** | AI วิเคราะห์และเลือกตัวเลือกที่ดีที่สุดอัตโนมัติ จากนั้นจองและชำระเงินให้ครบ |

---

## 2. Tech Stack

### Backend
| ส่วน | เทคโนโลยี |
|------|------------|
| Framework | FastAPI 0.115.5 + Uvicorn 0.30.6 |
| LLM | Google Gemini (`google-genai` SDK v0.6.0 + `google-generativeai` ≥0.8.0) |
| Primary Model | `gemini-2.5-flash` |
| Pro Model | `gemini-2.5-pro` |
| Live Audio Model | `gemini-2.5-flash-native-audio-preview-12-2025` |
| TTS Model | `gemini-2.5-flash-preview-tts` |
| Fallback Chain | `gemini-2.5-flash` → `gemini-2.0-flash-lite` |
| Orchestration | LangGraph ≥0.2 + LangChain ≥0.3 + LangChain-Google-GenAI ≥2.0 |
| Database | **MongoDB Atlas** (Motor 3.6 async driver + PyMongo ≥4.9) |
| Cache / Rate Limit | **In-process memory** เป็นค่าเริ่มต้น (options cache, workflow state, rate limit, general cache) โดยมี Redis แบบ **optional** ผ่าน `REDIS_URL` + `ENABLE_REDIS_CACHE` (ใช้ร่วมกับ `redis_client.py`, `redis_cache.py`, `redis_rate_limiter.py` และ LangGraph Redis checkpointer) |
| Travel API | Amadeus SDK 9.0 |
| Maps | Google Maps Python Client 4.10 |
| Payment | Omise 0.10 |
| Auth | Google Identity Services + Firebase Admin SDK ≥6.5 |
| Email | Gmail SMTP (`smtplib`) — ส่ง OTP verification |
| HTTP Client | httpx 0.27.2 (async) |
| ML/Intent | scikit-learn ≥1.3 (TF-IDF + LR + MLP) |
| Retry | tenacity 9.0 |
| Password | passlib[bcrypt] 1.7.4 |

### Frontend
| ส่วน | เทคโนโลยี |
|------|------------|
| Framework | React 18.3 + Vite 5.4 |
| Maps UI | @react-google-maps/api 2.20 |
| Auth | Firebase SDK 10.13 |
| Animation | Lottie-react 2.4 |
| Alerts | SweetAlert2 11.26 |
| Routing | ไม่ใช้ React Router — จัดการ view ใน `App.jsx` |
| Styling | **React + Tailwind CSS v4** (ผ่าน `@tailwindcss/postcss` + `@import "tailwindcss";` ใน `index.css`) + base CSS เดิม (font, scrollbar, font-size system) + Theme (Light/Dark ผ่าน `ThemeContext` + `theme-content.css`) — ไม่มี MUI |
| HTTP | Native `fetch` (ไม่มี Axios) |

### 2.1 Framework & Library Overview (Backend)

- **FastAPI + Uvicorn**: Framework + ASGI server สำหรับสร้าง REST API แบบ async ใช้เป็น entry point หลักของ backend (`main.py`) รองรับ SSE, WebSocket (live audio), middleware, dependency injection และทำงานคู่กับ Uvicorn เพื่อรันเป็น production server
- **Google Gemini SDK (`google-genai`, `google-generativeai`)**: Client SDK สำหรับเรียก LLM / TTS / Live Audio ของ Gemini ใช้ใน `llm.py`, `live_audio_service.py`, `tts_service.py` และ `gemini_agent.py` เพื่อ:
  - ทำ reasoning วางแผนทริป (LLM)
  - สร้างเสียงพูดภาษาไทย (TTS)
  - คุยแบบ real‑time voice (Live Audio)
- **LangGraph + LangChain**: Orchestration layer สำหรับประกอบ LLM + tools + state machine:
  - LangGraph: ใช้สร้าง workflow graph (`workflow_graph.py`, `agent_mode_graph.py`, `full_workflow_graph.py`) เพื่อควบคุมลำดับขั้นตอนค้นหา/เลือก/จอง
  - LangChain (+ langchain-google-genai): ใช้เป็น abstraction ของ LLM, tools, retrievers ในบางส่วนของ agent
- **MongoDB (Motor + PyMongo)**: ฐานข้อมูลหลักสำหรับเก็บ users, sessions, bookings, memories, RL tables ฯลฯ:
  - Motor (async driver) ใช้ใน `mongodb_storage.py` ให้ FastAPI ใช้งานแบบ async
  - PyMongo ใช้คู่กับเครื่องมือ admin/IndexModel
- **Redis (optional)**: ใช้เป็น cache / rate limiter / LangGraph checkpointer เมื่อกำหนด `REDIS_URL`:
  - `redis_client.py` จัดการ connection และ health
  - `redis_cache.py`, `options_cache.py`, `workflow_state.py`, `redis_rate_limiter.py` ใช้ Redis ร่วมกับ in‑process memory cache เพื่อเพิ่ม performance และรองรับหลาย instance
- **Amadeus SDK**: SDK ทางการของ Amadeus ใช้ค้นหาเที่ยวบิน/ที่พัก และสร้าง booking จริง (sandbox/prod แยก key) ผ่าน `travel_service.py` และ MCP tools
- **Google Maps Python Client**: ใช้ geocoding, distance matrix, และข้อมูลสถานที่ (เช่น สนามบิน, เมือง, landmark) ใน `google_maps_client.py` / `location_service.py`
- **Omise SDK**: ใช้สร้าง charge/payment token, บันทึกบัตร และจัดการการชำระเงินใน `omise_service.py` + `/api/booking`
- **Firebase Admin SDK + Google Identity Services**: 
  - ฝั่ง backend: ใช้ Firebase Admin SDK สำหรับ verify token และจัดการ email verification/OTP
  - ฝั่ง frontend: ใช้ Google Identity Services เป็นปุ่ม login ด้วย Google
- **httpx (async)**: HTTP client หลักสำหรับเรียก external APIs (Amadeus, weather, อื่นๆ) แบบ async ใน `travel_service.py`, `mcp_*`
- **scikit-learn**: ใช้ใน ML intent layer (TF‑IDF + Logistic Regression / MLP) สำหรับ intent classification
- **tenacity**: ใช้ทำ retry/backoff รอบ LLM/API calls เพื่อลด error ชั่วคราว
- **passlib[bcrypt]**: จัดการ password hashing/verify สำหรับ account เข้า backend (เช่น admin)

### 2.2 Framework & Library Overview (Frontend)

- **React**: UI framework หลักของ frontend ใช้สร้างทุกหน้า (Home, AI Chat, Flights/Hotels/Car Rentals, MyBookings, Settings, Profile) ด้วย functional components + hooks (`useState`, `useEffect`, `useContext`, `useRef`)
- **Vite**: Build tool + dev server สำหรับ React project:
  - ให้ HMR แบบเร็ว, build bundle สำหรับ production
  - ใช้ `import.meta.env` เพื่ออ่านค่า `.env` (เช่น `VITE_API_BASE_URL`)
- **Tailwind CSS v4 + base CSS**:
  - Tailwind: utility‑first CSS สำหรับ layout/spacing/typography ของหน้า search, booking, chat ฯลฯ
  - base CSS เดิม: กำหนด font system, scrollbar, responsive font size, และ styling พื้นฐาน
  - `ThemeContext` + `theme-content.css`: ใช้สลับ Light/Dark theme และ override สีใน component ต่างๆ
- **@react-google-maps/api**: Wrapper React สำหรับ Google Maps JS API ใช้แสดงแผนที่/marker ในหน้าเกี่ยวกับ location
- **Firebase SDK (frontend)**: ใช้สำหรับ auth ฝั่ง client (login/register/verify email ผ่าน Firebase) และ sync กับ backend
- **Lottie-react**: แสดง animation (เช่น loading / empty states) แบบ JSON Lottie เพื่อให้ UI ดู modern
- **SweetAlert2**: ใช้ popup สวยๆ สำหรับแจ้งเตือน/ยืนยัน (เช่น confirm booking, error, success) ในทุกหน้า (Flights, Hotels, Car Rentals, Profile, Payment)
- **Native `fetch`**: ใช้เรียก backend API ทั้งหมด (ไม่มี Axios) พร้อม `credentials: 'include'` สำหรับส่ง cookie/session

---

## 3. โครงสร้างโปรเจกต์

```
AITravelAgent/
├── summary.md                     # เอกสารนี้
├── backend/
│   ├── main.py                    # FastAPI app entry point + lifespan
│   ├── run_server.py              # Alternative server runner
│   ├── requirements.txt           # Python dependencies
│   ├── Dockerfile                 # Multi-stage Docker build
│   ├── docker-compose.yml         # MongoDB + Redis + Backend services
│   ├── serviceAccountKey.json     # Firebase Admin SDK credentials (ไม่ commit)
│   ├── .env                       # Backend environment variables
│   ├── data/                      # Runtime data (sessions, logs)
│   └── app/
│       ├── api/                   # REST API routers
│       │   ├── chat.py            # /api/chat — SSE streaming, TTS, Live Audio
│       │   ├── auth.py            # /api/auth — register, login, OTP verify
│       │   ├── booking.py         # /api/booking — Omise payment, saved cards
│       │   ├── travel.py          # /api/travel
│       │   ├── amadeus_viewer.py  # /api/amadeus-viewer — standalone search UI
│       │   ├── admin.py           # /api/admin — dashboard + notification simulator (no Amadeus Data Viewer)
│       │   ├── trips.py           # /api/trips — CRUD ทริปอิสระ + link-chat
│       │   ├── mcp.py             # /api/mcp — MCP tool testing
│       │   ├── monitoring.py      # /api/monitoring — cost tracking
│       │   ├── diagnostics.py     # /api/diagnostics
│       │   ├── options_cache.py   # /api/options-cache
│       │   └── notification.py    # /api/notification
│       ├── engine/                # AI core
│       │   ├── agent.py           # TravelAgent + AgentIntelligence (Two-Pass ReAct)
│       │   ├── gemini_agent.py    # Controller + Responder system prompts
│       │   ├── workflow_manager.py# Slot/segment state machine
│       │   ├── data_normalization.py # Min-Max normalization (0–1)
│       │   ├── reinforcement_learning.py # Per-user Q-learning (MongoDB)
│       │   └── cost_tracker.py    # LLM token/cost tracking
│       ├── services/              # Business logic
│       │   ├── llm.py             # Gemini LLM (retry + fallback + MCP support)
│       │   ├── travel_service.py  # TravelOrchestrator (Amadeus + Maps)
│       │   ├── data_aggregator.py # Search results → StandardizedItem + Weighted Sum
│       │   ├── memory.py          # Agent long-term memory (MongoDB)
│       │   ├── mcp_server.py      # MCP tool executor
│       │   ├── mcp_amadeus.py     # Amadeus MCP tools
│       │   ├── mcp_google_maps.py # Google Maps MCP tools
│       │   ├── mcp_weather.py     # Weather MCP (Open-Meteo, free)
│       │   ├── ml_keyword_service.py # Intent classification (ML: TF-IDF + MLP/LR)
│       │   ├── model_selector.py  # Auto model selection by task complexity
│       │   ├── options_cache.py   # In-memory options cache (TTL 24h)
│       │   ├── workflow_state.py  # In-memory workflow step tracker
│       │   ├── workflow_history.py# MongoDB workflow history
│       │   ├── selection_preferences.py # Choice history + RL aggregation (learn from user selections)
│       │   ├── agent_monitor.py   # Admin dashboard activity tracker
│       │   ├── google_maps_client.py # Google Maps client
│       │   ├── location_service.py# Geocoding + IATA conversion
│       │   ├── omise_service.py   # Payment gateway
│       │   ├── email_service.py   # Gmail SMTP — OTP emails
│       │   ├── tts_service.py     # Gemini TTS (Thai)
│       │   ├── live_audio_service.py # Gemini Live API (real-time voice)
│       │   ├── notification_service.py # Push notifications (booking/auth/alerts)
│       │   ├── notification_preferences.py # User notification settings
│       │   ├── checkin_reminder_service.py # Check-in alerts (24h + 2h before)
│       │   └── title.py           # Auto-generate chat titles
│       ├── orchestration/         # LangGraph graphs
│       │   ├── agent_mode_graph.py     # Agent Mode auto-select/book graph
│       │   ├── workflow_graph.py       # Main workflow state machine
│       │   ├── full_workflow_graph.py  # Full workflow (START→controller→execute→responder→END)
│       │   └── langchain_llm.py        # LangChain ChatGoogleGenerativeAI wrappers
│       ├── models/
│       │   ├── database.py        # MongoDB Pydantic schemas
│       │   ├── trip_plan.py       # TripPlan Pydantic V2 model
│       │   ├── session.py         # UserSession model
│       │   ├── actions.py         # ControllerAction, ActionType, ActionLog
│       │   └── visa.py            # Visa records + warnings (per user/family)
│       ├── storage/
│       │   ├── mongodb_storage.py # MongoDB CRUD (Motor async) — primary storage
│       │   ├── connection_manager.py # MongoDB connection pool singleton
│       │   ├── redis_storage.py   # (deprecated stub — ไม่ใช้แล้ว)
│       │   ├── redis_sync.py      # (deprecated stub — ไม่ใช้แล้ว)
│       │   ├── json_storage.py    # JSON file storage (fallback)
│       │   └── interface.py       # StorageInterface ABC
│       └── core/
│           ├── config.py          # Settings (python-dotenv) — มี flag `enable_redis_cache`, `redis_url`
│           ├── logging.py         # Structured logger
│           ├── exceptions.py      # Custom exceptions
│           ├── resilience.py      # Rate limiting + health monitor
│           ├── redis_client.py    # Optional Redis client (ใช้ REDIS_URL/settings.redis_url)
│           ├── redis_cache.py     # Redis-backed cache + in-memory fallback
│           └── redis_rate_limiter.py # Redis-backed rate limiter + in-memory fallback
└── frontend/
    ├── index.html
    ├── vite.config.js
    ├── package.json
    ├── .env                       # Frontend environment variables
    └── src/
        ├── App.jsx                # Root component + view routing (no React Router)
        ├── main.jsx               # React entry point
        ├── config/
        │   └── firebase.js        # Firebase SDK init + auth exports
        ├── pages/
        │   ├── auth/
        │   │   ├── LoginPage.jsx
        │   │   ├── RegisterPage.jsx
        │   │   ├── ResetPasswordPage.jsx
        │   │   ├── VerifyEmailPage.jsx       # OTP verification
        │   │   ├── VerifyEmailFirebasePage.jsx
        │   │   ├── VerifyEmailSentPage.jsx
        │   │   └── VerifyEmailChangePage.jsx # Email change OTP
        │   ├── chat/
        │   │   ├── AITravelChat.jsx          # Primary chat UI
        │   │   └── AITravelChat.css
        │   ├── home/
        │   │   └── HomePage.jsx
        │   ├── profile/
        │   │   └── UserProfileEditPage.jsx
        │   ├── settings/
        │   │   └── SettingsPage.jsx
        │   ├── bookings/
        │   │   ├── MyBookingsPage.jsx
        │   │   └── PaymentPage.jsx
        │   └── search/
        │       ├── FlightsPage.jsx
        │       ├── HotelsPage.jsx
        │       └── CarRentalsPage.jsx
        ├── components/
        │   ├── common/
        │   │   ├── AppHeader.jsx
        │   │   ├── HomeHeader.jsx
        │   │   └── NotificationPanel.jsx
        │   ├── chat/
        │   │   └── SlotCards.jsx
        │   └── bookings/
        │       ├── TripSummaryUI.jsx
        │       ├── PlanChoiceCard.jsx
        │       ├── PlanChoiceCardFlights.jsx
        │       ├── PlanChoiceCardHotels.jsx
        │       ├── PlanChoiceCardTransfer.jsx
        │       ├── PaymentPopup.jsx
        │       └── planChoiceCardUtils.js
        ├── styles/
        │   └── theme-content.css    # Dark/Light overrides (Settings, Bookings, Notifications, Payment, Chat, Flights/Hotels)
        ├── context/
        │   ├── ThemeContext.jsx
        │   ├── LanguageContext.jsx
        │   └── FontSizeContext.jsx
        ├── translations/
        │   ├── en.js
        │   └── th.js
        └── utils/
            ├── cardUtils.js
            ├── passwordHash.js
            ├── omiseLoader.js
            ├── userDataManager.js
            └── textCorrection.js
```

---

## 4. AI Engine — Two-Pass ReAct Architecture

### 4.1 TravelAgent (`engine/agent.py`)

```python
async def run_turn(
    session_id: str,
    user_input: str,
    status_callback: Optional[Callable[[str, str, str], Awaitable[None]]] = None,
    mode: str = "normal"  # "normal" | "agent"
) -> str
```

**Two-Pass Loop:**

```
Pass 1: Controller Brain (JSON only)
  └─ Input: user message + session state + current date
  └─ Output: ControllerAction (ActionType enum)
       ├─ CALL_SEARCH      → ค้นหา Amadeus/MCP
       ├─ SELECT_OPTION    → เลือกตัวเลือก
       ├─ CREATE_ITINERARY → สร้างแผนทริป
       ├─ UPDATE_REQ       → อัปเดต requirements
       ├─ ASK_USER         → ถามผู้ใช้
       ├─ COMPLETE         → จบการทำงาน
       └─ ERROR            → ข้อผิดพลาด

Pass 2: Responder Brain (Thai natural language)
  └─ Input: action log + session state
  └─ Output: Thai response string
```

**Controller Loop**: สูงสุด `CONTROLLER_MAX_ITERATIONS` รอบ (default 3)  
**Parallel Search**: `asyncio.gather` ค้นหา flights + hotels + transfers พร้อมกัน (timeout 35s)

### 4.2 AgentIntelligence (`engine/agent.py`)

Intelligence facade ประกอบด้วย:
- `SmartDateParser` — แปลงวันที่ไทย/พุทธศักราช/ภาษาธรรมชาติ
- `LocationIntelligence` — แปลง landmark → เมือง, หา IATA
- `BudgetAdvisor` — ประเมินงบประมาณรวมทั้งทริป (เที่ยวบิน + ที่พัก + การเดินทาง) และบังคับให้ **ราคารวมจากตัวเลือกที่เลือกแล้ว** ไม่เกินงบที่ผู้ใช้กำหนด (ใช้เป็น constraint หลักเวลาเลือกตัวเลือก)
- `InputValidator` — ตรวจสอบ input ก่อนส่งให้ Controller
- `ProactiveRecommendations` — แนะนำเชิงรุก
- `SelfCorrectionValidator` — ตรวจสอบ output ของ Controller

### 4.3 วางแผนทริปเริ่มจากศูนย์ (Start from Zero)

เมื่อ **CURRENT STATE ไม่มี segments** (แผนว่าง) Controller จะ:
- **โหมดปกติ:** Action แรกต้องเป็น **CREATE_ITINERARY** (ดึงจุดหมาย/วันที่จากข้อความหรือค่าเริ่มต้น) หรือ **ASK_USER** (ถามจุดหมาย/วันที่เท่านั้น) — ไม่ข้ามไป CALL_SEARCH/UPDATE_REQ
- **Agent Mode:** Action แรกต้องเป็น **CREATE_ITINERARY** เท่านั้น — infer ทุกอย่าง (origin=Bangkok, วันที่ถัดไป/สุดสัปดาห์, guests=1); ไม่ใช้ ASK_USER

กฎอยู่ใน `CONTROLLER_SYSTEM_PROMPT` (START FROM ZERO) และ prompt จะถูก inject ข้อความเตือนเมื่อตรวจพบแผนว่าง

### 4.4 LLM Service (`services/llm.py`)

| Class | คำอธิบาย |
|-------|-----------|
| `LLMService` | Gemini API calls + retry + exponential backoff + fallback chain |
| `LLMServiceWithMCP` | LLMService + MCP tool calling support |
| `IntentBasedLLM` | เลือก model ตาม intent |
| `BrainType` | enum: `controller` / `responder` / `searcher` |
| `ModelType` | enum: flash / pro / ultra |

### 4.5 LangGraph Orchestration (`orchestration/`)

| Graph | คำอธิบาย |
|-------|-----------|
| `workflow_graph.py` | Main state machine: planning → searching → selecting → summary → booking → done |
| `agent_mode_graph.py` | Agent Mode: auto-select + auto-book flow |
| `full_workflow_graph.py` | Full workflow (START → controller → execute → responder → END) |

### 4.6 Data Accuracy — ข้อมูลเที่ยวบินและที่พัก (`gemini_agent.py`)

ใน **CONTROLLER_SYSTEM_PROMPT** และ **RESPONDER_SYSTEM_PROMPT** กำหนดให้ AI เข้าใจและใช้ข้อมูลต่อไปนี้เมื่อสรุปการจอง/แสดง My Bookings/ตอบคำถามผู้ใช้:

| ประเภท | ข้อมูลที่ต้องมีความแม่นยำ |
|--------|---------------------------|
| **เที่ยวบิน** | PNR/รหัสจอง 6 หลัก, ชื่อสายการบิน + หมายเลขเที่ยวบิน, วันที่+เวลา (ออก/ถึง) เป็น**เวลาท้องถิ่น**, สนามบิน+รหัส IATA, เทอร์มินัล, สัมภาระ, ข้อมูลพาสปอร์ต (ถ้ามี) |
| **ที่พัก** | หมายเลขยืนยันการจอง (Confirmation Number), ชื่อ+ที่อยู่ละเอียด, วันที่ Check-in/Check-out + เวลาเข้าพักได้, นโยบายชำระเงิน/ยกเลิก, บริการเสริม (อาหารเช้า Wi‑Fi ที่จอดรถ ฯลฯ), เบอร์/อีเมลที่พัก (ถ้ามี) |

Responder มีกฎ **สรุปการจอง (Booking Summary)** ให้อ้างอิงและแสดงข้อมูลตามโครงด้านบนเท่าที่ระบบมี และระบุชัดเจนว่าเวลาเป็นเวลาท้องถิ่น

---

## 5. MCP Tools (Model Context Protocol)

### Amadeus MCP (`mcp_amadeus.py`)
| Tool | คำอธิบาย |
|------|-----------|
| `search_flights` | ค้นหาเที่ยวบิน (origin, destination, date, adults, non_stop) |
| `search_hotels` | ค้นหาโรงแรม (location, check_in, check_out, guests, radius) |
| `search_transfers` | ค้นหา transfer (airport ↔ city) |
| `search_transfers_by_geo` | ค้นหา transfer ด้วยพิกัด GPS |
| `search_activities` | ค้นหากิจกรรม/ทัวร์ |
| `book_flight` | จองเที่ยวบิน (Amadeus sandbox) |
| `book_hotel` | จองโรงแรม (Amadeus sandbox) |

### Google Maps MCP (`mcp_google_maps.py`)
| Tool | คำอธิบาย |
|------|-----------|
| `geocode_location` | แปลงชื่อสถานที่ → พิกัด lat/lng |
| `find_nearest_airport` | หาสนามบินที่ใกล้ที่สุด (IATA code) |
| `plan_route` | วางแผนเส้นทาง A → B |
| `plan_route_with_waypoints` | เส้นทางหลายจุดแวะ |
| `search_nearby_places` | ค้นหาสถานที่ใกล้เคียง |
| `get_place_details` | รายละเอียดสถานที่จาก place_id |
| `compare_transport_modes` | เปรียบเทียบ รถ/ขนส่งสาธารณะ/เดิน |

### Weather MCP (`mcp_weather.py`)
| Tool | คำอธิบาย |
|------|-----------|
| `get_weather_forecast` | พยากรณ์อากาศ (Open-Meteo, ฟรี ไม่ต้องมี API key) |
| `get_destination_timezone` | timezone + เวลาท้องถิ่น |

---

## 6. ML/DL Ranking System

ระบบนี้ใช้ **ML/DL และ RL 2 ชั้นหลักๆ**:  
- ชั้นแรกคือ **LLM ภายนอก (Gemini)** ซึ่ง Google เทรนมาล่วงหน้า (อาจมี RLHF ภายใน) ใช้สำหรับเข้าใจภาษาธรรมชาติ วางแผนทริป และสร้างคำตอบ แต่เรา *ไม่ฝึกโมเดลนี้ต่อในระบบ*  
- ชั้นที่สองคือ **ML/RL ภายในระบบเอง** (ส่วนนี้สรุปในหัวข้อ 6.1–6.5) ได้แก่ intent classifier (TF‑IDF + LR/MLP), weighted‑score ranking, Q‑Learning (`reinforcement_learning.py`) และ aggregation จากประวัติการเลือก (`selection_preferences.py`) เพื่อ re‑rank ตัวเลือกก่อนส่งให้ LLM เลือก — RL ในระบบจึงทำหน้าที่เป็น **signal เสริมในการจัดอันดับตัวเลือก** ไม่ได้ควบคุมการสนทนาโดยตรง

### 6.1 Intent Classification (2-Tier)

```
Tier 1: TF-IDF + MLPClassifier (scikit-learn, hidden: 256→128→64, ReLU, Adam)
    ↓ fallback
Tier 2: TF-IDF + LogisticRegression (CalibratedClassifierCV, ~90% accuracy)
```

**Intents**: `flight`, `hotel`, `transport`, `date`, `destination`, `booking`, `edit`, `general`

### 6.2 Weighted Sum Scoring (`data_aggregator.py`)

สูตร: **S_i = Σ w_j × norm_j(x_ij)**

Min-Max normalization ก่อน (lower-is-better criteria ถูก invert):

| ประเภท | price | duration | stops | rating | review_count | distance |
|--------|-------|----------|-------|--------|--------------|----------|
| flight | 0.35 | 0.30 | 0.20 | 0.10 | 0.05 | — |
| hotel | 0.30 | — | — | 0.35 | 0.20 | 0.15 |
| transfer | 0.40 | 0.35 | — | 0.25 | — | — |
| default | 0.50 | — | — | 0.30 | 0.20 | — |

ผล: `StandardizedItem.weighted_score` (0–1, สูง = ดี)

### 6.3 Reinforcement Learning (`reinforcement_learning.py`)

**Algorithm**: Q-Learning แบบ episodic (per-user, per-slot)

| Parameter | Value |
|-----------|-------|
| ALPHA (learning rate) | 0.3 |
| GAMMA (discount factor) | 0.9 |
| Q-table storage | MongoDB `user_preference_scores` |
| Reward history | MongoDB `user_feedback_history` |
| Max history per user | 500 records |

**Reward values:**
| Action | Reward |
|--------|--------|
| เลือกตัวเลือก | +0.3 |
| จองสำเร็จ | +1.0 |
| Feedback บวก | +0.5 |
| ปฏิเสธตัวเลือก | −0.2 |
| ยกเลิกการจอง | −0.5 |
| Feedback ลบ | −0.3 |
| แก้ไขการเลือก | −0.1 |

**Integration กับ Agent Mode:**
```
final_score = weighted_score (0–1) + rl_bonus (0–0.2)
rl_bonus = (Q_value + 1.0) / 2.0 × 0.20   # map Q∈[-1,+1] → [0, 0.2]
```

Options ถูก re-rank ตาม `final_score` ก่อนส่งให้ LLM เลือก

### 6.4 Auto Model Selection (`model_selector.py`)

เลือก Gemini model ตาม task complexity อัตโนมัติ  
เปิดด้วย `ENABLE_AUTO_MODEL_SWITCHING=true` ใน `.env`

### 6.5 Selection Preferences (Choice History + RL/ML)

| ส่วน | คำอธิบาย |
|------|-----------|
| **Collection** | `user_choice_history` — บันทึกทุกครั้งที่ผู้ใช้เลือกตัวเลือก (flight/hotel/transport): slot, ราคา, จุดหมาย, ต้นทาง, ชื่อสายการบิน/ที่พัก |
| **Service** | `app/services/selection_preferences.py` — `record_choice()`, `get_selection_preferences_summary()` |
| **Aggregation** | สรุปจาก choice history + RL (`user_feedback_history` / `user_preference_scores`) เป็นข้อความ: ช่วงราคาที่เลือกบ่อย, จุดหมายที่ไปบ่อย, สายการบิน/ที่พักที่เลือกบ่อย |
| **User Profile** | ใส่ block "ความชอบจากการเลือก (RL+ประวัติการเลือก)" ใน `_get_user_profile_context()` — แชทและ Agent Mode ใช้ |
| **Agent Mode** | Selection prompt มี "SELECTION PREFERENCES (from past choices + RL)" ร่วมกับ RL scores และ ML intent |
| **Opt-in** | `preferences.learnFromMyChoices` (default true) — ปิดได้ในโปรไฟล์; ไม่บันทึก/ไม่ใส่ใน context ถ้าปิด |

---

## 7. Authentication Flow

### Email/Password Registration
```
1. กรอกฟอร์ม → POST /api/auth/register
2. Backend: สร้าง user ใน MongoDB, generate OTP (6 หลัก, หมดอายุ 4 นาที)
3. Backend: ส่ง OTP ผ่าน Gmail SMTP
4. ผู้ใช้รับอีเมล → กรอก OTP ในหน้า VerifyEmailPage
5. Frontend: POST /api/auth/verify-email { otp }
6. Backend: ตรวจสอบ OTP + อายุ → set email_verified=True ใน MongoDB
7. SweetAlert "ยืนยันอีเมลสำเร็จ!" → redirect ไปหน้า Login
```

### Google Login
```
1. Firebase Google Sign-In (popup) → idToken
2. POST /api/auth/firebase → verify token กับ Firebase Admin
3. Backend: ดึง email_verified จาก Firebase token → set ใน MongoDB อัตโนมัติ
4. ไม่ต้องยืนยันอีเมลเพิ่ม (Google/Firebase ยืนยันให้แล้ว)
```

### Login Block
- ถ้า `email_verified=false` → 403 `EMAIL_NOT_VERIFIED` → ส่ง OTP ใหม่ผ่าน Gmail SMTP → redirect ไปหน้า verify-email-sent

### 7.4 การส่งอีเมลและสุ่มเลข OTP

#### การส่งอีเมล (Email Service)
- **ที่อยู่โค้ด**: `app/services/email_service.py` — คลาส `EmailService` + ฟังก์ชัน `_send_gmail()`
- **โปรโตคอล**: Gmail SMTP แบบ SSL (พอร์ต 465) ผ่าน `smtplib.SMTP_SSL("smtp.gmail.com", 465)`
- **การตั้งค่า**: ใช้ตัวแปรจาก `.env`
  - `GMAIL_USER` — อีเมล Gmail ที่ใช้ส่ง (เช่น `user@gmail.com`)
  - `GMAIL_APP_PASSWORD` — รหัสผ่านแอป (App Password) จาก [Google Account → Security → App passwords](https://myaccount.google.com/apppasswords) (ไม่ใช้รหัสผ่านเข้าสู่ระบบปกติ)
- **การส่ง**: สร้าง `MIMEMultipart` แนบ HTML (UTF-8) เป็นเนื้อหาอีเมล → `server.login()` แล้ว `server.sendmail()` ไปยัง `to_email`
- **จุดที่เรียกใช้**:
  - สมัครสมาชิก: หลังสร้าง user → ส่ง OTP ยืนยันอีเมล
  - ส่ง OTP ใหม่: `POST /api/auth/send-verification-email`
  - เปลี่ยนอีเมล: ส่ง OTP ไปอีเมลใหม่ (`send_email_change_otp`)
  - ลืมรหัสผ่าน: `POST /api/auth/send-reset-password-otp` → ส่ง OTP รีเซ็ตรหัสผ่าน

#### การสุ่มเลข OTP
- **ที่อยู่โค้ด**: `EmailService.generate_verification_token()` ใน `app/services/email_service.py`
- **วิธีสุ่ม**: ใช้โมดูล **`secrets`** (cryptographically secure random) ของ Python
  - `secrets.randbelow(1000000)` — สุ่มจำนวนเต็มในช่วง `[0, 999999]`
  - จัดรูปแบบเป็น **6 หลัก** (เติมศูนย์ด้านหน้า): `f"{secrets.randbelow(1000000):06d}"`
  - ตัวอย่างผลลัพธ์: `"042817"`, `"999000"`
- **ความปลอดภัย**: `secrets` เหมาะสำหรับค่าแบบ token/OTP มากกว่า `random` เพราะกันการคาดเดาจากผู้โจมตี
- **อายุ OTP**: หลังส่ง ระบบบันทึก `email_verification_sent_at` (หรือ `reset_password_otp_sent_at`) ใน MongoDB — ตอนตรวจ OTP เปรียบเทียบกับ `datetime.utcnow()` ถ้าเกิน **4 นาที** ถือว่าหมดอายุ และส่งข้อความ "รหัส OTP หมดอายุ (4 นาที) กรุณาขอรหัสใหม่"

### 7.5 การตั้งค่าความเป็นส่วนตัว (Privacy Settings)

อยู่ใน **การตั้งค่า (Settings)** → ส่วน **ความเป็นส่วนตัว** — เก็บใน `users.preferences` และ sync กับ backend ผ่าน `savePreferencesToBackend`.

| รายการ | UI | คำอธิบาย |
|--------|-----|----------|
| **ระดับความเป็นส่วนตัว** (Privacy Level) | Dropdown | **ส่วนตัว (private)** = ห้ามแชร์ข้อมูลผู้ใช้ทุกอย่างให้ AI: ไม่ส่ง user profile, ไม่ส่งความจำ (memory), ไม่ส่งความชอบการเดินทาง (travel preferences) ให้ AI และไม่เรียนรู้จากบทสนทนา (ไม่ consolidate). **สาธารณะ (public)** = ใช้ค่าจาก "การแชร์ข้อมูลให้ AI" ตามปกติ (ส่ง profile/memory/preferences ได้ ถ้าเปิดแชร์) |
| **การแชร์ข้อมูลให้ AI** (Data Sharing) | Toggle เปิด/ปิด | เมื่อระดับเป็น **สาธารณะ**: เปิด = ระบบทำ memory consolidation และส่งความชอบให้ AI; ปิด = ไม่เรียนรู้จากบทสนทนา. เมื่อระดับเป็น **ส่วนตัว**: ไม่ส่งข้อมูลผู้ใช้ให้ AI ไม่ว่าตัวนี้จะเปิดหรือปิด |

- **ที่อยู่ Frontend**: `frontend/src/pages/settings/SettingsPage.jsx` — `handlePrivacyChange('privacyLevel' | 'dataSharing' | ...)` แล้ว `savePreferencesToBackend(next)` ส่งไป `PUT /api/auth/profile` เก็บใน `users.preferences`  
- **ที่อยู่ Backend**: `app/engine/agent.py` — ใช้ `_is_private_mode(user_id)` ตรวจ `privacyLevel === 'private'`; ถ้าส่วนตัว จะไม่โหลด memory, ไม่ส่ง user profile, เคลียร์ travel_preferences และไม่เรียก consolidate. `app/services/memory.py` — ก่อน `consolidate()` ตรวจ `privacyLevel` และ `dataSharing` เช่นกัน

---

## 8. Session & Data Flow

```
User Message
    │
    ▼
chat.py (SSE streaming endpoint)
    │ validate session ownership
    │ rate limit check
    ▼
TravelAgent.run_turn()
    │
    ├─ Controller Brain (Gemini) → ControllerAction
    │   ├─ CALL_SEARCH → asyncio.gather([search_flights, search_hotels, search_transfers])
    │   │   ├─ MCP tools (timeout 20s each)
    │   │   └─ DataAggregator → Weighted Sum scoring → StandardizedItem[]
    │   ├─ SELECT_OPTION → SlotManager.set_segment_selected()
    │   │   └─ RL: record_reward("select_option", +0.3)
    │   ├─ CREATE_ITINERARY → build TripPlan
    │   └─ COMPLETE → exit loop
    │
    ├─ [Agent Mode] _run_agent_mode_auto_complete()
    │   ├─ RL: get_option_scores() → Q-values
    │   ├─ Compute final_score = weighted_score + rl_bonus
    │   ├─ Re-rank options
    │   ├─ Gemini Intelligence: select best option
    │   └─ Auto-book → POST /api/booking/create → Omise payment
    │
    ├─ Responder Brain (Gemini) → Thai response
    │
    ├─ Memory: consolidate() [fire-and-forget]
    └─ Storage: save_session() → MongoDB Atlas (real-time)
```

### Storage Architecture
| ประเภทข้อมูล | เก็บที่ | อายุ | หายเมื่อ |
|-------------|---------|------|----------|
| บทสนทนา (sessions/conversations) | **MongoDB Atlas** | ถาวร | ลบด้วยตัวเอง |
| Long-term memory | **MongoDB Atlas** (`memories`) | ถาวร | ลบด้วยตัวเอง |
| Q-table (RL) | **MongoDB Atlas** (`user_preference_scores`) | ถาวร | ลบด้วยตัวเอง |
| Options cache (ตัวเลือกเที่ยวบิน/โรงแรม) | **In-process memory** (Python dict) | 24h | restart backend |
| Workflow state (step tracker) | **In-process memory** | session | restart backend |

### 8.1 Frontend Chat (AITravelChat) — Cache-First & Persistence

| เหตุการณ์ | พฤติกรรม |
|-----------|----------|
| **เปิดแชทครั้งแรก** | โหลดรายการ sessions จาก backend → bulk fetch ประวัติทุกแชทครั้งเดียว (`GET /api/chat/histories?chat_ids=...`) → เก็บใน `historyCache` (in-memory Map) |
| **กดเปลี่ยนแชท** | อ่านจาก `historyCache` ทันที — ไม่ fetch ซ้ำ, ไม่ spinner |
| **ส่งข้อความใหม่** | อัปเดต `trips` state + sync เข้า `historyCache` |
| **ลบแชท** | ลบจาก `loadedTripsRef` + `historyCache` + backend + UI |
| **ปิดหน้า/แท็บ** | `beforeunload` + unmount: save snapshot (trips + messages จาก cache) ลง localStorage |

- **Trip Selector Bar**: ถูกลบออก — AI จัดการ trip context เอง
- **TripSummaryUI (TripSummaryCard + FinalTripSummary)**: แสดง**เฉพาะเมื่อ**ผู้ใช้พิมพ์ข้อความที่มีคำว่า **"จองเลย"** ในประโยค; เมื่อเปลี่ยนแชทจะ reset (ซ่อนจนกว่าจะพิมพ์ "จองเลย" อีกครั้ง)

---

## 9. MongoDB Collections

| Collection | คำอธิบาย | Indexes หลัก |
|-----------|---------|-------------|
| `sessions` | Chat sessions + TripPlan state | unique `session_id`, `user_id`, `last_updated` |
| `users` | User accounts, profiles, family members | unique `user_id`, unique sparse `email`, `last_active` |
| `memories` | AI long-term memory per user | `user_id`, `importance`, `category`, compound `(user_id, importance)` |
| `bookings` | Confirmed bookings | unique sparse `booking_id`, `user_id`, `status`, `created_at` |
| `conversations` | Message history per session | `session_id`, `user_id`, compound `(session_id, updated_at)` |
| `user_saved_cards` | Omise saved cards per user | unique `user_id`, `updated_at` |
| `workflow_history` | Workflow step transitions (analytics) | compound `(session_id, ts)`, `(user_id, ts)` |
| `user_preference_scores` | คะแนนความชอบผู้ใช้ (RL Q-table) | unique compound `(user_id, slot_name, option_key)` |
| `user_feedback_history` | ประวัติ feedback / reward | compound `(user_id, created_at)`, `(user_id, slot_name)` |
| `user_choice_history` | ประวัติการเลือกตัวเลือก (Selection Preferences) | `user_id`, `created_at` |
| `trips` | ทริปอิสระจากแชท (trip_id, chat_ids[]) | unique `trip_id`, `user_id` |

> Index creation ใช้ `create_indexes_safe()` — handle `OperationFailure` code 85 gracefully (ไม่ crash ถ้า index conflict)

---

## 10. API Endpoints (ครบทุก endpoint)

### Chat (`/api/chat`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| POST | `/api/chat/stream` | SSE streaming chat (หลัก) |
| POST | `/api/chat` | Non-streaming chat |
| GET | `/api/chat/history/{client_trip_id}` | ประวัติบทสนทนาของ trip |
| GET | `/api/chat/histories` | Bulk ประวัติทุกแชทในครั้งเดียว (cache-first, query param `chat_ids`) |
| GET | `/api/chat/sessions` | รายการ sessions ของ user |
| POST | `/api/chat/select_choice` | เลือก plan_choices / slot_choices จาก Agent |
| POST | `/api/chat/tts` | แปลงข้อความเป็นเสียง (Gemini TTS) |
| WS | `/api/chat/live-audio` | WebSocket real-time voice (Gemini Live API) |
| DELETE | `/api/chat/sessions/{chat_id}` | ลบ session + ประวัติบทสนทนา |
| POST | `/api/chat/reset` | Reset chat context |
| POST | `/api/chat/auto-delete-old` | ลบ sessions เก่ากว่า N วัน |
| POST | `/api/chat/flush-session` | No-op (MongoDB-only mode) |

### Trips (`/api/trips`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| GET | `/api/trips` | รายการทริปของ user |
| POST | `/api/trips` | สร้างทริปใหม่ |
| GET | `/api/trips/{trip_id}` | รายละเอียดทริป |
| PATCH | `/api/trips/{trip_id}` | แก้ไขชื่อ/สถานะทริป |
| DELETE | `/api/trips/{trip_id}` | ลบทริป |
| POST | `/api/trips/{trip_id}/link-chat` | เชื่อมแชทกับทริป |
| GET | `/api/trips/{trip_id}/chats` | รายการแชทที่เชื่อมกับทริป |

### Auth (`/api/auth`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| POST | `/api/auth/register` | สมัครสมาชิก (ส่ง OTP ยืนยัน) |
| POST | `/api/auth/login` | เข้าสู่ระบบ |
| POST | `/api/auth/logout` | ออกจากระบบ |
| GET | `/api/auth/me` | ข้อมูลผู้ใช้ปัจจุบัน |
| POST | `/api/auth/google` | Google login (Firebase token) |
| POST | `/api/auth/send-verification-email` | ส่ง OTP ใหม่ (Gmail SMTP) |
| POST | `/api/auth/verify-email` | ยืนยันอีเมลด้วย OTP (หมดอายุ 4 นาที) |
| POST | `/api/auth/verify-email-firebase` | ยืนยันอีเมล (Firebase oobCode) |
| POST | `/api/auth/forgot-password` | ลืมรหัสผ่าน |
| POST | `/api/auth/reset-password` | รีเซ็ตรหัสผ่าน |

### Booking (`/api/booking`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| POST | `/api/booking/create` | สร้าง booking ใหม่ |
| GET | `/api/booking/list` | รายการ bookings ของ user |
| POST | `/api/booking/payment` | ชำระเงิน booking |
| POST | `/api/booking/cancel` | ยกเลิก booking |
| PUT | `/api/booking/update` | แก้ไข booking |
| POST | `/api/booking/create-charge` | สร้าง Omise charge จาก token |
| GET | `/api/booking/payment-config` | Omise public key สำหรับ frontend |
| GET | `/api/booking/payment-page/{booking_id}` | หน้าชำระเงิน |
| GET | `/api/booking/omise.js` | Proxy Omise.js CDN (หลีกเลี่ยง ad-blocker) |
| GET | `/api/booking/saved-cards` | รายการบัตรที่บันทึกไว้ |
| POST | `/api/booking/saved-cards` | เพิ่มบัตร (Omise customer + MongoDB) |
| PUT | `/api/booking/saved-cards/{card_id}/set-primary` | ตั้งบัตรหลัก |
| POST | `/api/booking/saved-cards/add-local` | เพิ่มบัตรใน MongoDB เท่านั้น |
| DELETE | `/api/booking/saved-cards/{card_id}` | ลบบัตร |
| POST | `/api/booking/test-omise` | ทดสอบ Omise connection |
| GET | `/api/booking/test-omise` | ทดสอบ Omise config |

### Monitoring (`/api/monitoring`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| GET | `/api/monitoring/cost/session/{session_id}` | Cost summary ของ session |
| GET | `/api/monitoring/cost/all` | Cost ทุก sessions |
| GET | `/api/monitoring/cost/breakdown/{session_id}` | Cost แยกตาม brain type |
| POST | `/api/monitoring/cost/reset/{session_id}` | Reset cost tracking |
| GET | `/api/monitoring/health` | Health check |
| POST | `/api/monitoring/sync/redis/session/{session_id}` | No-op (cache layer; session in MongoDB) |
| POST | `/api/monitoring/sync/redis/all` | No-op (Redis เป็น cache; source of truth คือ MongoDB) |
| GET | `/api/monitoring/sync/redis/status` | สถานะ Redis (redis_available เมื่อ REDIS_URL ตั้งค่า) |

### Health (`/health`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| GET | `/health` | Health check (MongoDB + Redis status when REDIS_URL set) |

### Admin (backend HTML + cookie auth)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| GET | `/admin` | แดชบอร์ดแอดมิน (แสดงหน้า login ถ้ายังไม่มี cookie ที่ถูกต้อง) |
| POST | `/admin/login` | รับ username/password จากฟอร์ม → ตั้ง cookie `admin_session` → redirect /admin |
| GET | `/admin/logout` | ลบ cookie → redirect /admin |

---

## 11. Data Models

### StandardizedItem (`data_aggregator.py`)
```python
class StandardizedItem(BaseModel):
    id: str
    category: ItemCategory          # flight | hotel | transfer | activity
    provider: str
    display_name: str
    price_amount: float
    currency: str                   # default: "THB"
    is_price_available: bool
    rating: Optional[float]
    duration: Optional[str]         # ISO 8601: "PT2H30M"
    description: Optional[str]
    location: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    deep_link_url: Optional[str]
    raw_data: Dict[str, Any]
    tags: List[str]                 # ["ถูกสุด", "เร็วที่สุด", "แนะนำ"]
    recommended: bool
    weighted_score: float           # 0–1, Weighted Sum score
```

### TripPlan (`models/trip_plan.py`)
```
TripPlan
└── travel: TravelPlan
    ├── flights: FlightPlan
    │   ├── outbound: Segment[]
    │   └── inbound: Segment[]
    ├── accommodation: AccommodationPlan
    │   └── segments: Segment[]
    └── transport: TransportPlan
        └── segments: Segment[]

Segment
├── slot_name: str
├── requirements: Dict
├── options_pool: List[Dict]    # StandardizedItem.model_dump()
├── selected_index: Optional[int]
└── status: SegmentStatus       # PENDING | SEARCHING | SELECTING | SELECTED | BOOKED
```

### User (`models/database.py`)
```python
class User(BaseModel):
    user_id: str                    # "user_XXXXXXXXXX"
    email: str
    email_verified: bool
    name_th: Optional[str]          # ชื่อภาษาไทย
    name_en: Optional[str]          # ชื่อภาษาอังกฤษ
    phone: Optional[str]
    passports: List[Dict[str, Any]]         # Multi-passport (รองรับหลายเล่ม)
    primary_passport: Optional[Dict[str, Any]]
    passport_warnings: List[str]            # เช่น 6-month rule / หมดอายุ
    visa_records: List[Dict[str, Any]]      # Multi-visa (รองรับหลายประเทศ/หลายประเภท)
    visa_warnings: List[str]                # เตือน linked_passport ไม่ตรงกับเล่มปัจจุบัน ฯลฯ
    passport_number: Optional[str]          # legacy (sync จาก primary passport เพื่อ backward compatibility)
    family_members: List[FamilyMember]
    omise_customer_id: Optional[str]
    created_at: datetime
    last_active: datetime
```

### Multi-Passport (แนวคิดหลัก)

- **หนึ่งคนมีได้หลายเล่ม** (`passports[]`) แต่ **หนึ่งทริปควรใช้ 1 เล่ม** เป็นหลัก (เลือกจาก `primary_passport` หรือให้ผู้ใช้เลือกก่อนยืนยันจอง)
- **Validity**: ใช้เฉพาะเล่มที่ยังไม่หมดอายุและสถานะ `active`
- **6-Month Rule**: ระบบสร้าง `passport_warnings` ถ้าเหลืออายุ < 6 เดือน

### Multi-Visa (แนวคิดหลัก)

- **หนึ่งคนมีวีซ่าได้ไม่จำกัด** (`visa_records[]`) — หลายประเทศพร้อมกัน/หลายประเภทต่อประเทศ
- **วีซ่าผูกกับพาสปอร์ต** (`linked_passport`) หากผู้ใช้เปลี่ยนเล่ม ระบบใส่ `visa_warnings` เพื่อเตือนให้พกเล่มเดิม

### โครงข้อมูล Fare Rules / Fare Details (เที่ยวบิน)

เงื่อนไขตั๋ว (Refund, Change, Check-in, Baggage, Fare Type) ออกแบบเป็น canonical schema รองรับการแสดง Badge คืนเงินได้/ไม่ได้, สรุปเงื่อนไขก่อนชำระเงิน และการ map จาก Amadeus (pricingOptions, fareDetailsBySegment, Fare Rules API ในอนาคต) โดยมีโครงสร้างหลักดังนี้:

- **Refund Policy:** `non_refundable` | `refundable_fee` | `full_refund`
- **Change Policy:** รองรับ `fee_amount`, `plus_fare_difference`, `time_limit_hours`
- **Check-in Policy:** ข้อมูลเวลาเปิด/ปิดเช็คอินออนไลน์ และเวลาที่ควรถึงสนามบิน
- **Baggage:** แยก `checked` และ `carry_on`

---

## 12. Environment Variables (ครบทุกตัว)

### Backend (`.env`)
```bash
# Gemini LLM
GEMINI_API_KEY=
GEMINI_FLASH_MODEL=gemini-2.5-flash
GEMINI_PRO_MODEL=gemini-2.5-pro
GEMINI_LIVE_AUDIO_MODEL=gemini-2.5-flash-native-audio-preview-12-2025
GEMINI_TTS_MODEL=gemini-2.5-flash-preview-tts

# LLM Behavior
LLM_MAX_RETRIES=3
LLM_TIMEOUT=120
CONTROLLER_MAX_ITERATIONS=3
CONTROLLER_TIMEOUT=120
CONTROLLER_TEMPERATURE=0.3
RESPONDER_TEMPERATURE=0.7
CHAT_TIMEOUT_AGENT=180
CHAT_TIMEOUT_NORMAL=120
ENABLE_AUTO_MODEL_SWITCHING=false    # เปิดเพื่อ auto-select model

# LangGraph Flags
ENABLE_LANGCHAIN_ORCHESTRATION=true
ENABLE_LANGGRAPH_AGENT_MODE=true
ENABLE_LANGGRAPH_CHECKPOINTER=true
ENABLE_LANGGRAPH_FULL_WORKFLOW=true

# Google Maps
GOOGLE_MAPS_API_KEY=

# Amadeus (Search — Production)
AMADEUS_SEARCH_ENV=production
AMADEUS_CLIENT_ID=
AMADEUS_CLIENT_SECRET=
AMADEUS_API_KEY=                     # legacy fallback
AMADEUS_API_SECRET=                  # legacy fallback
AMADEUS_CACHE_TTL=3600

# Amadeus (Booking — Sandbox เท่านั้น)
AMADEUS_BOOKING_ENV=test
AMADEUS_BOOKING_CLIENT_ID=
AMADEUS_BOOKING_CLIENT_SECRET=
AMADEUS_DISABLE_PROD_BOOKING=1       # safety guard

# MongoDB Atlas
MONGO_URI=mongodb+srv://<user>:<pass>@cluster0.xxxxx.mongodb.net/?appName=Cluster0
MONGO_DB_NAME=travel_agent

# Auth
SECRET_KEY=                          # ต้องเปลี่ยนก่อน production
GOOGLE_CLIENT_ID=

# Firebase Admin SDK
FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json

# Admin Dashboard
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=              # ใช้กับหน้า login และ Basic Auth
ADMIN_ENABLED=true
ADMIN_REQUIRE_AUTH=true      # เปิดแล้วใช้หน้า login ที่ /admin (cookie) หรือ Basic Auth

# Payment (Omise)
OMISE_SECRET_KEY=
OMISE_PUBLIC_KEY=

# Gmail SMTP
GMAIL_USER=
GMAIL_APP_PASSWORD=                  # App Password จาก myaccount.google.com/apppasswords

# App
FRONTEND_URL=http://localhost:5173
API_HOST=0.0.0.0
API_PORT=8000
API_BASE_URL=http://localhost:8000   # Internal URL สำหรับ Agent Mode booking call
SITE_NAME=AI Travel Agent

# Storage
DATA_DIR=./data
SESSIONS_DIR=./data/sessions

# Logging
LOG_LEVEL=INFO
```

### Frontend (`.env`)
```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=
VITE_GOOGLE_MAPS_API_KEY=
VITE_FIREBASE_ENABLED=true
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
```

---

## 13. Python Dependencies (`requirements.txt`)

```
fastapi==0.115.5
uvicorn[standard]==0.30.6
python-dotenv==1.0.1
pydantic==2.8.2
amadeus==9.0.0
google-genai==0.6.0
google-generativeai>=0.8.0
googlemaps==4.10.0
httpx==0.27.2
aiofiles==24.1.0
tenacity==9.0.0
motor==3.6.0
pymongo>=4.9,<4.10
psutil==5.9.8
redis==7.1.0                 # package ยังอยู่ใน requirements แต่ไม่ได้ใช้งานแล้ว
omise==0.10.0
passlib[bcrypt]==1.7.4
watchdog==6.0.0
firebase-admin>=6.5.0
python-dateutil>=2.8.2
numpy>=1.24.0
scikit-learn>=1.3.0
langchain>=0.3.0
langchain-core>=0.3.0
langchain-google-genai>=2.0.0
langgraph>=0.2.0
langgraph-checkpoint-redis>=0.3.0
```

---

## 14. npm Dependencies (`package.json`)

```json
"dependencies": {
  "@react-google-maps/api": "^2.20.8",
  "firebase": "^10.13.2",
  "lottie-react": "^2.4.1",
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "sweetalert2": "^11.26.17"
},
"devDependencies": {
  "@tailwindcss/postcss": "^4.2.1",
  "@vitejs/plugin-react": "^4.3.1",
  "autoprefixer": "^10.4.27",
  "baseline-browser-mapping": "^2.9.12",
  "postcss": "^8.5.8",
  "tailwindcss": "^4.2.1",
  "vite": "^5.4.3"
}
```

---

## 15. Docker

### `Dockerfile` (Multi-stage build)
```
Stage 1 — Builder:
  base: python:3.12-slim
  install: gcc, g++
  pip install: requirements.txt → /install

Stage 2 — Production:
  base: python:3.12-slim
  copy: /install → site-packages
  copy: app code
  create: /app/data/sessions, /app/logs
  user: appuser (UID 1000, non-root)
  expose: 8000
  healthcheck: GET http://localhost:8000/health (30s interval, 10s timeout, 3 retries)
  cmd: python main.py
```

### `docker-compose.yml`
| Service | Image | Port | Notes |
|---------|-------|------|-------|
| `mongodb` | `mongo:7.0` | `27017:27017` | volume: `mongodb_data`, DB: `travel_agent` |
| `redis` | `redis:7-alpine` | `6379:6379` | AOF persistence, volume: `redis_data` (ใช้กับ LangGraph Redis checkpointer เมื่อกำหนด `REDIS_URL`) |
| `backend` | Built from `./Dockerfile` | `8000:8000` | พึ่งพา MongoDB เป็นหลัก; Redis เป็น optional สำหรับ LangGraph/อนาคต |

> **หมายเหตุ**: core backend (options cache, rate limit ฯลฯ) ยังใช้ in-memory; Redis service ใน `docker-compose.yml` ใช้เฉพาะกรณีที่เปิด LangGraph Redis checkpointer หรือ integration อื่นที่ต้องการ `REDIS_URL`

---

## 16. Production Hardening (Implemented)

| ส่วน | การแก้ไข |
|------|-----------|
| **Gemini Retry** | 3 attempts/model, exponential backoff (2→4→8s), fallback chain |
| **Gemini SDK** | อัปเกรดจาก `google-generativeai` (deprecated) เป็น `google.genai` v0.6.0 |
| **Amadeus Token** | `asyncio.Lock` ป้องกัน concurrent refresh race condition |
| **LRU Cache** | `_geocoding_cache` + `_iata_cache` จำกัด 500 entries (evict oldest) |
| **Input Validation** | `message` max 4000 chars, `mode` allowlist (`normal`/`agent`) |
| **Debug Logs** | ปิดโดย default, rotate เมื่อเกิน 10 MB |
| **Startup Validation** | `SECRET_KEY` default → `RuntimeError` ใน production |
| **MCP Timeout** | `asyncio.wait_for(..., timeout=20s)` สำหรับ MCP tools |
| **Auto-select Guard** | `_auto_select_in_progress` flag + `finally` reset |
| **RL Init** | Q-value initial = `ALPHA × reward` (สอดคล้องกับ update rule) |
| **MongoDB Atlas** | ใช้ Atlas cloud — ไม่ต้องรัน MongoDB local |
| **Redis (optional)** | เมื่อกำหนด `REDIS_URL` และเปิด `ENABLE_REDIS_CACHE` จะใช้ Redis ผ่าน `redis_client.py` สำหรับ cache (`redis_cache.py`), rate limit (`redis_rate_limiter.py`) และ LangGraph Redis checkpointer; ถ้าไม่ตั้งค่าจะ fallback เป็น in-memory ทั้งหมด |
| **Index Safety** | `create_indexes_safe()` handle conflict gracefully ไม่ crash |
| **Session Security** | `session_id.split("::")[0] == user_id` ownership check |
| **Omise.js Proxy** | Backend proxy หลีกเลี่ยง ad-blocker/CORS |

---

## 17. การรันระบบ

```bash
# 1. Backend
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 2. Frontend
cd frontend
npm run dev
# → http://localhost:5173
```

**Prerequisites:**
- Python 3.12+
- Node.js 18+
- MongoDB Atlas (ตั้งค่า `MONGO_URI` ใน `backend/.env`)
- Redis (optional) — ใช้ได้เมื่อกำหนด `REDIS_URL` และ/หรือเปิด `ENABLE_REDIS_CACHE`; ถ้าไม่ตั้งค่า ระบบจะใช้ in-memory cache/rate limit และ LangGraph checkpoint จะไม่ใช้ Redis
- MongoDB Atlas จำเป็น (หรือ MongoDB local)

---

## 18. Known Limitations

| ส่วน | ข้อจำกัด |
|------|-----------|
| Amadeus Booking | ใช้ sandbox เท่านั้น — ไม่จองจริง |
| Email | Gmail SMTP ส่งได้ทุกอีเมลทุกค่าย · OTP หมดอายุ 4 นาที · ต้องมี App Password |
| Options Cache | ใช้ **in-process memory** (Python dict) เป็นหลัก และจะใช้ Redis เพิ่มเติมได้เมื่อเปิด `ENABLE_REDIS_CACHE`; แคชใน Redis/in-memory จะหายเมื่อ restart backend หรือเคลียร์ key |
| LangGraph | ยังเป็น optional — `ENABLE_LANGGRAPH_*` flags ใน config |
| TTS/Live Audio | ต้องการ Gemini Live API key แยก |
| docker-compose.yml | มี Redis service — ใช้ได้กับ LangGraph Redis checkpointer และ core cache/rate limit (ผ่าน `redis_client.py`) เมื่อกำหนด `REDIS_URL`; ถ้าไม่รัน Redis จะ fallback เป็น in-memory |
| `redis` package | อยู่ใน requirements.txt — ใช้กับ `redis.asyncio` ใน `redis_client.py` / `RedisCache` / `RedisRateLimiter` (optional; ระบบทำงานได้แม้ใช้เฉพาะ in-memory) |

---

## 19. Changelog

### v2.7.0 (March 2026)

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **Car Rentals Page (ค้นหารถเช่า)** | ออกแบบหน้า `CarRentalsPage.jsx` ใหม่ให้ UI และ UX ใกล้เคียง Flights/Hotels: ฟอร์มค้นหาด้านบน, การ์ดผลลัพธ์, รองรับโหมดค้นหาผ่าน API + โหมดบันทึกเอง (manual) พร้อมเชื่อมต่อ `/api/booking/create` ให้บันทึกเป็น booking จริงในระบบ (trip_id ขึ้นต้น `car-...`). |
| **Car Rentals Validation** | เพิ่ม validation จำนวนผู้โดยสาร: ถ้าผู้โดยสารมากกว่าจำนวนที่นั่งของรถ จะไม่ให้จองและแสดง SweetAlert เตือน. |
| **My Bookings — รถเช่า** | ใน `MyBookingsPage.jsx` ตรวจ booking ประเภทรถเช่า (trip_id `car-`, `source = car_rental_search` หรือมี `travel_slots.cars`): หัวการ์ดแสดง `ต้นทาง → ปลายทาง · รุ่นรถ` (เช่น `HKT → HKT · Toyota Yaris 1.2`), ช่องจำนวนคืนเปลี่ยน label เป็น **“จำนวนวันที่เช่า”** และหน่วยเป็น “วัน”. |
| **Booking Integration (Car Rentals + AI)** | booking รถเช่าจากหน้า `CarRentalsPage` ใช้ payload โครงสร้างเดียวกับ AITravelChat/Trips (plan.transport.car_rental.segments + travel_slots.cars) ทำให้ MyBookings และ TripSummary แสดงและคำนวณราคารวมร่วมกับ flight/hotel ได้ถูกต้อง. |
| **Redis Core Integration (optional)** | เพิ่ม `app/core/redis_client.py` และผูก Redis กับ cache (`redis_cache.py`) และ rate limiter (`redis_rate_limiter.py`): ถ้ามี `REDIS_URL` และ `ENABLE_REDIS_CACHE=true` จะใช้ Redis เป็น distributed cache/rate limit; ถ้าไม่มีก็ทำงานแบบ in-memory เหมือนเดิม. |

### v2.6.0 (March 2026 — Design Draft)

| ส่วน | การเปลี่ยนแปลง (ระดับออกแบบ/นำไป implement ใน v2.7.0) |
|------|-------------------------------------------|
| **Redis (design)** | ออกแบบให้ Redis เป็น optional: ตั้ง `REDIS_URL` ใน .env → ใช้ Redis สำหรับ cache และ rate limit; ไม่ตั้ง → fallback in-memory เหมือนเดิม (นำไป implement จริงใน v2.7.0 ผ่าน `redis_client.py`, `redis_cache.py`, `redis_rate_limiter.py`). |
| **redis_client (design)** | ร่างโมดูล `app/core/redis_client.py` (init/close/is_redis_available + helper functions) ซึ่งถูกสร้างและใช้งานจริงใน v2.7.0. |
| **Config (design)** | วางแผนเพิ่ม `redis_url`, `enable_redis_cache` ใน `app/core/config.py` (มีอยู่แล้วในเวอร์ชันปัจจุบัน). |
| **Health & Monitoring (partial)** | `GET /api/monitoring/sync/redis/status` มี field `redis_available` ที่อ่านจาก LangGraph/Redis layer เมื่อกำหนด `REDIS_URL`; เวอร์ชันปัจจุบันมี Redis client ส่วนกลางใน core แล้ว. |

### v2.5.0 (March 2026)

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **Data Accuracy (AI Prompts)** | ใน `CONTROLLER_SYSTEM_PROMPT` และ `get_responder_system_prompt`: เพิ่มส่วน "DATA ACCURACY" — กำหนดข้อมูลเที่ยวบิน (PNR, เวลาท้องถิ่น, เทอร์มินัล, สัมภาระ, พาสปอร์ต) และที่พัก (Confirmation Number, ที่อยู่, Check-in/out, นโยบายชำระ/ยกเลิก, บริการ, ติดต่อ); Responder มีกฎ "สรุปการจอง" ให้ใช้ข้อมูลเหล่านี้เมื่อตอบคำถาม/แสดง My Bookings |
| **Voice Chat** | โหมดแชทด้วยเสียง: ต้องล็อกอินก่อนเริ่ม; เมื่อ Live WebSocket (Gemini Live API) error/close/error message → fallback เป็น Simple Voice Mode (Web Speech API SpeechRecognition + sendMessage + TTS) |
| **Trip Evaluation Mode** | Frontend ส่ง `mode` (ask/agent) ไปยัง `/api/chat/agent-feedback`; Backend บันทึก `mode` ใน trip evaluation — Dashboard แสดงโหมดถูกต้อง (ASK vs Agent) |
| **Admin Dashboard — คะแนน** | คำนวณ combined score แม้มีแค่ avg_accuracy หรือ avg_user_stars อย่างใดอย่างหนึ่ง; เพิ่มคอลัมน์ combined_score_pct ในตารางต่อ user; limit 300 รายการ, แสดง trips ถึง 100 รายการ |
| **Admin Dashboard — AI รู้จัก User** | API `get_user_familiarity` คืน `breakdown`: memory_summary, profile_summary, preferences_summary; แดชบอร์ดแสดงส่วน "AI รู้จัก User นี้อย่างไรบ้าง" (ความจำ, โปรไฟล์, ความชอบการเดินทาง) |
| **Hotel Search (Frontend)** | หน้า Hotels: การ์ดแสดงหลายรูป (carousel), ดาว/จำนวนรีวิว, ที่อยู่, สิ่งอำนวยความสะดวก (icons+labels), ราคาสุดคุ้ม, ปุ่มดูราคา; รองรับ dark theme และ responsive |

### v2.4.0 (March 2026)

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **Selection Preferences (RL+ML)** | Service `selection_preferences.py`: บันทึก choice history (`user_choice_history`), สรุปความชอบจากการเลือก + RL → ใส่ใน User Profile และ Agent Mode selection prompt; preference `learnFromMyChoices` (opt-in) |
| **Admin Login** | หน้า login แทน Basic Auth popup: GET/POST `/admin/login`, GET `/admin/logout`; cookie `admin_session` (signed, 1 วัน); `/api/admin/*` รองรับทั้ง cookie และ Basic Auth |
| **Admin Dashboard** | ลบส่วน Amadeus Data Viewer ออกจากแดชบอร์ด; เพิ่มปุ่ม "ออกจากระบบ" |
| **วางแผนเริ่มจากศูนย์** | Controller: เมื่อแผนว่าง (ไม่มี segments) action แรกต้องเป็น CREATE_ITINERARY หรือ ASK_USER; inject ข้อความเตือนใน prompt; กฎ START FROM ZERO ใน `CONTROLLER_SYSTEM_PROMPT` |
| **Agent Mode เริ่มจากศูนย์** | โหมด Agent เมื่อแผนว่าง: บังคับ CREATE_ITINERARY พร้อม infer (origin=Bangkok, วันที่ถัดไป, guests=1); ไม่ใช้ ASK_USER |

### v2.3.0 (February 2026)

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **วีซ่า + ผู้จองร่วม** | Backend: โมเดล/helpers วีซ่า (`app/models/visa.py`); `get_me` / `update_profile` รองรับ `visa_records` + `visa_warnings` ต่อสมาชิกใน `family`; แชท/agent ใช้ข้อมูลวีซ่า |
| **พาสปอร์ตหลายเล่ม** | รองรับ `passports` array ต่อคน; มี `is_primary` flag; เช็กอายุเล่ม (6-Month Rule); sync ข้อมูล primary เข้าฟิลด์ legacy เพื่อ backward compatibility |
| **Frontend วีซ่า/พาสปอร์ต** | หน้าแก้ไขโปรไฟล์: ฟอร์มผู้จองร่วมมี `passports[]` และ `visa_records[]` (เพิ่ม/แก้/ลบ, ผูกพาสปอร์ต, validation); TripSummaryUI แสดงผู้จองร่วมในสรุปการจอง |
| **แชท** | คลิกรายการแชทใน sidebar → โหลดประวัติแชททันที (`loadHistoryForChat`) ไม่รอ fetch แยก |
| **หน้าแก้ไขโปรไฟล์** | แก้ ReferenceError `emptyPassportForm`/`emptyVisaForm` (ย้ายนิยามก่อนใช้); ธีมมืดครบ (พื้นหลัง, การ์ด, input/select/textarea, ข้อความคำอธิบาย มองเห็นชัด) |
| **My Bookings ธีมมืด** | ใช้ selector `.my-bookings-content[data-theme="dark"]`; พื้นหลัง container/การ์ด/loading/empty, รายละเอียดจอง, บล็อกเที่ยวบิน/โรงแรม, กรอบราคารวม, การ์ดรายชื่อผู้โดยสาร (`.booking-passengers`), ป้ายสถานะ/ผู้โดยสาร, ปุ่ม — โทนมืดครบ |
| **การแจ้งเตือน ธีมมืด** | NotificationPanel ใช้ `useTheme()` + `data-theme` บนพาเนล; ใน `theme-content.css` เพิ่มสไตล์ธีมมืดสำหรับหัวข้อ, แถบกรอง, รายการแจ้งเตือน, ไอคอนตามประเภท, ข้อความและเวลา |

### v2.2.0

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **Frontend Chat** | Cache-first: bulk fetch ประวัติทุกแชทครั้งเดียว → `historyCache`; สลับแชทอ่านจาก cache ไม่ spinner; บทสนทนาคงอยู่จนปิดแท็บ (ไม่ clear cache ตอน fetchSessions) |
| **Trip Selector Bar** | ลบแถบเลือกทริปออก — AI จัดการ context เอง |
| **TripSummaryUI** | แสดงเฉพาะเมื่อผู้ใช้พิมพ์คำว่า "จองเลย" ในข้อความ |
| **API** | เพิ่ม `GET /api/chat/histories` (bulk), router `/api/trips` (CRUD + link-chat) |
| **MongoDB** | Collection เปลี่ยนชื่อ: `rl_qtable` → `user_preference_scores`, `rl_rewards` → `user_feedback_history`; เพิ่ม collection `trips` |
| **Storage** | ลบ `hybrid_storage.py` — ใช้ MongoDB (mongodb_storage) โดยตรง |
| **React** | เพิ่ม `useCallback` ใน import; ย้าย bulk-fetch + beforeunload ไปหลังการประกาศ `activeTripId`/`trips` (แก้ TDZ) |