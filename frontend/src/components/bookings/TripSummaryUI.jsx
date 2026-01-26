import React from 'react';
import './PlanChoiceCard.css';
import './TripSummaryUI.css';

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
    'TW': "T'way Air",
    'SQ': 'Singapore Airlines', 'MH': 'Malaysia Airlines', 'CX': 'Cathay Pacific',
    'JL': 'Japan Airlines', 'NH': 'All Nippon Airways', 'KE': 'Korean Air',
  };
  return airlineNames[code] || code;
}

// ✅ ดึง airline logo จาก CDN - หลายแหล่งข้อมูล
function getAirlineLogoUrl(carrierCode, attempt = 1) {
  if (!carrierCode) return null;
  
  const code = carrierCode.toUpperCase();
  
  switch (attempt) {
    case 1:
      return `https://logos.skyscnr.com/images/airlines/favicon/${code}.png`;
    case 2:
      return `https://avicon.io/api/airlines/${code}`;
    case 3:
      return `https://www.airlinecodes.info/airline-logos/${code}.png`;
    case 4:
      return `https://d1yjjnpx0p53s8.cloudfront.net/images/airlines/${code}.png`;
    case 5:
      return `https://pics.avs.io/200/200/${code}.png`;
    default:
      return null;
  }
}

// ✅ Component สำหรับแสดง airline logo พร้อม fallback
function AirlineLogo({ carrierCode, size = 32, style = {} }) {
  const [logoAttempt, setLogoAttempt] = React.useState(1);
  const [logoError, setLogoError] = React.useState(false);
  const [currentUrl, setCurrentUrl] = React.useState(null);
  
  React.useEffect(() => {
    if (carrierCode) {
      setLogoAttempt(1);
      setLogoError(false);
      setCurrentUrl(getAirlineLogoUrl(carrierCode, 1));
    }
  }, [carrierCode]);
  
  const handleImageError = () => {
    if (logoAttempt < 5) {
      const nextAttempt = logoAttempt + 1;
      setLogoAttempt(nextAttempt);
      setCurrentUrl(getAirlineLogoUrl(carrierCode, nextAttempt));
    } else {
      setLogoError(true);
    }
  };
  
  if (!carrierCode || logoError || !currentUrl) {
    return (
      <div style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '6px',
        background: 'rgba(255, 255, 255, 0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: `${Math.max(10, size * 0.35)}px`,
        fontWeight: '600',
        color: '#fff',
        ...style
      }}>
        {carrierCode || 'N/A'}
      </div>
    );
  }
  
  return (
    <img
      src={currentUrl}
      alt={`${carrierCode} logo`}
      style={{
        width: `${size}px`,
        height: `${size}px`,
        borderRadius: '6px',
        objectFit: 'contain',
        background: 'rgba(255, 255, 255, 0.05)',
        padding: '4px',
        ...style
      }}
      onError={handleImageError}
      onLoad={() => {
        if (logoError) setLogoError(false);
      }}
    />
  );
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

