import React, { useState, useEffect } from 'react';
import './MyBookingsPage.css';
import AppHeader from './AppHeader';

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

export default function MyBookingsPage({ user, onBack, onLogout }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState({});
  const [activeTab, setActiveTab] = useState('bookings'); // Default to 'bookings'

  useEffect(() => {
    loadBookings();
  }, []);

  const loadBookings = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/list`, {
        credentials: 'include',
      });
      const data = await res.json();
      if (data?.ok) {
        setBookings(data.bookings || []);
      } else {
        setError('ไม่สามารถโหลดข้อมูลการจองได้');
      }
    } catch (err) {
      setError('เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'));
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
      const res = await fetch(`${API_BASE_URL}/api/booking/cancel?booking_id=${bookingId}`, {
        method: 'POST',
        credentials: 'include',
      });
      const data = await res.json();
      if (data?.ok) {
        alert(data.message || 'ยกเลิกการจองสำเร็จ');
        await loadBookings(); // Reload bookings
      } else {
        alert('เกิดข้อผิดพลาด: ' + (data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing({ ...processing, [bookingId]: null });
    }
  };

  const handlePayment = async (bookingId) => {
    if (!confirm('คุณต้องการชำระเงินเพื่อยืนยันการจองนี้หรือไม่?')) {
      return;
    }

    setProcessing({ ...processing, [bookingId]: 'paying' });
    try {
      const res = await fetch(`${API_BASE_URL}/api/booking/payment?booking_id=${bookingId}`, {
        method: 'POST',
        credentials: 'include',
      });
      const data = await res.json();
      if (data?.ok) {
        alert(data.message || 'ชำระเงินสำเร็จ');
        await loadBookings(); // Reload bookings
      } else {
        alert('เกิดข้อผิดพลาด: ' + (data.detail?.message || data.detail || 'Unknown error'));
      }
    } catch (err) {
      alert('เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'));
    } finally {
      setProcessing({ ...processing, [bookingId]: null });
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
        onTabChange={handleTabChange}
        onNavigateToBookings={null}
        onLogout={onLogout}
        notificationCount={0}
      />

      {/* Content */}
      <div className="my-bookings-content">

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
            const origin = travelSlots.origin_city || travelSlots.origin || '';
            const dest = travelSlots.destination_city || travelSlots.destination || '';
            const dateGo = travelSlots.departure_date || travelSlots.start_date || '';
            
            return (
              <div key={booking._id} className="booking-card">
                <div className="booking-header">
                  <div className="booking-title">
                    <span>{origin && dest ? `${origin} → ${dest}` : 'ทริป'}</span>
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
                  {booking.total_price && (
                    <div className="booking-detail-row">
                      <span className="detail-label">ราคารวม:</span>
                      <span className="detail-value price">
                        {formatCurrency(booking.total_price, booking.currency)}
                      </span>
                    </div>
                  )}
                  {booking.amadeus_booking_reference && (
                    <div className="booking-detail-row">
                      <span className="detail-label">หมายเลขการจอง:</span>
                      <span className="detail-value">{booking.amadeus_booking_reference}</span>
                    </div>
                  )}
                </div>

                {plan.flight && (
                  <div className="booking-flight-info">
                    <div className="flight-label">✈️ เที่ยวบิน</div>
                    {plan.flight.segments && plan.flight.segments.length > 0 && (
                      <div className="flight-route">
                        {plan.flight.segments[0].from} → {plan.flight.segments[plan.flight.segments.length - 1].to}
                      </div>
                    )}
                  </div>
                )}

                {plan.hotel && (
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
    </div>
  );
}

