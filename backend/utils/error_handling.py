"""
Error handling utilities and helpers
Provides consistent error handling patterns across the application
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Callable, TypeVar, Union
import logging
import traceback
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar('T')


def safe_get(dictionary: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    """
    Safely get nested dictionary values.
    
    Args:
        dictionary: Dictionary to search
        *keys: Nested keys to access
        default: Default value if key doesn't exist
    
    Returns:
        Value at nested key or default
    
    Example:
        safe_get(data, "user", "profile", "name", default="Unknown")
    """
    try:
        value = dictionary
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
            if value is None:
                return default
        return value if value is not None else default
    except (KeyError, TypeError, AttributeError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert value to int, return default on error"""
    try:
        if value is None:
            return default
        return int(float(str(value)))
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert value to float, return default on error"""
    try:
        if value is None:
            return default
        return float(str(value))
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert value to string, return default on error"""
    try:
        if value is None:
            return default
        return str(value).strip() if isinstance(value, str) else str(value)
    except (ValueError, TypeError):
        return default


def safe_list(value: Any, default: Optional[list] = None) -> list:
    """Safely convert value to list, return default on error"""
    if default is None:
        default = []
    try:
        if value is None:
            return default
        if isinstance(value, list):
            return value
        if isinstance(value, (tuple, set)):
            return list(value)
        return [value]
    except (TypeError, ValueError):
        return default


def safe_dict(value: Any, default: Optional[dict] = None) -> dict:
    """Safely convert value to dict, return default on error"""
    if default is None:
        default = {}
    try:
        if value is None:
            return default
        if isinstance(value, dict):
            return value
        return default
    except (TypeError, ValueError):
        return default


def handle_async_error(
    func: Callable,
    default_return: Any = None,
    log_error: bool = True,
    error_message: Optional[str] = None
) -> Callable:
    """
    Decorator to handle errors in async functions.
    
    Args:
        func: Async function to wrap
        default_return: Value to return on error
        log_error: Whether to log the error
        error_message: Custom error message
    
    Returns:
        Wrapped function
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if log_error:
                error_msg = error_message or f"Error in {func.__name__}"
                logger.error(f"{error_msg}: {str(e)}", exc_info=True)
            return default_return
    return wrapper


def handle_sync_error(
    func: Callable,
    default_return: Any = None,
    log_error: bool = True,
    error_message: Optional[str] = None
) -> Callable:
    """
    Decorator to handle errors in sync functions.
    
    Args:
        func: Function to wrap
        default_return: Value to return on error
        log_error: Whether to log the error
        error_message: Custom error message
    
    Returns:
        Wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if log_error:
                error_msg = error_message or f"Error in {func.__name__}"
                logger.error(f"{error_msg}: {str(e)}", exc_info=True)
            return default_return
    return wrapper


def validate_required_fields(data: Dict[str, Any], required_fields: list[str]) -> tuple[bool, Optional[str]]:
    """
    Validate that required fields exist in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(data, dict):
        return False, "Data must be a dictionary"
    
    missing = [field for field in required_fields if field not in data or data[field] is None]
    if missing:
        return False, f"Missing required fields: {', '.join(missing)}"
    
    return True, None


def validate_non_empty(data: Union[list, dict, str, Any], field_name: str = "field") -> tuple[bool, Optional[str]]:
    """
    Validate that data is not empty.
    
    Args:
        data: Data to validate
        field_name: Name of the field for error message
    
    Returns:
        (is_valid, error_message)
    """
    if data is None:
        return False, f"{field_name} cannot be None"
    
    if isinstance(data, (list, dict, str)):
        if len(data) == 0:
            return False, f"{field_name} cannot be empty"
    
    return True, None

