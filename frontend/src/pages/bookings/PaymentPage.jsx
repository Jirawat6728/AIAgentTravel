import React, { useState, useEffect } from 'react';
import './PaymentPage.css';
import AppHeader from '../../components/common/AppHeader';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Load Omise.js script
const loadOmiseScript = () => {
  return new Promise((resolve, reject) => {
    if (window.Omise) {
      resolve();
      return;
    }
    
    const script = document.createElement('script');
    script.src = 'https://cdn.omise.co/omise.js';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Omise.js'));
    document.head.appendChild(script);
  });
};

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
    
    loadOmiseScript().then(() => {
      setOmiseLoaded(true);
    }).catch(err => {
      console.error('Failed to load Omise:', err);
      setError('ไม่สามารถโหลดระบบชำระเงินได้ กรุณารีเฟรชหน้า');
    });
  }, [bookingId]);

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
      
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }

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

    setProcessing(true);
    setError(null);

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

      // Set Omise public key
      window.Omise.setPublicKey(omisePublicKey);

      // Create Omise token
      const card = {
        name: formData.cardName,
        number: formData.cardNumber.replace(/\s/g, ''),
        expiration_month: formData.cardExpiry.split('/')[0],
        expiration_year: '20' + formData.cardExpiry.split('/')[1],
        security_code: formData.cardCvv,
        city: formData.city,
        postal_code: formData.postalCode,
        country: formData.country
      };

      const tokenResponse = await window.Omise.createToken('card', card);
      
      if (tokenResponse.object === 'error') {
        throw new Error(tokenResponse.message || 'ข้อมูลบัตรไม่ถูกต้อง');
      }

      // Create charge via backend
      // Get booking_id from URL if not provided as prop
      const urlParams = new URLSearchParams(window.location.search);
      const urlBookingId = urlParams.get('booking_id') || urlParams.get('id');
      const finalBookingId = bookingId || urlBookingId;
      
      const headers = {
        'Content-Type': 'application/json'
      };
      
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }

      const chargeRes = await fetch(`${API_BASE_URL}/api/booking/create-charge`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          booking_id: finalBookingId,
          token: tokenResponse.id,
          amount: booking.total_price || 0,
          currency: booking.currency || 'THB'
        })
      });

      const chargeData = await chargeRes.json();

      if (!chargeRes.ok || !chargeData.ok) {
        throw new Error(chargeData.detail || chargeData.error || 'การชำระเงินล้มเหลว');
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
        <div className="payment-page-content">
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
        <div className="payment-page-content">
          <div className="payment-error">❌ {error}</div>
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
  const amount = booking?.total_price || 0;
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
      
      <div className="payment-page-content">
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
                ❌ {error}
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
                
                <div className="form-group">
                  <label className="form-label">หมายเลขบัตร</label>
                  <input
                    type="text"
                    className="form-input"
                    value={formData.cardNumber}
                    onChange={(e) => setFormData({...formData, cardNumber: formatCardNumber(e.target.value)})}
                    placeholder="1234 1234 1234 1234"
                    maxLength="19"
                    required
                  />
                  <div className="card-icons">
                    <div className="card-icon">Visa</div>
                    <div className="card-icon">MC</div>
                    <div className="card-icon">AMEX</div>
                    <div className="card-icon">JCB</div>
                  </div>
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
                    required
                  />
                </div>
              </div>
              
              <div className="form-section">
                <div className="section-title">ที่อยู่ในการเรียกเก็บเงิน</div>
                
                <div className="form-group">
                  <label className="form-label">ประเทศ</label>
                  <select
                    className="form-input"
                    value={formData.country}
                    onChange={(e) => setFormData({...formData, country: e.target.value})}
                    required
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
                    required
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
                      required
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">จังหวัด</label>
                    <input
                      type="text"
                      className="form-input"
                      value={formData.province}
                      onChange={(e) => setFormData({...formData, province: e.target.value})}
                      required
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
                    required
                  />
                </div>
              </div>
              
              <button
                type="submit"
                className="btn-submit"
                disabled={processing || !omiseLoaded || amount <= 0}
              >
                {processing ? 'กำลังประมวลผล...' : `ชำระเงิน ${new Intl.NumberFormat('th-TH', {
                  style: 'currency',
                  currency: currency,
                  minimumFractionDigits: 0,
                }).format(amount)}`}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
