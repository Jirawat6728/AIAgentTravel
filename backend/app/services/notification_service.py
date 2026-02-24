"""
Notification Service — helper สำหรับสร้างและ push notification ทุกประเภท
ใช้ร่วมกันได้จาก booking.py, auth.py, และ scheduled jobs
"""

from datetime import datetime
from typing import Any, Dict, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_and_push_notification(
    *,
    db,
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    booking_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    check_preferences: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    สร้าง notification ใน MongoDB แล้ว push ผ่าน SSE ทันที
    ถ้า check_preferences=True จะตรวจสอบ user preferences ก่อน
    คืนค่า notification doc ที่สร้าง หรือ None ถ้าไม่ได้สร้าง
    """
    try:
        if check_preferences:
            from app.services.notification_preferences import should_create_in_app_notification
            users_collection = db["users"]
            user_doc = await users_collection.find_one({"user_id": user_id})
            if not should_create_in_app_notification(user_doc, notif_type):
                logger.debug(f"Skipped notification type={notif_type} for user={user_id} (preferences)")
                return None

        notifications_collection = db.get_collection("notifications")
        doc = {
            "user_id": user_id,
            "type": notif_type,
            "title": title,
            "message": message,
            "read": False,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {},
        }
        if booking_id:
            doc["booking_id"] = booking_id

        result = await notifications_collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        doc.pop("_id", None)

        from app.api.notification import push_notification_event
        await push_notification_event(user_id, doc)

        logger.info(f"Notification created: type={notif_type} user={user_id} title={title!r}")
        return doc

    except Exception as e:
        logger.warning(f"Failed to create notification type={notif_type} user={user_id}: {e}")
        return None
