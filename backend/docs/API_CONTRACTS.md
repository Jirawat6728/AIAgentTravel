# API Contracts (Test-Validated)

Contracts below are validated by TestSprite tests (TC001–TC006). Use them when integrating or writing new tests.

---

## Auth API

### `POST /api/auth/register`
- **Request:** `{ email, password, firstName, lastName }` (camelCase). `phone` optional.
- **Response:** `201 Created` with `{ ok: true, user: {...} }`. Sets session cookie.
- **Note:** No `access_token`. Auth is session-cookie based.

### `POST /api/auth/login`
- **Request:** `{ email, password, remember_me? }`
- **Response:** `200` with `{ ok: true, user: {...} }`. Sets session cookie. No JWT/access_token.

### `GET /api/auth/me`
- **Auth:** Session cookie (or none).
- **Response:** `200` with `{ user: {...} }` when authenticated, `{ user: null }` when not. No `401` for unauthenticated.

### `POST /api/auth/google`
- **Request:** `{ id_token }` (not `token`). Google ID token from OAuth.
- **Response:** `200` with `{ ok, user }`, or `400`/`401`/`500` if invalid or not configured.

---

## Travel API

### `POST /api/travel/smart-search`
- **Request:** `{ query: string, user_id?: string, context?: object }`.
  - Use **natural-language** `query` only (e.g. `"เที่ยวบินจากกรุงเทพไปภูเก็ต 1 กรกฎาคม 2026 กลับ 10 กรกฎาคม 2 ผู้ใหญ่"`).
  - Do **not** use structured fields (`origin`, `destination`, `departure_date`, etc.); those yield `422`.
- **Response:** `200` with `{ intent, location?, flights?, hotels?, transfers?, activities?, summary }`. Lists may be `null` or empty.

---

## Booking API

### `POST /api/booking/create`
- **Request:** `{ trip_id, user_id, plan, travel_slots, total_price, currency? }`.
  - `plan`: dict (e.g. `{ flights, hotels, ground_transfers, budget, travelers }`).
  - `travel_slots`: dict (e.g. `{ origin_city, destination_city, departure_date, return_date, nights }`).
- **Headers:** `X-User-ID` optional (can use `user_id` in body).
- **Response:** `200`/`201` with `{ ok, booking_id, message, status }`. `status` e.g. `pending_payment`, `pending`, `confirmed`, `cancelled`, `failed`, `processing`.

### `POST /api/booking/cancel?booking_id=...`
- **Cancel:** Use `POST` with `booking_id` as query param. No `DELETE /api/booking/:id`.

---

## Chat API

### `POST /api/chat`
- **Headers:** `X-User-ID`, `X-Conversation-ID` (or `chat_id` in body). Required for auth.
- **Request:** `{ message, chat_id?, user_id? }`. `message` required.
- **Response:** `200` with `{ response, session_id }`, or `500` if e.g. GEMINI_API_KEY missing.

---

## MCP Tools API

### `GET /api/mcp/tools`
- **Response:** `200` with list of tools (structure may vary).

### `POST /api/mcp/execute`
- **Request:** `{ tool_name, parameters }`.
- **Response:** `200` with execution result object.
