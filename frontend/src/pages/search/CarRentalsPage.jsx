import React, { useState, useRef, useEffect, useCallback } from 'react';
import { createPortal } from 'react-dom';
import Swal from 'sweetalert2';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import { formatPriceInThb } from '../../utils/currency';
import './CarRentalsPage.css';

export default function CarRentalsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToProfile = null, onNavigateToSettings = null, onNavigateToHome = null, notificationCount = 0, notifications = [], onMarkNotificationAsRead = null, onClearAllNotifications = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();

  // --- State สำหรับโหมดค้นหา ---
  const [pickupLocation, setPickupLocation] = useState('');
  const [dropoffLocation, setDropoffLocation] = useState('');
  const [pickupDate, setPickupDate] = useState('');
  const [dropoffDate, setDropoffDate] = useState('');
  const [passengers, setPassengers] = useState(1);

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [cars, setCars] = useState([]);
  const [hasSearched, setHasSearched] = useState(false);

  const todayStr = new Date().toISOString().slice(0, 10);

  // --- Guests dropdown (เหมือน FlightsPage/HotelsPage) ---
  const PASSENGER_PANEL_WIDTH = 260;
  const [passengerDropdownOpen, setPassengerDropdownOpen] = useState(false);
  const [passengerPanelPosition, setPassengerPanelPosition] = useState(null);
  const passengerDropdownRef = useRef(null);
  const passengerPanelRef = useRef(null);
  const passengerTriggerRef = useRef(null);

  const updatePassengerPanelPosition = useCallback(() => {
    if (!passengerTriggerRef.current) return;
    const rect = passengerTriggerRef.current.getBoundingClientRect();
    const padding = 12;
    let left = rect.left;
    if (left + PASSENGER_PANEL_WIDTH > window.innerWidth - padding) {
      left = Math.max(padding, window.innerWidth - PASSENGER_PANEL_WIDTH - padding);
    }
    setPassengerPanelPosition({
      top: rect.bottom + 8,
      left,
      width: PASSENGER_PANEL_WIDTH,
    });
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      const inTrigger = passengerDropdownRef.current?.contains(e.target);
      const inPanel = passengerPanelRef.current?.contains(e.target);
      if (!inTrigger && !inPanel) setPassengerDropdownOpen(false);
    };
    if (passengerDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [passengerDropdownOpen]);

  useEffect(() => {
    if (!passengerDropdownOpen) {
      setPassengerPanelPosition(null);
      return;
    }
    updatePassengerPanelPosition();
    const onScrollOrResize = () => updatePassengerPanelPosition();
    window.addEventListener('scroll', onScrollOrResize, true);
    window.addEventListener('resize', onScrollOrResize);
    return () => {
      window.removeEventListener('scroll', onScrollOrResize, true);
      window.removeEventListener('resize', onScrollOrResize);
    };
  }, [passengerDropdownOpen, updatePassengerPanelPosition]);

  const handleTabChange = (tab) => {
    if (tab === 'ai' && onNavigateToAI) onNavigateToAI();
    else if (tab === 'bookings' && onNavigateToBookings) onNavigateToBookings();
    else if (tab === 'flights' && onNavigateToFlights) onNavigateToFlights();
    else if (tab === 'hotels' && onNavigateToHotels) onNavigateToHotels();
    else if (tab === 'car-rentals' && onNavigateToCarRentals) onNavigateToCarRentals();
  };

  // --- 1. ค้นหารถเช่า ---
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!pickupLocation.trim() || !pickupDate || !dropoffDate) { 
      await Swal.fire({
        icon: 'warning',
        text: 'กรุณากรอกข้อมูลรับรถและคืนรถให้ครบถ้วน',
        toast: true,
        position: 'top',
        showConfirmButton: false,
        timer: 2500,
      });
      return; 
    }
    
    setHasSearched(true);
    setIsLoading(true);
    setError(null);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const params = new URLSearchParams({ 
        location: pickupLocation, 
        pickup_date: pickupDate, 
        dropoff_date: dropoffDate 
      });
      
      const res = await fetch(`${baseUrl}/api/mcp/search/cars?${params.toString()}`, {
        method: 'POST',
        headers: { Accept: 'application/json' },
      });
      
      const data = await res.json();
      
      // ถ้า API หาไม่เจอ หรือยังไม่ได้ทำ API รถเช่าหลังบ้าน ให้จำลองข้อมูลขึ้นมาโชว์ก่อน
      if (!res.ok || !data.cars || data.cars.length === 0) {
        setCars([
          { name: "Toyota Yaris 1.2 หรือเทียบเท่า", price: { total: 1200 }, type: "Economy", seats: 4 },
          { name: "Honda Civic 1.8 หรือเทียบเท่า", price: { total: 2500 }, type: "Standard", seats: 5 },
          { name: "Toyota Fortuner 2.4 หรือเทียบเท่า", price: { total: 3800 }, type: "SUV", seats: 7 }
        ]);
        setIsLoading(false);
        return;
      }
      
      setCars(data.cars || []);
    } catch (err) {
      // Fallback Mock Data เวลาเชื่อม API ไม่ติด
      setCars([
        { name: "Toyota Yaris 1.2 หรือเทียบเท่า", price: { total: 1200 }, type: "Economy", seats: 4 },
        { name: "Honda Civic 1.8 หรือเทียบเท่า", price: { total: 2500 }, type: "Standard", seats: 5 }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 2. สร้าง booking ผ่าน /api/booking/create (เหมือน Flights/Hotels) ---
  const createCarBooking = async (payload) => {
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
      const errMsg = typeof data?.detail === 'string'
        ? data.detail
        : (data?.detail?.[0]?.msg || data?.message || data?.error);
      throw new Error(errMsg || 'บันทึกไม่สำเร็จ');
    }
    return data;
  };

  const handleBookSearchResult = (car) => {
    const name = car.name || car.vehicle?.name || 'รถเช่าคุณภาพ';
    const type = car.type || car.category || 'รถเช่า';
    const seats = car.seats || car.capacity || passengers || 1;
    const priceObj = car.price || car.offers?.[0]?.price || {};
    const total = parseFloat(priceObj.total ?? priceObj.base ?? 0) || 0;

    handleBook({
      car_model: name,
      type,
      seats,
      pickup: pickupLocation,
      dropoff: dropoffLocation || pickupLocation,
      pickup_date: pickupDate,
      dropoff_date: dropoffDate,
      price: total,
    });
  };

  const handleBook = async ({ car_model, type, seats, pickup, dropoff, pickup_date, dropoff_date, price }) => {
    if (!user) {
      const { isConfirmed } = await Swal.fire({
        icon: 'warning',
        title: 'กรุณาเข้าสู่ระบบ',
        text: 'กรุณา Login ก่อนจองรถเช่า',
        showCancelButton: true,
        confirmButtonText: 'เข้าสู่ระบบ',
        cancelButtonText: 'ยกเลิก',
      });
      if (isConfirmed) onSignIn?.();
      return;
    }

    // จำกัดจำนวนคนไม่ให้เกินจำนวนที่นั่งของรถ (เช่น เกิน 4 คนสำหรับรถเล็ก)
    if (passengers > (seats || 0)) {
      await Swal.fire({
        icon: 'warning',
        title: 'จำนวนผู้โดยสารเกินที่นั่ง',
        text: `รุ่นรถนี้รองรับได้สูงสุด ${seats} คน โปรดลดจำนวนผู้โดยสาร หรือเลือกรถที่นั่งได้มากกว่า`,
        confirmButtonText: 'ตกลง',
        confirmButtonColor: '#f59e0b',
      });
      return;
    }

    const nights = (() => {
      if (!pickup_date || !dropoff_date) return 1;
      const a = new Date(pickup_date);
      const b = new Date(dropoff_date);
      return Math.max(1, Math.round((b - a) / 86400000));
    })();

    const confirmHtml = `<div style="text-align:left;">
      <p style="margin:0 0 0.3rem 0;font-weight:600;color:#1565c0;">🚗 ${type || 'รถเช่า'} • นั่งได้ ${seats || 1} คน · ผู้โดยสาร ${passengers} คน</p>
      <p style="margin:0 0 0.3rem 0;color:#333;">${car_model}</p>
      <p style="margin:0 0 0.4rem 0;color:#666;">รับรถ: ${pickup} • คืนรถ: ${dropoff}</p>
      <p style="margin:0 0 0.5rem 0;color:#666;">${pickup_date} – ${dropoff_date} (${nights} วัน)</p>
      <p style="margin:0;font-size:1.1rem;">ราคารวม <strong style="color:#c62828;">${formatPriceInThb(price, 'THB')}</strong></p>
    </div>`;

    const { isConfirmed } = await Swal.fire({
      icon: 'question',
      title: 'ยืนยันจองรถเช่า',
      html: confirmHtml,
      showCancelButton: true,
      confirmButtonText: 'ยืนยันจอง',
      cancelButtonText: 'ยกเลิก',
      confirmButtonColor: '#c62828',
    });
    if (!isConfirmed) return;

    const userId = user?.user_id || user?.id;
    const segment = {
      selected_option: {
        raw_data: {
          name: car_model,
          type,
          seats,
          pickup,
          dropoff,
          pickup_date,
          dropoff_date,
        },
        price_amount: price,
        currency: 'THB',
        car_model,
      },
    };
    const plan = {
      transport: {
        car_rental: {
          segments: [segment],
        },
      },
    };
    const travelSlots = {
      origin_city: pickup,
      destination_city: dropoff,
      pickup_location: pickup,
      dropoff_location: dropoff,
      pickup_date,
      dropoff_date,
      passengers,
      nights,
      cars: [segment],
      source: 'car_rental_search',
    };

    setIsLoading(true);
    setError(null);
    try {
      await createCarBooking({
        trip_id: `car-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
        chat_id: null,
        user_id: userId,
        plan,
        travel_slots: travelSlots,
        total_price: price,
        currency: 'THB',
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
      setError(err.message);
      await Swal.fire({
        icon: 'error',
        title: 'บันทึกไม่สำเร็จ',
        text: err.message,
        confirmButtonText: 'ตกลง',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="car-rentals-page" data-theme={theme}>
      <AppHeader
        activeTab="car-rentals"
        theme={theme}
        user={user}
        onTabChange={handleTabChange}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onNavigateToHome={onNavigateToHome}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        onNavigateToBookings={onNavigateToBookings}
        onNavigateToAI={onNavigateToAI}
        onNavigateToFlights={onNavigateToFlights}
        onNavigateToHotels={onNavigateToHotels}
        onNavigateToCarRentals={onNavigateToCarRentals}
        notificationCount={notificationCount}
        notifications={notifications}
        onMarkNotificationAsRead={onMarkNotificationAsRead}
        onClearAllNotifications={onClearAllNotifications}
        isConnected={true}
      />

      <div className="car-rentals-content" data-theme={theme} data-font-size={fontSize}>
            <div className="car-rentals-search-container">
              <form className="car-rentals-search-form" onSubmit={handleSearch}>
                <div className="car-rentals-field-wrap">
                  <label className="car-rentals-field-label">สถานที่รับรถ</label>
                  <input
                    type="text"
                    className="car-rentals-input"
                    placeholder="เช่น HKT / สนามบินภูเก็ต"
                    value={pickupLocation}
                    onChange={(e) => setPickupLocation(e.target.value)}
                  />
                </div>
                <div className="car-rentals-field-wrap">
                  <label className="car-rentals-field-label">สถานที่คืนรถ</label>
                  <input
                    type="text"
                    className="car-rentals-input"
                    placeholder="คืนรถที่เดิมหรือเมืองอื่น"
                    value={dropoffLocation}
                    onChange={(e) => setDropoffLocation(e.target.value)}
                  />
                </div>
                <div className="car-rentals-field-wrap">
                  <label className="car-rentals-field-label">วันที่รับรถ</label>
                  <input
                    type="date"
                    className="car-rentals-input"
                    value={pickupDate}
                    min={todayStr}
                    onChange={(e) => setPickupDate(e.target.value)}
                  />
                </div>
                <div className="car-rentals-field-wrap">
                  <label className="car-rentals-field-label">วันที่คืนรถ</label>
                  <input
                    type="date"
                    className="car-rentals-input"
                    value={dropoffDate}
                    min={pickupDate || todayStr}
                    onChange={(e) => setDropoffDate(e.target.value)}
                  />
                </div>

                <div className="car-rentals-field-wrap car-rentals-guests-dropdown-wrap" ref={passengerDropdownRef}>
                  <label className="car-rentals-field-label">จำนวนผู้โดยสาร</label>
                  <div
                    ref={passengerTriggerRef}
                    className="car-rentals-guests-trigger"
                    onClick={() => setPassengerDropdownOpen((o) => !o)}
                    role="button"
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        setPassengerDropdownOpen((o) => !o);
                      }
                    }}
                    aria-expanded={passengerDropdownOpen}
                    aria-haspopup="dialog"
                  >
                    <span className="car-rentals-guests-trigger-icon" aria-hidden="true">👤</span>
                    <span className="car-rentals-guests-trigger-count">{passengers} คน</span>
                    <span className={`car-rentals-guests-trigger-arrow ${passengerDropdownOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
                  </div>
                  {passengerDropdownOpen && passengerPanelPosition && createPortal(
                    <div
                      ref={passengerPanelRef}
                      className="car-rentals-guests-dropdown-panel"
                      data-theme={theme}
                      role="dialog"
                      aria-label="จำนวนผู้โดยสาร"
                      style={{
                        position: 'fixed',
                        top: passengerPanelPosition.top,
                        left: passengerPanelPosition.left,
                        width: passengerPanelPosition.width,
                        minWidth: passengerPanelPosition.width,
                        maxWidth: passengerPanelPosition.width,
                      }}
                    >
                      <div className="car-rentals-guests-dropdown-row">
                        <div className="car-rentals-guests-dropdown-label">ผู้โดยสาร</div>
                        <div className="car-rentals-guests-dropdown-controls">
                          <button
                            type="button"
                            className="car-rentals-guests-btn"
                            onClick={() => setPassengers((g) => Math.max(1, g - 1))}
                            aria-label="-"
                          >
                            −
                          </button>
                          <span className="car-rentals-guests-dropdown-value">{passengers}</span>
                          <button
                            type="button"
                            className="car-rentals-guests-btn"
                            onClick={() => setPassengers((g) => Math.min(7, g + 1))}
                            aria-label="+"
                          >
                            +
                          </button>
                        </div>
                      </div>
                    </div>,
                    document.body,
                  )}
                </div>

                <div className="car-rentals-btn-wrap">
                  <span className="car-rentals-field-label car-rentals-field-label-invisible" aria-hidden="true">&#8203;</span>
                  <button type="submit" className="car-rentals-btn-search" disabled={isLoading}>
                    {isLoading ? 'กำลังค้นหา...' : 'ค้นหา'}
                  </button>
                </div>
              </form>
            </div>

            {error && (
              <div className="car-rentals-error" role="alert">
                {error}
              </div>
            )}

            {/* --- Results Section --- */}
            <div className="car-rentals-results">
              {hasSearched && !isLoading && cars.length === 0 && (
                <div className="car-rentals-no-data" role="status">
                  ไม่พบรถเช่าตรงตามเงื่อนไข
                </div>
              )}
              {cars.length > 0 && (
                <div className="car-rentals-results-count">
                  พบรถเช่า {cars.length} คัน
                </div>
              )}

              {cars.map((car, i) => {
                const name = car.name || car.vehicle?.name || 'รถเช่าคุณภาพ';
                const type = car.type || car.category || 'รถเช่า';
                const seats = car.seats || car.capacity || passengers || 1;
                const priceObj = car.price || car.offers?.[0]?.price || {};
                const total = parseFloat(priceObj.total ?? priceObj.base ?? 0) || 0;
                const transmission = car.transmission || car.gear || 'เกียร์อัตโนมัติหรือเทียบเท่า';
                const luggage = car.luggage || car.bags || 2;

                return (
                  <div key={i} className="car-rentals-result-card">
                    <div>
                      <div style={{ color: '#e67e22', fontWeight: 700, fontSize: '0.9rem', marginBottom: '4px' }}>
                        🚗 {type} • นั่งได้ {seats} คน
                      </div>
                      <h3 className="car-rentals-card-name">{name}</h3>
                      <div className="car-rentals-card-desc">
                        รับรถ: {pickupLocation || 'จุดรับรถที่เลือก'} · คืนรถ: {dropoffLocation || pickupLocation || 'จุดคืนรถที่เลือก'}
                        <br />
                        {pickupDate && dropoffDate ? `${pickupDate} – ${dropoffDate}` : 'เลือกวันที่รับ–คืนรถ'}
                        <br />
                        {transmission} • กระเป๋า {luggage} ใบ
                      </div>
                    </div>

                    <div style={{ textAlign: 'right' }}>
                      <div className="car-rentals-card-price">
                        {formatPriceInThb(total, 'THB')}
                      </div>
                      <div style={{ fontSize: '0.8rem', color: '#777', marginTop: '2px' }}>
                        ราคารวมต่อทริป
                      </div>
                      <div className="car-rentals-card-actions">
                        <button
                          type="button"
                          className="car-rentals-btn-book"
                          onClick={() => handleBookSearchResult(car)}
                          disabled={isLoading}
                        >
                          จองตอนนี้
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