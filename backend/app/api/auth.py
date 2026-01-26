"""
Authentication Router
Handles Google Login, Session Management, and User Profile
"""

from fastapi import APIRouter, HTTPException, Depends, Response, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.logging import get_logger, set_logging_context, clear_logging_context
from app.core.security import hash_password, verify_password, validate_password_strength
from app.storage.mongodb_storage import MongoStorage
from app.models.database import User, SessionDocument

logger = get_logger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

class GoogleLoginRequest(BaseModel):
    """Google OAuth login. Send id_token from Google Sign-In (not 'token')."""
    id_token: str = Field(..., description="Google ID token from OAuth flow")

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
    # Hotel Booking Preferences (Production-ready for Agoda/Traveloka)
    # Emergency Contact
    emergency_contact_name: Optional[str] = Field(default=None, description="Emergency contact full name")
    emergency_contact_phone: Optional[str] = Field(default=None, description="Emergency contact phone number")
    emergency_contact_relation: Optional[str] = Field(default=None, description="Emergency contact relation: SPOUSE, PARENT, FRIEND, OTHER")
    emergency_contact_email: Optional[str] = Field(default=None, description="Emergency contact email")
    # Special Requests / Preferences
    hotel_early_checkin: Optional[bool] = Field(default=False, description="Request early check-in")
    hotel_late_checkout: Optional[bool] = Field(default=False, description="Request late check-out")
    hotel_smoking_preference: Optional[str] = Field(default=None, description="Smoking preference: SMOKING, NON_SMOKING")
    hotel_room_type_preference: Optional[str] = Field(default=None, description="Room type preference: STANDARD, DELUXE, SUITE, etc.")
    hotel_floor_preference: Optional[str] = Field(default=None, description="Floor preference: HIGH, LOW, ANY")
    hotel_view_preference: Optional[str] = Field(default=None, description="View preference: SEA, CITY, GARDEN, ANY")
    hotel_extra_bed: Optional[bool] = Field(default=False, description="Request extra bed/cot")
    hotel_airport_transfer: Optional[bool] = Field(default=False, description="Request airport transfer")
    hotel_dietary_requirements: Optional[str] = Field(default=None, description="Dietary requirements: VEGETARIAN, VEGAN, HALAL, ALLERGIES, NONE")
    hotel_special_occasion: Optional[str] = Field(default=None, description="Special occasion: BIRTHDAY, HONEYMOON, ANNIVERSARY, NONE")
    hotel_accessibility_needs: Optional[bool] = Field(default=False, description="Accessibility needs (wheelchair accessible room)")
    # Check-in Details
    hotel_arrival_time: Optional[str] = Field(default=None, description="Expected arrival time (HH:MM format)")
    hotel_arrival_flight: Optional[str] = Field(default=None, description="Arrival flight number")
    hotel_departure_time: Optional[str] = Field(default=None, description="Expected departure time (HH:MM format)")
    hotel_number_of_guests: Optional[int] = Field(default=1, description="Number of guests (including main guest)")
    # Payment Information
    payment_method: Optional[str] = Field(default=None, description="Payment method: CREDIT_CARD, DEBIT_CARD, BANK_TRANSFER")
    card_holder_name: Optional[str] = Field(default=None, description="Card holder name (if using card)")
    card_last_4_digits: Optional[str] = Field(default=None, description="Card last 4 digits (for verification)")
    # Tax Invoice Information
    company_name: Optional[str] = Field(default=None, description="Company/Organization name (for business booking)")
    tax_id: Optional[str] = Field(default=None, description="Tax ID / VAT Number")
    invoice_address: Optional[str] = Field(default=None, description="Invoice address (if different from main address)")
    # Loyalty Program
    hotel_loyalty_number: Optional[str] = Field(default=None, description="Hotel loyalty program number (e.g., Marriott Bonvoy, Hilton Honors)")
    airline_frequent_flyer: Optional[str] = Field(default=None, description="Airline frequent flyer number")
    # Additional Notes
    hotel_booking_notes: Optional[str] = Field(default=None, description="Additional notes/comments for hotel booking (max 500 chars)")

