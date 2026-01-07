"""
Production-Grade AI Travel Agent - FastAPI Entry Point
Two-Pass ReAct Architecture with Robust Error Handling
"""

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
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router
from app.api.travel import router as travel_router
from app.api.admin import router as admin_router
from app.api.mcp import router as mcp_router

# Setup logging
setup_logging("travel_agent", settings.log_level, settings.log_file)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events for FastAPI
    Startup and shutdown logic
    """
    # Startup
    logger.info("Starting Production-Grade AI Travel Agent")
    logger.info(f"Gemini Model: {settings.gemini_model_name}")
    logger.info(f"Sessions Directory: {settings.sessions_dir}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Travel Agent")


# Initialize FastAPI app
app = FastAPI(
    title="Production-Grade AI Travel Agent",
    description="Two-Pass ReAct Architecture with Robust Error Handling",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(travel_router)
app.include_router(admin_router)
app.include_router(mcp_router)

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
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "travel_agent",
        "version": "2.0.0"
    }


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
