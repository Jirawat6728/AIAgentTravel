import React, { useState, useEffect } from 'react';
import './PaymentPage.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { loadOmiseScript, createTokenAsync } from '../../utils/omiseLoader';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export default function PaymentPage({ 
  bookingId, 
  user, 
  onBack, 
  onPaymentSuccess,
  onNavigateToHome = null,
  onNavigateToProfile = null,
  onNavigateToSettings = null,
  onLogout = null,
  onSignIn = null
}) {
  const [booking, setBooking] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [omiseLoaded, setOmiseLoaded] = useState(false);
  
  // วิธีชำระเงิน: ใช้บัตรที่บันทึก หรือ บัตรใหม่
  const [paymentMethod, setPaymentMethod] = useState('new'); // 'new' | 'saved'
  const [selectedSavedCardId, setSelectedSavedCardId] = useState(null);
  const [savedCards, setSavedCards] = useState([]); // โหลดจาก API GET /api/booking/saved-cards
  const [savedCardsCustomerId, setSavedCardsCustomerId] = useState(null);
  const [primaryCardId, setPrimaryCardId] = useState(null); // บัตรหลักจาก API
  const [showAllSavedCards, setShowAllSavedCards] = useState(false); // true = แสดงทุกบัตร + ปุ่มเปลี่ยนบัตร
  const [saveCardChecked, setSaveCardChecked] = useState(false);
  // ที่อยู่เรียกเก็บเงิน: ใช้ที่อยู่ปัจจุบัน (จากโปรไฟล์) หรือ ใส่ที่อยู่ใหม่
  const [billingAddressChoice, setBillingAddressChoice] = useState('new'); // 'current' | 'new'
  
  // Form state
  const [formData, setFormData] = useState({
    email: user?.email || '',
    cardNumber: '',
    cardExpiry: '',
    cardCvv: '',
    cardName: user?.full_name || user?.first_name || '',
    country: 'TH',
    address1: '',
    address2: '',
    city: '',
    province: '',
    postalCode: ''
  });

  const theme = useTheme();
  const fontSize = useFontSize();

  // ที่อยู่ปัจจุบันจากโปรไฟล์ (มี address_line1 หรือ city ถือว่ามีที่อยู่)
  const userHasAddress = Boolean(
    user?.address_line1?.trim() || user?.city?.trim() || user?.postal_code?.trim()
  );
  const userBillingAddress = userHasAddress
    ? {
        country: user?.country || 'TH',
        address1: user?.address_line1 || '',
        address2: user?.address_line2 || '',
        city: user?.city || '',
        province: user?.province || '',
        postalCode: user?.postal_code || ''
      }
    : null;

  useEffect(() => {
    // Get booking_id from URL if not provided as prop
    const urlParams = new URLSearchParams(window.location.search);
    const urlBookingId = urlParams.get('booking_id') || urlParams.get('id');
    const finalBookingId = bookingId || urlBookingId;
    
    if (finalBookingId) {
      // Update bookingId if from URL
      if (urlBookingId && !bookingId) {
        // bookingId will be used from URL
      }
      loadBooking();
    } else {
      setError('ไม่พบ Booking ID');
      setLoading(false);
    }
    
    loadOmiseScript(API_BASE_URL).then(() => {
      setOmiseLoaded(true);
      setError(null);
    }).catch(err => {
      console.error('Failed to load Omise:', err);
      setError('omise_load_failed');
    });
  }, [bookingId]);

  const retryLoadOmise = () => {
    setError(null);
    loadOmiseScript(API_BASE_URL).then(() => {
      setOmiseLoaded(true);
    }).catch(() => {
      setError('omise_load_failed');
    });
  };

  // โหลดบัตรที่บันทึกไว้จาก MongoDB (ต่อ User) — ใช้ user_id ตรงกับ list/create-charge
  const loadSavedCards = React.useCallback(() => {
    const uid = user?.user_id || user?.id;
    if (!uid) return Promise.resolve();
    const headers = { 'Content-Type': 'application/json', 'X-User-ID': uid };
    return fetch(`${API_BASE_URL}/api/booking/saved-cards`, { headers, credentials: 'include' })
      .then((res) => res.ok ? res.json() : Promise.reject(new Error(res.status === 401 ? 'Unauthorized' : 'Failed to load saved cards')))
      .then((data) => {
        if (data.ok && Array.isArray(data.cards)) {
          setSavedCards(data.cards);
          if (data.customer_id) setSavedCardsCustomerId(data.customer_id);
          if (data.primary_card_id !== undefined) setPrimaryCardId(data.primary_card_id);
          if (data.cards.length > 0) {
            const primaryId = data.primary_card_id;
            const primaryExists = primaryId && data.cards.some((c) => c.card_id === primaryId);
            setSelectedSavedCardId(primaryExists ? primaryId : data.cards[0].card_id);
            setPaymentMethod('saved');
          }
        }
      })
      .catch((err) => {
        console.warn('[PaymentPage] Saved cards load failed:', err.message);
      });
  }, [user?.user_id, user?.id]);

  useEffect(() => {
    loadSavedCards();
  }, [loadSavedCards]);

  // โหลดบัตรอีกครั้งหลัง delay เมื่อมี user (กรณี request แรกไปก่อน user พร้อม)
  useEffect(() => {
    const uid = user?.user_id || user?.id;
    if (!uid) return;
    const t = setTimeout(loadSavedCards, 600);
    return () => clearTimeout(t);
  }, [user?.user_id, user?.id, loadSavedCards]);

  const billingAddressChoiceInitialized = React.useRef(false);
  useEffect(() => {
    if (user?.id && userHasAddress && !billingAddressChoiceInitialized.current) {
      billingAddressChoiceInitialized.current = true;
      setBillingAddressChoice('current');
    }
  }, [user?.id, userHasAddress]);

  const loadBooking = async () => {
    setLoading(true);
    setError(null);
    try {
      // Get booking_id from URL if not provided as prop
      const urlParams = new URLSearchParams(window.location.search);
      const urlBookingId = urlParams.get('booking_id') || urlParams.get('id');
      const finalBookingId = bookingId || urlBookingId;
      
      if (!finalBookingId) {
        setError('ไม่พบ Booking ID');
        setLoading(false);
        return;
      }
      
      const headers = {
        'Content-Type': 'application/json'
      };
      
      const userId = user?.user_id || user?.id;
      if (userId) headers['X-User-ID'] = userId;

      const res = await fetch(`${API_BASE_URL}/api/booking/list`, {
        headers,
        credentials: 'include',
      });
      
      if (!res.ok) {
        throw new Error(`HTTP Error: ${res.status}`);
      }
      
      const data = await res.json();
      
      if (data?.ok && data.bookings) {
        const foundBooking = data.bookings.find(b => 
          b._id === finalBookingId || 
          b.booking_id === finalBookingId ||
          String(b._id) === String(finalBookingId)
        );
        if (foundBooking) {
          setBooking(foundBooking);
          
          // Pre-fill form with user data if available
          if (user) {
            setFormData(prev => ({
              ...prev,
              email: user.email || prev.email,
              cardName: user.full_name || user.first_name || prev.cardName
            }));
          }
        } else {
          setError('ไม่พบข้อมูลการจอง');
        }
      } else {
        setError('ไม่สามารถโหลดข้อมูลการจองได้');
      }
    } catch (err) {
      console.error('[PaymentPage] Error loading booking:', err);
      setError(err.message || 'เกิดข้อผิดพลาดในการเชื่อมต่อ');
    } finally {
      setLoading(false);
    }
  };

  const formatCardNumber = (value) => {
    const cleaned = value.replace(/\s/g, '');
    const formatted = cleaned.match(/.{1,4}/g)?.join(' ') || cleaned;
    return formatted.substring(0, 19);
  };

  /**
   * IIN (Issuer Identification Number) — 6 หลักแรกของเลขบัตร ใช้ระบุเครือข่าย/ผู้ออกบัตร
   * คืนค่า { cardType, iin, label } หรือ null ถ้า IIN ไม่ตรงช่วงที่รองรับ
   */
  const getCardTypeFromIIN = (cardNumber) => {
    const digits = (cardNumber || '').replace(/\s/g, '');
    if (digits.length < 6 || !/^\d+$/.test(digits)) return null;
    const iin6 = digits.substring(0, 6);
    const iin4 = digits.substring(0, 4);
    const iin2 = digits.substring(0, 2);
    const n6 = parseInt(iin6, 10);
    const n4 = parseInt(iin4, 10);
    const n2 = parseInt(iin2, 10);

    // Visa: IIN ขึ้นต้นด้วย 4
    if (digits.startsWith('4')) return { cardType: 'visa', iin: iin6, label: 'Visa' };
    // American Express: 34, 37
    if (iin2 === '34' || iin2 === '37') return { cardType: 'amex', iin: iin6, label: 'American Express' };
    // JCB: 3528–3589 (IIN 6 หลัก)
    if (n4 >= 3528 && n4 <= 3589) return { cardType: 'jcb', iin: iin6, label: 'JCB' };
    // Diners Club: 300-305, 36, 38, 39
    if ((n4 >= 300 && n4 <= 305) || iin2 === '36' || iin2 === '38' || iin2 === '39') return { cardType: 'diners', iin: iin6, label: 'Diners Club' };
    // Discover: 6011, 644-649, 65, 622126-622925
    if (iin4 === '6011') return { cardType: 'discover', iin: iin6, label: 'Discover' };
    if (n4 >= 644 && n4 <= 649) return { cardType: 'discover', iin: iin6, label: 'Discover' };
    if (iin2 === '65') return { cardType: 'discover', iin: iin6, label: 'Discover' };
    if (n6 >= 622126 && n6 <= 622925) return { cardType: 'discover', iin: iin6, label: 'Discover' };
    // UnionPay: 62
    if (digits.startsWith('62')) return { cardType: 'unionpay', iin: iin6, label: 'UnionPay' };
    // Mastercard: 51-55 (5x), 2221-2720 (4 หลัก)
    if (n2 >= 51 && n2 <= 55) return { cardType: 'mastercard', iin: iin6, label: 'Mastercard' };
    if (n4 >= 2221 && n4 <= 2720) return { cardType: 'mastercard', iin: iin6, label: 'Mastercard' };
    return null;
  };

  /**
   * ระบุชนิดบัตรจากเลขบัตร — ใช้ IIN เมื่อมี 6 หลักขึ้นไป ไม่งั้นใช้ prefix เบื้องต้น
   */
  const getCardType = (cardNumber) => {
    const digits = (cardNumber || '').replace(/\s/g, '');
    if (digits.length < 2) return null;
    const fromIIN = getCardTypeFromIIN(cardNumber);
    if (fromIIN) return fromIIN.cardType;
    if (/^4/.test(digits)) return 'visa';
    if (/^3[47]/.test(digits)) return 'amex';
    if (/^35/.test(digits)) return 'jcb';
    if (/^3[68]/.test(digits) || /^30[0-5]/.test(digits)) return 'diners';
    if (/^6011/.test(digits) || /^64[4-9]/.test(digits) || /^65/.test(digits) || /^622/.test(digits)) return 'discover';
    if (/^62/.test(digits)) return 'unionpay';
    if (/^5[1-5]/.test(digits) || /^2(22[1-9]|2[3-9]\d|[3-6]\d{2}|7[01]\d|720)/.test(digits)) return 'mastercard';
    return null;
  };
  const detectedCardType = getCardType(formData.cardNumber);
  const iinInfo = getCardTypeFromIIN(formData.cardNumber);

  /**
   * เช็คเลขบัตรจาก IIN + ความยาวตามมาตรฐานเครือข่าย
   */
  const validateCardNumber = (cardNumber) => {
    const digits = (cardNumber || '').replace(/\s/g, '');
    if (!/^\d+$/.test(digits) || digits.length < 13) {
      return { valid: false, cardType: null, message: 'กรุณากรอกเลขบัตรอย่างน้อย 13 หลัก' };
    }
    const len = digits.length;
    const byIIN = getCardTypeFromIIN(cardNumber);

    if (byIIN) {
      const { cardType, iin, label } = byIIN;
      const iinDisplay = iin ? ` (IIN ${iin})` : '';
      switch (cardType) {
        case 'visa':
          if (len === 13 || len === 16) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 13 หรือ 16 หลัก` };
        case 'amex':
          if (len === 15) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 15 หลัก` };
        case 'jcb':
          if (len === 15 || len === 16) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 15 หรือ 16 หลัก` };
        case 'diners':
          if (len === 14) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 14 หลัก` };
        case 'discover':
          if (len >= 16 && len <= 19) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 16–19 หลัก` };
        case 'unionpay':
          if (len >= 16 && len <= 19) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 16–19 หลัก` };
        case 'mastercard':
          if (len === 16) return { valid: true, cardType, message: `บัตร ${label}${iinDisplay}` };
          return { valid: false, cardType, message: `บัตร ${label} ต้อง 16 หลัก` };
        default:
          break;
      }
    }

    // ไม่ตรง IIN ที่รองรับ
    return { valid: false, cardType: null, message: 'เลขบัตร (IIN) ไม่ตรงกับเครือข่ายบัตรที่รองรับ' };
  };
  const cardCheck = formData.cardNumber.replace(/\s/g, '').length >= 13
    ? validateCardNumber(formData.cardNumber)
    : { valid: null, cardType: detectedCardType, message: null };

  const formatExpiry = (value) => {
    const cleaned = value.replace(/\D/g, '');
    if (cleaned.length >= 2) {
      return cleaned.substring(0, 2) + '/' + cleaned.substring(2, 4);
    }
    return cleaned;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!omiseLoaded || !window.Omise) {
      setError('ระบบชำระเงินยังไม่พร้อม กรุณารอสักครู่');
      return;
    }

    if (!booking) {
      setError('ไม่พบข้อมูลการจอง');
      return;
    }
    if (!user?.id) {
      setError('กรุณาเข้าสู่ระบบเพื่อชำระเงิน');
      return;
    }

    if (paymentMethod === 'saved') {
      if (!selectedSavedCardId || !savedCardsCustomerId) {
        setError('กรุณาเลือกบัตรที่บันทึกไว้');
        return;
      }
      const urlParams = new URLSearchParams(window.location.search);
      const urlBookingId = urlParams.get('booking_id') || urlParams.get('id');
      const finalBookingId = [booking?.booking_id, booking?._id, bookingId, urlBookingId]
        .map((v) => (v && typeof v === 'object' && v.$oid ? v.$oid : v))
        .find((v) => v != null && String(v).trim() !== '');
      const bookingIdStr = finalBookingId != null ? String(finalBookingId).trim() : '';
      if (!bookingIdStr) {
        setError('ไม่พบ Booking ID กรุณากลับไปเลือกการจองใหม่');
        return;
      }
      setProcessing(true);
      setError(null);
      try {
        const headers = { 'Content-Type': 'application/json' };
        const uid = user?.user_id || user?.id;
        if (uid) headers['X-User-ID'] = uid;
        const chargeRes = await fetch(`${API_BASE_URL}/api/booking/create-charge`, {
          method: 'POST',
          headers,
          credentials: 'include',
          body: JSON.stringify({
            booking_id: bookingIdStr,
            card_id: selectedSavedCardId,
            customer_id: savedCardsCustomerId,
            amount: Number(booking?.total_price) || 0,
            currency: (booking?.currency || 'THB').toUpperCase()
          })
        });
        const chargeData = await chargeRes.json();
        const getChargeError = (data) => {
          const d = data?.detail;
          if (typeof d === 'string') return d;
          if (Array.isArray(d) && d.length > 0) return (d[0]?.msg || d[0]?.message) || d.map((e) => e.msg).filter(Boolean).join(', ');
          if (d && typeof d === 'object' && d.message) return d.message;
          return data?.error || 'การชำระเงินล้มเหลว';
        };
        if (!chargeRes.ok || !chargeData.ok) {
          throw new Error(getChargeError(chargeData));
        }
        if (onPaymentSuccess) {
          onPaymentSuccess(bookingIdStr, chargeData);
        } else {
          window.location.href = `/bookings?booking_id=${bookingIdStr}&payment_status=success`;
        }
      } catch (err) {
        setError(err.message || 'เกิดข้อผิดพลาดในการชำระเงิน');
      } finally {
        setProcessing(false);
      }
      return;
    }

    const cardValidation = validateCardNumber(formData.cardNumber);
    if (formData.cardNumber.replace(/\s/g, '').length >= 13 && !cardValidation.valid) {
      setError(cardValidation.message || 'เลขบัตรไม่ถูกต้อง');
      return;
    }
    const expiryParts = (formData.cardExpiry || '').trim().split('/').map((p) => p.trim());
    if (expiryParts.length !== 2 || expiryParts[0].length !== 2 || expiryParts[1].length !== 2) {
      setError('กรุณากรอกวันหมดอายุบัตรรูปแบบ MM/YY');
      return;
    }
    if (!(formData.cardCvv || '').replace(/\s/g, '').match(/^\d{3,4}$/)) {
      setError('กรุณากรอก CVV 3 หรือ 4 หลัก');
      return;
    }

    setProcessing(true);
    setError(null);

    const urlParams = new URLSearchParams(window.location.search);
    const urlBookingId = urlParams.get('booking_id') || urlParams.get('id');
    const finalBookingIdRaw = [booking?.booking_id, booking?._id, bookingId, urlBookingId]
      .map((v) => (v && typeof v === 'object' && v.$oid ? v.$oid : v))
      .find((v) => v != null && String(v).trim() !== '');
    const finalBookingId = finalBookingIdRaw != null ? String(finalBookingIdRaw).trim() : '';
    if (!finalBookingId) {
      setError('ไม่พบ Booking ID กรุณากลับไปเลือกการจองใหม่');
      return;
    }
    const chargeAmount = Math.round((Number(booking?.total_price) || 0) * 100) / 100;
    if (chargeAmount <= 0) {
      setError('ยอดชำระไม่ถูกต้อง');
      return;
    }

    const getChargeError = (chargeData) => {
      const d = chargeData?.detail;
      if (typeof d === 'string') return d;
      if (Array.isArray(d) && d.length > 0) {
        const first = d[0];
        return first?.msg || first?.message || d.map((e) => e.msg || e.message).filter(Boolean).join(', ') || 'ข้อมูลไม่ถูกต้อง';
      }
      if (d && typeof d === 'object' && d.message) return d.message;
      return chargeData?.error || 'การชำระเงินล้มเหลว';
    };

    try {
      // Get Omise public key from backend
      const configRes = await fetch(`${API_BASE_URL}/api/booking/payment-config`, {
        credentials: 'include',
      });
      
      let omisePublicKey = null;
      if (configRes.ok) {
        const configData = await configRes.json();
        omisePublicKey = configData.public_key;
      }
      
      if (!omisePublicKey) {
        throw new Error('ไม่พบ Omise Public Key กรุณาติดต่อผู้ดูแลระบบ');
      }

      window.Omise.setPublicKey(omisePublicKey);

      const billingForSubmit = billingAddressChoice === 'current' && userBillingAddress
        ? userBillingAddress
        : { city: formData.city, postalCode: formData.postalCode, country: formData.country };
      const card = {
        name: formData.cardName,
        number: formData.cardNumber.replace(/\s/g, ''),
        expiration_month: expiryParts[0],
        expiration_year: '20' + expiryParts[1],
        security_code: formData.cardCvv,
        city: billingForSubmit.city,
        postal_code: billingForSubmit.postalCode || billingForSubmit.postal_code,
        country: billingForSubmit.country
      };

      const tokenResponse = await createTokenAsync(card);

      const headers = { 'Content-Type': 'application/json' };
      const userId = user?.user_id || user?.id;
      if (userId) headers['X-User-ID'] = userId;

      let tokenToCharge = tokenResponse.id;
      // บัตรที่บันทึกใน Local: ผูก Omise อัตโนมัติเมื่อชำระด้วยบัตรใหม่ (สร้าง customer + บัตร แล้วชาร์จ)
      const shouldSaveAndChargeWithCustomer = saveCardChecked || (savedCards.length > 0 && !savedCardsCustomerId);
      if (shouldSaveAndChargeWithCustomer) {
        const saveRes = await fetch(`${API_BASE_URL}/api/booking/saved-cards`, {
          method: 'POST',
          headers,
          credentials: 'include',
          body: JSON.stringify({ token: tokenResponse.id, email: (formData.email || user?.email || '').trim() || undefined })
        });
        const saveData = await saveRes.json();
        if (saveData.ok && saveData.cards?.length > 0 && saveData.customer_id) {
          const lastCard = saveData.cards[saveData.cards.length - 1];
          tokenToCharge = null;
          setSavedCards(saveData.cards);
          setSavedCardsCustomerId(saveData.customer_id);
          const chargeRes = await fetch(`${API_BASE_URL}/api/booking/create-charge`, {
            method: 'POST',
            headers,
            credentials: 'include',
            body: JSON.stringify({
              booking_id: finalBookingId,
              card_id: lastCard.card_id,
              customer_id: saveData.customer_id,
              amount: chargeAmount,
              currency: (booking?.currency || 'THB').toUpperCase()
            })
          });
          const chargeData = await chargeRes.json();
          if (!chargeRes.ok || !chargeData.ok) {
            throw new Error(getChargeError(chargeData));
          }
          if (onPaymentSuccess) onPaymentSuccess(finalBookingId, chargeData);
          else window.location.href = `/bookings?booking_id=${finalBookingId}&payment_status=success`;
          setProcessing(false);
          return;
        }
      }

      const chargeRes = await fetch(`${API_BASE_URL}/api/booking/create-charge`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          booking_id: finalBookingId,
          token: tokenToCharge,
          amount: chargeAmount,
          currency: (booking?.currency || 'THB').toUpperCase()
        })
      });

      const chargeData = await chargeRes.json();

      if (!chargeRes.ok || !chargeData.ok) {
        throw new Error(getChargeError(chargeData));
      }

      // Payment successful - reuse finalBookingId from above
      
      if (onPaymentSuccess) {
        onPaymentSuccess(finalBookingId, chargeData);
      } else {
        // Redirect to bookings page
        window.location.href = `/bookings?booking_id=${finalBookingId}&payment_status=success`;
      }

    } catch (err) {
      console.error('[PaymentPage] Payment error:', err);
      setError(err.message || 'เกิดข้อผิดพลาดในการชำระเงิน');
      setProcessing(false);
    }
  };

  if (loading) {
    return (
      <div className="payment-page-container">
        <AppHeader
          activeTab="bookings"
          user={user}
          onNavigateToHome={onNavigateToHome}
          onNavigateToBookings={onBack}
          onLogout={onLogout}
          onSignIn={onSignIn}
          onNavigateToProfile={onNavigateToProfile}
          onNavigateToSettings={onNavigateToSettings}
        />
        <div className="payment-page-content" data-theme={theme} data-font-size={fontSize}>
          <div className="payment-loading">⏳ กำลังโหลดข้อมูล...</div>
        </div>
      </div>
    );
  }

  if (error && !booking) {
    return (
      <div className="payment-page-container">
        <AppHeader
          activeTab="bookings"
          user={user}
          onNavigateToHome={onNavigateToHome}
          onNavigateToBookings={onBack}
          onLogout={onLogout}
          onSignIn={onSignIn}
          onNavigateToProfile={onNavigateToProfile}
          onNavigateToSettings={onNavigateToSettings}
        />
        <div className="payment-page-content" data-theme={theme} data-font-size={fontSize}>
          <div className="payment-error">
            ❌ {error === 'omise_load_failed'
              ? 'โหลด Omise ไม่สำเร็จ — ถ้ามีบัตรที่บันทึกไว้สามารถเลือก "ใช้บัตรที่บันทึกไว้" ชำระได้ หรือลองปิด Ad blocker / รีเฟรช / กดลองอีกครั้ง'
              : error}
          </div>
          {error === 'omise_load_failed' && (
            <button type="button" onClick={retryLoadOmise} className="btn-back" style={{ marginTop: 12 }}>
              🔄 ลองโหลดอีกครั้ง
            </button>
          )}
          {onBack && (
            <button onClick={onBack} className="btn-back">
              ← กลับไปยัง My Bookings
            </button>
          )}
        </div>
      </div>
    );
  }

  const travelSlots = booking?.travel_slots || {};
  const origin = travelSlots.origin_city || travelSlots.origin || '';
  const destination = travelSlots.destination_city || travelSlots.destination || '';
  const departureDate = travelSlots.departure_date || '';
  // ปัดยอดเป็น 2 ทศนิยมให้ตรงกับยอดที่ส่ง charge — แสดงและเรียกเก็บเท่ากัน
  const amount = Math.round((Number(booking?.total_price) || 0) * 100) / 100;
  const currency = booking?.currency || 'THB';

  return (
    <div className="payment-page-container">
      <AppHeader
        activeTab="bookings"
        user={user}
        onNavigateToHome={onNavigateToHome}
        onNavigateToBookings={onBack}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
      />
      
      <div className="payment-page-content" data-theme={theme} data-font-size={fontSize}>
        <div className="payment-wrapper">
          {/* Left Panel: Order Summary */}
          <div className="payment-order-summary">
            <div className="order-header">
              {onBack && (
                <span className="back-arrow" onClick={onBack}>←</span>
              )}
              <span className="order-title">สรุปการสั่งซื้อ</span>
            </div>
            
            <div className="price-display">
              <div className="price-main">
                {new Intl.NumberFormat('th-TH', {
                  style: 'currency',
                  currency: currency,
                  minimumFractionDigits: 0,
                }).format(amount)}
              </div>
              <div className="price-period">สำหรับการจองทริป</div>
            </div>
            
            <div className="product-details">
              <div className="product-name">✈️ {origin && destination ? `${origin} → ${destination}` : 'ทริป'}</div>
              <div className="product-description">
                {departureDate && <div>วันเดินทาง: {departureDate}</div>}
                {travelSlots.nights && <div>จำนวนคืน: {travelSlots.nights} คืน</div>}
                {travelSlots.adults && <div>ผู้โดยสาร: {travelSlots.adults} ผู้ใหญ่</div>}
              </div>
            </div>
            
            <div className="price-breakdown">
              <div className="price-row">
                <span>รวม</span>
                <span>
                  {new Intl.NumberFormat('th-TH', {
                    style: 'currency',
                    currency: currency,
                    minimumFractionDigits: 0,
                  }).format(amount)}
                </span>
              </div>
              <div className="price-row total">
                <span>ยอดรวมที่ต้องชำระวันนี้</span>
                <span>
                  {new Intl.NumberFormat('th-TH', {
                    style: 'currency',
                    currency: currency,
                    minimumFractionDigits: 0,
                  }).format(amount)}
                </span>
              </div>
            </div>
          </div>

          {/* Right Panel: Payment Form */}
          <div className="payment-form-panel">
            <h1 className="form-header">ชำระเงินด้วยบัตร</h1>
            
            {error && (
              <div className="error-message">
                ❌ {error === 'omise_load_failed'
                  ? 'โหลดระบบชำระเงิน (Omise) ไม่สำเร็จ — ลองปิด Ad blocker / ตรวจสอบเน็ต หรือกดลองอีกครั้ง'
                  : error}
                {error === 'omise_load_failed' && (
                  <button type="button" onClick={retryLoadOmise} className="btn-retry-omise">
                    🔄 ลองโหลดอีกครั้ง
                  </button>
                )}
              </div>
            )}
            
            <form id="paymentForm" onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">อีเมล</label>
                <input
                  type="email"
                  className="form-input"
                  value={formData.email}
                  onChange={(e) => setFormData({...formData, email: e.target.value})}
                  placeholder="your@email.com"
                  required
                />
              </div>
              
              <div className="form-section">
                <div className="section-title">วิธีการชำระเงิน</div>
                
                <div className="payment-method-toggle">
                  <div className="payment-method-options">
                    <label className={`payment-method-option ${savedCards.length === 0 ? 'disabled' : ''}`} title={savedCards.length === 0 ? 'ไม่มีบัตรที่บันทึก หรือกดโหลดอีกครั้ง' : ''}>
                      <input
                        type="radio"
                        name="paymentMethod"
                        checked={paymentMethod === 'saved'}
                        disabled={savedCards.length === 0}
                        onChange={() => { setPaymentMethod('saved'); setSelectedSavedCardId(selectedSavedCardId || savedCards[0]?.card_id); setError(null); }}
                      />
                      <span>ใช้บัตรที่บันทึกไว้{savedCards.length === 0 ? ' (ยังไม่มีบัตร)' : ''}</span>
                    </label>
                    {savedCards.length === 0 && (user?.user_id || user?.id) && (
                      <button type="button" onClick={loadSavedCards} className="btn-add-card-inline" style={{ marginLeft: 8, fontSize: '0.85rem' }}>
                        โหลดบัตรอีกครั้ง
                      </button>
                    )}
                    <label className="payment-method-option">
                      <input
                        type="radio"
                        name="paymentMethod"
                        checked={paymentMethod === 'new'}
                        onChange={() => { setPaymentMethod('new'); setError(null); }}
                      />
                      <span>ใช้บัตรใหม่</span>
                    </label>
                  </div>
                  {paymentMethod === 'saved' && savedCards.length > 0 && (
                      <div className="saved-cards-list">
                        {(() => {
                          const selectedCard = savedCards.find((c) => c.card_id === selectedSavedCardId) || savedCards[0];
                          const cardsToShow = showAllSavedCards ? savedCards : (selectedCard ? [selectedCard] : []);
                          return (
                            <>
                              {cardsToShow.map((card) => (
                                <label key={card.card_id} className={`saved-card-item ${selectedSavedCardId === card.card_id ? 'selected' : ''}`}>
                                  <input
                                    type="radio"
                                    name="savedCard"
                                    checked={selectedSavedCardId === card.card_id}
                                    onChange={() => {
                                      setSelectedSavedCardId(card.card_id);
                                      setError(null);
                                      setShowAllSavedCards(false);
                                    }}
                                  />
                                  <span className="saved-card-mask">•••• •••• •••• {card.last4}</span>
                                  <span className="saved-card-brand">{card.brand}</span>
                                  <span className="saved-card-expiry">{card.expiry_month}/{card.expiry_year}</span>
                                  {primaryCardId === card.card_id && (
                                    <span className="saved-card-primary-badge" style={{ marginLeft: '8px', fontSize: '0.75rem', color: 'var(--primary, #6366f1)', fontWeight: 600 }}>บัตรหลัก</span>
                                  )}
                                </label>
                              ))}
                              <div style={{ marginTop: '0.5rem' }}>
                                {!showAllSavedCards ? (
                                  <button
                                    type="button"
                                    className="btn-add-card-inline"
                                    onClick={() => setShowAllSavedCards(true)}
                                    style={{ borderStyle: 'solid', borderColor: 'var(--border, #e5e7eb)' }}
                                  >
                                    เปลี่ยนบัตร
                                  </button>
                                ) : (
                                  <button
                                    type="button"
                                    className="btn-add-card-inline"
                                    onClick={() => setShowAllSavedCards(false)}
                                    style={{ borderStyle: 'solid', borderColor: 'var(--border, #e5e7eb)' }}
                                  >
                                    ยกเลิก
                                  </button>
                                )}
                              </div>
                              <div className="form-group saved-cvv-only">
                          <label className="form-label">CVV</label>
                          <input
                            type="text"
                            className="form-input"
                            placeholder="123"
                            maxLength="4"
                            value={formData.cardCvv}
                            onChange={(e) => setFormData({ ...formData, cardCvv: e.target.value.replace(/\D/g, '').substring(0, 4) })}
                          />
                        </div>
                            </>
                          );
                        })()}
                      </div>
                    )}
                  </div>
                
                {paymentMethod === 'new' && (
                <>
                <div className="form-group">
                  <label className="form-label">หมายเลขบัตร</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.cardNumber}
                    onChange={(e) => setFormData({...formData, cardNumber: formatCardNumber(e.target.value)})}
                    placeholder="1234 1234 1234 1234"
                    maxLength="19"
                    required={paymentMethod === 'new'}
                  />
                  {formData.cardNumber.replace(/\s/g, '').length > 0 && (
                    <>
                      {detectedCardType && (
                        <div className="card-icons card-icons-single" aria-label="ชนิดบัตรที่ตรงกับเลขบัตร">
                          {detectedCardType === 'visa' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร Visa">
                              {/* Visa — โลโก้อย่างเป็นทางการ: คำว่า VISA สีน้ำเงินบนพื้นขาว */}
                              <svg viewBox="0 0 56 24" width="56" height="24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <rect width="56" height="24" fill="#fff"/>
                                <text x="28" y="16" textAnchor="middle" fill="#1A1F71" fontSize="13" fontWeight="700" fontFamily="Arial,sans-serif">VISA</text>
                              </svg>
                            </div>
                          )}
                          {detectedCardType === 'mastercard' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร Mastercard">
                              {/* Mastercard — โลโก้อย่างเป็นทางการ: วงกลมแดง-ส้มซ้อน พื้นหลังโปร่งใส */}
                              <svg viewBox="0 0 56 24" width="56" height="24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="20" cy="12" r="8" fill="#EB001B"/>
                                <circle cx="36" cy="12" r="8" fill="#F79E1B"/>
                                <path fill="#E85A00" fillOpacity="0.9" d="M28 4a8 8 0 0 1 0 16 8 8 0 0 1 0-16z"/>
                              </svg>
                            </div>
                          )}
                          {detectedCardType === 'amex' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร American Express">
                              {/* American Express — สีน้ำเงินแบรนด์ปัจจุบัน */}
                              <svg viewBox="0 0 56 24" width="56" height="24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <rect width="56" height="24" rx="3" fill="#006FCF"/>
                                <text x="28" y="9.5" textAnchor="middle" fill="#fff" fontSize="5.5" fontWeight="700" fontFamily="Arial,sans-serif">AMERICAN</text>
                                <text x="28" y="17.5" textAnchor="middle" fill="#fff" fontSize="5.5" fontWeight="700" fontFamily="Arial,sans-serif">EXPRESS</text>
                              </svg>
                            </div>
                          )}
                          {detectedCardType === 'jcb' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร JCB">
                              {/* JCB — ใช้โลโก้อย่างเป็นทางการ (รูปที่ส่งมา) */}
                              <img src="/images/jcb-logo.png" alt="JCB" width="56" height="24" style={{ objectFit: 'contain' }} />
                            </div>
                          )}
                          {detectedCardType === 'discover' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร Discover">
                              {/* Discover — สีส้มแบรนด์ปัจจุบัน #FF6000 */}
                              <svg viewBox="0 0 56 24" width="56" height="24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <rect width="56" height="24" rx="3" fill="#FF6000"/>
                                <text x="28" y="15.5" textAnchor="middle" fill="#fff" fontSize="8" fontWeight="700" fontFamily="Arial,sans-serif">Discover</text>
                              </svg>
                            </div>
                          )}
                          {detectedCardType === 'diners' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร Diners Club">
                              {/* Diners Club International — โลโก้ปัจจุบัน */}
                              <svg viewBox="0 0 56 24" width="56" height="24" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
                                <rect width="56" height="24" rx="3" fill="#0079BE"/>
                                <text x="28" y="15.5" textAnchor="middle" fill="#fff" fontSize="7" fontWeight="700" fontFamily="Arial,sans-serif">Diners Club</text>
                              </svg>
                            </div>
                          )}
                          {detectedCardType === 'unionpay' && (
                            <div className="card-icon card-icon-symbol card-icon-active" title="บัตร UnionPay">
                              {/* UnionPay — ใช้โลโก้อย่างเป็นทางการ (รูปที่ส่งมา) */}
                              <img src="/images/unionpay-logo.png" alt="UnionPay" width="56" height="24" style={{ objectFit: 'contain' }} />
                            </div>
                          )}
                        </div>
                      )}
                      {cardCheck.message && (
                        <div className={`card-check-msg ${cardCheck.valid === true ? 'card-check-valid' : cardCheck.valid === false ? 'card-check-invalid' : ''}`} role="status">
                          {cardCheck.message}
                        </div>
                      )}
                    </>
                  )}
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">วันหมดอายุ (MM/YY)</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.cardExpiry}
                      onChange={(e) => setFormData({...formData, cardExpiry: formatExpiry(e.target.value)})}
                      placeholder="MM/YY"
                      maxLength="5"
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">CVV</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.cardCvv}
                      onChange={(e) => setFormData({...formData, cardCvv: e.target.value.replace(/\D/g, '').substring(0, 4)})}
                      placeholder="123"
                      maxLength="4"
                      required
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label className="form-label">ชื่อเจ้าของบัตร</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.cardName}
                    onChange={(e) => setFormData({...formData, cardName: e.target.value})}
                    placeholder="ชื่อ-นามสกุล"
                    required={paymentMethod === 'new'}
                  />
                </div>
                <div className="form-group">
                  <label className="payment-save-card-option">
                    <input
                      type="checkbox"
                      checked={saveCardChecked}
                      onChange={(e) => setSaveCardChecked(e.target.checked)}
                    />
                    <span>บันทึกบัตรไว้ใช้ครั้งถัดไป (เก็บในบัญชีของฉัน)</span>
                  </label>
                </div>
                </>
                )}
              </div>
              
              <div className="form-section">
                <div className="section-title">ที่อยู่ในการเรียกเก็บเงิน</div>
                
                <div className="payment-method-options" style={{ marginBottom: '1rem' }}>
                  <label className="payment-method-option">
                    <input
                      type="radio"
                      name="billingAddress"
                      checked={billingAddressChoice === 'current'}
                      onChange={() => setBillingAddressChoice('current')}
                      disabled={!userHasAddress}
                    />
                    <span>ใช้ที่อยู่ปัจจุบัน</span>
                    {!userHasAddress && (
                      <span className="form-hint" style={{ marginLeft: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary, #666)' }}>
                        (ยังไม่มีที่อยู่ในโปรไฟล์)
                      </span>
                    )}
                  </label>
                  <label className="payment-method-option">
                    <input
                      type="radio"
                      name="billingAddress"
                      checked={billingAddressChoice === 'new'}
                      onChange={() => setBillingAddressChoice('new')}
                    />
                    <span>ใส่ที่อยู่ใหม่</span>
                  </label>
                </div>

                {billingAddressChoice === 'current' && userBillingAddress && (
                  <div className="billing-address-summary" style={{ padding: '0.75rem 1rem', background: 'var(--surface-secondary, #f5f5f5)', borderRadius: '8px', marginBottom: '1rem', fontSize: '0.9rem' }}>
                    {[userBillingAddress.address1, userBillingAddress.address2].filter(Boolean).join(' ')}
                    {userBillingAddress.city && ` ${userBillingAddress.city}`}
                    {userBillingAddress.province && ` ${userBillingAddress.province}`}
                    {userBillingAddress.postalCode && ` ${userBillingAddress.postalCode}`}
                    {userBillingAddress.country === 'TH' && ' ไทย'}
                  </div>
                )}

                {(billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)) && (
                <>
                <div className="form-group">
                  <label className="form-label">ประเทศ</label>
                  <select
                    className="form-input"
                    value={formData.country}
                    onChange={(e) => setFormData({...formData, country: e.target.value})}
                    required={billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)}
                  >
                    <option value="TH">ไทย</option>
                    <option value="US">United States</option>
                    <option value="GB">United Kingdom</option>
                    <option value="JP">Japan</option>
                    <option value="KR">South Korea</option>
                  </select>
                </div>
                
                <div className="form-group">
                  <label className="form-label">ที่อยู่บรรทัดที่ 1</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.address1}
                    onChange={(e) => setFormData({...formData, address1: e.target.value})}
                    required={billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)}
                  />
                </div>
                
                <div className="form-group">
                  <label className="form-label">ที่อยู่บรรทัดที่ 2</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.address2}
                    onChange={(e) => setFormData({...formData, address2: e.target.value})}
                  />
                </div>
                
                <div className="form-row">
                  <div className="form-group">
                    <label className="form-label">เมือง</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.city}
                      onChange={(e) => setFormData({...formData, city: e.target.value})}
                      required={billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">จังหวัด</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.province}
                      onChange={(e) => setFormData({...formData, province: e.target.value})}
                      required={billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)}
                    />
                  </div>
                </div>
                
                <div className="form-group">
                  <label className="form-label">รหัสไปรษณีย์</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.postalCode}
                    onChange={(e) => setFormData({...formData, postalCode: e.target.value.replace(/\D/g, '')})}
                    required={billingAddressChoice === 'new' || (billingAddressChoice === 'current' && !userHasAddress)}
                  />
                </div>
                </>
                )}
              </div>
              
              {paymentMethod === 'saved' && savedCards.length > 0 && !savedCardsCustomerId && (
                <div className="error-message" style={{ marginBottom: '1rem' }}>
                  ⚠️ บัตรที่บันทึกไว้ชุดนี้ยังไม่ผูกกับ Omise — ไม่สามารถกดชำระได้ กรุณาเลือก <strong>ใช้บัตรใหม่</strong> แล้วกรอกบัตรเพื่อชำระ หรือเพิ่มบัตรใหม่จาก Settings เพื่อให้มีบัตรที่ชำระได้
                </div>
              )}
              {paymentMethod === 'new' && !omiseLoaded && (
                <div className="error-message" style={{ marginBottom: '1rem' }}>
                  ⏳ กำลังโหลดระบบชำระเงิน (Omise)... ถ้าโหลดนานเกินไป ลองปิด Ad blocker / รีเฟรชหน้า หรือกดปุ่ม "ลองโหลดอีกครั้ง" ด้านบน
                </div>
              )}
              <button
                type="submit"
                className="btn-submit"
                disabled={processing || amount <= 0 || (paymentMethod === 'new' && !omiseLoaded) || (paymentMethod === 'saved' && (!selectedSavedCardId || !savedCardsCustomerId))}
              >
                {processing ? 'กำลังประมวลผล...' : `ชำระเงิน ${new Intl.NumberFormat('th-TH', {
                  style: 'currency',
                  currency: currency,
                  minimumFractionDigits: 0,
                }).format(amount)}`}
              </button>
              <p className="payment-powered-by">Powered by Omise</p>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
