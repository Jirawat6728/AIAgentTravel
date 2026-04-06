import React, { useState, useEffect } from 'react';
import Swal from 'sweetalert2';
import './MyBookingsPage.css';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useLanguage } from '../../context/LanguageContext';
import { useFontSize } from '../../context/FontSizeContext';
import PaymentPopup from '../../components/bookings/PaymentPopup';
import { formatPriceInThb, toThb } from '../../utils/currency';
import { isTripPastTransactionDeadline } from '../../utils/tripDateLock';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';

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

function getStatusBadge(status) {
  const badges = {
    pending_payment: { textKey: 'bookings.statusPending', class: 'status-pending' },
    confirmed: { textKey: 'bookings.statusConfirmed', class: 'status-confirmed' },
    paid: { textKey: 'bookings.statusPaid', class: 'status-paid' },
    cancelled: { textKey: 'bookings.statusCancelled', class: 'status-cancelled' },
    payment_failed: { textKey: 'bookings.statusFailed', class: 'status-failed' },
  };
  return badges[status] || { text: status, class: 'status-unknown' };
}

export default function MyBookingsPage({ user, onBack, onLogout, onSignIn, notificationCount = 0, notifications = [], onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, onNavigateToAI = null, onNavigateToPayment = null, onMarkNotificationAsRead = null, isActive = true }) {
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [processing, setProcessing] = useState({});
  const [activeTab, setActiveTab] = useState('bookings'); // Default to 'bookings'
  const [paymentModal, setPaymentModal] = useState(null); // { bookingId, booking, paymentUrl }
  const [editModal, setEditModal] = useState(null); // { bookingId, booking, formData }
  const [editFlightSearch, setEditFlightSearch] = useState({
    loading: false,
    outbound: [], inboundResults: [],
    outboundError: null, inboundError: null,
    searched: false,
    activeTab: 'outbound', // 'outbound' | 'inbound'
    confirmedOutbound: false,
    confirmedInbound: false,
    collapsed: false, // ซ่อนรายการหลังยืนยัน
  });
  const [editHotelSearch, setEditHotelSearch] = useState({ loading: false, results: [], error: null });
  const [editCarSearch, setEditCarSearch] = useState({ loading: false, results: [], error: null });
  const [refundModal, setRefundModal] = useState(null); // { bookingId, booking, eligibility: { refundable_items, total_refundable_amount, can_full_refund, message }, loading }

  // โหลดรายการเมื่อ user เปลี่ยน หรือเมื่อเปิดแท็บ My Bookings (หลังจองจาก Agent)
  useEffect(() => {
    loadBookings();
  }, [user?.id, user?.user_id, isActive]); // Reload when user changes or when page becomes active

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
    
    // ✅ Also listen for custom events (same window) — รอสั้นๆ ให้ backend commit + invalidate cache ก่อนโหลดใหม่
    const handleBookingCreated = () => {
      console.log('[MyBookings] Booking created event received, refreshing...');
      setTimeout(() => loadBookings(), 600);
    };
    
    window.addEventListener('bookingCreated', handleBookingCreated);
    
    // ✅ โหลดใหม่เมื่อผู้ใช้กลับมาเปิดแท็บ (เผื่อ event ข้ามหรือจองจากอีกแท็บ)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && isActive) loadBookings();
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('bookingCreated', handleBookingCreated);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isActive]);

  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

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

  const handleRefundClick = async (bookingId) => {
    const booking = bookings.find((b) => b._id === bookingId);
    if (!booking) return;
    if (isTripPastTransactionDeadline(booking.travel_slots, booking.plan)) {
      await Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถขอคืนเงินผ่านหน้านี้ได้ (ดูรายละเอียดการจองได้ตามปกติ)',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#2563eb',
      });
      return;
    }
    setRefundModal({
      bookingId,
      booking,
      eligibility: null,
      loading: true,
    });
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user?.id) headers['X-User-ID'] = user.id;
      const res = await fetch(
        `${API_BASE_URL}/api/booking/refund-eligibility?booking_id=${encodeURIComponent(bookingId)}`,
        { headers, credentials: 'include' }
      );
      const data = await res.json();
      const eligibility = data?.ok
        ? {
            refundable_items: data.refundable_items || [],
            total_refundable_amount: data.total_refundable_amount ?? 0,
            can_full_refund: data.can_full_refund,
            message: data.message || 'กำลังตรวจสอบเงื่อนไขการคืนเงิน',
          }
        : {
            refundable_items: [],
            total_refundable_amount: 0,
            can_full_refund: false,
            message: data.detail || 'ไม่สามารถโหลดข้อมูลได้',
          };

      setRefundModal((prev) => ({ ...prev, eligibility, loading: false }));

      const totalRefundable = eligibility.total_refundable_amount ?? 0;
      const currency = booking?.currency || 'THB';

      if (totalRefundable <= 0) {
        await Swal.fire({
          icon: 'info',
          title: 'ไม่สามารถคืนเงินได้',
          text: 'ไม่สามารถคืนเงินได้ตามเงื่อนไขของโรงแรมหรือสายการบิน',
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#2563eb',
        });
        setRefundModal(null);
        return;
      }

      const itemsList = (eligibility.refundable_items || [])
        .map(
          (item) =>
            `• ${item.label}: ${formatPriceInThb(item.amount, item.currency || currency)} — ${item.refundable ? '✅ คืนได้' : item.reason || '❌ คืนไม่ได้'}`
        )
        .join('\n');
      const conditionsHtml =
        (eligibility.message ? `<p style="text-align:left;margin-bottom:12px;">${eligibility.message}</p>` : '') +
        (itemsList ? `<pre style="text-align:left;white-space:pre-wrap;font-size:13px;background:#f3f4f6;padding:12px;border-radius:8px;margin:0 0 12px 0;">${itemsList}</pre>` : '') +
        `<p style="text-align:left;font-weight:700;margin:0;">ยอดที่คืนได้รวม: ${formatPriceInThb(totalRefundable, currency)}</p>`;

      await Swal.fire({
        icon: 'info',
        title: 'เงื่อนไขการคืนเงิน',
        html: conditionsHtml,
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#2563eb',
        width: 480,
      });
    } catch (err) {
      setRefundModal((prev) => ({
        ...prev,
        eligibility: { refundable_items: [], total_refundable_amount: 0, can_full_refund: false, message: err.message || 'เกิดข้อผิดพลาด' },
        loading: false,
      }));
      await Swal.fire({
        icon: 'warning',
        title: 'ไม่สามารถคืนเงินได้',
        text: 'ไม่สามารถคืนเงินได้ตามเงื่อนไขของโรงแรมหรือสายการบิน หรือเกิดข้อผิดพลาดในการตรวจสอบ',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#2563eb',
      });
      setRefundModal(null);
    }
  };

  const handleRefundConfirm = async (refundType = 'full') => {
    if (!refundModal?.bookingId) return;
    const bid = refundModal.bookingId;
    const rb = bookings.find((b) => b._id === bid);
    if (rb && isTripPastTransactionDeadline(rb.travel_slots, rb.plan)) {
      await Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถดำเนินการคืนเงินได้',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#2563eb',
      });
      return;
    }
    setProcessing((p) => ({ ...p, [bid]: 'refunding' }));
    try {
      const headers = { 'Content-Type': 'application/json' };
      if (user?.id) headers['X-User-ID'] = user.id;
      const body = { booking_id: bid, refund_type: refundType };
      if (refundType === 'partial') {
        const refundableTypes = (refundModal.eligibility?.refundable_items || [])
          .filter((i) => i.refundable)
          .map((i) => i.type);
        if (refundableTypes.length) body.items = refundableTypes;
      }
      const res = await fetch(`${API_BASE_URL}/api/booking/refund`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (data?.ok) {
        setRefundModal(null);
        await loadBookings();
        await Swal.fire({
          icon: 'success',
          title: 'คืนเงินสำเร็จ',
          text: data.message || 'ดำเนินการคืนเงินเรียบร้อยแล้ว',
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#2563eb',
        });
      } else {
        await Swal.fire({
          icon: 'error',
          title: 'คืนเงินไม่สำเร็จ',
          text: data.detail || data.message || 'เกิดข้อผิดพลาดในการคืนเงิน',
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#2563eb',
        });
      }
    } catch (err) {
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: err.message || 'เกิดข้อผิดพลาดในการคืนเงิน',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#2563eb',
      });
    } finally {
      setProcessing((p) => ({ ...p, [bid]: null }));
    }
  };

  const handleCancel = async (bookingId) => {
    const b = bookings.find((x) => x._id === bookingId);
    if (b && isTripPastTransactionDeadline(b.travel_slots, b.plan)) {
      await Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถยกเลิกการจองได้ (ดูรายละเอียดได้ตามปกติ)',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#6366f1',
      });
      return;
    }
    const result = await Swal.fire({
      title: t('bookings.confirmCancel') || 'คุณต้องการยกเลิกการจองนี้หรือไม่?',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: t('bookings.cancelBooking') || '❌ ยกเลิกการจอง',
      confirmButtonColor: '#d9534f',
      cancelButtonText: 'ไม่ ยกเลิก',
      cancelButtonColor: '#6c757d',
      reverseButtons: true,
    });
    if (!result.isConfirmed) return;

    setProcessing((p) => ({ ...p, [bookingId]: 'cancelling' }));
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
        await Swal.fire({
          icon: 'success',
          title: t('bookings.cancelSuccess') || 'ยกเลิกการจองสำเร็จ',
          text: data.message || null,
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#6366f1',
        });
        await loadBookings();
      } else {
        const errorMsg = data.detail
          ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
          : 'Unknown error';
        await Swal.fire({
          icon: 'error',
          title: 'เกิดข้อผิดพลาด',
          text: errorMsg,
          confirmButtonText: 'ตกลง',
          confirmButtonColor: '#6366f1',
        });
      }
    } catch (err) {
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: err.message || 'Unknown error',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#6366f1',
      });
    } finally {
      setProcessing((p) => ({ ...p, [bookingId]: null }));
    }
  };

  const handlePayment = async (bookingId) => {
    const booking = bookings.find(b => b._id === bookingId);
    if (!booking) {
      Swal.fire({ icon: 'warning', text: 'ไม่พบข้อมูลการจอง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (isTripPastTransactionDeadline(booking.travel_slots, booking.plan)) {
      await Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถชำระเงินได้',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#6366f1',
      });
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
          Swal.fire({ icon: 'success', text: data.message || 'ชำระเงินสำเร็จ', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
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
            onNavigateToPayment(urlBookingId, booking);
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
        Swal.fire({ icon: 'error', text: 'เกิดข้อผิดพลาด: ' + errorMsg, toast: true, position: 'top', showConfirmButton: false, timer: 3000 });
      }
    } catch (err) {
      const errorMessage = err.message || 'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ';
      Swal.fire({ icon: 'error', text: errorMessage, toast: true, position: 'top', showConfirmButton: false, timer: 3000 });
    } finally {
      setProcessing({ ...processing, [bookingId]: null });
    }
  };

    const handlePaymentMethodSelect = (method) => {
    if (!paymentModal) return;
    const pb = paymentModal.booking;
    if (pb && isTripPastTransactionDeadline(pb.travel_slots, pb.plan)) {
      Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถชำระเงินได้',
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#6366f1',
      });
      return;
    }
    
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
        Swal.fire({ icon: 'warning', text: 'ลิงก์ชำระเงินไม่พร้อมใช้งาน กรุณาลองใหม่อีกครั้ง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      }
    }
  };

  const handleEdit = (bookingId) => {
    const booking = bookings.find(b => b._id === bookingId);
    if (!booking) {
      Swal.fire({ icon: 'warning', text: 'ไม่พบข้อมูลการจอง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (isTripPastTransactionDeadline(booking.travel_slots, booking.plan)) {
      Swal.fire({
        icon: 'info',
        title: 'ทริปสิ้นสุดแล้ว',
        text: 'เลยวันเดินทางแล้ว — ไม่สามารถแก้ไขการจองได้ (ดูรายละเอียดได้ตามปกติ)',
        toast: true,
        position: 'top',
        showConfirmButton: false,
        timer: 3200,
      });
      return;
    }

    const tripId = booking.trip_id;
    const chatId = booking.chat_id;

    // ── กรณีที่ 1: booking จาก AI Chat (มี chat_id) → ไปหน้าแชทเพื่อแก้ไขผ่าน AI ──
    if (chatId && tripId) {
    const editContext = {
      bookingId: bookingId,
      tripId: tripId,
      chatId: chatId,
      booking: booking,
      action: 'edit_trip'
    };
    localStorage.setItem('edit_booking_context', JSON.stringify(editContext));
    
    if (onNavigateToAI) {
      onNavigateToAI(tripId, chatId, '');
    } else {
      window.location.href = `/chat?trip_id=${tripId}&chat_id=${chatId}&edit_booking=${bookingId}`;
    }
      return;
    }

    // ── กรณีที่ 2: booking จาก FlightsPage/HotelsPage/CarRentalsPage (ไม่มี chat_id) → เปิด Edit Modal ──
    const slots = booking.travel_slots || {};
    const plan = booking.plan || {};
    const flightOpt = plan?.travel?.flights?.outbound?.[0]?.selected_option || {};
    const source = tripId?.startsWith('flight-') ? 'flight'
          : tripId?.startsWith('hotel-')  ? 'hotel'
          : tripId?.startsWith('car-')    ? 'car'
          : 'direct';

    const accSeg = plan?.accommodation?.segments?.[0];
    const transportSeg = plan?.transport?.segments?.[0] || plan?.travel?.ground_transport?.[0];

    setEditFlightSearch({ loading: false, outbound: [], inboundResults: [], outboundError: null, inboundError: null, searched: false, activeTab: 'outbound', hasReturn: false, confirmedOutbound: false, confirmedInbound: false, collapsed: false });
    setEditHotelSearch({ loading: false, results: [], error: null });
    setEditCarSearch({ loading: false, results: [], error: null });
    setEditModal({
      bookingId: bookingId,
      booking: booking,
      source,
      selectedHotel: null,
      selectedTransfer: null,
      formData: {
        origin_city:        slots.origin_city        || '',
        destination_city:   slots.destination_city   || '',
        departure_date:     slots.departure_date      || '',
        return_date:        slots.return_date         || '',
        adults:             slots.adults              || 1,
        children:           slots.children            || 0,
        passengers:         slots.passengers          || 1,
        location:           slots.location            || slots.destination_city || '',
        check_in:           slots.check_in            || '',
        check_out:          slots.check_out           || '',
        guests:             slots.guests              || 1,
        total_price:        booking.total_price       || flightOpt.price_amount || accSeg?.selected_option?.price_amount || transportSeg?.selected_option?.price_amount || 0,
        currency:           booking.currency          || flightOpt.currency || accSeg?.selected_option?.currency || transportSeg?.selected_option?.currency || 'THB',
        notes:              booking.notes             || '',
      }
    });
  };

  const handleEditFlightSearch = async () => {
    if (!editModal) return;
    const fd = editModal.formData;
    if (!fd.origin_city?.trim() || !fd.destination_city?.trim()) {
      setEditFlightSearch(prev => ({ ...prev, loading: false, outboundError: 'กรุณากรอกต้นทางและปลายทางก่อนค้นหา', searched: true }));
      return;
    }
    if (!fd.departure_date) {
      setEditFlightSearch(prev => ({ ...prev, loading: false, outboundError: 'กรุณาเลือกวันเดินทางก่อนค้นหา', searched: true }));
      return;
    }

    const hasReturn = !!fd.return_date;
    setEditFlightSearch({
      loading: true,
      outbound: [], inboundResults: [],
      outboundError: null, inboundError: null,
      searched: false,
      activeTab: 'outbound',
    });

    const searchFlight = async (origin, destination, date) => {
      const params = new URLSearchParams({ origin, destination, departure_date: date });
      const res = await fetch(`${API_BASE_URL}/api/mcp/search/flights?${params.toString()}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' },
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) {
        const msg = typeof data.detail === 'string' ? data.detail : (data.detail?.[0]?.msg || 'ค้นหาไม่สำเร็จ');
        throw new Error(msg);
      }
      return data.flights || [];
    };

    // ค้นหาขาไปและขากลับพร้อมกัน
    const [outboundResult, inboundResult] = await Promise.allSettled([
      searchFlight(fd.origin_city.trim(), fd.destination_city.trim(), fd.departure_date),
      hasReturn
        ? searchFlight(fd.destination_city.trim(), fd.origin_city.trim(), fd.return_date)
        : Promise.resolve(null),
    ]);

    setEditFlightSearch({
      loading: false,
      outbound: outboundResult.status === 'fulfilled' ? (outboundResult.value || []) : [],
      inboundResults: inboundResult.status === 'fulfilled' ? (inboundResult.value || []) : [],
      outboundError: outboundResult.status === 'rejected' ? outboundResult.reason?.message : null,
      inboundError: inboundResult.status === 'rejected' ? inboundResult.reason?.message : null,
      searched: true,
      activeTab: 'outbound',
      hasReturn,
    });
  };

  const handleSelectEditFlight = (flight, leg) => {
    // leg: 'outbound' | 'inbound'
    if (!editModal) return;
    setEditModal(prev => {
      const updated = {
        ...prev,
        selectedOutbound: leg === 'outbound' ? flight : prev.selectedOutbound,
        selectedInbound: leg === 'inbound' ? flight : prev.selectedInbound,
      };
      // คำนวณราคารวม
      const outPrice = parseFloat(updated.selectedOutbound?.price?.total) || 0;
      const inPrice = parseFloat(updated.selectedInbound?.price?.total) || 0;
      const currency = flight.price?.currency || prev.formData.currency || 'THB';
      return {
        ...updated,
        formData: { ...prev.formData, total_price: outPrice + inPrice, currency },
      };
    });
  };

  const handleEditHotelSearch = async () => {
    if (!editModal || editModal.source !== 'hotel') return;
    const fd = editModal.formData;
    if (!fd.location?.trim()) {
      setEditHotelSearch(prev => ({ ...prev, error: 'กรุณากรอกสถานที่/เมือง', results: [] }));
      return;
    }
    if (!fd.check_in || !fd.check_out) {
      setEditHotelSearch(prev => ({ ...prev, error: 'กรุณาเลือกวันเช็คอินและเช็คเอาท์', results: [] }));
      return;
    }
    setEditHotelSearch({ loading: true, results: [], error: null });
    try {
      const params = new URLSearchParams({
        location: fd.location.trim(),
        check_in: fd.check_in,
        check_out: fd.check_out,
        guests: String(Math.max(1, parseInt(fd.guests) || 1)),
      });
      const res = await fetch(`${API_BASE_URL}/api/mcp/search/hotels?${params.toString()}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ค้นหาไม่สำเร็จ');
      const list = data.hotels || data.results || (Array.isArray(data) ? data : []);
      setEditHotelSearch({ loading: false, results: list, error: list.length === 0 ? 'ไม่พบที่พัก' : null });
    } catch (err) {
      setEditHotelSearch({ loading: false, results: [], error: err.message || 'เกิดข้อผิดพลาด' });
    }
  };

  const handleSelectEditHotel = (hotel) => {
    if (!editModal) return;
    const name = hotel.name || hotel.hotel?.name || hotel.display_name || 'ที่พัก';
    const priceObj = hotel.price || hotel.offers?.[0]?.price || {};
    const total = parseFloat(priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0) || 0;
    const currency = priceObj.currency || 'THB';
    setEditModal(prev => ({
      ...prev,
      selectedHotel: hotel,
      formData: { ...prev.formData, total_price: total, currency },
    }));
  };

  const handleEditCarSearch = async () => {
    if (!editModal || editModal.source !== 'car') return;
    const fd = editModal.formData;
    if (!fd.origin_city?.trim() || !fd.destination_city?.trim()) {
      setEditCarSearch(prev => ({ ...prev, error: 'กรุณากรอกจุดรับและจุดส่ง', results: [] }));
      return;
    }
    if (!fd.departure_date) {
      setEditCarSearch(prev => ({ ...prev, error: 'กรุณาเลือกวันที่', results: [] }));
      return;
    }
    setEditCarSearch({ loading: true, results: [], error: null });
    try {
      const params = new URLSearchParams({
        origin: fd.origin_city.trim(),
        destination: fd.destination_city.trim(),
        date: fd.departure_date,
        passengers: String(Math.max(1, parseInt(fd.passengers) || 1)),
      });
      const res = await fetch(`${API_BASE_URL}/api/mcp/search/transfers?${params.toString()}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
        credentials: 'include',
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || 'ค้นหาไม่สำเร็จ');
      const list = data.transfers || (Array.isArray(data) ? data : []);
      setEditCarSearch({ loading: false, results: list, error: list.length === 0 ? 'ไม่พบตัวเลือก' : null });
    } catch (err) {
      setEditCarSearch({ loading: false, results: [], error: err.message || 'เกิดข้อผิดพลาด' });
    }
  };

  const handleSelectEditCar = (tr) => {
    if (!editModal) return;
    const priceObj = tr.price || tr.total_price || {};
    const total = parseFloat(typeof priceObj === 'number' ? priceObj : (priceObj.total ?? priceObj.amount ?? priceObj ?? 0)) || 0;
    const currency = (priceObj && priceObj.currency) || 'THB';
    setEditModal(prev => ({
      ...prev,
      selectedTransfer: tr,
      formData: { ...prev.formData, total_price: total, currency },
    }));
  };

  const handleUpdateBooking = async () => {
    if (!editModal) return;

    const fd = editModal.formData;
    const source = editModal.source;

    if (source === 'flight') {
      if (!fd.origin_city?.trim() || !fd.destination_city?.trim()) {
        Swal.fire({ icon: 'warning', text: 'กรุณากรอกต้นทางและปลายทาง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
      if (!fd.departure_date) {
        Swal.fire({ icon: 'warning', text: 'กรุณาเลือกวันเดินทาง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
      if (fd.return_date && fd.return_date < fd.departure_date) {
        Swal.fire({ icon: 'warning', text: 'วันกลับต้องไม่ก่อนวันเดินทาง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
    } else if (source === 'hotel') {
      if (!fd.location?.trim()) {
        Swal.fire({ icon: 'warning', text: 'กรุณากรอกสถานที่/เมือง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
      if (!fd.check_in || !fd.check_out) {
        Swal.fire({ icon: 'warning', text: 'กรุณาเลือกวันเช็คอินและเช็คเอาท์', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
    } else if (source === 'car') {
      if (!fd.origin_city?.trim() || !fd.destination_city?.trim()) {
        Swal.fire({ icon: 'warning', text: 'กรุณากรอกจุดรับและจุดส่ง', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
      if (!fd.departure_date) {
        Swal.fire({ icon: 'warning', text: 'กรุณาเลือกวันที่', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
        return;
      }
    }

    setProcessing(prev => ({ ...prev, [editModal.bookingId]: 'updating' }));
    try {
      const userId = user?.user_id || user?.id;
      const headers = { 'Content-Type': 'application/json' };
      if (userId) headers['X-User-ID'] = userId;

      let updatePayload = {
        total_price: parseFloat(fd.total_price) || editModal.booking.total_price,
        ...(fd.notes ? { notes: fd.notes } : {}),
      };

      if (source === 'flight') {
        updatePayload.travel_slots = {
          origin_city:      fd.origin_city.trim(),
          destination_city: fd.destination_city.trim(),
          departure_date:   fd.departure_date,
          return_date:      fd.return_date || null,
          adults:           parseInt(fd.adults) || 1,
          children:         parseInt(fd.children) || 0,
        };
      } else if (source === 'hotel') {
        const hotel = editModal.selectedHotel;
        const existingPlan = editModal.booking.plan || {};
        const nights = (() => {
          if (!fd.check_in || !fd.check_out) return 1;
          const a = new Date(fd.check_in);
          const b = new Date(fd.check_out);
          return Math.max(1, Math.round((b - a) / 86400000));
        })();
        let segment;
        if (hotel) {
          const name = hotel.name || hotel.hotel?.name || hotel.display_name || 'ที่พัก';
          const priceObj = hotel.price || hotel.offers?.[0]?.price || {};
          const total = parseFloat(priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0) || 0;
          const currency = priceObj.currency || 'THB';
          segment = {
            selected_option: {
              raw_data: hotel,
              price_amount: total,
              currency,
              hotel_name: name,
            },
          };
        } else {
          const acc = existingPlan.accommodation?.segments?.[0];
          segment = acc || { selected_option: { price_amount: fd.total_price, currency: fd.currency || 'THB', hotel_name: 'ที่พัก' } };
        }
        updatePayload.plan = { ...existingPlan, accommodation: { segments: [segment] } };
        updatePayload.travel_slots = {
          ...(editModal.booking.travel_slots || {}),
          destination_city: fd.location?.trim(),
          location: fd.location?.trim(),
          check_in: fd.check_in,
          check_out: fd.check_out,
          guests: parseInt(fd.guests) || 1,
          nights,
          accommodations: [segment],
          source: 'hotel_search',
        };
      } else if (source === 'car') {
        const tr = editModal.selectedTransfer;
        const existingPlan = editModal.booking.plan || {};
        let segment;
        if (tr) {
          const name = tr.name || tr.transfer_type || tr.vehicle?.name || 'รถ';
          const priceObj = tr.price || tr.total_price || {};
          const total = parseFloat(typeof priceObj === 'number' ? priceObj : (priceObj.total ?? priceObj.amount ?? priceObj ?? 0)) || 0;
          const currency = (priceObj && priceObj.currency) || 'THB';
          segment = {
            selected_option: {
              raw_data: tr,
              price_amount: total,
              currency,
              display_name: name,
              route: `${fd.origin_city} → ${fd.destination_city}`,
            },
            requirements: {
              origin: fd.origin_city,
              destination: fd.destination_city,
              date: fd.departure_date,
              passengers: parseInt(fd.passengers) || 1,
            },
          };
        } else {
          const transportSeg = existingPlan.transport?.segments?.[0] || existingPlan.travel?.ground_transport?.[0];
          segment = transportSeg || {
            selected_option: { price_amount: fd.total_price, currency: fd.currency || 'THB', display_name: 'รถ' },
            requirements: { origin: fd.origin_city, destination: fd.destination_city, date: fd.departure_date, passengers: parseInt(fd.passengers) || 1 },
          };
        }
        updatePayload.plan = { ...existingPlan, transport: { segments: [segment] } };
        updatePayload.travel_slots = {
          ...(editModal.booking.travel_slots || {}),
          origin_city: fd.origin_city.trim(),
          destination_city: fd.destination_city.trim(),
          departure_date: fd.departure_date,
          ground_transport: [segment],
          transport: {
            type: 'transfer',
            route: `${fd.origin_city} → ${fd.destination_city}`,
            price_amount: parseFloat(fd.total_price) || 0,
            currency: fd.currency || 'THB',
          },
          source: 'car_search',
          passengers: parseInt(fd.passengers) || 1,
        };
      } else {
        updatePayload.travel_slots = {
          origin_city:      fd.origin_city?.trim(),
          destination_city: fd.destination_city?.trim(),
          departure_date:   fd.departure_date,
          return_date:      fd.return_date || null,
          adults:           parseInt(fd.adults) || 1,
          children:         parseInt(fd.children) || 0,
        };
      }

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
        setEditModal(null);
        await loadBookings();
      } else {
        throw new Error(data.detail || 'Unknown error');
      }
    } catch (err) {
      Swal.fire({ icon: 'error', text: 'เกิดข้อผิดพลาด: ' + (err.message || 'Unknown error'), toast: true, position: 'top', showConfirmButton: false, timer: 3000 });
    } finally {
      setProcessing(prev => ({ ...prev, [editModal.bookingId]: null }));
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab !== 'bookings' && onBack) {
      onBack();
    }
  };

  // ✅ แต่ละทริป (trip_id) แสดงเฉพาะการจองที่ยังไม่ยกเลิก 1 อัน — หลังแก้ไขทริปจะไม่โผล่ 2 การ์ด
  const displayBookings = (() => {
    const byTrip = {};
    (bookings || []).forEach((b) => {
      const tid = b.trip_id || b._id;
      if (!byTrip[tid]) byTrip[tid] = [];
      byTrip[tid].push(b);
    });
    return Object.values(byTrip).map((arr) => {
      const active = arr.filter((b) => (b.status || '').toLowerCase() !== 'cancelled');
      const list = active.length ? active : arr;
      list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
      return list[0];
    });
  })();

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
      <div className="my-bookings-content" data-theme={theme} data-font-size={fontSize}>

        {loading ? (
          <div className="my-bookings-loading">{t('bookings.loading')}</div>
        ) : error ? (
          <div className="my-bookings-error">❌ {error}</div>
        ) : displayBookings.length === 0 ? (
          <div className="my-bookings-empty">
            <div className="empty-icon">📭</div>
            <div className="empty-text">{t('bookings.noBookings')}</div>
            <div className="empty-subtext">{t('bookings.noBookingsDesc')}</div>
          </div>
        ) : (
          <div className="bookings-list">
          {displayBookings.map((booking) => {
            const plan = booking.plan || {};
            const travelSlots = booking.travel_slots || {};
            const tripPastDeadline = isTripPastTransactionDeadline(travelSlots, plan);
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
            const carSegments = travelSlots.cars || plan?.transport?.car_rental?.segments || [];

            // ✅ ตรวจสอบว่ามาจาก FlightSearch (trip_id ขึ้นต้นด้วย "flight-" หรือ source = 'flight_search')
            const isFromFlightSearch = (booking.trip_id || '').startsWith('flight-') || travelSlots.source === 'flight_search';

            // ✅ ตรวจสอบว่าเป็นรถเช่า (จาก CarRentalsPage หรือ AI car rental)
            const isCarRental =
              (booking.trip_id || '').startsWith('car-') ||
              travelSlots.source === 'car_rental_search' ||
              (carSegments && carSegments.length > 0) ||
              plan?.transport?.type === 'car_rental';

            // ✅ airline code สำหรับแสดง logo (จาก travel_slots หรือ plan)
            const airlineCode = travelSlots.airline_code
              || plan?.travel?.flights?.outbound?.[0]?.selected_option?.raw_data?.itineraries?.[0]?.segments?.[0]?.carrierCode
              || '';

            // ✅ รุ่นรถสำหรับรถเช่า (ใช้แสดงต่อจากเส้นทาง เช่น HKT → HKT · Toyota Yaris 1.2)
            let carModel = '';
            if (isCarRental) {
              const seg = Array.isArray(carSegments) && carSegments.length > 0 ? carSegments[0] : null;
              const so = seg?.selected_option || {};
              const raw = so.raw_data || {};
              carModel =
                raw.car_model ||
                raw.name ||
                raw.model ||
                so.car_model ||
                so.display_name ||
                plan?.transport?.name ||
                '';
            }

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
            
            // ✅ Fallback: ดึง outboundFlight จาก plan.travel.flights เมื่อ travel_slots.flights ว่าง
            if (!outboundFlight && plan?.travel?.flights?.outbound?.length > 0) {
              const planOutbound = plan.travel.flights.outbound[0];
              const planSel = planOutbound?.selected_option || {};
              const planRaw = planSel?.raw_data || {};
              const planItineraries = planRaw?.itineraries || [];
              if (planItineraries.length > 0) {
                const outSegs = planItineraries[0]?.segments || [];
                if (outSegs.length > 0) {
                  const fSeg = outSegs[0];
                  const lSeg = outSegs[outSegs.length - 1];
                  outboundFlight = {
                    from: fSeg?.departure?.iataCode || travelSlots.departure_iata || travelSlots.origin_city || '',
                    to: lSeg?.arrival?.iataCode || travelSlots.arrival_iata || travelSlots.destination_city || '',
                    airline: fSeg?.carrierCode || '',
                    flightNumber: `${fSeg?.carrierCode || ''}${fSeg?.number || ''}`,
                    departureTime: fSeg?.departure?.at || '',
                    arrivalTime: lSeg?.arrival?.at || '',
                    price: planSel?.price_amount || planSel?.price_total || 0,
                    currency: planSel?.currency || 'THB'
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

            // ✅ ดึงข้อมูลรถเช่า/การเดินทาง จาก travel_slots.transport หรือ ground_transport
            let transportInfo = null;
            const slotTransport = travelSlots.transport;
            if (slotTransport && (slotTransport.price != null || slotTransport.price_amount != null || slotTransport.route || slotTransport.type)) {
              transportInfo = {
                type: slotTransport.type || slotTransport.category || 'transfer',
                route: slotTransport.route || '',
                price: slotTransport.price ?? slotTransport.price_amount ?? 0,
                currency: slotTransport.currency || 'THB',
                duration: slotTransport.duration,
                vehicle_type: slotTransport.vehicle_type || slotTransport.car_type,
                provider: slotTransport.provider || slotTransport.company
              };
            } else if (groundTransport.length > 0) {
              const firstTransport = groundTransport[0];
              const selectedOption = firstTransport?.selected_option || {};
              const req = firstTransport?.requirements || {};
              const origin = req?.origin ?? req?.from ?? '';
              const dest = req?.destination ?? req?.to ?? '';
              transportInfo = {
                type: selectedOption?.category || firstTransport?.category || 'transfer',
                route: (origin && dest) ? `${origin} → ${dest}` : (selectedOption?.display_name || selectedOption?.route || ''),
                price: selectedOption?.price_amount ?? selectedOption?.price_total ?? 0,
                currency: selectedOption?.currency || 'THB',
                duration: selectedOption?.duration,
                vehicle_type: selectedOption?.vehicle_type || selectedOption?.car_type,
                provider: selectedOption?.provider || selectedOption?.company
              };
            }
            // Fallback: จาก plan.transport / plan.travel.ground_transport
            if (!transportInfo && (plan?.transport?.price != null || plan?.transport?.price_amount != null || (plan?.travel?.ground_transport?.length > 0))) {
              const pt = plan.transport || {};
              const gt = plan.travel?.ground_transport || [];
              if (pt.route || pt.type || pt.price != null || pt.price_amount != null) {
                transportInfo = {
                  type: pt.type || pt.category || 'transfer',
                  route: pt.route || '',
                  price: pt.price ?? pt.price_amount ?? 0,
                  currency: pt.currency || 'THB',
                  duration: pt.duration
                };
              } else if (gt.length > 0 && gt[0]?.selected_option) {
                const so = gt[0].selected_option;
                const r = gt[0].requirements || {};
                transportInfo = {
                  type: so?.category || 'transfer',
                  route: [r?.origin || r?.from, r?.destination || r?.to].filter(Boolean).join(' → ') || so?.display_name || '',
                  price: so?.price_amount ?? so?.price_total ?? 0,
                  currency: so?.currency || 'THB',
                  duration: so?.duration
                };
              }
            }

            // ✅ ที่พักอย่างเดียว = มีที่พัก แต่ไม่มีเที่ยวบิน
            const isAccommodationOnly = hotelInfo && !outboundFlight && !inboundFlight;

            // ✅ ราคารวมที่แสดง: แปลงทุกส่วนเป็น THB (เที่ยวบิน + ที่พัก + รถเช่า/การเดินทาง)
            const outPrice = Number(outboundFlight?.price) || 0;
            const inPrice = Number(inboundFlight?.price) || 0;
            const hotelPriceNum = Number(hotelInfo?.price) || 0;
            const transportPriceNum = Number(transportInfo?.price) || 0;
            const outThb = toThb(outPrice, outboundFlight?.currency || 'THB') ?? 0;
            const inThb = toThb(inPrice, inboundFlight?.currency || 'THB') ?? 0;
            const hotelThb = toThb(hotelPriceNum, hotelInfo?.currency || 'THB') ?? 0;
            const transportThb = toThb(transportPriceNum, transportInfo?.currency || 'THB') ?? 0;
            const hasComponentPrices = outPrice > 0 || inPrice > 0 || hotelPriceNum > 0 || transportPriceNum > 0;
            const summedTotalThb = outThb + inThb + hotelThb + transportThb;
            const displayTotalPrice = hasComponentPrices && summedTotalThb > 0 ? summedTotalThb : (booking.total_price || 0);
            const displayCurrency = 'THB';
            
            return (
              <div key={booking._id} className="booking-card">
                <div className="booking-header">
                  <div className="booking-title">
                    {/* ✅ Airline logo เมื่อมาจาก FlightSearch */}
                    {isFromFlightSearch && airlineCode && (
                      <span className="airline-logo-badge" title={`สายการบิน ${airlineCode}`}>
                        <img
                          src={`https://content.airhex.com/content/logos/thumbnails_200_65_${airlineCode}_r.png`}
                          alt={airlineCode}
                          className="airline-logo-img"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'inline-flex';
                          }}
                        />
                        <span className="airline-logo-fallback" style={{ display: 'none' }}>
                          ✈️ {airlineCode}
                        </span>
                      </span>
                    )}
                    <span>
                      {isAccommodationOnly && hotelInfo?.name
                        ? `🏨 ${hotelInfo.name}`
                        : origin && dest
                          ? `${origin} → ${dest}${isCarRental && carModel ? ` · ${carModel}` : ''}`
                          : 'ทริป'}
                    </span>
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
                      {statusBadge.textKey ? t(statusBadge.textKey) : statusBadge.text}
                    </span>
                  </div>
                  <div className="booking-date">
                    {booking.amadeus_booking_reference || booking.booking_reference || formatThaiDate(booking.created_at)}
                  </div>
                </div>

                {tripPastDeadline && (
                  <div
                    className="trip-readonly-banner"
                    style={{
                      margin: '0 0 12px',
                      padding: '10px 14px',
                      background: 'rgba(245, 158, 11, 0.15)',
                      border: '1px solid rgba(245, 158, 11, 0.45)',
                      borderRadius: 10,
                      fontSize: 13,
                      color: 'var(--text-primary, #1f2937)',
                      lineHeight: 1.45,
                    }}
                  >
                    <strong>🔒 โหมดดูอย่างเดียว</strong> — ทริปนี้เลยวันเดินทางแล้ว ไม่สามารถชำระเงิน แก้ไข ยกเลิก หรือคืนเงินได้
                  </div>
                )}

                <div className="booking-details">
                  <div className="booking-detail-row">
                    <span className="detail-label">{isAccommodationOnly ? 'เช็คอิน:' : 'วันเดินทาง:'}</span>
                    <span className="detail-value">{formatThaiDate(dateGo)}</span>
                  </div>
                  {dateReturn && (
                    <div className="booking-detail-row">
                      <span className="detail-label">{isAccommodationOnly ? 'เช็คเอาท์:' : 'วันกลับ:'}</span>
                      <span className="detail-value">{formatThaiDate(dateReturn)}</span>
                    </div>
                  )}
                  {nights && (
                    <div className="booking-detail-row">
                      <span className="detail-label">{isCarRental ? 'จำนวนวันที่เช่า:' : 'จำนวนคืน:'}</span>
                      <span className="detail-value">{nights} {isCarRental ? 'วัน' : 'คืน'}</span>
                    </div>
                  )}
                  <div className="booking-detail-row">
                    <span className="detail-label">{isAccommodationOnly ? 'จำนวนผู้เข้าพัก:' : 'ผู้โดยสาร:'}</span>
                    <span className="detail-value">
                      {adults} ผู้ใหญ่{children > 0 ? `, ${children} เด็ก` : ''}
                    </span>
                  </div>
                  {/* ✅ รายชื่อผู้โดยสาร */}
                  {(() => {
                    const passengers = booking.passengers || [];
                    if (passengers.length === 0) return null;

                    // ชื่อไทยจาก user profile (ถ้ากรอกไว้)
                    const userThaiName = user
                      ? `${user.first_name_th || ''} ${user.last_name_th || ''}`.trim()
                      : '';
                    // ชื่ออังกฤษจาก user profile
                    const userEnName = user
                      ? `${user.first_name || ''} ${user.last_name || ''}`.trim()
                      : '';

                    return (
                      <div className="booking-passengers">
                        <div className="passengers-label">👤 {isAccommodationOnly ? 'รายชื่อผู้เข้าพัก' : 'รายชื่อผู้โดยสาร'}</div>
                        <div className="passengers-list">
                          {passengers.map((pax, idx) => {
                            let displayName = pax.name_th || pax.name || '';
                            if (pax.is_main_booker) {
                              // ลำดับ: ชื่อไทยจาก profile → ชื่อไทยใน pax → ชื่ออังกฤษจาก profile → ชื่อใน pax
                              displayName = userThaiName || pax.name_th || userEnName || pax.name || '';
                            }
                            return (
                              <div key={idx} className="passenger-item">
                                <span className={`passenger-type-badge ${pax.type === 'child' ? 'child' : 'adult'}`}>
                                  {pax.type === 'child' ? '👶 เด็ก' : '👤 ผู้ใหญ่'}
                                </span>
                                <span className="passenger-name">
                                  {displayName}
                                  {pax.is_main_booker && <span className="main-booker-tag"> (ผู้จอง)</span>}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })()}
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
                  
                  {/* ✅ แสดงราคารวมทั้งหมด (เด่นชัด) — ใช้ผลรวมขาไป+ขากลับ+ที่พักเมื่อมี เพื่อให้ตรงกับรายการด้านล่าง */}
                  {displayTotalPrice > 0 && (
                    <div className="booking-total-price">
                      <div className="total-price-label">💰 ราคารวมทั้งหมด</div>
                      <div className="total-price-value">
                        {formatPriceInThb(displayTotalPrice, displayCurrency)}
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
                            ขาไป: {formatPriceInThb(outboundFlight.price, outboundFlight.currency)}
                          </span>
                        )}
                        {outboundFlight?.price > 0 && inboundFlight?.price > 0 && <span> • </span>}
                        {inboundFlight?.price > 0 && (
                          <span>
                            ขากลับ: {formatPriceInThb(inboundFlight.price, inboundFlight.currency)}
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
                        {formatPriceInThb(hotelInfo.price, hotelInfo.currency)}
                      </div>
                    )}
                  </div>
                )}

                {/* ✅ แสดงข้อมูลรถเช่า/การเดินทาง จาก travel_slots */}
                {transportInfo && (
                  <div className="booking-transport-info" style={{ marginTop: '12px' }}>
                    <div className="hotel-label">🚗 {transportInfo.type === 'car_rental' || transportInfo.vehicle_type ? 'รถเช่า' : 'การเดินทาง'}</div>
                    {transportInfo.route && (
                      <div style={{ fontSize: '14px', fontWeight: 600, marginBottom: '4px' }}>{transportInfo.route}</div>
                    )}
                    {(transportInfo.vehicle_type || transportInfo.provider) && (
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        {[transportInfo.vehicle_type, transportInfo.provider].filter(Boolean).join(' • ')}
                      </div>
                    )}
                    {transportInfo.duration && (
                      <div style={{ fontSize: '13px', color: '#6b7280', marginTop: '4px' }}>
                        ⏱️ {transportInfo.duration}
                      </div>
                    )}
                    {(transportInfo.price > 0 || transportInfo.price != null) && (
                      <div style={{ fontSize: '13px', color: '#2563eb', marginTop: '4px', fontWeight: 600 }}>
                        {formatPriceInThb(transportInfo.price, transportInfo.currency)}
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
                        ราคาไฟท์บิน: {formatPriceInThb(plan.flight.price_total, plan.flight.currency || booking.currency || 'THB')}
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
                        disabled={tripPastDeadline || processing[booking._id] === 'paying'}
                      >
                        {processing[booking._id] === 'paying' ? t('bookings.processing') : t('bookings.pay')}
                      </button>
                      <button
                        className="btn-edit"
                        onClick={() => handleEdit(booking._id)}
                        disabled={tripPastDeadline || processing[booking._id] === 'updating'}
                      >
                        {processing[booking._id] === 'updating' ? t('bookings.processing') : t('bookings.edit')}
                      </button>
                      <button
                        className="btn-cancel"
                        onClick={() => handleCancel(booking._id)}
                        disabled={tripPastDeadline || processing[booking._id] === 'cancelling'}
                      >
                        {processing[booking._id] === 'cancelling' ? t('bookings.processing') : t('bookings.cancelBooking')}
                      </button>
                    </>
                  )}
                  {booking.status === 'confirmed' && (
                    <button
                      className="btn-cancel"
                      onClick={() => handleCancel(booking._id)}
                      disabled={tripPastDeadline || processing[booking._id] === 'cancelling'}
                    >
                      {processing[booking._id] === 'cancelling' ? t('bookings.processing') : t('bookings.cancelBooking')}
                    </button>
                  )}
                  {booking.status === 'paid' && (
                    <button
                      className="btn-refund"
                      onClick={() => handleRefundClick(booking._id)}
                      disabled={tripPastDeadline || processing[booking._id] === 'refunding'}
                    >
                      {processing[booking._id] === 'refunding' ? t('bookings.processing') : t('bookings.refund')}
                    </button>
                  )}
                  {booking.status === 'cancelled' && (
                    <div className="booking-cancelled-note">
                      {t('bookings.cancelled')}
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
          <div className="payment-modal edit-booking-modal" onClick={(e) => e.stopPropagation()}>
            <div className="payment-modal-header">
              <h2>
                {editModal.source === 'flight' ? '✈️' : editModal.source === 'hotel' ? '🏨' : editModal.source === 'car' ? '🚗' : '✏️'}
                {' '}แก้ไขการจอง
              </h2>
              <button className="payment-modal-close" onClick={() => setEditModal(null)}>✕</button>
            </div>
            
            <div className="payment-modal-body">
              <div className="edit-form">
                {/* ── ฟอร์มเที่ยวบิน ── */}
                {editModal.source === 'flight' && (
                  <>
                <div className="edit-form-row">
                <div className="form-group">
                    <label className="form-label">📍 ต้นทาง <span className="required">*</span></label>
                  <input
                    type="text"
                    className="form-input"
                    value={editModal.formData.origin_city}
                      onChange={(e) => { setEditModal({ ...editModal, formData: { ...editModal.formData, origin_city: e.target.value }, selectedOutbound: null, selectedInbound: null }); setEditFlightSearch({ loading: false, outbound: [], inboundResults: [], outboundError: null, inboundError: null, searched: false, activeTab: 'outbound', hasReturn: false, confirmedOutbound: false, confirmedInbound: false, collapsed: false }); }}
                      placeholder="เช่น กรุงเทพ (BKK)"
                  />
                </div>
                <div className="form-group">
                    <label className="form-label">🏁 ปลายทาง <span className="required">*</span></label>
                  <input
                    type="text"
                    className="form-input"
                    value={editModal.formData.destination_city}
                      onChange={(e) => { setEditModal({ ...editModal, formData: { ...editModal.formData, destination_city: e.target.value }, selectedOutbound: null, selectedInbound: null }); setEditFlightSearch({ loading: false, outbound: [], inboundResults: [], outboundError: null, inboundError: null, searched: false, activeTab: 'outbound', hasReturn: false, confirmedOutbound: false, confirmedInbound: false, collapsed: false }); }}
                      placeholder="เช่น ภูเก็ต (HKT)"
                    />
                  </div>
                </div>
                <div className="edit-form-row">
                <div className="form-group">
                    <label className="form-label">📅 วันเดินทาง <span className="required">*</span></label>
                  <input
                    type="date"
                    className="form-input"
                    value={editModal.formData.departure_date}
                      onChange={(e) => { setEditModal({ ...editModal, formData: { ...editModal.formData, departure_date: e.target.value }, selectedOutbound: null, selectedInbound: null }); setEditFlightSearch({ loading: false, outbound: [], inboundResults: [], outboundError: null, inboundError: null, searched: false, activeTab: 'outbound', hasReturn: false, confirmedOutbound: false, confirmedInbound: false, collapsed: false }); }}
                  />
                </div>
                <div className="form-group">
                    <label className="form-label">📅 วันกลับ <span style={{ color: '#9ca3af', fontSize: '0.75rem' }}>(ถ้ามี)</span></label>
                  <input
                    type="date"
                    className="form-input"
                    value={editModal.formData.return_date}
                      min={editModal.formData.departure_date}
                      onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, return_date: e.target.value } })}
                    />
                  </div>
                </div>
                <div className="edit-form-row">
                <div className="form-group">
                    <label className="form-label">👤 ผู้ใหญ่</label>
                  <input
                    type="number"
                    className="form-input"
                      value={editModal.formData.adults}
                      min="1" max="9"
                      onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, adults: e.target.value } })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="form-label">👶 เด็ก</label>
                    <input
                      type="number"
                      className="form-input"
                      value={editModal.formData.children}
                      min="0" max="9"
                      onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, children: e.target.value } })}
                    />
                  </div>
                </div>
                <div className="edit-flight-search-section">
                  <div className="edit-flight-search-header">
                    <span className="edit-flight-search-label">
                      ✈️ ตรวจสอบเที่ยวบินที่รองรับ
                      {editModal.formData.return_date && <span className="efi-roundtrip-badge">ไป-กลับ</span>}
                    </span>
                    <button
                      type="button"
                      className="btn-search-flights"
                      onClick={handleEditFlightSearch}
                      disabled={editFlightSearch.loading}
                    >
                      {editFlightSearch.loading ? '🔍 กำลังค้นหา...' : '🔍 ค้นหาเที่ยวบิน'}
                    </button>
                  </div>

                  {editFlightSearch.searched && !editFlightSearch.loading && (() => {
                    const hasReturn = editFlightSearch.hasReturn;
                    const collapsed = editFlightSearch.collapsed;

                    // helper: แปลง flight → summary 1 บรรทัด
                    const flightSummary = (f) => {
                      if (!f) return null;
                      const seg = f.itineraries?.[0]?.segments?.[0];
                      const dep = seg?.departure?.at ? new Date(seg.departure.at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false }) : '--:--';
                      const arr = seg?.arrival?.at ? new Date(seg.arrival.at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false }) : '--:--';
                      return `${seg?.carrierCode} ${seg?.number}  ${dep}→${arr}  ${seg?.departure?.iataCode}→${seg?.arrival?.iataCode}  ${formatPriceInThb(parseFloat(f.price?.total || 0), f.price?.currency)}`;
                    };

                    // ── Collapsed view (หลังยืนยัน) ──────────────────────────
                    if (collapsed) {
                      return (
                        <div className="efi-confirmed-summary">
                          <div className="efi-confirmed-rows">
                            {editModal.selectedOutbound && (
                              <div className="efi-confirmed-row">
                                <span className="efi-confirmed-leg">✈️ ขาไป</span>
                                <span className="efi-confirmed-detail">{flightSummary(editModal.selectedOutbound)}</span>
                              </div>
                            )}
                            {editModal.selectedInbound && (
                              <div className="efi-confirmed-row">
                                <span className="efi-confirmed-leg">🔄 ขากลับ</span>
                                <span className="efi-confirmed-detail">{flightSummary(editModal.selectedInbound)}</span>
                              </div>
                            )}
                          </div>
                          <button type="button" className="btn-change-flight"
                            onClick={() => setEditFlightSearch(prev => ({ ...prev, collapsed: false, confirmedOutbound: false, confirmedInbound: false }))}
                          >
                            เปลี่ยน
                          </button>
                        </div>
                      );
                    }

                    // ── Expanded view (กำลังเลือก) ────────────────────────────
                    const renderFlightList = (flights, error, leg) => {
                      if (error) return <div className="edit-flight-error">❌ {error}</div>;
                      if (leg === 'inbound' && flights === null) return null;
                      if (!flights || flights.length === 0)
                        return <div className="edit-flight-no-result">⚠️ ไม่พบเที่ยวบินสำหรับเส้นทางและวันที่นี้</div>;
                      const selectedFlight = leg === 'outbound' ? editModal.selectedOutbound : editModal.selectedInbound;
                      const isConfirmed = leg === 'outbound' ? editFlightSearch.confirmedOutbound : editFlightSearch.confirmedInbound;
                      return (
                        <div className="edit-flight-results">
                          <div className="edit-flight-results-title">พบ {flights.length} เที่ยวบิน — เลือกเพื่ออัปเดตราคา</div>
                          <div className="edit-flight-list">
                            {flights.slice(0, 5).map((f, idx) => {
                              const seg = f.itineraries?.[0]?.segments?.[0];
                              const depTime = seg?.departure?.at ? new Date(seg.departure.at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false }) : '--:--';
                              const arrTime = seg?.arrival?.at ? new Date(seg.arrival.at).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false }) : '--:--';
                              const price = parseFloat(f.price?.total) || 0;
                              const fCurrency = f.price?.currency || 'THB';
                              const isSelected = selectedFlight === f;
                              return (
                                <button key={idx} type="button"
                                  className={`edit-flight-item${isSelected ? ' selected' : ''}`}
                                  onClick={() => handleSelectEditFlight(f, leg)}
                                >
                                  <span className="efi-code">{seg?.carrierCode} {seg?.number}</span>
                                  <span className="efi-time">{depTime} → {arrTime}</span>
                                  <span className="efi-route">{seg?.departure?.iataCode} → {seg?.arrival?.iataCode}</span>
                                  <span className="efi-price">{formatPriceInThb(price, fCurrency)}</span>
                                  {isSelected && <span className="efi-check">✓</span>}
                                </button>
                              );
                            })}
                          </div>
                          {/* ปุ่มตกลง — แสดงเมื่อเลือกแล้ว */}
                          {selectedFlight && !isConfirmed && (
                            <button type="button" className="btn-confirm-flight"
                              onClick={() => {
                                const newConfirmedOut = leg === 'outbound' ? true : editFlightSearch.confirmedOutbound;
                                const newConfirmedIn  = leg === 'inbound'  ? true : editFlightSearch.confirmedInbound;
                                // collapse ถ้า: ขาเดียว หรือ ไป-กลับแต่ทั้งสองขายืนยันแล้ว หรือขากลับไม่มีผล
                                const shouldCollapse = !hasReturn || (newConfirmedOut && (newConfirmedIn || !editFlightSearch.inboundResults?.length));
                                setEditFlightSearch(prev => ({
                                  ...prev,
                                  confirmedOutbound: newConfirmedOut,
                                  confirmedInbound: newConfirmedIn,
                                  collapsed: shouldCollapse,
                                  // ถ้ายังไม่ collapse และเป็นขาไป ให้สลับไปแท็บขากลับอัตโนมัติ
                                  activeTab: (!shouldCollapse && leg === 'outbound') ? 'inbound' : prev.activeTab,
                                }));
                              }}
                            >
                              ✅ ตกลง ยืนยันเที่ยวบินนี้
                            </button>
                          )}
                        </div>
                      );
                    };

                    if (!hasReturn) {
                      return renderFlightList(editFlightSearch.outbound, editFlightSearch.outboundError, 'outbound');
                    }

                    // ไป-กลับ: แสดง tab
                    return (
                      <div>
                        <div className="efi-tab-bar">
                          <button type="button"
                            className={`efi-tab${editFlightSearch.activeTab === 'outbound' ? ' active' : ''}`}
                            onClick={() => setEditFlightSearch(prev => ({ ...prev, activeTab: 'outbound' }))}
                          >
                            ✈️ ขาไป
                            {editFlightSearch.confirmedOutbound && <span className="efi-tab-check"> ✓</span>}
                          </button>
                          <button type="button"
                            className={`efi-tab${editFlightSearch.activeTab === 'inbound' ? ' active' : ''}`}
                            onClick={() => setEditFlightSearch(prev => ({ ...prev, activeTab: 'inbound' }))}
                          >
                            🔄 ขากลับ
                            {editFlightSearch.confirmedInbound && <span className="efi-tab-check"> ✓</span>}
                          </button>
                        </div>
                        {editFlightSearch.activeTab === 'outbound'
                          ? renderFlightList(editFlightSearch.outbound, editFlightSearch.outboundError, 'outbound')
                          : renderFlightList(editFlightSearch.inboundResults, editFlightSearch.inboundError, 'inbound')
                        }
                        {(editModal.selectedOutbound || editModal.selectedInbound) && (
                          <div className="efi-price-summary">
                            {editModal.selectedOutbound && (
                              <span>ขาไป {formatPriceInThb(parseFloat(editModal.selectedOutbound.price?.total || 0), editModal.selectedOutbound.price?.currency)}</span>
                            )}
                            {editModal.selectedOutbound && editModal.selectedInbound && <span className="efi-plus">+</span>}
                            {editModal.selectedInbound && (
                              <span>ขากลับ {formatPriceInThb(parseFloat(editModal.selectedInbound.price?.total || 0), editModal.selectedInbound.price?.currency)}</span>
                            )}
                            <span className="efi-total">
                              รวม {formatPriceInThb(
                                (parseFloat(editModal.selectedOutbound?.price?.total) || 0) + (parseFloat(editModal.selectedInbound?.price?.total) || 0),
                                editModal.selectedOutbound?.price?.currency || editModal.selectedInbound?.price?.currency
                              )}
                            </span>
                          </div>
                        )}
                      </div>
                    );
                  })()}
                </div>
                  </>
                )}

                {/* ── ฟอร์มที่พัก ── */}
                {editModal.source === 'hotel' && (
                  <>
                    <div className="edit-form-row">
                      <div className="form-group">
                        <label className="form-label">📍 สถานที่ / เมือง <span className="required">*</span></label>
                        <input
                          type="text"
                          className="form-input"
                          value={editModal.formData.location}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, location: e.target.value }, selectedHotel: null })}
                          placeholder="เช่น กรุงเทพมหานคร"
                        />
                      </div>
                    </div>
                    <div className="edit-form-row">
                      <div className="form-group">
                        <label className="form-label">📅 เช็คอิน <span className="required">*</span></label>
                        <input
                          type="date"
                          className="form-input"
                          value={editModal.formData.check_in}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, check_in: e.target.value }, selectedHotel: null })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">📅 เช็คเอาท์ <span className="required">*</span></label>
                        <input
                          type="date"
                          className="form-input"
                          value={editModal.formData.check_out}
                          min={editModal.formData.check_in}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, check_out: e.target.value }, selectedHotel: null })}
                        />
                      </div>
                    </div>
                    <div className="edit-form-row">
                      <div className="form-group">
                        <label className="form-label">👤 จำนวนผู้เข้าพัก</label>
                        <input
                          type="number"
                          className="form-input"
                          value={editModal.formData.guests}
                          min="1"
                          max="9"
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, guests: e.target.value }, selectedHotel: null })}
                        />
                      </div>
                    </div>
                    <div className="edit-flight-search-section">
                      <div className="edit-flight-search-header">
                        <span className="edit-flight-search-label">🏨 ค้นหาที่พักใหม่</span>
                        <button type="button" className="btn-search-flights" onClick={handleEditHotelSearch} disabled={editHotelSearch.loading}>
                          {editHotelSearch.loading ? '🔍 กำลังค้นหา...' : '🔍 ค้นหาที่พัก'}
                        </button>
                      </div>
                      {editHotelSearch.error && <div className="edit-flight-error">❌ {editHotelSearch.error}</div>}
                      {editHotelSearch.results.length > 0 && (
                        <div className="edit-flight-results">
                          <div className="edit-flight-results-title">พบ {editHotelSearch.results.length} ที่พัก — เลือกเพื่ออัปเดตราคา</div>
                          <div className="edit-flight-list">
                            {editHotelSearch.results.slice(0, 5).map((h, idx) => {
                              const name = h.name || h.hotel?.name || h.display_name || 'ที่พัก';
                              const priceObj = h.price || h.offers?.[0]?.price || {};
                              const total = parseFloat(priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0) || 0;
                              const currency = priceObj.currency || 'THB';
                              const isSelected = editModal.selectedHotel === h;
                              return (
                                <button key={idx} type="button" className={`edit-flight-item${isSelected ? ' selected' : ''}`} onClick={() => handleSelectEditHotel(h)}>
                                  <span className="efi-code">🏨</span>
                                  <span className="efi-route">{name}</span>
                                  <span className="efi-price">{formatPriceInThb(total, currency)}</span>
                                  {isSelected && <span className="efi-check">✓</span>}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* ── ฟอร์มรถเช่า/การเดินทาง ── */}
                {editModal.source === 'car' && (
                  <>
                    <div className="edit-form-row">
                      <div className="form-group">
                        <label className="form-label">📍 จุดรับ <span className="required">*</span></label>
                        <input
                          type="text"
                          className="form-input"
                          value={editModal.formData.origin_city}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, origin_city: e.target.value }, selectedTransfer: null })}
                          placeholder="เช่น สนามบินสุวรรณภูมิ"
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">🏁 จุดส่ง <span className="required">*</span></label>
                        <input
                          type="text"
                          className="form-input"
                          value={editModal.formData.destination_city}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, destination_city: e.target.value }, selectedTransfer: null })}
                          placeholder="เช่น โรงแรมกลางเมือง"
                        />
                      </div>
                    </div>
                    <div className="edit-form-row">
                      <div className="form-group">
                        <label className="form-label">📅 วันที่ <span className="required">*</span></label>
                        <input
                          type="date"
                          className="form-input"
                          value={editModal.formData.departure_date}
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, departure_date: e.target.value }, selectedTransfer: null })}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label">👤 จำนวนผู้โดยสาร</label>
                        <input
                          type="number"
                          className="form-input"
                          value={editModal.formData.passengers}
                          min="1"
                          max="9"
                          onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, passengers: e.target.value }, selectedTransfer: null })}
                        />
                      </div>
                    </div>
                    <div className="edit-flight-search-section">
                      <div className="edit-flight-search-header">
                        <span className="edit-flight-search-label">🚗 ค้นหารถ/การเดินทาง</span>
                        <button type="button" className="btn-search-flights" onClick={handleEditCarSearch} disabled={editCarSearch.loading}>
                          {editCarSearch.loading ? '🔍 กำลังค้นหา...' : '🔍 ค้นหา'}
                        </button>
                      </div>
                      {editCarSearch.error && <div className="edit-flight-error">❌ {editCarSearch.error}</div>}
                      {editCarSearch.results.length > 0 && (
                        <div className="edit-flight-results">
                          <div className="edit-flight-results-title">พบ {editCarSearch.results.length} ตัวเลือก — เลือกเพื่ออัปเดตราคา</div>
                          <div className="edit-flight-list">
                            {editCarSearch.results.slice(0, 5).map((tr, idx) => {
                              const name = tr.name || tr.transfer_type || tr.vehicle?.name || 'รถ';
                              const priceObj = tr.price || tr.total_price || {};
                              const total = parseFloat(typeof priceObj === 'number' ? priceObj : (priceObj.total ?? priceObj.amount ?? priceObj ?? 0)) || 0;
                              const currency = (priceObj && priceObj.currency) || 'THB';
                              const isSelected = editModal.selectedTransfer === tr;
                              return (
                                <button key={idx} type="button" className={`edit-flight-item${isSelected ? ' selected' : ''}`} onClick={() => handleSelectEditCar(tr)}>
                                  <span className="efi-code">🚗</span>
                                  <span className="efi-route">{name}</span>
                                  <span className="efi-price">{formatPriceInThb(total, currency)}</span>
                                  {isSelected && <span className="efi-check">✓</span>}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  </>
                )}

                {/* หมายเหตุ (ใช้ร่วมกันทุกประเภท) */}
                <div className="form-group">
                  <label className="form-label">📝 หมายเหตุ / ความต้องการพิเศษ</label>
                  <textarea
                    className="form-input edit-notes-input"
                    value={editModal.formData.notes}
                    onChange={(e) => setEditModal({ ...editModal, formData: { ...editModal.formData, notes: e.target.value } })}
                    placeholder={editModal.source === 'hotel' ? 'เช่น ต้องการห้องติดทะเล...' : editModal.source === 'car' ? 'เช่น ต้องการคาร์ซีท...' : 'เช่น ต้องการที่นั่งริมหน้าต่าง, อาหารมังสวิรัติ...'}
                    rows={2}
                  />
                </div>

                {/* ราคา (read-only info) */}
                <div className="edit-price-info">
                  <span className="edit-price-label">💰 {editModal.source === 'flight' && (editModal.selectedOutbound || editModal.selectedInbound) ? 'ราคาเที่ยวบินที่เลือก' : editModal.source === 'hotel' && editModal.selectedHotel ? 'ราคาที่พักที่เลือก' : editModal.source === 'car' && editModal.selectedTransfer ? 'ราคารถที่เลือก' : 'ราคาปัจจุบัน'}</span>
                  <span className="edit-price-value">
                    {formatPriceInThb(editModal.formData.total_price, editModal.formData.currency)}
                  </span>
                </div>
              </div>

              <div className="edit-modal-actions">
                <button 
                  className="btn-save"
                  onClick={handleUpdateBooking}
                  disabled={processing[editModal.bookingId] === 'updating'}
                >
                  {processing[editModal.bookingId] === 'updating' ? '⏳ กำลังบันทึก...' : '💾 บันทึกการเปลี่ยนแปลง'}
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

      {/* Refund Modal */}
      {refundModal && (
        <div className="payment-modal-overlay" onClick={() => !refundModal.loading && setRefundModal(null)}>
          <div className="payment-modal refund-modal" onClick={(e) => e.stopPropagation()}>
            <div className="payment-modal-header">
              <h2>↩️ คืนเงินรายการจอง</h2>
              <button className="payment-modal-close" onClick={() => !refundModal.loading && setRefundModal(null)}>✕</button>
            </div>
            <div className="payment-modal-body">
              {refundModal.loading ? (
                <p style={{ textAlign: 'center', padding: 24 }}>กำลังตรวจสอบเงื่อนไขการคืนเงิน...</p>
              ) : refundModal.eligibility ? (
                <>
                  <p className="refund-message" style={{ marginBottom: 16, color: '#374151' }}>{refundModal.eligibility.message}</p>
                  {refundModal.eligibility.refundable_items?.length > 0 && (
                    <ul className="refund-items-list" style={{ listStyle: 'none', padding: 0, margin: '0 0 16px 0' }}>
                      {refundModal.eligibility.refundable_items.map((item, idx) => (
                        <li key={idx} style={{ padding: '8px 0', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
                          <span>{item.label}</span>
                          <span style={{ fontWeight: 600 }}>{formatPriceInThb(item.amount, item.currency)}</span>
                          <span style={{ fontSize: 12, color: item.refundable ? '#059669' : '#6b7280' }}>
                            {item.refundable ? '✅ คืนได้' : (item.reason || '❌ คืนไม่ได้')}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {refundModal.eligibility.total_refundable_amount > 0 && (
                    <p style={{ fontWeight: 700, fontSize: 16, marginBottom: 16 }}>
                      ยอดที่คืนได้รวม: {formatPriceInThb(refundModal.eligibility.total_refundable_amount, refundModal.booking?.currency || 'THB')}
                    </p>
                  )}
                  <div className="refund-modal-actions" style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginTop: 16 }}>
                    {refundModal.eligibility.can_full_refund && refundModal.eligibility.total_refundable_amount > 0 && (
                      <button
                        className="btn-refund-confirm-full"
                        onClick={() => handleRefundConfirm('full')}
                        disabled={processing[refundModal.bookingId] === 'refunding'}
                      >
                        {processing[refundModal.bookingId] === 'refunding' ? 'กำลังดำเนินการ...' : 'คืนเงินทั้งหมด'}
                      </button>
                    )}
                    {refundModal.eligibility.total_refundable_amount > 0 && !refundModal.eligibility.can_full_refund && (
                      <button
                        className="btn-refund-confirm-partial"
                        onClick={() => handleRefundConfirm('partial')}
                        disabled={processing[refundModal.bookingId] === 'refunding'}
                      >
                        {processing[refundModal.bookingId] === 'refunding' ? 'กำลังดำเนินการ...' : 'คืนเงินเฉพาะส่วนที่อนุญาต'}
                      </button>
                    )}
                    <button type="button" className="btn-cancel-edit" onClick={() => setRefundModal(null)}>
                      ปิด
                    </button>
                  </div>
                  {refundModal.eligibility.total_refundable_amount === 0 && (
                    <p style={{ color: '#6b7280', marginTop: 8 }}>ไม่สามารถคืนเงินได้ตามเงื่อนไขสายการบิน/โรงแรม</p>
                  )}
                </>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

