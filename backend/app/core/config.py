"""
Application Configuration
Centralized settings management
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load .env file
_BASE_DIR = Path(__file__).parent.parent.parent
_DOTENV_PATH = Path(os.getenv("DOTENV_PATH") or (_BASE_DIR / ".env"))
load_dotenv(dotenv_path=_DOTENV_PATH, override=True)


class Settings:
    """Application settings"""
    
    def __init__(self):
        # LLM Configuration
        self.gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model_name: str = os.getenv("GEMINI_MODEL_NAME", "gemini-3-flash-preview").strip()
        self.gemini_timeout_seconds: int = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))
        self.gemini_max_retries: int = int(os.getenv("GEMINI_MAX_RETRIES", "3"))
        
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
        
        # Authentication Configuration
        self.google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        self.secret_key: str = os.getenv("SECRET_KEY", "super-secret-key-for-travel-agent-123").strip()
        self.session_cookie_name: str = "session_id"
        self.session_expiry_days: int = 30
        
        # Google Maps Configuration
        self.google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
        
        # Amadeus Configuration
        self.amadeus_api_key: str = os.getenv("AMADEUS_API_KEY", "").strip()
        self.amadeus_api_secret: str = os.getenv("AMADEUS_API_SECRET", "").strip()
        self.amadeus_env: str = os.getenv("AMADEUS_ENV", "test").strip()
        
        # Amadeus Search Configuration
        self.amadeus_search_env: str = os.getenv("AMADEUS_SEARCH_ENV", "test").strip()
        
        # Amadeus Booking Configuration
        self.amadeus_booking_env: str = os.getenv("AMADEUS_BOOKING_ENV", "test").strip()


# Global settings instance
settings = Settings()

