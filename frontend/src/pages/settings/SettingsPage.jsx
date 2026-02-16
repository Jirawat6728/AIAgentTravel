import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import { formatCardNumber, getCardType, validateCardNumber } from '../../utils/cardUtils';
import { sha256Password } from '../../utils/passwordHash.js';
import './SettingsPage.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

/** โลโก้บัตรเครดิตแบบขาว สำหรับใช้บนพื้นหลังสีเข้ม — ใช้ในส่วนบัตรที่บันทึกไว้ */
const CARD_LOGO_SVG = {
  visa: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="16" textAnchor="middle" fill="currentColor" fontSize="14" fontWeight="700" fontFamily="Arial,sans-serif">VISA</text>
    </svg>
  ),
  mastercard: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <circle cx="20" cy="12" r="8" fill="rgba(255,255,255,0.9)" />
      <circle cx="36" cy="12" r="8" fill="rgba(255,255,255,0.7)" />
      <path fill="rgba(255,255,255,0.85)" fillOpacity="0.9" d="M28 4a8 8 0 0 1 0 16 8 8 0 0 1 0-16z" />
    </svg>
  ),
  amex: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="10" textAnchor="middle" fill="currentColor" fontSize="5" fontWeight="700" fontFamily="Arial,sans-serif">AMERICAN</text>
      <text x="28" y="17" textAnchor="middle" fill="currentColor" fontSize="5" fontWeight="700" fontFamily="Arial,sans-serif">EXPRESS</text>
    </svg>
  ),
  jcb: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="16" textAnchor="middle" fill="currentColor" fontSize="14" fontWeight="700" fontFamily="Arial,sans-serif">JCB</text>
    </svg>
  ),
  discover: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="15" textAnchor="middle" fill="currentColor" fontSize="8" fontWeight="700" fontFamily="Arial,sans-serif">Discover</text>
    </svg>
  ),
  diners: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="15" textAnchor="middle" fill="currentColor" fontSize="7" fontWeight="700" fontFamily="Arial,sans-serif">Diners Club</text>
    </svg>
  ),
  unionpay: (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="15" textAnchor="middle" fill="currentColor" fontSize="8" fontWeight="700" fontFamily="Arial,sans-serif">UnionPay</text>
    </svg>
  ),
};

function CardBrandLogo({ brand, className = '' }) {
  const key = (brand || 'card').toLowerCase().replace(/\s+/g, '').replace('americanexpress', 'amex');
  const logo = CARD_LOGO_SVG[key] || (
    <svg viewBox="0 0 56 24" width="48" height="20" xmlns="http://www.w3.org/2000/svg">
      <text x="28" y="15" textAnchor="middle" fill="currentColor" fontSize="10" fontWeight="700" fontFamily="Arial,sans-serif">Card</text>
    </svg>
  );
  return <span className={`card-brand-logo ${className}`} style={{ color: 'inherit', display: 'inline-flex' }}>{logo}</span>;
}

