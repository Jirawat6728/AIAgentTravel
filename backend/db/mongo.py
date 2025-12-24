from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

load_dotenv(override=True)

MONGO_URI = (os.getenv("MONGO_URI") or os.getenv("MONGODB_URI") or "").strip()
MONGO_DB_NAME = (os.getenv("MONGO_DB_NAME") or "travel_agent").strip()

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


async def connect_to_mongo():
    global _client, _db
    if _db is not None:
        return
    if not MONGO_URI:
        # allow running without mongo
        _client = None
        _db = None
        return
    _client = AsyncIOMotorClient(MONGO_URI)
    _db = _client[MONGO_DB_NAME]


async def close_mongo():
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Mongo not connected. Set MONGO_URI and call connect_to_mongo() on startup.")
    return _db
