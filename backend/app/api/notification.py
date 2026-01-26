"""
Notification API Router
Handles user notifications (booking created, payment status, etc.)
"""

from fastapi import APIRouter, HTTPException, Request
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.logging import get_logger
from app.core.config import settings
from app.storage.mongodb_storage import MongoStorage
from app.core.security import extract_user_id_from_request

logger = get_logger(__name__)

router = APIRouter(prefix="/api/notification", tags=["notifications"])


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
        
        cursor = notifications_collection.find(query).sort("created_at", -1).limit(50)
        notifications = await cursor.to_list(length=50)
        
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
        
        # ✅ SECURITY: Only update notification if it belongs to this user
        from bson import ObjectId
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
        
        if result.matched_count == 0:
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
