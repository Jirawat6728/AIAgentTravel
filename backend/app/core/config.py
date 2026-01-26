import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file
_BASE_DIR = Path(__file__).parent.parent.parent
_DOTENV_PATH = Path(os.getenv("DOTENV_PATH") or (_BASE_DIR / ".env"))
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)

# Import logger after dotenv is loaded
# Note: Logger is created lazily to avoid circular imports
from app.core.logging import get_logger


class Settings:
    """Application settings"""
    
    def __init__(self):
        # Get logger lazily to avoid circular import issues
        logger = get_logger(__name__)
        
        # LLM Configuration - Gemini (Primary)
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        # Model names must be set in .env file
        # Note: gemini-1.5-flash is deprecated, use gemini-2.5-flash instead
        default_model = os.getenv("GEMINI_MODEL_NAME", "").strip()
        if not default_model:
            raise ValueError("GEMINI_MODEL_NAME is required in .env file. Example: GEMINI_MODEL_NAME=gemini-2.5-flash")
        # Auto-update deprecated 1.5 models to 2.5
        if "1.5" in default_model:
            default_model = default_model.replace("1.5", "2.5")
            logger.warning(f"Auto-updated deprecated model name to: {default_model}")
        self.gemini_model_name: str = default_model
        
        sonnet_model = os.getenv("GEMINI_SONNET_MODEL", "").strip()
        if not sonnet_model:
            sonnet_model = default_model  # Fallback to default model
        elif "1.5" in sonnet_model:
            sonnet_model = sonnet_model.replace("1.5", "2.5")
            logger.warning(f"Auto-updated deprecated sonnet model to: {sonnet_model}")
        self.gemini_sonnet_model: str = sonnet_model
        self.gemini_timeout_seconds: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
        self.gemini_max_retries: int = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        self.enable_gemini: bool = os.getenv("ENABLE_GEMINI", "true").lower() == "true"  # Enabled by default
        
        # 🤖 Auto Model Switching Configuration (Disabled for now)
        self.enable_auto_model_switching: bool = os.getenv("ENABLE_AUTO_MODEL_SWITCHING", "false").lower() == "true"
        # Model names must be set in .env file
        flash_model = os.getenv("GEMINI_FLASH_MODEL", "").strip()
        if not flash_model:
            flash_model = default_model  # Fallback to default model
        elif "1.5" in flash_model:
            flash_model = flash_model.replace("1.5", "2.5")
            logger.warning(f"Auto-updated deprecated flash model to: {flash_model}")
        self.gemini_flash_model: str = flash_model
        
        pro_model = os.getenv("GEMINI_PRO_MODEL", "").strip()
        if not pro_model:
            pro_model = default_model  # Fallback to default model
        self.gemini_pro_model: str = pro_model
        
        ultra_model = os.getenv("GEMINI_ULTRA_MODEL", "").strip()
        if not ultra_model:
            ultra_model = default_model  # Fallback to default model
        self.gemini_ultra_model: str = ultra_model
        
        # Storage Configuration
        self.sessions_dir: Path = Path(_BASE_DIR / "data" / "sessions")
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        
        # Logging Configuration
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO").upper()
        log_file_str = os.getenv("LOG_FILE")
        self.log_file: Optional[Path] = Path(log_file_str) if log_file_str else None
        
        # Agent Configuration
        self.controller_max_iterations: int = int(os.getenv("CONTROLLER_MAX_ITERATIONS", "3"))
        self.controller_temperature: float = float(os.getenv("CONTROLLER_TEMPERATURE", "0.3"))
        self.responder_temperature: float = float(os.getenv("RESPONDER_TEMPERATURE", "0.7"))
        
        # MongoDB Configuration
        self.mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.mongodb_database: str = os.getenv("MONGODB_DATABASE", "travel_agent")
        
        # Redis Configuration
        self.redis_host: str = os.getenv("REDIS_HOST", "localhost")
        self.redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
        self.redis_password: Optional[str] = os.getenv("REDIS_PASSWORD")
        self.redis_db: int = int(os.getenv("REDIS_DB", "0"))
        self.redis_ttl: int = int(os.getenv("REDIS_TTL", "3600")) # Default 1 hour for cache
        
        # Authentication Configuration
        # Try GOOGLE_CLIENT_ID first, fallback to VITE_GOOGLE_CLIENT_ID (for shared .env)
        self.google_client_id: str = (
            os.getenv("GOOGLE_CLIENT_ID", "").strip() or 
            os.getenv("VITE_GOOGLE_CLIENT_ID", "").strip()
        )
        self.secret_key: str = os.getenv("SECRET_KEY", "super-secret-key-for-travel-agent-123").strip()
        self.session_cookie_name: str = "session_id"
        self.session_expiry_days: int = 30
        
        # Google Maps Configuration
        self.google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        
        # Amadeus Configuration (Legacy - for backward compatibility)
        self.amadeus_api_key: str = os.getenv("AMADEUS_API_KEY", "").strip()
        self.amadeus_api_secret: str = os.getenv("AMADEUS_API_SECRET", "").strip()
        self.amadeus_env: str = os.getenv("AMADEUS_ENV", "test").strip()
        
        # ✅ Amadeus Search Configuration (แยก keys เพื่อความปลอดภัย)
        self.amadeus_search_env: str = os.getenv("AMADEUS_SEARCH_ENV", "test").strip()
        # Search API Keys: ถ้าไม่ตั้งค่าให้ใช้ legacy keys (backward compatibility)
        self.amadeus_search_api_key: str = os.getenv("AMADEUS_SEARCH_API_KEY", "").strip() or self.amadeus_api_key
        self.amadeus_search_api_secret: str = os.getenv("AMADEUS_SEARCH_API_SECRET", "").strip() or self.amadeus_api_secret
        
        # ✅ Amadeus Booking Configuration (แยก keys เพื่อความปลอดภัย)
        self.amadeus_booking_env: str = os.getenv("AMADEUS_BOOKING_ENV", "test").strip()
        # Booking API Keys: ถ้าไม่ตั้งค่าให้ใช้ legacy keys (backward compatibility)
        self.amadeus_booking_api_key: str = os.getenv("AMADEUS_BOOKING_API_KEY", "").strip() or self.amadeus_api_key
        self.amadeus_booking_api_secret: str = os.getenv("AMADEUS_BOOKING_API_SECRET", "").strip() or self.amadeus_api_secret
        
        # 🔒 Admin Dashboard Configuration (Production Security)
        self.admin_password: str = os.getenv("ADMIN_PASSWORD", "").strip()
        self.admin_enabled: bool = os.getenv("ADMIN_ENABLED", "true").lower() == "true"
        self.admin_require_auth: bool = os.getenv("ADMIN_REQUIRE_AUTH", "true").lower() == "true"
        
        # 💳 Omise Payment Gateway Configuration
        self.omise_secret_key: str = os.getenv("OMISE_SECRET_KEY", "").strip()
        self.omise_public_key: str = os.getenv("OMISE_PUBLIC_KEY", "").strip()
        self.frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()


# Global settings instance
settings = Settings()

