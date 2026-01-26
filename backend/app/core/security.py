"""
Security utilities for password hashing, validation, and user authentication
รวม security.py และ security_helpers.py เป็นไฟล์เดียว
"""
import re
import hashlib
import logging
import bcrypt
from typing import Tuple, Optional
from fastapi import Request, HTTPException
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Bcrypt rounds (cost factor) - 12 is a good balance between security and performance
BCRYPT_ROUNDS = 12


def _pre_hash_password(password: str) -> bytes:
    """
    Pre-hash password with SHA-256 to bypass bcrypt's 72 byte limit
    and handle encoding issues.
    
    Args:
        password: Plain text password
        
    Returns:
        SHA-256 hash bytes (always 32 bytes, well under bcrypt's 72 byte limit)
    """
    # SHA-256 hash the password (always produces 32 bytes)
    # This is always well under bcrypt's 72 byte limit
    hashed_bytes = hashlib.sha256(password.encode('utf-8')).digest()
    return hashed_bytes


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (with SHA-256 pre-hashing)
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password (as string)
    """
    if not password:
        raise ValueError("Password cannot be empty")
    
    if not isinstance(password, str):
        raise TypeError("Password must be a string")
    
    # Pre-hash to handle long passwords (SHA-256 = 32 bytes, well under 72 bytes)
    pre_hashed_bytes = _pre_hash_password(password)
    byte_length = len(pre_hashed_bytes)
    
    logger.debug(f"Pre-hashed password length: {byte_length} bytes")
    
    # Double-check: Ensure the pre-hashed bytes are within bcrypt's 72 byte limit
    if byte_length > 72:
        # Truncate to 72 bytes if somehow it exceeds (shouldn't happen with SHA-256)
        logger.warning(f"Pre-hashed password exceeded 72 bytes ({byte_length}), truncating")
        pre_hashed_bytes = pre_hashed_bytes[:72]
        byte_length = len(pre_hashed_bytes)
    
    # Hash with bcrypt directly - the pre_hashed_bytes are guaranteed to be <= 72 bytes
    try:
        # Generate salt and hash
        salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
        hashed_bytes = bcrypt.hashpw(pre_hashed_bytes, salt)
        # Convert to string for storage
        hashed = hashed_bytes.decode('utf-8')
        logger.debug(f"Password hashed successfully (pre-hash: {byte_length} bytes)")
        return hashed
    except Exception as e:
        logger.error(f"Bcrypt hashing failed: {e}, pre-hash length: {byte_length} bytes")
        raise ValueError(f"Password hashing failed: {e}")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        # Pre-hash the input password
        pre_hashed_bytes = _pre_hash_password(plain_password)
        
        # Ensure it's within 72 bytes
        if len(pre_hashed_bytes) > 72:
            pre_hashed_bytes = pre_hashed_bytes[:72]
        
        # Convert hashed_password string to bytes
        hashed_bytes = hashed_password.encode('utf-8')
        
        # Verify using bcrypt
        return bcrypt.checkpw(pre_hashed_bytes, hashed_bytes)
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        # Fallback for old passwords that weren't pre-hashed (migration path)
        try:
            # Try verifying the plain password directly (for old passwords)
            plain_bytes = plain_password.encode('utf-8')
            if len(plain_bytes) > 72:
                plain_bytes = plain_bytes[:72]
            hashed_bytes = hashed_password.encode('utf-8')
            return bcrypt.checkpw(plain_bytes, hashed_bytes)
        except Exception:
            return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password strength
    
    Requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    - Contains at least one special character
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"
    
    return True, ""


def calculate_password_strength(password: str) -> dict:
    """
    Calculate password strength score and feedback
    
    Args:
        password: Password to evaluate
        
    Returns:
        Dict with score (0-4) and feedback messages
    """
    score = 0
    feedback = []
    
    # Length check
    if len(password) >= 8:
        score += 1
    else:
        feedback.append("Add more characters (minimum 8)")
    
    # Uppercase check
    if re.search(r"[A-Z]", password):
        score += 1
    else:
        feedback.append("Add uppercase letters (A-Z)")
    
    # Lowercase check
    if re.search(r"[a-z]", password):
        score += 1
    else:
        feedback.append("Add lowercase letters (a-z)")
    
    # Number check
    if re.search(r"\d", password):
        score += 1
    else:
        feedback.append("Add numbers (0-9)")
    
    # Special character check
    if re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        score += 1
    else:
        feedback.append("Add special characters (!@#$...)")
    
    # Additional length bonus
    if len(password) >= 12:
        score = min(score + 1, 5)
    
    # Strength label
    if score <= 1:
        strength = "Very Weak"
    elif score == 2:
        strength = "Weak"
    elif score == 3:
        strength = "Fair"
    elif score == 4:
        strength = "Good"
    else:
        strength = "Strong"
    
    return {
        "score": score,
        "strength": strength,
        "feedback": feedback
    }


# =============================================================================
# Security Helper Functions (from security_helpers.py)
# =============================================================================

def extract_user_id_from_request(request: Request) -> Optional[str]:
    """
    Extract user_id from request (cookie first, then header)
    
    Args:
        request: FastAPI Request object
        
    Returns:
        user_id string or None if not found
    """
    # ✅ Priority: Session cookie > X-User-ID header
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        user_id = request.headers.get("X-User-ID")
    
    return user_id


def extract_user_id_from_session_id(session_id: str) -> Optional[str]:
    """
    Extract user_id from session_id (format: user_id::chat_id)
    
    Args:
        session_id: Session identifier (format: user_id::chat_id)
        
    Returns:
        user_id string or None if invalid format
    """
    if not session_id:
        return None
    
    if "::" in session_id:
        return session_id.split("::")[0]
    
    # If no "::" separator, assume entire session_id is user_id (backward compatibility)
    return session_id


def validate_user_owns_resource(
    resource_user_id: str,
    requesting_user_id: Optional[str],
    resource_type: str = "resource",
    resource_id: Optional[str] = None
) -> bool:
    """
    Validate that requesting user owns the resource
    
    Args:
        resource_user_id: user_id from the resource (database)
        requesting_user_id: user_id from request (session cookie/header)
        resource_type: Type of resource for logging (e.g., "booking", "session")
        resource_id: Optional resource ID for logging
        
    Returns:
        True if user owns resource, False otherwise
        
    Raises:
        HTTPException: 403 if user does not own resource
    """
    if not requesting_user_id:
        logger.warning(f"Unauthorized access attempt: No user_id in request for {resource_type} {resource_id}")
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    if resource_user_id != requesting_user_id:
        logger.error(
            f"🚨 SECURITY ALERT: {resource_type} ownership mismatch! "
            f"resource_user_id={resource_user_id}, requesting_user_id={requesting_user_id}, "
            f"resource_id={resource_id}"
        )
        raise HTTPException(
            status_code=403,
            detail=f"You do not have permission to access this {resource_type}"
        )
    
    return True


def validate_session_user_id(session_id: str, user_id: Optional[str]) -> bool:
    """
    Validate that session_id matches user_id
    
    Args:
        session_id: Session identifier (format: user_id::chat_id)
        user_id: User identifier from request
        
    Returns:
        True if session belongs to user, False otherwise
        
    Raises:
        HTTPException: 403 if session does not belong to user
    """
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    expected_user_id = extract_user_id_from_session_id(session_id)
    if not expected_user_id:
        logger.warning(f"Invalid session_id format: {session_id}")
        raise HTTPException(
            status_code=400,
            detail="Invalid session identifier"
        )
    
    if expected_user_id != user_id:
        logger.error(
            f"🚨 SECURITY ALERT: Session ownership mismatch! "
            f"session_id={session_id}, expected_user_id={expected_user_id}, "
            f"requesting_user_id={user_id}"
        )
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this session"
        )
    
    return True


def build_user_filter(user_id: Optional[str], filter_dict: Optional[dict] = None) -> dict:
    """
    Build MongoDB query filter with user_id
    
    ✅ CRITICAL: Always use this function to ensure user_id is included in queries
    This prevents data leakage between users
    
    Args:
        user_id: User identifier (must not be None)
        filter_dict: Additional filter criteria
        
    Returns:
        MongoDB query filter dictionary with user_id
        
    Raises:
        ValueError: If user_id is None
    """
    if not user_id:
        raise ValueError("user_id is required for data isolation")
    
    if filter_dict is None:
        filter_dict = {}
    
    # ✅ CRITICAL: Always include user_id in filter to prevent data leakage
    filter_dict["user_id"] = user_id
    
    return filter_dict
