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
from db.repos.sessions_repo import SessionsRepo
from db.repos.users_repo import UsersRepo
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
