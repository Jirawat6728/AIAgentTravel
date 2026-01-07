import React, { useState, useRef, useEffect } from 'react';
import './AppHeader.css';
import NotificationPanel from './NotificationPanel';

export default function AppHeader({ 
  activeTab = 'ai', 
  user = null, 
  onTabChange = () => {},
  onNavigateToBookings = null,
  onNavigateToAI = null,
  onNavigateToFlights = null,
  onNavigateToHotels = null,
  onNavigateToCarRentals = null,
  onLogout = () => {},
  onAIClick = null,
  onNotificationClick = null,
  notificationCount = 0,
  isConnected = true,
  notifications = [],
  onSignIn = null
}) {
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [showUserPopup, setShowUserPopup] = useState(false);
  const notificationButtonRef = useRef(null);
  const userPopupRef = useRef(null);
  const [notificationPosition, setNotificationPosition] = useState({ right: 0, top: 0 });

  useEffect(() => {
    if (isNotificationOpen && notificationButtonRef.current) {
      const buttonRect = notificationButtonRef.current.getBoundingClientRect();
      const headerRect = notificationButtonRef.current.closest('.app-header')?.getBoundingClientRect();
      
      if (headerRect) {
        // คำนวณตำแหน่งจากขอบขวาของ header
        const right = window.innerWidth - buttonRect.right;
        const top = headerRect.bottom;
        setNotificationPosition({ right, top });
      }
    }
  }, [isNotificationOpen]);

  // Close user popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userPopupRef.current && !userPopupRef.current.contains(event.target)) {
        setShowUserPopup(false);
      }
    };

    if (showUserPopup) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserPopup]);
  const handleTabClick = (tab, e) => {
    e.preventDefault();
    if (tab === 'bookings' && onNavigateToBookings) {
      onNavigateToBookings();
    } else if (tab === 'ai' && onNavigateToAI) {
      onNavigateToAI();
    } else if (tab === 'flights' && onNavigateToFlights) {
      onNavigateToFlights();
    } else if (tab === 'hotels' && onNavigateToHotels) {
      onNavigateToHotels();
    } else if (tab === 'car-rentals' && onNavigateToCarRentals) {
      onNavigateToCarRentals();
    } else {
      // Fallback: เรียก onTabChange
      onTabChange(tab);
    }
  };

  const handleAIClick = () => {
    if (onAIClick) {
      onAIClick();
    } else {
      // Default: Scroll to chat input or focus on input
      const chatInput = document.querySelector('.chat-input-textarea');
      if (chatInput) {
        chatInput.focus();
      }
    }
  };

  const handleNotificationClick = () => {
    setIsNotificationOpen(!isNotificationOpen);
    if (onNotificationClick) {
      onNotificationClick();
    }
  };

  return (
    <header className="app-header">
      <div className="app-header-content">
        <div className="app-logo-section">
          <div className="app-logo-icon">
            <svg className="app-plane-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
            </svg>
          </div>
          <span className="app-logo-text">AI Travel Agent</span>
        </div>

        <nav className="app-nav-links">
          <a 
            href="#" 
            className={`app-nav-link ${activeTab === 'flights' ? 'active' : ''}`}
            onClick={(e) => handleTabClick('flights', e)}
            title="Flights"
          >
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
            </svg>
            <span className="app-nav-text">Flights</span>
          </a>
          <a 
            href="#" 
            className={`app-nav-link ${activeTab === 'hotels' ? 'active' : ''}`}
            onClick={(e) => handleTabClick('hotels', e)}
            title="Hotels"
          >
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
            </svg>
            <span className="app-nav-text">Hotels</span>
          </a>
          <button 
            className={`app-nav-link app-nav-link-ai ${activeTab === 'ai' ? 'active' : ''}`}
            onClick={(e) => {
              e.preventDefault();
              handleAIClick();
              if (onNavigateToAI) {
                onNavigateToAI();
              }
            }}
            title={isConnected ? "เริ่มสนทนากับ AI (เชื่อมต่อแล้ว)" : "เริ่มสนทนากับ AI (ไม่เชื่อมต่อ)"}
          >
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span className="app-ai-nav-text">Agent</span>
            <div className={`app-connection-status-dot ${isConnected ? 'app-status-connected' : 'app-status-disconnected'}`}></div>
          </button>
          <a 
            href="#" 
            className={`app-nav-link ${activeTab === 'car-rentals' ? 'active' : ''}`}
            onClick={(e) => handleTabClick('car-rentals', e)}
            title="Car Rentals"
          >
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5S16.67 13 17.5 13s1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z"/>
            </svg>
            <span className="app-nav-text">Car Rentals</span>
          </a>
          <a 
            href="#" 
            className={`app-nav-link ${activeTab === 'bookings' ? 'active' : ''}`}
            onClick={(e) => handleTabClick('bookings', e)}
            title="My Bookings"
          >
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>
            </svg>
            <span className="app-nav-text">My Bookings</span>
          </a>
        </nav>

        <div className="app-user-section">
          <button 
            ref={notificationButtonRef}
            className={`app-btn-notification ${isNotificationOpen ? 'active' : ''}`}
            onClick={handleNotificationClick}
            title="การแจ้งเตือน"
          >
            <svg className="app-notification-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.89 2 2 2zm6-6v-5c0-3.07-1.64-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.63 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"/>
            </svg>
            {notificationCount > 0 && (
              <span className="app-notification-badge">{notificationCount}</span>
            )}
          </button>
          
          <div className="app-user-menu-container" ref={userPopupRef}>
            {user ? (
              <>
                <div 
                  className="app-user-info app-user-clickable"
                  onClick={() => setShowUserPopup(!showUserPopup)}
                >
                  <div className="app-user-avatar">
                    <span className="app-user-initial">
                      {user.first_name && user.last_name 
                        ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                        : (user.name || 'U').charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="app-user-name">
                    {user.first_name && user.last_name 
                      ? `${user.first_name} ${user.last_name}`
                      : user.name || 'User'}
                  </span>
                  <svg className="app-user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                {showUserPopup && (
                  <div className="app-user-popup">
                    <div className="app-user-popup-header">
                      <div className="app-user-popup-avatar">
                        {user.first_name && user.last_name 
                          ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                          : (user.name || 'U').charAt(0).toUpperCase()}
                      </div>
                      <div className="app-user-popup-info">
                        <div className="app-user-popup-name">
                          {user.first_name && user.last_name 
                            ? `${user.first_name} ${user.last_name}`
                            : user.name || 'User'}
                        </div>
                        {user.email && (
                          <div className="app-user-popup-email">{user.email}</div>
                        )}
                      </div>
                    </div>
                    <div className="app-user-popup-divider"></div>
                    <div className="app-user-popup-actions">
                      {onLogout && (
                        <button onClick={onLogout} className="app-user-popup-button app-user-popup-button-signout">
                          <svg className="app-user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                          </svg>
                          Logout
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                {onSignIn ? (
                  <>
                    <button 
                      onClick={() => setShowUserPopup(!showUserPopup)} 
                      className="app-btn-signin"
                    >
                      Sign In
                      <svg className="app-user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                    {showUserPopup && (
                      <div className="app-user-popup">
                        <div className="app-user-popup-header">
                          <div className="app-user-popup-guest-icon">
                            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                            </svg>
                          </div>
                          <div className="app-user-popup-info">
                            <div className="app-user-popup-name">Guest</div>
                            <div className="app-user-popup-email">Sign in to access your account</div>
                          </div>
                        </div>
                        <div className="app-user-popup-divider"></div>
                        <div className="app-user-popup-actions">
                          <button onClick={onSignIn} className="app-user-popup-button app-user-popup-button-signin">
                            <svg className="app-user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                            </svg>
                            Sign In
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <div className="app-user-info">
                    <div className="app-user-avatar">
                      <span className="app-user-initial">G</span>
                    </div>
                    <span className="app-user-name">Guest</span>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* Notification Panel */}
      <NotificationPanel
        isOpen={isNotificationOpen}
        onClose={() => setIsNotificationOpen(false)}
        notificationCount={notificationCount}
        notifications={notifications}
        position={notificationPosition}
      />
    </header>
  );
}

