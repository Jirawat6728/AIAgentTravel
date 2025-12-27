from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt

JWT_SECRET = (os.getenv("AUTH_JWT_SECRET") or "dev_secret_change_me").strip()
JWT_ALG = "HS256"
JWT_DAYS = int(os.getenv("AUTH_JWT_DAYS") or "14")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(*, user_id: str, session_id: str, extra: Optional[Dict[str, Any]] = None) -> str:
    now = _now()
    payload: Dict[str, Any] = {
        "sub": user_id,
        "sid": session_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=JWT_DAYS)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
