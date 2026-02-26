import React, { useState } from 'react';
import './RegisterPage.css';
import { useLanguage } from '../../context/LanguageContext';

export default function RegisterPage({ onRegister, onNavigateToLogin, onGoogleLogin, onNavigateToHome }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    firstName: '',
    lastName: '',
    firstNameTh: '',
    lastNameTh: '',
    phone: ''
  });
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState(''); // ข้อความหลังลงทะเบียน (เช่น ส่งอีเมลยืนยันแล้ว)
  const { t } = useLanguage();
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, feedback: [] });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const calculatePasswordStrength = (password) => {
    let score = 0;
    const feedback = [];

    if (password.length >= 8) score++;
    else feedback.push(t('auth.req8chars'));

    if (/[A-Z]/.test(password)) score++;
    else feedback.push(t('auth.reqUppercase'));

    if (/[a-z]/.test(password)) score++;
    else feedback.push(t('auth.reqLowercase'));

    if (/\d/.test(password)) score++;
    else feedback.push(t('auth.reqNumber'));

    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    else feedback.push(t('auth.reqSpecial'));

    return { score, feedback };
  };

  const validateField = (name, value) => {
    switch (name) {
      case 'firstName':
        if (!value.trim()) return 'กรุณากรอกชื่อ';
        if (!/^[A-Za-z\s]+$/.test(value.trim())) return 'ชื่อต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
        if (value.trim().length < 2) return 'ชื่อต้องมีอย่างน้อย 2 ตัวอักษร';
        return '';
      case 'lastName':
        if (!value.trim()) return 'กรุณากรอกนามสกุล';
        if (!/^[A-Za-z\s]+$/.test(value.trim())) return 'นามสกุลต้องเป็นตัวอักษรภาษาอังกฤษเท่านั้น';
        if (value.trim().length < 2) return 'นามสกุลต้องมีอย่างน้อย 2 ตัวอักษร';
        return '';
      case 'firstNameTh':
        if (!value.trim()) return 'กรุณากรอกชื่อภาษาไทย';
        if (!/^[ก-๙\s]+$/.test(value.trim())) return 'ชื่อภาษาไทยต้องเป็นภาษาไทยเท่านั้น';
        if (value.trim().length < 2) return 'ชื่อภาษาไทยต้องมีอย่างน้อย 2 ตัวอักษร';
        return '';
      case 'lastNameTh':
        if (!value.trim()) return 'กรุณากรอกนามสกุลภาษาไทย';
        if (!/^[ก-๙\s]+$/.test(value.trim())) return 'นามสกุลภาษาไทยต้องเป็นภาษาไทยเท่านั้น';
        if (value.trim().length < 2) return 'นามสกุลภาษาไทยต้องมีอย่างน้อย 2 ตัวอักษร';
        return '';
      case 'email':
        if (!value.trim()) return 'กรุณากรอกอีเมล';
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return 'รูปแบบอีเมลไม่ถูกต้อง';
        return '';
      case 'phone':
        if (!value.trim()) return 'กรุณากรอกเบอร์โทรศัพท์';
        if (!/^0[0-9]{8,9}$/.test(value.replace(/[-\s]/g, ''))) return 'เบอร์โทรต้องขึ้นต้นด้วย 0 และมี 9-10 หลัก';
        return '';
      case 'password':
        if (!value) return 'กรุณากรอกรหัสผ่าน';
        if (value.length < 8) return 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร';
        if (!/[A-Z]/.test(value)) return 'รหัสผ่านต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว';
        if (!/[a-z]/.test(value)) return 'รหัสผ่านต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว';
        if (!/\d/.test(value)) return 'รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว';
        if (!/[!@#$%^&*(),.?":{}|<>]/.test(value)) return 'รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว';
        return '';
      case 'confirmPassword':
        if (!value) return 'กรุณายืนยันรหัสผ่าน';
        if (formData.password !== value) return 'รหัสผ่านไม่ตรงกัน';
        return '';
      default:
        return '';
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    if (name === 'password') {
      setPasswordStrength(calculatePasswordStrength(value));
      // re-validate confirmPassword ถ้ากรอกไปแล้ว
      if (formData.confirmPassword) {
        setErrors(prev => ({
          ...prev,
          confirmPassword: formData.confirmPassword !== value ? 'รหัสผ่านไม่ตรงกัน' : '',
        }));
      }
    }

    // clear error ทันทีที่แก้ไข
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
  };

  const handleBlur = (e) => {
    const { name, value } = e.target;
    const err = validateField(name, value);
    if (err) setErrors(prev => ({ ...prev, [name]: err }));
  };

  const validate = () => {
    const fields = ['firstName', 'lastName', 'firstNameTh', 'lastNameTh', 'email', 'phone', 'password', 'confirmPassword'];
    const newErrors = {};
    fields.forEach(field => {
      const err = validateField(field, formData[field]);
      if (err) newErrors[field] = err;
    });
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // ปุ่มสมัครสมาชิกกดไม่ได้ถ้าช่องบังคับยังไม่ครบ
  const isFormIncomplete =
    !formData.firstName.trim() ||
    !formData.lastName.trim() ||
    !formData.firstNameTh.trim() ||
    !formData.lastNameTh.trim() ||
    !formData.email.trim() ||
    !formData.phone.trim() ||
    !formData.password ||
    !formData.confirmPassword;

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    setIsSuccess(false);
    setErrors({}); // Clear previous errors
    try {
      const data = await onRegister({
        email: formData.email,
        password: formData.password,
        firstName: formData.firstName,
        lastName: formData.lastName,
        firstNameTh: formData.firstNameTh.trim() || undefined,
        lastNameTh: formData.lastNameTh.trim() || undefined,
        phone: formData.phone
      });
      
      // Registration successful - show checkmark
      setIsSuccess(true);
      setIsSubmitting(false);
      if (data?.verification_email_sent && data?.message) {
        setSuccessMessage(data.message);
      }

      // ถ้าต้องยืนยันอีเมล → App.jsx จะ navigate ไป verify-email-sent แล้ว
      // ถ้า email verified แล้ว (admin/dev) → navigate ไป login
      if (data?.email_verified) {
        setTimeout(() => {
          if (onNavigateToLogin) {
            onNavigateToLogin();
          }
        }, 1500);
      }
      
    } catch (error) {
      console.error('Registration error:', error);
      const errorMessage = error?.message || String(error);
      
      // Check for common errors
      let displayMessage = errorMessage;
      if (errorMessage.includes('fetch') || errorMessage.includes('Failed to fetch')) {
        displayMessage = t('auth.errNetworkError');
      } else if (errorMessage.includes('NetworkError') || errorMessage.includes('network')) {
        displayMessage = t('auth.errNetworkError');
      } else if (errorMessage.includes('Email already registered') || errorMessage.includes('already exists')) {
        displayMessage = t('auth.errEmailTaken');
      }
      
      setErrors({
        general: t('auth.errRegisterFailed') + displayMessage
      });
      setIsSubmitting(false);
      setIsSuccess(false);
    }
  };

  return (
    <div className="register-container">
      {/* Header with Logo + AI Travel Agent text (เหมือนหน้าเข้าสู่ระบบ) */}
      <header className="register-transparent-header">
        <div className="header-logo" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <img src="/favicon.svg" alt="" className="login-logo-img" aria-hidden="true" />
          <span className="header-logo-text">AITravelAgent</span>
        </div>
      </header>

      <main className="register-main">
        {/* Main Card Container */}
        <div className="register-card-wrapper">
          {/* Left Side - Image */}
          <div className="register-image-section">
            <div className="register-image-container">
              <img 
                src="/1949136.jpg" 
                alt="Travel Illustration" 
                className="register-illustration"
                onError={(e) => {
                  // Fallback to placeholder if image not found
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
              <div className="register-illustration-placeholder" style={{ display: 'none' }}>
                <svg viewBox="0 0 400 300" className="placeholder-svg">
                  <circle cx="100" cy="150" r="40" fill="#fbbf24" opacity="0.3"/>
                  <circle cx="200" cy="150" r="40" fill="#3b82f6" opacity="0.3"/>
                  <circle cx="300" cy="150" r="40" fill="#ec4899" opacity="0.3"/>
                  <text x="200" y="160" textAnchor="middle" fill="#6b7280" fontSize="14" fontFamily="Arial">
                    Travel Illustration
                  </text>
                </svg>
              </div>
            </div>
          </div>

          {/* Right Side - Register Form */}
          <div className="register-form-section">
            <div className="register-card">
            <h2 className="register-title">{t('auth.register')}</h2>
            <p className="register-subtitle">
              {t('auth.startPlanning')}
            </p>

            <form onSubmit={handleSubmit} className="form-content">
              {/* Error Message */}
              {errors.general && (
                <div style={{
                  padding: '0.75rem',
                  background: '#fee2e2',
                  border: '1px solid #fecaca',
                  borderRadius: '0.5rem',
                  color: '#dc2626',
                  fontSize: '0.875rem'
                }}>
                  {errors.general}
                </div>
              )}

              {/* ชื่อ นามสกุล ชื่อภาษาไทย นามสกุลภาษาไทย - 1 แถว 4 คอลัมน์ */}
              <div className="form-row form-row-4">
                <div className="form-group">
                  <label htmlFor="firstName" className="form-label">{t('auth.firstName')}</label>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.firstName')}
                    className={`form-input ${errors.firstName ? 'error' : formData.firstName.trim().length >= 2 && /^[A-Za-z\s]+$/.test(formData.firstName.trim()) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.firstName && <span className="error-message">{errors.firstName}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="lastName" className="form-label">{t('auth.lastName')}</label>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.lastName')}
                    className={`form-input ${errors.lastName ? 'error' : formData.lastName.trim().length >= 2 && /^[A-Za-z\s]+$/.test(formData.lastName.trim()) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.lastName && <span className="error-message">{errors.lastName}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="firstNameTh" className="form-label">{t('auth.firstNameTh')}</label>
                  <input
                    type="text"
                    id="firstNameTh"
                    name="firstNameTh"
                    value={formData.firstNameTh}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.firstNameTh')}
                    className={`form-input ${errors.firstNameTh ? 'error' : formData.firstNameTh.trim() && /^[ก-๙\s]+$/.test(formData.firstNameTh.trim()) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.firstNameTh && <span className="error-message">{errors.firstNameTh}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="lastNameTh" className="form-label">{t('auth.lastNameTh')}</label>
                  <input
                    type="text"
                    id="lastNameTh"
                    name="lastNameTh"
                    value={formData.lastNameTh}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.lastNameTh')}
                    className={`form-input ${errors.lastNameTh ? 'error' : formData.lastNameTh.trim() && /^[ก-๙\s]+$/.test(formData.lastNameTh.trim()) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.lastNameTh && <span className="error-message">{errors.lastNameTh}</span>}
                </div>
              </div>

              {/* Email and Phone - 2 columns */}
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="email" className="form-label">{t('auth.email')}</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.email')}
                    className={`form-input ${errors.email ? 'error' : /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.email && <span className="error-message">{errors.email}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="phone" className="form-label">{t('auth.phone')}</label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    onBlur={handleBlur}
                    placeholder={t('auth.phone')}
                    className={`form-input ${errors.phone ? 'error' : /^0[0-9]{8,9}$/.test(formData.phone.replace(/[-\s]/g, '')) ? 'valid' : ''}`}
                    disabled={isSubmitting}
                    maxLength={10}
                  />
                  {errors.phone && <span className="error-message">{errors.phone}</span>}
                </div>
              </div>

              {/* Password */}
              <div className="form-group">
                <label htmlFor="password" className="form-label">{t('auth.password')}</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder={t('auth.password')}
                    className={`form-input has-toggle ${errors.password ? 'error' : passwordStrength.score === 5 ? 'valid' : ''}`}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    title={showPassword ? "Hide password" : "Show password"}
                    disabled={isSubmitting}
                  >
                    {showPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10.94 6.08A6.93 6.93 0 0 1 12 6c3.18 0 6.17 2.29 7.91 6a15.23 15.23 0 0 1-.9 1.64 1 1 0 0 1-1.7-.3 1 1 0 0 0-1.72-1.04 6 6 0 0 0-1.54-1.54 1 1 0 0 0-1.72 1.04 1 1 0 0 1-1.7.3 7.12 7.12 0 0 1-1.9-1.9 1 1 0 0 0-1.72-1.04ZM3.71 2.29a1 1 0 0 0-1.42 1.42l3.1 3.09a14.62 14.62 0 0 0-3.31 4.8 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 5.05-1.54l3.24 3.25a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42Zm6.36 9.19 2.45 2.45A1.81 1.81 0 0 1 12 14a2 2 0 0 1-2-2 1.81 1.81 0 0 1 .07-.52ZM5.22 7.72a15.08 15.08 0 0 0-1.9 4.28 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 3.78-.84l-2.86-2.86a2 2 0 0 1-2.64-2.64L5.22 7.72Z" fill="currentColor"/>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 8a5 5 0 1 1 5-5 5 5 0 0 1-5 5Zm0-12.5a7.49 7.49 0 0 0-6.32 3.15L4.9 8.09a9 9 0 0 1 7.1-3.09 9 9 0 0 1 7.1 3.09l-.78.56A7.49 7.49 0 0 0 12 4.5Zm-10.23 .36A1 1 0 0 0 1 5.64l18 18a1 1 0 0 0 1.41-1.41Z" fill="currentColor"/>
                        <path d="M12 6.5a5.74 5.74 0 0 1 4.23 1.77 1 1 0 0 0 1.41 0 1 1 0 0 0 0-1.42A7.74 7.74 0 0 0 12 4.5a7 7 0 0 0-5.91 3.15L5.4 8.21A5 5 0 0 1 12 6.5Zm3.5 3.5a1 1 0 0 0-1.41 1.41l2.22 2.22A1 1 0 0 0 17 12a1 1 0 0 0-1.5-1.5Z" fill="currentColor"/>
                      </svg>
                    )}
                  </button>
                </div>
                {errors.password && <span className="error-message">{errors.password}</span>}
                
                {/* Password Strength Indicator */}
                {formData.password && (
                  <div className="password-strength">
                    <div className="strength-bar">
                      <div 
                        className={`strength-fill strength-${passwordStrength.score}`}
                        style={{ width: `${(passwordStrength.score / 5) * 100}%` }}
                      ></div>
                    </div>
                    <div className="strength-text">
                      {t('auth.strengthLabel')}
                      <span className={`strength-label strength-${passwordStrength.score}`}>
                        {passwordStrength.score === 0 && t('auth.strengthVeryWeak')}
                        {passwordStrength.score === 1 && t('auth.strengthWeak')}
                        {passwordStrength.score === 2 && t('auth.strengthFair')}
                        {passwordStrength.score === 3 && t('auth.strengthGood')}
                        {passwordStrength.score === 4 && t('auth.strengthStrong')}
                        {passwordStrength.score === 5 && t('auth.strengthVeryStrong')}
                      </span>
                    </div>
                    {passwordStrength.feedback.length > 0 && (
                      <div className="strength-feedback">
                        {t('auth.passwordRequirements')}
                        {passwordStrength.feedback.join(', ')}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="form-group">
                <label htmlFor="confirmPassword" className="form-label">{t('auth.confirmPassword')}</label>
                <div className="password-input-wrapper">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder={t('auth.confirmPassword')}
                    className={`form-input has-toggle ${errors.confirmPassword ? 'error' : formData.confirmPassword && formData.password === formData.confirmPassword ? 'valid' : ''}`}
                    onBlur={handleBlur}
                    disabled={isSubmitting}
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowConfirmPassword((v) => !v)}
                    aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                    title={showConfirmPassword ? "Hide password" : "Show password"}
                    disabled={isSubmitting}
                  >
                    {showConfirmPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10.94 6.08A6.93 6.93 0 0 1 12 6c3.18 0 6.17 2.29 7.91 6a15.23 15.23 0 0 1-.9 1.64 1 1 0 0 1-1.7-.3 1 1 0 0 0-1.72-1.04 6 6 0 0 0-1.54-1.54 1 1 0 0 0-1.72 1.04 1 1 0 0 1-1.7.3 7.12 7.12 0 0 1-1.9-1.9 1 1 0 0 0-1.72-1.04ZM3.71 2.29a1 1 0 0 0-1.42 1.42l3.1 3.09a14.62 14.62 0 0 0-3.31 4.8 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 5.05-1.54l3.24 3.25a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42Zm6.36 9.19 2.45 2.45A1.81 1.81 0 0 1 12 14a2 2 0 0 1-2-2 1.81 1.81 0 0 1 .07-.52ZM5.22 7.72a15.08 15.08 0 0 0-1.9 4.28 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 3.78-.84l-2.86-2.86a2 2 0 0 1-2.64-2.64L5.22 7.72Z" fill="currentColor"/>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 8a5 5 0 1 1 5-5 5 5 0 0 1-5 5Zm0-12.5a7.49 7.49 0 0 0-6.32 3.15L4.9 8.09a9 9 0 0 1 7.1-3.09 9 9 0 0 1 7.1 3.09l-.78.56A7.49 7.49 0 0 0 12 4.5Zm-10.23 .36A1 1 0 0 0 1 5.64l18 18a1 1 0 0 0 1.41-1.41Z" fill="currentColor"/>
                        <path d="M12 6.5a5.74 5.74 0 0 1 4.23 1.77 1 1 0 0 0 1.41 0 1 1 0 0 0 0-1.42A7.74 7.74 0 0 0 12 4.5a7 7 0 0 0-5.91 3.15L5.4 8.21A5 5 0 0 1 12 6.5Zm3.5 3.5a1 1 0 0 0-1.41 1.41l2.22 2.22A1 1 0 0 0 17 12a1 1 0 0 0-1.5-1.5Z" fill="currentColor"/>
                      </svg>
                    )}
                  </button>
                </div>
                {errors.confirmPassword && <span className="error-message">{errors.confirmPassword}</span>}
              </div>

              {/* Submit Button */}
              <button type="submit" className={`btn-register ${isSuccess ? 'btn-success' : ''}`} disabled={isSubmitting || isSuccess || isFormIncomplete}>
                {isSuccess ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor"/>
                    </svg>
                    {t('auth.registerSuccess')}
                  </span>
                ) : isSubmitting ? (
                  t('auth.registering')
                ) : (
                  t('auth.register')
                )}
              </button>

              {isSuccess && successMessage && (
                <p className="register-verification-message" role="alert">
                  {successMessage}
                </p>
              )}

              {/* Link to Login */}
              <div className="login-link">
                <span>{t('auth.hasAccount')} </span>
                <button type="button" onClick={onNavigateToLogin} className="link-button">
                  {t('auth.login')}
                </button>
              </div>
            </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
