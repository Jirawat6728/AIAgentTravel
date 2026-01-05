from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from core.auth import (
    AUTH_COOKIE_NAME,
    AUTH_SESSION_TTL_DAYS,
    create_access_token,
    get_current_user,
)
from db import get_db
from db.mongo.repos.sessions_repo import SessionsRepo
from db.mongo.repos.users_repo import UsersRepo
from services.google_auth import verify_google_id_token

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_SECURE = (os.getenv("AUTH_COOKIE_SECURE") or "0").strip().lower() in {"1", "true", "yes"}
COOKIE_SAMESITE = (os.getenv("AUTH_COOKIE_SAMESITE") or "lax").strip().lower()  # lax|strict|none


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., description="Google ID token from Google Identity Services")


@router.post("/google")
async def login_with_google(payload: GoogleLoginRequest, request: Request, response: Response):
    """Exchange a Google ID token for a backend session (httpOnly cookie)."""
    try:
        claims = verify_google_id_token(payload.id_token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Google token invalid: {e}")

    db = get_db()
    users = UsersRepo(db)
    sessions = SessionsRepo(db)

    user = await users.upsert_google_user(
        sub=str(claims["sub"]),
        email=str(claims["email"]),
        name=claims.get("name"),
        picture=claims.get("picture"),
        raw_claims=claims,
    )

    sess = await sessions.create(
        user_id=user["_id"],
        ttl_days=AUTH_SESSION_TTL_DAYS,
        user_agent=request.headers.get("user-agent"),
    )

    token = create_access_token(user_id=str(user["_id"]), session_id=str(sess["_id"]), ttl_days=AUTH_SESSION_TTL_DAYS)

    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=AUTH_SESSION_TTL_DAYS * 24 * 60 * 60,
        path="/",
    )

    return {
        "ok": True,
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
        },
    }


@router.get("/me")
async def me(user: Dict[str, Any] = Depends(get_current_user)):
    return {
        "ok": True,
        "user": {
            "id": str(user["_id"]),
            "email": user.get("email"),
            "name": user.get("name"),
            "picture": user.get("picture"),
            # Profile fields
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "phone": user.get("phone"),
            "dob": user.get("dob"),
            "gender": user.get("gender"),
            "passport_no": user.get("passport_no"),
            "passport_expiry": user.get("passport_expiry"),
            "nationality": user.get("nationality"),
            "address_line1": user.get("address_line1"),
            "address_line2": user.get("address_line2"),
            "city": user.get("city"),
            "province": user.get("province"),
            "postal_code": user.get("postal_code"),
            "country": user.get("country"),
        },
    }


class UpdateProfileRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    passport_no: Optional[str] = None
    passport_expiry: Optional[str] = None
    nationality: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None


@router.put("/profile")
async def update_profile(
    payload: UpdateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user),
):
    """Update user profile information."""
    db = get_db()
    users = UsersRepo(db)
    
    updated = await users.update_profile(
        user_id=user["_id"],
        first_name=payload.first_name,
        last_name=payload.last_name,
        phone=payload.phone,
        dob=payload.dob,
        gender=payload.gender,
        passport_no=payload.passport_no,
        passport_expiry=payload.passport_expiry,
        nationality=payload.nationality,
        address_line1=payload.address_line1,
        address_line2=payload.address_line2,
        city=payload.city,
        province=payload.province,
        postal_code=payload.postal_code,
        country=payload.country,
    )
    
    if not updated:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "ok": True,
        "user": {
            "id": str(updated["_id"]),
            "email": updated.get("email"),
            "name": updated.get("name"),
            "picture": updated.get("picture"),
            "first_name": updated.get("first_name"),
            "last_name": updated.get("last_name"),
            "phone": updated.get("phone"),
            "dob": updated.get("dob"),
            "gender": updated.get("gender"),
            "passport_no": updated.get("passport_no"),
            "passport_expiry": updated.get("passport_expiry"),
            "nationality": updated.get("nationality"),
            "address_line1": updated.get("address_line1"),
            "address_line2": updated.get("address_line2"),
            "city": updated.get("city"),
            "province": updated.get("province"),
            "postal_code": updated.get("postal_code"),
            "country": updated.get("country"),
        },
    }


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
):
    # best-effort revoke session if present
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if token:
        try:
            import jwt
            from core.auth import AUTH_JWT_SECRET, AUTH_JWT_ALG
            payload = jwt.decode(token, AUTH_JWT_SECRET, algorithms=[AUTH_JWT_ALG])
            sid = payload.get("sid")
            if sid:
                db = get_db()
                await SessionsRepo(db).revoke(str(sid))
        except Exception:
            pass

    response.delete_cookie(key=AUTH_COOKIE_NAME, path="/")
    return {"ok": True}
