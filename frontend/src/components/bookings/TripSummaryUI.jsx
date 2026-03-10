import React from 'react';
import { AIRLINE_NAMES, AIRLINE_DOMAINS } from '../../data/airlineNames';
import { formatPriceInThb } from '../../utils/currency';
import './PlanChoiceCard.css';
import './TripSummaryUI.css';

/** แสดงราคาเป็นบาท (THB) เสมอ — ใช้ util ร่วม */
function moneyThb(amount, sourceCurrency) {
  return formatPriceInThb(amount, sourceCurrency);
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

function formatDateThai(dateStr) {
  if (!dateStr || typeof dateStr !== 'string') return '';
  const d = new Date(dateStr.trim() + 'T00:00:00');
  if (Number.isNaN(d.getTime())) return dateStr;
  const day = d.getDate();
  const months = ['มกราคม', 'กุมภาพันธ์', 'มีนาคม', 'เมษายน', 'พฤษภาคม', 'มิถุนายน', 'กรกฎาคม', 'สิงหาคม', 'กันยายน', 'ตุลาคม', 'พฤศจิกายน', 'ธันวาคม'];
  const month = months[d.getMonth()];
  const be = d.getFullYear() + 543;
  return `${day} ${month} ${be}`;
}

function getAirlineName(code) {
  if (!code) return 'Unknown';
  return AIRLINE_NAMES[String(code).toUpperCase()] || code;
}

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
    case 5: {
      const domain = AIRLINE_DOMAINS[code];
      if (domain) {
        return `https://www.google.com/s2/favicons?sz=128&domain=${domain}`;
      }
      return null;
    }
    case 6:
      return `https://pics.avs.io/200/200/${code}.png`;
    default:
      return null;
  }
}

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
    const maxAttempts = 6;
    let nextAttempt = logoAttempt + 1;
    let url = getAirlineLogoUrl(carrierCode, nextAttempt);
    while (!url && nextAttempt < maxAttempts) {
      nextAttempt += 1;
      url = getAirlineLogoUrl(carrierCode, nextAttempt);
    }
    if (url) {
      setLogoAttempt(nextAttempt);
      setCurrentUrl(url);
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

function formatThaiDate(isoDate) {
  if (!isoDate) return '';
  try {
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

/** แยก segments เป็นขาไป/ขากลับ เมื่อ API ส่งมาแค่ segments ไม่มี outbound/inbound */
function splitFlightSegmentsToOutboundInbound(segments, travelSlots) {
  if (!Array.isArray(segments) || segments.length === 0) return { outbound: [], inbound: [] };
  if (segments.length === 1) return { outbound: segments, inbound: [] };
  const origin = (travelSlots?.origin_city || travelSlots?.origin || segments[0]?.from || '').toString().trim().toUpperCase();
  // แยกตามจุดกลับถึงต้นทางได้เฉพาะเมื่อมี origin ชัดเจน (ถ้า origin ว่างจะไม่ใช้ logic นี้)
  if (origin) {
    const originArrivalIndex = segments.findIndex((seg, idx) => idx > 0 && (seg.to || '').toString().trim().toUpperCase() === origin);
    if (originArrivalIndex > 0) {
      return {
        outbound: segments.slice(0, originArrivalIndex),
        inbound: segments.slice(originArrivalIndex),
      };
    }
  }
  const mid = Math.ceil(segments.length / 2);
  return { outbound: segments.slice(0, mid), inbound: segments.slice(mid) };
}

export function TripSummaryCard({ plan, travelSlots, cachedOptions, cacheValidation, workflowValidation }) {
  if (!plan) return null;
  
  const validationIssues = cacheValidation?.issues || [];
  const validationWarnings = cacheValidation?.warnings || [];

  const currency =
    plan?.price_breakdown?.currency ||
    plan?.currency ||
    plan?.flight?.currency ||
    plan?.travel?.flights?.currency ||
    plan?.hotel?.currency ||
    plan?.accommodation?.currency ||
    'THB';

  // ✅ ราคารวม: รองรับทั้ง structure เก่าและใหม่
  const total =
    typeof plan?.total_price === 'number'
      ? plan.total_price
      : typeof plan?.price === 'number'
        ? plan.price
        : typeof plan?.summary?.total_price === 'number'
          ? plan.summary.total_price
          : (() => {
              const f = (plan?.flight?.total_price ?? plan?.flight?.price_total ?? plan?.travel?.flights?.total_price) || 0;
              const h = (plan?.hotel?.total_price ?? plan?.hotel?.price_total ?? plan?.accommodation?.total_price) || 0;
              const t = (plan?.transport?.price ?? plan?.transport?.price_amount ?? plan?.travel?.ground_transport?.price) || 0;
              const sum = Number(f) + Number(h) + Number(t);
              return sum > 0 ? sum : undefined;
            })();

  const totalText = moneyThb(total, currency) || safeText(plan?.total_price_text || plan?.summary?.total_price_text) || '—';

  const legs = Array.isArray(travelSlots?.legs) ? travelSlots.legs : [];
  const isMultiCity = legs.length > 1;
  const origin = travelSlots?.origin_city || travelSlots?.origin || travelSlots?.origin_iata || legs[0]?.origin || '';
  const dest = travelSlots?.destination_city || travelSlots?.destination || travelSlots?.destination_iata || (legs.length ? legs[legs.length - 1]?.destination : '');
  const dateGo = travelSlots?.departure_date || travelSlots?.start_date || travelSlots?.check_in || legs[0]?.departure_date || '';
  
  // ✅ คำนวณวันกลับถ้ายังไม่มี
  let dateBack = travelSlots?.return_date || travelSlots?.end_date || travelSlots?.check_out || '';
  if (!dateBack && dateGo && travelSlots?.nights != null) {
    try {
      const startDate = new Date(dateGo);
      const nights = parseInt(travelSlots.nights) || 0;
      const returnDate = new Date(startDate);
      returnDate.setDate(returnDate.getDate() + nights);
      dateBack = returnDate.toISOString().split('T')[0];
    } catch (e) {
      console.error('Error calculating return date:', e);
    }
  }
  
  const pax = [
    travelSlots?.adults != null && Number(travelSlots.adults) > 0 ? `${travelSlots.adults} ผู้ใหญ่` : null,
    travelSlots?.children != null && Number(travelSlots.children) > 0 ? `${travelSlots.children} เด็ก` : null,
  ].filter(Boolean).join(', ');

  // ✅ Extract flight details — รองรับทั้ง plan.flight และ plan.travel.flights
  const flightData = plan?.flight || plan?.travel?.flights || {};
  const flight = flightData;
  const flightSegments = flight?.segments || [];
  const firstSegment = flightSegments[0];
  const lastSegment = flightSegments[flightSegments.length - 1];
  // ✅ ถ้าไม่มี outbound/inbound แยกจาก API ให้แยกจาก segments เพื่อแสดงขาไป/ขากลับ
  const hasOutboundInbound = (flight?.outbound?.length > 0) || (flight?.inbound?.length > 0);
  const split = hasOutboundInbound ? null : splitFlightSegmentsToOutboundInbound(flightSegments, travelSlots);
  const outboundSegments = hasOutboundInbound ? (flight.outbound || []) : (split?.outbound || []);
  const inboundSegments = hasOutboundInbound ? (flight.inbound || []) : (split?.inbound || []);
  
  // ✅ Extract hotel details — รองรับทั้ง plan.hotel และ plan.accommodation
  const hotel = plan?.hotel || plan?.accommodation || {};
  const hotelSegments = hotel?.segments || [];
  
  // ✅ Extract transport details — รองรับทั้ง plan.transport และ plan.travel.ground_transport
  const transportRaw = plan?.transport || plan?.travel?.ground_transport || {};
  const transport = Array.isArray(transportRaw) ? { segments: transportRaw } : transportRaw;
  const transportSegments = transport?.segments || [];

  // ✅ ตรวจสอบว่ามีข้อมูลอะไรบ้าง เพื่อแสดง title ที่เหมาะสม
  const hasFlightData = flightSegments.length > 0 || outboundSegments.length > 0;
  const hasHotelData = hotelSegments.length > 0 || !!hotel.hotelName;
  const hasTransportData = transportSegments.length > 0 || !!transport.type;
  const isRoundTrip = inboundSegments.length > 0 || !!dateBack;

  const routeLabel = isMultiCity ? 'เส้นทาง (หลายสถานที่)' : (hasHotelData && !hasFlightData ? 'สถานที่' : 'ต้นทาง → ปลายทาง');
  const routeText = isMultiCity && legs.length
    ? [legs[0]?.origin, ...legs.map((l) => l.destination)].filter(Boolean).join(' → ')
    : (origin && dest ? `${origin} → ${dest}` : origin || dest);
  
  // ✅ Title ตามสถานการณ์
  const summaryTitle = (() => {
    if (hasFlightData && hasHotelData) return '✅ สรุปทริป (เที่ยวบิน + ที่พัก)';
    if (hasFlightData && !hasHotelData) return '✅ สรุปทริป (เที่ยวบิน)';
    if (!hasFlightData && hasHotelData) return '✅ สรุปทริป (ที่พัก)';
    if (hasTransportData) return '✅ สรุปทริป (การเดินทาง)';
    return '✅ สรุปทริป';
  })();

  // ✅ สรุปจำนวนตัวเลือกจาก plan (fallback เมื่อ cache แสดง 0 ทั้งหมด)
  const outboundList = flight?.outbound || plan?.travel?.flights?.outbound || [];
  const inboundList = flight?.inbound || plan?.travel?.flights?.inbound || [];
  const accommodationList = hotel?.segments || plan?.accommodation?.segments || [];
  const groundList = transport?.segments || plan?.travel?.ground_transport || [];
  const summaryFromPlanCard = {
    flights_outbound: Array.isArray(outboundList) ? outboundList.length : (outboundList ? 1 : 0),
    flights_inbound: Array.isArray(inboundList) ? inboundList.length : (inboundList ? 1 : 0),
    ground_transport: Array.isArray(groundList) ? groundList.length : (groundList ? 1 : 0),
    accommodation: Array.isArray(accommodationList) ? accommodationList.length : (accommodationList ? 1 : 0),
  };
  const cacheSum = cacheValidation?.summary;
  const cacheHasAny = cacheSum && ((cacheSum.flights_outbound || 0) + (cacheSum.flights_inbound || 0) + (cacheSum.ground_transport || 0) + (cacheSum.accommodation || 0) > 0);
  const effectiveSum = cacheHasAny ? cacheSum : summaryFromPlanCard;

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">{summaryTitle}</span>
        </div>
      </div>

      {/* Overview */}
      <div className="plan-card-section">
        <div className="plan-card-section-title">🧾 ภาพรวม</div>
        <div className="plan-card-section-body">
          {(origin || dest || routeText) && kv(routeLabel, routeText)}
          {dateGo && kv(hasHotelData && !hasFlightData ? 'วันเช็คอิน' : 'วันเดินทาง', formatThaiDate(dateGo))}
          {dateBack && kv(hasHotelData && !hasFlightData ? 'วันเช็คเอาท์' : 'วันกลับ', formatThaiDate(dateBack))}
          {pax && kv(hasHotelData && !hasFlightData ? 'จำนวนผู้เข้าพัก' : 'ผู้โดยสาร', pax)}
        </div>
      </div>

      {/* Flight Details */}
      {flightSegments.length > 0 && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {/* ✅ แสดงขาไป (Outbound) - แสดง logo ทุก segment เมื่อต่อเครื่อง */}
            {outboundSegments.length > 0 && (
              <div style={{ marginBottom: inboundSegments.length > 0 ? '16px' : '0' }}>
                <div style={{ fontWeight: 600, marginBottom: '8px', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🛫 ขาไป
                </div>
                {outboundSegments.map((seg, idx) => {
                  const isLast = idx === outboundSegments.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #3b82f6' }}>
                      {seg.carrier && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <AirlineLogo carrierCode={seg.carrier} size={36} />
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(seg.carrier)}</div>
                            {seg.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{seg.carrier}{seg.number}</div>}
                          </div>
                        </div>
                      )}
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
            
            {/* ✅ แสดงขากลับ (Inbound) - แสดง logo ทุก segment เมื่อต่อเครื่อง */}
            {inboundSegments.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, marginBottom: '8px', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  🛬 ขากลับ
                </div>
                {inboundSegments.map((seg, idx) => {
                  const isLast = idx === inboundSegments.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #10b981' }}>
                      {seg.carrier && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <AirlineLogo carrierCode={seg.carrier} size={36} />
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(seg.carrier)}</div>
                            {seg.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{seg.carrier}{seg.number}</div>}
                          </div>
                        </div>
                      )}
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
            
            {/* ✅ Fallback: แสดงแบบเดิมถ้ามีแค่ segment เดียวหรือแยกขาไป/ขากลับไม่ได้ */}
            {outboundSegments.length === 0 && inboundSegments.length === 0 && firstSegment && (
              <>
                {firstSegment.carrier && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                    <AirlineLogo carrierCode={firstSegment.carrier} size={36} />
                    <div>
                      <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(firstSegment.carrier)}</div>
                      {firstSegment.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{firstSegment.carrier}{firstSegment.number}</div>}
                    </div>
                  </div>
                )}
                {firstSegment.from && lastSegment.to && kv('เส้นทาง', `${firstSegment.from} → ${lastSegment.to}`)}
                {firstSegment.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstSegment.departure))}
                {lastSegment.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastSegment.arrival))}
                {flight.is_non_stop !== undefined && kv('บินตรง', flight.is_non_stop ? 'ใช่' : `แวะ ${flight.num_stops || 0} ครั้ง`)}
              </>
            )}
            
            {/* ✅ ราคารวม */}
            {flight.currency && (flight.total_price != null || flight.price_total != null) && kv('ราคาไฟท์บิน', moneyThb(flight.total_price ?? flight.price_total, flight.currency))}
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
                    {grouped.price_total > 0 && kv('ราคา', moneyThb(grouped.price_total, grouped.currency))}
                  </div>
                ));
              })()
            ) : (
              <>
                {hotel.hotelName && kv('ชื่อโรงแรม', hotel.hotelName)}
                {hotel.nights != null && kv('จำนวนคืน', `${hotel.nights} คืน`)}
                {hotel.boardType && kv('ประเภทอาหาร', hotel.boardType)}
                {hotel.address && kv('ที่อยู่', hotel.address)}
                {hotel.price_total && kv('ราคา', moneyThb(hotel.price_total, hotel.currency || currency))}
                {hotel.price && !hotel.price_total && kv('ราคา', moneyThb(hotel.price, hotel.currency || currency))}
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
                  {seg.price && kv('ราคา', moneyThb(seg.price, seg.currency || currency))}
                </div>
              ))
            ) : (
              <>
                {transport.type && kv('ประเภท', transport.type)}
                {transport.route && kv('เส้นทาง', transport.route)}
                {transport.duration && kv('ระยะเวลา', transport.duration)}
                {(transport.price != null || transport.price_amount != null) && kv('ราคา', moneyThb(transport.price ?? transport.price_amount, transport.currency || currency))}
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
            {plan.price_breakdown.flight && kv('ไฟท์บิน', moneyThb(plan.price_breakdown.flight, currency))}
            {plan.price_breakdown.hotel && kv('ที่พัก', moneyThb(plan.price_breakdown.hotel, currency))}
            {plan.price_breakdown.transport && kv('การเดินทาง', moneyThb(plan.price_breakdown.transport, currency))}
            {plan.price_breakdown.car && kv('รถเช่า', moneyThb(plan.price_breakdown.car, currency))}
          </div>
        </div>
      )}

      {/* Total Price */}
      <div className="plan-card-footer">
        <div className="plan-card-price">{totalText || '—'}</div>
        <div className="summary-note">ราคาอ้างอิงจาก Amadeus Search (production){currency !== 'THB' ? ' · แสดงเป็นบาท (อัตราอ้างอิง)' : ''}</div>
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
          {(cacheValidation.summary || effectiveSum) && (
            <div style={{ marginTop: '8px', fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)' }}>
              {cacheHasAny ? 'ตัวเลือกที่แคช: ' : 'ตัวเลือกที่เลือก: '}
              เที่ยวบินขาไป {effectiveSum.flights_outbound ?? 0}, 
              เที่ยวบินขากลับ {effectiveSum.flights_inbound ?? 0}, 
              การเดินทาง {effectiveSum.ground_transport ?? 0}, 
              ที่พัก {effectiveSum.accommodation ?? 0}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// EditSectionCard removed - users can now type directly in chat

/** ตรวจว่าเมือง/จุดหมายอยู่ในประเทศไทยหรือไม่ (ใช้สำหรับซ่อนข้อมูลพาสปอร์ตเมื่อเดินทางในประเทศ) */
export function isLocationInThailand(loc) {
  if (!loc || typeof loc !== 'string') return false;
  const s = loc.toLowerCase().trim();
  const thaiDomestic = [
    'bangkok', 'bkk', 'dmk', 'กรุงเทพ', 'don mueang', 'suvarnabhumi',
    'chiang mai', 'cnx', 'เชียงใหม่', 'phuket', 'hkt', 'ภูเก็ต',
    'krabi', 'kbv', 'กระบี่', 'samui', 'usm', 'สมุย', 'koh samui',
    'hat yai', 'hdj', 'หาดใหญ่', 'udon thani', 'uth', 'udon', 'อุดร',
    'khon kaen', 'kkc', 'ขอนแก่น', 'ubon ratchathani', 'ubn', 'อุบล',
    'nakhon si thammarat', 'nst', 'นครศรีธรรมราช', 'surat thani', 'urt', 'สุราษฎร์',
    'pattaya', 'utapao', 'utm', 'พัทยา', 'chiang rai', 'cei', 'เชียงราย',
    'lampang', 'lpi', 'ลำปาง', 'phitsanulok', 'phs', 'พิษณุโลก'
  ];
  return thaiDomestic.some((key) => s.includes(key) || s === key);
}

export function UserInfoCard({ userProfile, onEdit, isDomesticTravel = false }) {
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

  const showPassportSection = !isDomesticTravel;
  const readyToBook = hasRequiredInfo && (isDomesticTravel || hasPassportInfo);

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">👤 ข้อมูลผู้ใช้สำหรับการจอง</span>
        </div>
      </div>

      {!userProfile ? (
        <div className="plan-card-section">
          <div className="plan-card-section-body plan-card-small">
            <div>⚠️ ยังไม่ได้กรอกข้อมูลผู้ใช้</div>
            <div style={{ marginTop: '8px' }}>
              {isDomesticTravel
                ? 'กรุณากรอกข้อมูลก่อนยืนยันจอง (ชื่อ, นามสกุล, อีเมล, เบอร์โทร)'
                : 'กรุณากรอกข้อมูลก่อนยืนยันจอง (ชื่อ, นามสกุล, อีเมล, เบอร์โทร, พาสปอร์ต)'}
            </div>
          </div>
        </div>
      ) : (
        <>
          <div className="plan-card-section">
            <div className="plan-card-section-title">ข้อมูลพื้นฐาน</div>
            <div className="plan-card-section-body">
              {kv('ชื่อ (ไทย)', userProfile.first_name_th || '—')}
              {kv('นามสกุล (ไทย)', userProfile.last_name_th || '—')}
              {kv('ชื่อ (EN)', userProfile.first_name || '—')}
              {kv('นามสกุล (EN)', userProfile.last_name || '—')}
              {userProfile.national_id && kv('เลขบัตรประชาชน', userProfile.national_id)}
              {kv('อีเมล', userProfile.email || '—')}
              {kv('เบอร์โทร', userProfile.phone || '—')}
              {kv('วันเกิด', userProfile.dob ? formatDateThai(userProfile.dob) : '—')}
              {kv('เพศ', userProfile.gender || '—')}
            </div>
          </div>

          {/* ผู้จองร่วม (Co-bookers / Family) */}
          {Array.isArray(userProfile.family) && userProfile.family.length > 0 && userProfile.family.map((member, index) => (
            <div key={member.id || `family-${index}`} className="plan-card-section">
              <div className="plan-card-section-title">
                👥 ผู้จองร่วม {index + 1} {member.type === 'child' ? '(เด็ก)' : '(ผู้ใหญ่)'}
              </div>
              <div className="plan-card-section-body">
                {kv('ชื่อ (ไทย)', member.first_name_th || '—')}
                {kv('นามสกุล (ไทย)', member.last_name_th || '—')}
                {kv('ชื่อ (EN)', member.first_name || '—')}
                {kv('นามสกุล (EN)', member.last_name || '—')}
                {member.national_id && kv('เลขบัตรประชาชน', member.national_id)}
                {kv('วันเกิด', member.date_of_birth ? formatDateThai(member.date_of_birth) : '—')}
                {kv('เพศ', member.gender || '—')}
              </div>
              {showPassportSection && (member.passport_no || member.passport_expiry || (member.passports && member.passports.length > 0)) && (
                <div className="plan-card-section-body" style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(0,0,0,0.06)' }}>
                  <div className="plan-card-small" style={{ marginBottom: '6px', fontWeight: 600, color: '#374151' }}>ข้อมูลพาสปอร์ต</div>
                  {member.passports && member.passports.length > 0 ? (
                    (member.primary_passport || member.passports[0]).passport_no && (
                      <>
                        {kv('เลขพาสปอร์ต', (member.primary_passport || member.passports[0]).passport_no)}
                        {kv('วันหมดอายุ', (member.primary_passport || member.passports[0]).passport_expiry ? formatDateThai((member.primary_passport || member.passports[0]).passport_expiry) : '—')}
                        {(member.primary_passport || member.passports[0]).nationality && kv('สัญชาติ', (member.primary_passport || member.passports[0]).nationality)}
                      </>
                    )
                  ) : (
                    <>
                      {kv('เลขพาสปอร์ต', member.passport_no || '—')}
                      {kv('วันหมดอายุ', member.passport_expiry ? formatDateThai(member.passport_expiry) : '—')}
                      {member.nationality && kv('สัญชาติ', member.nationality)}
                      {member.passport_issue_date && kv('วันออกหนังสือเดินทาง', formatDateThai(member.passport_issue_date))}
                      {member.passport_given_names && kv('ชื่อตามหนังสือเดินทาง (EN)', member.passport_given_names)}
                      {member.passport_surname && kv('นามสกุลตามหนังสือเดินทาง (EN)', member.passport_surname)}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}

          {showPassportSection && (
          <div className="plan-card-section">
            <div className="plan-card-section-title">ข้อมูลพาสปอร์ต</div>
            <div className="plan-card-section-body">
              {kv('เลขพาสปอร์ต', userProfile.passport_no || '—')}
              {kv('วันหมดอายุ', userProfile.passport_expiry ? formatDateThai(userProfile.passport_expiry) : '—')}
              {kv('สัญชาติ', userProfile.nationality || '—')}
              {userProfile.passport_issue_date && kv('วันออกหนังสือเดินทาง', formatDateThai(userProfile.passport_issue_date))}
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
          )}

          {/* Visa Information Section */}
          {userProfile.visa_type && (
            <div className="plan-card-section">
              <div className="plan-card-section-title">🛂 ข้อมูลวีซ่า</div>
              <div className="plan-card-section-body">
                {kv('ประเภทวีซ่า', userProfile.visa_type || '—')}
                {kv('เลขที่วีซ่า', userProfile.visa_number || '—')}
                {kv('ประเทศที่ออกวีซ่า', userProfile.visa_issuing_country || '—')}
                {kv('วันออกวีซ่า', userProfile.visa_issue_date ? formatDateThai(userProfile.visa_issue_date) : '—')}
                {kv('วันหมดอายุวีซ่า', userProfile.visa_expiry_date ? formatDateThai(userProfile.visa_expiry_date) : '—')}
                {kv('ประเภทการเข้าประเทศ', userProfile.visa_entry_type === 'S' ? 'ครั้งเดียว (Single Entry)' : userProfile.visa_entry_type === 'M' ? 'หลายครั้ง (Multiple Entry)' : userProfile.visa_entry_type || '—')}
                {kv('วัตถุประสงค์', userProfile.visa_purpose === 'T' ? 'ท่องเที่ยว' : userProfile.visa_purpose === 'B' ? 'ธุรกิจ' : userProfile.visa_purpose === 'S' ? 'ศึกษา' : userProfile.visa_purpose === 'W' ? 'ทำงาน' : userProfile.visa_purpose === 'TR' ? 'ผ่านทาง' : userProfile.visa_purpose === 'O' ? 'อื่นๆ' : userProfile.visa_purpose || '—')}
              </div>
            </div>
          )}

          {/* Emergency Contact & Hotel Guests */}
          {(userProfile.emergency_contact_name || userProfile.emergency_contact_phone || userProfile.hotel_number_of_guests) && (
            <div className="plan-card-section">
              <div className="plan-card-section-title">🏨 ข้อมูลสำหรับการจอง</div>
              <div className="plan-card-section-body">
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
                {userProfile.hotel_number_of_guests && (
                  <div style={{ marginTop: '12px' }}>{kv('จำนวนผู้เข้าพัก', `${userProfile.hotel_number_of_guests} คน`)}</div>
                )}
              </div>
            </div>
          )}

        </>
      )}
    </div>
  );
}

export function ConfirmBookingCard({ canBook, onConfirm, onPayment, note, isBooking, bookingResult, chatMode = 'normal', agentState = null, onNavigateToBookings = null }) {
  const needsPayment = bookingResult?.needs_payment || bookingResult?.status === 'pending_payment';
  const isConfirmed = bookingResult?.status === 'confirmed' || bookingResult?.status === 'paid';
  const isAlreadyBooked = bookingResult && !bookingResult.ok && bookingResult.already_booked === true;
  
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
          {(needsPayment || isConfirmed) && !isAlreadyBooked && (
            <span className="plan-card-tag">
              {needsPayment ? 'รอชำระเงิน' : 'จองสำเร็จ'}
            </span>
          )}
          {isAlreadyBooked && (
            <span className="plan-card-tag" style={{ background: '#fef3c7', color: '#92400e' }}>
              จองไปแล้ว
            </span>
          )}
        </div>
      </div>

      {isBooking ? (
        <div className="plan-card-section">
          <div className="plan-card-section-body plan-card-small">
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span className="plan-card-spinner" />
              <span>กำลังดำเนินการ...</span>
            </div>
            <div style={{ marginTop: '8px', opacity: 0.8 }}>
              {needsPayment ? 'กำลังสร้างการจอง...' : 'กำลังชำระเงินและจอง...'}
            </div>
          </div>
        </div>
      ) : bookingResult && isAlreadyBooked ? (
        <div className="plan-card-section">
          <div className="plan-card-section-title" style={{ color: '#92400e' }}>
            📋 จองไปแล้ว
          </div>
          <div className="plan-card-section-body plan-card-small">
            <p style={{ margin: 0 }}>{bookingResult.message}</p>
            {onNavigateToBookings && (
              <div className="plan-card-footer summary-footer" style={{ marginTop: '16px' }}>
                <button
                  type="button"
                  className="plan-card-button"
                  style={{ background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}
                  onClick={onNavigateToBookings}
                >
                  📋 ไปที่ My Bookings
                </button>
              </div>
            )}
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
                  {moneyThb(bookingResult.total_price, bookingResult.currency) || new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB', minimumFractionDigits: 0 }).format(bookingResult.total_price)}
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

          {/* ✅ Agent Mode: ซ่อนปุ่มยืนยัน (ระบบจองให้อัตโนมัติ) — ไม่แสดงข้อความ Agent Mode ตรงนี้ ให้แชทแจ้งว่าจองแล้ว */}
          {!isAutoBooked && !isAutoBookingInProgress && (
            <div className="plan-card-footer summary-footer">
              <button
                className={`plan-card-button ${!canBook ? 'summary-disabled' : ''}`}
                disabled={!canBook || isBooking}
                onClick={onConfirm}
              >
                ✅ ยืนยันการจอง
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ✅ Final Trip Summary - สรุปครบถ้วนก่อนจอง
// ✅ ไม่แสดงการ์ด "สรุปทริปสุดท้าย พร้อมจอง" ตามที่ผู้ใช้ขอให้ลบออก
export function FinalTripSummary({ plan, travelSlots, userProfile, cachedOptions, cacheValidation, workflowValidation }) {
  return null;
  if (!plan) return null;

  const flight = plan.flight || plan.travel?.flights || {};
  const hotelRaw = plan.hotel || plan.accommodation || {};
  const hotel = hotelRaw;
  const transportRaw = plan.transport || plan.travel?.ground_transport || {};
  const transport = Array.isArray(transportRaw) ? { segments: transportRaw } : transportRaw;
  const currency = plan.currency || plan.flight?.currency || plan.travel?.flights?.currency || plan.hotel?.currency || plan.accommodation?.currency || 'THB';
  // ✅ สรุปจำนวนตัวเลือกจาก plan (fallback เมื่อ cache แสดง 0 ทั้งหมด)
  const outboundList = flight.outbound || plan.travel?.flights?.outbound || [];
  const inboundList = flight.inbound || plan.travel?.flights?.inbound || [];
  const accommodationList = hotel.segments || (Array.isArray(plan.accommodation?.segments) ? plan.accommodation.segments : []) || [];
  const groundList = transport.segments || (Array.isArray(plan.travel?.ground_transport) ? plan.travel.ground_transport : []) || [];
  const summaryFromPlan = {
    flights_outbound: Array.isArray(outboundList) ? outboundList.length : (outboundList ? 1 : 0),
    flights_inbound: Array.isArray(inboundList) ? inboundList.length : (inboundList ? 1 : 0),
    ground_transport: Array.isArray(groundList) ? groundList.length : (groundList ? 1 : 0),
    accommodation: Array.isArray(accommodationList) ? accommodationList.length : (accommodationList ? 1 : 0),
  };
  const cacheSummary = cacheValidation?.summary;
  const cacheHasCounts = cacheSummary && ( (cacheSummary.flights_outbound || 0) + (cacheSummary.flights_inbound || 0) + (cacheSummary.ground_transport || 0) + (cacheSummary.accommodation || 0) > 0 );
  const effectiveSummary = cacheHasCounts ? cacheSummary : summaryFromPlan;
  const summaryLabel = cacheHasCounts ? '📊 สรุปตัวเลือกที่แคช:' : '📊 สรุปตัวเลือกที่เลือก:';
  // ✅ ราคารวม: จาก plan หรือคำนวณจาก flight+hotel+transport แบบ catalog
  const totalPrice = typeof plan.total_price === 'number' ? plan.total_price
    : typeof plan.price === 'number' ? plan.price
    : (() => {
        const f = (flight.total_price ?? flight.price_total) || 0;
        const h = (hotel.total_price ?? hotel.price_total) || 0;
        const t = (transport.price ?? transport.price_amount) || 0;
        return Number(f) + Number(h) + Number(t);
      })();

  const flightSegments = flight.segments || [];
  const hotelSegments = hotel.segments || [];
  const transportSegments = transport.segments || [];
  // ✅ ถ้าไม่มี outbound/inbound แยกจาก API ให้แยกจาก segments เพื่อแสดงขาไป/ขากลับ
  const hasOutboundInboundFinal = (flight.outbound?.length > 0) || (flight.inbound?.length > 0);
  const splitFinal = hasOutboundInboundFinal ? null : splitFlightSegmentsToOutboundInbound(flightSegments, travelSlots);
  const outboundSegmentsFinal = hasOutboundInboundFinal ? (flight.outbound || []) : (splitFinal?.outbound || []);
  const inboundSegmentsFinal = hasOutboundInboundFinal ? (flight.inbound || []) : (splitFinal?.inbound || []);

  // ✅ ตรวจสอบว่ามีข้อมูลอะไรบ้าง
  const hasFinalFlightData = flightSegments.length > 0 || outboundSegmentsFinal.length > 0;
  const hasFinalHotelData = hotelSegments.length > 0 || !!hotel.hotelName;

  // Format dates
  const startDate = formatThaiDate(travelSlots?.departure_date || travelSlots?.start_date || travelSlots?.check_in);
  const returnDate = formatThaiDate(travelSlots?.return_date || travelSlots?.end_date || travelSlots?.check_out);
  const nights = travelSlots?.nights || 0;
  const adults = travelSlots?.adults || 1;
  const children = travelSlots?.children || 0;

  return (
    <div className="plan-card plan-card-final-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">
            {hasFinalFlightData && hasFinalHotelData ? '📋 สรุปทริปสุดท้าย (เที่ยวบิน + ที่พัก)' :
             hasFinalFlightData ? '📋 สรุปทริปสุดท้าย (เที่ยวบิน)' :
             hasFinalHotelData ? '📋 สรุปทริปสุดท้าย (ที่พัก)' :
             '📋 สรุปทริปสุดท้าย'}
          </span>
          <span className="plan-card-tag final-summary-tag">พร้อมจอง</span>
        </div>
      </div>

      {/* Flight Details */}
      {(flightSegments.length > 0 || outboundSegmentsFinal.length > 0 || inboundSegmentsFinal.length > 0) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>
          <div className="plan-card-section-body">
            {/* ✅ แสดงขาไป (Outbound) */}
            {outboundSegmentsFinal.length > 0 && (
              <div style={{ marginBottom: inboundSegmentsFinal.length > 0 ? '20px' : '0', paddingBottom: inboundSegmentsFinal.length > 0 ? '16px' : '0', borderBottom: inboundSegmentsFinal.length > 0 ? '1px solid #e5e7eb' : 'none' }}>
                <div style={{ fontWeight: 600, marginBottom: '12px', color: '#2563eb', fontSize: '15px' }}>🛫 ขาไป</div>
                {outboundSegmentsFinal.map((seg, idx) => {
                  const isLast = idx === outboundSegmentsFinal.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #3b82f6' }}>
                      {seg.carrier && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <AirlineLogo carrierCode={seg.carrier} size={36} />
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(seg.carrier)}</div>
                            {seg.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{seg.carrier}{seg.number}</div>}
                          </div>
                        </div>
                      )}
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
            {inboundSegmentsFinal.length > 0 && (
              <div>
                <div style={{ fontWeight: 600, marginBottom: '12px', color: '#2563eb', fontSize: '15px' }}>🛬 ขากลับ</div>
                {inboundSegmentsFinal.map((seg, idx) => {
                  const isLast = idx === inboundSegmentsFinal.length - 1;
                  return (
                    <div key={idx} style={{ marginBottom: isLast ? '0' : '12px', paddingLeft: '8px', borderLeft: '3px solid #10b981' }}>
                      {seg.carrier && (
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                          <AirlineLogo carrierCode={seg.carrier} size={36} />
                          <div>
                            <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(seg.carrier)}</div>
                            {seg.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{seg.carrier}{seg.number}</div>}
                          </div>
                        </div>
                      )}
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
            
            {/* ✅ Fallback: แสดงแบบเดิมถ้าแยกขาไป/ขากลับไม่ได้ */}
            {outboundSegmentsFinal.length === 0 && inboundSegmentsFinal.length === 0 && flightSegments.length > 0 && (
              <>
                {flightSegments.map((seg, idx) => (
                  <div key={idx} style={{ marginBottom: idx < flightSegments.length - 1 ? '12px' : '0' }}>
                    {seg.carrier && (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px', flexWrap: 'wrap' }}>
                        <AirlineLogo carrierCode={seg.carrier} size={36} />
                        <div>
                          <div style={{ fontWeight: 600, fontSize: '14px' }}>{getAirlineName(seg.carrier)}</div>
                          {seg.number && <div style={{ fontSize: '12px', opacity: 0.85 }}>{seg.carrier}{seg.number}</div>}
                        </div>
                      </div>
                    )}
                    {seg.from && seg.to && kv(`เส้นทาง (${idx + 1})`, `${seg.from} → ${seg.to}`)}
                    {seg.departure && kv('วัน-เวลาออก', formatThaiDateTime(seg.departure))}
                    {seg.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(seg.arrival))}
                    {seg.duration && kv('ระยะเวลา', formatDuration(seg.duration))}
                  </div>
                ))}
              </>
            )}
            
            {/* ✅ ราคารวม */}
            {flight.total_price && kv('ราคา', moneyThb(flight.total_price, currency))}
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
                  {seg.price && kv('ราคา', moneyThb(seg.price, seg.currency || currency))}
                </div>
              ))
            ) : (
              <>
                {hotel.hotelName && kv('ชื่อโรงแรม', hotel.hotelName)}
                {hotel.city && kv('เมือง', hotel.city)}
                {hotel.nights && kv('จำนวนคืน', `${hotel.nights} คืน`)}
                {hotel.boardType && kv('ประเภทอาหาร', hotel.boardType)}
                {hotel.address && kv('ที่อยู่', hotel.address)}
                {(hotel.total_price != null || hotel.price_total != null) && kv('ราคา', moneyThb(hotel.total_price ?? hotel.price_total, currency))}
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
                  {seg.price && kv('ราคา', moneyThb(seg.price, seg.currency || currency))}
                </div>
              ))
            ) : (
              <>
                {transport.type && kv('ประเภท', transport.type)}
                {transport.route && kv('เส้นทาง', transport.route)}
                {transport.duration && kv('ระยะเวลา', transport.duration)}
                {(transport.price != null || transport.price_amount != null) && kv('ราคา', moneyThb(transport.price ?? transport.price_amount, currency))}
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
            {plan.price_breakdown.flight && kv('ไฟท์บิน', moneyThb(plan.price_breakdown.flight, currency))}
            {plan.price_breakdown.hotel && kv('ที่พัก', moneyThb(plan.price_breakdown.hotel, currency))}
            {plan.price_breakdown.transport && kv('การเดินทาง', moneyThb(plan.price_breakdown.transport, currency))}
            {plan.price_breakdown.car && kv('รถเช่า', moneyThb(plan.price_breakdown.car, currency))}
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
          <div className="plan-card-price-value">{moneyThb(totalPrice, currency)}</div>
        </div>
        <div className="summary-note">ราคาอ้างอิงจาก Amadeus Search (production){currency !== 'THB' ? ' · แสดงเป็นบาท (อัตราอ้างอิง)' : ''}</div>
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
          {(cacheValidation.summary || effectiveSummary) && (
            <div style={{ marginTop: '12px', padding: '8px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'rgba(255, 255, 255, 0.8)', marginBottom: '4px' }}>
                {summaryLabel}
              </div>
              <div style={{ fontSize: '11px', color: 'rgba(255, 255, 255, 0.7)', lineHeight: '1.6' }}>
                ✈️ เที่ยวบินขาไป: {effectiveSummary.flights_outbound ?? 0} ตัวเลือก<br/>
                ✈️ เที่ยวบินขากลับ: {effectiveSummary.flights_inbound ?? 0} ตัวเลือก<br/>
                🚗 การเดินทาง: {effectiveSummary.ground_transport ?? 0} ตัวเลือก<br/>
                🏨 ที่พัก: {effectiveSummary.accommodation ?? 0} ตัวเลือก
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
