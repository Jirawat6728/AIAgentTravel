import React, { useState } from 'react';
import Swal from 'sweetalert2';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import { useFontSize } from '../../context/FontSizeContext';
import { useLanguage } from '../../context/LanguageContext';
import './FlightsPage.css';

export default function FlightsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHotels, onNavigateToCarRentals, onNavigateToHome = null, onNavigateToProfile = null, onNavigateToSettings = null }) {
  const theme = useTheme();
  const { t } = useLanguage();
  const fontSize = useFontSize();
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [flights, setFlights] = useState([]);

  // วันที่น้อยที่สุดที่เลือกได้ = วันนี้ (ห้ามเลือกวันที่ผ่านมาแล้ว) ใช้เวลา local
  const todayStr = React.useMemo(() => {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  }, []);

  // ฟังก์ชันแปลงเวลาให้อ่านง่าย
  const formatTime = (isoStr) => {
    if (!isoStr) return '--:--';
    return new Date(isoStr).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  // --- 1. ค้นหา: ใช้พารามิเตอร์ departure_date ตามรูป image_61207d ---
  const handleSearch = async (e) => {
    e.preventDefault();
    const originTrim = (origin || '').trim();
    const destTrim = (destination || '').trim();
    if (!originTrim || !destTrim || !date) {
      alert("กรุณากรอกต้นทาง ปลายทาง และวันที่เดินทาง");
      return;
    }
    if (date < todayStr) {
      alert("กรุณาเลือกวันที่เดินทางเป็นวันนี้หรือวันถัดไป (ไม่สามารถเลือกวันที่ผ่านมาแล้ว)");
      return;
    }
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      // Backend รองรับชื่อเมือง (เช่น กรุงเทพ โตเกียว) และรหัส IATA (BKK, NRT) — จะแปลงชื่อเมืองเป็นรหัสให้
      const params = new URLSearchParams({ origin: originTrim, destination: destTrim, departure_date: date });
      
      const response = await fetch(`${baseUrl}/api/mcp/search/flights?${params.toString()}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });

      const resData = await response.json();
      if (!response.ok) {
        const errMsg = typeof resData.detail === 'string'
          ? resData.detail
          : (resData.detail?.[0]?.msg || resData.detail?.msg);
        throw new Error(errMsg || "ค้นหาไม่สำเร็จ");
      }

      // ดึงจากฟิลด์ flights ตามที่สำเร็จใน image_612c1a.jpg (รูปแบบ Amadeus: itineraries, price)
      setFlights(resData.flights || []);
    } catch (err) {
      alert("Search Error: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 2. จอง: ใช้ /api/booking/create ให้ตรงกับ AITravelChat (ไม่ใช้ MCP save_booking ที่ไม่มีใน backend) ---
  const handleBooking = async (f) => {
    if (!user) {
      const { isConfirmed } = await Swal.fire({
        icon: 'warning',
        title: 'กรุณาเข้าสู่ระบบ',
        text: 'กรุณา Login ก่อนจองเที่ยวบิน',
        showCancelButton: true,
        confirmButtonText: 'เข้าสู่ระบบ',
        cancelButtonText: 'ยกเลิก'
      });
      if (isConfirmed) onSignIn?.();
      return;
    }

    const seg = f.itineraries[0].segments[0];
    const depTime = formatTime(seg.departure?.at);
    const arrTime = formatTime(seg.arrival?.at);
    const { isConfirmed } = await Swal.fire({
      icon: 'question',
      title: 'ยืนยันการจอง',
      html: `<p style="margin: 0 0 0.5rem 0;">เที่ยวบิน <strong>${seg.carrierCode} ${seg.number}</strong></p>
             <p style="margin: 0 0 0.5rem 0; color: #666;">${depTime} → ${arrTime}</p>
             <p style="margin: 0; font-size: 1.1rem;">ราคา <strong style="color: #c62828;">฿${parseFloat(f.price?.total || 0).toLocaleString()}</strong></p>`,
      showCancelButton: true,
      confirmButtonText: 'ยืนยันจอง',
      cancelButtonText: 'ยกเลิก',
      confirmButtonColor: '#c62828'
    });
    if (!isConfirmed) return;

    setIsLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const userId = user?.user_id || user?.id;
      const tripId = `flight-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

      // โครงสร้าง plan/travel_slots ให้สอดคล้องกับ AITravelChat และ backend chat API
      const plan = {
        travel: {
          flights: {
            outbound: [{
              selected_option: {
                raw_data: f,
                price_amount: parseFloat(f.price?.total) || 0,
                currency: f.price?.currency || "THB"
              }
            }],
            inbound: []
          }
        }
      };
      const travelSlots = {
        origin_city: origin,
        destination_city: destination,
        departure_date: date,
        adults: 1
      };
      const payload = {
        trip_id: tripId,
        chat_id: null,
        user_id: userId,
        plan,
        travel_slots: travelSlots,
        total_price: parseFloat(f.price?.total) || 0,
        currency: f.price?.currency || "THB",
        mode: "normal"
      };

      const response = await fetch(`${baseUrl}/api/booking/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userId ? { 'X-User-ID': userId } : {})
        },
        credentials: 'include',
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (response.ok && data?.booking_id) {
        await Swal.fire({
          icon: 'success',
          title: 'จองสำเร็จ',
          text: 'ข้อมูลบันทึกลงระบบเรียบร้อยแล้ว คุณสามารถชำระเงินได้ที่ การจองของฉัน',
          confirmButtonText: 'ไปที่การจองของฉัน',
          confirmButtonColor: '#1565c0'
        });
        onNavigateToBookings?.();
      } else {
        const errMsg = typeof data?.detail === 'string' ? data.detail : (data?.detail?.[0]?.msg || data?.message);
        await Swal.fire({
          icon: 'error',
          title: 'บันทึกไม่สำเร็จ',
          text: errMsg || 'Invalid request format',
          confirmButtonText: 'ตกลง'
        });
      }
    } catch (err) {
      await Swal.fire({
        icon: 'error',
        title: 'เกิดข้อผิดพลาด',
        text: err.message,
        confirmButtonText: 'ตกลง'
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flights-page">
      <AppHeader
        activeTab="flights"
        user={user}
        onTabChange={(tab) => {
          if (tab === 'bookings') onNavigateToBookings?.();
          else if (tab === 'ai') onNavigateToAI?.();
          else if (tab === 'hotels') onNavigateToHotels?.();
          else if (tab === 'car-rentals') onNavigateToCarRentals?.();
        }}
        onLogout={onLogout}
        onSignIn={onSignIn}
        onNavigateToHome={onNavigateToHome}
        onNavigateToProfile={onNavigateToProfile}
        onNavigateToSettings={onNavigateToSettings}
        isConnected={true}
      />
      <div className="flights-content" data-theme={theme} data-font-size={fontSize}>
        <div className="flights-hero">
          <h1>{t('flights.title')}</h1>
          <p className="flights-hero-desc">{t('flights.subtitle')}</p>
        </div>
        <div className="flights-search-container">
          <form className="flights-search-form" onSubmit={handleSearch}>
            <input
              type="text"
              className="flights-input"
              placeholder={t('flights.origin')}
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              aria-label={t('flights.origin')}
            />
            <input
              type="text"
              className="flights-input"
              placeholder={t('flights.destination')}
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              aria-label={t('flights.destination')}
            />
            <div className="flights-input-date-wrap" aria-label={t('flights.date')}>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                min={todayStr}
                aria-label={t('flights.date')}
                title={t('flights.date')}
              />
              <span className="flights-calendar-icon" aria-hidden="true">📅</span>
            </div>
            <button type="submit" className="flights-btn-search" disabled={isLoading}>
              {isLoading ? t('flights.searching') : t('flights.search')}
            </button>
          </form>

          <div className="flights-results">
            {flights.map((f, i) => (
              <div key={i} className="flights-result-card">
                <div>
                  <div className="flight-code">
                    {f.itineraries[0].segments[0].carrierCode} {f.itineraries[0].segments[0].number}
                  </div>
                  <div className="flight-times">
                    {formatTime(f.itineraries[0].segments[0].departure.at)} ➔ {formatTime(f.itineraries[0].segments[0].arrival.at)}
                  </div>
                  <div className="flight-route">
                    {origin} ({f.itineraries[0].segments[0].departure.iataCode}) → {destination} ({f.itineraries[0].segments[0].arrival.iataCode})
                  </div>
                </div>
                <div className="flight-price-wrap">
                  <div className="flight-price">฿{parseFloat(f.price.total).toLocaleString()}</div>
                  <button type="button" className="flights-btn-book" onClick={() => handleBooking(f)}>
                    {t('flights.bookNow')}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}