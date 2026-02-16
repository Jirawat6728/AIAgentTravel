import React, { useState } from 'react';
import './LoginPage.css';

export default function LoginPage({ onLogin, onGoogleLogin, onNavigateToRegister, onNavigateToResetPassword, onNavigateToHome }) {
  // ✅ Load saved email and rememberMe preference from localStorage
  const savedEmail = localStorage.getItem('remembered_email') || '';
  const savedRememberMe = localStorage.getItem('remember_me') === 'true';
  
  const [email, setEmail] = useState(savedEmail);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(savedRememberMe);
  const [lang, setLang] = useState('th');
  const [errors, setErrors] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [passwordError, setPasswordError] = useState(false);
  const [emailError, setEmailError] = useState(false);
  const [shakePassword, setShakePassword] = useState(false);
  const [shakeEmail, setShakeEmail] = useState(false);

  const validate = () => {
    const newErrors = {};
    
    if (!email.trim()) {
      newErrors.email = lang === 'th' ? 'กรุณากรอกอีเมล' : 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = lang === 'th' ? 'รูปแบบอีเมลไม่ถูกต้อง' : 'Invalid email format';
    }
    
    if (!password) {
      newErrors.password = lang === 'th' ? 'กรุณากรอกรหัสผ่าน' : 'Password is required';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name === 'email') {
      setEmail(value);
      // Clear email error when user starts typing
      if (emailError) {
        setEmailError(false);
        setShakeEmail(false);
      }
    } else if (name === 'password') {
      setPassword(value);
      // Clear password error when user starts typing
      if (passwordError) {
        setPasswordError(false);
        setShakePassword(false);
      }
    }
    // Clear error when user starts typing
    if (errors[name] || errors.general) {
      setErrors(prev => ({
        ...prev,
        [name]: '',
        general: ''
      }));
    }
  };

  const handleLoginClick = async (e) => {
    e.preventDefault();
    
    if (!validate()) {
      return;
    }

    setIsLoading(true);
    setPasswordError(false);
    setEmailError(false);
    setShakePassword(false);
    setShakeEmail(false);
    setErrors(prev => ({ ...prev, general: '' }));
    
    try {
      await onLogin(email, password, rememberMe);
      
      // ✅ Save email and rememberMe preference if checkbox is checked
      if (rememberMe) {
        localStorage.setItem('remembered_email', email);
        localStorage.setItem('remember_me', 'true');
      } else {
        // Clear saved data if user unchecks "remember me"
        localStorage.removeItem('remembered_email');
        localStorage.removeItem('remember_me');
      }
      
      // Login successful - clear any errors
      setPasswordError(false);
      setEmailError(false);
      setShakePassword(false);
      setShakeEmail(false);
    } catch (error) {
      console.error('Login error:', error);
      
      // Check error message to determine which field to show error
      const errorMessage = error.message || error.detail || String(error);
      
      // ✅ Check if email not found
      if (errorMessage.includes('Email not found') || errorMessage.includes('email not found')) {
        // Show email error with shake animation
        setEmailError(true);
        setShakeEmail(true);
        
        // Remove shake animation class after animation completes (600ms)
        setTimeout(() => {
          setShakeEmail(false);
        }, 600);
        
        // Clear password field
        setPassword('');
      }
      // ✅ Check if it's a password/authentication error (wrong credentials)
      else if (errorMessage.includes('Invalid email or password') || 
               errorMessage.includes('password') || 
               errorMessage.includes('401') ||
               errorMessage.includes('Unauthorized')) {
        // Show password error with shake animation
        setPasswordError(true);
        setShakePassword(true);
        setErrors({
          general: lang === 'th' ? 'อีเมลหรือรหัสผ่านไม่ถูกต้อง' : 'Email or password is incorrect'
        });
        
        // Remove shake animation class after animation completes (600ms)
        setTimeout(() => {
          setShakePassword(false);
        }, 600);
        
        // Clear password field
        setPassword('');
      } else {
        setErrors({
          general: lang === 'th' 
            ? 'เกิดข้อผิดพลาดในการเข้าสู่ระบบ: ' + errorMessage
            : 'Login failed: ' + errorMessage
        });
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleLoginClick(e);
    }
  };

  // 🈯️ ข้อความ 2 ภาษา
  const text = {
    en: {
      title: 'Log In',
      email: 'Email',
      password: 'Password',
      remember: 'Remember me',
      signIn: 'Sign In',
      signUp: 'Sign Up',
      forgot: 'Forgot Password?',
      orContinue: 'Or continue with',
      google: 'Login with Google',
      appName: 'AI Travel Agent',
    },
    th: {
      title: 'เข้าสู่ระบบ',
      email: 'อีเมล',
      password: 'รหัสผ่าน',
      remember: 'จำฉันไว้',
      signIn: 'เข้าสู่ระบบ',
      signUp: 'สมัครสมาชิก',
      forgot: 'ลืมรหัสผ่าน?',
      orContinue: 'หรือต่อด้วย',
      google: 'เข้าสู่ระบบด้วย Google',
      appName: 'ผู้ช่วยท่องเที่ยวอัจฉริยะ',
    },
  };

  return (
    <div className="login-container">
      {/* Header with Logo + AI Travel Agent text */}
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
                  // Fallback to placeholder if image not found
                  e.target.style.display = 'none';
                  e.target.nextElementSibling.style.display = 'flex';
                }}
              />
              {/* Alternative: Use image from Freepik - place image file in public folder and update src */}
              {/* <img 
                src="/travel-image.png" 
                alt="Travel Illustration" 
                className="login-illustration"
              /> */}
              <div className="login-illustration-placeholder" style={{ display: 'none' }}>
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

          {/* Right Side - Login Form */}
          <div className="login-form-section">
            <div className="login-card">
            <h2 className="login-title">{text[lang].title}</h2>
            <p className="login-subtitle">
              {lang === 'th' ? 'ยินดีต้อนรับกลับมา! กรุณาเข้าสู่ระบบเพื่อใช้งาน' : 'Welcome back! Please login to your account.'}
            </p>

            <form onSubmit={handleLoginClick} className="form-content">
              {/* Email */}
              <div className="form-group">
                <label htmlFor="email" className="form-label">{text[lang].email}</label>
                <div className={shakeEmail ? 'shake' : ''}>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={email}
                    onChange={handleChange}
                    placeholder={text[lang].email}
                    className={`form-input ${savedEmail && rememberMe ? 'remembered' : ''} ${emailError ? 'error' : ''}`}
                    autoComplete="email"
                  />
                </div>
                {emailError && (
                  <div className="error-message" style={{ color: '#dc2626', fontSize: '0.875rem', marginTop: '0.25rem' }}>
                    {lang === 'th' ? 'ไม่พบอีเมลนี้ในระบบ' : 'Email not found'}
                  </div>
                )}
              </div>

              {/* Password */}
              <div className="form-group">
                <label htmlFor="password" className="form-label">{text[lang].password}</label>
                <div className={`password-input-wrapper ${shakePassword ? 'shake' : ''}`}>
                  <input
                    type={showPassword ? "text" : "password"}
                    id="password"
                    name="password"
                    value={password}
                    onChange={handleChange}
                    placeholder={text[lang].password}
                    className={`form-input has-toggle ${passwordError ? 'error' : ''}`}
                  />
                  <button
                    type="button"
                    className="toggle-password"
                    onClick={() => setShowPassword((v) => !v)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    title={showPassword ? "Hide password" : "Show password"}
                  >
                    {showPassword ? (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M10.94 6.08A6.93 6.93 0 0 1 12 6c3.18 0 6.17 2.29 7.91 6a15.23 15.23 0 0 1-.9 1.64 1 1 0 0 1-1.7-.3 1 1 0 0 0-1.72-1.04 6 6 0 0 0-1.54-1.54 1 1 0 0 0-1.72 1.04 1 1 0 0 1-1.7.3 7.12 7.12 0 0 1-1.9-1.9 1 1 0 0 0-1.72-1.04ZM3.71 2.29a1 1 0 0 0-1.42 1.42l3.1 3.09a14.62 14.62 0 0 0-3.31 4.8 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 5.05-1.54l3.24 3.25a1 1 0 0 0 1.42 0 1 1 0 0 0 0-1.42Zm6.36 9.19 2.45 2.45A1.81 1.81 0 0 1 12 14a2 2 0 0 1-2-2 1.81 1.81 0 0 1 .07-.52ZM5.22 7.72a15.08 15.08 0 0 0-1.9 4.28 1 1 0 0 0 0 .8C4.83 15.85 8.21 18 12 18a9.26 9.26 0 0 0 3.78-.84l-2.86-2.86a2 2 0 0 1-2.64-2.64L5.22 7.72Z" fill="currentColor"/>
                      </svg>
                    ) : (
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Zm0 8a5 5 0 1 1 5-5 5 5 0 0 1-5 5Zm0-12.5a7.49 7.49 0 0 0-6.32 3.15L4.9 8.09a9 9 0 0 1 7.1-3.09 9 9 0 0 1 7.1 3.09l-.78.56A7.49 7.49 0 0 0 12 4.5Zm-10.23.36A1 1 0 0 0 1 5.64l18 18a1 1 0 0 0 1.41-1.41Z" fill="currentColor"/>
                        <path d="M12 6.5a5.74 5.74 0 0 1 4.23 1.77 1 1 0 0 0 1.41 0 1 1 0 0 0 0-1.42A7.74 7.74 0 0 0 12 4.5a7 7 0 0 0-5.91 3.15L5.4 8.21A5 5 0 0 1 12 6.5Zm3.5 3.5a1 1 0 0 0-1.41 1.41l2.22 2.22A1 1 0 0 0 17 12a1 1 0 0 0-1.5-1.5Z" fill="currentColor"/>
                      </svg>
                    )}
                  </button>
                </div>
              </div>

              {/* Remember Me and Forgot Password */}
              <div className="remember-me">
                <div className="checkbox-wrapper">
                  <input
                    type="checkbox"
                    id="remember"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="checkbox"
                  />
                  <label htmlFor="remember" className="checkbox-label">
                    {text[lang].remember}
                  </label>
                </div>
                <div className="forgot-password">
                  <button type="button" onClick={onNavigateToResetPassword} className="forgot-link" style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}>
                    {text[lang].forgot}
                  </button>
                </div>
              </div>

              {/* General error (wrong credentials, etc.) */}
              {errors.general && (
                <div className="error-message" style={{ color: '#dc2626', fontSize: '0.875rem', marginTop: '0.25rem', marginBottom: '0.5rem' }}>
                  {errors.general}
                </div>
              )}

              {/* Submit Button */}
              <button type="submit" className="btn-login" disabled={isLoading}>
                {isLoading ? (lang === 'th' ? 'กำลังเข้าสู่ระบบ...' : 'Signing in...') : text[lang].signIn}
              </button>

              {/* Register Link */}
              <div className="register-link">
                <span>{lang === 'th' ? 'ยังไม่มีบัญชี? ' : "Don't have an account? "}</span>
                <button type="button" onClick={onNavigateToRegister} className="link-button">
                  {text[lang].signUp}
                </button>
              </div>

              {/* Divider */}
              <div className="divider">
                <span className="divider-text">{text[lang].orContinue}</span>
              </div>

              {/* Google Login */}
              <button 
                type="button"
                onClick={onGoogleLogin} 
                className="btn-google"
                disabled={isLoading}
              >
                <svg className="google-icon" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                {text[lang].google}
              </button>
            </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
