import React, { useState, useRef, useEffect } from 'react';
import './HomePage.css';

export default function HomePage({ onGetStarted, onSignIn, onSignOut, isLoggedIn, user }) {
  const [searchQuery, setSearchQuery] = useState('');
  const [showUserPopup, setShowUserPopup] = useState(false);
  const userPopupRef = useRef(null);

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      onGetStarted(searchQuery);
    }
  };

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
    <div className="home-container">
      {/* Header */}
      <header className="home-header">
        <div className="header-content">
          <div className="logo-section">
            <div className="logo-icon">
              <svg className="plane-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
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
                      {user.first_name && user.last_name 
                        ? `${user.first_name} ${user.last_name}`
                        : user.name || 'ผู้ใช้'}
                    </span>
                    <svg className="user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                  {showUserPopup && (
                    <div className="user-popup">
                      <div className="user-popup-header">
                        <div className="user-popup-avatar">
                          {user.first_name && user.last_name 
                            ? `${user.first_name.charAt(0)}${user.last_name.charAt(0)}`
                            : (user.name || 'U').charAt(0).toUpperCase()}
                        </div>
                        <div className="user-popup-info">
                          <div className="user-popup-name">
                            {user.first_name && user.last_name 
                              ? `${user.first_name} ${user.last_name}`
                              : user.name || 'ผู้ใช้'}
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
                          Sign Out
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <button 
                    onClick={() => setShowUserPopup(!showUserPopup)} 
                    className="btn-header btn-header-signin"
                  >
                    Sign In
                    <svg className="user-dropdown-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  {showUserPopup && (
                    <div className="user-popup">
                      <div className="user-popup-header">
                        <div className="user-popup-guest-icon">
                          <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                          </svg>
                        </div>
                        <div className="user-popup-info">
                          <div className="user-popup-name">Guest</div>
                          <div className="user-popup-email">Sign in to access your account</div>
                        </div>
                      </div>
                      <div className="user-popup-divider"></div>
                      <div className="user-popup-actions">
                        <button onClick={onSignIn} className="user-popup-button user-popup-button-signin">
                          <svg className="user-popup-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                          </svg>
                          Sign In
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
            <button onClick={onGetStarted} className="btn-header-primary">Get Started</button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-background">
          <div className="gradient-overlay"></div>
          <div className="animated-shapes">
            <div className="shape shape-1"></div>
            <div className="shape shape-2"></div>
            <div className="shape shape-3"></div>
          </div>
        </div>
        
        <div className="hero-content">
          <div className="hero-badge">
            <span className="badge-text">✨ Powered by AI</span>
          </div>
          <h1 className="hero-title">
            Your Personal AI Travel Agent
          </h1>
          <p className="hero-subtitle">
            Plan your perfect trip with AI. Find flights, hotels, and get personalized recommendations instantly.
          </p>
          
          {/* Search Bar */}
          <form onSubmit={handleSearch} className="search-box">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Where do you want to go? (e.g., Tokyo, Paris, New York)"
              className="search-input"
            />
            <button type="submit" className="search-button">
              <svg className="search-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Search
            </button>
          </form>

          {/* Quick Actions */}
          <div className="quick-actions">
            <button onClick={() => onGetStarted('flights')} className="quick-action">
              <span>✈️</span> Find Flights
            </button>
            <button onClick={() => onGetStarted('hotels')} className="quick-action">
              <span>🏨</span> Book Hotels
            </button>
            <button onClick={() => onGetStarted('destinations')} className="quick-action">
              <span>🌍</span> Explore Destinations
            </button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="features-content">
          <div className="section-header">
            <h2 className="section-title">Why Choose AI Travel Agent?</h2>
            <p className="section-subtitle">Experience the future of travel planning</p>
          </div>

          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon feature-icon-blue">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="feature-title">Instant AI Responses</h3>
              <p className="feature-description">Get real-time answers to your travel questions powered by Google Gemini AI</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-green">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9" />
                </svg>
              </div>
              <h3 className="feature-title">Global Flight Search</h3>
              <p className="feature-description">Access real-time flight data from Amadeus API covering worldwide destinations</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-purple">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
              </div>
              <h3 className="feature-title">Hotel Booking</h3>
              <p className="feature-description">Find and compare hotels with competitive prices and detailed information</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-orange">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
              </div>
              <h3 className="feature-title">Natural Conversations</h3>
              <p className="feature-description">Chat naturally in Thai or English - AI understands your travel needs</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-pink">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">24/7 Availability</h3>
              <p className="feature-description">Plan your trips anytime, anywhere with our always-on AI assistant</p>
            </div>

            <div className="feature-card">
              <div className="feature-icon feature-icon-teal">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h3 className="feature-title">Verified Results</h3>
              <p className="feature-description">All flight and hotel data comes from trusted Amadeus travel API</p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" className="how-it-works-section">
        <div className="how-it-works-content">
          <div className="section-header">
            <h2 className="section-title">How It Works</h2>
            <p className="section-subtitle">Start planning your dream trip in 3 simple steps</p>
          </div>

          <div className="steps-container">
            <div className="step-card">
              <div className="step-number">1</div>
              <div className="step-content">
                <h3 className="step-title">Ask Your Question</h3>
                <p className="step-description">Simply type where you want to go or what you're looking for - our AI understands natural language</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">2</div>
              <div className="step-content">
                <h3 className="step-title">AI Searches for You</h3>
                <p className="step-description">Watch as AI analyzes your request and searches through thousands of flights and hotels</p>
              </div>
            </div>

            <div className="step-arrow">→</div>

            <div className="step-card">
              <div className="step-number">3</div>
              <div className="step-content">
                <h3 className="step-title">Get Instant Results</h3>
                <p className="step-description">Receive personalized recommendations with prices, times, and all the details you need</p>
              </div>
            </div>
          </div>
        </div>
      </section>


      {/* CTA Section */}
      <section className="cta-section">
        <div className="cta-content">
          <h2 className="cta-title">Ready to Start Your Journey?</h2>
          <p className="cta-subtitle">Join thousands of travelers who trust AI Travel Agent</p>
          <button onClick={onGetStarted} className="cta-button">
            Get Started Now
            <svg className="arrow-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </section>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-content">
          <div className="footer-section">
            <div className="footer-logo">
              <div className="logo-icon">
                <svg className="plane-icon" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
                </svg>
              </div>
              <span className="logo-text">AI Travel Agent</span>
            </div>
            <p className="footer-description">Your intelligent companion for seamless travel planning</p>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">Product</h4>
            <a href="#features" className="footer-link">Features</a>
            <a href="#how-it-works" className="footer-link">How it Works</a>
            <a href="#destinations" className="footer-link">Destinations</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">Company</h4>
            <a href="#about" className="footer-link">About Us</a>
            <a href="#" className="footer-link">Contact</a>
            <a href="#" className="footer-link">Privacy Policy</a>
          </div>

          <div className="footer-section">
            <h4 className="footer-title">Connect</h4>
            <a href="#" className="footer-link">Twitter</a>
            <a href="#" className="footer-link">Facebook</a>
            <a href="#" className="footer-link">Instagram</a>
          </div>
        </div>

        <div className="footer-bottom">
          <p>© 2025 AI Travel Agent. Powered by Gemini & Amadeus </p>
        </div>
      </footer>
    </div>
  );
}