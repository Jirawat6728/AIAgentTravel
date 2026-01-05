from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Cookie, Depends, HTTPException, Request
from jwt import PyJWTError

from db import get_db
from db.mongo.repos.sessions_repo import SessionsRepo
from db.mongo.repos.users_repo import UsersRepo

AUTH_JWT_SECRET = (os.getenv("AUTH_JWT_SECRET") or "dev-change-me").strip()
AUTH_JWT_ALG = (os.getenv("AUTH_JWT_ALG") or "HS256").strip()
AUTH_SESSION_TTL_DAYS = int(os.getenv("AUTH_SESSION_TTL_DAYS") or "7")
AUTH_COOKIE_NAME = (os.getenv("AUTH_COOKIE_NAME") or "access_token").strip()


def _jwt_encode(payload: Dict[str, Any]) -> str:
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm=AUTH_JWT_ALG)


def _jwt_decode(token: str) -> Dict[str, Any]:
    return jwt.decode(token, AUTH_JWT_SECRET, algorithms=[AUTH_JWT_ALG])


def create_access_token(*, user_id: str, session_id: str, ttl_days: int) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=ttl_days)
    return _jwt_encode(
        {
            "sub": str(user_id),
            "sid": str(session_id),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "typ": "access",
        }
    )


async def get_current_user(
    request: Request,
    access_token: Optional[str] = Cookie(default=None, alias=AUTH_COOKIE_NAME),
) -> Dict[str, Any]:
    token = access_token
    if not token:
        # allow Authorization header too
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = _jwt_decode(token)
        session_id = payload.get("sid")
        user_id = payload.get("sub")
        if not session_id or not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    db = get_db()
    sessions = SessionsRepo(db)
    sess = await sessions.get_active(str(session_id))
    if not sess:
        raise HTTPException(status_code=401, detail="Session expired")

    users = UsersRepo(db)
    user = await users.get_by_id(sess["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return user
