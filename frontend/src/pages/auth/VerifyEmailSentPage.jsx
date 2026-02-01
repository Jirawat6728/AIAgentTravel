import React from 'react';
import './VerifyEmailSentPage.css';

export default function VerifyEmailSentPage({ email, onNavigateToHome, onNavigateToSettings }) {
  return (
    <div className="verify-email-sent-container">
      <div className="verify-email-sent-card">
        <div className="verify-email-sent-icon">✉️</div>
        <h1>กรุณาตรวจสอบอีเมล</h1>
        <p className="verify-email-sent-email">{email || 'อีเมลของคุณ'}</p>
        <p className="verify-email-sent-desc">
          เราได้ส่งลิงก์ยืนยันอีเมลไปที่กล่องจดหมายของคุณแล้ว
          <br />
          กรุณาคลิกปุ่ม <strong>「ยืนยันอีเมล」</strong> ในอีเมลเพื่อดำเนินการต่อ
        </p>
        <p className="verify-email-sent-note">
          ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam หรือ Junk
        </p>
        <div className="verify-email-sent-actions">
          <button className="btn-primary" onClick={onNavigateToHome}>
            ไปหน้าแรก
          </button>
          <button className="btn-secondary" onClick={onNavigateToSettings}>
            กลับไปการตั้งค่า
          </button>
        </div>
      </div>
    </div>
  );
}
