"""
เราเตอร์ API การแจ้งเตือน
จัดการการแจ้งเตือนผู้ใช้ (จองสร้างแล้ว สถานะการชำระเงิน ฯลฯ)
รองรับ SSE (Server-Sent Events) สำหรับ real-time push
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import json
from app.core.logging import get_logger
from app.core.config import settings
from app.storage.mongodb_storage import MongoStorage
from app.core.security import extract_user_id_from_request

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notification", tags=["notifications"])

# ── SSE subscriber registry ──────────────────────────────────────────────────
# { user_id: [asyncio.Queue, ...] }
_sse_subscribers: Dict[str, List[asyncio.Queue]] = {}


def _get_queues(user_id: str) -> List[asyncio.Queue]:
    return _sse_subscribers.get(user_id, [])


async def push_notification_event(user_id: str, notification: dict):
    """
    เรียกจาก booking.py หลัง insert_one เพื่อ push event ไปยัง SSE subscribers ทันที
    """
    queues = _get_queues(user_id)
    if not queues:
        return
    payload = json.dumps({"type": "new_notification", "notification": notification}, ensure_ascii=False)
    dead = []
    for q in queues:
        try:
            q.put_nowait(payload)
        except asyncio.QueueFull:
            dead.append(q)
    # ลบ queue ที่เต็ม (client ตายแล้ว)
    for q in dead:
        try:
            _sse_subscribers[user_id].remove(q)
        except ValueError:
            pass


@router.get("/list")
async def list_notifications(request: Request):
    """
    List all notifications for the current user
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            return {
                "ok": True,
                "notifications": [],
                "count": 0,
                "unread_count": 0
            }
        
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            return {
                "ok": True,
                "notifications": [],
                "count": 0,
                "unread_count": 0,
                "message": "Database connection unavailable"
            }
        
        notifications_collection = storage.db.get_collection("notifications")
        
        # ✅ SECURITY: Query only notifications for this specific user_id
        query = {"user_id": user_id}
        
        # ✅ CRUD STABILITY: Query with timeout protection
        import asyncio
        try:
            cursor = notifications_collection.find(query).sort("created_at", -1).limit(50)
            notifications = await asyncio.wait_for(cursor.to_list(length=50), timeout=5.0)
        except asyncio.TimeoutError:
            logger.error(f"Notifications query timeout for user: {user_id}")
            return {
                "ok": False,
                "notifications": [],
                "count": 0,
                "unread_count": 0,
                "error": "Query timeout"
            }
        except Exception as query_error:
            logger.error(f"Notifications query error for user {user_id}: {query_error}", exc_info=True)
            return {
                "ok": False,
                "notifications": [],
                "count": 0,
                "unread_count": 0,
                "error": "Failed to retrieve notifications"
            }
        
        # Convert ObjectId to string and format
        formatted_notifications = []
        unread_count = 0
        for notif in notifications:
            notif["_id"] = str(notif["_id"])
            if not notif.get("read", False):
                unread_count += 1
            formatted_notifications.append({
                "id": notif["_id"],
                "type": notif.get("type", "info"),
                "title": notif.get("title", "Notification"),
                "message": notif.get("message", ""),
                "read": notif.get("read", False),
                "created_at": notif.get("created_at"),
                "booking_id": notif.get("booking_id"),
                "metadata": notif.get("metadata", {})
            })
        
        logger.info(f"Retrieved {len(formatted_notifications)} notifications for user: {user_id} (unread: {unread_count})")
        
        return {
            "ok": True,
            "notifications": formatted_notifications,
            "count": len(formatted_notifications),
            "unread_count": unread_count
        }
        
    except Exception as e:
        logger.error(f"Failed to list notifications: {e}", exc_info=True)
        return {
            "ok": False,
            "notifications": [],
            "count": 0,
            "unread_count": 0,
            "error": str(e)
        }


