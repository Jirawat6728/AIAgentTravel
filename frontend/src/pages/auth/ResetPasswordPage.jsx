import React, { useState } from 'react';
import './ResetPasswordPage.css';
import { sha256Password } from '../../utils/passwordHash.js';
import Swal from 'sweetalert2';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export default function ResetPasswordPage({ onNavigateToLogin, onNavigateToHome, onNavigateToRegister }) {
  const [email, setEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [lang, setLang] = useState('th');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingUser, setIsLoadingUser] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [userInfo, setUserInfo] = useState(null);
  const [step, setStep] = useState('email'); // 'email' | 'otp'
  const [otp, setOtp] = useState('');
  const [otpError, setOtpError] = useState('');
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, feedback: [] });

  const calculatePasswordStrength = (password) => {
    let score = 0;
    const feedback = [];
    if (password.length >= 8) score++; else feedback.push(lang === 'th' ? 'อย่างน้อย 8 ตัวอักษร' : 'At least 8 characters');
    if (/[A-Z]/.test(password)) score++; else feedback.push(lang === 'th' ? 'ตัวพิมพ์ใหญ่ (A-Z)' : 'Uppercase (A-Z)');
    if (/[a-z]/.test(password)) score++; else feedback.push(lang === 'th' ? 'ตัวพิมพ์เล็ก (a-z)' : 'Lowercase (a-z)');
    if (/\d/.test(password)) score++; else feedback.push(lang === 'th' ? 'ตัวเลข (0-9)' : 'Number (0-9)');
    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++; else feedback.push(lang === 'th' ? 'อักขระพิเศษ (!@#$...)' : 'Special char (!@#$...)');
    return { score, feedback };
  };

  const strengthColors = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#22c55e'];
  const strengthLabels = lang === 'th'
    ? ['อ่อนแอมาก', 'อ่อนแอ', 'พอใช้', 'ดี', 'แข็งแกร่ง']
    : ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

  const validate = () => {
    const newErrors = {};
    
    if (step === 'email') {
      if (!email.trim()) {
        newErrors.email = lang === 'th' ? 'กรุณากรอกอีเมล' : 'Email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        newErrors.email = lang === 'th' ? 'รูปแบบอีเมลไม่ถูกต้อง' : 'Invalid email format';
      }
    } else if (step === 'otp') {
      if (!newPassword) {
        newErrors.newPassword = lang === 'th' ? 'กรุณากรอกรหัสผ่านใหม่' : 'New password is required';
      } else if (newPassword.length < 8) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร' : 'Password must be at least 8 characters';
      } else if (!/[A-Z]/.test(newPassword)) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว' : 'Password must have at least one uppercase letter';
      } else if (!/[a-z]/.test(newPassword)) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว' : 'Password must have at least one lowercase letter';
      } else if (!/\d/.test(newPassword)) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว' : 'Password must have at least one number';
      } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(newPassword)) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว (!@#$...)' : 'Password must have at least one special character (!@#$...)';
      }
      if (!confirmPassword) {
        newErrors.confirmPassword = lang === 'th' ? 'กรุณายืนยันรหัสผ่าน' : 'Please confirm password';
      } else if (newPassword !== confirmPassword) {
        newErrors.confirmPassword = lang === 'th' ? 'รหัสผ่านไม่ตรงกัน' : 'Passwords do not match';
      }
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'email') {
      setEmail(value);
      // Clear email error when user starts typing
      if (errors.email || errors.general) {
        setErrors(prev => ({
          ...prev,
          email: '',
          general: ''
        }));
      }
    } else if (name === 'newPassword') {
      setNewPassword(value);
      setPasswordStrength(calculatePasswordStrength(value));
      if (confirmPassword && confirmPassword !== value) {
        setErrors(prev => ({ ...prev, confirmPassword: lang === 'th' ? 'รหัสผ่านไม่ตรงกัน' : 'Passwords do not match' }));
      } else if (confirmPassword) {
        setErrors(prev => ({ ...prev, confirmPassword: '' }));
      }
    } else if (name === 'confirmPassword') {
      setConfirmPassword(value);
    }
    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  // SweetAlert OTP dialog เหมือนเปลี่ยนอีเมล/ยืนยันอีเมล — เมื่อกรอก OTP ถูกไปหน้าเปลี่ยนรหัสผ่าน
  const showResetPasswordOtpDialog = async (emailToUse) => {
    const buildHTML = (err = '') => `
      <p style="color:#6366f1;font-weight:600;font-size:14px;margin:0 0 16px;word-break:break-all;">${emailToUse}</p>
      <p style="color:#4b5563;font-size:14px;margin:0 0 16px;line-height:1.6;">
        เราได้ส่งรหัส OTP 6 หลักไปที่อีเมลของคุณแล้ว<br>
        <span style="color:#9ca3af;font-size:12px;">ไม่พบอีเมล? ตรวจสอบโฟลเดอร์ Spam</span>
      </p>
      <div id="reset-otp-inputs" style="display:flex;gap:8px;justify-content:center;margin:0 0 8px;">
        ${[0, 1, 2, 3, 4, 5].map((i) => `
          <input id="reset-otp-${i}" type="text" inputmode="numeric" maxlength="1"
            style="width:44px;height:52px;text-align:center;font-size:24px;font-weight:700;
                   border:2px solid ${err ? '#ef4444' : '#a5b4fc'};border-radius:10px;
                   color:#4f46e5;background:#f5f3ff;outline:none;" />`).join('')}
      </div>
      ${err ? `<p style="color:#ef4444;font-size:13px;margin:4px 0 0;">${err}</p>` : ''}
      <p id="reset-otp-countdown-wrap" style="color:#f59e0b;font-size:12px;margin:12px 0 0;display:flex;align-items:center;justify-content:center;gap:8px;flex-wrap:wrap;">
        <span>⏰ รหัสหมดอายุใน <strong id="reset-otp-countdown-text">4:00</strong></span>
        <button id="reset-otp-resend-btn" type="button" style="display:none;background:#6366f1;color:#fff;border:none;border-radius:6px;padding:3px 10px;font-size:11px;cursor:pointer;font-weight:600;">ขอรหัสใหม่</button>
      </p>
    `;

    let countdownTimer = null;
    let isExpired = false;

    const startCountdown = () => {
      // clear timer เดิมก่อนเสมอ
      if (countdownTimer) clearInterval(countdownTimer);
      countdownTimer = null;
      isExpired = false;
      // reset ปุ่มยืนยัน
      const confirmBtn = document.querySelector('.swal2-confirm');
      if (confirmBtn) confirmBtn.disabled = false;

      const expiryAt = Date.now() + 4 * 60 * 1000; // 4 นาที
      const update = () => {
        const el = document.getElementById('reset-otp-countdown-text');
        const wrap = document.getElementById('reset-otp-countdown-wrap');
        if (!el) return;
        const remaining = Math.max(0, Math.ceil((expiryAt - Date.now()) / 1000));
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        el.textContent = `${mins}:${String(secs).padStart(2, '0')}`;
        if (remaining <= 0) {
          if (countdownTimer) clearInterval(countdownTimer);
          countdownTimer = null;
          isExpired = true;
          if (wrap) {
            wrap.style.color = '#ef4444';
            wrap.innerHTML = '⏰ <strong>' + (lang === 'th' ? 'รหัสหมดอายุแล้ว กรุณาขอรหัสใหม่' : 'Code expired. Please request a new code.') + '</strong>';
          }
          // ปิดปุ่มยืนยันเมื่อหมดเวลา
          const btn = document.querySelector('.swal2-confirm');
          if (btn) btn.disabled = true;
          // แสดงปุ่มขอรหัสใหม่
          const resendBtn = document.getElementById('reset-otp-resend-btn');
          if (resendBtn) resendBtn.style.display = 'inline-block';
        }
      };
      update();
      countdownTimer = setInterval(update, 1000);
    };

    const doResend = async () => {
      const resendBtn = document.getElementById('reset-otp-resend-btn');
      if (resendBtn) { resendBtn.disabled = true; resendBtn.textContent = 'กำลังส่ง...'; }
      try {
        await fetch(`${API_BASE_URL}/api/auth/send-reset-password-otp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email: emailToUse }),
        });
      } catch (_) { /* ignore */ }
      for (let i = 0; i < 6; i++) {
        const inp = document.getElementById(`reset-otp-${i}`);
        if (inp) inp.value = '';
      }
      if (resendBtn) resendBtn.style.display = 'none';
      document.getElementById('reset-otp-0')?.focus();
      startCountdown();
    };

    const setupInputs = () => {
      for (let i = 0; i < 6; i++) {
        const el = document.getElementById(`reset-otp-${i}`);
        if (!el) continue;
        el.addEventListener('input', (e) => {
          e.target.value = e.target.value.replace(/\D/g, '').slice(0, 1);
          if (e.target.value && i < 5) document.getElementById(`reset-otp-${i + 1}`)?.focus();
        });
        el.addEventListener('keydown', (e) => {
          if (e.key === 'Backspace' && !e.target.value && i > 0) document.getElementById(`reset-otp-${i - 1}`)?.focus();
        });
        el.addEventListener('paste', (e) => {
          e.preventDefault();
          const pasted = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, 6);
          pasted.split('').forEach((ch, j) => {
            const inp = document.getElementById(`reset-otp-${j}`);
            if (inp) inp.value = ch;
          });
          document.getElementById(`reset-otp-${Math.min(pasted.length, 5)}`)?.focus();
        });
      }
      document.getElementById('reset-otp-0')?.focus();
      document.getElementById('reset-otp-resend-btn')?.addEventListener('click', doResend);
      startCountdown();
    };

    while (true) {
      const result = await Swal.fire({
        title: lang === 'th' ? 'กรอกรหัส OTP 📧' : 'Enter OTP 📧',
        html: buildHTML(),
        showCancelButton: true,
        confirmButtonText: lang === 'th' ? 'ยืนยัน' : 'Confirm',
        confirmButtonColor: '#6366f1',
        cancelButtonText: lang === 'th' ? 'ยกเลิก' : 'Cancel',
        cancelButtonColor: '#e5e7eb',
        allowOutsideClick: false,
        focusConfirm: false,
        didOpen: setupInputs,
        didClose: () => {
          if (countdownTimer) clearInterval(countdownTimer);
          countdownTimer = null;
        },
        preConfirm: () => {
          if (isExpired) {
            Swal.showValidationMessage(lang === 'th' ? 'รหัส OTP หมดอายุแล้ว กรุณากดขอรหัสใหม่' : 'OTP expired. Please request a new code.');
            return false;
          }
          const otpValue = Array.from({ length: 6 }, (_, i) => document.getElementById(`reset-otp-${i}`)?.value || '').join('');
          if (otpValue.length < 6 || /\D/.test(otpValue)) {
            Swal.showValidationMessage(lang === 'th' ? 'กรุณากรอกรหัส OTP ให้ครบ 6 หลัก' : 'Please enter all 6 digits');
            return false;
          }
          return otpValue;
        },
      });

      if (!result.isConfirmed) return null;

      try {
        const res = await fetch(`${API_BASE_URL}/api/auth/verify-reset-password-otp`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ email: emailToUse, otp: result.value }),
        });
        const data = await res.json().catch(() => ({}));

        if (res.ok && data.ok) {
          await Swal.fire({
            icon: 'success',
            title: lang === 'th' ? 'รหัส OTP ถูกต้อง ✅' : 'OTP verified ✅',
            text: lang === 'th' ? 'กรุณาตั้งรหัสผ่านใหม่ด้านล่าง' : 'Please set your new password below.',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#6366f1',
          });
          return result.value;
        }

        const errMsg = typeof data.detail === 'string' ? data.detail : (lang === 'th' ? 'รหัส OTP ไม่ถูกต้อง' : 'Invalid OTP');
        const errResult = await Swal.fire({
          icon: 'error',
          title: lang === 'th' ? 'OTP ไม่ถูกต้อง' : 'Invalid OTP',
          html: `<p style="color:#4b5563;margin:0 0 4px;">${errMsg}</p>
                 <p style="color:#9ca3af;font-size:12px;margin:0;">${lang === 'th' ? 'กรุณาตรวจสอบอีเมลและกรอกรหัสใหม่' : 'Please check your email and try again.'}</p>`,
          confirmButtonText: lang === 'th' ? 'ลองใหม่' : 'Try again',
          confirmButtonColor: '#6366f1',
          showDenyButton: true,
          denyButtonText: lang === 'th' ? 'ขอรหัสใหม่' : 'Resend OTP',
          denyButtonColor: '#e5e7eb',
        });
        if (errResult.isDenied) {
          await fetch(`${API_BASE_URL}/api/auth/send-reset-password-otp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'include',
            body: JSON.stringify({ email: emailToUse }),
          });
          await Swal.fire({
            icon: 'info',
            title: lang === 'th' ? 'ส่ง OTP ใหม่แล้ว' : 'OTP resent',
            text: lang === 'th' ? 'กรุณาตรวจสอบอีเมลและกรอกรหัสใหม่' : 'Please check your email.',
            confirmButtonText: 'ตกลง',
            confirmButtonColor: '#6366f1',
          });
        }
      } catch {
        await Swal.fire({
          icon: 'error',
          title: lang === 'th' ? 'เกิดข้อผิดพลาด' : 'Error',
          text: lang === 'th' ? 'ไม่สามารถเชื่อมต่อได้ กรุณาลองใหม่' : 'Connection error. Please try again.',
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#6366f1',
        });
        return null;
      }
    }
  };

  const handleCheckEmail = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoadingUser(true);
    setErrors({});
    setSuccessMessage('');
    setOtpError('');
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/send-reset-password-otp`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ email: email.trim() })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const errorMessage = data.detail || data.message || (lang === 'th' ? 'ไม่พบผู้ใช้ในระบบ' : 'User not found');
        throw new Error(errorMessage);
      }
      const emailToUse = data.email || email.trim();
      const otpValue = await showResetPasswordOtpDialog(emailToUse);
      if (otpValue != null) {
        setStep('otp');
        setOtp(otpValue);
      }
    } catch (error) {
      console.error('Send reset password OTP error:', error);
      setErrors({
        general: error.message,
        email: lang === 'th'
          ? 'อีเมลนี้ไม่มีในระบบ กรุณาตรวจสอบหรือสมัครสมาชิกใหม่'
          : 'This email is not registered. Please check or register a new account.'
      });
    } finally {
      setIsLoadingUser(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    if (!validate()) return;

    setIsLoading(true);
    setErrors({});
    setOtpError('');
    setSuccessMessage('');
    try {
      const newPasswordHash = await sha256Password(newPassword);
      const res = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Password-Encoding': 'sha256',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: email.trim(),
          new_password: newPasswordHash,
          otp: otp.trim()
        })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = data.detail || data.message || 'Failed to reset password';
        if (msg.includes('OTP')) setOtpError(msg);
        throw new Error(msg);
      }
      setSuccessMessage(
        lang === 'th'
          ? `เปลี่ยนรหัสผ่านสำเร็จแล้ว${data.backup_created ? ' (ได้ทำการ backup รหัสผ่านเดิมไว้แล้ว)' : ''}`
          : `Password reset successfully${data.backup_created ? ' (old password has been backed up)' : ''}`
      );
      setNewPassword('');
      setConfirmPassword('');
      setOtp('');
      setStep('email');
      setUserInfo(null);
    } catch (error) {
      console.error('Reset password error:', error);
      setErrors({
        general: lang === 'th'
          ? error.message || 'เกิดข้อผิดพลาด กรุณาลองใหม่อีกครั้ง'
          : error.message || 'An error occurred. Please try again.'
      });
    } finally {
      setIsLoading(false);
    }
  };

  const text = {
    en: {
      title: 'Reset Password',
      subtitle: 'Enter your email to check and reset password.',
      email: 'Email',
      checkBtn: 'Check Email',
      otpSent: 'We sent a 6-digit OTP to your email. Enter it below.',
      otpLabel: 'OTP Code',
      newPassword: 'New Password',
      confirmPassword: 'Confirm Password',
      resetBtn: 'Reset Password',
      backToLogin: 'Back to Login',
      backToEmail: 'Back to Email',
      success: 'Password reset successfully!',
    },
    th: {
      title: 'รีเซ็ตรหัสผ่าน',
      subtitle: 'กรอกอีเมลของคุณเพื่อตรวจสอบและเปลี่ยนรหัสผ่าน',
      email: 'อีเมล',
      checkBtn: 'ตรวจสอบอีเมล',
      otpSent: 'ส่งรหัส OTP 6 หลักไปที่อีเมลของคุณแล้ว กรุณากรอกรหัสด้านล่าง',
      otpLabel: 'รหัส OTP',
      newPassword: 'รหัสผ่านใหม่',
      confirmPassword: 'ยืนยันรหัสผ่าน',
      resetBtn: 'เปลี่ยนรหัสผ่าน',
      backToLogin: 'กลับไปหน้าเข้าสู่ระบบ',
      backToEmail: 'กลับไปกรอกอีเมล',
      success: 'เปลี่ยนรหัสผ่านสำเร็จ!',
    },
  };

  return (
    <div className="login-container">
      {/* Transparent Header with Logo */}
      <header className="login-transparent-header">
        <div className="header-logo" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <img src="/favicon.svg" alt="" className="login-logo-img" aria-hidden="true" />
          <span className="header-logo-text">AITravelAgent</span>
        </div>
      </header>

      <main className="login-main">
        {/* Main Card Container */}
        <div className="login-card-wrapper">
          {/* Left Side - Image */}
          <div className="login-image-section">
            <div className="login-image-container">
              <img 
                src="/1949136.jpg" 
                alt="Travel Illustration" 
                className="login-illustration"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
              <div className="login-illustration-placeholder" style={{ display: 'none' }}>
                <svg viewBox="0 0 400 300" className="placeholder-svg">
                  <circle cx="100" cy="150" r="40" fill="#fbbf24" opacity="0.3"/>
                  <circle cx="200" cy="150" r="40" fill="#3b82f6" opacity="0.3"/>
                  <circle cx="300" cy="150" r="40" fill="#ec4899" opacity="0.3"/>
                </svg>
              </div>
            </div>
          </div>

          {/* Right Side - Form Section */}
          <div className="login-form-section">
            <div className="login-card">
              <h2 className="login-title">{text[lang].title}</h2>
              <p className="login-subtitle">
                {successMessage ? text[lang].success : text[lang].subtitle}
              </p>

              {successMessage ? (
                <div className="form-content">
                  <div className="success-message" style={{ color: '#10b981', textAlign: 'center', padding: '1rem', background: '#ecfdf5', borderRadius: '0.5rem' }}>
                    {successMessage}
                  </div>
                  <button type="button" className="btn-login" onClick={onNavigateToLogin}>
                    {text[lang].backToLogin}
                  </button>
                </div>
              ) : step === 'otp' ? (
                <form onSubmit={handleResetPassword} className="form-content">
                  <div className="form-group">
                    <label htmlFor="newPassword" className="form-label">{text[lang].newPassword}</label>
                    <div className="password-input-wrapper">
                      <input
                        type={showNewPassword ? 'text' : 'password'}
                        id="newPassword"
                        name="newPassword"
                        value={newPassword}
                        onChange={handleChange}
                        placeholder={text[lang].newPassword}
                        className={`form-input has-toggle ${errors.newPassword ? 'error' : passwordStrength.score === 5 ? 'valid' : ''}`}
                        autoComplete="new-password"
                      />
                      <button type="button" className="toggle-password" onClick={() => setShowNewPassword(v => !v)} aria-label={showNewPassword ? 'Hide' : 'Show'}>
                        {showNewPassword ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M10.94 6.08A6.93 6.93 0 0 1 12 6c3.18 0 6.17 2.29 7.91 6a15.23 15.23 0 0 1-.9 1.64 1 1 0 0 1-1.7-.3 1 1 0 0 0-1.72-1.04 6 6 0 0 0-1.54-1.54 1 1 0 0 0-1.72 1.04 1 1 0 0 1-1.7.3 7.12 7.12 0 0 1-1.9-1.9 1 1 0 0 0-1.72-1.04ZM3.71 2.29a1 1 0 0 0-1.42 1.42l3.1 3.09a14.62 14.62 0 0 0-3.31 4.8 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 5.05-1.54l3.24 3.25a1 1 0 0 0 1.42-1.42Zm6.36 9.19 2.45 2.45A1.81 1.81 0 0 1 12 14a2 2 0 0 1-2-2 1.81 1.81 0 0 1 .07-.52Z" fill="currentColor"/></svg>
                        ) : (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 8a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-15.5C7 1.5 2.73 4.61 1 9c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 4.61 17 1.5 12 1.5Z" fill="currentColor"/></svg>
                        )}
                      </button>
                    </div>
                    {errors.newPassword && <span className="error-message">{errors.newPassword}</span>}
                    {newPassword && (
                      <div className="password-strength" style={{ marginTop: '8px' }}>
                        <div className="strength-bar">
                          <div
                            className="strength-fill"
                            style={{
                              width: `${(passwordStrength.score / 5) * 100}%`,
                              background: strengthColors[passwordStrength.score - 1] || '#e5e7eb',
                              height: '4px', borderRadius: '2px', transition: 'width 0.3s, background 0.3s'
                            }}
                          />
                        </div>
                        <div className="strength-text" style={{ fontSize: '12px', marginTop: '4px', color: '#6b7280', display: 'flex', justifyContent: 'space-between' }}>
                          <span>{lang === 'th' ? 'ความแข็งแกร่ง: ' : 'Strength: '}
                            <span style={{ color: strengthColors[passwordStrength.score - 1] || '#9ca3af', fontWeight: 600 }}>
                              {passwordStrength.score > 0 ? strengthLabels[passwordStrength.score - 1] : (lang === 'th' ? 'อ่อนแาก' : 'Very Weak')}
                            </span>
                          </span>
                        </div>
                        {passwordStrength.feedback.length > 0 && (
                          <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
                            {lang === 'th' ? 'ต้องมี: ' : 'Requires: '}{passwordStrength.feedback.join(', ')}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="form-group">
                    <label htmlFor="confirmPassword" className="form-label">{text[lang].confirmPassword}</label>
                    <div className="password-input-wrapper">
                      <input
                        type={showConfirmPassword ? 'text' : 'password'}
                        id="confirmPassword"
                        name="confirmPassword"
                        value={confirmPassword}
                        onChange={handleChange}
                        placeholder={text[lang].confirmPassword}
                        className={`form-input has-toggle ${errors.confirmPassword ? 'error' : confirmPassword && newPassword === confirmPassword ? 'valid' : ''}`}
                        autoComplete="new-password"
                      />
                      <button type="button" className="toggle-password" onClick={() => setShowConfirmPassword(v => !v)} aria-label={showConfirmPassword ? 'Hide' : 'Show'}>
                        {showConfirmPassword ? (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M10.94 6.08A6.93 6.93 0 0 1 12 6c3.18 0 6.17 2.29 7.91 6a15.23 15.23 0 0 1-.9 1.64 1 1 0 0 1-1.7-.3 1 1 0 0 0-1.72-1.04 6 6 0 0 0-1.54-1.54 1 1 0 0 0-1.72 1.04 1 1 0 0 1-1.7.3 7.12 7.12 0 0 1-1.9-1.9 1 1 0 0 0-1.72-1.04ZM3.71 2.29a1 1 0 0 0-1.42 1.42l3.1 3.09a14.62 14.62 0 0 0-3.31 4.8 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 5.05-1.54l3.24 3.25a1 1 0 0 0 1.42-1.42Zm6.36 9.19 2.45 2.45A1.81 1.81 0 0 1 12 14a2 2 0 0 1-2-2 1.81 1.81 0 0 1 .07-.52Z" fill="currentColor"/></svg>
                        ) : (
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 8a5 5 0 1 1 0-10 5 5 0 0 1 0 10Zm0-15.5C7 1.5 2.73 4.61 1 9c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5C21.27 4.61 17 1.5 12 1.5Z" fill="currentColor"/></svg>
                        )}
                      </button>
                    </div>
                    {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
                  </div>
                  {errors.general && (
                    <div className="error-message" style={{ textAlign: 'center', marginBottom: '0.5rem' }}>
                      {errors.general}
                    </div>
                  )}
                  <button type="submit" className="btn-login" disabled={isLoading}>
                    {isLoading ? (lang === 'th' ? 'กำลังเปลี่ยนรหัสผ่าน...' : 'Resetting...') : text[lang].resetBtn}
                  </button>
                  <div className="register-link">
                    <button
                      type="button"
                      onClick={() => {
                        setStep('email');
                        setOtp('');
                        setOtpError('');
                        setNewPassword('');
                        setConfirmPassword('');
                        setErrors({});
                      }}
                      className="link-button"
                    >
                      {text[lang].backToEmail}
                    </button>
                  </div>
                </form>
              ) : step === 'email' ? (
                <form onSubmit={handleCheckEmail} className="form-content">
                  {/* Email */}
                  <div className="form-group">
                    <label htmlFor="email" className="form-label">{text[lang].email}</label>
                    <input
                      type="email"
                      id="email"
                      name="email"
                      value={email}
                      onChange={handleChange}
                      placeholder={text[lang].email}
                      className={`form-input ${errors.email ? 'error' : ''}`}
                      autoComplete="email"
                    />
                    {errors.email && <span className="error-message">{errors.email}</span>}
                  </div>

                  {errors.general && (
                    <div style={{ 
                      textAlign: 'center', 
                      padding: '1rem',
                      background: '#fef2f2',
                      border: '1px solid #fecaca',
                      borderRadius: '0.5rem',
                      color: '#dc2626',
                      marginBottom: '1rem'
                    }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        {errors.general}
                      </div>
                      {errors.email && (
                        <div style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
                          {errors.email}
                        </div>
                      )}
                      {onNavigateToRegister && (
                        <div style={{ marginTop: '1rem' }}>
                          <button 
                            type="button" 
                            onClick={onNavigateToRegister}
                            style={{
                              background: 'transparent',
                              border: 'none',
                              color: '#3b82f6',
                              textDecoration: 'underline',
                              cursor: 'pointer',
                              fontSize: '0.9rem'
                            }}
                          >
                            {lang === 'th' ? 'สมัครสมาชิกใหม่' : 'Register new account'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Submit Button */}
                  <button type="submit" className="btn-login" disabled={isLoadingUser}>
                    {isLoadingUser ? (lang === 'th' ? 'กำลังตรวจสอบ...' : 'Checking...') : text[lang].checkBtn}
                  </button>

                  {/* Back to Login Link */}
                  <div className="register-link">
                    <button type="button" onClick={onNavigateToLogin} className="link-button">
                      {text[lang].backToLogin}
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}