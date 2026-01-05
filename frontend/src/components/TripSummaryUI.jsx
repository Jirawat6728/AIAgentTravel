import React from 'react';
import './AITravelChat.css';

function money(currency, n) {
  if (n == null || Number.isNaN(Number(n))) return null;
  const c = currency || 'THB';
  try {
    // if THB -> no decimals
    const opts = {
      style: 'currency',
      currency: c,
      maximumFractionDigits: c === 'THB' ? 0 : 2,
    };
    return new Intl.NumberFormat('th-TH', opts).format(Number(n));
  } catch {
    return `${c} ${Number(n).toLocaleString('th-TH')}`;
  }
}

function safeText(v) {
  if (v == null) return '';
  return String(v);
}

function kv(label, value) {
  const v = safeText(value).trim();
  return (
    <div className="summary-kv">
      <div className="summary-k">{label}</div>
      <div className="summary-v">{v || '—'}</div>
    </div>
  );
}

// ✅ Helper functions for formatting flight details
function getAirlineName(code) {
  if (!code) return 'Unknown';
  const airlineNames = {
    'TG': 'Thai Airways', 'FD': 'Thai AirAsia', 'SL': 'Thai Lion Air', 'PG': 'Bangkok Airways',
    'VZ': 'Thai Vietjet Air', 'WE': 'Thai Smile', 'XJ': 'Thai AirAsia X', 'DD': 'Nok Air',
    'SQ': 'Singapore Airlines', 'MH': 'Malaysia Airlines', 'CX': 'Cathay Pacific',
    'JL': 'Japan Airlines', 'NH': 'All Nippon Airways', 'KE': 'Korean Air',
  };
  return airlineNames[code] || code;
}

function formatDuration(isoDuration) {
  if (!isoDuration) return '';
  const match = isoDuration.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
  if (!match) return isoDuration;
  const hours = parseInt(match[1] || 0);
  const minutes = parseInt(match[2] || 0);
  const parts = [];
  if (hours > 0) parts.push(`${hours} ชั่วโมง`);
  if (minutes > 0) parts.push(`${minutes} นาที`);
  return parts.join(' ') || '0 นาที';
}

// ✅ แปลงวันที่จาก ISO format (2025-12-31) เป็นรูปแบบไทย (31/12/2568)
function formatThaiDate(isoDate) {
  if (!isoDate) return '';
  try {
    // Parse ISO date string (YYYY-MM-DD หรือ YYYY-MM-DDTHH:mm:ss)
    let dateStr = isoDate;
    // ถ้ามีเวลา ให้ตัดออก (ใช้แค่วันที่)
    if (dateStr.includes('T')) {
      dateStr = dateStr.split('T')[0];
    }
    
    const date = new Date(dateStr + 'T00:00:00'); // เพิ่มเวลาเพื่อหลีกเลี่ยง timezone issues
    if (isNaN(date.getTime())) return isoDate; // ถ้า parse ไม่ได้ ให้คืนค่าเดิม
    
    const day = date.getDate();
    const month = date.getMonth() + 1; // getMonth() returns 0-11
    const year = date.getFullYear() + 543; // แปลง ค.ศ. เป็น พ.ศ.
    
    return `${day}/${month}/${year}`;
  } catch (e) {
    console.error('Error formatting Thai date:', e);
    return isoDate; // ถ้าเกิด error ให้คืนค่าเดิม
  }
}

