import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import './VerifyEmailPage.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function VerifyEmailFirebasePage({ onNavigateToHome, onNavigateToLogin }) {
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oobCode = params.get('oobCode');
    const email = params.get('email');

    if (!oobCode) {
      setStatus('error');
      setMessage('ลิงก์ยืนยันอีเมลไม่ถูกต้อง กรุณาขอส่งอีเมลยืนยันใหม่');
      Swal.fire({
        icon: 'error',
        title: 'ลิงก์ไม่ถูกต้อง',
        text: 'ลิงก์ยืนยันอีเมลไม่ถูกต้อง กรุณาขอส่งอีเมลยืนยันใหม่',
        confirmButtonText: 'เข้าสู่ระบบ',
        confirmButtonColor: '#6366f1',
      }).then(() => onNavigateToLogin());
      return;
    }

    const verify = async () => {
      try {
        const { auth } = await import('../../config/firebase.js');
        const { applyActionCode } = await import('firebase/auth');

        if (!auth) {
          throw new Error('Firebase ไม่ได้ตั้งค่า');
        }

        await applyActionCode(auth, oobCode);

        // แจ้ง backend ให้ set email_verified=True ใน MongoDB
        const res = await fetch(
          `${API_BASE_URL}/api/auth/verify-email-firebase`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email }),
          }
        );
        const data = await res.json().catch(() => ({}));

        // Firebase verify สำเร็จ → ถือว่า OK เสมอ (backend อาจ fail ได้บ้าง)
        setStatus('success');
        setMessage('ยืนยันอีเมลสำเร็จแล้ว คุณสามารถเข้าสู่ระบบได้ตามปกติ');
        await Swal.fire({
          icon: 'success',
          title: 'ยืนยันอีเมลสำเร็จ! 🎉',
          html: `
            <p style="color:#4b5563;margin:0 0 0.5rem;">อีเมลของคุณได้รับการยืนยันเรียบร้อยแล้ว</p>
            <p style="color:#6366f1;font-weight:600;margin:0;">พร้อมใช้งาน AI Travel Agent แล้ว!</p>
          `,
          confirmButtonText: 'เข้าสู่ระบบ',
          confirmButtonColor: '#6366f1',
          allowOutsideClick: false,
        });
        onNavigateToLogin();
      } catch (err) {
        const code = err?.code || '';
        let errMsg = 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือขอส่งอีเมลยืนยันใหม่';
        if (code === 'auth/invalid-action-code' || code === 'auth/expired-action-code') {
          errMsg = 'ลิงก์ยืนยันหมดอายุหรือถูกใช้ไปแล้ว กรุณาขอส่งอีเมลยืนยันใหม่';
        }
        setStatus('error');
        setMessage(errMsg);
        Swal.fire({
          icon: 'error',
          title: 'ยืนยันอีเมลไม่สำเร็จ',
          text: errMsg,
          confirmButtonText: 'เข้าสู่ระบบ',
          confirmButtonColor: '#6366f1',
        }).then(() => onNavigateToLogin());
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
              <button className="btn-primary" onClick={onNavigateToLogin}>
                เข้าสู่ระบบ
              </button>
              <button className="btn-secondary" onClick={onNavigateToHome}>
                ไปหน้าแรก
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
              <button className="btn-primary" onClick={onNavigateToLogin}>
                เข้าสู่ระบบ
              </button>
              <button className="btn-secondary" onClick={onNavigateToHome}>
                ไปหน้าแรก
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
