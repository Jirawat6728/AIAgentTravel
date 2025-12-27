from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

DEFAULT_SESSION_DAYS = int(os.getenv("SESSION_DAYS") or "14")


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuthRepo:
    """DB layer for authentication and sessions."""

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def upsert_google_identity(
        self,
        *,
        google_sub: str,
        email: Optional[str],
        email_verified: Optional[bool],
        name: Optional[str],
        picture: Optional[str],
        locale: Optional[str] = None,
    ) -> Tuple[ObjectId, Dict[str, Any]]:
        """Bind Google account to a user (create if missing)."""
        if not google_sub:
            raise ValueError("google_sub is required")

        ident = await self.db.auth_identities.find_one({"provider": "google", "provider_user_id": google_sub})

        if ident:
            user_id = ident["user_id"]

            # Update user
            await self.db.users.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "updated_at": _now(),
                        "profile.display_name": name,
                        "profile.photo_url": picture,
                        "profile.locale": locale,
                        **({"primary_email": email} if email else {}),
                        **({"emails": [email]} if email else {}),
                    }
                },
                upsert=True,
            )

            # Update identity
            await self.db.auth_identities.update_one(
                {"_id": ident["_id"]},
                {
                    "$set": {
                        "updated_at": _now(),
                        "email": email,
                        "email_verified": email_verified,
                        "profile": {"name": name, "picture": picture, "locale": locale},
                    }
                },
            )

            user = await self.db.users.find_one({"_id": user_id})
            return user_id, (user or {})

        # Create new user
        user_doc: Dict[str, Any] = {
            "created_at": _now(),
            "updated_at": _now(),
            "primary_email": email,
            "emails": [email] if email else [],
            "profile": {"display_name": name, "photo_url": picture, "locale": locale},
            "roles": ["user"],
            "status": "active",
            "features": {"payments_enabled": False},
        }
        ins = await self.db.users.insert_one(user_doc)
        user_id = ins.inserted_id

        ident_doc: Dict[str, Any] = {
            "created_at": _now(),
            "updated_at": _now(),
            "provider": "google",
            "provider_user_id": google_sub,
            "user_id": user_id,
            "email": email,
            "email_verified": email_verified,
            "profile": {"name": name, "picture": picture, "locale": locale},
        }
        await self.db.auth_identities.insert_one(ident_doc)

        user = await self.db.users.find_one({"_id": user_id})
        return user_id, (user or {})

    async def create_session(
        self,
        *,
        user_id: ObjectId,
        ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        days: int = DEFAULT_SESSION_DAYS,
    ) -> Dict[str, Any]:
        sid = str(uuid.uuid4())
        now = _now()
        sess = {
            "session_id": sid,
            "user_id": user_id,
            "created_at": now,
            "last_seen_at": now,
            "expires_at": now + timedelta(days=days),
            "revoked_at": None,
            "ip": ip,
            "user_agent": user_agent,
        }
        await self.db.sessions.insert_one(sess)
        return sess

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        return await self.db.sessions.find_one({"session_id": session_id, "revoked_at": None})

    async def touch_session(self, session_id: str) -> None:
        await self.db.sessions.update_one({"session_id": session_id, "revoked_at": None}, {"$set": {"last_seen_at": _now()}})

    async def revoke_session(self, session_id: str) -> None:
        await self.db.sessions.update_one({"session_id": session_id}, {"$set": {"revoked_at": _now()}})

    # Omise future placeholder
    async def set_user_payment_customer(self, *, user_id: ObjectId, provider: str, customer_id: str) -> None:
        await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"updated_at": _now(), "features.payments_enabled": True, "payments.provider": provider, "payments.customer_id": customer_id}},
        )
