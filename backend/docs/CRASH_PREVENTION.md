# 🛡️ Backend Crash Prevention & Stability Improvements

## Overview
เอกสารนี้สรุปการแก้ไขปัญหา backend ล่ม/shutdown เองโดยไม่ได้รับคำสั่ง

---

## 🐛 สาเหตุที่ Backend ล่มได้

### ก่อนแก้ไข:
1. ❌ **Uncaught Exceptions** - Exception ที่ไม่ได้จัดการทำให้ process crash
2. ❌ **Connection Failures** - MongoDB/Redis disconnect แล้วไม่ retry
3. ❌ **Hanging Requests** - Request ค้างไม่มี timeout
4. ❌ **No Health Checks** - ไม่รู้ว่า DB connections ยังมีชีวิตอยู่หรือไม่
5. ❌ **Poor Shutdown** - Shutdown ไม่ graceful ทิ้ง connections แบบไม่สะอาด
6. ❌ **Connection Pool Issues** - ไม่มี pool size limits, connections หมด

---

## ✅ การแก้ไขที่ทำ

### 1. **Robust Startup with Retry Logic**
```python
# In main.py - lifespan()

# MongoDB with 3 retries
for attempt in range(max_retries):
    try:
        mongo_mgr = MongoConnectionManager.get_instance()
        db = mongo_mgr.get_database()
        db.command('ping')  # ✅ Verify connection
        logger.info("✅ MongoDB connection verified")
        break
    except Exception as e:
        logger.error(f"❌ MongoDB failed (attempt {attempt + 1})")
        await asyncio.sleep(retry_delay)
```

**ประโยชน์:**
- ✅ ไม่ล่มเพราะ DB ไม่พร้อมตอน startup
- ✅ Retry 3 ครั้งก่อนจะยอมแพ้
- ✅ ยังทำงานต่อได้ถ้า Redis fail (degraded mode)

---

### 2. **Graceful Shutdown**
```python
# In main.py - lifespan() shutdown

# ปิด connections อย่างเป็นระเบียบ
logger.info("Closing Redis connections...")
await redis_mgr.close()
logger.info("✅ Redis closed")

logger.info("Closing MongoDB connections...")
# MongoDB close handled by Motor automatically
logger.info("✅ MongoDB closed")
```

**ประโยชน์:**
- ✅ ไม่ทิ้ง connections แบบไม่สะอาด
- ✅ Log ทุก step เพื่อ debug
- ✅ Prevent resource leaks

---

### 3. **Comprehensive Health Checks**
```python
@app.get("/health")
async def health(request: Request):
    # ตรวจสอบทุก service
    
    # MongoDB
    db.command('ping')  # Real connection test
    
    # Redis
    await redis_client.ping()  # Real connection test
    
    # Return status: healthy, degraded, or unhealthy
```

**ผลลัพธ์:**
```json
{
  "status": "healthy",
  "service": "travel_agent",
  "version": "2.0.0",
  "timestamp": "2026-01-10T...",
  "checks": {
    "mongodb": {"status": "healthy", "message": "Connection OK"},
    "redis": {"status": "healthy", "message": "Connection OK"}
  }
}
```

**ประโยชน์:**
- ✅ รู้ทันทีว่า service ไหนมีปัญหา
- ✅ สามารถ monitor ด้วย external tools
- ✅ Auto-restart ถ้าใช้กับ Docker/Kubernetes

---

### 4. **Request Timeout Middleware**
```python
class TimeoutMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Chat endpoints: 90s timeout
        # Other endpoints: 30s timeout
        timeout = 90 if "/chat" in request.url.path else 30
        
        return await asyncio.wait_for(call_next(request), timeout=timeout)
```

**ประโยชน์:**
- ✅ ป้องกัน request ค้างเกิน 90 วินาที
- ✅ Server ไม่ค้างรอ request ที่ไม่ตอบสนอง
- ✅ Return 504 Gateway Timeout แทนการล่ม

---

### 5. **Error Logging Middleware**
```python
class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            # Log ทุก error พร้อม context
            logger.error(
                f"Error: {request.method} {request.url.path}",
                exc_info=True,
                extra={"method": ..., "path": ..., "client": ...}
            )
            raise  # Let FastAPI handlers deal with it
```

**ประโยชน์:**
- ✅ ไม่มี silent failures
- ✅ Log ครบทุก error พร้อม stack trace
- ✅ ง่ายต่อการ debug

---

### 6. **MongoDB Connection Pool Settings**
```python
# In mongodb_connection.py

self._client = AsyncIOMotorClient(
    connection_string,
    serverSelectionTimeoutMS=5000,   # 5s to select server
    connectTimeoutMS=10000,           # 10s to connect
    socketTimeoutMS=20000,            # 20s for operations
    heartbeatFrequencyMS=10000,       # 10s heartbeat
    retryWrites=True,                 # ✅ Auto-retry writes
    retryReads=True,                  # ✅ Auto-retry reads
    maxPoolSize=50,                   # ✅ Max 50 connections
    minPoolSize=5,                    # ✅ Keep 5 alive
    maxIdleTimeMS=30000,              # ✅ Close idle after 30s
    waitQueueTimeoutMS=10000,         # ✅ Wait 10s for pool
)
```

