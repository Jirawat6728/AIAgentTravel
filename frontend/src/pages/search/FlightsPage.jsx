import React, { useState } from 'react';
import AppHeader from '../../components/common/AppHeader';
import { useTheme } from '../../context/ThemeContext';
import './FlightsPage.css';

export default function FlightsPage({ user, onLogout, onSignIn, onNavigateToBookings, onNavigateToAI, onNavigateToFlights, onNavigateToHome = null }) {
  const theme = useTheme();
  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [date, setDate] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [flights, setFlights] = useState([]);

  // ฟังก์ชันแปลงเวลาให้อ่านง่าย
  const formatTime = (isoStr) => {
    if (!isoStr) return '--:--';
    return new Date(isoStr).toLocaleTimeString('th-TH', { hour: '2-digit', minute: '2-digit', hour12: false });
  };

  // --- 1. ค้นหา: ใช้พารามิเตอร์ departure_date ตามรูป image_61207d ---
  const handleSearch = async (e) => {
    e.preventDefault();
    if (!origin || !destination || !date) {
      alert("กรุณากรอกข้อมูลให้ครบถ้วน");
      return;
    }
    setIsLoading(true);
    setError(null);

    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      // 🎯 ต้องใช้ชื่อ departure_date ตามหลักฐานใน image_61207d.png
      const params = new URLSearchParams({ origin, destination, departure_date: date });
      
      const response = await fetch(`${baseUrl}/api/mcp/search/flights?${params.toString()}`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });

      const resData = await response.json();
      if (!response.ok) throw new Error(resData.detail?.[0]?.msg || "ค้นหาไม่สำเร็จ");

      // ดึงจากฟิลด์ flights ตามที่สำเร็จใน image_612c1a.jpg
      setFlights(resData.flights || []);
    } catch (err) {
      alert("Search Error: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  // --- 2. 🎯 จอง: ปรับโครงสร้าง Arguments ให้ "แบน (Flat)" เพื่อเลิก Validation Error ---
  const handleBooking = async (f) => {
    if (!user) { alert("กรุณา Login ก่อนจอง"); onSignIn?.(); return; }

    const seg = f.itineraries[0].segments[0];
    if (!window.confirm(`ยืนยันการจอง ${seg.carrierCode}${seg.number} ราคา ฿${f.price.total}?`)) return;

    setIsLoading(true);
    try {
      const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      
      // 📦 ปรับ arguments ให้ชั้นเดียว ไม่ซ้อน Object เพื่อลดความผิดพลาด
      const payload = {
        tool: "save_booking",
        arguments: {
          user_email: user.email,
          booking_type: "flight",
          origin: origin,
          destination: destination,
          flight_number: `${seg.carrierCode}${seg.number}`,
          departure_time: seg.departure.at,
          arrival_time: seg.arrival.at,
          price: parseFloat(f.price.total),
          currency: f.price.currency || "THB"
        }
      };

      const response = await fetch(`${baseUrl}/api/mcp/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (response.ok) {
        alert("🎉 สำเร็จ! ข้อมูลบันทึกลง Database เรียบร้อยแล้ว");
        onNavigateToBookings?.();
      } else {
        console.error("Debug Error:", result);
        alert("❌ บันทึกไม่สำเร็จ: " + (result.error || result.message || "Invalid request format"));
      }
    } catch (err) {
      alert("❌ Error: " + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flights-page">
      <AppHeader activeTab="flights" user={user} onTabChange={(tab) => tab === 'bookings' && onNavigateToBookings()} onLogout={onLogout} onSignIn={onSignIn} isConnected={true} />
      <div className="flights-content" data-theme={theme}>
        <div className="flights-hero" style={{ padding: '40px', textAlign: 'center' }}><h1>ค้นหาเที่ยวบิน</h1></div>
        <div className="search-container" style={{ maxWidth: '900px', margin: '0 auto', padding: '20px' }}>
          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '10px', justifyContent: 'center', backgroundColor: '#fff', padding: '20px', borderRadius: '15px', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }}>
            <input type="text" placeholder="BKK" value={origin} onChange={(e) => setOrigin(e.target.value.toUpperCase())} style={{ padding: '10px', width: '100px', borderRadius: '8px', border: '1px solid #ddd' }} />
            <input type="text" placeholder="CNX" value={destination} onChange={(e) => setDestination(e.target.value.toUpperCase())} style={{ padding: '10px', width: '100px', borderRadius: '8px', border: '1px solid #ddd' }} />
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} style={{ padding: '10px', borderRadius: '8px', border: '1px solid #ddd' }} />
            <button type="submit" disabled={isLoading} style={{ padding: '10px 20px', backgroundColor: '#0066cc', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
              {isLoading ? 'กำลังค้นหา...' : 'ค้นหา'}
            </button>
          </form>

          <div className="results" style={{ marginTop: '30px' }}>
            {flights.map((f, i) => (
              <div key={i} style={{ backgroundColor: '#fff', padding: '20px', marginBottom: '15px', borderRadius: '12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.05)' }}>
                <div>
                  <div style={{ fontWeight: 'bold', color: '#0066cc' }}>{f.itineraries[0].segments[0].carrierCode} {f.itineraries[0].segments[0].number}</div>
                  <div style={{ fontSize: '20px', fontWeight: 'bold', margin: '10px 0' }}>
                    {formatTime(f.itineraries[0].segments[0].departure.at)} ➔ {formatTime(f.itineraries[0].segments[0].arrival.at)}
                  </div>
                  <div style={{ color: '#888', fontSize: '12px' }}>{origin} ({f.itineraries[0].segments[0].departure.iataCode}) - {destination} ({f.itineraries[0].segments[0].arrival.iataCode})</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#ff4d4f' }}>฿{parseFloat(f.price.total).toLocaleString()}</div>
                  <button onClick={() => handleBooking(f)} style={{ marginTop: '10px', padding: '8px 20px', backgroundColor: '#ff4d4f', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>จองตอนนี้</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}