@router.get("/stream")
async def notification_stream(request: Request):
    """
    SSE endpoint — client subscribe แล้วรับ push ทันทีเมื่อมี notification ใหม่
    ใช้แทน polling ทุก 60 วินาที
    """
    user_id = extract_user_id_from_request(request)
    if not user_id:
        return StreamingResponse(
            iter(["data: {\"type\":\"error\",\"message\":\"unauthenticated\"}\n\n"]),
            media_type="text/event-stream"
        )

    queue: asyncio.Queue = asyncio.Queue(maxsize=50)

    # ลงทะเบียน subscriber
    if user_id not in _sse_subscribers:
        _sse_subscribers[user_id] = []
    _sse_subscribers[user_id].append(queue)
    logger.info(f"SSE subscriber added for user: {user_id} (total: {len(_sse_subscribers[user_id])})")

    async def event_generator():
        try:
            # ส่ง heartbeat แรกทันที
            yield "data: {\"type\":\"connected\"}\n\n"
            while True:
                # ตรวจว่า client ยังเชื่อมต่ออยู่
                if await request.is_disconnected():
                    break
                try:
                    # รอ event สูงสุด 25 วินาที แล้วส่ง heartbeat
                    payload = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    # heartbeat เพื่อไม่ให้ connection timeout
                    yield "data: {\"type\":\"heartbeat\"}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            # ยกเลิกการลงทะเบียน
            try:
                _sse_subscribers[user_id].remove(queue)
                if not _sse_subscribers[user_id]:
                    del _sse_subscribers[user_id]
            except (ValueError, KeyError):
                pass
            logger.info(f"SSE subscriber removed for user: {user_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # ปิด Nginx buffering
        }
    )


@router.get("/count")
async def get_notification_count(request: Request):
    """
    Get unread notification count for the current user
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            return {
                "ok": True,
                "count": 0
            }
        
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            return {
                "ok": True,
                "count": 0
            }
        
        notifications_collection = storage.db.get_collection("notifications")
        
        # ✅ SECURITY: Count only unread notifications for this specific user_id
        unread_count = await notifications_collection.count_documents({
            "user_id": user_id,
            "read": False
        })
        
        return {
            "ok": True,
            "count": unread_count
        }
        
    except Exception as e:
        logger.error(f"Failed to get notification count: {e}", exc_info=True)
        return {
            "ok": False,
            "count": 0,
            "error": str(e)
        }


@router.post("/mark-read")
async def mark_notification_read(request: Request, notification_id: str):
    """
    Mark a notification as read
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        notifications_collection = storage.db.get_collection("notifications")
        
        # ✅ CRUD STABILITY: Only update notification if it belongs to this user (atomic operation)
        from bson import ObjectId
        try:
            result = await notifications_collection.update_one(
                {
                    "_id": ObjectId(notification_id),
                    "user_id": user_id  # ✅ CRITICAL: Ensure user owns this notification
                },
                {
                    "$set": {
                        "read": True,
                        "read_at": datetime.utcnow().isoformat()
                    }
                }
            )
        except Exception as obj_id_error:
            # ✅ CRUD STABILITY: Handle invalid ObjectId format
            logger.warning(f"Invalid notification_id format: {notification_id}, error: {obj_id_error}")
            raise HTTPException(status_code=400, detail="Invalid notification ID format")
        
        if result.matched_count == 0:
            logger.warning(f"Notification not found or access denied: notification_id={notification_id}, user_id={user_id}")
            raise HTTPException(status_code=404, detail="Notification not found or access denied")
        
        return {
            "ok": True,
            "message": "Notification marked as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark notification as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")


