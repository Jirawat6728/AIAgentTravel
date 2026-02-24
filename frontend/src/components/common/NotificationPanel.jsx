import React, { useState, useEffect } from 'react';
import './NotificationPanel.css';

function getRelativeTime(isoString) {
  if (!isoString) return 'เมื่อสักครู่';
  try {
    const date = new Date(isoString);
    const diffMs = Date.now() - date.getTime();
    if (isNaN(diffMs) || diffMs < 0) return 'เมื่อสักครู่';
    const diffSec  = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays  = Math.floor(diffMs / 86400000);
    if (diffSec < 10)  return 'เมื่อสักครู่';
    if (diffSec < 60)  return `${diffSec} วินาทีที่แล้ว`;
    if (diffMins < 60) return `${diffMins} นาทีที่แล้ว`;
    if (diffHours < 24) return `${diffHours} ชั่วโมงที่แล้ว`;
    if (diffDays === 1) return 'เมื่อวาน';
    if (diffDays < 7)  return `${diffDays} วันที่แล้ว`;
    return date.toLocaleDateString('th-TH', { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return 'เมื่อสักครู่';
  }
}

// ── Icon & color mapping per notification type ────────────────────────────
const TYPE_CONFIG = {
  // Booking
  booking_created:          { icon: '🎫', color: 'blue',   label: 'การจอง' },
  booking_cancelled:        { icon: '❌', color: 'red',    label: 'ยกเลิกการจอง' },
  booking_updated:          { icon: '✏️', color: 'blue',   label: 'อัปเดตการจอง' },
  trip_change:              { icon: '✏️', color: 'blue',   label: 'อัปเดตทริป' },
  // Payment
  payment_status:           { icon: '💳', color: 'green',  label: 'การชำระเงิน' },
  payment_success:          { icon: '✅', color: 'green',  label: 'ชำระเงินสำเร็จ' },
  payment_failed:           { icon: '⚠️', color: 'red',    label: 'ชำระเงินล้มเหลว' },
  // Flight alerts
  flight_delayed:           { icon: '⏰', color: 'orange', label: 'เที่ยวบินล่าช้า' },
  flight_cancelled:         { icon: '🚫', color: 'red',    label: 'เที่ยวบินถูกยกเลิก' },
  flight_rescheduled:       { icon: '🔄', color: 'orange', label: 'เปลี่ยนเวลาบิน' },
  trip_alert:               { icon: '⚠️', color: 'orange', label: 'แจ้งเตือนทริป' },
  // Check-in
  checkin_reminder_flight:  { icon: '✈️', color: 'teal',   label: 'เช็คอินเครื่องบิน' },
  checkin_reminder_hotel:   { icon: '🏨', color: 'teal',   label: 'เช็คอินโรงแรม' },
  // Account
  account_email_changed:    { icon: '📧', color: 'purple', label: 'เปลี่ยนอีเมล' },
  account_password_changed: { icon: '🔒', color: 'purple', label: 'เปลี่ยนรหัสผ่าน' },
  account_card_added:       { icon: '💳', color: 'green',  label: 'เพิ่มบัตร' },
  account_card_removed:     { icon: '🗑️', color: 'gray',   label: 'ลบบัตร' },
  account_cotraveler_added: { icon: '👥', color: 'blue',   label: 'ผู้จองร่วม' },
  account_profile_updated:  { icon: '👤', color: 'purple', label: 'อัปเดตโปรไฟล์' },
};

function getTypeConfig(type) {
  return TYPE_CONFIG[type] || { icon: '🔔', color: 'gray', label: 'แจ้งเตือน' };
}

export default function NotificationPanel({ 
  isOpen, 
  onClose, 
  notificationCount = 0,
  notifications = [],
  position = { right: 0, top: 0 },
  onNavigateToBookings = null,
  onMarkAsRead = null,
  onClearAll = null
}) {
  const [localNotifications, setLocalNotifications] = useState(notifications);
  const [markingIds, setMarkingIds] = useState(new Set());
  const [activeFilter, setActiveFilter] = useState('all');
  const [, setTick] = useState(0); // force re-render ทุก 30 วินาที เพื่ออัปเดต relative time

  useEffect(() => {
    if (!isOpen) return;
    const timer = setInterval(() => setTick(t => t + 1), 30000);
    return () => clearInterval(timer);
  }, [isOpen]);

  React.useEffect(() => {
    setLocalNotifications(notifications);
  }, [notifications]);

  const handleMarkAsRead = (id) => {
    setMarkingIds(prev => new Set(prev).add(id));
    setTimeout(() => {
      setLocalNotifications(prev =>
        prev.map(notif => notif.id === id ? { ...notif, isRead: true } : notif)
      );
      setMarkingIds(prev => {
        const next = new Set(prev);
        next.delete(id);
        return next;
      });
      if (onMarkAsRead) onMarkAsRead(id);
    }, 250);
  };

  const handleClearAll = () => {
    // mark ทุกอันเป็น read แต่ไม่ลบออก — ยังดูประวัติได้ใน "ที่ผ่านมา"
    setLocalNotifications(prev => prev.map(notif => ({ ...notif, isRead: true })));
    if (onClearAll) onClearAll(); // sync กับ backend (mark-all-read)
  };

  // Filter categories
  const FILTERS = [
    { key: 'all',      label: 'ทั้งหมด' },
    { key: 'booking',  label: '🎫 การจอง' },
    { key: 'payment',  label: '💳 ชำระเงิน' },
    { key: 'flight',   label: '✈️ เที่ยวบิน' },
    { key: 'checkin',  label: '🏨 เช็คอิน' },
    { key: 'account',  label: '👤 บัญชี' },
  ];

  const FILTER_TYPES = {
    booking:  ['booking_created', 'booking_cancelled', 'booking_updated', 'trip_change', 'trip_alert'],
    payment:  ['payment_status', 'payment_success', 'payment_failed'],
    flight:   ['flight_delayed', 'flight_cancelled', 'flight_rescheduled'],
    checkin:  ['checkin_reminder_flight', 'checkin_reminder_hotel'],
    account:  ['account_email_changed', 'account_password_changed', 'account_card_added', 'account_card_removed', 'account_cotraveler_added', 'account_profile_updated'],
  };

  const filterNotif = (list) => {
    if (activeFilter === 'all') return list;
    const types = FILTER_TYPES[activeFilter] || [];
    return list.filter(n => types.includes(n.type));
  };

  const newNotifications = filterNotif(localNotifications.filter(n => !n.isRead));
  const previousNotifications = filterNotif(localNotifications.filter(n => n.isRead));

  if (!isOpen) return null;

  const renderNotifItem = (notification, isNew) => {
    const cfg = getTypeConfig(notification.type);
    return (
      <div
        key={notification.id}
        className={`notification-item ${isNew ? 'new' : 'previous'} notif-color-${cfg.color}${markingIds.has(notification.id) ? ' marking-read' : ''}`}
        onClick={() => {
          if (!notification.isRead) handleMarkAsRead(notification.id);
          if (notification.bookingId) {
            if (onNavigateToBookings) onNavigateToBookings();
            else if (window.location.pathname !== '/bookings') window.location.href = '/bookings';
            onClose();
          }
        }}
        style={{ cursor: 'pointer' }}
      >
        <div className={`notification-icon-wrap notif-icon-${cfg.color}`}>
          <span className="notif-type-icon">{cfg.icon}</span>
        </div>
        <div className="notification-content">
          <div className="notif-type-label">{notification.title || cfg.label}</div>
          <div className="notification-text">{notification.message}</div>
          <div className="notification-time">
            <span className="time-icon">🕐</span>
            {getRelativeTime(notification.created_at)}
          </div>
        </div>
        {isNew && <div className="notif-unread-dot" />}
      </div>
    );
  };

  return (
    <div className="notification-panel-overlay" onClick={onClose}>
      <div
        className="notification-panel"
        onClick={(e) => e.stopPropagation()}
        style={{ right: `${position.right}px`, top: `${position.top}px` }}
      >
        {/* Header */}
        <div className="notification-panel-header">
          <div className="notification-panel-title">
            <span>การแจ้งเตือน</span>
            {localNotifications.filter(n => !n.isRead).length > 0 && (
              <span className="notification-badge-new">
                {localNotifications.filter(n => !n.isRead).length} ใหม่
              </span>
            )}
          </div>
          <button className="notification-clear-all-btn" onClick={handleClearAll}>
            ล้างทั้งหมด
          </button>
        </div>

        {/* Filter tabs */}
        <div className="notif-filter-bar">
          {FILTERS.map(f => (
            <button
              key={f.key}
              className={`notif-filter-btn${activeFilter === f.key ? ' active' : ''}`}
              onClick={() => setActiveFilter(f.key)}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="notification-panel-content">
          {/* New */}
          {newNotifications.length > 0 && (
            <div className="notification-section">
              <div className="notification-section-header">
                <span>ใหม่</span>
              </div>
              <div className="notification-list">
                {newNotifications.map(n => renderNotifItem(n, true))}
              </div>
            </div>
          )}

          {/* Previous */}
          <div className="notification-section">
            <div className="notification-section-header">
              <span>ที่ผ่านมา</span>
              {localNotifications.some(n => !n.isRead) && (
                <button className="notification-clear-all-btn-small" onClick={handleClearAll}>
                  ล้างทั้งหมด
                </button>
              )}
            </div>
            {previousNotifications.length > 0 ? (
              <div className="notification-list">
                {previousNotifications.map(n => renderNotifItem(n, false))}
              </div>
            ) : (
              <p className="notification-empty-inline">ยังไม่มีการแจ้งเตือนที่อ่านแล้ว</p>
            )}
          </div>

          {/* Empty state */}
          {localNotifications.length === 0 && (
            <div className="notification-empty">
              <div className="notification-empty-icon">🔔</div>
              <div className="notification-empty-text">ยังไม่มีการแจ้งเตือน</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
