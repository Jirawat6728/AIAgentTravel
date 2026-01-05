"""
Cookie utility functions
Provides cookie parsing and management
"""

from __future__ import annotations
from typing import Dict, Optional
from fastapi import Request, Response
import logging

logger = logging.getLogger(__name__)


def get_cookie(request: Request, name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get cookie value from request
    
    Args:
        request: FastAPI Request object
        name: Cookie name
        default: Default value if cookie not found
    
    Returns:
        Cookie value or default
    """
    return request.cookies.get(name, default)


def set_cookie(
    response: Response,
    name: str,
    value: str,
    max_age: int = 7 * 24 * 60 * 60,  # 7 days default
    path: str = "/",
    domain: Optional[str] = None,
    secure: bool = True,
    httponly: bool = True,
    samesite: str = "Lax",
) -> None:
    """
    Set cookie in response
    
    Args:
        response: FastAPI Response object
        name: Cookie name
        value: Cookie value
        max_age: Max age in seconds (default: 7 days)
        path: Cookie path (default: "/")
        domain: Cookie domain (optional)
        secure: Secure flag (default: True)
        httponly: HttpOnly flag (default: True)
        samesite: SameSite attribute (default: "Lax")
    """
    response.set_cookie(
        key=name,
        value=value,
        max_age=max_age,
        path=path,
        domain=domain,
        secure=secure,
        httponly=httponly,
        samesite=samesite,
    )


def delete_cookie(
    response: Response,
    name: str,
    path: str = "/",
    domain: Optional[str] = None,
) -> None:
    """
    Delete cookie by setting expiration to past
    
    Args:
        response: FastAPI Response object
        name: Cookie name
        path: Cookie path (default: "/")
        domain: Cookie domain (optional)
    """
    response.delete_cookie(
        key=name,
        path=path,
        domain=domain,
    )


def get_all_cookies(request: Request) -> Dict[str, str]:
    """
    Get all cookies from request
    
    Args:
        request: FastAPI Request object
    
    Returns:
        Dictionary of cookie names and values
    """
    return dict(request.cookies)


def has_cookie(request: Request, name: str) -> bool:
    """
    Check if cookie exists
    
    Args:
        request: FastAPI Request object
        name: Cookie name
    
    Returns:
        True if cookie exists, False otherwise
    """
    return name in request.cookies

