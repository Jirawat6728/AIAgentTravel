"""
เซอร์วิสอีเมลยืนยันตัวตนผ่าน Firebase
การส่งอีเมลยืนยันทำที่ฝั่ง Client ด้วย Firebase Auth sendEmailVerification()
Backend ไม่ส่งอีเมลเอง — ใช้เป็น no-op และเก็บ interface สำหรับ register/update-email
"""

from __future__ import annotations
from typing import Optional
import secrets
import urllib.parse

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Email service: การยืนยันอีเมลใช้ Firebase Auth บนฝั่ง Client
    send_verification_email() เป็น no-op — คืน True เพื่อให้ flow ทำงานต่อได้
    """

    def __init__(self):
        self.frontend_url = getattr(settings, "frontend_url", "") or ""
        # ใช้ Firebase เป็นช่องทางยืนยันอีเมล — ไม่ต้องมี Nodemailer/EMAIL_SERVICE_URL
        self.is_configured = bool(
            getattr(settings, "firebase_project_id", None)
            or getattr(settings, "firebase_credentials_path", None)
        )
        if not self.is_configured:
            logger.debug(
                "Firebase not configured. Email verification is handled by Firebase on the client."
            )

    def generate_verification_token(self) -> str:
        """Generate a secure verification token (สำหรับ /verify-email กับ custom token ถ้าต้องการ)"""
        return secrets.token_urlsafe(32)

    def create_verification_url(self, token: str) -> str:
        """Create verification URL with token"""
        verification_path = f"/verify-email?token={urllib.parse.quote(token)}"
        return f"{self.frontend_url.rstrip('/')}{verification_path}"

    def send_verification_email(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        No-op: การส่งอีเมลยืนยันทำที่ฝั่ง Client ด้วย Firebase Auth sendEmailVerification()
        คืน True เพื่อให้ register/update-email ทำงานต่อได้
        """
        logger.info(
            f"Email verification for {to_email} is handled by Firebase on the client (sendEmailVerification)."
        )
        return True


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
