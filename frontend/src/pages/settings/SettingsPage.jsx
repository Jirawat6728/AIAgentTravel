import React, { useState, useEffect } from 'react';
import './SettingsPage.css';
import AppHeader from '../../components/common/AppHeader';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function SettingsPage({
  user,
  onLogout,
  onNavigateToHome,
  onNavigateToProfile,
  onNavigateToBookings,
  onNavigateToAI,
  onNavigateToFlights,
  onNavigateToHotels,
  onNavigateToCarRentals,
  notificationCount = 0,
  onRefreshUser = null,
  onSendVerificationEmailSuccess = null
}) {
  const [activeSection, setActiveSection] = useState('account');
  const [settings, setSettings] = useState({
    // Account Settings
    emailVerified: user?.email_verified || false,
    authProvider: user?.auth_provider || 'email',
    
    // Notifications
    notificationsEnabled: true,
    bookingNotifications: true,
    paymentNotifications: true,
    tripChangeNotifications: true,
    emailNotifications: true,
    
    // Privacy
    privacyLevel: 'standard',
    dataSharing: false,
    autoDeleteConversations: false,
    autoDeleteDays: 30,
    
    // AI Agent
    chatLanguage: 'th',
    responseStyle: 'balanced',
    detailLevel: 'medium',
    reinforcementLearning: true,
    agentPersonality: 'friendly',
    
    // Booking Preferences
    defaultPaymentMethod: user?.payment_method || '',
    
    // Theme & Display
    theme: 'light',
    fontSize: 'medium',
    language: 'th',
  });

  const [isSaving, setIsSaving] = useState(false);
  const [showDeletePopup, setShowDeletePopup] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [changePasswordData, setChangePasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  });
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [showUpdateEmail, setShowUpdateEmail] = useState(false);
  const [newEmail, setNewEmail] = useState('');
  // เปลี่ยนเบอร์โทร (OTP)
  const [showChangePhone, setShowChangePhone] = useState(false);
  const [newPhone, setNewPhone] = useState('');
  const [phoneOtp, setPhoneOtp] = useState('');
  const [phoneOtpSent, setPhoneOtpSent] = useState(false);
  const [phoneOtpLoading, setPhoneOtpLoading] = useState(false);
  const [phoneError, setPhoneError] = useState('');

  useEffect(() => {
    // Load settings from user preferences
    if (user?.preferences) {
      setSettings(prev => ({
        ...prev,
        ...user.preferences
      }));
    }
  }, [user]);

  // Sync email_verified from Firebase when user is Firebase (after they verified via Firebase link)
  useEffect(() => {
    if (user?.auth_provider !== 'firebase' || activeSection !== 'account' || !onRefreshUser) return;
    let cancelled = false;
    (async () => {
      try {
        const { auth } = await import('../../config/firebase.js');
        if (!auth?.currentUser) return;
        const idToken = await auth.currentUser.getIdToken(true);
        if (cancelled) return;
        const res = await fetch(`${API_BASE_URL}/api/auth/firebase-refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ idToken }),
        });
        if (cancelled) return;
        const data = await res.json();
        if (res.ok && data.ok && data.user) {
          onRefreshUser();
        }
      } catch (e) {
        if (!cancelled) console.debug('Firebase refresh sync:', e);
      }
    })();
    return () => { cancelled = true; };
  }, [user?.auth_provider, activeSection, onRefreshUser]);

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          preferences: settings
        })
      });
      
      const data = await res.json();
      if (data.ok) {
        alert('บันทึกการตั้งค่าสำเร็จ');
        if (onRefreshUser) {
          onRefreshUser();
        }
      } else {
        throw new Error(data.detail || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      alert(`เกิดข้อผิดพลาดในการบันทึก: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleChangePassword = async () => {
    if (changePasswordData.newPassword !== changePasswordData.confirmPassword) {
      alert('รหัสผ่านใหม่ไม่ตรงกัน');
      return;
    }
    
    if (changePasswordData.newPassword.length < 6) {
      alert('รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร');
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          current_password: changePasswordData.currentPassword,
          new_password: changePasswordData.newPassword
        })
      });
      
      const data = await res.json();
      if (data.ok) {
        alert('เปลี่ยนรหัสผ่านสำเร็จ');
        setChangePasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
        setShowChangePassword(false);
      } else {
        throw new Error(data.detail || 'Failed to change password');
      }
    } catch (error) {
      console.error('Error changing password:', error);
      alert(`เกิดข้อผิดพลาด: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleUpdateEmail = async () => {
    if (!newEmail || !newEmail.includes('@')) {
      alert('กรุณากรอกอีเมลที่ถูกต้อง');
      return;
    }

    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/update-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          new_email: newEmail
        })
      });
      
      const data = await res.json();
      if (data.ok) {
        const updatedEmail = data.email || newEmail;
        setNewEmail('');
        setShowUpdateEmail(false);
        if (onRefreshUser) {
          onRefreshUser();
        }
        if (onUpdateEmailSuccess) {
          onUpdateEmailSuccess(updatedEmail);
        } else {
          alert('ส่งอีเมลยืนยันไปยังอีเมลใหม่แล้ว กรุณาตรวจสอบอีเมล');
        }
      } else {
        throw new Error(data.detail || 'Failed to update email');
      }
    } catch (error) {
      console.error('Error updating email:', error);
      alert(`เกิดข้อผิดพลาด: ${error.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSendVerificationEmail = async () => {
    const isFirebaseUser = user?.auth_provider === 'firebase';
    if (isFirebaseUser) {
      try {
        const { auth, sendEmailVerification } = await import('../../config/firebase.js');
        if (!auth?.currentUser) {
          alert('กรุณารีเฟรชหรือเข้าสู่ระบบด้วย Firebase อีกครั้ง เพื่อส่งอีเมลยืนยัน');
          return;
        }
        await sendEmailVerification(auth.currentUser);
        if (onSendVerificationEmailSuccess) {
          onSendVerificationEmailSuccess(auth.currentUser?.email || user?.email);
        } else {
          alert('ส่งอีเมลยืนยันแล้ว (Firebase) กรุณาตรวจสอบอีเมล เมื่อยืนยันแล้วให้รีเฟรชหรือกลับมาหน้านี้');
        }
      } catch (error) {
        console.error('Firebase sendEmailVerification error:', error);
        alert(`เกิดข้อผิดพลาด: ${error.message || 'ส่งอีเมลยืนยันไม่สำเร็จ'}`);
      }
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/send-verification-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include'
      });
      
      const data = await res.json();
      if (data.ok) {
        if (onSendVerificationEmailSuccess) {
          onSendVerificationEmailSuccess(data.email || user?.email);
        } else {
          alert('ส่งอีเมลยืนยันแล้ว กรุณาตรวจสอบอีเมล');
        }
      } else {
        throw new Error(data.detail || 'Failed to send verification email');
      }
    } catch (error) {
      console.error('Error sending verification email:', error);
      alert(`เกิดข้อผิดพลาด: ${error.message}`);
    }
  };

  const handleConfirmDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: 'DELETE',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' }
      });
      
      const data = await res.json();
      if (res.ok && data.ok) {
        alert('บัญชีถูกลบเรียบร้อยแล้ว');
        localStorage.clear();
        sessionStorage.clear();
        setShowDeletePopup(false);
        if (onLogout) {
          onLogout();
        } else {
          window.location.href = '/';
        }
      } else {
        throw new Error(data.detail || 'Failed to delete account');
      }
    } catch (error) {
      console.error('Delete account error:', error);
      alert(`เกิดข้อผิดพลาดในการลบบัญชี: ${error.message || 'Unknown error'}`);
    } finally {
      setIsDeleting(false);
    }
  };

  const agentPersonalityTemplates = {
    friendly: { name: 'เป็นมิตร', description: 'พูดคุยแบบเป็นกันเอง อบอุ่น' },
    professional: { name: 'มืออาชีพ', description: 'เป็นทางการ ชัดเจน ตรงไปตรงมา' },
    casual: { name: 'สบายๆ', description: 'พูดคุยแบบไม่เป็นทางการ สนุกสนาน' },
    teenager: { name: 'เพื่อนวัยรุ่น', description: 'พูดคุยแบบวัยรุ่น ใช้ภาษาสมัยใหม่ สนุกสนาน' },
    detailed: { name: 'ละเอียด', description: 'ให้ข้อมูลครบถ้วน รายละเอียดเยอะ' },
    concise: { name: 'กระชับ', description: 'ตอบสั้นๆ ตรงประเด็น' }
  };

  const renderAccountSettings = () => (
    <div className="settings-section">
      <h3>การตั้งค่าบัญชี</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>เปลี่ยนรหัสผ่าน</label>
        </div>
        <div className="settings-item-control">
          {!showChangePassword ? (
            <button 
              className="btn-secondary"
              onClick={() => setShowChangePassword(true)}
            >
              เปลี่ยนรหัสผ่าน
            </button>
          ) : (
            <div className="password-change-form">
              <input
                type="password"
                placeholder="รหัสผ่านปัจจุบัน"
                value={changePasswordData.currentPassword}
                onChange={(e) => setChangePasswordData(prev => ({ ...prev, currentPassword: e.target.value }))}
                className="form-input"
              />
              <input
                type="password"
                placeholder="รหัสผ่านใหม่"
                value={changePasswordData.newPassword}
                onChange={(e) => setChangePasswordData(prev => ({ ...prev, newPassword: e.target.value }))}
                className="form-input"
              />
              <input
                type="password"
                placeholder="ยืนยันรหัสผ่านใหม่"
                value={changePasswordData.confirmPassword}
                onChange={(e) => setChangePasswordData(prev => ({ ...prev, confirmPassword: e.target.value }))}
                className="form-input"
              />
              <div className="form-actions">
                <button className="btn-secondary" onClick={() => setShowChangePassword(false)}>
                  ยกเลิก
                </button>
                <button className="btn-primary" onClick={handleChangePassword} disabled={isSaving}>
                  {isSaving ? 'กำลังบันทึก...' : 'บันทึก'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>อัปเดตอีเมล</label>
          <small>อีเมลปัจจุบัน: {user?.email}</small>
        </div>
        <div className="settings-item-control">
          {!showUpdateEmail ? (
            <button 
              className="btn-secondary"
              onClick={() => setShowUpdateEmail(true)}
            >
              เปลี่ยนอีเมล
            </button>
          ) : (
            <div className="email-update-form">
              <input
                type="email"
                placeholder="อีเมลใหม่"
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                className="form-input"
              />
              <div className="form-actions">
                <button className="btn-secondary" onClick={() => setShowUpdateEmail(false)}>
                  ยกเลิก
                </button>
                <button className="btn-primary" onClick={handleUpdateEmail} disabled={isSaving}>
                  {isSaving ? 'กำลังบันทึก...' : 'บันทึก'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>สถานะการยืนยันอีเมล</label>
          <small>
            {settings.emailVerified ? (
              <span style={{ color: 'green' }}>✓ ยืนยันแล้ว</span>
            ) : (
              <span style={{ color: '#6b7280' }}>ยังไม่ยืนยัน</span>
            )}
          </small>
        </div>
        <div className="settings-item-control">
          {!settings.emailVerified && (
            <button 
              className="btn-secondary"
              onClick={handleSendVerificationEmail}
            >
              ส่งอีเมลยืนยัน
            </button>
          )}
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>อัปเดตเบอร์โทรศัพท์</label>
          <small>เบอร์ปัจจุบัน: {user?.phone || '—'}</small>
        </div>
        <div className="settings-item-control">
          {!showChangePhone ? (
            <button
              className="btn-secondary"
              onClick={() => {
                setShowChangePhone(true);
                setNewPhone('');
                setPhoneOtp('');
                setPhoneOtpSent(false);
                setPhoneError('');
              }}
            >
              เปลี่ยนเบอร์โทร
            </button>
          ) : (
            <div className="phone-otp-flow" style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxWidth: '320px' }}>
              {!phoneOtpSent ? (
                <>
                  <input
                    type="tel"
                    value={newPhone}
                    onChange={(e) => setNewPhone(e.target.value)}
                    placeholder="เบอร์ใหม่ เช่น 0812345678"
                    className="form-input"
                  />
                  {phoneError && <small style={{ color: '#dc2626' }}>{phoneError}</small>}
                  <div className="form-actions" style={{ display: 'flex', gap: '8px' }}>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={phoneOtpLoading || !/^0[689]\d{8}$|^0[2-9]\d{7,8}$/.test(newPhone.replace(/[-\s()]/g, ''))}
                      onClick={async () => {
                        const cleaned = newPhone.replace(/[-\s()]/g, '');
                        if (!/^0[689]\d{8}$|^0[2-9]\d{7,8}$/.test(cleaned)) {
                          setPhoneError('รูปแบบเบอร์โทรไม่ถูกต้อง (เช่น 0812345678)');
                          return;
                        }
                        setPhoneOtpLoading(true);
                        setPhoneError('');
                        try {
                          const res = await fetch(`${API_BASE_URL}/api/auth/send-phone-otp`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify({ new_phone: cleaned }),
                          });
                          const data = await res.json();
                          if (res.ok && data.ok) {
                            setPhoneOtpSent(true);
                            setPhoneOtp('');
                          } else {
                            setPhoneError(data.detail || 'ส่ง OTP ไม่สำเร็จ');
                          }
                        } catch (err) {
                          setPhoneError(err.message || 'ส่ง OTP ไม่สำเร็จ');
                        } finally {
                          setPhoneOtpLoading(false);
                        }
                      }}
                    >
                      {phoneOtpLoading ? 'กำลังส่ง...' : 'ส่ง OTP'}
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => { setShowChangePhone(false); setNewPhone(''); setPhoneOtpSent(false); setPhoneError(''); }}>ยกเลิก</button>
                  </div>
                </>
              ) : (
                <>
                  <input
                    type="text"
                    value={phoneOtp}
                    onChange={(e) => setPhoneOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                    placeholder="รหัส OTP 6 หลัก"
                    className="form-input"
                    maxLength={6}
                  />
                  {phoneError && <small style={{ color: '#dc2626' }}>{phoneError}</small>}
                  <div className="form-actions" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn-primary"
                      disabled={phoneOtpLoading || phoneOtp.length !== 6}
                      onClick={async () => {
                        setPhoneOtpLoading(true);
                        setPhoneError('');
                        try {
                          const res = await fetch(`${API_BASE_URL}/api/auth/verify-phone`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            credentials: 'include',
                            body: JSON.stringify({ otp: phoneOtp }),
                          });
                          const data = await res.json();
                          if (res.ok && data.ok) {
                            setShowChangePhone(false);
                            setNewPhone('');
                            setPhoneOtp('');
                            setPhoneOtpSent(false);
                            if (onRefreshUser) onRefreshUser();
                          } else {
                            setPhoneError(data.detail || 'รหัส OTP ไม่ถูกต้อง');
                          }
                        } catch (err) {
                          setPhoneError(err.message || 'ยืนยัน OTP ไม่สำเร็จ');
                        } finally {
                          setPhoneOtpLoading(false);
                        }
                      }}
                    >
                      {phoneOtpLoading ? 'กำลังยืนยัน...' : 'ยืนยัน OTP'}
                    </button>
                    <button type="button" className="btn-secondary" onClick={() => { setPhoneOtpSent(false); setPhoneOtp(''); setPhoneError(''); }}>ส่ง OTP ใหม่</button>
                    <button type="button" className="btn-secondary" onClick={() => { setShowChangePhone(false); setNewPhone(''); setPhoneOtp(''); setPhoneOtpSent(false); setPhoneError(''); }}>ยกเลิก</button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>เชื่อมต่อบัญชี</label>
          <small>ผู้ให้บริการ: {settings.authProvider === 'google' ? 'Google' : settings.authProvider === 'firebase' ? 'Firebase' : 'Email/Password'}</small>
        </div>
        <div className="settings-item-control">
          <button className="btn-secondary" disabled>
            {settings.authProvider === 'google' || settings.authProvider === 'firebase' ? 'เชื่อมต่อแล้ว' : 'เชื่อมต่อ Google'}
          </button>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ลบบัญชี</label>
          <small style={{ color: '#d32f2f' }}>⚠️ การลบบัญชีจะลบข้อมูลทั้งหมดอย่างถาวร</small>
        </div>
        <div className="settings-item-control">
          <button 
            className="btn-danger"
            onClick={() => setShowDeletePopup(true)}
          >
            ลบบัญชี
          </button>
        </div>
      </div>
    </div>
  );

  const renderNotifications = () => (
    <div className="settings-section">
      <h3>การแจ้งเตือน</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>เปิด/ปิดการแจ้งเตือน</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.notificationsEnabled}
              onChange={(e) => handleSettingChange('notificationsEnabled', e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การแจ้งเตือนการจอง</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.bookingNotifications}
              onChange={(e) => handleSettingChange('bookingNotifications', e.target.checked)}
              disabled={!settings.notificationsEnabled}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การแจ้งเตือนสถานะการชำระเงิน</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.paymentNotifications}
              onChange={(e) => handleSettingChange('paymentNotifications', e.target.checked)}
              disabled={!settings.notificationsEnabled}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การแจ้งเตือนการเปลี่ยนแปลงทริป</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.tripChangeNotifications}
              onChange={(e) => handleSettingChange('tripChangeNotifications', e.target.checked)}
              disabled={!settings.notificationsEnabled}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การแจ้งเตือนทางอีเมล</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.emailNotifications}
              onChange={(e) => handleSettingChange('emailNotifications', e.target.checked)}
              disabled={!settings.notificationsEnabled}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>
    </div>
  );

  const renderPrivacy = () => (
    <div className="settings-section">
      <h3>ความเป็นส่วนตัว</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>ระดับความเป็นส่วนตัว</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.privacyLevel}
            onChange={(e) => handleSettingChange('privacyLevel', e.target.value)}
            className="form-select"
          >
            <option value="public">สาธารณะ</option>
            <option value="standard">มาตรฐาน</option>
            <option value="private">ส่วนตัว</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การแชร์ข้อมูล</label>
          <small>อนุญาตให้แชร์ข้อมูลเพื่อปรับปรุงบริการ</small>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.dataSharing}
              onChange={(e) => handleSettingChange('dataSharing', e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>การลบข้อมูลการสนทนา (Auto-delete)</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.autoDeleteConversations}
              onChange={(e) => handleSettingChange('autoDeleteConversations', e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      {settings.autoDeleteConversations && (
        <div className="settings-item">
          <div className="settings-item-label">
            <label>ลบอัตโนมัติหลังจาก (วัน)</label>
          </div>
          <div className="settings-item-control">
            <input
              type="number"
              min="1"
              max="365"
              value={settings.autoDeleteDays}
              onChange={(e) => handleSettingChange('autoDeleteDays', parseInt(e.target.value))}
              className="form-input"
              style={{ width: '100px' }}
            />
          </div>
        </div>
      )}
    </div>
  );

  const renderAIAgent = () => (
    <div className="settings-section">
      <h3>การตั้งค่า AI Agent</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>ภาษาในการสนทนา</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.chatLanguage}
            onChange={(e) => handleSettingChange('chatLanguage', e.target.value)}
            className="form-select"
          >
            <option value="th">ไทย</option>
            <option value="en">English</option>
            <option value="auto">อัตโนมัติ</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>รูปแบบการตอบกลับ</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.responseStyle}
            onChange={(e) => handleSettingChange('responseStyle', e.target.value)}
            className="form-select"
          >
            <option value="short">สั้น</option>
            <option value="balanced">สมดุล</option>
            <option value="long">ยาว</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ระดับความละเอียดของคำแนะนำ</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.detailLevel}
            onChange={(e) => handleSettingChange('detailLevel', e.target.value)}
            className="form-select"
          >
            <option value="low">ต่ำ</option>
            <option value="medium">ปานกลาง</option>
            <option value="high">สูง</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>เปิด/ปิด Reinforcement Learning</label>
          <small>เรียนรู้จากพฤติกรรมผู้ใช้เพื่อปรับปรุงคำแนะนำ</small>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.reinforcementLearning}
              onChange={(e) => handleSettingChange('reinforcementLearning', e.target.checked)}
            />
            <span className="toggle-slider"></span>
          </label>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>บุคลิก Agent</label>
          <small>เลือกบุคลิกของ AI Agent ให้เข้ากับคุณ</small>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.agentPersonality}
            onChange={(e) => handleSettingChange('agentPersonality', e.target.value)}
            className="form-select"
          >
            {Object.entries(agentPersonalityTemplates).map(([key, template]) => (
              <option key={key} value={key}>
                {template.name} - {template.description}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );

  const renderBookingPreferences = () => (
    <div className="settings-section">
      <h3>การตั้งค่าการจอง</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>วิธีการชำระเงินเริ่มต้น</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.defaultPaymentMethod}
            onChange={(e) => handleSettingChange('defaultPaymentMethod', e.target.value)}
            className="form-select"
          >
            <option value="">-- เลือก --</option>
            <option value="CREDIT_CARD">บัตรเครดิต</option>
            <option value="DEBIT_CARD">บัตรเดบิต</option>
            <option value="BANK_TRANSFER">โอนเงิน</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ข้อมูลบัตรเครดิต</label>
          <small>{user?.card_holder_name ? `${user.card_holder_name} •••• ${user.card_last_4_digits}` : 'ยังไม่ได้บันทึก'}</small>
        </div>
        <div className="settings-item-control">
          <button 
            className="btn-secondary"
            onClick={() => onNavigateToProfile && onNavigateToProfile()}
          >
            จัดการ
          </button>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ข้อมูลใบกำกับภาษี</label>
          <small>{user?.company_name ? user.company_name : 'ยังไม่ได้บันทึก'}</small>
        </div>
        <div className="settings-item-control">
          <button 
            className="btn-secondary"
            onClick={() => onNavigateToProfile && onNavigateToProfile()}
          >
            จัดการ
          </button>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>โปรแกรมสะสมแต้ม/ไมล์</label>
          <small>
            {user?.hotel_loyalty_number || user?.airline_frequent_flyer 
              ? `${user.hotel_loyalty_number || ''} ${user.airline_frequent_flyer || ''}`.trim()
              : 'ยังไม่ได้บันทึก'}
          </small>
        </div>
        <div className="settings-item-control">
          <button 
            className="btn-secondary"
            onClick={() => onNavigateToProfile && onNavigateToProfile()}
          >
            จัดการ
          </button>
        </div>
      </div>
    </div>
  );

  const renderThemeDisplay = () => (
    <div className="settings-section">
      <h3>ธีมและการแสดงผล</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>โหมดสี</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.theme}
            onChange={(e) => handleSettingChange('theme', e.target.value)}
            className="form-select"
          >
            <option value="light">สว่าง</option>
            <option value="dark">มืด</option>
            <option value="auto">อัตโนมัติ</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ขนาดตัวอักษร</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.fontSize}
            onChange={(e) => handleSettingChange('fontSize', e.target.value)}
            className="form-select"
          >
            <option value="small">เล็ก</option>
            <option value="medium">ปานกลาง</option>
            <option value="large">ใหญ่</option>
          </select>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ภาษา</label>
        </div>
        <div className="settings-item-control">
          <select
            value={settings.language}
            onChange={(e) => handleSettingChange('language', e.target.value)}
            className="form-select"
          >
            <option value="th">ไทย</option>
            <option value="en">English</option>
          </select>
        </div>
      </div>
    </div>
  );

  const renderAbout = () => (
    <div className="settings-section">
      <h3>เกี่ยวกับ</h3>
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>เวอร์ชันแอป</label>
        </div>
        <div className="settings-item-control">
          <span>1.0.0</span>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>เงื่อนไขการใช้งาน</label>
        </div>
        <div className="settings-item-control">
          <button className="btn-link">ดูเงื่อนไขการใช้งาน</button>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>นโยบายความเป็นส่วนตัว</label>
        </div>
        <div className="settings-item-control">
          <button className="btn-link">ดูนโยบายความเป็นส่วนตัว</button>
        </div>
      </div>

      <div className="settings-item">
        <div className="settings-item-label">
          <label>ติดต่อผู้ดูแลระบบ</label>
        </div>
        <div className="settings-item-control">
          <a href="mailto:support@aitravelagent.com" className="btn-link">
            support@aitravelagent.com
          </a>
        </div>
      </div>
    </div>
  );

  const sections = [
    { id: 'account', name: 'การตั้งค่าบัญชี', icon: '👤' },
    { id: 'notifications', name: 'การแจ้งเตือน', icon: '🔔' },
    { id: 'privacy', name: 'ความเป็นส่วนตัว', icon: '🔒' },
    { id: 'ai-agent', name: 'การตั้งค่า AI Agent', icon: '🤖' },
    { id: 'booking', name: 'การตั้งค่าการจอง', icon: '📅' },
    { id: 'theme', name: 'ธีมและการแสดงผล', icon: '🎨' },
    { id: 'about', name: 'เกี่ยวกับ', icon: 'ℹ️' }
  ];

  return (
    <div className="settings-page">
      <AppHeader
        user={user}
        onLogout={onLogout}
        onNavigateToHome={onNavigateToHome}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        notificationCount={notificationCount}
      />
      
      <div className="settings-container">
        <div className="settings-sidebar">
          <h2>การตั้งค่า</h2>
          <nav className="settings-nav">
            {sections.map(section => (
              <button
                key={section.id}
                className={`settings-nav-item ${activeSection === section.id ? 'active' : ''}`}
                onClick={() => setActiveSection(section.id)}
              >
                <span className="settings-nav-icon">{section.icon}</span>
                <span>{section.name}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="settings-content">
          {activeSection === 'account' && renderAccountSettings()}
          {activeSection === 'notifications' && renderNotifications()}
          {activeSection === 'privacy' && renderPrivacy()}
          {activeSection === 'ai-agent' && renderAIAgent()}
          {activeSection === 'booking' && renderBookingPreferences()}
          {activeSection === 'theme' && renderThemeDisplay()}
          {activeSection === 'about' && renderAbout()}

          <div className="settings-actions">
            <button 
              className="btn-primary"
              onClick={handleSaveSettings}
              disabled={isSaving}
            >
              {isSaving ? 'กำลังบันทึก...' : 'บันทึกการตั้งค่า'}
            </button>
          </div>
        </div>
      </div>

      {/* Delete Account Popup */}
      {showDeletePopup && (
        <div 
          className="delete-account-popup-overlay"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000
          }}
          onClick={() => setShowDeletePopup(false)}
        >
          <div 
            className="delete-account-popup"
            style={{
              backgroundColor: 'white',
              borderRadius: '12px',
              padding: '32px',
              maxWidth: '500px',
              width: '90%',
              boxShadow: '0 4px 20px rgba(0, 0, 0, 0.3)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ color: '#d32f2f', marginBottom: '16px' }}>🗑️ ลบบัญชี</h3>
            <p style={{ color: '#666', marginBottom: '20px' }}>
              การลบบัญชีจะลบข้อมูลทั้งหมดของคุณอย่างถาวร รวมถึง:
            </p>
            <ul style={{ marginBottom: '20px', paddingLeft: '20px', color: '#666' }}>
              <li>ข้อมูลโปรไฟล์</li>
              <li>ประวัติการจองทั้งหมด</li>
              <li>ประวัติการสนทนา</li>
              <li>ความจำและความชอบ</li>
              <li>การแจ้งเตือนทั้งหมด</li>
            </ul>
            <div style={{ 
              backgroundColor: '#fff3cd', 
              border: '1px solid #ffc107', 
              borderRadius: '6px', 
              padding: '12px', 
              marginBottom: '24px'
            }}>
              <strong style={{ color: '#d32f2f' }}>⚠️ การกระทำนี้ไม่สามารถยกเลิกได้!</strong>
            </div>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setShowDeletePopup(false)}
                disabled={isDeleting}
                className="btn-secondary"
              >
                ยกเลิก
              </button>
              <button
                onClick={handleConfirmDeleteAccount}
                disabled={isDeleting}
                className="btn-danger"
              >
                {isDeleting ? 'กำลังลบบัญชี...' : 'ยืนยันลบบัญชี'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
