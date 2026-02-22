"""
เซอร์วิสอีเมลยืนยันตัวตนผ่าน Firebase
การส่งอีเมลยืนยันทำที่ฝั่ง Client ด้วย Firebase Auth sendEmailVerification()
สำหรับเปลี่ยนอีเมล: ส่งลิงก์ยืนยันไปอีเมลใหม่ (ใช้ EMAIL_SERVICE_URL ถ้ามี)
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
    สำหรับเปลี่ยนอีเมล: send_email_change_verification() ส่งลิงก์ไปอีเมลใหม่ (EMAIL_SERVICE_URL หรือ no-op)
    """

    def __init__(self):
        self.frontend_url = getattr(settings, "frontend_url", "") or ""
        self.email_service_url = getattr(settings, "email_service_url", "") or ""
        has_firebase = bool(
            getattr(settings, "firebase_project_id", None)
            or getattr(settings, "firebase_credentials_path", None)
        )
        # ยืนยันอีเมลใช้ได้เมื่อมี Firebase (ฝั่ง Client) หรือ EMAIL_SERVICE_URL (ส่งลิงก์ทางอีเมล)
        self.is_configured = bool(has_firebase or self.email_service_url)
        if not has_firebase:
            logger.debug(
                "Firebase not configured. Email verification can use EMAIL_SERVICE_URL to send link."
            )

    def generate_verification_token(self) -> str:
        """Generate a secure verification token (สำหรับ /verify-email กับ custom token ถ้าต้องการ)"""
        return secrets.token_urlsafe(32)

    def create_verification_url(self, token: str) -> str:
        """Create verification URL with token"""
        verification_path = f"/verify-email?token={urllib.parse.quote(token)}"
        return f"{self.frontend_url.rstrip('/')}{verification_path}"

    def create_email_change_verification_url(self, token: str) -> str:
        """Create verification URL for email change (กดลิงก์แล้วเปลี่ยนอีเมลและยืนยันในครั้งเดียว)"""
        path = f"/verify-email-change?token={urllib.parse.quote(token)}"
        return f"{self.frontend_url.rstrip('/')}{path}"

    def send_verification_email(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        ส่งอีเมลยืนยัน: ถ้ามี EMAIL_SERVICE_URL จะส่งลิงก์ /verify-email?token=... ทางอีเมล
        ถ้าไม่มี (ใช้เฉพาะ Firebase) เป็น no-op — ฝั่ง Client ใช้ Firebase sendEmailVerification()
        """
        link_url = self.create_verification_url(token)
        subject = "ยืนยันอีเมล - AI Travel Agent"
        name = user_name or "คุณ"
        if self.email_service_url:
            try:
                import httpx
                url = f"{self.email_service_url.rstrip('/')}/send"
                payload = {
                    "to": to_email,
                    "subject": subject,
                    "template": "verify-email",
                    "context": {"userName": name, "linkUrl": link_url},
                }
                r = httpx.post(url, json=payload, timeout=10.0)
                if r.is_success:
                    logger.info(f"Verification email sent to {to_email}")
                    return True
                logger.warning(f"Email service returned {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.warning(f"Failed to send verification email via EMAIL_SERVICE_URL: {e}")
        logger.warning(
            f"Email verification for {to_email}: no email sent (EMAIL_SERVICE_URL not set; use Firebase on client or set EMAIL_SERVICE_URL in .env)."
        )
        return False

    def send_email_change_verification(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """
        ส่งอีเมลเปลี่ยนอีเมลไปที่อีเมลใหม่ มีลิงก์กดเพื่อยืนยันและอัปเดตอีเมลใน MongoDB
        ถ้ามี EMAIL_SERVICE_URL จะ POST { to, subject, template, context } ไปที่ {url}/send (NestJS Mailer)
        """
        link_url = self.create_email_change_verification_url(token)
        subject = "ยืนยันการเปลี่ยนอีเมล - AI Travel Agent"
        name = user_name or "คุณ"
        if self.email_service_url:
            try:
                import httpx
                url = f"{self.email_service_url.rstrip('/')}/send"
                payload = {
                    "to": to_email,
                    "subject": subject,
                    "template": "verify-email-change",
                    "context": {"userName": name, "newEmail": to_email, "linkUrl": link_url},
                }
                r = httpx.post(url, json=payload, timeout=10.0)
                if r.is_success:
                    logger.info(f"Email change verification sent to {to_email}")
                    return True
                logger.warning(f"Email service returned {r.status_code}: {r.text[:200]}")
            except Exception as e:
                logger.warning(f"Failed to send email via EMAIL_SERVICE_URL: {e}")
        logger.info(f"Email change verification link for {to_email} (no mail sent): {link_url[:50]}...")
        return True


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    """Get or create email service instance"""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
