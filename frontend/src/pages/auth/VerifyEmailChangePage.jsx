import React, { useState, useEffect } from 'react';
import './VerifyEmailPage.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VerifyEmailChangePage({ onNavigateToHome, onNavigateToSettings }) {
  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [message, setMessage] = useState('');
  const [newEmail, setNewEmail] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (!token) {
      setStatus('error');
      setMessage('ลิงก์ยืนยันการเปลี่ยนอีเมลไม่ถูกต้อง หรือไม่มี token กรุณาขอส่งลิงก์ใหม่จากหน้าตั้งค่า');
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/auth/verify-email-change?token=${encodeURIComponent(token)}`,
          { method: 'POST', credentials: 'include' }
        );
        const data = await res.json();

        if (res.ok && data.ok) {
          setStatus('success');
          setMessage(data.message || 'เปลี่ยนอีเมลและยืนยันสำเร็จ');
          if (data.email) setNewEmail(data.email);
        } else {
          setStatus('error');
          setMessage(data.detail || 'ลิงก์หมดอายุหรือไม่ถูกต้อง กรุณาขอส่งลิงก์ใหม่จากหน้าตั้งค่า');
        }
      } catch (err) {
        setStatus('error');
        setMessage('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือขอส่งลิงก์ใหม่จากหน้าตั้งค่า');
      }
    };

    verify();
  }, []);

  return (
    <div className="verify-email-container">
      <div className="verify-email-card">
        {status === 'loading' && (
          <>
            <div className="verify-email-icon verify-email-icon-loading">⏳</div>
            <h1>กำลังยืนยันการเปลี่ยนอีเมล...</h1>
            <p>กรุณารอสักครู่</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="verify-email-icon verify-email-icon-success">✓</div>
            <h1>เปลี่ยนอีเมลสำเร็จ</h1>
            <p>{message}</p>
            {newEmail && <p className="verify-email-new-email">อีเมลใหม่: <strong>{newEmail}</strong></p>}
            <div className="verify-email-actions">
              <button className="btn-primary" onClick={onNavigateToHome}>
                ไปหน้าแรก
              </button>
              <button className="btn-secondary" onClick={onNavigateToSettings}>
                ตั้งค่า
              </button>
            </div>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="verify-email-icon verify-email-icon-error">✕</div>
            <h1>ยืนยันการเปลี่ยนอีเมลไม่สำเร็จ</h1>
            <p>{message}</p>
            <div className="verify-email-actions">
              <button className="btn-primary" onClick={onNavigateToHome}>
                ไปหน้าแรก
              </button>
              <button className="btn-secondary" onClick={onNavigateToSettings}>
                ไปตั้งค่า
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
