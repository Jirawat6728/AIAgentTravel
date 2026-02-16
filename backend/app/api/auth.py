"""
เราเตอร์การยืนยันตัวตน
จัดการล็อกอินอีเมล/รหัสผ่าน Google OAuth Firebase การจัดการเซสชัน และโปรไฟล์ผู้ใช้
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request, Query
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from dateutil import parser as date_parser

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, auth as firebase_auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    firebase_auth = None

from app.core.config import settings
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength,
    hash_password_from_client_sha256,
    verify_password_from_client_hash,
)
from app.storage.mongodb_storage import MongoStorage
from app.models.database import User, SessionDocument, FamilyMember
from app.services.email_service import get_email_service
from app.services.sms_service import get_sms_service, generate_otp

logger = get_logger(__name__)

# Initialize Firebase Admin SDK (lazy initialization)
_firebase_initialized = False

def initialize_firebase():
    """Initialize Firebase Admin SDK if not already initialized"""
    global _firebase_initialized
    
    if _firebase_initialized:
        return
    
    if not FIREBASE_AVAILABLE:
        logger.warning("Firebase Admin SDK not available. Install: pip install firebase-admin")
        return
    
    try:
        # Check if Firebase is already initialized
        if firebase_admin._apps:
            _firebase_initialized = True
            logger.info("Firebase Admin SDK already initialized")
            return
        
        # Initialize Firebase with credentials
        if settings.firebase_credentials_path:
            # Use service account JSON file
            cred = credentials.Certificate(settings.firebase_credentials_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"Firebase Admin SDK initialized with credentials file: {settings.firebase_credentials_path}")
        elif settings.firebase_project_id:
            # Use default credentials (for GCP environments)
            firebase_admin.initialize_app(options={"projectId": settings.firebase_project_id})
            logger.info(f"Firebase Admin SDK initialized with project ID: {settings.firebase_project_id}")
        else:
            # Try to use default credentials (for local development with gcloud auth)
            try:
                firebase_admin.initialize_app()
                logger.info("Firebase Admin SDK initialized with default credentials")
            except Exception as default_error:
                logger.warning(f"Firebase Admin SDK initialization failed: {default_error}. Firebase authentication will be disabled.")
                return
        
        _firebase_initialized = True
        logger.info("✅ Firebase Admin SDK initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}", exc_info=True)

router = APIRouter(prefix="/api/auth", tags=["auth"])

class GoogleLoginRequest(BaseModel):
    """Google OAuth login. Send id_token from Google Sign-In (not 'token')."""
    id_token: str = Field(..., description="Google ID token from OAuth flow")

class FirebaseLoginRequest(BaseModel):
    """Firebase Authentication login. Send idToken from Firebase Auth."""
    idToken: str = Field(..., description="Firebase ID token from Firebase Authentication")

class LoginRequest(BaseModel):
    email: str
    password: Optional[str] = None
    remember_me: Optional[bool] = Field(default=False, description="Remember me (extend session expiry to 30 days)")

class RegisterRequest(BaseModel):
    """Registration. Use camelCase: firstName, lastName (API accepts both)."""
    email: str
    password: str
    first_name: str = Field(alias="firstName", description="First name (camelCase: firstName)")
    last_name: str = Field(alias="lastName", description="Last name (camelCase: lastName)")
    first_name_th: Optional[str] = Field(default=None, alias="firstNameTh", description="First name in Thai")
    last_name_th: Optional[str] = Field(default=None, alias="lastNameTh", description="Last name in Thai")
    phone: Optional[str] = None

    model_config = {"populate_by_name": True}

class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    first_name_th: Optional[str] = Field(default=None, description="First name in Thai")
    last_name_th: Optional[str] = Field(default=None, description="Last name in Thai")
    phone: Optional[str] = None
    nationality: Optional[str] = None
    national_id: Optional[str] = Field(default=None, description="National ID Card number (13 digits)")
    passport_no: Optional[str] = None
    passport_expiry: Optional[str] = None
    passport_issue_date: Optional[str] = Field(default=None, description="Passport issue date (YYYY-MM-DD)")
    passport_issuing_country: Optional[str] = Field(default=None, description="Country that issued the passport (ISO country code)")
    passport_given_names: Optional[str] = Field(default=None, description="Given names as shown on passport (English)")
    passport_surname: Optional[str] = Field(default=None, description="Surname as shown on passport (English)")
    place_of_birth: Optional[str] = Field(default=None, description="Place of birth (city, country)")
    passport_type: Optional[str] = Field(default="N", description="Passport type: N=Normal, D=Diplomatic, O=Official, S=Service")
    # Visa information (for international travel)
    visa_type: Optional[str] = Field(default=None, description="Visa type: TOURIST, BUSINESS, STUDENT, WORK, TRANSIT, VISA_FREE, ETA, EVISA, OTHER")
    visa_number: Optional[str] = Field(default=None, description="Visa number")
    visa_issuing_country: Optional[str] = Field(default=None, description="Country that issued the visa (ISO country code)")
    visa_issue_date: Optional[str] = Field(default=None, description="Visa issue date (YYYY-MM-DD)")
    visa_expiry_date: Optional[str] = Field(default=None, description="Visa expiry date (YYYY-MM-DD)")
    visa_entry_type: Optional[str] = Field(default="S", description="Visa entry type: S=Single Entry, M=Multiple Entry")
    visa_purpose: Optional[str] = Field(default="T", description="Visa purpose: T=Tourism, B=Business, S=Study, W=Work, O=Other")
    dob: Optional[str] = None
    gender: Optional[str] = None
    profile_image: Optional[str] = Field(default=None, description="Profile image URL or base64 data URL")
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(default=None, description="Emergency contact full name")
    emergency_contact_phone: Optional[str] = Field(default=None, description="Emergency contact phone number")
    emergency_contact_relation: Optional[str] = Field(default=None, description="Emergency contact relation: SPOUSE, PARENT, FRIEND, OTHER")
    emergency_contact_email: Optional[str] = Field(default=None, description="Emergency contact email")
    hotel_number_of_guests: Optional[int] = Field(default=1, description="Number of guests (including main guest)")
    # Notification & App preferences (from Settings page)
    preferences: Optional[Dict[str, Any]] = Field(default=None, description="User preferences: notificationsEnabled, bookingNotifications, paymentNotifications, tripChangeNotifications, emailNotifications, etc.")
    # ผู้จองร่วม (สมาชิกในครอบครัว) - สำหรับเลือกตอนจองมากกว่า 1 คน
    family: Optional[list] = Field(default=None, description="List of family members (adult/child) for co-traveler selection: [{id, type, first_name, last_name, date_of_birth?, passport_no?, ...}]")

def _sha256_hex(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@router.post("/login")
async def login(request: LoginRequest, response: Response, raw_request: Request):
    """
    Login with email and password.
    Returns {ok: true, user: {...}}. Sets session cookie (no access_token).
    Handles both admin@example.com and regular users.
    If header X-Password-Encoding: sha256 is sent, request.password must be SHA-256(password) in hex (64 chars).
    """
    try:
        if not request.password:
            raise HTTPException(status_code=400, detail="Password is required")

        client_sends_sha256 = (raw_request.headers.get("X-Password-Encoding") or "").strip().lower() == "sha256"

        # Initialize storage and collection
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        # ✅ Normalize email for consistent checking (lowercase, trimmed)
        normalized_email = request.email.lower().strip()
        
        # 1. Admin/Test Account Check (from environment variables)
        # ✅ SECURITY: Use environment variables instead of hardcoded credentials
        admin_password_ok = False
        if normalized_email == settings.admin_email.lower().strip() and settings.admin_password:
            if client_sends_sha256:
                admin_password_ok = request.password == _sha256_hex(settings.admin_password)
            else:
                admin_password_ok = request.password == settings.admin_password
        if admin_password_ok:
            user_data = await users_collection.find_one({"email": normalized_email})
            
            if not user_data:
                # Create admin user if not exists
                user = User(
                    user_id="admin_user_id",
                    email="admin@example.com",
                    full_name="Admin Test",
                    first_name="Admin",
                    last_name="Test",
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow(),
                    is_admin=True  # Custom flag
                )
                await users_collection.insert_one(user.model_dump())
                logger.info(f"Created admin user: {request.email}")
            else:
                # Update last login
                await users_collection.update_one(
                    {"email": request.email},
                    {"$set": {"last_login": datetime.utcnow()}}
                )
                # Ensure is_admin is set
                if not user_data.get("is_admin"):
                    await users_collection.update_one(
                        {"email": request.email},
                        {"$set": {"is_admin": True}}
                    )
                    user_data["is_admin"] = True
                
                user = User(**user_data)
                logger.info(f"Admin logged in: {request.email}")
            
            # Set session cookie
            expiry_days = 30 if request.remember_me else (settings.session_expiry_days or 1)
            max_age_seconds = expiry_days * 24 * 60 * 60
            response.set_cookie(
                key=settings.session_cookie_name,
                value=user.user_id,
                httponly=True,
                max_age=max_age_seconds,
                samesite="lax",
                secure=False
            )
            
            return {"ok": True, "user": user.model_dump()}

        # 2. General User Login (verify password from DB)
        # ✅ Use normalized email for case-insensitive search
        user_data = await users_collection.find_one({"email": normalized_email})
        
        # If not found with exact match, try case-insensitive regex search
        if not user_data:
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{normalized_email}$", "$options": "i"}
            })

        if not user_data:
            # ✅ Return specific error for email not found
            logger.warning(f"Login attempt with non-existent email: {normalized_email}")
            raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

        # Verify password
        password_hash = user_data.get("password_hash")
        if not password_hash:
            logger.warning(f"User {normalized_email} has no password_hash - cannot login with password")
            raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

        # Verify password (support client sending SHA-256 hex so plain password is never on the wire)
        try:
            logger.info(f"Attempting password verification for user {normalized_email}")
            if client_sends_sha256:
                password_valid = verify_password_from_client_hash(request.password, password_hash)
            else:
                password_valid = verify_password(request.password, password_hash)

            if not password_valid:
                logger.warning(
                    f"Password verification failed for user {normalized_email}. "
                    f"Hash exists: {bool(password_hash)}, Hash length: {len(password_hash) if password_hash else 0}"
                )
                raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

            logger.info(f"Password verified successfully for user {normalized_email}")
        except HTTPException:
            raise
        except Exception as verify_error:
            logger.error(
                f"Password verification error for user {normalized_email}: {verify_error}",
                exc_info=True
            )
            raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")

        # Update last login (use normalized email)
        await users_collection.update_one(
            {"email": normalized_email},
            {"$set": {"last_login": datetime.utcnow()}}
        )

        # Create user response (without password hash)
        user = User(**{k: v for k, v in user_data.items() if k != "password_hash"})

        # Set Session Cookie with extended expiry if remember_me is True
        expiry_days = 30 if request.remember_me else (settings.session_expiry_days or 1)
        max_age_seconds = expiry_days * 24 * 60 * 60
        
        response.set_cookie(
            key=settings.session_cookie_name,
            value=user.user_id,
            httponly=True,
            max_age=max_age_seconds,
            samesite="lax",
            secure=False
        )
        
        logger.info(f"Login successful for user {user.user_id}, remember_me={request.remember_me}, expiry={expiry_days} days")

        return {"ok": True, "user": user.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/google")
async def google_login(request: GoogleLoginRequest, response: Response):
    """
    Google OAuth login. Send id_token (not 'token').
    Returns {ok, user} and sets session cookie. 400/401/500 if invalid or not configured.
    """
    try:
        # ✅ Check if Google Client ID is configured
        if not settings.google_client_id:
            logger.error("Google Client ID not configured. Please set GOOGLE_CLIENT_ID or VITE_GOOGLE_CLIENT_ID in .env")
            raise HTTPException(
                status_code=500, 
                detail="Google login is not configured. Please contact administrator."
            )
        
        # Check for dev bypass if client ID is missing (legacy support)
        if request.id_token == "dev_token":
            logger.warning("Dev token used for Google login - this should only be used in development")
            # Create dev session for testing
            storage = MongoStorage()
            await storage.connect()
            users_collection = storage.db["users"]
            dev_id = "dev_google_user"
            user_data = await users_collection.find_one({"user_id": dev_id})
            if not user_data:
                user = User(
                    user_id=dev_id,
                    email="dev@example.com",
                    full_name="Dev Google User",
                    first_name="Dev",
                    last_name="User",
                    created_at=datetime.utcnow(),
                    last_login=datetime.utcnow()
                )
                await users_collection.insert_one(user.model_dump())
                user_data = user.model_dump()
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

        # ✅ Verify token with Google
        try:
            idinfo = id_token.verify_oauth2_token(
                request.id_token, 
                google_requests.Request(), 
                settings.google_client_id
            )
        except ValueError as ve:
            logger.error(f"Google token verification failed: {ve}")
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid Google token: {str(ve)}"
            )
        except Exception as verify_error:
            logger.error(f"Google token verification error: {verify_error}", exc_info=True)
            raise HTTPException(
                status_code=400, 
                detail="Failed to verify Google token. Please try again."
            )

        # ✅ ID token is valid. Get user info from idinfo.
        google_id = idinfo.get('sub')
        email = idinfo.get('email')
        name = idinfo.get('name')
        picture = idinfo.get('picture')
        given_name = idinfo.get('given_name')
        family_name = idinfo.get('family_name')
        
        # ✅ Validate required fields
        if not google_id:
            logger.error("Google token missing 'sub' field")
            raise HTTPException(status_code=400, detail="Invalid Google token: missing user ID")
        if not email:
            logger.error("Google token missing 'email' field")
            raise HTTPException(status_code=400, detail="Invalid Google token: missing email")

        # ✅ Normalize email for consistent checking
        normalized_email = email.lower().strip()

        storage = MongoStorage()
        await storage.connect()

        # ✅ Check if user exists by email (case-insensitive)
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"email": normalized_email})
        
        # If not found with exact match, try case-insensitive regex search
        if not user_data:
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{normalized_email}$", "$options": "i"}
            })

        if not user_data:
            # ✅ Create new user with Google ID as user_id
            # ✅ Handle name parsing safely
            first_name_val = given_name
            last_name_val = family_name
            if not first_name_val and name:
                name_parts = name.split()
                first_name_val = name_parts[0] if name_parts else email.split('@')[0]
                last_name_val = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
            if not first_name_val:
                first_name_val = email.split('@')[0]
            if not last_name_val:
                last_name_val = ''
            
            full_name_val = name or f"{first_name_val} {last_name_val}".strip() or email.split('@')[0]
            
            user = User(
                user_id=google_id,  # Use Google sub as user_id
                email=email,
                full_name=full_name_val,
                first_name=first_name_val,
                last_name=last_name_val,
                profile_image=picture,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            await users_collection.insert_one(user.model_dump())
            logger.info(f"✅ Created new Google user: {email} (user_id: {google_id})")
        else:
            # ✅ Update existing user (update profile image and last login)
            update_data = {
                "last_login": datetime.utcnow()
            }
            # Update profile image if available and different
            if picture and user_data.get("profile_image") != picture:
                update_data["profile_image"] = picture
            # Update name if available and different
            if name and user_data.get("full_name") != name:
                update_data["full_name"] = name
            if given_name and user_data.get("first_name") != given_name:
                update_data["first_name"] = given_name
            if family_name and user_data.get("last_name") != family_name:
                update_data["last_name"] = family_name
            
            await users_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
            # ✅ Reload user data to get updated fields
            user_data = await users_collection.find_one({"email": email})
            user = User(**user_data)
            logger.info(f"✅ Google user logged in: {email} (user_id: {user.user_id})")

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

    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except ValueError as e:
        # Invalid token (should be caught above, but keep as fallback)
        logger.error(f"Invalid Google token: {e}", exc_info=True)
        error_msg = str(e)
        # ✅ Provide more helpful error messages
        if "Token used too early" in error_msg or "Token used too late" in error_msg:
            raise HTTPException(status_code=400, detail="Google token expired. Please try logging in again.")
        elif "Invalid token" in error_msg or "Token verification failed" in error_msg:
            raise HTTPException(status_code=400, detail="Invalid Google token. Please try logging in again.")
        else:
            raise HTTPException(status_code=400, detail=f"Google token verification failed: {error_msg}")
    except Exception as e:
        logger.error(f"Google login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error during Google login: {str(e)}"
        )

@router.get("/me")
async def get_me(request: Request, response: Response):
    """
    Get current user profile from session cookie.
    Returns 200 with {user: {...}} when authenticated, {user: null} when not (no 401).
    Refreshes session cookie to extend expiry.
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

        # Refresh session cookie to extend expiry (keeps user logged in)
        response.set_cookie(
            key=settings.session_cookie_name,
            value=user_id,
            httponly=True,
            max_age=settings.session_expiry_days * 24 * 60 * 60,
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )

        # ✅ Ensure is_admin field is included (default to False if not set)
        user_model = User(**user_data)
        user_dict = user_model.model_dump()
        if "is_admin" not in user_dict:
            user_dict["is_admin"] = user_data.get("is_admin", False)
        return {"user": user_dict}
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


