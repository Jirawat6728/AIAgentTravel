import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import Swal from 'sweetalert2';
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

  // --- State สำหรับโหมดค้นหา (เดิม) ---
  const [location, setLocation] = useState('');
  const [checkIn, setCheckIn] = useState('');
  const [checkOut, setCheckOut] = useState('');
  const [guests, setGuests] = useState(1);
  const [guestsDropdownOpen, setGuestsDropdownOpen] = useState(false);
  const [guestsPanelPosition, setGuestsPanelPosition] = useState(null);
  const guestsDropdownRef = useRef(null);
  const guestsPanelRef = useRef(null);
  const guestsTriggerRef = useRef(null);

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

  // --- ฟังก์ชันจัดการ UI เดิม ---
  const updateGuestsPanelPosition = useCallback(() => {
    if (!guestsTriggerRef.current) return;
    const rect = guestsTriggerRef.current.getBoundingClientRect();
    const padding = 12;
    let left = rect.left;
    if (left + GUESTS_PANEL_WIDTH > window.innerWidth - padding) {
      left = Math.max(padding, window.innerWidth - GUESTS_PANEL_WIDTH - padding);
    }
    setGuestsPanelPosition({ top: rect.bottom + 8, left, width: GUESTS_PANEL_WIDTH });
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
    if (!guestsDropdownOpen) { setGuestsPanelPosition(null); return; }
    updateGuestsPanelPosition();
    const onScrollOrResize = () => updateGuestsPanelPosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [guestsDropdownOpen, updateGuestsPanelPosition]);

  const handleTabChange = (tab) => {
    if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
  };

  // --- 1. ฟังก์ชันค้นหาที่พัก (เดิม) ---
  const handleSearch = async (e) => {
    e.preventDefault();
    const loc = (location || '').trim();
    if (!loc || !checkIn || !checkOut) { alert(t('hotels.errFillAll') || 'กรุณากรอกข้อมูลให้ครบ'); return; }
    if (checkOut <= checkIn) { alert(t('hotels.errCheckOutAfter') || 'วันเช็คเอาท์ต้องอยู่หลังวันเช็คอิน'); return; }
    
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
        setError(data.detail || data.message || data.error || 'เกิดข้อผิดพลาด');
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

  // --- 2. จองที่พักผ่าน /api/booking/create (เหมือน FlightsPage) ---
  const createHotelBooking = async (payload) => {
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const userId = user?.user_id || user?.id;
    const res = await fetch(`${baseUrl}/api/booking/create`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(userId ? { 'X-User-ID': userId } : {}),
      },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      const errMsg = typeof data?.detail === 'string' ? data.detail : (data?.detail?.[0]?.msg || data?.message);
      throw new Error(errMsg || 'บันทึกไม่สำเร็จ');
    }
    return data;
  };

  const handleBookSearchResult = async (hotel) => {
    if (!user) {
      const { isConfirmed } = await Swal.fire({
        icon: 'warning',
        title: 'กรุณาเข้าสู่ระบบ',
        text: 'กรุณา Login ก่อนจองที่พัก',
        showCancelButton: true,
        confirmButtonText: 'เข้าสู่ระบบ',
        cancelButtonText: 'ยกเลิก',
      });
      if (isConfirmed) onSignIn?.();
      return;
    }
    const name = hotel.name || hotel.hotel?.name || hotel.display_name || 'ที่พัก';
    const priceObj = hotel.price || hotel.offers?.[0]?.price || {};
    const total = parseFloat(priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0) || 0;
    const currency = priceObj.currency || 'THB';
    const nights = hotel.nights || (() => {
      if (!checkIn || !checkOut) return 1;
      const a = new Date(checkIn);
      const b = new Date(checkOut);
      return Math.max(1, Math.round((b - a) / 86400000));
    })();

    const confirmHtml = `<div style="text-align: left;">
      <p style="margin: 0 0 0.3rem 0; font-weight: 600; color: #1565c0;">🏨 ${name}</p>
      <p style="margin: 0 0 0.5rem 0; color: #666;">${checkIn} – ${checkOut} (${nights} คืน) · ${guests} คน</p>
      <p style="margin: 0; font-size: 1.1rem;">ราคารวม <strong style="color: #c62828;">${formatPriceInThb(total, currency)}</strong></p>
    </div>`;
    const { isConfirmed } = await Swal.fire({
      icon: 'question',
      title: 'ยืนยันจองที่พัก',
      html: confirmHtml,
      showCancelButton: true,
      confirmButtonText: 'ยืนยันจอง',
      cancelButtonText: 'ยกเลิก',
      confirmButtonColor: '#c62828',
    });
    if (!isConfirmed) return;

    const segment = {
      selected_option: {
        raw_data: hotel,
        price_amount: total,
        currency,
        hotel_name: name,
      },
    };
    const plan = { accommodation: { segments: [segment] } };
    const travelSlots = {
      destination_city: location,
      location,
      check_in: checkIn,
      check_out: checkOut,
      guests,
      nights,
      accommodations: [segment],
      source: 'hotel_search',
    };
    setIsLoading(true);
    setError(null);
    try {
      await createHotelBooking({
        trip_id: `hotel-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        chat_id: null,
        user_id: user?.user_id || user?.id,
        plan,
        travel_slots: travelSlots,
        total_price: total,
        currency,
        mode: 'normal',
      });
      await Swal.fire({
        icon: 'success',
        title: 'จองสำเร็จ',
        text: 'ข้อมูลบันทึกลงระบบเรียบร้อยแล้ว คุณสามารถชำระเงินได้ที่ การจองของฉัน',
        confirmButtonText: 'ไปที่การจองของฉัน',
        confirmButtonColor: '#1565c0',
      });
      onNavigateToBookings?.();
    } catch (err) {
      await Swal.fire({ icon: 'error', title: 'บันทึกไม่สำเร็จ', text: err.message, confirmButtonText: 'ตกลง' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="hotels-page" data-theme={theme}>
      <AppHeader
        activeTab="hotels" user={user} onNavigateToHome={onNavigateToHome}
        onTabChange={handleTabChange} onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI} onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels} onNavigateToCarRentals={onNavigateToCarRentals}
        onLogout={onLogout} onSignIn={onSignIn} notificationCount={notificationCount}
        notifications={notifications} onMarkNotificationAsRead={onMarkNotificationAsRead}
        onClearAllNotifications={onClearAllNotifications} isConnected={true}
        onNavigateToProfile={onNavigateToProfile} onNavigateToSettings={onNavigateToSettings}
      />

      <div className="hotels-content" data-theme={theme} data-font-size={fontSize}>
            <div className="hotels-search-container">
              <form className="hotels-search-form" onSubmit={handleSearch}>
                {/* --- โค้ด Form เดิมของคุณ ไม่ได้แก้เลย --- */}
                <div className="hotels-field-wrap">
                  <label className="hotels-field-label" htmlFor="hotels-location">{t('hotels.location')}</label>
                  <input id="hotels-location" type="text" className="hotels-input" placeholder={t('hotels.location')} value={location} onChange={(e) => setLocation(e.target.value)} aria-label={t('hotels.location')} />
                </div>
                <div className="hotels-field-wrap">
                  <label className="hotels-field-label" htmlFor="hotels-check-in">{t('hotels.checkIn')}</label>
                  <input id="hotels-check-in" type="date" className="hotels-input" value={checkIn} min={todayStr} max={maxDateStr} onChange={(e) => setCheckIn(e.target.value)} aria-label={t('hotels.checkIn')} />
                </div>
                <div className="hotels-field-wrap">
                  <label className="hotels-field-label" htmlFor="hotels-check-out">{t('hotels.checkOut')}</label>
                  <input id="hotels-check-out" type="date" className="hotels-input" value={checkOut} min={checkIn || todayStr} max={maxDateStr} onChange={(e) => setCheckOut(e.target.value)} aria-label={t('hotels.checkOut')} />
                </div>
                
                {/* Dropdown ผู้เข้าพักเดิมของคุณ */}
                <div className="hotels-field-wrap hotels-guests-dropdown-wrap" ref={guestsDropdownRef}>
                  <label className="hotels-field-label" id="hotels-guests-label">{t('hotels.guests')}</label>
                  <div ref={guestsTriggerRef} className="hotels-guests-trigger" onClick={() => setGuestsDropdownOpen((o) => !o)} role="button" tabIndex={0} aria-haspopup="dialog" aria-expanded={guestsDropdownOpen} aria-labelledby="hotels-guests-label">
                    <span className="hotels-guests-trigger-icon" aria-hidden="true">👤</span>
                    <span className="hotels-guests-trigger-count">{guests} {t('flights.persons')}</span>
                    <span className={`hotels-guests-trigger-arrow ${guestsDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
                  </div>
                  {guestsDropdownOpen && guestsPanelPosition && createPortal(
                    <div ref={guestsPanelRef} className="hotels-guests-dropdown-panel" data-theme={theme} role="dialog" aria-label={t('hotels.guests')} style={{ position: 'fixed', top: guestsPanelPosition.top, left: guestsPanelPosition.left, width: guestsPanelPosition.width, minWidth: guestsPanelPosition.width, maxWidth: guestsPanelPosition.width }}>
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

            {error && <div className="hotels-error" role="alert" style={{ marginTop: '20px' }}>{error}</div>}

            <div className="hotels-results">
              {hasSearched && !isLoading && hotels.length === 0 && <div className="hotels-no-data" role="status">{t('hotels.noData')}</div>}
              {hotels.length > 0 && <div className="hotels-results-count">พบ {hotels.length} ที่พัก</div>}
              
              {hotels.map((h, i) => {
                const name = h.name || h.hotel?.name || h.display_name || 'ที่พัก';
                const priceObj = h.price || h.offers?.[0]?.price || {};
                const total = priceObj.total ?? priceObj.totalAmount ?? priceObj.base ?? 0;
                const currency = priceObj.currency || 'THB';
                const rating = h.rating || h.hotel?.rating || h.starRating;
                const address = typeof h.address === 'string' ? h.address : (h.hotel?.address?.lines?.length ? h.hotel.address.lines.join(', ') : (h.hotel?.address?.cityName ? [h.hotel.address.cityName, h.hotel.address.countryCode].filter(Boolean).join(', ') : (h.hotel?.cityCode ? `เมือง ${h.hotel.cityCode}` : '')));
                const imageUrl = (h.image_urls && h.image_urls[0])
                  || (h.visuals?.image_urls && h.visuals.image_urls[0])
                  || (h.images && h.images[0])
                  || h.photo
                  || (h.media && h.media[0] && (typeof h.media[0] === 'string' ? h.media[0] : h.media[0].url || h.media[0].uri))
                  || null;
                const placeholderImage = 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300"><rect fill="#e2e8f0" width="400" height="300"/><path fill="#94a3b8" d="M200 100 L280 160 L280 260 L120 260 L120 160 Z"/><circle fill="#94a3b8" cx="200" cy="140" r="25"/><text x="200" y="230" text-anchor="middle" fill="#64748b" font-size="14" font-family="sans-serif">ที่พัก</text></svg>');
                return (
                  <div key={h.id || h.hotel?.hotelId || i} className="hotels-result-card">
                    <div className="hotels-card-image-wrap">
                      <img
                        src={imageUrl || placeholderImage}
                        alt=""
                        className="hotels-card-image"
                        loading="lazy"
                        onError={(e) => { e.target.onerror = null; e.target.src = placeholderImage; }}
                      />
                    </div>
                    <div className="hotels-card-body">
                      <h3 className="hotels-card-name">{name}</h3>
                      {address ? <div className="hotels-card-address">{address}</div> : null}
                      {rating != null && <div className="hotels-card-rating">⭐ {rating}</div>}
                      <div className="hotels-card-price">
                        {formatPriceInThb(total, currency)} {h.nights ? `/ ${h.nights} คืน` : ''}
                      </div>
                      <div className="hotels-card-actions">
                        <button
                          type="button"
                          className="hotels-btn-book"
                          onClick={() => handleBookSearchResult(h)}
                          disabled={isLoading}
                        >
                          {t('hotels.bookNow')}
                        </button>
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