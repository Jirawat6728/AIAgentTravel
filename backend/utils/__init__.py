"""
Utility functions
"""

# Cache module removed - replaced by core.agent_brain.py
from .cookies import (
    get_cookie,
    set_cookie,
    delete_cookie,
    get_all_cookies,
    has_cookie,
)

__all__ = [
    # Cookies
    "get_cookie",
    "set_cookie",
    "delete_cookie",
    "get_all_cookies",
    "has_cookie",
]
