import React, { useState } from 'react';
import './NotificationPanel.css';

export default function NotificationPanel({ 
  isOpen, 
  onClose, 
  notificationCount = 0,
  notifications = [],
  position = { right: 0, top: 0 },
  onNavigateToBookings = null,
  onMarkAsRead = null  // ✅ New callback to sync with parent
}) {
  const [activeTab, setActiveTab] = useState('all');
  const [taskCategoryFilter, setTaskCategoryFilter] = useState('all'); // all | booking | email_confirm | add_info
  const [localNotifications, setLocalNotifications] = useState(notifications);

  // Update local notifications when prop changes
  React.useEffect(() => {
    setLocalNotifications(notifications);
  }, [notifications]);

  // รีเซ็ต task category filter เมื่อเปลี่ยนไปแท็บอื่น
  React.useEffect(() => {
    if (activeTab !== 'tasks') setTaskCategoryFilter('all');
  }, [activeTab]);

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
  };

  const newNotifications = localNotifications.filter(n => !n.isRead);
  const previousNotifications = localNotifications.filter(n => n.isRead);

  const taskNotifications = localNotifications.filter(n => n.type === 'task');
  const taskFilteredByCategory =
    taskCategoryFilter === 'all'
      ? taskNotifications
      : taskNotifications.filter(n => (n.taskCategory || 'add_info') === taskCategoryFilter);

  const filteredNotifications = activeTab === 'all'
    ? localNotifications
    : activeTab === 'tasks'
    ? taskFilteredByCategory
    : localNotifications.filter(n => n.type === 'reminder');

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
            <span>YOUR NOTIFICATIONS</span>
            {newNotifications.length > 0 && (
              <span className="notification-badge-new">{newNotifications.length} New</span>
            )}
          </div>
          <button className="notification-clear-all-btn" onClick={handleClearAll}>
            X Clear All
          </button>
        </div>

        {/* Tabs */}
        <div className="notification-panel-tabs">
          <button 
            className={`notification-tab ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            VIEW ALL
          </button>
          <button 
            className={`notification-tab ${activeTab === 'tasks' ? 'active' : ''}`}
            onClick={() => setActiveTab('tasks')}
          >
            TASKS
          </button>
          <button 
            className={`notification-tab ${activeTab === 'reminders' ? 'active' : ''}`}
            onClick={() => setActiveTab('reminders')}
          >
            REMINDERS
          </button>
        </div>

        {/* หมวดย่อยสำหรับ TASKS: การจองตั๋ว | ยืนยันอีเมลก่อนจอง | การเพิ่มข้อมูล */}
        {activeTab === 'tasks' && (
          <div className="notification-task-categories">
            <button
              className={`notification-task-cat-btn ${taskCategoryFilter === 'all' ? 'active' : ''}`}
              onClick={() => setTaskCategoryFilter('all')}
            >
              ทั้งหมด
            </button>
            <button
              className={`notification-task-cat-btn ${taskCategoryFilter === 'booking' ? 'active' : ''}`}
              onClick={() => setTaskCategoryFilter('booking')}
            >
              การจองตั๋ว
            </button>
            <button
              className={`notification-task-cat-btn ${taskCategoryFilter === 'email_confirm' ? 'active' : ''}`}
              onClick={() => setTaskCategoryFilter('email_confirm')}
            >
              ยืนยันอีเมลก่อนจอง
            </button>
            <button
              className={`notification-task-cat-btn ${taskCategoryFilter === 'add_info' ? 'active' : ''}`}
              onClick={() => setTaskCategoryFilter('add_info')}
            >
              การเพิ่มข้อมูล
            </button>
          </div>
        )}

        {/* Content */}
        <div className="notification-panel-content">
          {/* New Notifications */}
          {newNotifications.length > 0 && (
            <div className="notification-section">
              <div className="notification-list">
                {newNotifications
                  .filter(n => {
                    if (activeTab === 'all') return true;
                    if (activeTab === 'reminders') return n.type === 'reminder';
                    if (activeTab === 'tasks' && n.type === 'task') {
                      return taskCategoryFilter === 'all' || (n.taskCategory || 'add_info') === taskCategoryFilter;
                    }
                    return false;
                  })
                  .map((notification) => (
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
                        title="Mark As Read"
                      >
                        Mark As Read
                      </button>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Previous Notifications */}
          {previousNotifications.length > 0 && (
            <div className="notification-section">
              <div className="notification-section-header">
                <span>PREVIOUS NOTIFICATIONS</span>
                <button className="notification-clear-all-btn-small" onClick={handleClearAll}>
                  X Clear All
                </button>
              </div>
              <div className="notification-list">
                {previousNotifications
                  .filter(n => {
                    if (activeTab === 'all') return true;
                    if (activeTab === 'reminders') return n.type === 'reminder';
                    if (activeTab === 'tasks' && n.type === 'task') {
                      return taskCategoryFilter === 'all' || (n.taskCategory || 'add_info') === taskCategoryFilter;
                    }
                    return false;
                  })
                  .map((notification) => (
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
                      <div className="notification-actions">
                        <button className="notification-action-btn">✕</button>
                        <button className="notification-action-btn check">✓</button>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Empty State */}
          {filteredNotifications.length === 0 && (
            <div className="notification-empty">
              <div className="notification-empty-icon">🔔</div>
              <div className="notification-empty-text">No notifications</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