@router.post("/mark-all-read")
async def mark_all_notifications_read(request: Request):
    """
    Mark all notifications as read for the current user
    """
    try:
        # ✅ Use security helper function (prioritizes cookie, then header)
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        notifications_collection = storage.db.get_collection("notifications")
        
        # ✅ SECURITY: Only update notifications for this user
        result = await notifications_collection.update_many(
            {
                "user_id": user_id,
                "read": False
            },
            {
                "$set": {
                    "read": True,
                    "read_at": datetime.utcnow().isoformat()
                }
            }
        )
        
        return {
            "ok": True,
            "message": f"Marked {result.modified_count} notifications as read"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to mark all notifications as read: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark all notifications as read: {str(e)}")


@router.post("/clear-all")
async def clear_all_notifications(request: Request):
    """
    ลบการแจ้งเตือนทั้งหมดออกเฉพาะของ user ปัจจุบัน (ตาม X-User-ID หรือ session)
    """
    try:
        user_id = extract_user_id_from_request(request)
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        storage = MongoStorage()
        await storage.connect()
        
        if storage.db is None:
            raise HTTPException(status_code=500, detail="Database connection unavailable")
        
        notifications_collection = storage.db.get_collection("notifications")
        
        result = await notifications_collection.delete_many({"user_id": user_id})
        
        logger.info(f"Cleared all notifications for user: {user_id}, deleted: {result.deleted_count}")
        
        return {
            "ok": True,
            "message": f"ลบการแจ้งเตือนทั้งหมดแล้ว ({result.deleted_count} รายการ)",
            "deleted_count": result.deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to clear notifications: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="ไม่สามารถล้างการแจ้งเตือนได้")


# ── Flight Status Trigger (Demo / Admin) ─────────────────────────────────────

class FlightStatusRequest(BaseModel):
    booking_id: str
    status: str          # "delayed" | "cancelled" | "rescheduled"
    delay_minutes: Optional[int] = 0


@router.post("/trigger-flight-status")
async def trigger_flight_status(request: Request, body: FlightStatusRequest):
    """
    (Demo) อัปเดต flight_status ของ booking แล้วส่ง notification ทันที
    ใช้สำหรับ demo / admin เพื่อจำลองสถานการณ์ไฟท์ดีเลย์/ยกเลิก
    """
    user_id = extract_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    valid_statuses = {"delayed", "cancelled", "rescheduled"}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"status must be one of {valid_statuses}")

    storage = MongoStorage()
    await storage.connect()
    if storage.db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    from bson import ObjectId
    bookings_col = storage.db.get_collection("bookings")

    # หา booking
    booking = None
    try:
        booking = await bookings_col.find_one({"_id": ObjectId(body.booking_id), "user_id": user_id})
    except Exception:
        pass
    if not booking:
        booking = await bookings_col.find_one({"booking_id": body.booking_id, "user_id": user_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking_id = str(booking.get("booking_id") or booking["_id"])

    # อัปเดต flight_status
    update_fields: Dict[str, Any] = {
        "flight_status": body.status,
        "updated_at": datetime.utcnow().isoformat(),
    }
    if body.status == "delayed" and body.delay_minutes:
        update_fields["delay_minutes"] = body.delay_minutes

    # ล้าง sent_reminders สำหรับ alert นี้ เพื่อให้ส่งใหม่ได้
    alert_key = f"trip_alert_{body.status}"
    await bookings_col.update_one(
        {"_id": booking["_id"]},
        {
            "$set": update_fields,
            "$pull": {"sent_reminders": alert_key},
        }
    )

    # Push notification ทันที
    from app.services.notification_service import create_and_push_notification

    if body.status == "cancelled":
        title = "เที่ยวบินถูกยกเลิกโดยสายการบิน"
        msg = f"เที่ยวบินในการจอง #{booking_id[:8]} ถูกยกเลิกโดยสายการบิน กรุณาติดต่อสายการบินหรือแก้ไขทริปของคุณ"
        notif_type = "flight_cancelled"
    elif body.status == "delayed":
        delay_min = body.delay_minutes or 0
        title = "เที่ยวบินล่าช้า"
        msg = f"เที่ยวบินในการจอง #{booking_id[:8]} ล่าช้าประมาณ {delay_min} นาที"
        notif_type = "flight_delayed"
    else:
        title = "เที่ยวบินเปลี่ยนเวลา"
        msg = f"เที่ยวบินในการจอง #{booking_id[:8]} มีการเปลี่ยนแปลงเวลา กรุณาตรวจสอบและแก้ไขทริปของคุณ"
        notif_type = "flight_rescheduled"

    await create_and_push_notification(
        db=storage.db,
        user_id=user_id,
        notif_type=notif_type,
        title=title,
        message=msg,
        booking_id=booking_id,
        metadata={"flight_status": body.status, "delay_minutes": body.delay_minutes},
        check_preferences=False,  # force send สำหรับ demo
    )

    return {"ok": True, "message": f"Flight status updated to '{body.status}' and notification sent"}


@router.post("/trigger-trip-alert")
async def trigger_trip_alert(request: Request, body: dict):
    """
    (Demo) ส่ง trip_alert notification — แจ้งเตือนให้ user แก้ไขทริปที่เปลี่ยนแปลงมากเกินไป
    body: { booking_id, message (optional) }
    """
    user_id = extract_user_id_from_request(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    booking_id = body.get("booking_id", "")
    custom_msg = body.get("message", "")

    storage = MongoStorage()
    await storage.connect()
    if storage.db is None:
        raise HTTPException(status_code=500, detail="Database unavailable")

    from app.services.notification_service import create_and_push_notification
    await create_and_push_notification(
        db=storage.db,
        user_id=user_id,
        notif_type="trip_alert",
        title="ทริปของคุณมีการเปลี่ยนแปลงมาก",
        message=custom_msg or f"ทริปในการจอง #{booking_id[:8] if booking_id else '?'} มีการเปลี่ยนแปลงหลายรายการ กรุณาตรวจสอบและแก้ไขทริปเพื่อไม่ให้ทริปล่ม",
        booking_id=booking_id or None,
        metadata={"trigger": "manual"},
        check_preferences=False,
    )
    return {"ok": True, "message": "Trip alert notification sent"}