export { CardBrandLogo };

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
  const [notificationSaveStatus, setNotificationSaveStatus] = useState(null);
  const [notificationSaveError, setNotificationSaveError] = useState(null);
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
  // บัตรเครดิต/เดบิต (saved cards)
  const [savedCards, setSavedCards] = useState([]);
  const [primaryCardId, setPrimaryCardId] = useState(null);
  const [cardsLoading, setCardsLoading] = useState(false);
  const [cardsError, setCardsError] = useState(null);
  const [deletingCardId, setDeletingCardId] = useState(null);
  const [settingPrimaryId, setSettingPrimaryId] = useState(null);

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

  // โหลดรายการบัตรเมื่อเปิดหมวดบัตรเครดิต/เดบิต
  useEffect(() => {
    if (activeSection !== 'cards' || !user?.id) return;
    setCardsLoading(true);
    setCardsError(null);
    const headers = { 'X-User-ID': user.id };
    fetch(`${API_BASE_URL}/api/booking/saved-cards`, { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('โหลดบัตรไม่สำเร็จ'))))
      .then((data) => {
        if (data.ok && Array.isArray(data.cards)) setSavedCards(data.cards);
        if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
      })
      .catch((err) => setCardsError(err.message || 'โหลดบัตรไม่สำเร็จ'))
      .finally(() => setCardsLoading(false));
  }, [activeSection, user?.id]);


  const handleClickAddCard = () => {
    Swal.fire({
      title: '💳 เพิ่มบัตรใหม่',
      customClass: { popup: 'add-card-popup' },
      html: `
        <div style="text-align: left;">
          <div class="add-card-field">
            <label class="add-card-label" for="swal-card-number">หมายเลขบัตร</label>
            <input id="swal-card-number" type="text" class="add-card-input" placeholder="1234 5678 9012 3456" maxlength="19" />
            <div id="swal-card-type-display" class="add-card-type-display" aria-live="polite"></div>
          </div>
          <div class="add-card-field">
            <label class="add-card-label" for="swal-card-name">ชื่อบนบัตร</label>
            <input id="swal-card-name" type="text" class="add-card-input" placeholder="ชื่อ-นามสกุล" />
          </div>
          <div class="add-card-row">
            <div class="add-card-field">
              <label class="add-card-label" for="swal-card-expiry">หมดอายุ (MM/YY)</label>
              <input id="swal-card-expiry" type="text" class="add-card-input" placeholder="MM/YY" maxlength="5" />
            </div>
            <div class="add-card-field">
              <label class="add-card-label" for="swal-card-cvv">CVV</label>
              <input id="swal-card-cvv" type="text" class="add-card-input" placeholder="123" maxlength="4" />
            </div>
          </div>
        </div>
      `,
      showCancelButton: true,
      confirmButtonText: 'บันทึก',
      cancelButtonText: 'ยกเลิก',
      width: 440,
      didOpen: () => {
        const input = document.getElementById('swal-card-number');
        const display = document.getElementById('swal-card-type-display');
        if (!input || !display) return;
        const logos = {
          visa: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" fill="#fff" rx="2"/><text x="28" y="16" text-anchor="middle" fill="#1A1F71" font-size="12" font-weight="700" font-family="Arial,sans-serif">VISA</text></svg>',
          mastercard: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><circle cx="20" cy="12" r="8" fill="#EB001B"/><circle cx="36" cy="12" r="8" fill="#F79E1B"/><path fill="#E85A00" fill-opacity="0.9" d="M28 4a8 8 0 0 1 0 16 8 8 0 0 1 0-16z"/></svg>',
          amex: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#006FCF"/><text x="28" y="9.5" text-anchor="middle" fill="#fff" font-size="5" font-weight="700" font-family="Arial,sans-serif">AMERICAN</text><text x="28" y="17.5" text-anchor="middle" fill="#fff" font-size="5" font-weight="700" font-family="Arial,sans-serif">EXPRESS</text></svg>',
          jcb: '<img src="/images/jcb-logo.png" alt="JCB" class="card-logo-img" width="48" height="22" />',
          discover: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#FF6000"/><text x="28" y="15.5" text-anchor="middle" fill="#fff" font-size="7" font-weight="700" font-family="Arial,sans-serif">Discover</text></svg>',
          diners: '<svg viewBox="0 0 56 24" width="48" height="22" xmlns="http://www.w3.org/2000/svg"><rect width="56" height="24" rx="3" fill="#0079BE"/><text x="28" y="15.5" text-anchor="middle" fill="#fff" font-size="6" font-weight="700" font-family="Arial,sans-serif">Diners Club</text></svg>',
          unionpay: '<img src="/images/unionpay-logo.png" alt="UnionPay" class="card-logo-img" width="48" height="22" />'
        };
        const update = () => {
          const raw = input.value.replace(/\D/g, '');
          input.value = formatCardNumber(input.value);
          input.classList.remove('card-visa', 'card-mastercard', 'card-amex', 'card-jcb', 'card-discover', 'card-diners', 'card-unionpay');
          if (raw.length >= 2) {
            const cardType = getCardType(input.value);
            let html = '';
            if (cardType && logos[cardType]) {
              html = '<span class="card-logo-wrap">' + logos[cardType] + '</span>';
              input.classList.add('card-' + cardType);
            }
            display.innerHTML = html;
            display.className = 'add-card-type-display ' + (cardType ? 'visible' : '');
            if (raw.length >= 13) {
              const v = validateCardNumber(input.value);
              const statusSpan = v.valid ? '<span class="card-logo-valid">✓ ถูกต้อง</span>' : '<span class="card-logo-invalid">' + (v.message || 'ไม่ถูกต้อง') + '</span>';
              display.innerHTML = (cardType && logos[cardType] ? '<span class="card-logo-wrap">' + logos[cardType] + '</span>' : '') + statusSpan;
              display.className = 'add-card-type-display visible ' + (v.valid ? 'valid' : 'invalid');
            }
          } else {
            display.innerHTML = '';
            display.className = 'add-card-type-display';
          }
        };
        input.addEventListener('input', update);
        input.addEventListener('paste', () => setTimeout(update, 0));

        const expiryInput = document.getElementById('swal-card-expiry');
        if (expiryInput) {
          const formatExpiry = (val) => {
            const c = (val || '').replace(/\D/g, '');
            if (c.length >= 2) return c.substring(0, 2) + '/' + c.substring(2, 4);
            return c;
          };
          expiryInput.addEventListener('input', (e) => {
            e.target.value = formatExpiry(e.target.value);
            e.target.setSelectionRange(e.target.value.length, e.target.value.length);
          });
          expiryInput.addEventListener('paste', () => setTimeout(() => { expiryInput.value = formatExpiry(expiryInput.value); }, 0));
        }
      },
      preConfirm: () => {
        const cardNumber = (document.getElementById('swal-card-number')?.value || '').replace(/\s/g, '');
        const cardName = (document.getElementById('swal-card-name')?.value || '').trim();
        const cardExpiry = (document.getElementById('swal-card-expiry')?.value || '').trim();
        const cardCvv = (document.getElementById('swal-card-cvv')?.value || '').replace(/\s/g, '');

        if (!cardNumber) {
          Swal.showValidationMessage('กรุณากรอกหมายเลขบัตร');
          return false;
        }
        if (cardNumber.length < 13) {
          Swal.showValidationMessage('กรุณากรอกหมายเลขบัตรอย่างน้อย 13 หลัก');
          return false;
        }
        const v = validateCardNumber(document.getElementById('swal-card-number')?.value);
        if (!v.valid) {
          Swal.showValidationMessage(v.message || 'เลขบัตรไม่ถูกต้อง');
          return false;
        }

        if (!cardName || cardName.length < 2) {
          Swal.showValidationMessage('กรุณากรอกชื่อบนบัตร (อย่างน้อย 2 ตัวอักษร)');
          return false;
        }

        const parts = cardExpiry.split('/').map((p) => p.trim());
        if (parts.length !== 2 || parts[0].length !== 2 || parts[1].length !== 2) {
          Swal.showValidationMessage('กรุณากรอกวันหมดอายุรูปแบบ MM/YY');
          return false;
        }
        const mm = parseInt(parts[0], 10);
        const yy = parseInt(parts[1], 10);
        if (mm < 1 || mm > 12) {
          Swal.showValidationMessage('เดือนต้องอยู่ระหว่าง 01-12');
          return false;
        }
        const now = new Date();
        const fullYear = 2000 + yy;
        const expDate = new Date(fullYear, mm, 0);
        if (expDate < now) {
          Swal.showValidationMessage('บัตรหมดอายุแล้ว');
          return false;
        }

        if (!cardCvv || !/^\d{3,4}$/.test(cardCvv)) {
          Swal.showValidationMessage('กรุณากรอก CVV ให้ถูกต้อง (3-4 หลัก)');
          return false;
        }

        return { cardNumber, cardName, cardExpiry, cardCvv };
      }
    }).then(async (result) => {
      if (result.isConfirmed && result.value) {
        const { cardNumber, cardName, cardExpiry, cardCvv } = result.value;
        const last4 = cardNumber.replace(/\s/g, '').slice(-4);
        const brand = getCardType(cardNumber) || 'visa';
        const [mm, yy] = cardExpiry.split('/').map((p) => p.trim());
        try {
          const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards/add-local`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-User-ID': user?.id || '' },
            credentials: 'include',
            body: JSON.stringify({ last4, brand, expiry_month: mm, expiry_year: yy, name: cardName })
          });
          const data = await res.json();
          if (data.ok) {
            setSavedCards(data.cards || []);
            if (data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
            Swal.fire({ icon: 'success', title: 'บันทึกสำเร็จ', text: 'บัตรของคุณถูกบันทึกแล้ว', confirmButtonText: 'ตกลง' });
          } else {
            throw new Error(data.detail || 'บันทึกไม่สำเร็จ');
          }
        } catch (err) {
          Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message || 'บันทึกบัตรไม่สำเร็จ', confirmButtonText: 'ตกลง' });
        }
      }
    });
  };

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const savePreferencesToBackend = async (prefs) => {
    const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...(user?.id && { 'X-User-ID': user.id }) },
      credentials: 'include',
      body: JSON.stringify({ preferences: prefs })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'บันทึกไม่สำเร็จ');
    if (onRefreshUser) onRefreshUser();
    return data;
  };

  const handleThemeChange = (value) => {
    const next = { ...settings, theme: value };
    setSettings(next);
    savePreferencesToBackend(next).catch((err) => {
      console.error('Failed to save theme:', err);
    });
  };

  const handleNotificationChange = (key, value) => {
    const next = { ...settings, [key]: value };
    setSettings(next);
    savePreferencesToBackend(next).then(() => {
      setNotificationSaveStatus('saved');
      setTimeout(() => setNotificationSaveStatus(null), 2000);
    }).catch((err) => {
      setNotificationSaveStatus('error');
      setNotificationSaveError(err.message);
      setTimeout(() => { setNotificationSaveStatus(null); setNotificationSaveError(null); }, 3000);
    });
  };

  const handleSaveSettings = async () => {
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/auth/profile`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...(user?.id && { 'X-User-ID': user.id }) },
        credentials: 'include',
        body: JSON.stringify({
          preferences: settings
        })
      });
      
      const data = await res.json();
      if (data.ok) {
        await Swal.fire({
          icon: 'success',
          title: 'บันทึกสำเร็จ',
          text: 'บันทึกการตั้งค่าสำเร็จแล้ว',
          confirmButtonText: 'ตกลง'
        });
        if (onRefreshUser) {
          onRefreshUser();
        }
      } else {
        throw new Error(data.detail || 'Failed to save settings');
      }
    } catch (error) {
      console.error('Error saving settings:', error);
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: error.message || 'เกิดข้อผิดพลาดในการบันทึก',
        confirmButtonText: 'ตกลง'
      });
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
      const currentHash = await sha256Password(changePasswordData.currentPassword);
      const newHash = await sha256Password(changePasswordData.newPassword);
      const res = await fetch(`${API_BASE_URL}/api/auth/change-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Password-Encoding': 'sha256',
        },
        credentials: 'include',
        body: JSON.stringify({
          current_password: currentHash,
          new_password: newHash
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

  const fetchSavedCards = () => {
    if (!user?.id) return;
    setCardsLoading(true);
    setCardsError(null);
    const headers = { 'X-User-ID': user.id };
    fetch(`${API_BASE_URL}/api/booking/saved-cards`, { headers, credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('โหลดบัตรไม่สำเร็จ'))))
      .then((data) => {
        if (data.ok && Array.isArray(data.cards)) setSavedCards(data.cards);
        if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
      })
      .catch((err) => setCardsError(err.message || 'โหลดบัตรไม่สำเร็จ'))
      .finally(() => setCardsLoading(false));
  };

  const handleSetPrimaryCard = async (cardId) => {
    if (!user?.id || !cardId) return;
    setSettingPrimaryId(cardId);
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards/${encodeURIComponent(cardId)}/set-primary`, {
        method: 'PUT',
        headers: { 'X-User-ID': user.id },
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ตั้งบัตรหลักไม่สำเร็จ');
      if (data.ok) setPrimaryCardId(cardId);
    } catch (err) {
      setCardsError(err.message || 'ตั้งบัตรหลักไม่สำเร็จ');
    } finally {
      setSettingPrimaryId(null);
    }
  };

  const handleDeleteCard = async (cardId) => {
    if (!user?.id || !cardId) return;
    setDeletingCardId(cardId);
    try {
      const headers = { 'X-User-ID': user.id };
      const res = await fetch(`${API_BASE_URL}/api/booking/saved-cards/${encodeURIComponent(cardId)}`, {
        method: 'DELETE',
        headers,
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ลบบัตรไม่สำเร็จ');
      if (data.ok && data.cards) setSavedCards(data.cards);
      if (data.ok && data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
    } catch (err) {
      setCardsError(err.message || 'ลบบัตรไม่สำเร็จ');
    } finally {
      setDeletingCardId(null);
    }
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
      {notificationSaveStatus === 'saved' && (
        <p className="settings-save-feedback" style={{ color: '#22c55e', marginBottom: 12, fontSize: 14 }}>✓ บันทึกแล้ว</p>
      )}
      {notificationSaveStatus === 'error' && notificationSaveError && (
        <p className="settings-save-feedback" style={{ color: '#ef4444', marginBottom: 12, fontSize: 14 }}>⚠ {notificationSaveError}</p>
      )}
      
      <div className="settings-item">
        <div className="settings-item-label">
          <label>เปิด/ปิดการแจ้งเตือน</label>
        </div>
        <div className="settings-item-control">
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={settings.notificationsEnabled}
              onChange={(e) => handleNotificationChange('notificationsEnabled', e.target.checked)}
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
              onChange={(e) => handleNotificationChange('bookingNotifications', e.target.checked)}
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
              onChange={(e) => handleNotificationChange('paymentNotifications', e.target.checked)}
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
              onChange={(e) => handleNotificationChange('tripChangeNotifications', e.target.checked)}
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
              onChange={(e) => handleNotificationChange('emailNotifications', e.target.checked)}
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

  const renderCards = () => (
    <div className="settings-section settings-section-cards">
      <h3>บัตรเครดิต/เดบิต</h3>
      <p className="settings-cards-desc">จัดการบัตรสำหรับใช้ชำระเงินในระบบ — เพิ่มหรือลบบัตรได้ที่นี่</p>
      {cardsLoading && <p className="settings-cards-loading">กำลังโหลดรายการบัตร...</p>}
      {cardsError && (
        <div className="settings-cards-error">
          <span>{cardsError}</span>
          <button type="button" className="btn-secondary" onClick={fetchSavedCards}>โหลดใหม่</button>
        </div> 
      )}  
      {!cardsLoading && savedCards.length > 0 && (
        <div className="settings-cards-list">
          <h4>บัตรที่บันทึกไว้</h4>
          <div className="settings-cards-scroll">
          <ul className="settings-cards-grid">
            {savedCards.map((c) => {
              const brandKey = (c.brand || 'card').toLowerCase().replace(/\s+/g, '');
              const cardClass = ['visa','mastercard','amex','americanexpress','jcb','discover','diners','unionpay'].includes(brandKey)
                ? `settings-card-visual card-${brandKey.replace('americanexpress','amex')}`
                : 'settings-card-visual card-default';
              return (
                <li key={c.card_id || c.id} className="settings-card-item">
                  <div className={`${cardClass} ${primaryCardId === (c.card_id || c.id) ? 'settings-card-primary' : ''}`}>
                    <div className="settings-card-visual-top">
                      {primaryCardId === (c.card_id || c.id) && (
                        <span className="settings-card-primary-badge">บัตรหลัก</span>
                      )}
                    </div>
                    <div className="settings-card-visual-mid">
                      <span className="settings-card-visual-number">•••• •••• •••• {c.last4 || '****'}</span>
                      {c.name && <span className="settings-card-visual-name">{c.name}</span>}
                    </div>
                    <div className="settings-card-visual-bottom">
                      <span className="settings-card-visual-expiry">หมดอายุ {c.expiry_month || '**'}/{c.expiry_year || '**'}</span>
                      <span className="settings-card-visual-logo"><CardBrandLogo brand={c.brand} /></span>
                    </div>
                  </div>
                  <div className="settings-card-actions">
                    {primaryCardId !== (c.card_id || c.id) && (
                      <button
                        type="button"
                        className="btn-secondary btn-set-primary-card"
                        onClick={() => handleSetPrimaryCard(c.card_id || c.id)}
                        disabled={settingPrimaryId === (c.card_id || c.id)}
                      >
                        {settingPrimaryId === (c.card_id || c.id) ? 'กำลังตั้ง...' : 'ตั้งเป็นหลัก'}
                      </button>
                    )}
                    <button
                      type="button"
                      className="btn-secondary btn-delete-card"
                      onClick={() => handleDeleteCard(c.card_id || c.id)}
                      disabled={deletingCardId === (c.card_id || c.id)}
                    >
                      {deletingCardId === (c.card_id || c.id) ? 'กำลังลบ...' : 'ลบ'}
                    </button>
                  </div>
                </li>
              );
            })}
          </ul>
          </div>
        </div>
      )}

      {!cardsLoading && (
        <div className="settings-cards-add">
          <h4>เพิ่มบัตรใหม่</h4>
          <button
            type="button"
            className="btn-primary btn-add-card"
            onClick={handleClickAddCard}
          >
            เพิ่มบัตร
          </button>
        </div>
      )}
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
            onChange={(e) => handleThemeChange(e.target.value)}
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

  const theme = useTheme();

  const sections = [
    { id: 'account', name: 'การตั้งค่าบัญชี', icon: '👤' },
    { id: 'notifications', name: 'การแจ้งเตือน', icon: '🔔' },
    { id: 'privacy', name: 'ความเป็นส่วนตัว', icon: '🔒' },
    { id: 'ai-agent', name: 'การตั้งค่า AI Agent', icon: '🤖' },
    { id: 'cards', name: 'บัตรเครดิต/เดบิต', icon: '💳' },
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
      
      <div className="settings-content-area" data-theme={theme}>
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
          {activeSection === 'cards' && renderCards()}
          {activeSection === 'theme' && renderThemeDisplay()}
          {activeSection === 'about' && renderAbout()}
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