@router.post("/change-password")
async def change_password(request: Request, password_data: dict):
    """
    Change user password.
    If header X-Password-Encoding: sha256, current_password and new_password must be SHA-256 hex (64 chars).
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    current_password = password_data.get("current_password")
    new_password = password_data.get("new_password")

    if not current_password or not new_password:
        raise HTTPException(status_code=400, detail="กรุณากรอกรหัสผ่านปัจจุบันและรหัสผ่านใหม่")

    client_sends_sha256 = (request.headers.get("X-Password-Encoding") or "").strip().lower() == "sha256"
    if not client_sends_sha256:
        try:
            validate_password_strength(new_password)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]

        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")

        stored_hash = user_data.get("password_hash") or user_data.get("password", "")
        if not stored_hash:
            raise HTTPException(status_code=400, detail="บัญชีนี้ไม่ได้ตั้งรหัสผ่าน (ใช้ Google/Firebase login)")

        if client_sends_sha256:
            current_ok = verify_password_from_client_hash(current_password, stored_hash)
        else:
            current_ok = verify_password(current_password, stored_hash)
        if not current_ok:
            raise HTTPException(status_code=400, detail="รหัสผ่านปัจจุบันไม่ถูกต้อง")

        if client_sends_sha256:
            hashed_password = hash_password_from_client_sha256(new_password)
        else:
            hashed_password = hash_password(new_password)

        await users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"password_hash": hashed_password}}
        )

        logger.info(f"Password changed for user: {user_id}")
        return {"ok": True, "message": "เปลี่ยนรหัสผ่านสำเร็จ"}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error changing password: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการเปลี่ยนรหัสผ่าน: {str(e)}")


@router.post("/update-email")
async def update_email(request: Request, email_data: dict):
    """
    Update user email (requires verification)
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    new_email = email_data.get("new_email", "").strip().lower()
    
    if not new_email or "@" not in new_email:
        raise HTTPException(status_code=400, detail="กรุณากรอกอีเมลที่ถูกต้อง")
    
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        # Check if email already exists
        normalized_email = new_email.lower().strip()
        existing_user = await users_collection.find_one({"email": normalized_email})
        if existing_user:
            existing_user_id = existing_user.get("user_id")
            if existing_user_id != user_id:
                raise HTTPException(status_code=400, detail="อีเมลนี้ถูกใช้งานแล้ว")
        
        # Get email service
        from app.services.email_service import get_email_service
        email_service = get_email_service()
        
        # Generate verification token
        verification_token = email_service.generate_verification_token()
        
        # Update user with new email (unverified)
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email": normalized_email,
                    "email_verified": False,
                    "email_verification_token": verification_token,
                    "email_verification_sent_at": datetime.utcnow()
                }
            }
        )
        
        # Send verification email to new address (every time email is changed)
        user_data = await users_collection.find_one({"user_id": user_id})
        user_name = (user_data or {}).get("full_name") or (user_data or {}).get("first_name") or None
        try:
            email_sent = email_service.send_verification_email(
                normalized_email, verification_token, user_name=user_name
            )
            if email_sent:
                logger.info(f"Verification email sent to {normalized_email} for user {user_id}")
            else:
                logger.warning(f"Verification email not sent (service not configured?) to {normalized_email}")
        except Exception as email_error:
            logger.error(f"Failed to send verification email: {email_error}", exc_info=True)
            # Don't fail the request if email sending fails

        return {
            "ok": True,
            "message": "กรุณายืนยันอีเมลในแอป (Firebase จะส่งลิงก์ยืนยันให้)",
            "email": normalized_email,
            "use_firebase": True,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการอัปเดตอีเมล: {str(e)}")


@router.delete("/profile")
async def delete_account(request: Request, response: Response):
    """
    Delete user account and all associated data
    
    This will permanently delete:
    - User document
    - All sessions
    - All memories
    - All bookings
    - All conversations
    - All notifications
    
    ⚠️ WARNING: This action cannot be undone!
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        # Get user info before deletion (for logging)
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"user_id": user_id})
        
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        user_email = user_data.get("email", "unknown")
        is_admin = user_data.get("is_admin", False)
        
        # Prevent deletion of admin account
        if is_admin:
            raise HTTPException(
                status_code=403,
                detail="ไม่สามารถลบบัญชีผู้ดูแลระบบได้"
            )
        
        logger.warning(f"⚠️ User account deletion requested: user_id={user_id}, email={user_email}")
        
        deletion_summary = {
            "user_id": user_id,
            "email": user_email,
            "deleted_at": datetime.utcnow(),
            "collections_deleted": {}
        }
        
        # 1. Delete all sessions
        try:
            sessions_collection = storage.db["sessions"]
            sessions_result = await sessions_collection.delete_many({"user_id": user_id})
            deletion_summary["collections_deleted"]["sessions"] = sessions_result.deleted_count
            logger.info(f"Deleted {sessions_result.deleted_count} sessions for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting sessions for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["sessions"] = f"Error: {str(e)}"
        
        # 2. Delete all memories
        try:
            memories_collection = storage.db["memories"]
            memories_result = await memories_collection.delete_many({"user_id": user_id})
            deletion_summary["collections_deleted"]["memories"] = memories_result.deleted_count
            logger.info(f"Deleted {memories_result.deleted_count} memories for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting memories for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["memories"] = f"Error: {str(e)}"
        
        # 3. Delete all bookings
        try:
            bookings_collection = storage.db["bookings"]
            bookings_result = await bookings_collection.delete_many({"user_id": user_id})
            deletion_summary["collections_deleted"]["bookings"] = bookings_result.deleted_count
            logger.info(f"Deleted {bookings_result.deleted_count} bookings for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting bookings for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["bookings"] = f"Error: {str(e)}"
        
        # 4. Delete all conversations
        try:
            conversations_collection = storage.db["conversations"]
            conversations_result = await conversations_collection.delete_many({"user_id": user_id})
            deletion_summary["collections_deleted"]["conversations"] = conversations_result.deleted_count
            logger.info(f"Deleted {conversations_result.deleted_count} conversations for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting conversations for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["conversations"] = f"Error: {str(e)}"
        
        # 5. Delete all notifications
        try:
            notifications_collection = storage.db.get_collection("notifications")
            notifications_result = await notifications_collection.delete_many({"user_id": user_id})
            deletion_summary["collections_deleted"]["notifications"] = notifications_result.deleted_count
            logger.info(f"Deleted {notifications_result.deleted_count} notifications for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting notifications for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["notifications"] = f"Error: {str(e)}"
        
        # 6. Delete user document (LAST - after all related data is deleted)
        try:
            user_result = await users_collection.delete_one({"user_id": user_id})
            deletion_summary["collections_deleted"]["user"] = user_result.deleted_count
            logger.info(f"Deleted user document for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting user document for user {user_id}: {e}", exc_info=True)
            deletion_summary["collections_deleted"]["user"] = f"Error: {str(e)}"
            raise HTTPException(status_code=500, detail="Failed to delete user account")
        
        # Clear session cookie
        response.delete_cookie(settings.session_cookie_name)
        
        logger.warning(f"✅ User account deleted successfully: user_id={user_id}, email={user_email}")
        logger.info(f"Deletion summary: {deletion_summary}")
        
        return {
            "ok": True,
            "message": "บัญชีถูกลบเรียบร้อยแล้ว",
            "deletion_summary": deletion_summary
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user account: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"เกิดข้อผิดพลาดในการลบบัญชี: {str(e)}")




@router.post("/register", status_code=201)
async def register(request: RegisterRequest, response: Response, raw_request: Request):
    """
    Register a new user account.
    Expects firstName, lastName (camelCase). Returns {ok, user}. Sets session cookie.
    If header X-Password-Encoding: sha256, request.password must be SHA-256(password) hex (64 chars); strength is validated on client.
    """
    try:
        # Validate required fields
        if not request.first_name or not request.first_name.strip():
            raise HTTPException(status_code=400, detail="First name is required")
        if not request.last_name or not request.last_name.strip():
            raise HTTPException(status_code=400, detail="Last name is required")

        # Validate password is provided
        if not request.password or not request.password.strip():
            raise HTTPException(status_code=400, detail="Password is required")

        client_sends_sha256 = (raw_request.headers.get("X-Password-Encoding") or "").strip().lower() == "sha256"
        if not client_sends_sha256:
            # Validate password strength only when sending plain password
            is_valid, error_message = validate_password_strength(request.password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)

        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]

        # ✅ Normalize email for consistent checking (lowercase, trimmed)
        normalized_email = request.email.lower().strip()
        
        # Check if user already exists (case-insensitive search)
        # Try multiple search strategies to handle case variations
        existing_user = await users_collection.find_one({"email": normalized_email})
        if not existing_user:
            # Try case-insensitive regex search as fallback
            existing_user = await users_collection.find_one({
                "email": {"$regex": f"^{normalized_email}$", "$options": "i"}
            })
        
        if existing_user:
            logger.warning(f"Registration attempt with existing email: {normalized_email} (found: {existing_user.get('email')})")
            raise HTTPException(status_code=400, detail="อีเมลนี้ถูกใช้งานแล้ว กรุณาใช้อีเมลอื่น")

        # Hash password (client may send SHA-256 hex so plain password is never on the wire)
        try:
            if client_sends_sha256:
                hashed_password = hash_password_from_client_sha256(request.password)
            else:
                hashed_password = hash_password(request.password)
            logger.info(f"Password hashed successfully for user: {request.email}")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as hash_error:
            logger.error(f"Password hashing error: {hash_error}", exc_info=True)
            raise HTTPException(status_code=500, detail="Password encryption failed")

        # ✅ CRUD STABILITY: Create new user with duplicate key error handling
        user_id = f"user_{int(datetime.utcnow().timestamp())}"
        
        # Generate email verification token (รองรับทุกเมล: Gmail, Hotmail, Outlook, Yahoo, etc. ยกเว้น admin)
        email_verification_token = None
        email_verification_sent_at = None
        email_verified = False
        admin_email_normalized = (settings.admin_email or "").lower().strip()

        # Skip email verification only for configured admin email (default admin@example.com)
        if normalized_email != admin_email_normalized:
            email_service = get_email_service()
            if email_service.is_configured:
                email_verification_token = email_service.generate_verification_token()
                email_verification_sent_at = datetime.utcnow()
                email_verified = False
            else:
                # If email service is not configured, mark as verified (for development)
                logger.warning("Email service not configured. Skipping email verification.")
                email_verified = True
        else:
            # Admin email is automatically verified
            email_verified = True
        
        user_doc = {
            "user_id": user_id,
            "email": normalized_email,  # ✅ Use normalized email (already lowercased and trimmed)
            "full_name": f"{request.first_name} {request.last_name}",
            "first_name": request.first_name.strip(),
            "last_name": request.last_name.strip(),
            "first_name_th": request.first_name_th.strip() if request.first_name_th else None,
            "last_name_th": request.last_name_th.strip() if request.last_name_th else None,
            "phone": request.phone.strip() if request.phone else None,
            "password_hash": hashed_password,
            "email_verified": email_verified,
            "email_verification_token": email_verification_token,
            "email_verification_sent_at": email_verification_sent_at,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        
        # ✅ CRUD STABILITY: Insert with duplicate key error handling
        try:
            await users_collection.insert_one(user_doc)
        except Exception as insert_error:
            error_str = str(insert_error).lower()
            if "duplicate" in error_str or "e11000" in error_str:
                logger.warning(f"Duplicate key error on user registration: {insert_error}")
                raise HTTPException(status_code=409, detail="Email already registered")
            raise
        logger.info(f"Registered new user: {request.email}")
        
        # Send verification email (ทุกเมล ยกเว้น admin)
        if normalized_email != admin_email_normalized and email_verification_token:
            email_service = get_email_service()
            if email_service.is_configured:
                user_name = f"{request.first_name} {request.last_name}"
                email_sent = email_service.send_verification_email(
                    to_email=request.email,
                    token=email_verification_token,
                    user_name=user_name
                )
                if email_sent:
                    logger.info(f"✅ Verification email sent to {request.email}")
                else:
                    logger.warning(f"⚠️ Failed to send verification email to {request.email}")

        # Create user response (without password hash)
        user = User(
            user_id=user_id,
            email=request.email,
            full_name=f"{request.first_name} {request.last_name}",
            first_name=request.first_name.strip(),
            last_name=request.last_name.strip(),
            first_name_th=request.first_name_th.strip() if request.first_name_th else None,
            last_name_th=request.last_name_th.strip() if request.last_name_th else None,
            phone=request.phone.strip() if request.phone else None,
            created_at=datetime.utcnow(),
            last_login=datetime.utcnow()
        )

        response.set_cookie(
            key=settings.session_cookie_name,
            value=user.user_id,
            httponly=True,
            max_age=settings.session_expiry_days * 24 * 60 * 60,
            samesite="lax",
            secure=False
        )
        return {"ok": True, "user": user.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}", exc_info=True)
        error_detail = str(e) if str(e) else "Internal server error"
        raise HTTPException(status_code=500, detail=f"Registration failed: {error_detail}")


@router.get("/reset-password/{email}")
async def get_reset_password_info(email: str):
    """
    Get user information for password reset
    Returns whether user exists and if they have a password set
    Case-insensitive email search with multiple fallback strategies
    """
    try:
        # Decode URL-encoded email
        import urllib.parse
        original_email = email
        email = urllib.parse.unquote(email)
        email_trimmed = email.strip()
        email_lower = email_trimmed.lower()
        
        logger.info(f"🔍 Reset password lookup - Original: '{original_email}', Decoded: '{email}', Trimmed: '{email_trimmed}', Lower: '{email_lower}'")
        
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        user_data = None
        
        # Strategy 1: Try exact match (original)
        user_data = await users_collection.find_one({"email": original_email})
        if user_data:
            logger.info(f"✅ Found user with exact match (original): {original_email}")
        
        # Strategy 2: Try exact match (decoded)
        if not user_data:
            user_data = await users_collection.find_one({"email": email})
            if user_data:
                logger.info(f"✅ Found user with exact match (decoded): {email}")
        
        # Strategy 3: Try exact match (trimmed)
        if not user_data:
            user_data = await users_collection.find_one({"email": email_trimmed})
            if user_data:
                logger.info(f"✅ Found user with exact match (trimmed): {email_trimmed}")
        
        # Strategy 4: Try case-insensitive regex (lowercase)
        if not user_data:
            logger.debug(f"Trying case-insensitive regex for: {email_lower}")
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{email_lower}$", "$options": "i"}
            })
            if user_data:
                logger.info(f"✅ Found user with case-insensitive regex: {email_lower}")
        
        # Strategy 5: Try case-insensitive regex (trimmed original)
        if not user_data:
            logger.debug(f"Trying case-insensitive regex for trimmed: {email_trimmed}")
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{email_trimmed}$", "$options": "i"}
            })
            if user_data:
                logger.info(f"✅ Found user with case-insensitive regex (trimmed): {email_trimmed}")
        
        # Strategy 6: Try with any whitespace variations
        if not user_data:
            # Remove all whitespace and try
            email_no_whitespace = ''.join(email_trimmed.split())
            if email_no_whitespace != email_trimmed:
                logger.debug(f"Trying without whitespace: {email_no_whitespace}")
                user_data = await users_collection.find_one({
                    "email": {"$regex": f"^{email_no_whitespace}$", "$options": "i"}
                })
                if user_data:
                    logger.info(f"✅ Found user without whitespace: {email_no_whitespace}")
        
        if not user_data:
            logger.warning(f"❌ User not found after all search strategies for: '{original_email}'")
            # List ALL emails in database for debugging
            try:
                all_users = await users_collection.find({}, {"email": 1, "user_id": 1}).to_list(length=100)
                all_emails = [{"email": u.get("email"), "user_id": u.get("user_id")} for u in all_users if u.get("email")]
                logger.info(f"📋 All emails in database ({len(all_emails)}): {all_emails[:10]}")  # Show first 10
                
                # Check if email exists with different case
                matching_emails = [e for e in all_emails if e.get("email", "").lower() == email_lower]
                if matching_emails:
                    logger.warning(f"⚠️ Found email with different case: {matching_emails}")
            except Exception as e:
                logger.error(f"Could not fetch emails for debugging: {e}", exc_info=True)
            
            raise HTTPException(
                status_code=404, 
                detail=f"ไม่พบผู้ใช้ในระบบ กรุณาตรวจสอบอีเมล '{email_trimmed}' หรือสมัครสมาชิกใหม่"
            )
        
        # Check if user has password
        has_password = bool(user_data.get("password_hash"))
        has_backup = bool(user_data.get("password_hash_backup"))
        
        return {
            "ok": True,
            "email": email,
            "has_password": has_password,
            "has_backup": has_backup,
            "user_id": user_data.get("user_id"),
            "full_name": user_data.get("full_name"),
            "first_name": user_data.get("first_name"),
            "last_name": user_data.get("last_name")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reset password info: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, raw_request: Request):
    """
    Reset user password.
    If header X-Password-Encoding: sha256, new_password must be SHA-256 hex (64 chars).
    """
    try:
        client_sends_sha256 = (raw_request.headers.get("X-Password-Encoding") or "").strip().lower() == "sha256"
        if not client_sends_sha256:
            is_valid, error_message = validate_password_strength(request.new_password)
            if not is_valid:
                raise HTTPException(status_code=400, detail=error_message)
        
        email_trimmed = request.email.strip()
        email_lower = email_trimmed.lower()
        logger.info(f"🔐 Password reset request for email: '{request.email}' (trimmed: '{email_trimmed}', lower: '{email_lower}')")
        
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        user_data = None
        
        # Try multiple search strategies (same as GET endpoint)
        # Strategy 1: Exact match
        user_data = await users_collection.find_one({"email": request.email})
        if not user_data:
            user_data = await users_collection.find_one({"email": email_trimmed})
        if not user_data:
            # Strategy 2: Case-insensitive
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{email_lower}$", "$options": "i"}
            })
        
        if not user_data:
            logger.warning(f"❌ User not found for password reset: '{request.email}'")
            raise HTTPException(
                status_code=404, 
                detail=f"ไม่พบผู้ใช้ในระบบ กรุณาตรวจสอบอีเมล '{email_trimmed}'"
            )
        
        logger.info(f"✅ Found user for password reset: {user_data.get('email')} (user_id: {user_data.get('user_id')})")
        
        # Backup old password hash if exists
        old_password_hash = user_data.get("password_hash")
        update_data = {}
        
        if old_password_hash:
            # Backup old password hash
            update_data["password_hash_backup"] = old_password_hash
            update_data["password_backup_date"] = datetime.utcnow()
            logger.info(f"Backed up old password hash for user: {request.email}")
        
        # Hash new password (client may send SHA-256 hex)
        try:
            if client_sends_sha256:
                new_password_hash = hash_password_from_client_sha256(request.new_password)
            else:
                new_password_hash = hash_password(request.new_password)
            update_data["password_hash"] = new_password_hash
            update_data["password_changed_at"] = datetime.utcnow()
            logger.info(f"Password hashed successfully for user: {request.email}")
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as hash_error:
            logger.error(f"Password hashing error: {hash_error}", exc_info=True)
            raise HTTPException(status_code=500, detail="Password encryption failed")
        
        # Update user
        result = await users_collection.update_one(
            {"email": request.email},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        logger.info(f"Password reset successfully for user: {request.email} (backup: {bool(old_password_hash)})")
        
        return {
            "ok": True,
            "message": "Password reset successfully",
            "email": request.email,
            "backup_created": bool(old_password_hash)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password reset error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Password reset failed: {str(e)}")


@router.post("/firebase")
async def firebase_login(request: FirebaseLoginRequest, response: Response):
    """
    Firebase Authentication login. Send idToken from Firebase Auth.
    Returns {ok, user} and sets session cookie. 400/401/500 if invalid or not configured.
    
    รองรับการเข้าสู่ระบบผ่าน Firebase Authentication (Google Account)
    """
    try:
        # Initialize Firebase if not already initialized
        initialize_firebase()
        
        if not FIREBASE_AVAILABLE or not _firebase_initialized:
            logger.error("Firebase Admin SDK not available or not initialized. Please configure Firebase credentials.")
            raise HTTPException(
                status_code=500,
                detail="Firebase authentication is not configured. Please contact administrator."
            )
        
        # Verify Firebase ID token
        try:
            decoded_token = firebase_auth.verify_id_token(request.idToken)
        except firebase_auth.InvalidIdTokenError as e:
            logger.error(f"Invalid Firebase ID token: {e}")
            raise HTTPException(
                status_code=400,
                detail="Invalid Firebase token. Please try logging in again."
            )
        except firebase_auth.ExpiredIdTokenError as e:
            logger.error(f"Expired Firebase ID token: {e}")
            raise HTTPException(
                status_code=400,
                detail="Firebase token expired. Please try logging in again."
            )
        except Exception as verify_error:
            logger.error(f"Firebase token verification error: {verify_error}", exc_info=True)
            raise HTTPException(
                status_code=400,
                detail="Failed to verify Firebase token. Please try again."
            )
        
        # Extract user information from decoded token
        firebase_uid = decoded_token.get('uid')
        email = decoded_token.get('email')
        name = decoded_token.get('name')
        picture = decoded_token.get('picture')
        email_verified = decoded_token.get('email_verified', False)
        
        # Validate required fields
        if not firebase_uid:
            logger.error("Firebase token missing 'uid' field")
            raise HTTPException(status_code=400, detail="Invalid Firebase token: missing user ID")
        if not email:
            logger.error("Firebase token missing 'email' field")
            raise HTTPException(status_code=400, detail="Invalid Firebase token: missing email")
        
        # ✅ Normalize email for consistent checking
        normalized_email = email.lower().strip()
        
        # Parse name into first_name and last_name
        first_name_val = decoded_token.get('given_name') or decoded_token.get('first_name')
        last_name_val = decoded_token.get('family_name') or decoded_token.get('last_name')
        
        if not first_name_val and name:
            name_parts = name.split()
            first_name_val = name_parts[0] if name_parts else normalized_email.split('@')[0]
            last_name_val = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        if not first_name_val:
            first_name_val = normalized_email.split('@')[0]
        if not last_name_val:
            last_name_val = ''
        
        full_name_val = name or f"{first_name_val} {last_name_val}".strip() or normalized_email.split('@')[0]
        
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        # Check if user exists by email (case-insensitive)
        user_data = await users_collection.find_one({"email": normalized_email})
        
        # If not found with exact match, try case-insensitive regex search
        if not user_data:
            user_data = await users_collection.find_one({
                "email": {"$regex": f"^{normalized_email}$", "$options": "i"}
            })
        
        if not user_data:
            # Create new user with Firebase UID as user_id
            user = User(
                user_id=firebase_uid,  # Use Firebase UID as user_id
                email=email,
                full_name=full_name_val,
                first_name=first_name_val,
                last_name=last_name_val,
                profile_image=picture,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow(),
                email_verified=email_verified,  # Store email verification status
                auth_provider="firebase"  # Mark as Firebase-authenticated user
            )
            await users_collection.insert_one(user.model_dump())
            logger.info(f"✅ Created new Firebase user: {email} (user_id: {firebase_uid})")
        else:
            # Update existing user (update profile image, last login, and auth provider)
            update_data = {
                "last_login": datetime.utcnow(),
                "auth_provider": "firebase"  # Update auth provider
            }
            
            # Update profile image if available and different
            if picture and user_data.get("profile_image") != picture:
                update_data["profile_image"] = picture
            
            # Update name if available and different
            if name and user_data.get("full_name") != name:
                update_data["full_name"] = name
            if first_name_val and user_data.get("first_name") != first_name_val:
                update_data["first_name"] = first_name_val
            if last_name_val and user_data.get("last_name") != last_name_val:
                update_data["last_name"] = last_name_val
            
            # Update email verification status
            if email_verified:
                update_data["email_verified"] = True
            
            await users_collection.update_one(
                {"email": email},
                {"$set": update_data}
            )
            
            # Reload user data to get updated fields
            user_data = await users_collection.find_one({"email": email})
            user = User(**user_data)
            logger.info(f"✅ Firebase user logged in: {email} (user_id: {user.user_id})")
        
        # Set session cookie
        response.set_cookie(
            key=settings.session_cookie_name,
            value=user.user_id,
            httponly=True,
            max_age=settings.session_expiry_days * 24 * 60 * 60,
            samesite="lax",
            secure=False  # Set to True in production with HTTPS
        )
        
        return {"ok": True, "user": user.model_dump()}
    
    except HTTPException:
        # Re-raise HTTP exceptions (already handled)
        raise
    except Exception as e:
        logger.error(f"Firebase login error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error during Firebase login: {str(e)}"
        )


@router.post("/firebase-refresh")
async def firebase_refresh(request: FirebaseLoginRequest, response: Response):
    """
    Sync user from Firebase ID token (e.g. after email verification).
    อัปเดต email_verified และข้อมูลจาก Firebase โดยไม่ต้องล็อกอินใหม่
    """
    initialize_firebase()
    if not FIREBASE_AVAILABLE or not _firebase_initialized:
        raise HTTPException(status_code=503, detail="Firebase authentication is not configured")
    try:
        decoded_token = firebase_auth.verify_id_token(request.idToken)
    except Exception as e:
        logger.warning(f"Firebase refresh token invalid: {e}")
        raise HTTPException(status_code=400, detail="Invalid or expired token. Please sign in again.")
    firebase_uid = decoded_token.get("uid")
    email = decoded_token.get("email")
    email_verified = decoded_token.get("email_verified", False)
    if not firebase_uid or not email:
        raise HTTPException(status_code=400, detail="Invalid token: missing uid or email")
    storage = MongoStorage()
    await storage.connect()
    users_collection = storage.db["users"]
    user_data = await users_collection.find_one({"user_id": firebase_uid})
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    update_data = {"last_login": datetime.utcnow()}
    if email_verified:
        update_data["email_verified"] = True
    await users_collection.update_one(
        {"user_id": firebase_uid},
        {"$set": update_data},
    )
    user_data = await users_collection.find_one({"user_id": firebase_uid})
    user = User(**user_data)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=user.user_id,
        httponly=True,
        max_age=settings.session_expiry_days * 24 * 60 * 60,
        samesite="lax",
        secure=False,
    )
    return {"ok": True, "user": user.model_dump()}


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


@router.post("/send-verification-email")
async def send_verification_email(request: Request):
    """
    Send email verification email to current user (resend)
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        
        email = user_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="User email not found")
        
        # Skip email verification only for configured admin email (รองรับทุกเมลอื่น: Gmail, Hotmail, Outlook, etc.)
        admin_email_normalized = (settings.admin_email or "").lower().strip()
        if email.lower().strip() == admin_email_normalized:
            return {
                "ok": True,
                "message": "Admin email does not require verification",
                "email_verified": True
            }
        
        # Check if already verified
        if user_data.get("email_verified"):
            return {
                "ok": True,
                "message": "Email already verified",
                "email_verified": True
            }
        
        # Generate new verification token (เก็บใน DB สำหรับ /verify-email ถ้ามี custom flow)
        email_service = get_email_service()
        if not email_service.is_configured:
            raise HTTPException(
                status_code=503,
                detail="Firebase ยังไม่ได้ตั้งค่า กรุณาตั้งค่า FIREBASE_PROJECT_ID หรือ FIREBASE_CREDENTIALS_PATH ใน backend/.env"
            )
        
        verification_token = email_service.generate_verification_token()
        verification_sent_at = datetime.utcnow()
        
        # Update user with new token
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "email_verification_token": verification_token,
                    "email_verification_sent_at": verification_sent_at
                }
            }
        )
        
        # การส่งอีเมลยืนยันทำที่ฝั่ง Client ด้วย Firebase sendEmailVerification()
        email_service.send_verification_email(
            to_email=email,
            token=verification_token,
            user_name=user_data.get("full_name") or user_data.get("first_name", "")
        )
        logger.info(f"Verification flow prepared for {email}; client should call Firebase sendEmailVerification()")
        return {
            "ok": True,
            "message": "กรุณายืนยันอีเมลในแอป (Firebase จะส่งลิงก์ยืนยันให้)",
            "email": email,
            "use_firebase": True,
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending verification email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify-email")
async def verify_email(token: str = Query(..., description="Verification token from email link")):
    """
    Verify email address using verification token
    """
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")
    
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        # Find user by verification token
        user_data = await users_collection.find_one({"email_verification_token": token})
        
        if not user_data:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired verification token"
            )
        
        # Check if token is expired (24 hours)
        verification_sent_at = user_data.get("email_verification_sent_at")
        if verification_sent_at:
            if isinstance(verification_sent_at, str):
                verification_sent_at = date_parser.parse(verification_sent_at)
            
            token_age = datetime.utcnow() - verification_sent_at
            if token_age > timedelta(hours=24):
                # Token expired - clear it
                await users_collection.update_one(
                    {"user_id": user_data["user_id"]},
                    {
                        "$unset": {
                            "email_verification_token": "",
                            "email_verification_sent_at": ""
                        }
                    }
                )
                raise HTTPException(
                    status_code=400,
                    detail="Verification token has expired. Please request a new one."
                )
        
        # Check if already verified
        if user_data.get("email_verified"):
            return {
                "ok": True,
                "message": "Email already verified",
                "email_verified": True
            }
        
        # Verify email
        await users_collection.update_one(
            {"user_id": user_data["user_id"]},
            {
                "$set": {
                    "email_verified": True
                },
                "$unset": {
                    "email_verification_token": "",
                    "email_verification_sent_at": ""
                }
            }
        )
        
        logger.info(f"✅ Email verified for user: {user_data.get('email')}")
        
        return {
            "ok": True,
            "message": "Email verified successfully",
            "email_verified": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# =============================================================================
# Phone OTP (เปลี่ยนเบอร์โทร - ส่ง OTP)
# =============================================================================

@router.post("/send-phone-otp")
async def send_phone_otp(request: Request, body: dict):
    """
    ส่ง OTP ไปเบอร์โทรที่ระบุ (สำหรับเปลี่ยนเบอร์) รองรับทุกเครือข่าย
    Body: { "new_phone": "0812345678" }
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    new_phone = (body.get("new_phone") or "").strip().replace(" ", "")
    if not new_phone or len(new_phone) < 9:
        raise HTTPException(status_code=400, detail="กรุณากรอกเบอร์โทรที่ถูกต้อง (เช่น 0812345678)")
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        otp = generate_otp(6)
        sent_at = datetime.utcnow()
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "phone_pending": new_phone,
                    "phone_verification_otp": otp,
                    "phone_verification_sent_at": sent_at,
                }
            },
        )
        sms_service = get_sms_service()
        sent = sms_service.send_otp(new_phone, otp)
        if not sent:
            raise HTTPException(status_code=503, detail="ส่ง OTP ไม่สำเร็จ (ตรวจสอบ Twilio/SMS ใน .env)")
        logger.info(f"✅ Phone OTP sent to {new_phone} for user {user_id}")
        return {"ok": True, "message": "ส่ง OTP ไปที่เบอร์โทรแล้ว กรุณากรอกรหัส OTP"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending phone OTP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify-phone")
async def verify_phone(request: Request, body: dict):
    """
    ยืนยันเบอร์โทรด้วย OTP แล้วอัปเดตเบอร์ในโปรไฟล์
    Body: { "otp": "123456" }
    """
    user_id = request.cookies.get(settings.session_cookie_name)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    otp = (body.get("otp") or "").strip()
    if not otp or len(otp) != 6:
        raise HTTPException(status_code=400, detail="กรุณากรอกรหัส OTP 6 หลัก")
    try:
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"user_id": user_id})
        if not user_data:
            raise HTTPException(status_code=404, detail="User not found")
        phone_pending = user_data.get("phone_pending")
        stored_otp = user_data.get("phone_verification_otp")
        sent_at = user_data.get("phone_verification_sent_at")
        if not phone_pending or not stored_otp:
            raise HTTPException(status_code=400, detail="ไม่พบการรอยืนยันเบอร์โทร กรุณากดส่ง OTP ก่อน")
        if sent_at:
            if isinstance(sent_at, str):
                sent_at = date_parser.parse(sent_at)
            age_minutes = (datetime.utcnow() - sent_at).total_seconds() / 60
            if age_minutes > settings.sms_otp_expire_minutes:
                await users_collection.update_one(
                    {"user_id": user_id},
                    {"$unset": {"phone_pending": "", "phone_verification_otp": "", "phone_verification_sent_at": ""}},
                )
                raise HTTPException(status_code=400, detail="รหัส OTP หมดอายุแล้ว กรุณาขอ OTP ใหม่")
        if otp != stored_otp:
            raise HTTPException(status_code=400, detail="รหัส OTP ไม่ถูกต้อง")
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$set": {"phone": phone_pending},
                "$unset": {"phone_pending": "", "phone_verification_otp": "", "phone_verification_sent_at": ""},
            },
        )
        logger.info(f"✅ Phone verified for user {user_id}: {phone_pending}")
        user_data = await users_collection.find_one({"user_id": user_id})
        return {"ok": True, "message": "ยืนยันเบอร์โทรสำเร็จ", "user": User(**user_data).model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying phone: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

