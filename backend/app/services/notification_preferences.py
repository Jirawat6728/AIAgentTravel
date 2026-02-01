"""
การตั้งค่าการแจ้งเตือน: ตรวจสอบการตั้งค่าผู้ใช้ก่อนสร้างการแจ้งเตือนในแอป
หรือส่งการแจ้งเตือนทางอีเมล
"""

from typing import Any, Dict, Optional


# Notification type -> preference key (from Settings page)
NOTIFICATION_TYPE_PREFERENCE = {
    "booking_created": "bookingNotifications",
    "payment_status": "paymentNotifications",
    "trip_change": "tripChangeNotifications",
}


def get_preferences(user_doc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Get notification-related preferences from user document. Defaults to enabled."""
    prefs = (user_doc or {}).get("preferences") or {}
    return {
        "notificationsEnabled": prefs.get("notificationsEnabled", True),
        "bookingNotifications": prefs.get("bookingNotifications", True),
        "paymentNotifications": prefs.get("paymentNotifications", True),
        "tripChangeNotifications": prefs.get("tripChangeNotifications", True),
        "emailNotifications": prefs.get("emailNotifications", True),
    }


def should_create_in_app_notification(
    user_doc: Optional[Dict[str, Any]],
    notification_type: str,
) -> bool:
    """
    Return True if we should create an in-app notification for this user and type.
    Respects: notificationsEnabled (master) and type-specific (e.g. bookingNotifications).
    """
    prefs = get_preferences(user_doc)
    if not prefs.get("notificationsEnabled", True):
        return False
    key = NOTIFICATION_TYPE_PREFERENCE.get(notification_type)
    if not key:
        return True  # unknown type: allow
    return bool(prefs.get(key, True))


def should_send_email_notification(user_doc: Optional[Dict[str, Any]]) -> bool:
    """Return True if user has email notifications enabled (for future email digests)."""
    prefs = get_preferences(user_doc)
    return bool(prefs.get("emailNotifications", True))
