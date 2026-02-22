import React, { useEffect, useRef } from 'react';
import Swal from 'sweetalert2';

export default function VerifyEmailSentPage({ email, onNavigateToHome, onNavigateToSettings }) {
  const didShow = useRef(false);

  useEffect(() => {
    if (didShow.current) return;
    didShow.current = true;

    const emailDisplay = email || 'อีเมลของคุณ';
    const html = `
      <p style="color:#6366f1; font-weight:600; margin:0 0 1rem; word-break:break-all;">${emailDisplay}</p>
      <p style="color:#4b5563; margin:0 0 0.75rem; line-height:1.6;">
        เราได้ส่งลิงก์ยืนยันอีเมลไปที่กล่องจดหมายของคุณแล้ว<br/>
        กรุณาคลิกปุ่ม <strong>「ยืนยันอีเมล」</strong> ในอีเมลเพื่อดำเนินการต่อ
      </p>
      <p style="color:#9ca3af; font-size:0.9rem; margin:0;">ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam หรือ Junk</p>
    `;

    Swal.fire({
      icon: 'info',
      title: 'กรุณาตรวจสอบอีเมล',
      html,
      showConfirmButton: true,
      confirmButtonText: 'ตกลง',
      confirmButtonColor: '#6366f1',
      allowOutsideClick: true,
      allowEscapeKey: true,
    }).then(() => {
      onNavigateToSettings?.();
    });
  }, [email, onNavigateToHome, onNavigateToSettings]);

  return null;
}
