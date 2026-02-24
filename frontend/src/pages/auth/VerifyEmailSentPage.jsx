import React from 'react';
import './VerifyEmailSentPage.css';

export default function VerifyEmailSentPage({ email, from, onNavigateToHome, onNavigateToLogin, onNavigateToSettings }) {
  const emailDisplay = email || 'อีเมลของคุณ';

  const handleContinue = () => {
    if (from === 'register' || from === 'login') {
      onNavigateToLogin?.();
    } else {
      onNavigateToSettings?.();
    }
  };

  return (
    <div className="verify-email-sent-container">
      <div className="verify-email-sent-card">
        <div className="verify-email-sent-icon">📧</div>
        <h1>ตรวจสอบอีเมลของคุณ</h1>
        <p className="verify-email-sent-email">{emailDisplay}</p>
        <p className="verify-email-sent-desc">
          เราได้ส่งลิงก์ยืนยันอีเมลไปที่กล่องจดหมายของคุณแล้ว<br />
          กรุณาคลิก <strong>「ยืนยันอีเมล」</strong> ในอีเมลเพื่อเข้าสู่ระบบ
        </p>
        <p className="verify-email-sent-note">
          ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam หรือ Junk
        </p>
        <div className="verify-email-sent-actions">
          <button className="btn-primary" onClick={handleContinue}>
            {from === 'register' || from === 'login' ? 'ไปหน้าเข้าสู่ระบบ' : 'กลับไปตั้งค่า'}
          </button>
          <button className="btn-secondary" onClick={onNavigateToHome}>
            ไปหน้าแรก
          </button>
        </div>
      </div>
    </div>
  );
}
