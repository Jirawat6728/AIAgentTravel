from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import AgentException, StorageException, LLMException
from app.core.resilience import chat_rate_limiter, api_rate_limiter, payment_rate_limiter
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.travel import router as travel_router
from app.api.admin import router as admin_router
from app.api.mcp import router as mcp_router
from app.api.booking import router as booking_router
from app.api.amadeus_viewer import router as amadeus_viewer_router
from app.api.monitoring import router as monitoring_router
from app.api.options_cache import router as options_cache_router
from app.api.notification import router as notification_router
from app.api.diagnostics import router as diagnostics_router

# Setup logging
setup_logging("travel_agent", settings.log_level, settings.log_file)
logger = get_logger(__name__)


from app.storage.connection_manager import MongoConnectionManager, RedisConnectionManager
from app.storage.mongodb_storage import MongoStorage

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for FastAPI with Robust Error Handling
    Startup and shutdown logic with connection verification
    """
    # Startup
    logger.info("="*60)
    logger.info("Starting Production-Grade AI Travel Agent")
    logger.info(f"Gemini Model: {settings.gemini_model_name}")
    logger.info(f"Sessions Directory: {settings.sessions_dir}")
    logger.info(f"Omise Integration: {'Configured' if settings.omise_secret_key else 'Not Configured'}")
    
    # ✅ Validate Gemini API Key on startup
    if settings.enable_gemini:
        if not settings.gemini_api_key or not settings.gemini_api_key.strip():
            logger.error("="*60)
            logger.error("⚠️  WARNING: GEMINI_API_KEY is not set!")
            logger.error("   Chat functionality will not work without API key.")
            logger.error("   Please set GEMINI_API_KEY in your .env file.")
            logger.error("   Get your API key from: https://makersuite.google.com/app/apikey")
            logger.error("="*60)
        elif len(settings.gemini_api_key.strip()) < 20:
            logger.warning("="*60)
            logger.warning("⚠️  WARNING: GEMINI_API_KEY appears to be invalid (too short)")
            logger.warning("   Please check your API key in .env file.")
            logger.warning("="*60)
        else:
            logger.info(f"✅ Gemini API Key: {'*' * 6}{settings.gemini_api_key[-4:]} (configured)")
    else:
        logger.warning("⚠️  Gemini is disabled (ENABLE_GEMINI=false)")
    
    logger.info("="*60)
    
    # Store connection managers for health checks
    app.state.mongo_mgr = None
    app.state.redis_mgr = None
    app.state.startup_success = False
    
    # Initialize DB Connections with Retry
    max_retries = 3
    retry_delay = 2
    
    # MongoDB Initialization
    for attempt in range(max_retries):
        try:
            logger.info(f"Initializing MongoDB (attempt {attempt + 1}/{max_retries})...")
            mongo_mgr = MongoConnectionManager.get_instance()
            db = mongo_mgr.get_database()
            
            # Test connection
            db.command('ping')
            logger.info("[OK] MongoDB connection verified")
            
            # Setup indexes
            mongo_storage = MongoStorage()
            await mongo_storage.connect()
            logger.info("[OK] MongoDB indexes created")
            
            app.state.mongo_mgr = mongo_mgr
            break
            
        except Exception as e:
            logger.error(f"[FAIL] MongoDB initialization failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(retry_delay)
            else:
                logger.critical("Failed to initialize MongoDB after all retries. Server may be unstable.")
                # Don't exit - allow server to start but mark as unhealthy
    
    # Redis Initialization (Optional - don't fail startup if unavailable)
    for attempt in range(max_retries):
        try:
            logger.info(f"Initializing Redis (attempt {attempt + 1}/{max_retries})...")
            redis_mgr = RedisConnectionManager.get_instance()
            redis_client = await redis_mgr.get_redis()
            
            # Test connection (Redis is optional)
            if redis_client:
                await redis_client.ping()
                logger.info("[OK] Redis connection verified")
                app.state.redis_mgr = redis_mgr
                break
            else:
                # Redis unavailable but that's OK
                if attempt == max_retries - 1:
                    logger.info("[INFO] Redis unavailable - continuing without Redis (optional service)")
                else:
                    await asyncio.sleep(retry_delay)
            
        except Exception as e:
            logger.debug(f"[INFO] Redis initialization failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                import asyncio
                await asyncio.sleep(retry_delay)
            else:
                logger.info("[INFO] Redis unavailable - continuing without Redis (optional service)")
    
    # Mark startup as successful if at least MongoDB is available
    if app.state.mongo_mgr:
        app.state.startup_success = True
        logger.info("="*60)
        logger.info("[OK] Server startup completed successfully")
        logger.info("="*60)
        
        # Start health monitoring in background
        try:
            from app.core.resilience import health_monitor
            asyncio.create_task(health_monitor.start_monitoring())
            logger.info("[OK] Health monitor started")
        except Exception as e:
            logger.warning(f"Failed to start health monitor: {e}")
    else:
        logger.critical("="*60)
        logger.critical("⚠️  Server started in DEGRADED MODE - MongoDB unavailable")
        logger.critical("="*60)
    
    yield
    
    # Stop health monitoring on shutdown
    try:
        from app.core.resilience import health_monitor
        health_monitor.stop_monitoring()
    except Exception:
        pass
    
    # Graceful Shutdown
    logger.info("="*60)
    logger.info("Initiating graceful shutdown...")
    logger.info("="*60)
    
    try:
        # Close Redis connections
        if app.state.redis_mgr:
            logger.info("Closing Redis connections...")
            await app.state.redis_mgr.close()
            logger.info("[OK] Redis connections closed")
    except Exception as e:
        logger.error(f"Error closing Redis: {e}")
    
    try:
        # Close MongoDB connections
        if app.state.mongo_mgr:
            logger.info("Closing MongoDB connections...")
            # MongoClient doesn't need explicit close in motor, but we log it
            logger.info("[OK] MongoDB connections closed")
    except Exception as e:
        logger.error(f"Error closing MongoDB: {e}")
    
    logger.info("="*60)
    logger.info("[OK] Shutdown completed")
    logger.info("="*60)


# Initialize FastAPI app
app = FastAPI(
    title="Production-Grade AI Travel Agent",
    description="Two-Pass ReAct Architecture with Robust Error Handling",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
# ✅ Fixed: Cannot use wildcard "*" with credentials=True
# Must specify explicit origins when using credentials
# IMPORTANT: CORS middleware must be added FIRST (before other middlewares)
# to ensure it processes requests correctly
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative React dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # Backend itself (for testing)
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Request Timeout Middleware - Prevent hanging requests
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to prevent requests from hanging indefinitely"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            # ✅ Optimized timeouts: 90 seconds for chat (1.5 minute target), 60 for amadeus-viewer/search, 30 for others
            if request.url.path.startswith("/api/chat"):
                timeout = 90  # ✅ Changed from 60s to 90s for 1.5-minute search completion target
            elif request.url.path.startswith("/api/amadeus-viewer/search"):
                timeout = 60  # 1 minute timeout for Amadeus search (optimized for speed)
            else:
                timeout = 30
            
            return await asyncio.wait_for(
                call_next(request),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Request timeout: {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                content={
                    "error": "Request Timeout",
                    "message": "The request took too long to process. Please try again.",
                    "path": request.url.path
                }
            )
        except Exception as e:
            logger.error(f"Middleware error: {e}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Server Error",
                    "message": "An unexpected error occurred in middleware"
                }
            )

app.add_middleware(TimeoutMiddleware)

# Error Recovery Middleware - Log all errors
class ErrorLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all errors for debugging"""
    
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # Log the error with full details
            logger.error(
                f"Unhandled error in request: {request.method} {request.url.path}",
                exc_info=True,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "client": request.client.host if request.client else "unknown"
                }
            )
            # Re-raise to let FastAPI's exception handlers deal with it
            raise

