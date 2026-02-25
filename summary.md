# AI Travel Agent — Project Summary (ฉบับละเอียด)

> **Version**: 2.2.0 | **Architecture**: Two-Pass ReAct + LangGraph | **Last Updated**: February 2026

---

## 1. ภาพรวมระบบ

AI Travel Agent เป็นแอปพลิเคชันวางแผนการเดินทางแบบครบวงจร ผู้ใช้สนทนาเป็นภาษาไทยหรืออังกฤษกับ AI เพื่อค้นหาเที่ยวบิน โรงแรม และการเดินทาง จากนั้น AI จะจัดการเลือก จอง และชำระเงินให้อัตโนมัติ

### โหมดการทำงาน
| โหมด | คำอธิบาย |
|------|-----------|
| **Normal Mode** | AI แนะนำตัวเลือก ผู้ใช้เลือกเอง |
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
| Cache | **In-process memory** (Python dict, TTL 24h) — ไม่ใช้ Redis |
| Travel API | Amadeus SDK 9.0 |
| Maps | Google Maps Python Client 4.10 |
| Payment | Omise 0.10 |
| Auth | Google Identity Services + Firebase Admin SDK ≥6.5 |
| Email | Gmail SMTP (`smtplib`) — ส่ง OTP verification |
| HTTP Client | httpx 0.27.2 (async) |
| ML/Intent | scikit-learn ≥1.3 (TF-IDF + LR + MLP) |
| DL/Intent | PyTorch LSTM (optional, ติดตั้งแยก) |
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
| Styling | Pure CSS (ไม่มี Tailwind/MUI) |
| HTTP | Native `fetch` (ไม่มี Axios) |

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
│       │   ├── admin.py           # /api/admin — dashboard + notification simulator
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
│       │   ├── ml_keyword_service.py # Intent classification (3-tier ML/DL)
│       │   ├── dl_intent_model.py # PyTorch LSTM intent model (optional)
│       │   ├── model_selector.py  # Auto model selection by task complexity
│       │   ├── options_cache.py   # In-memory options cache (TTL 24h)
│       │   ├── workflow_state.py  # In-memory workflow step tracker
│       │   ├── workflow_history.py# MongoDB workflow history
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
│       │   └── actions.py         # ControllerAction, ActionType, ActionLog
│       ├── storage/
│       │   ├── mongodb_storage.py # MongoDB CRUD (Motor async) — primary storage
│       │   ├── connection_manager.py # MongoDB connection pool singleton
│       │   ├── redis_storage.py   # (deprecated stub — ไม่ใช้แล้ว)
│       │   ├── redis_sync.py      # (deprecated stub — ไม่ใช้แล้ว)
│       │   ├── json_storage.py    # JSON file storage (fallback)
│       │   └── interface.py       # StorageInterface ABC
│       └── core/
│           ├── config.py          # Settings (python-dotenv)
│           ├── logging.py         # Structured logger
│           ├── exceptions.py      # Custom exceptions
│           ├── resilience.py      # Rate limiting + health monitor
│           └── redis_rate_limiter.py # Rate limiter (in-memory fallback)
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
- `BudgetAdvisor` — ประเมินงบประมาณและแจ้งเตือน
- `InputValidator` — ตรวจสอบ input ก่อนส่งให้ Controller
- `ProactiveRecommendations` — แนะนำเชิงรุก
- `SelfCorrectionValidator` — ตรวจสอบ output ของ Controller

### 4.3 LLM Service (`services/llm.py`)

| Class | คำอธิบาย |
|-------|-----------|
| `LLMService` | Gemini API calls + retry + exponential backoff + fallback chain |
| `LLMServiceWithMCP` | LLMService + MCP tool calling support |
| `IntentBasedLLM` | เลือก model ตาม intent |
| `BrainType` | enum: `controller` / `responder` / `searcher` |
| `ModelType` | enum: flash / pro / ultra |

### 4.4 LangGraph Orchestration (`orchestration/`)

| Graph | คำอธิบาย |
|-------|-----------|
| `workflow_graph.py` | Main state machine: planning → searching → selecting → summary → booking → done |
| `agent_mode_graph.py` | Agent Mode: auto-select + auto-book flow |
| `full_workflow_graph.py` | Full workflow (START → controller → execute → responder → END) |

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

### 6.1 Intent Classification (3-Tier)

