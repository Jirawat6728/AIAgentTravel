"""การตั้งค่าแอป (ตัวแปรแวดล้อม, Redis, MongoDB, Gemini, Amadeus ฯลฯ)."""

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
        # Model names: ใช้จาก .env หรือ default gemini-2.5-flash เพื่อให้แอปรันได้แม้ .env จะไม่ครบ
        # Note: gemini-1.5-flash is deprecated, use gemini-2.5-flash instead
        default_model = (os.getenv("GEMINI_MODEL_NAME", "") or "gemini-2.5-flash").strip()
        if not default_model:
            default_model = "gemini-2.5-flash"
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
        # Default true: ใช้ LangChain/LangGraph เป็นค่าเริ่มต้นของระบบ (ไม่ต้องตั้งใน .env)
        self.enable_langchain_orchestration: bool = os.getenv("ENABLE_LANGCHAIN_ORCHESTRATION", "true").lower() == "true"
        self.enable_langgraph_agent_mode: bool = os.getenv("ENABLE_LANGGRAPH_AGENT_MODE", "true").lower() == "true"
        self.enable_langgraph_checkpointer: bool = os.getenv("ENABLE_LANGGRAPH_CHECKPOINTER", "true").lower() == "true"
        # เมื่อ true ให้ LangGraph จัดการ workflow ทั้งหมดแทน loop ใน agent.run_controller
        self.enable_langgraph_full_workflow: bool = os.getenv("ENABLE_LANGGRAPH_FULL_WORKFLOW", "true").lower() == "true"
        self.controller_max_iterations: int = int(os.getenv("CONTROLLER_MAX_ITERATIONS", "3"))
        self.controller_temperature: float = float(os.getenv("CONTROLLER_TEMPERATURE", "0.3"))
        self.responder_temperature: float = float(os.getenv("RESPONDER_TEMPERATURE", "0.7"))
        # Timeout ของ stream chat (ใช้ร่วมกันระหว่าง middleware และ chat.py)
        # Agent mode ใช้เวลานานกว่า (ค้นหา + เลือก + จอง) จึงให้ timeout สูงกว่า
        self.chat_timeout_agent: int = int(os.getenv("CHAT_TIMEOUT_AGENT", "120"))
        self.chat_timeout_normal: int = int(os.getenv("CHAT_TIMEOUT_NORMAL", "90"))
        # Middleware timeout ต้องมากกว่า chat timeout อย่างน้อย 10s (buffer)
        self.chat_middleware_timeout: int = self.chat_timeout_agent + 15
        
        # MongoDB Configuration
        self.mongodb_uri: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.mongodb_database: str = os.getenv("MONGODB_DATABASE", "travel_agent")
        
        # Authentication Configuration
        # Try GOOGLE_CLIENT_ID first, fallback to VITE_GOOGLE_CLIENT_ID (for shared .env)
        self.google_client_id: str = (
            os.getenv("GOOGLE_CLIENT_ID", "").strip() or 
            os.getenv("VITE_GOOGLE_CLIENT_ID", "").strip()
        )
        self.secret_key: str = os.getenv("SECRET_KEY", "super-secret-key-for-travel-agent-123").strip()
        self.session_cookie_name: str = "session_id"
        self.session_expiry_days: int = 30

        # Firebase Configuration
        # Firebase Admin SDK - can use service account JSON file or credentials
        firebase_creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "").strip()
        self.firebase_credentials_path: Optional[str] = firebase_creds_path if firebase_creds_path else None
        # Alternative: Use Firebase project ID (for default credentials)
        self.firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        # Firebase Web API Key (for frontend)
        self.firebase_api_key: str = os.getenv("FIREBASE_API_KEY", "").strip()
        self.firebase_auth_domain: str = os.getenv("FIREBASE_AUTH_DOMAIN", "").strip()
        
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
        self.admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com").strip()
        self.admin_password: str = os.getenv("ADMIN_PASSWORD", "").strip()
        self.admin_enabled: bool = os.getenv("ADMIN_ENABLED", "true").lower() == "true"
        self.admin_require_auth: bool = os.getenv("ADMIN_REQUIRE_AUTH", "true").lower() == "true"
        if not self.admin_password:
            logger.warning("ADMIN_PASSWORD not set - admin login disabled for security")
        
        # 💳 Omise Payment Gateway Configuration
        self.omise_secret_key: str = os.getenv("OMISE_SECRET_KEY", "").strip()
        self.omise_public_key: str = os.getenv("OMISE_PUBLIC_KEY", "").strip()
        self.frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
        # Backend base URL — used by Agent Mode to call booking API internally
        # Set API_BASE_URL in .env for production (e.g. https://api.yourdomain.com)
        self.api_base_url: str = os.getenv("API_BASE_URL", "").strip()

        # 📧 Gmail SMTP Configuration (สำหรับส่งอีเมลยืนยัน)
        self.gmail_user: str = os.getenv("GMAIL_USER", "").strip()
        self.gmail_app_password: str = os.getenv("GMAIL_APP_PASSWORD", "").strip()
        self.site_name: str = os.getenv("SITE_NAME", "AI Travel Agent").strip()


    def validate(self) -> list[str]:
        """
        ตรวจสอบค่า config ที่จำเป็นแล้วคืน list ของคำเตือน
        เรียกใน lifespan ของ main.py เพื่อแจ้งเตือนตอน startup
        """
        logger = get_logger(__name__)
        warnings: list[str] = []

        # ─── Critical: แอปทำงานไม่ได้ถ้าขาด ──────────────────────────────
        if not self.gemini_api_key:
            msg = "GEMINI_API_KEY ไม่ได้ตั้งค่า — chat จะไม่ทำงาน"
            logger.error(f"[config] ❌ {msg}")
            warnings.append(msg)
        elif len(self.gemini_api_key) < 20:
            msg = "GEMINI_API_KEY ดูเหมือนสั้นผิดปกติ (น้อยกว่า 20 ตัวอักษร)"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        is_production = os.getenv("APP_ENV", "development").lower() in ("production", "prod")

        if self.secret_key == "super-secret-key-for-travel-agent-123":
            if is_production:
                msg = "SECRET_KEY ยังเป็นค่า default — ห้าม deploy production โดยไม่เปลี่ยน SECRET_KEY"
                logger.error(f"[config] ❌ {msg}")
                raise RuntimeError(msg)
            else:
                msg = "SECRET_KEY ยังเป็นค่า default — ควรเปลี่ยนก่อน deploy production"
                logger.warning(f"[config] ⚠️  {msg}")
                warnings.append(msg)

        # ─── Important: ฟีเจอร์บางส่วนจะไม่ทำงาน ─────────────────────────
        if not self.amadeus_api_key and not self.amadeus_search_api_key:
            msg = "AMADEUS_API_KEY ไม่ได้ตั้งค่า — ค้นหาเที่ยวบิน/โรงแรมจะไม่ทำงาน"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        search_env = self.amadeus_search_env.lower()
        if search_env == "test":
            msg = "AMADEUS_SEARCH_ENV=test — ข้อมูลเที่ยวบิน/โรงแรมเป็นข้อมูลทดสอบ (sandbox) ไม่ใช่ข้อมูลจริง"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        if not self.omise_secret_key:
            msg = "OMISE_SECRET_KEY ไม่ได้ตั้งค่า — ระบบชำระเงินจะไม่ทำงาน"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        if not self.omise_public_key:
            msg = "OMISE_PUBLIC_KEY ไม่ได้ตั้งค่า — ระบบชำระเงินจะไม่ทำงาน"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        if not self.firebase_project_id and not self.firebase_credentials_path:
            msg = "FIREBASE_PROJECT_ID ไม่ได้ตั้งค่า — Firebase auth อาจไม่ทำงาน"
            logger.warning(f"[config] ⚠️  {msg}")
            warnings.append(msg)

        # ─── Informational ────────────────────────────────────────────────
        if not self.google_maps_api_key:
            logger.info("[config] ℹ️  GOOGLE_MAPS_API_KEY ไม่ได้ตั้งค่า — Maps features disabled")

        if not self.api_base_url:
            logger.info("[config] ℹ️  API_BASE_URL ไม่ได้ตั้งค่า — Agent Mode booking จะใช้ localhost:8000")

        if not warnings:
            logger.info("[config] ✅ การตรวจสอบ config ผ่านทั้งหมด")
        return warnings


# Global settings instance
settings = Settings()

