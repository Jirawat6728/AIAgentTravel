import React, { useState, useEffect } from 'react';
import './VerifyEmailPage.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VerifyEmailPage({ onNavigateToHome, onNavigateToLogin }) {
  const [status, setStatus] = useState('loading'); // 'loading' | 'success' | 'error'
  const [message, setMessage] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('token');

    if (!token) {
      setStatus('error');
      setMessage('ลิงก์ยืนยันอีเมลไม่ถูกต้อง หรือไม่มี token กรุณาขอส่งอีเมลยืนยันใหม่');
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch(
          `${API_BASE_URL}/api/auth/verify-email?token=${encodeURIComponent(token)}`,
          { method: 'POST', credentials: 'include' }
        );
        const data = await res.json();

        if (res.ok && data.ok) {
          setStatus('success');
          setMessage('ยืนยันอีเมลสำเร็จแล้ว คุณสามารถใช้งานได้ตามปกติ');
        } else {
          setStatus('error');
          setMessage(data.detail || 'ลิงก์หมดอายุหรือไม่ถูกต้อง กรุณาขอส่งอีเมลยืนยันใหม่');
        }
      } catch (err) {
        setStatus('error');
        setMessage('เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือขอส่งอีเมลยืนยันใหม่');
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
            <h1>กำลังยืนยันอีเมล...</h1>
            <p>กรุณารอสักครู่</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="verify-email-icon verify-email-icon-success">✓</div>
            <h1>ยืนยันอีเมลสำเร็จ</h1>
            <p>{message}</p>
            <div className="verify-email-actions">
              <button className="btn-primary" onClick={onNavigateToHome}>
                ไปหน้าแรก
              </button>
              <button className="btn-secondary" onClick={onNavigateToLogin}>
                เข้าสู่ระบบ
              </button>
            </div>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="verify-email-icon verify-email-icon-error">✕</div>
            <h1>ยืนยันอีเมลไม่สำเร็จ</h1>
            <p>{message}</p>
            <div className="verify-email-actions">
              <button className="btn-primary" onClick={onNavigateToHome}>
                ไปหน้าแรก
              </button>
              <button className="btn-secondary" onClick={onNavigateToLogin}>
                เข้าสู่ระบบ
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
