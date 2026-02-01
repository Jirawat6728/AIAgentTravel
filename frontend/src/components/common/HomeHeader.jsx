import React, { useState, useRef, useEffect } from 'react';
import './HomeHeader.css';

export default function HomeHeader({ isLoggedIn, user, onSignIn, onSignOut, onGetStarted, onNavigateToHome }) {
  const [showUserPopup, setShowUserPopup] = useState(false);
  const userPopupRef = useRef(null);

  // Close popup when clicking outside
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

  return (
    <header className="home-header">
      <div className="header-content">
        <div className="logo-section" onClick={onNavigateToHome} style={{ cursor: 'pointer' }}>
          <div className="logo-icon">
            <svg className="plane-icon" fill="currentColor" viewBox="0 0 24 24">
              <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z" />
            </svg>
          </div>
          <span className="logo-text">AI Travel Agent</span>
        </div>
        <div className="header-buttons">
          <div className="user-menu-container" ref={userPopupRef}>
            {isLoggedIn && user ? (
              <>
                <div 
                  className="user-name-display user-clickable"
                  onClick={() => setShowUserPopup(!showUserPopup)}
                >
                  <span className="user-greeting">สวัสดี,</span>
                  <span className="user-name-text">
                    {user.first_name || user.name || 'ผู้ใช้'}
                  </span>
                  <svg className="user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
                {showUserPopup && (
                  <div className="user-popup">
                    <div className="user-popup-header">
                      <div className="user-popup-avatar">
                        {(user.profile_image || user.picture) ? (
                          <img
                            src={user.profile_image || user.picture}
                            alt=""
                            className="user-popup-avatar-img"
                            onError={(e) => {
                              e.target.style.display = 'none';
                              const next = e.target.nextElementSibling;
                              if (next) next.style.display = 'flex';
                            }}
                          />
                        ) : null}
                        <span
                          className="user-popup-avatar-initial"
                          style={{ display: (user.profile_image || user.picture) ? 'none' : 'flex' }}
                        >
                          {user.first_name && user.last_name
                            ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                            : (user.name || 'U').charAt(0).toUpperCase()}
                        </span>
                      </div>
                      <div className="user-popup-info">
                        <div className="user-popup-name">
                          {user.first_name && user.last_name 
                            ? `${user.first_name} ${user.last_name}`
                            : (user.first_name || user.name || 'ผู้ใช้')}
                        </div>
                        {user.email && (
                          <div className="user-popup-email">{user.email}</div>
                        )}
                      </div>
                    </div>
                    <div className="user-popup-divider"></div>
                    <div className="user-popup-actions">
                      <button onClick={onSignOut} className="user-popup-button user-popup-button-signout">
                        <svg className="user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        ออกจากระบบ
                      </button>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                <button 
                  onClick={onSignIn} 
                  className="btn-header btn-header-signin"
                >
                  เข้าสู่ระบบ
                </button>
              </>
            )}
          </div>
          <button onClick={onGetStarted} className="btn-header-primary">เริ่มต้นใช้งาน</button>
        </div>
      </div>
    </header>
  );
}