```
Tier 1: PyTorch LSTM          (optional, ต้องติดตั้ง torch แยก)
    ↓ fallback
Tier 2: TF-IDF + MLPClassifier (scikit-learn, hidden: 256→128→64, ReLU, Adam)
    ↓ fallback
Tier 3: TF-IDF + LogisticRegression (CalibratedClassifierCV, ~90% accuracy)
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

---

## 7. Authentication Flow

### Email/Password Registration
```
1. กรอกฟอร์ม → POST /api/auth/register
2. Backend: สร้าง user ใน MongoDB, generate OTP (6 หลัก, หมดอายุ 5 นาที)
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
| POST | `/api/auth/verify-email` | ยืนยันอีเมลด้วย OTP (หมดอายุ 5 นาที) |
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
| POST | `/api/monitoring/sync/redis/session/{session_id}` | No-op (Redis removed) |
| POST | `/api/monitoring/sync/redis/all` | No-op (Redis removed) |
| GET | `/api/monitoring/sync/redis/status` | Returns Redis-removed status |

### Health (`/health`)
| Method | Path | คำอธิบาย |
|--------|------|-----------|
| GET | `/health` | Health check (MongoDB + Redis disabled status) |

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
    passport_number: Optional[str]
    family_members: List[FamilyMember]
    omise_customer_id: Optional[str]
    created_at: datetime
    last_active: datetime
```

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
ADMIN_PASSWORD=
ADMIN_ENABLED=true
ADMIN_REQUIRE_AUTH=true

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
  "@vitejs/plugin-react": "^4.3.1",
  "baseline-browser-mapping": "^2.9.12",
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
| `redis` | `redis:7-alpine` | `6379:6379` | AOF persistence, volume: `redis_data` |
| `backend` | Built from `./Dockerfile` | `8000:8000` | depends on healthy MongoDB + Redis |

> **หมายเหตุ**: docker-compose.yml ยังมี Redis service อยู่ แต่ backend code ไม่ได้ใช้ Redis แล้ว สามารถลบ redis service ออกจาก docker-compose.yml ได้

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
| **Redis Removed** | ลบออกทั้งหมด — ใช้ MongoDB 100% + in-process memory cache |
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
- ไม่ต้องการ Redis หรือ MongoDB local

---

## 18. Known Limitations

| ส่วน | ข้อจำกัด |
|------|-----------|
| Amadeus Booking | ใช้ sandbox เท่านั้น — ไม่จองจริง |
| Email | Gmail SMTP ส่งได้ทุกอีเมลทุกค่าย · OTP หมดอายุ 5 นาที · ต้องมี App Password |
| Options Cache | เก็บใน RAM — หายเมื่อ backend restart (user ต้องค้นหาใหม่) |
| PyTorch LSTM | ต้องติดตั้ง `torch` แยก (ไม่อยู่ใน requirements.txt) |
| LangGraph | ยังเป็น optional — `ENABLE_LANGGRAPH_*` flags ใน config |
| TTS/Live Audio | ต้องการ Gemini Live API key แยก |
| docker-compose.yml | ยังมี Redis service — สามารถลบออกได้เนื่องจากไม่ใช้แล้ว |
| `redis` package | ยังอยู่ใน requirements.txt — สามารถลบออกได้ |

---

## 19. Changelog (v2.2.0)

| ส่วน | การเปลี่ยนแปลง |
|------|-----------------|
| **Frontend Chat** | Cache-first: bulk fetch ประวัติทุกแชทครั้งเดียว → `historyCache`; สลับแชทอ่านจาก cache ไม่ spinner; บทสนทนาคงอยู่จนปิดแท็บ (ไม่ clear cache ตอน fetchSessions) |
| **Trip Selector Bar** | ลบแถบเลือกทริปออก — AI จัดการ context เอง |
| **TripSummaryUI** | แสดงเฉพาะเมื่อผู้ใช้พิมพ์คำว่า "จองเลย" ในข้อความ |
| **API** | เพิ่ม `GET /api/chat/histories` (bulk), router `/api/trips` (CRUD + link-chat) |
| **MongoDB** | Collection เปลี่ยนชื่อ: `rl_qtable` → `user_preference_scores`, `rl_rewards` → `user_feedback_history`; เพิ่ม collection `trips` |
| **Storage** | ลบ `hybrid_storage.py` — ใช้ MongoDB (mongodb_storage) โดยตรง |
| **React** | เพิ่ม `useCallback` ใน import; ย้าย bulk-fetch + beforeunload ไปหลังการประกาศ `activeTripId`/`trips` (แก้ TDZ) |