app.add_middleware(ErrorLoggingMiddleware)

# Rate Limiting Middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits"""
    
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_ip = request.client.host if request.client else "unknown"
        
        # Select appropriate rate limiter based on path
        if request.url.path.startswith("/api/chat"):
            limiter = chat_rate_limiter
        elif request.url.path.startswith("/api/booking/payment"):
            limiter = payment_rate_limiter
        else:
            limiter = api_rate_limiter
        
        # Check rate limit
        is_allowed, remaining = limiter.is_allowed(client_ip)
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for {client_ip} on {request.url.path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate Limit Exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )
        
        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        
        return response

app.add_middleware(RateLimitMiddleware)

# Include routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(travel_router)
app.include_router(admin_router)
app.include_router(diagnostics_router)
app.include_router(mcp_router)
app.include_router(booking_router)
app.include_router(amadeus_viewer_router)
app.include_router(monitoring_router)
app.include_router(options_cache_router)
app.include_router(notification_router)

# Serve static admin dashboard
@app.get("/admin", include_in_schema=False)
async def admin_dashboard():
    """Serve the admin dashboard HTML file"""
    admin_path = os.path.join(os.path.dirname(__file__), "static", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return {"error": "Admin dashboard file not found"}


# Global Exception Handler
@app.exception_handler(AgentException)
async def agent_exception_handler(request: Request, exc: AgentException):
    """Handle agent-specific exceptions"""
    logger.error(f"AgentException: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Agent Error",
            "message": str(exc),
            "type": "AgentException"
        }
    )


