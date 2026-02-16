"""
ระบบบันทึกเหตุการณ์ (Logging) ระดับ production
ทุก log มี session_id และ user_id สำหรับติดตาม
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from contextvars import ContextVar

# Context variables for request-scoped logging
_session_id: ContextVar[Optional[str]] = ContextVar('session_id', default=None)
_user_id: ContextVar[Optional[str]] = ContextVar('user_id', default=None)


class ContextualFormatter(logging.Formatter):
    """Formatter that includes session_id and user_id in logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Add context to record
        record.session_id = _session_id.get() or "N/A"
        record.user_id = _user_id.get() or "N/A"
        return super().format(record)


def setup_logging(
    name: str = "travel_agent",
    level: Optional[str] = None,
    log_file: Optional[Path] = None
) -> logging.Logger:
    """
    Setup production-grade structured logger
    
    Args:
        name: Logger name
        level: Logging level (defaults to settings.log_level)
        log_file: Optional log file path
        
    Returns:
        Configured logger
    """
    # Lazy import to avoid circular dependency
    from app.core.config import settings
    
    log_level = getattr(logging, (level or settings.log_level).upper(), logging.INFO)
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Console handler with contextual formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_format = ContextualFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - [session_id=%(session_id)s] [user_id=%(user_id)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file or settings.log_file:
        log_path = log_file or settings.log_file
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_handler.setLevel(log_level)
        file_format = ContextualFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - [session_id=%(session_id)s] [user_id=%(user_id)s] - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "travel_agent") -> logging.Logger:
    """
    Get logger instance
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Try to setup logging with settings, but fallback to basic setup
        # if settings are not available yet (during config initialization)
        try:
            setup_logging(name)
        except (ImportError, AttributeError):
            # Fallback to basic logger setup when settings are not available
            logger.setLevel(logging.INFO)
            if not logger.handlers:
                console_handler = logging.StreamHandler(sys.stdout)
                console_handler.setLevel(logging.INFO)
                basic_format = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                console_handler.setFormatter(basic_format)
                logger.addHandler(console_handler)
    return logger


def set_logging_context(session_id: Optional[str] = None, user_id: Optional[str] = None):
    """
    Set logging context for current request
    
    Args:
        session_id: Session identifier
        user_id: User identifier
    """
    if session_id:
        _session_id.set(session_id)
    if user_id:
        _user_id.set(user_id)


def clear_logging_context():
    """Clear logging context"""
    _session_id.set(None)
    _user_id.set(None)