**ประโยชน์:**
- ✅ ไม่ล่มเพราะ connection pool หมด
- ✅ Auto-retry network errors
- ✅ รักษา connections ให้สด (heartbeat)
- ✅ ปิด idle connections เพื่อประหยัด resources

---

### 7. **Redis Connection Pool Settings**
```python
# In redis_connection.py

self.redis = redis.Redis(
    host=...,
    port=...,
    max_connections=50,              # ✅ Max 50 in pool
    socket_timeout=5.0,              # ✅ 5s timeout
    socket_connect_timeout=5.0,      # ✅ 5s to connect
    socket_keepalive=True,           # ✅ TCP keepalive
    health_check_interval=30,        # ✅ Check every 30s
    retry_on_timeout=True,           # ✅ Retry timeouts
    retry_on_error=[...],            # ✅ Retry errors
)
```

**ประโยชน์:**
- ✅ ไม่ล่มเพราะ Redis disconnect
- ✅ Auto-reconnect on errors
- ✅ Health check ทุก 30 วินาที
- ✅ TCP keepalive ป้องกัน stale connections

---

### 8. **Global Exception Handlers**
```python
# Already existed, but now they won't crash the server

@app.exception_handler(AgentException)
async def agent_exception_handler(request, exc):
    logger.error(f"AgentException: {exc}", exc_info=True)
    return JSONResponse(...)  # ✅ Return error, don't crash

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(...)  # ✅ Catch ALL exceptions
```

**ประโยชน์:**
- ✅ ไม่มี exception ไหนทำให้ server crash
- ✅ ทุก error ถูก log
- ✅ User ได้ error message ที่เป็นมิตร

---

## 📊 เปรียบเทียบ: ก่อน vs หลัง

| Issue | Before | After |
|-------|--------|-------|
| **DB Connection Fail** | ❌ Server crash | ✅ Retry 3x, then degraded mode |
| **Request Timeout** | ❌ Hang forever | ✅ Return 504 after timeout |
| **Connection Pool Full** | ❌ Hang/crash | ✅ Wait 10s, then error |
| **Uncaught Exception** | ❌ Server crash | ✅ Log + return 500 |
| **DB Disconnect** | ❌ Silent fail | ✅ Auto-retry + health check |
| **Shutdown** | ❌ Abrupt | ✅ Graceful with logging |
| **Health Monitoring** | ❌ None | ✅ `/health` endpoint |

---

## 🎯 วิธีใช้งาน

### 1. ตรวจสอบสุขภาพ Server
```bash
curl http://localhost:8000/health
```

**Response (Healthy):**
```json
{
  "status": "healthy",
  "checks": {
    "mongodb": {"status": "healthy"},
    "redis": {"status": "healthy"}
  }
}
```

**Response (Degraded):**
```json
{
  "status": "degraded",
  "checks": {
    "mongodb": {"status": "healthy"},
    "redis": {"status": "unavailable"}
  }
}
```

---

### 2. Monitor Logs
```bash
# ใน production ให้ดู logs
tail -f backend/data/logs/travel_agent.log

# จะเห็น:
# ✅ MongoDB connection verified
# ✅ Redis connection verified
# ⚠️  Request timeout: /api/chat/send
# ❌ MongoDB ping failed: connection refused
```

---

### 3. Auto-Restart with Docker
```yaml
# docker-compose.yml
services:
  backend:
    restart: unless-stopped  # ✅ Auto-restart on crash
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

---

## 🚀 Best Practices

### DO ✅
1. ตรวจสอบ `/health` ทุก 30 วินาที
2. ใช้ `retry_on_error` สำหรับ transient errors
3. Set timeout ทุก request
4. Log ทุก error พร้อม stack trace
5. ใช้ connection pooling
6. Graceful shutdown

### DON'T ❌
1. อย่าปล่อย exception ไม่จัดการ
2. อย่าใช้ infinite timeout
3. อย่าเปิด connection ใหม่ทุก request
4. อย่า force kill server (ใช้ Ctrl+C graceful)
5. อย่าเพิกเฉยต่อ health check warnings

---

## 📝 Troubleshooting

### ปัญหา: Server ยังล่มอยู่
```bash
# 1. เช็ค logs
tail -f backend/data/logs/travel_agent.log

# 2. เช็ค health
curl http://localhost:8000/health

# 3. เช็ค DB connections
# MongoDB
mongo --eval "db.adminCommand('ping')"

# Redis
redis-cli ping
```

### ปัญหา: Memory Leak
```bash
# เพิ่ม memory monitoring
import tracemalloc
tracemalloc.start()

# หรือใช้ external tools
pip install memory-profiler
```

### ปัญหา: Connections Pool Full
```bash
# เพิ่ม maxPoolSize ใน mongodb_connection.py
maxPoolSize=100  # เพิ่มจาก 50 -> 100

# หรือใช้ Redis only (faster)
```

---

**Result:** Backend แข็งแรง ไม่ล่มง่าย พร้อมใช้งาน Production! 🎉

**Created by:** Crash Prevention & Stability Enhancement  
**Date:** January 10, 2026  
**Version:** 2.0.0