export function TripSummaryCard({ plan, travelSlots, cachedOptions, cacheValidation, workflowValidation }) {
  if (!plan) return null;
  
  // ✅ แสดง validation status ถ้ามี
  const showValidation = cacheValidation && !cacheValidation.valid;
  const validationIssues = cacheValidation?.issues || [];
  const validationWarnings = cacheValidation?.warnings || [];
  
  // ✅ แสดง workflow validation
  const workflowIssues = workflowValidation?.completeness_issues || [];
  const currentWorkflowStep = workflowValidation?.current_step || "unknown";
  const isWorkflowComplete = workflowValidation?.is_complete || false;

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
      {flightSegments.length > 0 && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {/* ✅ แสดงขาไป (Outbound) */}
            {flight.outbound && flight.outbound.length > 0 && (
              <div style={{ marginBottom: flight.inbound && flight.inbound.length > 0 ? '16px' : '0' }}>
                <div style={{ fontWeight: 600, marginBottom: '8px', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🛫 ขาไป
                  {(() => {
                    const firstOutbound = flight.outbound[0];
                    return firstOutbound?.carrier && <AirlineLogo carrierCode={firstOutbound.carrier} size={24} />;
                  })()}
                </div>
                {(() => {
                  const outboundSegs = flight.outbound;
                  const firstOutbound = outboundSegs[0];
                  const lastOutbound = outboundSegs[outboundSegs.length - 1];
                  return (
                    <>
                      {firstOutbound.carrier && kv('สายการบิน', getAirlineName(firstOutbound.carrier))}
                      {firstOutbound.number && kv('เลขเที่ยวบิน', `${firstOutbound.carrier || ''}${firstOutbound.number}`)}
                      {firstOutbound.from && lastOutbound.to && kv('เส้นทาง', `${firstOutbound.from} → ${lastOutbound.to}`)}
                      {firstOutbound.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstOutbound.departure))}
                      {lastOutbound.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastOutbound.arrival))}
                      {outboundSegs.length > 1 && kv('แวะ', `${outboundSegs.length - 1} ครั้ง`)}
                    </>
                  );
                })()}
              </div>
            )}
            
            {/* ✅ แสดงขากลับ (Inbound) */}
            {flight.inbound && flight.inbound.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, marginBottom: '8px', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🛬 ขากลับ
                  {(() => {
                    const firstInbound = flight.inbound[0];
                    return firstInbound?.carrier && <AirlineLogo carrierCode={firstInbound.carrier} size={24} />;
                  })()}
                </div>
                {(() => {
                  const inboundSegs = flight.inbound;
                  const firstInbound = inboundSegs[0];
                  const lastInbound = inboundSegs[inboundSegs.length - 1];
                  return (
                    <>
                      {firstInbound.carrier && kv('สายการบิน', getAirlineName(firstInbound.carrier))}
                      {firstInbound.number && kv('เลขเที่ยวบิน', `${firstInbound.carrier || ''}${firstInbound.number}`)}
                      {firstInbound.from && lastInbound.to && kv('เส้นทาง', `${firstInbound.from} → ${lastInbound.to}`)}
                      {firstInbound.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstInbound.departure))}
                      {lastInbound.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastInbound.arrival))}
                      {inboundSegs.length > 1 && kv('แวะ', `${inboundSegs.length - 1} ครั้ง`)}
                    </>
                  );
                })()}
              </div>
            )}
            
            {/* ✅ Fallback: แสดงแบบเดิมถ้าไม่มี outbound/inbound แยก */}
            {(!flight.outbound || flight.outbound.length === 0) && (!flight.inbound || flight.inbound.length === 0) && firstSegment && (
              <>
                {firstSegment.carrier && kv('สายการบิน', getAirlineName(firstSegment.carrier))}
                {firstSegment.number && kv('เลขเที่ยวบิน', `${firstSegment.carrier || ''}${firstSegment.number}`)}
                {firstSegment.from && lastSegment.to && kv('เส้นทาง', `${firstSegment.from} → ${lastSegment.to}`)}
                {firstSegment.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstSegment.departure))}
                {lastSegment.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastSegment.arrival))}
                {flight.is_non_stop !== undefined && kv('บินตรง', flight.is_non_stop ? 'ใช่' : `แวะ ${flight.num_stops || 0} ครั้ง`)}
              </>
            )}
            
            {/* ✅ ราคารวม */}
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

      {/* ✅ Cache Validation Status */}
      {cacheValidation && (
        <div className="plan-card-section" style={{ 
          marginTop: '16px', 
          padding: '12px',
          background: cacheValidation.valid ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          borderRadius: '8px',
          border: `1px solid ${cacheValidation.valid ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
        }}>
          <div className="plan-card-section-title" style={{ 
            color: cacheValidation.valid ? '#22c55e' : '#ef4444',
            fontSize: '13px',
            fontWeight: 600
          }}>
            {cacheValidation.valid ? '✅ ข้อมูลถูกต้อง' : '⚠️ ตรวจพบปัญหา'}
          </div>
          {validationIssues.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#ef4444', marginBottom: '4px' }}>ปัญหา:</div>
              {validationIssues.map((issue, idx) => (
                <div key={idx} style={{ fontSize: '11px', color: '#dc2626', marginLeft: '8px' }}>
                  • {issue}
                </div>
              ))}
            </div>
          )}
          {validationWarnings.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#f59e0b', marginBottom: '4px' }}>คำเตือน:</div>
              {validationWarnings.map((warning, idx) => (
                <div key={idx} style={{ fontSize: '11px', color: '#d97706', marginLeft: '8px' }}>
                  • {warning}
                </div>
              ))}
            </div>
          )}
          {cacheValidation.summary && (
            <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)' }}>
              ตัวเลือกที่แคช: เที่ยวบินขาไป {cacheValidation.summary.flights_outbound || 0}, 
              เที่ยวบินขากลับ {cacheValidation.summary.flights_inbound || 0}, 
              การเดินทาง {cacheValidation.summary.ground_transport || 0}, 
              ที่พัก {cacheValidation.summary.accommodation || 0}
            </div>
          )}
        </div>
      )}
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
              {kv('ชื่อ (EN)', userProfile.first_name || '—')}
              {kv('นามสกุล (EN)', userProfile.last_name || '—')}
              {userProfile.first_name_th && kv('ชื่อ (ไทย)', userProfile.first_name_th)}
              {userProfile.last_name_th && kv('นามสกุล (ไทย)', userProfile.last_name_th)}
              {userProfile.national_id && kv('เลขบัตรประชาชน', userProfile.national_id)}
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
              {userProfile.passport_issue_date && kv('วันออกหนังสือเดินทาง', userProfile.passport_issue_date)}
              {userProfile.passport_issuing_country && kv('ประเทศที่ออกหนังสือเดินทาง', userProfile.passport_issuing_country)}
              {userProfile.passport_given_names && kv('ชื่อตามหนังสือเดินทาง (EN)', userProfile.passport_given_names)}
              {userProfile.passport_surname && kv('นามสกุลตามหนังสือเดินทาง (EN)', userProfile.passport_surname)}
              {userProfile.place_of_birth && kv('สถานที่เกิด', userProfile.place_of_birth)}
            </div>
            {!hasPassportInfo && (
              <div className="plan-card-small" style={{ marginTop: '8px', opacity: 0.8 }}>
                ⚠️ ข้อมูลพาสปอร์ตยังไม่ครบ
              </div>
            )}
          </div>

          {/* Visa Information Section */}
          {userProfile.visa_type && (
            <div className="plan-card-section">
              <div className="plan-card-section-title">🛂 ข้อมูลวีซ่า</div>
              <div className="plan-card-section-body">
                {kv('ประเภทวีซ่า', userProfile.visa_type || '—')}
                {kv('เลขที่วีซ่า', userProfile.visa_number || '—')}
                {kv('ประเทศที่ออกวีซ่า', userProfile.visa_issuing_country || '—')}
                {kv('วันออกวีซ่า', userProfile.visa_issue_date || '—')}
                {kv('วันหมดอายุวีซ่า', userProfile.visa_expiry_date || '—')}
                {kv('ประเภทการเข้าประเทศ', userProfile.visa_entry_type === 'S' ? 'ครั้งเดียว (Single Entry)' : userProfile.visa_entry_type === 'M' ? 'หลายครั้ง (Multiple Entry)' : userProfile.visa_entry_type || '—')}
                {kv('วัตถุประสงค์', userProfile.visa_purpose === 'T' ? 'ท่องเที่ยว' : userProfile.visa_purpose === 'B' ? 'ธุรกิจ' : userProfile.visa_purpose === 'S' ? 'ศึกษา' : userProfile.visa_purpose === 'W' ? 'ทำงาน' : userProfile.visa_purpose === 'TR' ? 'ผ่านทาง' : userProfile.visa_purpose === 'O' ? 'อื่นๆ' : userProfile.visa_purpose || '—')}
              </div>
            </div>
          )}

          {/* Hotel Booking Preferences Section */}
          {(userProfile.emergency_contact_name || userProfile.hotel_early_checkin || userProfile.hotel_late_checkout || 
            userProfile.hotel_smoking_preference || userProfile.hotel_room_type_preference || userProfile.hotel_floor_preference ||
            userProfile.hotel_view_preference || userProfile.hotel_extra_bed || userProfile.hotel_airport_transfer ||
            userProfile.hotel_dietary_requirements || userProfile.hotel_special_occasion || userProfile.hotel_accessibility_needs ||
            userProfile.hotel_arrival_time || userProfile.hotel_arrival_flight || userProfile.hotel_departure_time ||
            userProfile.hotel_number_of_guests || userProfile.payment_method || userProfile.card_holder_name ||
            userProfile.company_name || userProfile.tax_id || userProfile.hotel_loyalty_number ||
            userProfile.airline_frequent_flyer || userProfile.hotel_booking_notes) && (
            <div className="plan-card-section">
              <div className="plan-card-section-title">🏨 ข้อมูลสำหรับการจองโรงแรม</div>
              <div className="plan-card-section-body">
                {/* Emergency Contact */}
                {(userProfile.emergency_contact_name || userProfile.emergency_contact_phone) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '8px', marginBottom: '4px', color: '#1e40af' }}>📞 ติดต่อฉุกเฉิน</div>
                    {userProfile.emergency_contact_name && kv('ชื่อ', userProfile.emergency_contact_name)}
                    {userProfile.emergency_contact_phone && kv('เบอร์โทร', userProfile.emergency_contact_phone)}
                    {userProfile.emergency_contact_relation && kv('ความสัมพันธ์', 
                      userProfile.emergency_contact_relation === 'SPOUSE' ? 'คู่สมรส' :
                      userProfile.emergency_contact_relation === 'PARENT' ? 'บิดา/มารดา' :
                      userProfile.emergency_contact_relation === 'FRIEND' ? 'เพื่อน' :
                      userProfile.emergency_contact_relation === 'OTHER' ? 'อื่นๆ' : userProfile.emergency_contact_relation)}
                    {userProfile.emergency_contact_email && kv('อีเมล', userProfile.emergency_contact_email)}
                  </>
                )}

                {/* Special Requests */}
                {(userProfile.hotel_early_checkin || userProfile.hotel_late_checkout || userProfile.hotel_smoking_preference ||
                  userProfile.hotel_room_type_preference || userProfile.hotel_floor_preference || userProfile.hotel_view_preference ||
                  userProfile.hotel_extra_bed || userProfile.hotel_airport_transfer || userProfile.hotel_dietary_requirements ||
                  userProfile.hotel_special_occasion || userProfile.hotel_accessibility_needs) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>⭐ ความต้องการพิเศษ</div>
                    {userProfile.hotel_early_checkin && kv('Early Check-in', 'ต้องการ')}
                    {userProfile.hotel_late_checkout && kv('Late Check-out', 'ต้องการ')}
                    {userProfile.hotel_smoking_preference && kv('บุหรี่', 
                      userProfile.hotel_smoking_preference === 'NON_SMOKING' ? 'ไม่สูบบุหรี่' :
                      userProfile.hotel_smoking_preference === 'SMOKING' ? 'สูบบุหรี่ได้' : userProfile.hotel_smoking_preference)}
                    {userProfile.hotel_room_type_preference && kv('ประเภทห้อง', userProfile.hotel_room_type_preference)}
                    {userProfile.hotel_floor_preference && kv('ชั้น', 
                      userProfile.hotel_floor_preference === 'HIGH' ? 'ชั้นสูง' :
                      userProfile.hotel_floor_preference === 'LOW' ? 'ชั้นต่ำ' :
                      userProfile.hotel_floor_preference === 'ANY' ? 'ไม่ระบุ' : userProfile.hotel_floor_preference)}
                    {userProfile.hotel_view_preference && kv('วิว', 
                      userProfile.hotel_view_preference === 'SEA' ? 'วิวทะเล' :
                      userProfile.hotel_view_preference === 'CITY' ? 'วิวเมือง' :
                      userProfile.hotel_view_preference === 'GARDEN' ? 'วิวสวน' :
                      userProfile.hotel_view_preference === 'ANY' ? 'ไม่ระบุ' : userProfile.hotel_view_preference)}
                    {userProfile.hotel_extra_bed && kv('เตียงเสริม', 'ต้องการ')}
                    {userProfile.hotel_airport_transfer && kv('รถรับส่งสนามบิน', 'ต้องการ')}
                    {userProfile.hotel_dietary_requirements && kv('อาหารพิเศษ', 
                      userProfile.hotel_dietary_requirements === 'VEGETARIAN' ? 'Vegetarian' :
                      userProfile.hotel_dietary_requirements === 'VEGAN' ? 'Vegan' :
                      userProfile.hotel_dietary_requirements === 'HALAL' ? 'Halal' :
                      userProfile.hotel_dietary_requirements === 'ALLERGIES' ? 'มีอาการแพ้' :
                      userProfile.hotel_dietary_requirements === 'NONE' ? 'ไม่มี' : userProfile.hotel_dietary_requirements)}
                    {userProfile.hotel_special_occasion && kv('โอกาสพิเศษ', 
                      userProfile.hotel_special_occasion === 'BIRTHDAY' ? 'วันเกิด' :
                      userProfile.hotel_special_occasion === 'HONEYMOON' ? 'ฮันนีมูน' :
                      userProfile.hotel_special_occasion === 'ANNIVERSARY' ? 'วันครบรอบ' :
                      userProfile.hotel_special_occasion === 'NONE' ? 'ไม่มี' : userProfile.hotel_special_occasion)}
                    {userProfile.hotel_accessibility_needs && kv('ห้องสำหรับผู้พิการ', 'ต้องการ')}
                  </>
                )}

                {/* Check-in Details */}
                {(userProfile.hotel_arrival_time || userProfile.hotel_arrival_flight || userProfile.hotel_departure_time || userProfile.hotel_number_of_guests) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>🕐 ข้อมูลการเข้าพัก</div>
                    {userProfile.hotel_arrival_time && kv('เวลาที่คาดว่าจะถึง', userProfile.hotel_arrival_time)}
                    {userProfile.hotel_arrival_flight && kv('เที่ยวบินที่มาถึง', userProfile.hotel_arrival_flight)}
                    {userProfile.hotel_departure_time && kv('เวลาที่ออกจากโรงแรม', userProfile.hotel_departure_time)}
                    {userProfile.hotel_number_of_guests && kv('จำนวนผู้เข้าพัก', `${userProfile.hotel_number_of_guests} คน`)}
                  </>
                )}

                {/* Payment Information */}
                {(userProfile.payment_method || userProfile.card_holder_name || userProfile.card_last_4_digits) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>💳 ข้อมูลการชำระเงิน</div>
                    {userProfile.payment_method && kv('วิธีชำระเงิน', 
                      userProfile.payment_method === 'CREDIT_CARD' ? 'บัตรเครดิต' :
                      userProfile.payment_method === 'DEBIT_CARD' ? 'บัตรเดบิต' :
                      userProfile.payment_method === 'BANK_TRANSFER' ? 'โอนเงินผ่านธนาคาร' : userProfile.payment_method)}
                    {userProfile.card_holder_name && kv('ชื่อเจ้าของบัตร', userProfile.card_holder_name)}
                    {userProfile.card_last_4_digits && kv('เลขบัตร 4 หลักสุดท้าย', `****${userProfile.card_last_4_digits}`)}
                  </>
                )}

                {/* Tax Invoice Information */}
                {(userProfile.company_name || userProfile.tax_id) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>🧾 ข้อมูลสำหรับออกใบกำกับภาษี</div>
                    {userProfile.company_name && kv('ชื่อบริษัท/องค์กร', userProfile.company_name)}
                    {userProfile.tax_id && kv('เลขประจำตัวผู้เสียภาษี', userProfile.tax_id)}
                  </>
                )}

                {/* Loyalty Program */}
                {(userProfile.hotel_loyalty_number || userProfile.airline_frequent_flyer) && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>🎁 โปรแกรมสะสมแต้ม/ไมล์</div>
                    {userProfile.hotel_loyalty_number && kv('เลขสมาชิกโรงแรม', userProfile.hotel_loyalty_number)}
                    {userProfile.airline_frequent_flyer && kv('เลขสมาชิกสายการบิน', userProfile.airline_frequent_flyer)}
                  </>
                )}

                {/* Additional Notes */}
                {userProfile.hotel_booking_notes && (
                  <>
                    <div style={{ fontWeight: 600, marginTop: '12px', marginBottom: '4px', color: '#1e40af' }}>📝 หมายเหตุเพิ่มเติม</div>
                    <div style={{ padding: '8px', background: '#f9fafb', borderRadius: '6px', fontSize: '14px', lineHeight: '1.6' }}>
                      {userProfile.hotel_booking_notes}
                    </div>
                  </>
                )}
              </div>
            </div>
          )}

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

export function ConfirmBookingCard({ canBook, onConfirm, onPayment, note, isBooking, bookingResult, chatMode = 'normal', agentState = null }) {
  const needsPayment = bookingResult?.needs_payment || bookingResult?.status === 'pending_payment';
  const isConfirmed = bookingResult?.status === 'confirmed' || bookingResult?.status === 'paid';
  
  // ✅ Agent Mode: Check if auto-booked (from agentState or bookingResult)
  const isAgentMode = chatMode === 'agent';
  const isAutoBooked = isAgentMode && (
    bookingResult?.auto_booked ||
    bookingResult?.status === 'pending_payment' ||
    bookingResult?.status === 'confirmed' ||
    agentState?.intent === 'booking' ||
    agentState?.step === 'completed' ||
    agentState?.step === 'pending_payment' ||
    agentState?.step === 'booking'
  );
  
  // ✅ In Agent Mode, if we have selected options but no booking yet, show "กำลังจองอัตโนมัติ..."
  const isAutoBookingInProgress = isAgentMode && !bookingResult && !isAutoBooked && canBook;
  
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

          {/* ✅ Agent Mode: Hide confirm button - booking happens automatically */}
          {!isAutoBooked && !isAutoBookingInProgress && (
            <div className="plan-card-footer summary-footer">
              <button
                className={`plan-card-button ${!canBook ? 'summary-disabled' : ''}`}
                disabled={!canBook || isBooking}
                onClick={onConfirm}
              >
                ✅ ยืนยันจองใน Sandbox
              </button>
            </div>
          )}
          
          {/* ✅ Agent Mode: Show auto-booking status when in progress */}
          {isAutoBookingInProgress && (
            <div className="plan-card-section">
              <div className="plan-card-section-body plan-card-small">
                <div style={{ color: '#10b981', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="plan-card-spinner" style={{ display: 'inline-block', width: '16px', height: '16px', border: '2px solid #10b981', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }}></span>
                  🤖 Agent Mode: กำลังเลือกตัวเลือกและจองให้อัตโนมัติ...
                </div>
                <div style={{ marginTop: '8px', opacity: 0.8, fontSize: '0.875rem' }}>
                  ไม่ต้องกดยืนยัน - ระบบจะจองให้อัตโนมัติ
                </div>
              </div>
            </div>
          )}
          
          {/* ✅ Agent Mode: Show auto-booked success message */}
          {isAutoBooked && bookingResult && (
            <div className="plan-card-section">
              <div className="plan-card-section-body plan-card-small">
                <div style={{ color: '#10b981', fontWeight: 600 }}>
                  ✅ Agent Mode: จองสำเร็จแล้ว!
                </div>
                <div style={{ marginTop: '8px', opacity: 0.8, fontSize: '0.875rem' }}>
                  กรุณาชำระเงินเพื่อยืนยันการจอง
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ✅ Final Trip Summary - สรุปครบถ้วนก่อนจอง
export function FinalTripSummary({ plan, travelSlots, userProfile, cachedOptions, cacheValidation, workflowValidation }) {
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
      {(flightSegments.length > 0 || (flight.outbound && flight.outbound.length > 0) || (flight.inbound && flight.inbound.length > 0)) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {/* ✅ แสดงขาไป (Outbound) */}
            {flight.outbound && flight.outbound.length > 0 && (
              <div style={{ marginBottom: flight.inbound && flight.inbound.length > 0 ? '20px' : '0', paddingBottom: flight.inbound && flight.inbound.length > 0 ? '16px' : '0', borderBottom: flight.inbound && flight.inbound.length > 0 ? '1px solid #e5e7eb' : 'none' }}>
                <div style={{ fontWeight: 600, marginBottom: '12px', color: '#2563eb', fontSize: '15px' }}>🛫 ขาไป</div>
                {flight.outbound.map((seg, idx) => {
                  const isLast = idx === flight.outbound.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #3b82f6' }}>
                      {seg.carrier && kv('สายการบิน', getAirlineName(seg.carrier))}
                      {seg.number && kv('เลขเที่ยวบิน', `${seg.carrier || ''}${seg.number}`)}
                      {seg.from && seg.to && kv('เส้นทาง', `${seg.from} → ${seg.to}`)}
                      {seg.departure && kv('วัน-เวลาออก', formatThaiDateTime(seg.departure))}
                      {seg.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(seg.arrival))}
                      {seg.duration && kv('ระยะเวลา', formatDuration(seg.duration))}
                      {!isLast && <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280' }}>↪ แวะเปลี่ยนเครื่อง</div>}
                    </div>
                  );
                })}
              </div>
            )}
            
            {/* ✅ แสดงขากลับ (Inbound) */}
            {flight.inbound && flight.inbound.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, marginBottom: '12px', color: '#2563eb', fontSize: '15px' }}>🛬 ขากลับ</div>
                {flight.inbound.map((seg, idx) => {
                  const isLast = idx === flight.inbound.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #10b981' }}>
                      {seg.carrier && kv('สายการบิน', getAirlineName(seg.carrier))}
                      {seg.number && kv('เลขเที่ยวบิน', `${seg.carrier || ''}${seg.number}`)}
                      {seg.from && seg.to && kv('เส้นทาง', `${seg.from} → ${seg.to}`)}
                      {seg.departure && kv('วัน-เวลาออก', formatThaiDateTime(seg.departure))}
                      {seg.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(seg.arrival))}
                      {seg.duration && kv('ระยะเวลา', formatDuration(seg.duration))}
                      {!isLast && <div style={{ marginTop: '8px', fontSize: '12px', color: '#6b7280' }}>↪ แวะเปลี่ยนเครื่อง</div>}
                    </div>
                  );
                })}
              </div>
            )}
            
            {/* ✅ Fallback: แสดงแบบเดิมถ้าไม่มี outbound/inbound แยก */}
            {(!flight.outbound || flight.outbound.length === 0) && (!flight.inbound || flight.inbound.length === 0) && flightSegments.length > 0 && (
              <>
                {flightSegments.map((seg, idx) => (
                  <div key={idx} style={{ marginBottom: idx < flightSegments.length - 1 ? '12px' : '0' }}>
                    {seg.from && seg.to && kv(`เส้นทาง (${idx + 1})`, `${seg.from} → ${seg.to}`)}
                    {seg.departure && kv('วัน-เวลาออก', formatThaiDateTime(seg.departure))}
                    {seg.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(seg.arrival))}
                    {seg.carrier && kv('สายการบิน', getAirlineName(seg.carrier))}
                    {seg.duration && kv('ระยะเวลา', formatDuration(seg.duration))}
                  </div>
                ))}
              </>
            )}
            
            {/* ✅ ราคารวม */}
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

      {/* ✅ Cache Validation Status - ขั้นสุดท้ายก่อนจอง */}
      {cacheValidation && (
        <div className="plan-card-section" style={{ 
          marginTop: '16px', 
          padding: '12px',
          background: cacheValidation.valid ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          borderRadius: '8px',
          border: `1px solid ${cacheValidation.valid ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
        }}>
          <div className="plan-card-section-title" style={{ 
            color: cacheValidation.valid ? '#22c55e' : '#ef4444',
            fontSize: '14px',
            fontWeight: 600
          }}>
            {cacheValidation.valid ? '✅ ข้อมูลถูกต้องพร้อมจอง' : '⚠️ ตรวจพบปัญหา - กรุณาตรวจสอบก่อนจอง'}
          </div>
          {cacheValidation.issues && cacheValidation.issues.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#ef4444', marginBottom: '4px' }}>ปัญหา:</div>
              {cacheValidation.issues.map((issue, idx) => (
                <div key={idx} style={{ fontSize: '11px', color: '#dc2626', marginLeft: '8px', marginTop: '2px' }}>
                  • {issue}
                </div>
              ))}
            </div>
          )}
          {cacheValidation.warnings && cacheValidation.warnings.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#f59e0b', marginBottom: '4px' }}>คำเตือน:</div>
              {cacheValidation.warnings.map((warning, idx) => (
                <div key={idx} style={{ fontSize: '11px', color: '#d97706', marginLeft: '8px', marginTop: '2px' }}>
                  • {warning}
                </div>
              ))}
            </div>
          )}
          {cacheValidation.summary && (
            <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255, 255, 255, 0.8)', marginBottom: '4px' }}>
                📊 สรุปตัวเลือกที่แคช:
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)', lineHeight: '1.6' }}>
                ✈️ เที่ยวบินขาไป: {cacheValidation.summary.flights_outbound || 0} ตัวเลือก<br/>
                ✈️ เที่ยวบินขากลับ: {cacheValidation.summary.flights_inbound || 0} ตัวเลือก<br/>
                🚗 การเดินทาง: {cacheValidation.summary.ground_transport || 0} ตัวเลือก<br/>
                🏨 ที่พัก: {cacheValidation.summary.accommodation || 0} ตัวเลือก
              </div>
            </div>
          )}
        </div>
      )}

      {/* ✅ Workflow Validation Status - ขั้นสุดท้ายก่อนจอง */}
      {workflowValidation && (
        <div className="plan-card-section" style={{ 
          marginTop: '16px', 
          padding: '12px',
          background: workflowValidation.is_complete ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
          borderRadius: '8px',
          border: `1px solid ${workflowValidation.is_complete ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
        }}>
          <div className="plan-card-section-title" style={{ 
            color: workflowValidation.is_complete ? '#22c55e' : '#ef4444',
            fontSize: '14px',
            fontWeight: 600
          }}>
            {workflowValidation.is_complete ? '✅ Workflow Complete - พร้อมจอง' : `❌ Workflow ไม่ครบ - ขั้นตอนปัจจุบัน: ${workflowValidation.current_step || 'unknown'}`}
          </div>
          {workflowValidation.completeness_issues && workflowValidation.completeness_issues.length > 0 && (
            <div style={{ marginTop: '8px' }}>
              <div style={{ fontSize: '12px', fontWeight: 600, color: '#ef4444', marginBottom: '4px' }}>ต้องแก้ไขก่อนจอง:</div>
              {workflowValidation.completeness_issues.map((issue, idx) => (
                <div key={idx} style={{ fontSize: '11px', color: '#dc2626', marginLeft: '8px', marginTop: '2px' }}>
                  • {issue}
                </div>
              ))}
            </div>
          )}
          {!workflowValidation.is_complete && (
            <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.8)', lineHeight: '1.6' }}>
                ⚠️ กรุณาทำให้ workflow ครบถ้วนก่อนจอง: {workflowValidation.required_slots?.join(', ') || 'all required slots'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
