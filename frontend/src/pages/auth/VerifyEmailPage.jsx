import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
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
      Swal.fire({
        icon: 'error',
        title: 'ลิงก์ไม่ถูกต้อง',
        text: 'ลิงก์ยืนยันอีเมลไม่ถูกต้อง หรือไม่มี token กรุณาขอส่งอีเมลยืนยันใหม่',
        confirmButtonText: 'เข้าสู่ระบบ',
        confirmButtonColor: '#6366f1',
      }).then(() => onNavigateToLogin());
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
          const alreadyVerified = data.already_verified;
          setMessage(alreadyVerified ? 'อีเมลของคุณได้รับการยืนยันแล้ว' : 'ยืนยันอีเมลสำเร็จแล้ว คุณสามารถใช้งานได้ตามปกติ');
          await Swal.fire({
            icon: 'success',
            title: alreadyVerified ? 'อีเมลยืนยันแล้ว ✅' : 'ยืนยันอีเมลสำเร็จ! 🎉',
            html: alreadyVerified
              ? `<p style="color:#4b5563;margin:0 0 0.5rem;">อีเมลของคุณได้รับการยืนยันแล้ว</p>
                 <p style="color:#6366f1;font-weight:600;margin:0;">เข้าสู่ระบบได้เลยครับ!</p>`
              : `<p style="color:#4b5563;margin:0 0 0.5rem;">อีเมลของคุณได้รับการยืนยันเรียบร้อยแล้ว</p>
                 <p style="color:#6366f1;font-weight:600;margin:0;">พร้อมใช้งาน AI Travel Agent แล้ว!</p>`,
            confirmButtonText: 'เข้าสู่ระบบ',
            confirmButtonColor: '#6366f1',
            allowOutsideClick: false,
          });
          onNavigateToLogin();
        } else {
          const errMsg = typeof data.detail === 'string'
            ? data.detail
            : 'ลิงก์หมดอายุหรือไม่ถูกต้อง กรุณาขอส่งอีเมลยืนยันใหม่';
          setStatus('error');
          setMessage(errMsg);
          await Swal.fire({
            icon: 'error',
            title: 'ยืนยันอีเมลไม่สำเร็จ',
            html: `
              <p style="color:#4b5563;margin:0 0 8px;">${errMsg}</p>
              <p style="color:#9ca3af;font-size:13px;margin:0;">กรุณาเข้าสู่ระบบเพื่อขอลิงก์ยืนยันใหม่</p>
            `,
            confirmButtonText: 'เข้าสู่ระบบ',
            confirmButtonColor: '#6366f1',
          });
          onNavigateToLogin();
        }
      } catch (err) {
        const errMsg = 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง หรือขอส่งอีเมลยืนยันใหม่';
        setStatus('error');
        setMessage(errMsg);
        await Swal.fire({
          icon: 'error',
          title: 'เกิดข้อผิดพลาด',
          text: errMsg,
          confirmButtonText: 'เข้าสู่ระบบ',
          confirmButtonColor: '#6366f1',
        });
        onNavigateToLogin();
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
