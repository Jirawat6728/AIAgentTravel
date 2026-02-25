"""
Trips API — CRUD สำหรับ trip entities ที่เป็นอิสระจาก chat
1 trip สามารถถูก link จากหลาย chat session ได้
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.storage.mongodb_storage import MongoStorage
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/trips", tags=["trips"])


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateTripRequest(BaseModel):
    title: str = Field(default="ทริปใหม่", max_length=200)
    trip_id: Optional[str] = Field(default=None, description="ถ้าส่งมา ใช้ id นี้ (frontend-generated), ถ้าไม่ส่ง backend สร้างให้")


class UpdateTripRequest(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    status: Optional[str] = Field(default=None, description="planning | booked | completed")


class LinkChatRequest(BaseModel):
    chat_id: str = Field(..., description="Chat (session) ที่ต้องการ link")


def _trip_to_response(doc: dict) -> dict:
    """แปลง MongoDB document เป็น response dict ที่ frontend ใช้ได้"""
    last_updated = doc.get("last_updated")
    created_at = doc.get("created_at")
    return {
        "trip_id": doc.get("trip_id"),
        "user_id": doc.get("user_id"),
        "title": doc.get("title") or "ทริปใหม่",
        "status": doc.get("status", "planning"),
        "booking_ids": doc.get("booking_ids", []),
        "has_plan": bool(doc.get("trip_plan")),
        "last_updated": last_updated.isoformat() if isinstance(last_updated, datetime) else last_updated,
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else created_at,
    }


def _get_user_id(request: Request) -> Optional[str]:
    from app.core.security import extract_user_id_from_request
    return extract_user_id_from_request(request)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("")
async def list_trips(fastapi_request: Request, limit: int = 50):
    """ดึง list ของ trips ทั้งหมดของ user"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    docs = await storage.list_trips(user_id, limit=min(limit, 100))
    return {"trips": [_trip_to_response(d) for d in docs]}


@router.post("")
async def create_trip(request: CreateTripRequest, fastapi_request: Request):
    """สร้าง trip ใหม่  ถ้าส่ง trip_id มาก็ใช้ id นั้น (idempotent)"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()

    if request.trip_id:
        # Frontend-generated id — upsert เพื่อให้ idempotent
        existing = await storage.get_trip(request.trip_id, user_id)
        if not existing:
            await storage.save_trip(
                trip_id=request.trip_id,
                user_id=user_id,
                trip_plan={},
                title=request.title,
                status="planning",
            )
        trip_id = request.trip_id
    else:
        trip_id = await storage.create_trip(user_id, title=request.title)

    doc = await storage.get_trip(trip_id, user_id)
    if not doc:
        raise HTTPException(status_code=500, detail="Failed to create trip")

    return _trip_to_response(doc)


@router.get("/{trip_id}")
async def get_trip(trip_id: str, fastapi_request: Request):
    """ดึงข้อมูล trip (รวม trip_plan)"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    doc = await storage.get_trip(trip_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    result = _trip_to_response(doc)
    result["trip_plan"] = doc.get("trip_plan", {})
    return result


@router.patch("/{trip_id}")
async def update_trip(trip_id: str, request: UpdateTripRequest, fastapi_request: Request):
    """แก้ไข title หรือ status ของ trip"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    doc = await storage.get_trip(trip_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    await storage.save_trip(
        trip_id=trip_id,
        user_id=user_id,
        trip_plan=doc.get("trip_plan", {}),
        title=request.title if request.title is not None else doc.get("title"),
        status=request.status if request.status is not None else doc.get("status"),
    )

    updated = await storage.get_trip(trip_id, user_id)
    return _trip_to_response(updated)


@router.delete("/{trip_id}")
async def delete_trip(trip_id: str, fastapi_request: Request):
    """ลบ trip และ unlink sessions ที่เชื่อมอยู่"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    ok = await storage.delete_trip(trip_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Trip not found or already deleted")
    return {"ok": True, "trip_id": trip_id}


@router.post("/{trip_id}/link-chat")
async def link_chat_to_trip(trip_id: str, request: LinkChatRequest, fastapi_request: Request):
    """Link chat session เข้ากับ trip นี้  ทำให้ chat ทำงานบน trip plan เดียวกัน"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    # ตรวจสอบว่า trip มีอยู่จริง
    doc = await storage.get_trip(trip_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    session_id = f"{user_id}::{request.chat_id}"
    ok = await storage.link_chat_to_trip(session_id, trip_id, user_id)
    return {"ok": ok, "session_id": session_id, "trip_id": trip_id}


@router.get("/{trip_id}/chats")
async def get_trip_chats(trip_id: str, fastapi_request: Request):
    """ดึง list ของ chats ทั้งหมดที่ link กับ trip นี้"""
    user_id = _get_user_id(fastapi_request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    storage = MongoStorage()
    doc = await storage.get_trip(trip_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    try:
        if storage.sessions_collection is None:
            await storage.connect()
        cursor = storage.sessions_collection.find(
            {"trip_id": trip_id, "user_id": user_id}
        ).sort("last_updated", -1)
        sessions = await cursor.to_list(length=100)
        chats = [
            {
                "chat_id": s.get("chat_id") or s.get("session_id", "").split("::")[-1],
                "session_id": s.get("session_id"),
                "title": s.get("title") or "แชทใหม่",
                "last_updated": s.get("last_updated").isoformat() if isinstance(s.get("last_updated"), datetime) else s.get("last_updated"),
            }
            for s in sessions
        ]
        return {"trip_id": trip_id, "chats": chats}
    except Exception as e:
        logger.error(f"get_trip_chats error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
