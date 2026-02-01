"""
เซอร์วิส SMS/OTP สำหรับยืนยันเบอร์โทร (Twilio หรือ stub สำหรับพัฒนา)
"""

from __future__ import annotations
from typing import Optional
import random
import string

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def generate_otp(length: int = 6) -> str:
    """Generate numeric OTP (e.g. 6 digits)."""
    return "".join(random.choices(string.digits, k=length))


class SMSService:
    """Send OTP via Twilio SMS or log for dev."""

    def __init__(self):
        self.is_configured = bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_phone_number
        )
        if not self.is_configured:
            logger.warning(
                "⚠️ SMS/Twilio not configured. OTP will be logged only. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER in .env"
            )

    def send_otp(self, to_phone: str, otp: str) -> bool:
        """
        Send OTP to phone. รองรับทุกเครือข่าย (ส่งผ่าน Twilio)
        If Twilio not configured, log OTP for dev (return True).
        """
        to_phone = (to_phone or "").strip().replace(" ", "")
        if not to_phone:
            return False
        # Normalize: ensure +country for Twilio (e.g. +66812345678)
        if not to_phone.startswith("+"):
            if to_phone.startswith("0"):
                to_phone = "+66" + to_phone[1:]  # Thailand
            else:
                to_phone = "+66" + to_phone

        if self.is_configured:
            try:
                from twilio.rest import Client
                client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
                message = client.messages.create(
                    body=f"รหัส OTP ของคุณ: {otp} ใช้ได้ {settings.sms_otp_expire_minutes} นาที (AI Travel Agent)",
                    from_=settings.twilio_phone_number,
                    to=to_phone,
                )
                logger.info(f"✅ OTP SMS sent to {to_phone} (sid: {message.sid})")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to send OTP SMS to {to_phone}: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"📱 [DEV] OTP for {to_phone}: {otp} (SMS not configured)")
            return True


_sms_service: Optional[SMSService] = None


def get_sms_service() -> SMSService:
    global _sms_service
    if _sms_service is None:
        _sms_service = SMSService()
    return _sms_service
