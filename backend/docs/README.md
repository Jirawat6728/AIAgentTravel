# Production-Grade AI Travel Agent

## Architecture: Two-Pass ReAct Loop

Production-ready AI Travel Agent with robust error handling, strict typing, and clean architecture.

## Project Structure

```
backend/
├── app/
│   ├── api/                  # FastAPI routers
│   │   └── chat.py          # Chat endpoint with background tasks
│   ├── core/                 # Core infrastructure
│   │   ├── config.py        # Application settings
│   │   ├── exceptions.py    # Custom exceptions
│   │   └── logging.py        # Structured logging
│   ├── engine/               # Core agent logic
│   │   └── agent.py         # Two-Pass ReAct Loop
│   ├── models/               # Pydantic V2 models
│   │   ├── trip_plan.py     # TripPlan, Segment
│   │   ├── session.py       # UserSession
│   │   └── actions.py       # ControllerAction, ActionLog
│   ├── services/             # External integrations
│   │   ├── llm.py           # LLM service with tenacity retries
│   │   └── title.py         # Title generator
│   └── storage/              # Repository Pattern
│       ├── interface.py     # StorageInterface (ABC)
│       └── json_storage.py   # Async JSON storage
├── main.py                   # FastAPI entry point
├── requirements.txt          # Dependencies
└── data/
    └── sessions/             # Session storage (JSON files)
```

## Key Features

### ✅ Production-Grade Stability

1. **Strict Typing & Validation**
   - Pydantic V2 models with enum validation
   - Instant corruption detection
   - Type-safe throughout

2. **Robust Error Handling**
   - All actions wrapped in try/except
   - Errors logged, not crashed
   - Safe fallback messages
   - Global exception handlers

3. **Async & Non-Blocking**
   - aiofiles for file I/O
   - Thread pool for LLM calls
   - Concurrent user support
   - Background tasks for title generation

4. **Structured Logging**
   - Every log includes session_id and user_id
   - No print statements
   - Production-ready format

5. **Repository Pattern**
   - Easy migration to PostgreSQL
   - Clean abstraction
   - Testable

6. **Retry Logic**
   - tenacity for LLM retries
   - Max 3 retries on JSON errors
   - Exponential backoff

## Two-Pass ReAct Loop

### Phase 1: Controller (Think & Act)
- Analyzes state and user input
- Decides next action (UPDATE_REQ, CALL_SEARCH, SELECT_OPTION, ASK_USER)
- Executes actions (with error handling)
- Loops max 3 times until ASK_USER
- All actions wrapped in try/except for stability

### Phase 2: Responder (Speak)
- Reads action_log
- Generates Thai response
- Reports what was done
- Asks for missing info

## API Usage

### Endpoint: `POST /chat`

**Headers:**
- `X-Conversation-ID`: Required
- `X-User-ID`: Optional (defaults to "anonymous")

**Request:**
```json
{
  "message": "ไป Tokyo วันที่ 25 ธันวาคม"
}
```

**Response:**
```json
{
  "response": "พบเที่ยวบิน 3 ตัวเลือก...",
  "session_id": "user123::chat1"
}
```

### Example

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "X-Conversation-ID: chat1" \
  -H "X-User-ID: user123" \
  -H "Content-Type: application/json" \
  -d '{"message": "ไป Tokyo"}'
```

## Running the Server

```bash
cd backend
python main.py
```

Or with uvicorn:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## Configuration

Set environment variables in `.env`:

```env
GEMINI_API_KEY=your_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash
GEMINI_TIMEOUT_SECONDS=30
GEMINI_MAX_RETRIES=3
LOG_LEVEL=INFO
```

## Error Handling

The system has comprehensive error handling:

- **AgentException**: Agent logic errors
- **StorageException**: Storage operation errors
- **LLMException**: LLM API errors
- **Global Handler**: Catches all unhandled exceptions

All errors return proper HTTP status codes and JSON responses.

## Background Tasks

Title generation runs in background:
- Only for first turn (when `session.title is None`)
- Non-blocking (doesn't delay response)
- Automatic fallback on failure

## Data Models

### Segment
- `status`: Enum['pending', 'searching', 'selecting', 'confirmed']
- `requirements`: Dict with search parameters
- `options_pool`: List of search results
- `selected_option`: Selected option (if confirmed)

### TripPlan
- `flights`: List[Segment]
- `accommodations`: List[Segment]
- `ground_transport`: List[Segment]

### UserSession
- `session_id`: Unique identifier
- `user_id`: User identifier
- `trip_plan`: TripPlan object
- `title`: Optional chat title
- `last_updated`: ISO timestamp

## Session Management

Sessions stored as JSON files:
- Location: `data/sessions/`
- Format: `{session_id}.json`
- Atomic writes (temp file + rename)
- Automatic validation on load

## Legacy Code

Old code moved to `_legacy_backup/` to prevent import conflicts.

## Dependencies

- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `pydantic`: Data validation
- `aiofiles`: Async file I/O
- `google-genai`: Gemini AI client
- `tenacity`: Retry logic
- `python-dotenv`: Environment variables

## Production Deployment

1. Set environment variables
2. Install dependencies: `pip install -r requirements.txt`
3. Run with production server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
   ```

## Testing

```bash
# Health check
curl http://localhost:8000/health

# Chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "X-Conversation-ID: test1" \
  -H "X-User-ID: test_user" \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'
```

## Architecture Benefits

1. **Stability**: Error handling prevents crashes
2. **Type Safety**: Pydantic catches errors early
3. **Concurrency**: Async operations support multiple users
4. **Maintainability**: Clean structure, Repository Pattern
5. **Scalability**: Easy to migrate to database
6. **Reliability**: Retry logic with tenacity
