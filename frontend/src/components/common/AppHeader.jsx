import React, { useState, useRef, useEffect, useCallback } from 'react';
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
  onNavigateToHome = null,
  onLogout = () => {},
  onAIClick = null,
  onNotificationClick = null,
  notificationCount = 0,
  isConnected = true,
  notifications = [],
  onSignIn = null,
  onNavigateToProfile = null,
  onNavigateToSettings = null,
  onMarkNotificationAsRead = null
}) {
  const [isNotificationOpen, setIsNotificationOpen] = useState(false);
  const [showUserPopup, setShowUserPopup] = useState(false);
  const notificationButtonRef = useRef(null);
  const userPopupRef = useRef(null);
  const [notificationPosition, setNotificationPosition] = useState({ right: 0, top: 0 });
  const navLinksRef = useRef(null);
  const [sliderStyle, setSliderStyle] = useState({ width: 0, left: 0 });
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef(null);

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

  // ✅ Update slider position when activeTab changes or window resizes
  const updateSliderPosition = useCallback(() => {
    if (!navLinksRef.current) return;
    
    const activeLink = navLinksRef.current.querySelector(`.app-nav-link.active`);
    if (activeLink) {
      const navLinksRect = navLinksRef.current.getBoundingClientRect();
      const activeLinkRect = activeLink.getBoundingClientRect();
      
      const left = activeLinkRect.left - navLinksRect.left;
      const width = activeLinkRect.width;
      
      setSliderStyle({
        width: `${width}px`,
        left: `${left}px`,
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)' // Smooth slide animation
      });
    }
  }, []);

  useEffect(() => {
    // ✅ Wait for DOM to update
    const timeoutId = setTimeout(updateSliderPosition, 0);
    
    // ✅ Handle window resize
    const handleResize = () => {
      updateSliderPosition();
    };
    
    window.addEventListener('resize', handleResize);
    
    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener('resize', handleResize);
    };
  }, [activeTab, updateSliderPosition]);

  // Close user popup when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (userPopupRef.current && !userPopupRef.current.contains(event.target)) {
        setShowUserPopup(false);
      }
      // ✅ Close mobile menu when clicking outside
      if (mobileMenuRef.current && !mobileMenuRef.current.contains(event.target)) {
        setIsMobileMenuOpen(false);
      }
    };

    if (showUserPopup || isMobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserPopup, isMobileMenuOpen]);
  const handleTabClick = (tab, e) => {
    e.preventDefault();
    setIsMobileMenuOpen(false);
    if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels(); // โรงแรม / ที่พักให้เช่า
    else if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
    onTabChange(tab);
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
        <div className="app-logo-section" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <div className="app-logo-icon">
            <svg className="app-plane-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
            </svg>
          </div>
          <span className="app-logo-text">AI Travel Agent</span>
        </div>

        {/* Desktop Navigation - เที่ยวบิน, โรงแรม/ที่พักให้เช่า, เอเจนท์, รถเช่า, การจองของฉัน */}
        <nav className="app-nav-links app-nav-links-desktop" ref={navLinksRef}>
          <div className="app-nav-slider" style={sliderStyle}></div>
          <a href="#" className={`app-nav-link ${activeTab === 'flights' ? 'active' : ''}`} onClick={(e) => handleTabClick('flights', e)} title="เที่ยวบิน">
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
            </svg>
            <span className="app-nav-text">เที่ยวบิน</span>
          </a>
          <a href="#" className={`app-nav-link ${activeTab === 'hotels' ? 'active' : ''}`} onClick={(e) => handleTabClick('hotels', e)} title="โรงแรม / ที่พักให้เช่า">
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9c0-2.21-1.79-4-4-4z" />
            </svg>
            <span className="app-nav-text">โรงแรม / ที่พักให้เช่า</span>
          </a>
          <a href="#" className={`app-nav-link ${activeTab === 'ai' ? 'active' : ''}`} onClick={(e) => handleTabClick('ai', e)} title="เอเจนท์">
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
            </svg>
            <span className="app-nav-text">เอเจนท์</span>
          </a>
          <a href="#" className={`app-nav-link ${activeTab === 'car-rentals' ? 'active' : ''}`} onClick={(e) => handleTabClick('car-rentals', e)} title="รถเช่า">
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z" />
            </svg>
            <span className="app-nav-text">รถเช่า</span>
          </a>
          <a href="#" className={`app-nav-link ${activeTab === 'bookings' ? 'active' : ''}`} onClick={(e) => handleTabClick('bookings', e)} title="การจองของฉัน">
            <svg className="app-nav-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" />
            </svg>
            <span className="app-nav-text">การจองของฉัน</span>
          </a>
        </nav>

        {/* ✅ Mobile Navigation - Dropdown Menu */}
        <div className="app-mobile-nav" ref={mobileMenuRef}>
          <button 
            className="app-mobile-menu-button"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="เมนู"
          >
            <svg className="app-mobile-menu-icon" fill="currentColor" viewBox="0 0 24 24">
              {isMobileMenuOpen ? (
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
              ) : (
                <path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/>
              )}
            </svg>
            <span className="app-mobile-menu-text">
              {activeTab === 'bookings' ? 'การจองของฉัน' : activeTab === 'ai' ? 'เอเจนท์' : 'เมนู'}
            </span>
          </button>
          
          {isMobileMenuOpen && (
            <div className="app-mobile-menu-dropdown">
              <button className={`app-mobile-menu-item ${activeTab === 'flights' ? 'active' : ''}`} onClick={(e) => handleTabClick('flights', e)}>
                <svg className="app-mobile-menu-item-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
                </svg>
                <span>เที่ยวบิน</span>
                {activeTab === 'flights' && <span className="app-mobile-menu-check">✓</span>}
              </button>
              <button className={`app-mobile-menu-item ${activeTab === 'hotels' ? 'active' : ''}`} onClick={(e) => handleTabClick('hotels', e)}>
                <svg className="app-mobile-menu-item-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M7 13c1.66 0 3-1.34 3-3S8.66 7 7 7s-3 1.34-3 3 1.34 3 3 3zm12-6h-8v7H3V5H1v15h2v-3h18v3h2v-9c0-2.21-1.79-4-4-4z" />
                </svg>
                <span>โรงแรม / ที่พักให้เช่า</span>
                {activeTab === 'hotels' && <span className="app-mobile-menu-check">✓</span>}
              </button>
              <button className={`app-mobile-menu-item ${activeTab === 'ai' ? 'active' : ''}`} onClick={(e) => handleTabClick('ai', e)}>
                <svg className="app-mobile-menu-item-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z" />
                </svg>
                <span>เอเจนท์</span>
                {activeTab === 'ai' && <span className="app-mobile-menu-check">✓</span>}
              </button>
              <button className={`app-mobile-menu-item ${activeTab === 'car-rentals' ? 'active' : ''}`} onClick={(e) => handleTabClick('car-rentals', e)}>
                <svg className="app-mobile-menu-item-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M18.92 6.01C18.72 5.42 18.16 5 17.5 5h-11c-.66 0-1.21.42-1.42 1.01L3 12v8c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-1h12v1c0 .55.45 1 1 1h1c.55 0 1-.45 1-1v-8l-2.08-5.99zM6.5 16c-.83 0-1.5-.67-1.5-1.5S5.67 13 6.5 13s1.5.67 1.5 1.5S7.33 16 6.5 16zm11 0c-.83 0-1.5-.67-1.5-1.5s.67-1.5 1.5-1.5 1.5.67 1.5 1.5-.67 1.5-1.5 1.5zM5 11l1.5-4.5h11L19 11H5z" />
                </svg>
                <span>รถเช่า</span>
                {activeTab === 'car-rentals' && <span className="app-mobile-menu-check">✓</span>}
              </button>
              <button className={`app-mobile-menu-item ${activeTab === 'bookings' ? 'active' : ''}`} onClick={(e) => handleTabClick('bookings', e)}>
                <svg className="app-mobile-menu-item-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z" />
                </svg>
                <span>การจองของฉัน</span>
                {activeTab === 'bookings' && <span className="app-mobile-menu-check">✓</span>}
              </button>
            </div>
          )}
        </div>

        <div className="app-user-section">
          {/* ✅ Mobile: My Bookings Button */}
          <button 
            className={`app-btn-bookings-mobile ${activeTab === 'bookings' ? 'active' : ''}`}
            onClick={(e) => handleTabClick('bookings', e)}
            title="การจองของฉัน / My Bookings"
          >
            <svg className="app-bookings-icon-mobile" fill="currentColor" viewBox="0 0 24 24">
              <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM7 10h5v5H7z"/>
            </svg>
          </button>
          
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
                    {(user.profile_image || user.picture) ? (
                      <img 
                        src={user.profile_image || user.picture} 
                        alt="User" 
                        className="app-user-avatar-img"
                        onError={(e) => {
                          e.target.style.display = 'none';
                          e.target.nextElementSibling.style.display = 'flex';
                        }}
                      />
                    ) : null}
                    <span className="app-user-initial" style={{ display: (user.profile_image || user.picture) ? 'none' : 'flex' }}>
                      {user.first_name && user.last_name 
                        ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                        : (user.name || 'U').charAt(0).toUpperCase()}
                    </span>
                  </div>
                  <span className="app-user-name">
                    {user.first_name || user.name || 'User'}
                  </span>
                  <svg className="app-user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                {showUserPopup && (
                  <div className="app-user-popup">
                    <div className="app-user-popup-header">
                      <div className="app-user-popup-avatar">
                        {(user.profile_image || user.picture) ? (
                          <img 
                            src={user.profile_image || user.picture} 
                            alt="User" 
                            className="app-user-avatar-img"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              e.target.nextElementSibling.style.display = 'flex';
                            }}
                          />
                        ) : null}
                        <span 
                          className="app-user-popup-initial"
                          style={{ display: (user.profile_image || user.picture) ? 'none' : 'flex' }}
                        >
                          {user.first_name && user.last_name 
                            ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                            : (user.name || 'U').charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="app-user-popup-info">
                        <div className="app-user-popup-name">
                          {user.first_name && user.last_name 
                            ? `${user.first_name} ${user.last_name}`
                            : (user.first_name || user.name || 'User')}
                        </div>
                        {user.email && (
                          <div className="app-user-popup-email">{user.email}</div>
                        )}
                      </div>
                    </div>
                    <div className="app-user-popup-divider"></div>
                    <div className="app-user-popup-actions">
                      {onNavigateToProfile && (
                        <button 
                          onClick={() => {
                            setShowUserPopup(false);
                            onNavigateToProfile();
                          }} 
                          className="app-user-popup-button app-user-popup-button-profile"
                        >
                          <svg className="app-user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                          แก้ไขโปรไฟล์
                        </button>
                      )}
                      {onNavigateToSettings && (
                        <button 
                          onClick={() => {
                            setShowUserPopup(false);
                            onNavigateToSettings();
                          }} 
                          className="app-user-popup-button app-user-popup-button-settings"
                        >
                          <svg className="app-user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          </svg>
                          การตั้งค่า
                        </button>
                      )}
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
                  <button 
                    onClick={onSignIn} 
                    className="app-btn-signin"
                  >
                    Sign In
                  </button>
                ) : null}
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
        onNavigateToBookings={onNavigateToBookings}
        onMarkAsRead={onMarkNotificationAsRead}
      />
    </header>
  );
}

