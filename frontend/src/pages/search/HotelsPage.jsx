import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import { formatPriceInThb } from '../../utils/currency';
import './HotelsPage.css';

const GUESTS_PANEL_WIDTH = 260;

export default function HotelsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, notificationCount = 0, notifications = [], onMarkNotificationAsRead = null, onClearAllNotifications = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

  const [location, setLocation] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState(1);
  const [guestsDropdownOpen, setGuestsDropdownOpen] = useState(false);
  const [guestsPanelPosition, setGuestsPanelPosition] = useState(null);
  const guestsDropdownRef = useRef(null);
  const guestsPanelRef = useRef(null);
  const guestsTriggerRef = useRef(null);

  const updateGuestsPanelPosition = useCallback(() => {
    if (!guestsTriggerRef.current) return;
    const rect = guestsTriggerRef.current.getBoundingClientRect();
    const padding = 12;
    let left = rect.left;
    if (left + GUESTS_PANEL_WIDTH > window.innerWidth - padding) {
      left = Math.max(padding, window.innerWidth - GUESTS_PANEL_WIDTH - padding);
    }
    setGuestsPanelPosition({
      top: rect.bottom + 8,
      left,
      width: GUESTS_PANEL_WIDTH,
    });
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      const inTrigger = guestsDropdownRef.current?.contains(e.target);
      const inPanel = guestsPanelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setGuestsDropdownOpen(false);
    };
    if (guestsDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [guestsDropdownOpen]);

  useEffect(() => {
    if (!guestsDropdownOpen) {
      setGuestsPanelPosition(null);
      return;
    }
    updateGuestsPanelPosition();
    const onScrollOrResize = () => updateGuestsPanelPosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [guestsDropdownOpen, updateGuestsPanelPosition]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hotels, setHotels] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  const todayStr = new Date().toISOString().slice(0, 10);
  const maxDateStr = (() => {
    const d = new Date();
    d.setFullYear(d.getFullYear() + 2);
    return d.toISOString().slice(0, 10);
  })();

  const handleTabChange = (tab) => {
    if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    const loc = (location || '').trim();
    if (!loc) {
      alert(t('hotels.errFillAll'));
      return;
    }
    if (!checkIn || !checkOut) {
      alert(t('hotels.errFillAll'));
      return;
    }
    if (checkOut <= checkIn) {
      alert(t('hotels.errCheckOutAfter'));
      return;
    }
    if (checkIn < todayStr) {
      alert(t('flights.errPastDate') || 'กรุณาเลือกวันเช็คอินที่ไม่ใช่อดีต');
      return;
    }
    setHasSearched(true);
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const params = new URLSearchParams({
        location: loc,
        check_in: checkIn,
        check_out: checkOut,
        guests: String(Math.max(1, Math.min(9, guests || 1))),
      });
      const res = await fetch(`${baseUrl}/api/mcp/search/hotels?${params.toString()}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setHotels([]);
        setError(data.detail || data.message || data.error || res.statusText || 'เกิดข้อผิดพลาด');
        return;
      }
      if (data.success && Array.isArray(data.hotels)) {
        setHotels(data.hotels);
      } else {
        setHotels([]);
        setError(data.message || data.error || 'ไม่พบที่พัก');
      }
    } catch (err) {
      setError(err.message || 'เกิดข้อผิดพลาด');
      setHotels([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="hotels-page" data-theme={theme}>
      <AppHeader
        activeTab="hotels"
        user={user}
        onNavigateToHome={onNavigateToHome}
        onTabChange={handleTabChange}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        onLogout={onLogout}
        onSignIn={onSignIn}
        notificationCount={notificationCount}
        notifications={notifications}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
        onClearAllNotifications={onClearAllNotifications}
        isConnected={true}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
      />

      <div className="hotels-content" data-theme={theme} data-font-size={fontSize}>
        <div className="hotels-search-container">
          <form className="hotels-search-form" onSubmit={handleSearch}>
            <div className="hotels-field-wrap">
              <label className="hotels-field-label" htmlFor="hotels-location">{t('hotels.location')}</label>
              <input
                id="hotels-location"
                type="text"
                className="hotels-input"
                placeholder={t('hotels.location')}
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                aria-label={t('hotels.location')}
              />
            </div>
            <div className="hotels-field-wrap">
              <label className="hotels-field-label" htmlFor="hotels-check-in">{t('hotels.checkIn')}</label>
              <input
                id="hotels-check-in"
                type="date"
                className="hotels-input"
                value={checkIn}
                min={todayStr}
                max={maxDateStr}
                onChange={(e) => setCheckIn(e.target.value)}
                aria-label={t('hotels.checkIn')}
              />
            </div>
            <div className="hotels-field-wrap">
              <label className="hotels-field-label" htmlFor="hotels-check-out">{t('hotels.checkOut')}</label>
              <input
                id="hotels-check-out"
                type="date"
                className="hotels-input"
                value={checkOut}
                min={checkIn || todayStr}
                max={maxDateStr}
                onChange={(e) => setCheckOut(e.target.value)}
                aria-label={t('hotels.checkOut')}
              />
            </div>
            <div className="hotels-field-wrap hotels-guests-dropdown-wrap" ref={guestsDropdownRef}>
              <label className="hotels-field-label" id="hotels-guests-label">{t('hotels.guests')}</label>
              <div
                ref={guestsTriggerRef}
                className="hotels-guests-trigger"
                onClick={() => setGuestsDropdownOpen((o) => !o)}
                role="button"
                tabIndex={0}
                aria-haspopup="dialog"
                aria-expanded={guestsDropdownOpen}
                aria-labelledby="hotels-guests-label"
              >
                <span className="hotels-guests-trigger-icon" aria-hidden="true">👤</span>
                <span className="hotels-guests-trigger-count">{guests} {t('flights.persons')}</span>
                <span className={`hotels-guests-trigger-arrow ${guestsDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
              </div>
              {guestsDropdownOpen && guestsPanelPosition && createPortal(
                <div
                  ref={guestsPanelRef}
                  className="hotels-guests-dropdown-panel"
                  data-theme={theme}
                  role="dialog"
                  aria-label={t('hotels.guests')}
                  style={{
                    position: 'fixed',
                    top: guestsPanelPosition.top,
                    left: guestsPanelPosition.left,
                    width: guestsPanelPosition.width,
                    minWidth: guestsPanelPosition.width,
                    maxWidth: guestsPanelPosition.width,
                  }}
                >
                  <div className="hotels-guests-dropdown-row">
                    <div className="hotels-guests-dropdown-label">{t('hotels.guests')}</div>
                    <div className="hotels-guests-dropdown-controls">
                      <button type="button" className="hotels-guests-btn" onClick={() => setGuests((g) => Math.max(1, g - 1))} aria-label="-">−</button>
                      <span className="hotels-guests-dropdown-value">{guests}</span>
                      <button type="button" className="hotels-guests-btn" onClick={() => setGuests((g) => Math.min(9, g + 1))} aria-label="+">+</button>
                    </div>
                  </div>
                </div>,
                document.body
              )}
            </div>
            <div className="hotels-btn-wrap">
              <span className="hotels-field-label hotels-field-label-invisible" aria-hidden="true">&#8203;</span>
              <button type="submit" className="hotels-btn-search" disabled={isLoading}>
                {isLoading ? t('hotels.searching') : t('hotels.search')}
              </button>
            </div>
          </form>
        </div>

        {error && (
          <div className="hotels-error" role="alert">
            {error}
          </div>
        )}

        <div className="hotels-results">
          {hasSearched && !isLoading && hotels.length === 0 && (
            <div className="hotels-no-data" role="status">{t('hotels.noData')}</div>
          )}
          {hotels.length > 0 && (
            <div className="hotels-results-count">
              พบ {hotels.length} ที่พัก
            </div>
          )}
          {hotels.map((h, i) => {
            const name = h.name || h.hotel?.name || h.display_name || 'ที่พัก';
            const priceObj = h.price || h.offers?.[0]?.price || {};
            const total = priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0;
            const currency = priceObj.currency || 'THB';
            const rating = h.rating || h.hotel?.rating || h.starRating;
            return (
              <div key={h.id || i} className="hotels-result-card">
                <div className="hotels-card-main">
                  <h3 className="hotels-card-name">{name}</h3>
                  {rating != null && (
                    <div className="hotels-card-rating">⭐ {rating}</div>
                  )}
                  {h.address && (
                    <div className="hotels-card-address">{h.address}</div>
                  )}
                  <div className="hotels-card-price">
                    {formatPriceInThb(total, currency)} {h.nights ? `/ ${h.nights} คืน` : ''}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
