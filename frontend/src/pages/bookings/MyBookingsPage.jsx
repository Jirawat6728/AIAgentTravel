import React, { useState, useEffect } from 'react';
import './MyBookingsPage.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import PaymentPopup from '../../components/bookings/PaymentPopup';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

function formatThaiDate(isoDate) {
  if (!isoDate) return '';
  try {
    const date = new Date(isoDate + 'T00:00:00');
    if (isNaN(date.getTime())) return isoDate;
    const day = date.getDate();
    const month = date.getMonth() + 1;
    const year = date.getFullYear() + 543;
    return `${day}/${month}/${year}`;
  } catch (e) {
    return isoDate;
  }
}

function formatThaiDateTime(isoDateTime) {
  if (!isoDateTime) return '';
  try {
    const date = new Date(isoDateTime);
    if (isNaN(date.getTime())) return isoDateTime;
    const day = date.getDate();
    const month = date.getMonth() + 1;
    const year = date.getFullYear() + 543;
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch (e) {
    return isoDateTime;
  }
}

function formatTime(isoDateTime) {
  if (!isoDateTime) return '';
  try {
    const date = new Date(isoDateTime);
    if (isNaN(date.getTime())) return '';
    const hours = date.getHours().toString().padStart(2, '0');
    const minutes = date.getMinutes().toString().padStart(2, '0');
    return `${hours}:${minutes}`;
  } catch (e) {
    return '';
  }
}

function formatCurrency(amount, currency = 'THB') {
  return new Intl.NumberFormat('th-TH', {
    style: 'currency',
    currency: currency,
    minimumFractionDigits: 0,
  }).format(amount);
}

function getStatusBadge(status) {
  const badges = {
    pending_payment: { text: 'รอชำระเงิน', class: 'status-pending' },
    confirmed: { text: 'จองสำเร็จ', class: 'status-confirmed' },
    paid: { text: 'ชำระเงินแล้ว', class: 'status-paid' },
    cancelled: { text: 'ยกเลิก', class: 'status-cancelled' },
    payment_failed: { text: 'ชำระเงินล้มเหลว', class: 'status-failed' },
  };
  return badges[status] || { text: status, class: 'status-unknown' };
}

export default function MyBookingsPage({ user, onBack, onLogout, onSignIn, notificationCount = 0, notifications = [], onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, onNavigateToAI = null, onNavigateToPayment = null, onMarkNotificationAsRead = null }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState({});
  const [activeTab, setActiveTab] = useState('bookings'); // Default to 'bookings'
  const [paymentModal, setPaymentModal] = useState(null); // { bookingId, booking, paymentUrl }
  const [editModal, setEditModal] = useState(null); // { bookingId, booking, formData }

  useEffect(() => {
    loadBookings();
  }, [user?.id]); // Reload when user changes

  useEffect(() => {
    document.body.classList.add('page-bookings');
    return () => document.body.classList.remove('page-bookings');
  }, []);

  // ✅ Listen for storage events to refresh when booking is created from another tab/window
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'booking_created' || e.key === 'booking_updated') {
        console.log('[MyBookings] Booking created/updated, refreshing...');
        loadBookings();
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    
    // ✅ Also listen for custom events (same window)
    const handleBookingCreated = () => {
      console.log('[MyBookings] Booking created event received, refreshing...');
      loadBookings();
    };
    
    window.addEventListener('bookingCreated', handleBookingCreated);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('bookingCreated', handleBookingCreated);
    };
  }, []);

  const theme = useTheme();

  const loadBookings = async () => {
    setLoading(true);
    setError(null);
    try {
      const headers = {
        'Content-Type': 'application/json'
      };
      
      // ✅ Send X-User-ID for guest/bypass mode
      // ✅ Use user.user_id (from backend) or user.id (fallback) - backend uses user_id
      const userIdToSend = user?.user_id || user?.id;
      if (userIdToSend) {
        headers['X-User-ID'] = userIdToSend;
      }

      // ✅ Add timeout (10 seconds) to prevent hanging
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      try {
        const res = await fetch(`${API_BASE_URL}/api/booking/list`, {
          headers,
          credentials: 'include',
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!res.ok) {
          const errorText = await res.text();
          console.error(`[MyBookings] HTTP Error ${res.status}:`, errorText);
          throw new Error(`HTTP Error: ${res.status}`);
        }
        
        const data = await res.json();
        
        if (data?.ok) {
          const bookingsList = data.bookings || [];
          setBookings(bookingsList);
          
          // ✅ Log only if there's an issue
          if (bookingsList.length === 0 && userIdToSend) {
            console.debug(`[MyBookings] No bookings found for user: ${userIdToSend}`);
          }
        } else {
          const errorMsg = data.message || data.detail || 'เกิดข้อผิดพลาดในการดึงข้อมูล';
          setError(errorMsg);
        }
      } catch (fetchErr) {
        clearTimeout(timeoutId);
        if (fetchErr.name === 'AbortError') {
          throw new Error('การเชื่อมต่อช้าเกินไป กรุณาลองใหม่อีกครั้ง');
        }
        throw fetchErr;
      }
    } catch (err) {
      console.error('[MyBookings] Error loading bookings:', err);
      const errorMessage = err.message || 'เกิดข้อผิดพลาดในการเชื่อมต่อ';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (bookingId) => {
    if (!confirm('คุณต้องการยกเลิกการจองนี้หรือไม่?')) {
      return;
    }

    setProcessing({ ...processing, [bookingId]: 'cancelling' });
    try {
      const headers = {};
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }

      const res = await fetch(`${API_BASE_URL}/api/booking/cancel?booking_id=${bookingId}`, {
        method: 'POST',
        headers,
        credentials: 'include',
      });
      const data = await res.json();
      if (data?.ok) {
        alert(data.message || 'ยกเลิกการจองสำเร็จ');
        await loadBookings(); // Reload bookings
      } else {
        const errorMsg = data.detail 
          ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
          : 'Unknown error';
        alert('เกิดข้อผิดพลาด: ' + errorMsg);
      }
    } catch (err) {
      alert('เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing({ ...processing, [bookingId]: null });
    }
  };

  const handlePayment = async (bookingId) => {
    const booking = bookings.find(b => b._id === bookingId);
    if (!booking) {
      alert('ไม่พบข้อมูลการจอง');
      return;
    }

    setProcessing({ ...processing, [bookingId]: 'paying' });
    try {
      const headers = {};
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }

      // Get payment URL from backend (Omise checkout)
      const res = await fetch(`${API_BASE_URL}/api/booking/payment?booking_id=${bookingId}`, {
        method: 'POST',
        headers,
        credentials: 'include',
      });
      
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        const errorMsg = errorData.detail || `HTTP ${res.status}`;
        
        // Translate common error messages to Thai
        let thaiMessage = errorMsg;
        if (errorMsg.includes('Payment gateway configuration missing')) {
          thaiMessage = 'ระบบชำระเงินยังไม่ได้ตั้งค่า กรุณาติดต่อผู้ดูแลระบบ';
        } else if (errorMsg.includes('Payment gateway authentication failed')) {
          thaiMessage = 'การยืนยันตัวตนกับระบบชำระเงินล้มเหลว กรุณาตรวจสอบ API Key';
        } else if (errorMsg.includes('Payment gateway unreachable')) {
          thaiMessage = 'ไม่สามารถเชื่อมต่อกับระบบชำระเงินได้ กรุณาลองใหม่อีกครั้ง';
        } else if (errorMsg.includes('Invalid response from payment gateway')) {
          thaiMessage = 'ระบบชำระเงินส่งข้อมูลผิดรูปแบบ กรุณาลองใหม่อีกครั้ง';
        } else if (errorMsg.includes('Payment processing failed')) {
          thaiMessage = 'การประมวลผลการชำระเงินล้มเหลว กรุณาลองใหม่อีกครั้ง';
        }
        
        throw new Error(thaiMessage);
      }
      
      const data = await res.json();
      
      if (data?.ok) {
        // If payment is already processed
        if (data.status === 'paid' || data.status === 'confirmed') {
          alert(data.message || 'ชำระเงินสำเร็จ');
          await loadBookings(); // Reload bookings
          return;
        }
        
        // ✅ ลิงก์ Omise โดยตรง (pay.omise.co ฯลฯ) → เด้งไปหน้าชำระเงินทันที
        if (data.payment_url && data.payment_url.startsWith('http') && (data.payment_url.includes('omise') || data.payment_url.includes('pay.'))) {
          window.location.href = data.payment_url;
        } else if (data.payment_url && (data.payment_url.includes('/payment-page/') || data.payment_url.includes('/api/booking/payment-page'))) {
          // ✅ หน้า payment ภายใน (SPA) → ใช้ callback ให้ App สลับ view + ตั้ง URL
          const paymentUrlParsed = new URL(data.payment_url, window.location.origin);
          const urlBookingId = paymentUrlParsed.pathname.split('/').pop() || bookingId;
          if (onNavigateToPayment) {
            onNavigateToPayment(urlBookingId);
          } else {
            if (window.history && window.history.pushState) {
              window.history.pushState({ view: 'payment' }, '', `/payment?booking_id=${urlBookingId}`);
              window.dispatchEvent(new PopStateEvent('popstate'));
            } else {
              window.location.href = `/payment?booking_id=${urlBookingId}`;
            }
          }
        } else {
          // Show payment modal with payment methods (for Omise Links)
          setPaymentModal({
            bookingId,
            booking,
            paymentUrl: data.payment_url,
            amount: booking.total_price,
            currency: booking.currency || 'THB'
          });
        }
      } else {
        let errorMsg = 'Unknown error';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (data.detail.message && typeof data.detail.message === 'string') {
            errorMsg = data.detail.message;
          } else {
            errorMsg = JSON.stringify(data.detail);
          }
        }
        alert('เกิดข้อผิดพลาด: ' + errorMsg);
      }
    } catch (err) {
      const errorMessage = err.message || 'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ';
      alert(`⚠️ ${errorMessage}`);
    } finally {
      setProcessing({ ...processing, [bookingId]: null });
    }
  };

    const handlePaymentMethodSelect = (method) => {
    if (!paymentModal) return;
    
    // Redirect to Omise payment gateway
    if (method === 'credit_card' || method === 'qr' || method === 'promptpay') {
      if (paymentModal.paymentUrl) {
        // If it's a fallback URL (internal link) because keys are missing/mocked
        // allow the redirect to happen so the user sees the mock page
        // BUT if user specifically wanted to avoid homepage redirect, we should just let it happen naturally
        
        // However, the issue described is "Development Mode: Omise API Keys Missing" alert
        // This comes from this specific check:
        /* 
        if (paymentModal.paymentUrl.includes('/payment/omise')) {
          alert('⚠️ Development Mode: Omise API Keys Missing\n\nThis is a fallback URL because payment gateway is not configured.\nTo fix: Add OMISE_SECRET_KEY in backend/.env');
          // Optional: Open in new tab to avoid breaking current SPA state
          window.open(paymentModal.paymentUrl, '_blank');
          return;
        }
        */
       
        // If the backend returns a fallback URL, it means it thinks keys are missing.
        // We will remove this client-side check and just follow the link.
        // If it's a mock URL, it goes to a mock page. If real, it goes to Omise.
        
        // For real payment URL (e.g. omise.co) OR our mock endpoint, just redirect.
        window.location.href = paymentModal.paymentUrl;
      } else {
        alert('ลิงก์ชำระเงินไม่พร้อมใช้งาน กรุณาลองใหม่อีกครั้ง');
      }
    }
  };

  const handleEdit = (bookingId) => {
    const booking = bookings.find(b => b._id === bookingId);
    if (!booking) {
      alert('ไม่พบข้อมูลการจอง');
      return;
    }

    // ✅ Navigate to chat page with trip_id and chat_id
    const tripId = booking.trip_id;
    const chatId = booking.chat_id || tripId;
    
    if (!tripId) {
      alert('ไม่พบข้อมูลทริป กรุณาติดต่อผู้ดูแลระบบ');
      return;
    }

    // ✅ Store booking info for chat to use
    const editContext = {
      bookingId: bookingId,
      tripId: tripId,
      chatId: chatId,
      booking: booking,
      action: 'edit_trip'
    };
    
    // Store in localStorage for chat to pick up
    localStorage.setItem('edit_booking_context', JSON.stringify(editContext));
    
    // ✅ Navigate to chat and send edit message
    if (onNavigateToAI) {
      // Navigate to chat (message will be auto-sent by AITravelChat)
      onNavigateToAI(tripId, chatId, '');
    } else {
      // Fallback: navigate using window.location
      window.location.href = `/chat?trip_id=${tripId}&chat_id=${chatId}&edit_booking=${bookingId}`;
    }
  };

  const handleUpdateBooking = async () => {
    if (!editModal) return;

    setProcessing({ ...processing, [editModal.bookingId]: 'updating' });
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user?.id) {
        headers['X-User-ID'] = user.id;
      }

      // Build update payload
      const updatePayload = {
        total_price: parseFloat(editModal.formData.total_price),
        travel_slots: {
          origin_city: editModal.formData.origin_city,
          destination_city: editModal.formData.destination_city,
          departure_date: editModal.formData.departure_date,
          return_date: editModal.formData.return_date
        }
      };

      const res = await fetch(`${API_BASE_URL}/api/booking/update?booking_id=${editModal.bookingId}`, {
        method: 'PUT',
        headers,
        credentials: 'include',
        body: JSON.stringify(updatePayload)
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${res.status}`);
      }

      const data = await res.json();

      if (data?.ok) {
        alert(data.message || 'อัปเดตการจองสำเร็จ');
        setEditModal(null);
        await loadBookings(); // Reload bookings
      } else {
        throw new Error(data.detail || 'Unknown error');
      }
    } catch (err) {
      alert('เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing({ ...processing, [editModal.bookingId]: null });
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab !== 'bookings' && onBack) {
      onBack();
    }
  };

  return (
    <div className="my-bookings-container">
      {/* Header */}
      <AppHeader
        activeTab={activeTab}
        user={user}
        onNavigateToHome={onNavigateToHome}
        onTabChange={handleTabChange}
        onNavigateToBookings={null}
        onLogout={onLogout}
        onSignIn={onSignIn}
        notificationCount={notificationCount}
        notifications={notifications}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
      />

      {/* Content */}
      <div className="my-bookings-content" data-theme={theme}>

        {loading ? (
          <div className="my-bookings-loading">⏳ กำลังโหลดข้อมูล...</div>
        ) : error ? (
          <div className="my-bookings-error">❌ {error}</div>
        ) : bookings.length === 0 ? (
          <div className="my-bookings-empty">
            <div className="empty-icon">📭</div>
            <div className="empty-text">ยังไม่มีการจอง</div>
            <div className="empty-subtext">เมื่อคุณจองทริป การจองจะแสดงที่นี่</div>
          </div>
        ) : (
          <div className="bookings-list">
          {bookings.map((booking) => {
            const plan = booking.plan || {};
            const travelSlots = booking.travel_slots || {};
            const statusBadge = getStatusBadge(booking.status);
            
            // ✅ ดึงข้อมูลจาก travel_slots (จาก database)
            const origin = travelSlots.origin_city || travelSlots.origin || '';
            const dest = travelSlots.destination_city || travelSlots.destination || '';
            const dateGo = travelSlots.departure_date || travelSlots.start_date || '';
            const dateReturn = travelSlots.return_date || travelSlots.end_date || '';
            const adults = travelSlots.adults || travelSlots.guests || 1;
            const children = travelSlots.children || 0;
            const nights = travelSlots.nights || null;
            
            // ✅ ดึงข้อมูลจาก travel_slots.flights (array of segments)
            const flights = travelSlots.flights || [];
            const accommodations = travelSlots.accommodations || [];
            const groundTransport = travelSlots.ground_transport || [];
            
            // ✅ ดึงข้อมูลเที่ยวบินจาก segments
            let outboundFlight = null;
            let inboundFlight = null;
            
            // ตรวจสอบว่ามี flight objects หลายตัวหรือไม่
            if (flights.length > 0) {
              // Flight ตัวแรก = ขาไป
              const firstFlight = flights[0];
              const firstSelectedOption = firstFlight?.selected_option || {};
              const firstRawData = firstSelectedOption?.raw_data || {};
              const firstItineraries = firstRawData?.itineraries || [];
              
              if (firstItineraries.length > 0) {
                // ขาไป (Outbound) - ใช้ itinerary แรกของ flight แรก
                const outItinerary = firstItineraries[0];
                const outSegments = outItinerary?.segments || [];
                if (outSegments.length > 0) {
                  const firstSeg = outSegments[0];
                  const lastSeg = outSegments[outSegments.length - 1];
                  outboundFlight = {
                    from: firstSeg?.departure?.iataCode || firstFlight?.requirements?.origin || '',
                    to: lastSeg?.arrival?.iataCode || firstFlight?.requirements?.destination || '',
                    airline: firstSeg?.carrierCode || '',
                    flightNumber: `${firstSeg?.carrierCode || ''}${firstSeg?.number || ''}`,
                    departureTime: firstSeg?.departure?.at || '',
                    arrivalTime: lastSeg?.arrival?.at || '',
                    price: firstSelectedOption?.price_amount || firstSelectedOption?.price_total || 0,
                    currency: firstSelectedOption?.currency || 'THB'
                  };
                }
              }
              
              // ขากลับ (Inbound) - ตรวจสอบหลายกรณี
              if (flights.length > 1) {
                // กรณีที่ 1: มี flight object ที่สอง (ขากลับ)
                const secondFlight = flights[1];
                const secondSelectedOption = secondFlight?.selected_option || {};
                const secondRawData = secondSelectedOption?.raw_data || {};
                const secondItineraries = secondRawData?.itineraries || [];
                
                if (secondItineraries.length > 0) {
                  const inItinerary = secondItineraries[0];
                  const inSegments = inItinerary?.segments || [];
                  if (inSegments.length > 0) {
                    const firstSeg = inSegments[0];
                    const lastSeg = inSegments[inSegments.length - 1];
                    inboundFlight = {
                      from: firstSeg?.departure?.iataCode || secondFlight?.requirements?.origin || '',
                      to: lastSeg?.arrival?.iataCode || secondFlight?.requirements?.destination || '',
                      airline: firstSeg?.carrierCode || '',
                      flightNumber: `${firstSeg?.carrierCode || ''}${firstSeg?.number || ''}`,
                      departureTime: firstSeg?.departure?.at || '',
                      arrivalTime: lastSeg?.arrival?.at || '',
                      price: secondSelectedOption?.price_amount || secondSelectedOption?.price_total || 0,
                      currency: secondSelectedOption?.currency || 'THB'
                    };
                  }
                }
              } else if (firstItineraries.length > 1) {
                // กรณีที่ 2: มี itinerary ที่สองใน flight object เดียวกัน (round trip)
                const inItinerary = firstItineraries[1];
                const inSegments = inItinerary?.segments || [];
                if (inSegments.length > 0) {
                  const firstSeg = inSegments[0];
                  const lastSeg = inSegments[inSegments.length - 1];
                  inboundFlight = {
                    from: firstSeg?.departure?.iataCode || '',
                    to: lastSeg?.arrival?.iataCode || '',
                    airline: firstSeg?.carrierCode || '',
                    flightNumber: `${firstSeg?.carrierCode || ''}${firstSeg?.number || ''}`,
                    departureTime: firstSeg?.departure?.at || '',
                    arrivalTime: lastSeg?.arrival?.at || '',
                  };
                }
              }
            }
            
            // ✅ ดึงข้อมูลที่พักจาก segments
            let hotelInfo = null;
            if (accommodations.length > 0) {
              const firstHotel = accommodations[0];
              const selectedOption = firstHotel?.selected_option || {};
              hotelInfo = {
                name: selectedOption?.display_name || selectedOption?.name || firstHotel?.requirements?.location || '',
                location: firstHotel?.requirements?.location || '',
                checkIn: firstHotel?.requirements?.check_in || '',
                checkOut: firstHotel?.requirements?.check_out || '',
                price: selectedOption?.price_amount || selectedOption?.price_total || 0,
                currency: selectedOption?.currency || 'THB',
                rating: selectedOption?.rating || null
              };
            }
            
            return (
              <div key={booking._id} className="booking-card">
                <div className="booking-header">
                  <div className="booking-title">
                    <span>{origin && dest ? `${origin} → ${dest}` : 'ทริป'}</span>
                    {/* ✅ Agent Mode Badge */}
                    {booking.metadata?.mode === 'agent' || booking.metadata?.auto_booked ? (
                      <span className="status-badge" style={{
                        background: 'rgba(139, 92, 246, 0.2)',
                        color: '#8b5cf6',
                        border: '1px solid rgba(139, 92, 246, 0.4)',
                        marginLeft: '8px',
                        fontSize: '12px',
                        padding: '4px 8px'
                      }}>
                        🤖 Agent Mode
                      </span>
                    ) : null}
                    <span className={`status-badge ${statusBadge.class}`}>
                      {statusBadge.text}
                    </span>
                  </div>
                  <div className="booking-date">
                    {formatThaiDate(booking.created_at)}
                  </div>
                </div>

                <div className="booking-details">
                  <div className="booking-detail-row">
                    <span className="detail-label">วันเดินทาง:</span>
                    <span className="detail-value">{formatThaiDate(dateGo)}</span>
                  </div>
                  {dateReturn && (
                    <div className="booking-detail-row">
                      <span className="detail-label">วันกลับ:</span>
                      <span className="detail-value">{formatThaiDate(dateReturn)}</span>
                    </div>
                  )}
                  {nights && (
                    <div className="booking-detail-row">
                      <span className="detail-label">จำนวนคืน:</span>
                      <span className="detail-value">{nights} คืน</span>
                    </div>
                  )}
                  <div className="booking-detail-row">
                    <span className="detail-label">ผู้โดยสาร:</span>
                    <span className="detail-value">
                      {adults} ผู้ใหญ่{children > 0 ? `, ${children} เด็ก` : ''}
                    </span>
                  </div>
                  {/* ✅ แสดงข้อมูลไฟท์บินขาไป */}
                  {outboundFlight && (
                    <div className="booking-flight-section">
                      <div className="flight-section-header">
                        <span className="flight-icon">🛫</span>
                        <span className="flight-label">ขาไป</span>
                      </div>
                      <div className="flight-details">
                        {outboundFlight.from && outboundFlight.to && (
                          <div className="flight-route">
                            {outboundFlight.from} → {outboundFlight.to}
                          </div>
                        )}
                        {outboundFlight.flightNumber && (
                          <div className="flight-number">
                            เที่ยวบิน: {outboundFlight.flightNumber}
                          </div>
                        )}
                        {outboundFlight.departureTime && (
                          <div className="flight-time">
                            ออก: {formatTime(outboundFlight.departureTime)}
                          </div>
                        )}
                        {outboundFlight.arrivalTime && (
                          <div className="flight-time">
                            ถึง: {formatTime(outboundFlight.arrivalTime)}
                          </div>
                        )}
                        {outboundFlight.airline && (
                          <div className="flight-airline">
                            สายการบิน: {outboundFlight.airline}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* ✅ แสดงข้อมูลไฟท์บินขากลับ */}
                  {inboundFlight && (
                    <div className="booking-flight-section">
                      <div className="flight-section-header">
                        <span className="flight-icon">🛬</span>
                        <span className="flight-label">ขากลับ</span>
                      </div>
                      <div className="flight-details">
                        {inboundFlight.from && inboundFlight.to && (
                          <div className="flight-route">
                            {inboundFlight.from} → {inboundFlight.to}
                          </div>
                        )}
                        {inboundFlight.flightNumber && (
                          <div className="flight-number">
                            เที่ยวบิน: {inboundFlight.flightNumber}
                          </div>
                        )}
                        {inboundFlight.departureTime && (
                          <div className="flight-time">
                            ออก: {formatTime(inboundFlight.departureTime)}
                          </div>
                        )}
                        {inboundFlight.arrivalTime && (
                          <div className="flight-time">
                            ถึง: {formatTime(inboundFlight.arrivalTime)}
                          </div>
                        )}
                        {inboundFlight.airline && (
                          <div className="flight-airline">
                            สายการบิน: {inboundFlight.airline}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* ✅ แสดงข้อมูลไฟท์บินจาก plan.flight (fallback) */}
                  {!outboundFlight && !inboundFlight && plan.flight && (
                    <div className="booking-flight-section">
                      <div className="flight-section-header">
                        <span className="flight-icon">✈️</span>
                        <span className="flight-label">เที่ยวบิน</span>
                      </div>
                      <div className="flight-details">
                        {plan.flight.outbound && plan.flight.outbound.length > 0 && (
                          <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontWeight: 600, marginBottom: '6px', color: '#2563eb' }}>🛫 ขาไป</div>
                            {plan.flight.outbound.map((seg, idx) => (
                              <div key={idx} style={{ marginBottom: '4px', fontSize: '14px' }}>
                                {seg.from && seg.to && `${seg.from} → ${seg.to}`}
                                {seg.number && ` (${seg.carrier || ''}${seg.number})`}
                                {seg.depart_time && ` - ออก ${formatTime(seg.depart_at || seg.departure)}`}
                                {seg.arrive_time && ` ถึง ${formatTime(seg.arrive_at || seg.arrival)}`}
                              </div>
                            ))}
                          </div>
                        )}
                        {plan.flight.inbound && plan.flight.inbound.length > 0 && (
                          <div>
                            <div style={{ fontWeight: 600, marginBottom: '6px', color: '#2563eb' }}>🛬 ขากลับ</div>
                            {plan.flight.inbound.map((seg, idx) => (
                              <div key={idx} style={{ marginBottom: '4px', fontSize: '14px' }}>
                                {seg.from && seg.to && `${seg.from} → ${seg.to}`}
                                {seg.number && ` (${seg.carrier || ''}${seg.number})`}
                                {seg.depart_time && ` - ออก ${formatTime(seg.depart_at || seg.departure)}`}
                                {seg.arrive_time && ` ถึง ${formatTime(seg.arrive_at || seg.arrival)}`}
                              </div>
                            ))}
                          </div>
                        )}
                        {plan.flight.segments && plan.flight.segments.length > 0 && (!plan.flight.outbound || plan.flight.outbound.length === 0) && (!plan.flight.inbound || plan.flight.inbound.length === 0) && (
                          <div className="flight-route">
                            {plan.flight.segments[0].from} → {plan.flight.segments[plan.flight.segments.length - 1].to}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* ✅ แสดงราคารวมทั้งหมด (เด่นชัด) */}
                  {booking.total_price && booking.total_price > 0 && (
                    <div className="booking-total-price">
                      <div className="total-price-label">💰 ราคารวมทั้งหมด</div>
                      <div className="total-price-value">
                        {formatCurrency(booking.total_price, booking.currency || 'THB')}
                      </div>
                    </div>
                  )}
                  {booking.amadeus_booking_reference && (
                    <div className="booking-detail-row">
                      <span className="detail-label">หมายเลขการจอง:</span>
                      <span className="detail-value">{booking.amadeus_booking_reference}</span>
                    </div>
                  )}
                </div>

                {/* ✅ แสดงข้อมูลเที่ยวบินจาก travel_slots */}
                {(outboundFlight || inboundFlight) && (
                  <div className="booking-flight-info">
                    <div className="flight-label">✈️ เที่ยวบิน</div>
                    
                    {/* ขาไป */}
                    {outboundFlight && (
                      <div className="flight-direction-section" style={{ marginBottom: inboundFlight ? '12px' : '0' }}>
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#2563eb', marginBottom: '4px' }}>🛫 ขาไป</div>
                        <div className="flight-route">
                          {outboundFlight.from} → {outboundFlight.to}
                        </div>
                        <div className="flight-details" style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                          {outboundFlight.airline} {outboundFlight.flightNumber}
                          {outboundFlight.departureTime && outboundFlight.arrivalTime && (
                            <span style={{ marginLeft: '8px' }}>
                              ({formatTime(outboundFlight.departureTime)} - {formatTime(outboundFlight.arrivalTime)})
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* ขากลับ */}
                    {inboundFlight && (
                      <div className="flight-direction-section">
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#10b981', marginBottom: '4px' }}>🛬 ขากลับ</div>
                        <div className="flight-route">
                          {inboundFlight.from} → {inboundFlight.to}
                        </div>
                        <div className="flight-details" style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                          {inboundFlight.airline} {inboundFlight.flightNumber}
                          {inboundFlight.departureTime && inboundFlight.arrivalTime && (
                            <span style={{ marginLeft: '8px' }}>
                              ({formatTime(inboundFlight.departureTime)} - {formatTime(inboundFlight.arrivalTime)})
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* แสดงราคา */}
                    {(outboundFlight?.price > 0 || inboundFlight?.price > 0) && (
                      <div style={{ fontSize: '13px', color: '#2563eb', marginTop: '8px', fontWeight: 600 }}>
                        {outboundFlight?.price > 0 && (
                          <span>
                            ขาไป: {formatCurrency(outboundFlight.price, outboundFlight.currency)}
                          </span>
                        )}
                        {outboundFlight?.price > 0 && inboundFlight?.price > 0 && <span> • </span>}
                        {inboundFlight?.price > 0 && (
                          <span>
                            ขากลับ: {formatCurrency(inboundFlight.price, inboundFlight.currency)}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* ✅ แสดงข้อมูลที่พักจาก travel_slots */}
                {hotelInfo && (
                  <div className="booking-hotel-info">
                    <div className="hotel-label">🏨 ที่พัก</div>
                    <div className="hotel-name">{hotelInfo.name || '—'}</div>
                    {hotelInfo.location && (
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        📍 {hotelInfo.location}
                      </div>
                    )}
                    {hotelInfo.checkIn && hotelInfo.checkOut && (
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        📅 เช็คอิน: {formatThaiDate(hotelInfo.checkIn)} - เช็คเอาท์: {formatThaiDate(hotelInfo.checkOut)}
                      </div>
                    )}
                    {hotelInfo.price > 0 && (
                      <div style={{ fontSize: '13px', color: '#2563eb', marginTop: '4px', fontWeight: 600 }}>
                        {formatCurrency(hotelInfo.price, hotelInfo.currency)}
                      </div>
                    )}
                  </div>
                )}

                {/* ✅ Fallback: แสดงข้อมูลจาก plan.flight ถ้าไม่มีใน travel_slots */}
                {!outboundFlight && !inboundFlight && plan.flight && (
                  <div className="booking-flight-info">
                    <div className="flight-label">✈️ เที่ยวบิน</div>
                    
                    {/* ✅ แสดงขาไปจาก plan.flight.outbound */}
                    {plan.flight.outbound && plan.flight.outbound.length > 0 && (
                      <div className="flight-direction-section" style={{ marginBottom: (plan.flight.inbound && plan.flight.inbound.length > 0) ? '12px' : '0' }}>
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#2563eb', marginBottom: '4px' }}>🛫 ขาไป</div>
                        {plan.flight.outbound.map((seg, idx) => (
                          <div key={idx} style={{ marginBottom: idx < plan.flight.outbound.length - 1 ? '6px' : '0' }}>
                            <div className="flight-route">
                              {seg.from} → {seg.to}
                            </div>
                            <div className="flight-details" style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                              {seg.carrier && seg.number && `${seg.carrier}${seg.number}`}
                              {seg.depart_time && ` - ออก ${seg.depart_time}`}
                              {seg.arrive_time && ` ถึง ${seg.arrive_time}`}
                              {seg.depart_at && !seg.depart_time && ` - ออก ${formatTime(seg.depart_at)}`}
                              {seg.arrive_at && !seg.arrive_time && ` ถึง ${formatTime(seg.arrive_at)}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* ✅ แสดงขากลับจาก plan.flight.inbound */}
                    {plan.flight.inbound && plan.flight.inbound.length > 0 && (
                      <div className="flight-direction-section">
                        <div style={{ fontSize: '12px', fontWeight: 600, color: '#10b981', marginBottom: '4px' }}>🛬 ขากลับ</div>
                        {plan.flight.inbound.map((seg, idx) => (
                          <div key={idx} style={{ marginBottom: idx < plan.flight.inbound.length - 1 ? '6px' : '0' }}>
                            <div className="flight-route">
                              {seg.from} → {seg.to}
                            </div>
                            <div className="flight-details" style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                              {seg.carrier && seg.number && `${seg.carrier}${seg.number}`}
                              {seg.depart_time && ` - ออก ${seg.depart_time}`}
                              {seg.arrive_time && ` ถึง ${seg.arrive_time}`}
                              {seg.depart_at && !seg.depart_time && ` - ออก ${formatTime(seg.depart_at)}`}
                              {seg.arrive_at && !seg.arrive_time && ` ถึง ${formatTime(seg.arrive_at)}`}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* ✅ Fallback: แสดงแบบเดิมถ้าไม่มี outbound/inbound */}
                    {(!plan.flight.outbound || plan.flight.outbound.length === 0) && (!plan.flight.inbound || plan.flight.inbound.length === 0) && plan.flight.segments && plan.flight.segments.length > 0 && (
                      <div className="flight-route">
                        {plan.flight.segments[0].from} → {plan.flight.segments[plan.flight.segments.length - 1].to}
                      </div>
                    )}
                    
                    {/* ✅ แสดงราคาไฟท์บิน */}
                    {plan.flight.price_total && (
                      <div style={{ fontSize: '13px', color: '#2563eb', marginTop: '8px', fontWeight: 600 }}>
                        ราคาไฟท์บิน: {formatCurrency(plan.flight.price_total, plan.flight.currency || booking.currency || 'THB')}
                      </div>
                    )}
                  </div>
                )}

                {!hotelInfo && plan.hotel && (
                  <div className="booking-hotel-info">
                    <div className="hotel-label">🏨 ที่พัก</div>
                    <div className="hotel-name">{plan.hotel.hotelName || plan.hotel.name || '—'}</div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="booking-actions">
                  {booking.status === 'pending_payment' && (
                    <>
                      <button
                        className="btn-payment"
                        onClick={() => handlePayment(booking._id)}
                        disabled={processing[booking._id] === 'paying'}
                      >
                        {processing[booking._id] === 'paying' ? 'กำลังดำเนินการ...' : '💳 จ่ายเงิน'}
                      </button>
                      <button
                        className="btn-edit"
                        onClick={() => handleEdit(booking._id)}
                        disabled={processing[booking._id] === 'updating'}
                      >
                        {processing[booking._id] === 'updating' ? 'กำลังดำเนินการ...' : '✏️ แก้ไข'}
                      </button>
                      <button
                        className="btn-cancel"
                        onClick={() => handleCancel(booking._id)}
                        disabled={processing[booking._id] === 'cancelling'}
                      >
                        {processing[booking._id] === 'cancelling' ? 'กำลังดำเนินการ...' : '❌ ยกเลิกการจอง'}
                      </button>
                    </>
                  )}
                  {booking.status === 'confirmed' && (
                    <button
                      className="btn-cancel"
                      onClick={() => handleCancel(booking._id)}
                      disabled={processing[booking._id] === 'cancelling'}
                    >
                      {processing[booking._id] === 'cancelling' ? 'กำลังดำเนินการ...' : '❌ ยกเลิกการจอง'}
                    </button>
                  )}
                  {booking.status === 'cancelled' && (
                    <div className="booking-cancelled-note">
                      การจองนี้ถูกยกเลิกแล้ว
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          </div>
        )}
      </div>

      {/* Payment Popup – shown after "จ่ายเงิน" */}
      <PaymentPopup
        open={!!paymentModal}
        onClose={() => setPaymentModal(null)}
        bookingId={paymentModal?.bookingId}
        booking={paymentModal?.booking}
        paymentUrl={paymentModal?.paymentUrl}
        amount={paymentModal?.amount}
        currency={paymentModal?.currency || 'THB'}
        onSelectMethod={handlePaymentMethodSelect}
      />

      {/* Edit Booking Modal */}
      {editModal && (
        <div className="payment-modal-overlay" onClick={() => setEditModal(null)}>
          <div className="payment-modal" onClick={(e) => e.stopPropagation()}>
            <div className="payment-modal-header">
              <h2>✏️ แก้ไขการจอง</h2>
              <button className="payment-modal-close" onClick={() => setEditModal(null)}>✕</button>
            </div>
            
            <div className="payment-modal-body">
              <div className="edit-form">
                <div className="form-group">
                  <label className="form-label">ต้นทาง</label>
                  <input
                    type="text"
                    className="form-input"
                    value={editModal.formData.origin_city}
                    onChange={(e) => setEditModal({
                      ...editModal,
                      formData: { ...editModal.formData, origin_city: e.target.value }
                    })}
                    placeholder="เช่น กรุงเทพ"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">ปลายทาง</label>
                  <input
                    type="text"
                    className="form-input"
                    value={editModal.formData.destination_city}
                    onChange={(e) => setEditModal({
                      ...editModal,
                      formData: { ...editModal.formData, destination_city: e.target.value }
                    })}
                    placeholder="เช่น ภูเก็ต"
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">วันเดินทาง</label>
                  <input
                    type="date"
                    className="form-input"
                    value={editModal.formData.departure_date}
                    onChange={(e) => setEditModal({
                      ...editModal,
                      formData: { ...editModal.formData, departure_date: e.target.value }
                    })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">วันกลับ</label>
                  <input
                    type="date"
                    className="form-input"
                    value={editModal.formData.return_date}
                    onChange={(e) => setEditModal({
                      ...editModal,
                      formData: { ...editModal.formData, return_date: e.target.value }
                    })}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">ราคารวม (บาท)</label>
                  <input
                    type="number"
                    className="form-input"
                    value={editModal.formData.total_price}
                    onChange={(e) => setEditModal({
                      ...editModal,
                      formData: { ...editModal.formData, total_price: e.target.value }
                    })}
                    placeholder="0"
                    min="0"
                  />
                </div>
              </div>

              <div className="edit-modal-actions">
                <button 
                  className="btn-save"
                  onClick={handleUpdateBooking}
                  disabled={processing[editModal.bookingId] === 'updating'}
                >
                  {processing[editModal.bookingId] === 'updating' ? 'กำลังบันทึก...' : '💾 บันทึกการเปลี่ยนแปลง'}
                </button>
                <button 
                  className="btn-cancel-edit"
                  onClick={() => setEditModal(null)}
                >
                  ยกเลิก
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

