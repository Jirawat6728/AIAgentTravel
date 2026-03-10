import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import { formatPriceInThb } from '../../utils/currency';
import Swal from 'sweetalert2';
import './CarRentalsPage.css';

const GUESTS_PANEL_WIDTH = 260;

export default function CarRentalsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, notificationCount = 0, notifications = [], onMarkNotificationAsRead = null, onClearAllNotifications = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

  const [pickupLocation, setPickupLocation] = useState('');
  const [returnLocation, setReturnLocation] = useState('');
  const [date, setDate] = useState('');
  const [passengers, setPassengers] = useState(1);
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
  const [transfers, setTransfers] = useState([]);
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
    const pickup = (pickupLocation || '').trim();
    const returnLoc = (returnLocation || '').trim();
    if (!pickup || !returnLoc) {
      Swal.fire({ icon: 'warning', text: t('carRentals.errFillAll'), toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (!date) {
      Swal.fire({ icon: 'warning', text: t('carRentals.errFillAll'), toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    if (date < todayStr) {
      Swal.fire({ icon: 'warning', text: t('flights.errPastDate') || 'กรุณาเลือกวันที่ที่ไม่ใช่อดีต', toast: true, position: 'top', showConfirmButton: false, timer: 2500 });
      return;
    }
    setHasSearched(true);
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
      const params = new URLSearchParams({
        origin: pickup,
        destination: returnLoc,
        date,
        passengers: String(Math.max(1, Math.min(9, passengers || 1))),
      });
      const res = await fetch(`${baseUrl}/api/mcp/search/transfers?${params.toString()}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setTransfers([]);
        setError(data.detail || data.message || data.error || res.statusText || 'เกิดข้อผิดพลาด');
        return;
      }
      if (data.success && Array.isArray(data.transfers)) {
        setTransfers(data.transfers);
      } else {
        setTransfers([]);
        setError(data.message || data.error || data.detail || 'ไม่พบตัวเลือกรถ');
      }
    } catch (err) {
      setError(err.message || 'เกิดข้อผิดพลาด');
      setTransfers([]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="car-rentals-page" data-theme={theme}>
      <AppHeader
        activeTab="car-rentals"
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

      <div className="car-rentals-content" data-theme={theme} data-font-size={fontSize}>
        <div className="car-rentals-search-container">
          <form className="car-rentals-search-form" onSubmit={handleSearch}>
            <div className="car-rentals-field-wrap">
              <label className="car-rentals-field-label" htmlFor="car-pickup">{t('carRentals.pickupLocation')}</label>
              <input
                id="car-pickup"
                type="text"
                className="car-rentals-input"
                placeholder={t('carRentals.pickupLocation')}
                value={pickupLocation}
                onChange={(e) => setPickupLocation(e.target.value)}
                aria-label={t('carRentals.pickupLocation')}
              />
            </div>
            <div className="car-rentals-field-wrap">
              <label className="car-rentals-field-label" htmlFor="car-return">{t('carRentals.returnLocation')}</label>
              <input
                id="car-return"
                type="text"
                className="car-rentals-input"
                placeholder={t('carRentals.returnLocation')}
                value={returnLocation}
                onChange={(e) => setReturnLocation(e.target.value)}
                aria-label={t('carRentals.returnLocation')}
              />
            </div>
            <div className="car-rentals-field-wrap">
              <label className="car-rentals-field-label" htmlFor="car-date">{t('carRentals.date')}</label>
              <input
                id="car-date"
                type="date"
                className="car-rentals-input"
                value={date}
                min={todayStr}
                max={maxDateStr}
                onChange={(e) => setDate(e.target.value)}
                aria-label={t('carRentals.date')}
              />
            </div>
            <div className="car-rentals-field-wrap car-rentals-guests-dropdown-wrap" ref={guestsDropdownRef}>
              <label className="car-rentals-field-label" id="car-passengers-label">{t('carRentals.passengers')}</label>
              <div
                ref={guestsTriggerRef}
                className="car-rentals-guests-trigger"
                onClick={() => setGuestsDropdownOpen((o) => !o)}
                role="button"
                tabIndex={0}
                aria-haspopup="dialog"
                aria-expanded={guestsDropdownOpen}
                aria-labelledby="car-passengers-label"
              >
                <span className="car-rentals-guests-trigger-icon" aria-hidden="true">👤</span>
                <span className="car-rentals-guests-trigger-count">{passengers} {t('flights.persons')}</span>
                <span className={`car-rentals-guests-trigger-arrow ${guestsDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
              </div>
              {guestsDropdownOpen && guestsPanelPosition && createPortal(
                <div
                  ref={guestsPanelRef}
                  className="car-rentals-guests-dropdown-panel"
                  data-theme={theme}
                  role="dialog"
                  aria-label={t('carRentals.passengers')}
                  style={{
                    position: 'fixed',
                    top: guestsPanelPosition.top,
                    left: guestsPanelPosition.left,
                    width: guestsPanelPosition.width,
                    minWidth: guestsPanelPosition.width,
                    maxWidth: guestsPanelPosition.width,
                  }}
                >
                  <div className="car-rentals-guests-dropdown-row">
                    <div className="car-rentals-guests-dropdown-label">{t('carRentals.passengers')}</div>
                    <div className="car-rentals-guests-dropdown-controls">
                      <button type="button" className="car-rentals-guests-btn" onClick={() => setPassengers((p) => Math.max(1, p - 1))} aria-label="-">−</button>
                      <span className="car-rentals-guests-dropdown-value">{passengers}</span>
                      <button type="button" className="car-rentals-guests-btn" onClick={() => setPassengers((p) => Math.min(9, p + 1))} aria-label="+">+</button>
                    </div>
                  </div>
                </div>,
                document.body
              )}
            </div>
            <div className="car-rentals-btn-wrap">
              <span className="car-rentals-field-label car-rentals-field-label-invisible" aria-hidden="true">&#8203;</span>
              <button type="submit" className="car-rentals-btn-search" disabled={isLoading}>
                {isLoading ? t('carRentals.searching') : t('carRentals.search')}
              </button>
            </div>
          </form>
        </div>

        {error && (
          <div className="car-rentals-error" role="alert">
            {error}
          </div>
        )}

        <div className="car-rentals-results">
          {hasSearched && !isLoading && transfers.length === 0 && (
            <div className="car-rentals-no-data" role="status">{t('carRentals.noData')}</div>
          )}
          {transfers.length > 0 && (
            <div className="car-rentals-results-count">
              พบ {transfers.length} ตัวเลือก
            </div>
          )}
          {transfers.map((tr, i) => {
            const name = tr.name || tr.transfer_type || tr.vehicle?.name || 'รถ';
            const priceObj = tr.price || tr.total_price || {};
            const total = typeof priceObj === 'number' ? priceObj : (priceObj.total ?? priceObj.amount ?? priceObj ?? 0);
            const currency = (priceObj && priceObj.currency) || 'THB';
            return (
              <div key={tr.id || i} className="car-rentals-result-card">
                <div className="car-rentals-card-main">
                  <h3 className="car-rentals-card-name">{name}</h3>
                  {tr.description && (
                    <div className="car-rentals-card-desc">{tr.description}</div>
                  )}
                  <div className="car-rentals-card-price">
                    {formatPriceInThb(total, currency)}
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
