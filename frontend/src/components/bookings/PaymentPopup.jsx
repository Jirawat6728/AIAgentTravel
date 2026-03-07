import React, { useState, useEffect, useCallback } from 'react';
import { formatPriceInThb } from '../../utils/currency';
import './PaymentPopup.css';

function formatThaiDate(isoDate) {
  if (!isoDate) return '—';
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
  return formatPriceInThb(amount, currency);
}

const PAYMENT_METHODS = [
  {
    id: 'credit_card',
    icon: '💳',
    title: 'บัตรเครดิต / เดบิต',
    desc: 'Visa, Mastercard, JCB',
    accent: '#0ea5e9',
  },
  {
    id: 'promptpay',
    icon: '📱',
    title: 'พร้อมเพย์',
    desc: 'สแกน QR ผ่านแอปธนาคาร',
    accent: '#10b981',
  },
  {
    id: 'qr',
    icon: '📲',
    title: 'Thai QR Payment',
    desc: 'ชำระผ่าน QR Code',
    accent: '#8b5cf6',
  },
];

/**
 * Payment popup shown after clicking "จ่ายเงิน" in My Bookings.
 * Displays booking summary, total amount, and payment method options.
 */
export default function PaymentPopup({
  open,
  onClose,
  bookingId,
  booking,
  paymentUrl,
  amount,
  currency = 'THB',
  onSelectMethod,
  onPayFullPage,
  fullPageUrl,
}) {
  const [redirecting, setRedirecting] = useState(false);

  const handleSelect = useCallback(
    (methodId) => {
      if (redirecting) return;
      if (!paymentUrl && !onSelectMethod) return;
      setRedirecting(true);
      if (onSelectMethod) {
        onSelectMethod(methodId);
        return;
      }
      if (paymentUrl) window.location.href = paymentUrl;
    },
    [redirecting, onSelectMethod, paymentUrl]
  );

  const handleClose = useCallback(() => {
    if (redirecting) return;
    onClose?.();
  }, [redirecting, onClose]);

  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.key === 'Escape') handleClose();
    };
    if (open) {
      document.addEventListener('keydown', onKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = '';
    };
  }, [open, handleClose]);

  if (!open) return null;

  const route =
    booking?.travel_slots?.origin_city && booking?.travel_slots?.destination_city
      ? `${booking.travel_slots.origin_city} → ${booking.travel_slots.destination_city}`
      : booking?.plan?.flight?.route || '—';
  const departureDate = formatThaiDate(booking?.travel_slots?.departure_date);
  const displayAmount = formatCurrency(amount ?? booking?.total_price ?? 0, currency ?? booking?.currency ?? 'THB');

  return (
    <div
      className="payment-popup-overlay"
      onClick={handleClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-popup-title"
    >
      <div
        className="payment-popup"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="payment-popup-header">
          <div className="payment-popup-header-content">
            <span className="payment-popup-icon" aria-hidden>💳</span>
            <div>
              <h2 id="payment-popup-title" className="payment-popup-title">
                ชำระเงิน
              </h2>
              <p className="payment-popup-subtitle">เลือกช่องทางที่สะดวก</p>
            </div>
          </div>
          <button
            type="button"
            className="payment-popup-close"
            onClick={handleClose}
            aria-label="ปิด"
            disabled={redirecting}
          >
            ✕
          </button>
        </div>

        <div className="payment-popup-body">
          <div className="payment-popup-summary">
            <div className="payment-popup-summary-row">
              <span className="payment-popup-label">ทริป</span>
              <span className="payment-popup-value">{route}</span>
            </div>
            {departureDate !== '—' && (
              <div className="payment-popup-summary-row">
                <span className="payment-popup-label">วันเดินทาง</span>
                <span className="payment-popup-value">{departureDate}</span>
              </div>
            )}
            <div className="payment-popup-amount-wrap">
              <span className="payment-popup-label">ยอดชำระ</span>
              <span className="payment-popup-amount">{displayAmount}</span>
            </div>
          </div>

          <div className="payment-popup-methods">
            <h3 className="payment-popup-methods-title">ช่องทางชำระเงิน</h3>
            {!paymentUrl ? (
              <p className="payment-popup-no-url">ลิงก์ชำระเงินไม่พร้อมใช้งาน กรุณาลองใหม่อีกครั้ง</p>
            ) : (
              <div className="payment-popup-methods-grid">
                {PAYMENT_METHODS.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className="payment-popup-method"
                  onClick={() => handleSelect(m.id)}
                  disabled={redirecting}
                  style={{ '--accent': m.accent }}
                >
                  <span className="payment-popup-method-icon">{m.icon}</span>
                  <div className="payment-popup-method-text">
                    <span className="payment-popup-method-title">{m.title}</span>
                    <span className="payment-popup-method-desc">{m.desc}</span>
                  </div>
                  <span className="payment-popup-method-arrow">›</span>
                </button>
                ))}
              </div>
            )}
          </div>

          {fullPageUrl && onPayFullPage && (
            <div className="payment-popup-fullpage">
              <button
                type="button"
                className="payment-popup-fullpage-btn"
                onClick={() => onPayFullPage(fullPageUrl)}
              >
                เปิดหน้าชำระเงินเต็มรูปแบบ
              </button>
            </div>
          )}

          {redirecting && (
            <div className="payment-popup-redirecting">
              <span className="payment-popup-spinner" />
              <span>กำลังนำคุณไปยังหน้าชำระเงิน...</span>
            </div>
          )}
        </div>

        <div className="payment-popup-footer">
          <p className="payment-popup-secure">
            <span className="payment-popup-secure-icon" aria-hidden>🔒</span>
            ชำระเงินอย่างปลอดภัยผ่าน Omise
          </p>
        </div>
      </div>
    </div>
  );
}
