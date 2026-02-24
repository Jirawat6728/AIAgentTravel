"""
Email Service — Gmail SMTP
- ส่ง OTP ยืนยันอีเมล (สมัครสมาชิก + เปลี่ยนอีเมล)
- ส่งผ่าน Gmail SMTP (App Password)
"""

from __future__ import annotations
from typing import Optional
import secrets
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _send_gmail(to_email: str, subject: str, html_body: str) -> bool:
    """ส่งอีเมลผ่าน Gmail SMTP"""
    smtp_user = getattr(settings, "gmail_user", None) or ""
    smtp_pass = getattr(settings, "gmail_app_password", None) or ""
    if not smtp_user or not smtp_pass:
        logger.warning("[EmailService] GMAIL_USER / GMAIL_APP_PASSWORD not set")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AI Travel Agent | noreply <{smtp_user}>"
        msg["To"] = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        logger.info(f"[EmailService] Email sent OK to {to_email}")
        return True
    except Exception as e:
        logger.error(f"[EmailService] Gmail SMTP error: {e}")
        return False


def _build_verification_html(
    user_name: str,
    otp: str,
    site_name: str = "AI Travel Agent",
    context: str = "register",
    new_email: str = "",
) -> str:
    """
    Build OTP email HTML.
    context='register'     → registration / re-send verification
    context='email_change' → email change verification (shows new_email)
    """
    otp_boxes = "".join(
        f'<span style="display:inline-block;width:48px;height:56px;line-height:56px;'
        f'background:#f5f3ff;border:2px solid #a5b4fc;border-radius:12px;'
        f'font-size:28px;font-weight:800;color:#4f46e5;text-align:center;margin:0 4px;">'
        f'{d}</span>'
        for d in otp
    )

    if context == "email_change":
        new_email_line = (
            f'<p style="color:#4f46e5;font-weight:700;font-size:16px;margin:4px 0 20px;">{new_email}</p>'
            if new_email else ""
        )
        body_text = (
            f'<p style="color:#6b7280;font-size:15px;line-height:1.8;margin:0 0 4px;">'
            f'คุณได้ขอเปลี่ยนอีเมลเป็น:</p>'
            f'{new_email_line}'
            f'<p style="color:#6b7280;font-size:15px;line-height:1.8;margin:0 0 28px;">'
            f'กรุณากรอก <strong style="color:#4f46e5;">รหัส OTP 6 หลัก</strong> '
            f'ด้านล่างเพื่อยืนยันการเปลี่ยนอีเมล</p>'
        )
        ignore_text = "หากไม่ได้ขอเปลี่ยนอีเมล กรุณาเพิกเฉยต่ออีเมลนี้"
    else:
        body_text = (
            f'<p style="color:#6b7280;font-size:15px;line-height:1.8;margin:0 0 28px;">'
            f'ขอบคุณที่สมัครสมาชิก <strong style="color:#4f46e5;">{site_name}</strong><br>'
            f'กรุณากรอก <strong style="color:#4f46e5;">รหัส OTP 6 หลัก</strong> '
            f'ด้านล่างเพื่อยืนยันอีเมลของคุณ</p>'
        )
        ignore_text = "หากไม่ได้สมัครสมาชิก กรุณาเพิกเฉยต่ออีเมลนี้"

    return f"""<!DOCTYPE html>
<html lang="th">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#eef2ff;font-family:'Noto Sans Thai',Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#eef2ff;padding:48px 16px;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:20px;overflow:hidden;box-shadow:0 8px 40px rgba(99,102,241,0.13);max-width:560px;width:100%;">

        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#4f46e5 0%,#7c3aed 60%,#a855f7 100%);padding:44px 40px 36px;text-align:center;">
          <div style="font-size:44px;margin-bottom:12px;">✈️</div>
          <h1 style="color:#ffffff;margin:0;font-size:26px;font-weight:800;letter-spacing:-0.5px;">{site_name}</h1>
          <p style="color:rgba(255,255,255,0.75);margin:8px 0 0;font-size:14px;">AI-Powered Travel Planning</p>
        </td></tr>

        <!-- Body -->
        <tr><td style="padding:44px 44px 36px;">
          <h2 style="color:#1e1b4b;font-size:22px;font-weight:700;margin:0 0 16px;">
            สวัสดีคุณ {user_name}! 👋
          </h2>
          {body_text}

          <!-- OTP Box -->
          <div style="text-align:center;margin:32px 0 24px;">
            <p style="color:#374151;font-size:14px;margin:0 0 16px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;">รหัส OTP ของคุณ</p>
            <div style="display:inline-block;">{otp_boxes}</div>
            <p style="color:#6b7280;font-size:13px;margin:16px 0 0;">หรือคัดลอกรหัส: <strong style="color:#4f46e5;font-size:20px;letter-spacing:4px;">{otp}</strong></p>
          </div>

          <!-- Warning box -->
          <div style="background:#fef9c3;border:1px solid #fde047;border-radius:10px;padding:14px 18px;margin:28px 0 0;">
            <p style="color:#854d0e;font-size:13px;margin:0;line-height:1.7;">
              &#9203;&nbsp;<strong>รหัส OTP จะหมดอายุใน 10 นาที</strong> กรุณากรอกโดยเร็ว<br>
              {ignore_text}
            </p>
          </div>
        </td></tr>

        <!-- Divider -->
        <tr><td style="padding:0 44px;"><hr style="border:none;border-top:1px solid #e5e7eb;margin:0;"></td></tr>

        <!-- Footer -->
        <tr><td style="padding:24px 44px;text-align:center;">
          <p style="color:#9ca3af;font-size:12px;margin:0;line-height:1.8;">
            © 2025 {site_name} &nbsp;·&nbsp; ส่งโดยระบบอัตโนมัติ กรุณาอย่าตอบกลับ<br>
            หากมีปัญหา กรุณาติดต่อทีมงาน
          </p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


class EmailService:
    """Email service: Gmail SMTP with OTP-based verification."""

    def __init__(self):
        self.site_name = getattr(settings, "site_name", "AI Travel Agent") or "AI Travel Agent"
        self.is_configured = True

    def generate_verification_token(self) -> str:
        """Generate 6-digit OTP."""
        return f"{secrets.randbelow(1000000):06d}"

    def send_verification_email(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """ส่ง OTP ยืนยันอีเมลหลังสมัครสมาชิก"""
        name = user_name or "คุณ"
        html = _build_verification_html(name, token, self.site_name, context="register")
        return _send_gmail(to_email, f"รหัส OTP ยืนยันอีเมล - {self.site_name}", html)

    def send_email_change_otp(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
        new_email: str = "",
    ) -> bool:
        """ส่ง OTP ยืนยันการเปลี่ยนอีเมล (แสดงอีเมลใหม่ในเนื้อหา)"""
        name = user_name or "คุณ"
        html = _build_verification_html(
            name, token, self.site_name,
            context="email_change",
            new_email=new_email or to_email,
        )
        return _send_gmail(to_email, f"รหัส OTP ยืนยันการเปลี่ยนอีเมล - {self.site_name}", html)

    # ── Legacy alias (kept for backward compat, not used) ──────────────────────
    def send_email_change_verification(
        self,
        to_email: str,
        token: str,
        user_name: Optional[str] = None,
    ) -> bool:
        """Deprecated: use send_email_change_otp instead."""
        return self.send_email_change_otp(to_email, token, user_name, new_email=to_email)


_email_service: Optional[EmailService] = None


def get_email_service() -> EmailService:
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
