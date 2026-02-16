import React, { useState } from 'react';
import './RegisterPage.css';

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
  const [lang, setLang] = useState('th');
  const [passwordStrength, setPasswordStrength] = useState({ score: 0, feedback: [] });
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const text = {
    en: {
      title: 'Create Account',
      email: 'Email',
      password: 'Password',
      confirmPassword: 'Confirm Password',
      firstName: 'First Name',
      lastName: 'Last Name',
      firstNameTh: 'First Name (Thai)',
      lastNameTh: 'Last Name (Thai)',
      phone: 'Phone Number',
      signUp: 'Sign Up',
      alreadyHaveAccount: 'Already have an account?',
      signIn: 'Sign In',
      orContinue: 'Or continue with',
      google: 'Sign up with Google',
      appName: 'AI Travel Agent',
    },
    th: {
      title: 'สมัครสมาชิก',
      email: 'อีเมล',
      password: 'รหัสผ่าน',
      confirmPassword: 'ยืนยันรหัสผ่าน',
      firstName: 'ชื่อ',
      lastName: 'นามสกุล',
      firstNameTh: 'ชื่อภาษาไทย',
      lastNameTh: 'นามสกุลภาษาไทย',
      phone: 'เบอร์โทรศัพท์',
      signUp: 'สมัครสมาชิก',
      alreadyHaveAccount: 'มีบัญชีอยู่แล้ว?',
      signIn: 'เข้าสู่ระบบ',
      orContinue: 'หรือต่อด้วย',
      google: 'สมัครด้วย Google',
      appName: 'ผู้ช่วยท่องเที่ยวอัจฉริยะ',
    },
  };

  const calculatePasswordStrength = (password) => {
    let score = 0;
    const feedback = [];

    if (password.length >= 8) score++;
    else feedback.push(lang === 'th' ? 'อย่างน้อย 8 ตัวอักษร' : 'At least 8 characters');

    if (/[A-Z]/.test(password)) score++;
    else feedback.push(lang === 'th' ? 'ตัวพิมพ์ใหญ่ (A-Z)' : 'Uppercase letter (A-Z)');

    if (/[a-z]/.test(password)) score++;
    else feedback.push(lang === 'th' ? 'ตัวพิมพ์เล็ก (a-z)' : 'Lowercase letter (a-z)');

    if (/\d/.test(password)) score++;
    else feedback.push(lang === 'th' ? 'ตัวเลข (0-9)' : 'Number (0-9)');

    if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score++;
    else feedback.push(lang === 'th' ? 'อักขระพิเศษ (!@#$...)' : 'Special character (!@#$...)');

    return { score, feedback };
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    // Calculate password strength
    if (name === 'password') {
      setPasswordStrength(calculatePasswordStrength(value));
    }

    // Clear error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({
        ...prev,
        [name]: ''
      }));
    }
  };

  const validate = () => {
    const newErrors = {};

    if (!formData.email.trim()) {
      newErrors.email = lang === 'th' ? 'กรุณากรอกอีเมล' : 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = lang === 'th' ? 'รูปแบบอีเมลไม่ถูกต้อง' : 'Invalid email format';
    }

    if (!formData.password) {
      newErrors.password = lang === 'th' ? 'กรุณากรอกรหัสผ่าน' : 'Password is required';
    } else if (formData.password.length < 8) {
      newErrors.password = lang === 'th' ? 'รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร' : 'Password must be at least 8 characters';
    } else if (!/[A-Z]/.test(formData.password)) {
      newErrors.password = lang === 'th' ? 'รหัสผ่านต้องมีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว' : 'Password must contain at least one uppercase letter';
    } else if (!/[a-z]/.test(formData.password)) {
      newErrors.password = lang === 'th' ? 'รหัสผ่านต้องมีตัวพิมพ์เล็กอย่างน้อย 1 ตัว' : 'Password must contain at least one lowercase letter';
    } else if (!/\d/.test(formData.password)) {
      newErrors.password = lang === 'th' ? 'รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว' : 'Password must contain at least one number';
    } else if (!/[!@#$%^&*(),.?":{}|<>]/.test(formData.password)) {
      newErrors.password = lang === 'th' ? 'รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว (!@#$...)' : 'Password must contain at least one special character';
    }

    if (!formData.confirmPassword) {
      newErrors.confirmPassword = lang === 'th' ? 'กรุณายืนยันรหัสผ่าน' : 'Please confirm password';
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = lang === 'th' ? 'รหัสผ่านไม่ตรงกัน' : 'Passwords do not match';
    }

    if (!formData.firstName.trim()) {
      newErrors.firstName = lang === 'th' ? 'กรุณากรอกชื่อ' : 'First name is required';
    }

    if (!formData.lastName.trim()) {
      newErrors.lastName = lang === 'th' ? 'กรุณากรอกนามสกุล' : 'Last name is required';
    }

    if (formData.phone && !/^[0-9]{9,10}$/.test(formData.phone.replace(/[-\s]/g, ''))) {
      newErrors.phone = lang === 'th' ? 'รูปแบบเบอร์โทรไม่ถูกต้อง (9-10 หลัก)' : 'Invalid phone number format';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsSubmitting(true);
    setIsSuccess(false);
    setErrors({}); // Clear previous errors
    try {
      await onRegister({
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
      
      // Wait 1.5 seconds then navigate to login
      setTimeout(() => {
        if (onNavigateToLogin) {
          onNavigateToLogin();
        }
      }, 1500);
      
    } catch (error) {
      console.error('Registration error:', error);
      const errorMessage = error?.message || String(error);
      
      // Check for common errors
      let displayMessage = errorMessage;
      if (errorMessage.includes('fetch') || errorMessage.includes('Failed to fetch')) {
        displayMessage = lang === 'th' 
          ? 'ไม่สามารถเชื่อมต่อกับเซิร์ฟเวอร์ได้ กรุณาตรวจสอบว่า backend ทำงานอยู่'
          : 'Cannot connect to server. Please check if backend is running';
      } else if (errorMessage.includes('NetworkError') || errorMessage.includes('network')) {
        displayMessage = lang === 'th'
          ? 'เกิดข้อผิดพลาดทางเครือข่าย กรุณาลองใหม่อีกครั้ง'
          : 'Network error. Please try again';
      } else if (errorMessage.includes('Email already registered') || errorMessage.includes('already exists')) {
        displayMessage = lang === 'th'
          ? 'อีเมลนี้ถูกใช้งานแล้ว กรุณาใช้อีเมลอื่น'
          : 'Email already registered. Please use a different email';
      }
      
      setErrors({
        general: lang === 'th' 
          ? 'เกิดข้อผิดพลาดในการสมัครสมาชิก: ' + displayMessage
          : 'Registration failed: ' + displayMessage
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
            <h2 className="register-title">{text[lang].title}</h2>
            <p className="register-subtitle">
              {lang === 'th' ? 'เริ่มต้นสร้างบัญชีของคุณเพื่อเริ่มวางแผนทริป' : "Let's get started with your travel planning."}
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
                  <label htmlFor="firstName" className="form-label">{text[lang].firstName}</label>
                  <input
                    type="text"
                    id="firstName"
                    name="firstName"
                    value={formData.firstName}
                    onChange={handleChange}
                    placeholder={text[lang].firstName}
                    className={`form-input ${errors.firstName ? 'error' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.firstName && <span className="error-message">{errors.firstName}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="lastName" className="form-label">{text[lang].lastName}</label>
                  <input
                    type="text"
                    id="lastName"
                    name="lastName"
                    value={formData.lastName}
                    onChange={handleChange}
                    placeholder={text[lang].lastName}
                    className={`form-input ${errors.lastName ? 'error' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.lastName && <span className="error-message">{errors.lastName}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="firstNameTh" className="form-label">{text[lang].firstNameTh}</label>
                  <input
                    type="text"
                    id="firstNameTh"
                    name="firstNameTh"
                    value={formData.firstNameTh}
                    onChange={handleChange}
                    placeholder={text[lang].firstNameTh}
                    className={`form-input ${errors.firstNameTh ? 'error' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.firstNameTh && <span className="error-message">{errors.firstNameTh}</span>}
                </div>
                <div className="form-group">
                  <label htmlFor="lastNameTh" className="form-label">{text[lang].lastNameTh}</label>
                  <input
                    type="text"
                    id="lastNameTh"
                    name="lastNameTh"
                    value={formData.lastNameTh}
                    onChange={handleChange}
                    placeholder={text[lang].lastNameTh}
                    className={`form-input ${errors.lastNameTh ? 'error' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.lastNameTh && <span className="error-message">{errors.lastNameTh}</span>}
                </div>
              </div>

              {/* Email and Phone - 2 columns */}
              <div className="form-row">
                <div className="form-group">
                  <label htmlFor="email" className="form-label">{text[lang].email}</label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={formData.email}
                    onChange={handleChange}
                    placeholder={text[lang].email}
                    className={`form-input ${errors.email ? 'error' : ''}`}
                    disabled={isSubmitting}
                  />
                  {errors.email && <span className="error-message">{errors.email}</span>}
                </div>

                <div className="form-group">
                  <label htmlFor="phone" className="form-label">{text[lang].phone}</label>
                  <input
                    type="tel"
                    id="phone"
                    name="phone"
                    value={formData.phone}
                    onChange={handleChange}
                    placeholder={text[lang].phone}
                    className={`form-input ${errors.phone ? 'error' : ''}`}
                  />
                  {errors.phone && <span className="error-message">{errors.phone}</span>}
                </div>
              </div>

              {/* Password */}
              <div className="form-group">
                <label htmlFor="password" className="form-label">{text[lang].password}</label>
                <div className="password-input-wrapper">
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    placeholder={text[lang].password}
                    className={`form-input has-toggle ${errors.password ? 'error' : ''}`}
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
                      {lang === 'th' ? 'ความแข็งแกร่ง: ' : 'Strength: '}
                      <span className={`strength-label strength-${passwordStrength.score}`}>
                        {passwordStrength.score === 0 && (lang === 'th' ? 'อ่อนแอมาก' : 'Very Weak')}
                        {passwordStrength.score === 1 && (lang === 'th' ? 'อ่อนแอ' : 'Weak')}
                        {passwordStrength.score === 2 && (lang === 'th' ? 'พอใช้' : 'Fair')}
                        {passwordStrength.score === 3 && (lang === 'th' ? 'ดี' : 'Good')}
                        {passwordStrength.score === 4 && (lang === 'th' ? 'แข็งแกร่ง' : 'Strong')}
                        {passwordStrength.score === 5 && (lang === 'th' ? 'แข็งแกร่งมาก' : 'Very Strong')}
                      </span>
                    </div>
                    {passwordStrength.feedback.length > 0 && (
                      <div className="strength-feedback">
                        {lang === 'th' ? 'ต้องมี: ' : 'Required: '}
                        {passwordStrength.feedback.join(', ')}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Confirm Password */}
              <div className="form-group">
                <label htmlFor="confirmPassword" className="form-label">{text[lang].confirmPassword}</label>
                <div className="password-input-wrapper">
                  <input
                    type={showConfirmPassword ? "text" : "password"}
                    id="confirmPassword"
                    name="confirmPassword"
                    value={formData.confirmPassword}
                    onChange={handleChange}
                    placeholder={text[lang].confirmPassword}
                    className={`form-input has-toggle ${errors.confirmPassword ? 'error' : ''}`}
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
              <button type="submit" className={`btn-register ${isSuccess ? 'btn-success' : ''}`} disabled={isSubmitting || isSuccess}>
                {isSuccess ? (
                  <span style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ flexShrink: 0 }}>
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor"/>
                    </svg>
                    {lang === 'th' ? 'สมัครสมาชิกสำเร็จ!' : 'Registration Successful!'}
                  </span>
                ) : isSubmitting ? (
                  lang === 'th' ? 'กำลังสมัคร...' : 'Registering...'
                ) : (
                  text[lang].signUp
                )}
              </button>

              {/* Link to Login */}
              <div className="login-link">
                <span>{text[lang].alreadyHaveAccount} </span>
                <button type="button" onClick={onNavigateToLogin} className="link-button">
                  {text[lang].signIn}
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
