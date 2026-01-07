"""
Authentication Router
Handles Google Login, Session Management, and User Profile
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.storage.mongodb_storage import MongoStorage
from app.models.database import User, SessionDocument

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

class GoogleLoginRequest(BaseModel):
    id_token: str

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    nationality: Optional[str] = None
    passport_no: Optional[str] = None
    passport_expiry: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None

@router.post("/google")
async def google_login(request: GoogleLoginRequest, response: Response):
    # ... existing code ...
    try:
        # Check for dev bypass if client ID is missing
        if not settings.google_client_id and request.id_token == "dev_token":
            return await create_dev_session(response)

        # Verify token with Google
        idinfo = id_token.verify_oauth2_token(
            request.id_token, 
            google_requests.Request(), 
            settings.google_client_id
        )

        # ID token is valid. Get user info from idinfo.
        google_id = idinfo['sub']
        email = idinfo['email']
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        given_name = idinfo.get('given_name')
        family_name = idinfo.get('family_name')

        storage = MongoStorage()
        await storage.connect()

        # Check if user exists in sessions collection (acting as users collection for now or use dedicated)
        # In a real system, we'd have a dedicated users collection
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"email": email})

        if not user_data:
            # Create new user
            user = User(
                user_id=google_id,
                email=email,
                full_name=name,
                first_name=given_name,
                last_name=family_name,
                profile_image=picture,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            await users_collection.insert_one(user.model_dump())
            logger.info(f"Created new user: {email}")
        else:
            # Update last login
            await users_collection.update_one(
                {"email": email},
                {"$set": {"last_login": datetime.utcnow()}}
            )
            user = User(**user_data)
            logger.info(f"User logged in: {email}")

        # Set session cookie (simplified: use google_id as session_id for now)
        # In production, use a signed JWT or a session store
        response.set_cookie(
            key=settings.session_cookie_name,
            value=user.user_id,
            httponly=True,
            max_age=settings.session_expiry_days * 24 * 60 * 60,
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )

        return {"ok": True, "user": user.model_dump()}

    except ValueError as e:
        # Invalid token
        logger.error(f"Invalid Google token: {e}")
        raise HTTPException(status_code=400, detail="Invalid token")
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/me")
async def get_me(request: Request):
    """
    Get current user profile from session cookie
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        return {"user": None}

    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"user_id": user_id})

        if not user_data:
            return {"user": None}

        return {"user": User(**user_data).model_dump()}
    except Exception as e:
        logger.error(f"Error getting user profile: {e}")
        return {"user": None}

@router.post("/logout")
async def logout(response: Response):
    """
    Clear session cookie
    """
    response.delete_cookie(settings.session_cookie_name)
    return {"ok": True}

@router.put("/profile")
async def update_profile(request: Request, profile: ProfileUpdateRequest):
    """
    Update current user profile
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        update_data = {k: v for k, v in profile.model_dump().items() if v is not None}
        if not update_data:
            return {"ok": True}

        result = await users_collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")

        # Get updated user
        user_data = await users_collection.find_one({"user_id": user_id})
        return {"ok": True, "user": User(**user_data).model_dump()}

    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """
    Standard login with email (Password is optional for dev)
    """
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]

        # Find user or create a new one
        user_data = await users_collection.find_one({"email": request.email})

        if not user_data:
            # Create a simple user for testing
            user = User(
                user_id=f"user_{int(datetime.utcnow().timestamp())}",
                email=request.email,
                full_name=request.email.split('@')[0],
                first_name=request.email.split('@')[0],
                last_name="Guest",
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            await users_collection.insert_one(user.model_dump())
            logger.info(f"Created new dev user: {request.email}")
        else:
            user = User(**user_data)
            await users_collection.update_one(
                {"email": request.email},
                {"$set": {"last_login": datetime.utcnow()}}
            )

        # Set Session Cookie
        response.set_cookie(
            key=settings.session_cookie_name,
            value=user.user_id,
            httponly=True,
            max_age=settings.session_expiry_days * 24 * 60 * 60,
            samesite="lax",
            secure=False
        )

        return {"ok": True, "user": user.model_dump()}

    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/dev-login")
async def dev_login(response: Response):
    """
    Special login for development when Google OAuth is not configured
    Only works on localhost
    """
    storage = MongoStorage()
    await storage.connect()
    users_collection = storage.db["users"]
    
    dev_id = "dev_guest_123"
    user_data = await users_collection.find_one({"user_id": dev_id})
    
    if not user_data:
        user = User(
            user_id=dev_id,
            email="guest@example.com",
            full_name="Guest User",
            first_name="Guest",
            last_name="User",
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )
        await users_collection.insert_one(user.model_dump())
    else:
        user = User(**user_data)

    response.set_cookie(
        key=settings.session_cookie_name,
        value=user.user_id,
        httponly=True,
        max_age=settings.session_expiry_days * 24 * 60 * 60,
        samesite="lax",
        secure=False
    )
    
    return {"ok": True, "user": user.model_dump()}