// ✅ แปลงวันที่และเวลาจาก ISO format (2025-12-31T14:30:00) เป็นรูปแบบไทย (31/12/2568 14:30)
function formatThaiDateTime(isoDateTime) {
  if (!isoDateTime) return '';
  try {
    // Parse ISO datetime string (YYYY-MM-DDTHH:mm:ss)
    const date = new Date(isoDateTime);
    if (isNaN(date.getTime())) return isoDateTime; // ถ้า parse ไม่ได้ ให้คืนค่าเดิม
    
    const day = date.getDate();
    const month = date.getMonth() + 1; // getMonth() returns 0-11
    const year = date.getFullYear() + 543; // แปลง ค.ศ. เป็น พ.ศ.
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch (e) {
    console.error('Error formatting Thai datetime:', e);
    return isoDateTime; // ถ้าเกิด error ให้คืนค่าเดิม
  }
}

export function TripSummaryCard({ plan, travelSlots }) {
  if (!plan) return null;

  const currency =
    plan?.price_breakdown?.currency ||
    plan?.currency ||
    plan?.flight?.currency ||
    plan?.hotel?.currency ||
    'THB';

  const total =
    typeof plan?.total_price === 'number'
      ? plan.total_price
      : typeof plan?.price === 'number'
        ? plan.price
        : plan?.summary?.total_price;

  const totalText = money(currency, total) || safeText(plan?.total_price_text || plan?.summary?.total_price_text);

  const origin = travelSlots?.origin_city || travelSlots?.origin || travelSlots?.origin_iata || '';
  const dest = travelSlots?.destination_city || travelSlots?.destination || travelSlots?.destination_iata || '';
  const dateGo = travelSlots?.departure_date || travelSlots?.start_date || '';
  
  // ✅ คำนวณวันกลับถ้ายังไม่มี
  let dateBack = travelSlots?.return_date || travelSlots?.end_date || '';
  if (!dateBack && dateGo && travelSlots?.nights != null) {
    try {
      const startDate = new Date(dateGo);
      const nights = parseInt(travelSlots.nights) || 0;
      const returnDate = new Date(startDate);
      returnDate.setDate(returnDate.getDate() + nights);
      dateBack = returnDate.toISOString().split('T')[0]; // ✅ แปลงเป็น YYYY-MM-DD
    } catch (e) {
      console.error('Error calculating return date:', e);
    }
  }
  
  const pax = [
    travelSlots?.adults != null ? `ผู้ใหญ่ ${travelSlots.adults}` : null,
    travelSlots?.children != null ? `เด็ก ${travelSlots.children}` : null,
    travelSlots?.infants != null ? `ทารก ${travelSlots.infants}` : null,
  ].filter(Boolean).join(' • ');

  const badgeLabel = plan?.badge?.label || plan?.label || 'ตัวเลือกที่เลือก';
  const title = plan?.title ? plan.title : `✅ เลือกช้อยส์ ${plan?.id ?? ''} — ${badgeLabel}`;

  // ✅ Extract flight details
  const flight = plan?.flight || {};
  const flightSegments = flight?.segments || [];
  const firstSegment = flightSegments[0];
  const lastSegment = flightSegments[flightSegments.length - 1];
  
  // ✅ Extract hotel details
  const hotel = plan?.hotel || {};
  const hotelSegments = hotel?.segments || [];
  
  // ✅ Extract transport details
  const transport = plan?.transport || {};
  const transportSegments = transport?.segments || [];

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">{title}</span>
          <span className="plan-card-tag">สรุปทริป</span>
        </div>
      </div>

      {/* Overview */}
      <div className="plan-card-section">
        <div className="plan-card-section-title">🧾 ภาพรวม</div>
        <div className="plan-card-section-body">
          {kv('ต้นทาง → ปลายทาง', origin && dest ? `${origin} → ${dest}` : '')}
          {kv('วันเดินทาง', formatThaiDate(dateGo))}
          {kv('วันกลับ', formatThaiDate(dateBack))}
          {kv('ผู้โดยสาร', pax)}
        </div>
      </div>

      {/* Flight Details */}
      {firstSegment && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {firstSegment.carrier && kv('สายการบิน', getAirlineName(firstSegment.carrier))}
            {firstSegment.number && kv('เลขเที่ยวบิน', `${firstSegment.carrier || ''}${firstSegment.number}`)}
            {firstSegment.from && lastSegment.to && kv('เส้นทาง', `${firstSegment.from} → ${lastSegment.to}`)}
            {firstSegment.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstSegment.departure))}
            {lastSegment.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastSegment.arrival))}
            {flight.total_duration_sec && kv('ระยะเวลาบิน', formatDuration(flight.total_duration))}
            {flight.is_non_stop !== undefined && kv('บินตรง', flight.is_non_stop ? 'ใช่' : `แวะ ${flight.num_stops || 0} ครั้ง`)}
            {flight.currency && flight.total_price && kv('ราคาไฟท์บิน', money(flight.currency, flight.total_price))}
          </div>
        </div>
      )}

      {/* Hotel Details */}
      {(hotelSegments.length > 0 || hotel.hotelName) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🏨 ที่พัก</div>
          <div className="plan-card-section-body">
            {hotelSegments.length > 0 ? (
              (() => {
                // ✅ Group hotel segments by hotelName and cityCode to avoid duplicates
                const groupedHotels = {};
                hotelSegments.forEach((seg) => {
                  // Use hotelName + cityCode as key to group properly
                  const key = `${seg.hotelName || 'Unknown'}-${seg.cityCode || seg.city || ''}`;
                  if (!groupedHotels[key]) {
                    groupedHotels[key] = {
                      hotelName: seg.hotelName,
                      hotelId: seg.hotelId,
                      city: seg.city || seg.cityCode,
                      address: seg.address,
                      boardType: seg.boardType,
                      currency: seg.currency || currency,
                      nights: 0,
                      price_total: 0,
                      segments: []
                    };
                  }
                  // Sum up nights and prices
                  groupedHotels[key].nights += (seg.nights || 0);
                  const segPrice = seg.price_total || seg.price || 0;
                  if (segPrice) {
                    groupedHotels[key].price_total += segPrice;
                  }
                  groupedHotels[key].segments.push(seg);
                });
                
                // ✅ Display grouped hotels (only unique hotels)
                const uniqueHotels = Object.values(groupedHotels);
                return uniqueHotels.map((grouped, idx) => (
                  <div key={idx} style={{ marginBottom: idx < uniqueHotels.length - 1 ? '12px' : '0' }}>
                    {grouped.city && kv('เมือง', grouped.city)}
                    {grouped.hotelName && kv('ชื่อโรงแรม', grouped.hotelName)}
                    {grouped.nights > 0 && kv('จำนวนคืน', `${grouped.nights} คืน`)}
                    {grouped.boardType && kv('ประเภทอาหาร', grouped.boardType)}
                    {grouped.address && kv('ที่อยู่', grouped.address)}
                    {grouped.price_total > 0 && kv('ราคา', money(grouped.currency, grouped.price_total))}
                  </div>
                ));
              })()
            ) : (
              <>
                {hotel.hotelName && kv('ชื่อโรงแรม', hotel.hotelName)}
                {hotel.nights != null && kv('จำนวนคืน', `${hotel.nights} คืน`)}
                {hotel.boardType && kv('ประเภทอาหาร', hotel.boardType)}
                {hotel.address && kv('ที่อยู่', hotel.address)}
                {hotel.price_total && kv('ราคา', money(hotel.currency || currency, hotel.price_total))}
                {hotel.price && !hotel.price_total && kv('ราคา', money(hotel.currency || currency, hotel.price))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Transport Details */}
      {(transportSegments.length > 0 || transport.type) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 การเดินทาง</div>
          <div className="plan-card-section-body">
            {transportSegments.length > 0 ? (
              transportSegments.map((seg, idx) => (
                <div key={idx} style={{ marginBottom: idx < transportSegments.length - 1 ? '12px' : '0' }}>
                  {seg.type && kv(`ประเภท (${idx + 1})`, seg.type)}
                  {seg.route && kv('เส้นทาง', seg.route)}
                  {seg.duration && kv('ระยะเวลา', seg.duration)}
                  {seg.price && kv('ราคา', money(seg.currency || currency, seg.price))}
                </div>
              ))
            ) : (
              <>
                {transport.type && kv('ประเภท', transport.type)}
                {transport.route && kv('เส้นทาง', transport.route)}
                {transport.duration && kv('ระยะเวลา', transport.duration)}
                {transport.price && kv('ราคา', money(transport.currency || currency, transport.price))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Price Breakdown */}
      {plan?.price_breakdown && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">💰 รายละเอียดราคา</div>
          <div className="plan-card-section-body">
            {plan.price_breakdown.flight && kv('ไฟท์บิน', money(currency, plan.price_breakdown.flight))}
            {plan.price_breakdown.hotel && kv('ที่พัก', money(currency, plan.price_breakdown.hotel))}
            {plan.price_breakdown.transport && kv('การเดินทาง', money(currency, plan.price_breakdown.transport))}
            {plan.price_breakdown.car && kv('รถเช่า', money(currency, plan.price_breakdown.car))}
          </div>
        </div>
      )}

      {/* Total Price */}
      <div className="plan-card-footer">
        <div className="plan-card-price">{totalText || '—'}</div>
        <div className="summary-note">ราคาอ้างอิงจาก Amadeus Search (production)</div>
      </div>
    </div>
  );
}

// EditSectionCard removed - users can now type directly in chat

export function UserInfoCard({ userProfile, onEdit }) {
  const hasRequiredInfo = userProfile && (
    userProfile.first_name && 
    userProfile.last_name && 
    userProfile.email && 
    userProfile.phone
  );

  const hasPassportInfo = userProfile && (
    userProfile.passport_no && 
    userProfile.passport_expiry && 
    userProfile.nationality
  );

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">👤 ข้อมูลผู้ใช้สำหรับการจอง</span>
          <span className="plan-card-tag">
            {hasRequiredInfo && hasPassportInfo ? 'พร้อมจอง' : 'กรุณากรอกข้อมูล'}
          </span>
        </div>
      </div>

      {!userProfile ? (
        <div className="plan-card-section">
          <div className="plan-card-section-body plan-card-small">
            <div>⚠️ ยังไม่ได้กรอกข้อมูลผู้ใช้</div>
            <div style={{ marginTop: '8px' }}>
              กรุณากรอกข้อมูลก่อนยืนยันจอง (ชื่อ, นามสกุล, อีเมล, เบอร์โทร, พาสปอร์ต)
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="plan-card-section">
            <div className="plan-card-section-title">ข้อมูลพื้นฐาน</div>
            <div className="plan-card-section-body">
              {kv('ชื่อ', userProfile.first_name || '—')}
              {kv('นามสกุล', userProfile.last_name || '—')}
              {kv('อีเมล', userProfile.email || '—')}
              {kv('เบอร์โทร', userProfile.phone || '—')}
              {kv('วันเกิด', userProfile.dob || '—')}
              {kv('เพศ', userProfile.gender || '—')}
            </div>
          </div>

          <div className="plan-card-section">
            <div className="plan-card-section-title">ข้อมูลพาสปอร์ต</div>
            <div className="plan-card-section-body">
              {kv('เลขพาสปอร์ต', userProfile.passport_no || '—')}
              {kv('วันหมดอายุ', userProfile.passport_expiry || '—')}
              {kv('สัญชาติ', userProfile.nationality || '—')}
            </div>
            {!hasPassportInfo && (
              <div className="plan-card-small" style={{ marginTop: '8px', opacity: 0.8 }}>
                ⚠️ ข้อมูลพาสปอร์ตยังไม่ครบ
              </div>
            )}
          </div>

          {onEdit && (
            <div className="plan-card-footer summary-footer">
              <button className="plan-card-button" onClick={onEdit}>
                ✏️ แก้ไขข้อมูล
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function ConfirmBookingCard({ canBook, onConfirm, onPayment, note, isBooking, bookingResult }) {
  const needsPayment = bookingResult?.needs_payment || bookingResult?.status === 'pending_payment';
  const isConfirmed = bookingResult?.status === 'confirmed' || bookingResult?.status === 'paid';
  
  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">✅ ยืนยันจอง</span>
          <span className="plan-card-tag">
            {needsPayment ? 'รอชำระเงิน' : isConfirmed ? 'จองสำเร็จ' : 'Sandbox'}
          </span>
        </div>
      </div>

      {isBooking ? (
        <div className="plan-card-section">
          <div className="plan-card-section-body plan-card-small">
            <div>⏳ กำลังดำเนินการ...</div>
            <div style={{ marginTop: '8px', opacity: 0.8 }}>
              {needsPayment ? 'กำลังสร้างการจอง...' : 'กำลังชำระเงินและจอง...'}
            </div>
          </div>
        </div>
      ) : bookingResult ? (
        <div className="plan-card-section">
          <div className="plan-card-section-title">
            {bookingResult.ok ? (needsPayment ? '✅ สร้างการจองสำเร็จ' : '✅ จองสำเร็จ') : '❌ ไม่สำเร็จ'}
          </div>
          <div className="plan-card-section-body plan-card-small">
            {bookingResult.message && (
              <div>{typeof bookingResult.message === 'string' ? bookingResult.message : JSON.stringify(bookingResult.message)}</div>
            )}
            
            {needsPayment && bookingResult.total_price && (
              <div style={{ marginTop: '12px', padding: '12px', background: '#f0f9ff', borderRadius: '8px' }}>
                <div style={{ fontWeight: 600, marginBottom: '8px' }}>💰 ราคารวม</div>
                <div style={{ fontSize: '20px', fontWeight: 700, color: '#1e40af' }}>
                  {new Intl.NumberFormat('th-TH', { style: 'currency', currency: bookingResult.currency || 'THB', minimumFractionDigits: 0 }).format(bookingResult.total_price)}
                </div>
              </div>
            )}
            
            {bookingResult.booking_reference && (
              <div style={{ marginTop: '12px' }}>
                <strong>📋 หมายเลขการจอง:</strong> {bookingResult.booking_reference}
              </div>
            )}
            
            {bookingResult.detail && (
              <div style={{ marginTop: '8px', opacity: 0.8 }}>
                {typeof bookingResult.detail === 'string' 
                  ? bookingResult.detail 
                  : JSON.stringify(bookingResult.detail)}
              </div>
            )}
            
            {needsPayment && bookingResult.booking_id && onPayment && (
              <div className="plan-card-footer summary-footer" style={{ marginTop: '16px' }}>
                <button
                  className="plan-card-button"
                  style={{ background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}
                  onClick={() => onPayment(bookingResult.booking_id)}
                  disabled={isBooking}
                >
                  💳 ชำระเงินและยืนยันจอง
                </button>
              </div>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="plan-card-section">
            <div className="plan-card-section-title">ความปลอดภัย</div>
            <div className="plan-card-section-body plan-card-small">
              <div>🔒 ระบบล็อกให้จองได้เฉพาะ Amadeus Sandbox (test) เท่านั้น</div>
              <div style={{ marginTop: '8px' }}>
                ⚠️ การจองนี้เป็นการทดสอบเท่านั้น ไม่ใช่การจองจริง
              </div>
              {note && <div className="plan-card-small" style={{ marginTop: '8px' }}>{note}</div>}
            </div>
          </div>

          <div className="plan-card-footer summary-footer">
            <button
              className={`plan-card-button ${!canBook ? 'summary-disabled' : ''}`}
              disabled={!canBook || isBooking}
              onClick={onConfirm}
            >
              ✅ ยืนยันจองใน Sandbox
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ✅ Final Trip Summary - สรุปครบถ้วนก่อนจอง
export function FinalTripSummary({ plan, travelSlots, userProfile }) {
  if (!plan) return null;

  const flight = plan.flight || {};
  const hotel = plan.hotel || {};
  const transport = plan.transport || {};
  const currency = plan.currency || 'THB';
  const totalPrice = plan.total_price || 0;

  const flightSegments = flight.segments || [];
  const hotelSegments = hotel.segments || [];
  const transportSegments = transport.segments || [];

  // Format dates
  const startDate = formatThaiDate(travelSlots?.start_date);
  const returnDate = formatThaiDate(travelSlots?.return_date || travelSlots?.end_date);
  const nights = travelSlots?.nights || 0;
  const adults = travelSlots?.adults || 1;
  const children = travelSlots?.children || 0;

  return (
    <div className="plan-card plan-card-final-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">📋 สรุปทริปสุดท้าย</span>
          <span className="plan-card-tag final-summary-tag">พร้อมจอง</span>
        </div>
      </div>

      {/* Trip Overview */}
      <div className="plan-card-section">
        <div className="plan-card-section-title">🎯 ข้อมูลทริป</div>
        <div className="plan-card-section-body">
          {travelSlots?.origin && travelSlots?.destination && kv('เส้นทาง', `${travelSlots.origin} → ${travelSlots.destination}`)}
          {startDate && kv('วันเดินทาง', startDate)}
          {returnDate && kv('วันกลับ', returnDate)}
          {nights > 0 && kv('จำนวนคืน', `${nights} คืน`)}
          {adults > 0 && kv('ผู้ใหญ่', `${adults} คน`)}
          {children > 0 && kv('เด็ก', `${children} คน`)}
        </div>
      </div>

      {/* Flight Details */}
      {flightSegments.length > 0 && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {flightSegments.map((seg, idx) => (
              <div key={idx} style={{ marginBottom: idx < flightSegments.length - 1 ? '12px' : '0' }}>
                {seg.from && seg.to && kv(`เส้นทาง (${idx + 1})`, `${seg.from} → ${seg.to}`)}
                {seg.departure && kv('วัน-เวลาออก', formatThaiDateTime(seg.departure))}
                {seg.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(seg.arrival))}
                {seg.carrier && kv('สายการบิน', getAirlineName(seg.carrier))}
                {seg.duration && kv('ระยะเวลา', formatDuration(seg.duration))}
              </div>
            ))}
            {flight.total_price && kv('ราคา', money(currency, flight.total_price))}
          </div>
        </div>
      )}

      {/* Hotel Details */}
      {(hotelSegments.length > 0 || hotel.hotelName) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🏨 ที่พัก</div>
          <div className="plan-card-section-body">
            {hotelSegments.length > 0 ? (
              hotelSegments.map((seg, idx) => (
                <div key={idx} style={{ marginBottom: idx < hotelSegments.length - 1 ? '12px' : '0' }}>
                  {seg.city && kv(`เมือง (${idx + 1})`, seg.city)}
                  {seg.hotelName && kv('ชื่อโรงแรม', seg.hotelName)}
                  {seg.nights && kv('จำนวนคืน', `${seg.nights} คืน`)}
                  {seg.boardType && kv('ประเภทอาหาร', seg.boardType)}
                  {seg.address && kv('ที่อยู่', seg.address)}
                  {seg.price && kv('ราคา', money(seg.currency || currency, seg.price))}
                </div>
              ))
            ) : (
              <>
                {hotel.hotelName && kv('ชื่อโรงแรม', hotel.hotelName)}
                {hotel.city && kv('เมือง', hotel.city)}
                {hotel.nights && kv('จำนวนคืน', `${hotel.nights} คืน`)}
                {hotel.boardType && kv('ประเภทอาหาร', hotel.boardType)}
                {hotel.address && kv('ที่อยู่', hotel.address)}
                {hotel.total_price && kv('ราคา', money(currency, hotel.total_price))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Transport Details */}
      {(transportSegments.length > 0 || transport.type) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 การเดินทาง</div>
          <div className="plan-card-section-body">
            {transportSegments.length > 0 ? (
              transportSegments.map((seg, idx) => (
                <div key={idx} style={{ marginBottom: idx < transportSegments.length - 1 ? '12px' : '0' }}>
                  {seg.type && kv(`ประเภท (${idx + 1})`, seg.type)}
                  {seg.route && kv('เส้นทาง', seg.route)}
                  {seg.duration && kv('ระยะเวลา', seg.duration)}
                  {seg.price && kv('ราคา', money(seg.currency || currency, seg.price))}
                </div>
              ))
            ) : (
              <>
                {transport.type && kv('ประเภท', transport.type)}
                {transport.route && kv('เส้นทาง', transport.route)}
                {transport.duration && kv('ระยะเวลา', transport.duration)}
                {transport.price && kv('ราคา', money(currency, transport.price))}
              </>
            )}
          </div>
        </div>
      )}

      {/* Price Breakdown */}
      {plan.price_breakdown && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">💰 รายละเอียดราคา</div>
          <div className="plan-card-section-body">
            {plan.price_breakdown.flight && kv('ไฟท์บิน', money(currency, plan.price_breakdown.flight))}
            {plan.price_breakdown.hotel && kv('ที่พัก', money(currency, plan.price_breakdown.hotel))}
            {plan.price_breakdown.transport && kv('การเดินทาง', money(currency, plan.price_breakdown.transport))}
            {plan.price_breakdown.car && kv('รถเช่า', money(currency, plan.price_breakdown.car))}
          </div>
        </div>
      )}

      {/* User Info Summary */}
      {userProfile && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">👤 ข้อมูลผู้จอง</div>
          <div className="plan-card-section-body">
            {userProfile.first_name && userProfile.last_name && kv('ชื่อ-นามสกุล', `${userProfile.first_name} ${userProfile.last_name}`)}
            {userProfile.email && kv('อีเมล', userProfile.email)}
            {userProfile.phone && kv('เบอร์โทรศัพท์', userProfile.phone)}
            {userProfile.passport_no && kv('เลขพาสปอร์ต', userProfile.passport_no)}
          </div>
        </div>
      )}

      {/* Total Price */}
      <div className="plan-card-footer">
        <div className="plan-card-price-final">
          <div className="plan-card-price-label">ราคารวมทั้งหมด</div>
          <div className="plan-card-price-value">{money(currency, totalPrice)}</div>
        </div>
        <div className="summary-note">ราคาอ้างอิงจาก Amadeus Search (production)</div>
      </div>
    </div>
  );
}
