import React, { useState } from 'react';
import './NotificationPanel.css';

export default function NotificationPanel({ 
  isOpen, 
  onClose, 
  notificationCount = 0,
  notifications = [],
  position = { right: 0, top: 0 },
  onNavigateToBookings = null,
  onMarkAsRead = null,
  onClearAll = null  // เรียกเมื่อกดล้างทั้งหมด (ให้ parent ทำ mark-all-read + refetch)
}) {
  const [localNotifications, setLocalNotifications] = useState(notifications);

  // Update local notifications when prop changes
  React.useEffect(() => {
    setLocalNotifications(notifications);
  }, [notifications]);

  const handleMarkAsRead = (id) => {
    // Update local state
    setLocalNotifications(prev => 
      prev.map(notif => 
        notif.id === id ? { ...notif, isRead: true } : notif
      )
    );
    // ✅ Sync with parent component
    if (onMarkAsRead) {
      onMarkAsRead(id);
    }
  };

  const handleClearAll = () => {
    setLocalNotifications(prev => 
      prev.map(notif => ({ ...notif, isRead: true }))
    );
    if (onClearAll) onClearAll();
  };

  const newNotifications = localNotifications.filter(n => !n.isRead);
  const previousNotifications = localNotifications.filter(n => n.isRead);

  if (!isOpen) return null;

  return (
    <div className="notification-panel-overlay" onClick={onClose}>
      <div 
        className="notification-panel" 
        onClick={(e) => e.stopPropagation()}
        style={{
          right: `${position.right}px`,
          top: `${position.top}px`
        }}
      >
        {/* Header */}
        <div className="notification-panel-header">
          <div className="notification-panel-title">
            <span>แจ้งเตือนรวม</span>
            {newNotifications.length > 0 && (
              <span className="notification-badge-new">{newNotifications.length} ใหม่</span>
            )}
          </div>
          <button className="notification-clear-all-btn" onClick={handleClearAll}>
            ล้างทั้งหมด
          </button>
        </div>

        {/* Content - แสดงการแจ้งเตือนที่ผ่านมาทั้งหมด */}
        <div className="notification-panel-content">
          {/* New Notifications */}
          {newNotifications.length > 0 && (
            <div className="notification-section">
              <div className="notification-section-header">
                <span>แจ้งเตือนใหม่</span>
              </div>
              <div className="notification-list">
                {newNotifications.map((notification) => (
                    <div 
                      key={notification.id} 
                      className="notification-item new"
                      onClick={() => {
                        // ✅ Mark as read automatically when clicked
                        if (!notification.isRead) {
                          handleMarkAsRead(notification.id);
                        }
                        // ✅ Navigate to bookings page when clicking notification
                        if (notification.bookingId) {
                          if (onNavigateToBookings) {
                            onNavigateToBookings();
                          } else if (window.location.pathname !== '/bookings') {
                            window.location.href = '/bookings';
                          }
                          onClose(); // Close notification panel after navigation
                        }
                      }}
                      style={{ cursor: notification.bookingId ? 'pointer' : 'default' }}
                    >
                      <div className="notification-icon">
                        {notification.type === 'task' ? (
                          <div className="icon-task">✓</div>
                        ) : (
                          <div className="icon-bell">🔔</div>
                        )}
                      </div>
                      <div className="notification-content">
                        <div className="notification-text">{notification.message}</div>
                        <div className="notification-time">
                          <span className="time-icon">🕐</span>
                          {notification.time}
                        </div>
                      </div>
                      <button 
                        className="notification-mark-read"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkAsRead(notification.id);
                        }}
                        title="ทำเครื่องหมายว่าอ่านแล้ว"
                      >
                        อ่านแล้ว
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* การแจ้งเตือนที่ผ่านมา — แสดงเสมอ (มีหรือไม่มีรายการ) */}
          <div className="notification-section">
            <div className="notification-section-header">
              <span>การแจ้งเตือนที่ผ่านมา</span>
              {localNotifications.some(n => !n.isRead) && (
                <button className="notification-clear-all-btn-small" onClick={handleClearAll}>
                  ล้างทั้งหมด
                </button>
              )}
            </div>
            {previousNotifications.length > 0 ? (
              <div className="notification-list">
                {previousNotifications.map((notification) => (
                  <div key={notification.id} className="notification-item previous">
                    <div className="notification-icon">
                      {notification.type === 'task' ? (
                        <div className="icon-task">✓</div>
                      ) : (
                        <div className="icon-bell">🔔</div>
                      )}
                    </div>
                    <div className="notification-content">
                      <div className="notification-text">{notification.message}</div>
                      <div className="notification-time">
                        <span className="time-icon">🕐</span>
                        {notification.time}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="notification-empty-inline" style={{ margin: '8px 0', color: '#6b7280', fontSize: 14 }}>ยังไม่มีการแจ้งเตือนที่อ่านแล้ว</p>
            )}
          </div>

          {/* Empty State */}
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

