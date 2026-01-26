import React, { useState } from 'react';
import './ResetPasswordPage.css';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

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
  const [step, setStep] = useState('email'); // 'email' or 'password'

  const validate = () => {
    const newErrors = {};
    
    if (step === 'email') {
      if (!email.trim()) {
        newErrors.email = lang === 'th' ? 'กรุณากรอกอีเมล' : 'Email is required';
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        newErrors.email = lang === 'th' ? 'รูปแบบอีเมลไม่ถูกต้อง' : 'Invalid email format';
      }
    } else if (step === 'password') {
      if (!newPassword.trim()) {
        newErrors.newPassword = lang === 'th' ? 'กรุณากรอกรหัสผ่านใหม่' : 'New password is required';
      } else if (newPassword.length < 6) {
        newErrors.newPassword = lang === 'th' ? 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร' : 'Password must be at least 6 characters';
      }
      
      if (!confirmPassword.trim()) {
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

  const handleCheckEmail = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsLoadingUser(true);
    setErrors({});
    setSuccessMessage('');
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/reset-password/${encodeURIComponent(email)}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'User not found' }));
        const errorMessage = errorData.detail || errorData.message || 'User not found';
        throw new Error(errorMessage);
      }
      
      const data = await res.json();
      setUserInfo(data);
      setStep('password');
      
    } catch (error) {
      console.error('Check email error:', error);
      const errorMsg = error.message || (lang === 'th' ? 'ไม่พบผู้ใช้ในระบบ' : 'User not found');
      setErrors({
        general: errorMsg,
        email: lang === 'th' 
          ? 'อีเมลนี้ไม่มีในระบบ กรุณาตรวจสอบหรือสมัครสมาชิกใหม่'
          : 'This email is not registered. Please check or register a new account.'
      });
      // ✅ Set email error to show red border (same as password error)
      // This will trigger the error class on the email input field
    } finally {
      setIsLoadingUser(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsLoading(true);
    setErrors({});
    setSuccessMessage('');
    
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          email: email,
          new_password: newPassword
        })
      });
      
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || 'Failed to reset password');
      }
      
      const data = await res.json();
      setSuccessMessage(
        lang === 'th' 
          ? `เปลี่ยนรหัสผ่านสำเร็จแล้ว${data.backup_created ? ' (ได้ทำการ backup รหัสผ่านเดิมไว้แล้ว)' : ''}` 
          : `Password reset successfully${data.backup_created ? ' (old password has been backed up)' : ''}`
      );
      
      // Reset form
      setNewPassword('');
      setConfirmPassword('');
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
      passwordStatus: 'Password Status',
      hasPassword: 'Has password set',
      noPassword: 'No password set',
      newPassword: 'New Password',
      confirmPassword: 'Confirm Password',
      resetBtn: 'Reset Password',
      backToLogin: 'Back to Login',
      backToEmail: 'Back to Email',
      success: 'Password reset successfully!',
      userInfo: 'User Information',
    },
    th: {
      title: 'รีเซ็ตรหัสผ่าน',
      subtitle: 'กรอกอีเมลของคุณเพื่อตรวจสอบและเปลี่ยนรหัสผ่าน',
      email: 'อีเมล',
      checkBtn: 'ตรวจสอบอีเมล',
      passwordStatus: 'สถานะรหัสผ่าน',
      hasPassword: 'มีรหัสผ่านอยู่แล้ว',
      noPassword: 'ยังไม่มีรหัสผ่าน',
      newPassword: 'รหัสผ่านใหม่',
      confirmPassword: 'ยืนยันรหัสผ่าน',
      resetBtn: 'เปลี่ยนรหัสผ่าน',
      backToLogin: 'กลับไปหน้าเข้าสู่ระบบ',
      backToEmail: 'กลับไปกรอกอีเมล',
      success: 'เปลี่ยนรหัสผ่านสำเร็จ!',
      userInfo: 'ข้อมูลผู้ใช้',
    },
  };

  return (
    <div className="login-container">
      {/* Transparent Header with Logo */}
      <header className="login-transparent-header">
        <div className="header-logo" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <div className="logo-icon-small">
            <svg className="plane-icon-small" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
            </svg>
          </div>
          <span className="logo-text-small">AI Travel Agent</span>
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
              ) : (
                <form onSubmit={handleResetPassword} className="form-content">
                  {/* User Info */}
                  {userInfo && (
                    <div style={{ 
                      background: '#f3f4f6', 
                      padding: '1rem', 
                      borderRadius: '0.5rem', 
                      marginBottom: '1rem' 
                    }}>
                      <div style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>
                        {text[lang].userInfo}
                      </div>
                      <div style={{ fontSize: '0.9rem', color: '#6b7280' }}>
                        <div><strong>Email:</strong> {userInfo.email}</div>
                        {userInfo.full_name && (
                          <div><strong>{lang === 'th' ? 'ชื่อ:' : 'Name:'}</strong> {userInfo.full_name}</div>
                        )}
                        <div style={{ marginTop: '0.5rem' }}>
                          <strong>{text[lang].passwordStatus}:</strong>{' '}
                          <span style={{ 
                            color: userInfo.has_password ? '#10b981' : '#ef4444',
                            fontWeight: 'bold'
                          }}>
                            {userInfo.has_password ? text[lang].hasPassword : text[lang].noPassword}
                          </span>
                          {userInfo.has_backup && (
                            <span style={{ 
                              color: '#3b82f6', 
                              fontSize: '0.85rem', 
                              marginLeft: '0.5rem' 
                            }}>
                              ({lang === 'th' ? 'มี backup' : 'has backup'})
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* New Password */}
                  <div className="form-group">
                    <label htmlFor="newPassword" className="form-label">{text[lang].newPassword}</label>
                    <input
                      type="password"
                      id="newPassword"
                      name="newPassword"
                      value={newPassword}
                      onChange={handleChange}
                      placeholder={text[lang].newPassword}
                      className={`form-input ${errors.newPassword ? 'error' : ''}`}
                      autoComplete="new-password"
                    />
                    {errors.newPassword && <span className="error-message">{errors.newPassword}</span>}
                  </div>

                  {/* Confirm Password */}
                  <div className="form-group">
                    <label htmlFor="confirmPassword" className="form-label">{text[lang].confirmPassword}</label>
                    <input
                      type="password"
                      id="confirmPassword"
                      name="confirmPassword"
                      value={confirmPassword}
                      onChange={handleChange}
                      placeholder={text[lang].confirmPassword}
                      className={`form-input ${errors.confirmPassword ? 'error' : ''}`}
                      autoComplete="new-password"
                    />
                    {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
                  </div>

                  {errors.general && (
                    <div className="error-message" style={{ textAlign: 'center' }}>
                      {errors.general}
                    </div>
                  )}

                  {/* Submit Button */}
                  <button type="submit" className="btn-login" disabled={isLoading}>
                    {isLoading ? (lang === 'th' ? 'กำลังเปลี่ยนรหัสผ่าน...' : 'Resetting...') : text[lang].resetBtn}
                  </button>

                  {/* Back to Email Link */}
                  <div className="register-link">
                    <button 
                      type="button" 
                      onClick={() => {
                        setStep('email');
                        setUserInfo(null);
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
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}