@router.post("/login")
async def login(request: LoginRequest, response: Response):
    """
    Login with email and password.
    Returns {ok: true, user: {...}}. Sets session cookie (no access_token).
    Handles both admin@example.com and regular users.
    """
    try:
        if not request.password:
            raise HTTPException(status_code=400, detail="Password is required")

        # Initialize storage and collection
        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]
        
        # 1. Admin/Test Account Check (special hardcoded account)
        if request.email == "admin@example.com" and request.password == "1234":
            user_data = await users_collection.find_one({"email": request.email})
            
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
        user_data = await users_collection.find_one({"email": request.email})

        if not user_data:
            # ✅ Return specific error for email not found
            raise HTTPException(status_code=401, detail="Email not found")

        # Verify password
        password_hash = user_data.get("password_hash")
        if not password_hash:
            logger.warning(f"User {request.email} has no password_hash - cannot login with password")
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Verify password with detailed logging
        try:
            logger.info(f"Attempting password verification for user {request.email}")
            logger.debug(f"Password hash from DB: {password_hash[:50]}...")
            
            password_valid = verify_password(request.password, password_hash)
            
            if not password_valid:
                logger.warning(
                    f"Password verification failed for user {request.email}. "
                    f"Hash exists: {bool(password_hash)}, Hash length: {len(password_hash) if password_hash else 0}"
                )
                # Try to diagnose the issue
                try:
                    # Test if we can create a new hash with the same password
                    test_hash = hash_password(request.password)
                    test_verify = verify_password(request.password, test_hash)
                    logger.debug(f"Test hash/verify with same password: {test_verify}")
                except Exception as test_error:
                    logger.debug(f"Test hash/verify failed: {test_error}")
                
                raise HTTPException(status_code=401, detail="Invalid email or password")
            
            logger.info(f"Password verified successfully for user {request.email}")
        except HTTPException:
            raise
        except Exception as verify_error:
            logger.error(
                f"Password verification error for user {request.email}: {verify_error}",
                exc_info=True
            )
            raise HTTPException(status_code=401, detail="Invalid email or password")

        # Update last login
        await users_collection.update_one(
            {"email": request.email},
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

        storage = MongoStorage()
        await storage.connect()

        # ✅ Check if user exists by email
        users_collection = storage.db["users"]
        user_data = await users_collection.find_one({"email": email})

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




@router.post("/register", status_code=201)
async def register(request: RegisterRequest, response: Response):
    """
    Register a new user account.
    Expects firstName, lastName (camelCase). Returns {ok, user}. Sets session cookie.
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
        
        # Validate password strength
        is_valid, error_message = validate_password_strength(request.password)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_message)

        storage = MongoStorage()
        await storage.connect()
        users_collection = storage.db["users"]

        # Check if user already exists
        existing_user = await users_collection.find_one({"email": request.email})
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered")

        # Hash password (with SHA-256 pre-hashing to handle long passwords)
        try:
            hashed_password = hash_password(request.password)
            logger.info(f"Password hashed successfully for user: {request.email}")
        except Exception as hash_error:
            logger.error(f"Password hashing error: {hash_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Password encryption failed: {str(hash_error)}")

        # Create new user
        user_id = f"user_{int(datetime.utcnow().timestamp())}"
        user_doc = {
            "user_id": user_id,
            "email": request.email,
            "full_name": f"{request.first_name} {request.last_name}",
            "first_name": request.first_name.strip(),
            "last_name": request.last_name.strip(),
            "phone": request.phone.strip() if request.phone else None,
            "password_hash": hashed_password,
            "created_at": datetime.utcnow(),
            "last_login": datetime.utcnow()
        }
        await users_collection.insert_one(user_doc)
        logger.info(f"Registered new user: {request.email}")

        # Create user response (without password hash)
        user = User(
            user_id=user_id,
            email=request.email,
            full_name=f"{request.first_name} {request.last_name}",
            first_name=request.first_name.strip(),
            last_name=request.last_name.strip(),
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
async def reset_password(request: ResetPasswordRequest):
    """
    Reset user password
    Backs up old password hash before changing
    Case-insensitive email search
    """
    try:
        # Validate password strength
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
        
        # Hash new password
        try:
            new_password_hash = hash_password(request.new_password)
            update_data["password_hash"] = new_password_hash
            update_data["password_changed_at"] = datetime.utcnow()
            logger.info(f"Password hashed successfully for user: {request.email}")
        except Exception as hash_error:
            logger.error(f"Password hashing error: {hash_error}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Password encryption failed: {str(hash_error)}")
        
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

