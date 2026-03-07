"""
Notification Service — helper สำหรับสร้างและ push notification ทุกประเภท
ใช้ร่วมกันได้จาก booking.py, auth.py, และ scheduled jobs
รองรับการส่งอีเมลแจ้งเตือน (ชำระเงินสำเร็จ, ทริปดีเลย์, ยกเลิก, แก้ไขทริป)
"""

from datetime import datetime
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services.notification_preferences import (
    get_preferences,
    NOTIFICATION_TYPE_PREFERENCE,
    should_send_email_notification,
)

logger = get_logger(__name__)


async def send_notification_email_if_enabled(
    *,
    db,
    user_id: str,
    notif_type: str,
    title: str,
    message: str,
    booking_id: Optional[str] = None,
) -> None:
    """
    ส่งอีเมลแจ้งเตือนถ้าผู้ใช้เปิดรับ (emailNotifications + type-specific preference).
    ใช้สำหรับ: payment_success, trip_change, trip_edited, flight_delayed, flight_cancelled, trip_alert
    """
    try:
        users_collection = db.get("users")
        if not users_collection:
            return
        user_doc = await users_collection.find_one({"user_id": user_id})
        if not user_doc:
            return
        to_email = (user_doc.get("email") or "").strip()
        if not to_email or "@" not in to_email:
            return
        if not should_send_email_notification(user_doc):
            logger.debug(f"Email notifications disabled for user {user_id}, skip email for {notif_type}")
            return
        prefs = get_preferences(user_doc)
        key = NOTIFICATION_TYPE_PREFERENCE.get(notif_type)
        if key and not prefs.get(key, True):
            logger.debug(f"Notification type {notif_type} disabled for user {user_id}, skip email")
            return
        site_name = getattr(settings, "site_name", "AI Travel Agent") or "AI Travel Agent"
        subject = f"{title} - {site_name}"
        from app.services.email_service import get_email_service
        email_service = get_email_service()
        sent = email_service.send_notification_email(to_email, subject, title, message)
        if sent:
            logger.info(f"Notification email sent: type={notif_type} to={to_email}")
        else:
            logger.warning(f"Notification email not sent (SMTP/config): type={notif_type} to={to_email}")
    except Exception as e:
        logger.warning(f"Failed to send notification email type={notif_type} user={user_id}: {e}")


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
            "created_at": datetime.utcnow().isoformat() + "Z",
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

        # ส่งอีเมลแจ้งเตือนถ้าผู้ใช้เปิดรับ (fire-and-forget)
        import asyncio
        asyncio.create_task(
            send_notification_email_if_enabled(
                db=db,
                user_id=user_id,
                notif_type=notif_type,
                title=title,
                message=message,
                booking_id=booking_id,
            )
        )

        return doc

    except Exception as e:
        logger.warning(f"Failed to create notification type={notif_type} user={user_id}: {e}")
        return None