@app.exception_handler(StorageException)
async def storage_exception_handler(request: Request, exc: StorageException):
    """Handle storage-specific exceptions"""
    logger.error(f"StorageException: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Storage Error",
            "message": str(exc),
            "type": "StorageException"
        }
    )


@app.exception_handler(LLMException)
async def llm_exception_handler(request: Request, exc: LLMException):
    """Handle LLM-specific exceptions"""
    logger.error(f"LLMException: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error": "LLM Service Error",
            "message": "System is busy. Please try again later.",
            "type": "LLMException"
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    logger.warning(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation Error",
            "message": "Invalid request format",
            "details": exc.errors()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler - catch all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred",
            "type": type(exc).__name__
        }
    )


@app.get("/health")
async def health(request: Request):
    """
    Comprehensive health check endpoint
    Checks all critical services and returns detailed status
    """
    health_status = {
        "status": "healthy",
        "service": "travel_agent",
        "version": "2.0.0",
        "timestamp": None,
        "checks": {}
    }
    
    import datetime
    health_status["timestamp"] = datetime.datetime.now().isoformat()
    
    # Check startup success
    startup_success = getattr(request.app.state, "startup_success", False)
    if not startup_success:
        # If startup didn't complete, check if MongoDB is at least available now
        try:
            mongo_mgr = getattr(request.app.state, "mongo_mgr", None)
            if mongo_mgr:
                db = mongo_mgr.get_database()
                db.command('ping')
                # MongoDB is available, mark as degraded but operational
                health_status["status"] = "degraded"
                health_status["checks"]["startup"] = {"status": "degraded", "message": "Startup incomplete but MongoDB available"}
            else:
                # No MongoDB, mark as unhealthy
                health_status["status"] = "unhealthy"
                health_status["checks"]["startup"] = {"status": "failed", "message": "Server failed to start properly - MongoDB unavailable"}
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content=health_status
                )
        except Exception as e:
            # MongoDB check failed, mark as unhealthy
            health_status["status"] = "unhealthy"
            health_status["checks"]["startup"] = {"status": "failed", "message": f"Server failed to start properly - MongoDB error: {str(e)}"}
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=health_status
            )
    
    # Check MongoDB
    try:
        mongo_mgr = request.app.state.mongo_mgr
        if mongo_mgr:
            db = mongo_mgr.get_database()
            db.command('ping')
            health_status["checks"]["mongodb"] = {"status": "healthy", "message": "Connection OK"}
        else:
            health_status["checks"]["mongodb"] = {"status": "unavailable", "message": "Not initialized"}
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["mongodb"] = {"status": "unhealthy", "message": str(e)}
        health_status["status"] = "unhealthy"
        logger.error(f"MongoDB health check failed: {e}")
    
    # Check Redis
    try:
        redis_mgr = request.app.state.redis_mgr
        if redis_mgr:
            redis_client = await redis_mgr.get_redis()
            await redis_client.ping()
            health_status["checks"]["redis"] = {"status": "healthy", "message": "Connection OK"}
        else:
            health_status["checks"]["redis"] = {"status": "unavailable", "message": "Not initialized"}
            # Redis is optional, don't mark as unhealthy
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "message": str(e)}
        logger.warning(f"Redis health check failed: {e}")
        # Redis failure is not critical
    
    # Return appropriate status code
    if health_status["status"] == "unhealthy":
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )
    elif health_status["status"] == "degraded":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=health_status
        )
    else:
        return health_status


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Production-Grade AI Travel Agent",
        "architecture": "Two-Pass ReAct",
        "version": "2.0.0",
        "endpoints": {
            "chat": "/chat",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=None  # Use our custom logging
    )
