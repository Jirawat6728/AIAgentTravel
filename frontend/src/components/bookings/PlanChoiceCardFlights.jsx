/**
 * PlanChoiceCard เฉพาะเที่ยวบิน (ไป-กลับ ทุกรูปแบบ)
 * แยกอิสระจาก PlanChoiceCard เพื่อแก้บั๊กและแสดงผลเที่ยวบินเท่านั้น
 */
import React, { useState } from 'react';
import { formatMoney, formatDuration } from './planChoiceCardUtils';
import './PlanChoiceCard.css';

// ---------- Flight-only helpers (แยกอิสระ) ----------
function getAirportName(code) {
  if (!code) return '';
  const airportNames = {
    'BKK': 'ท่าอากาศยานสุวรรณภูมิ', 'DMK': 'ท่าอากาศยานดอนเมือง', 'CNX': 'ท่าอากาศยานเชียงใหม่',
    'HKT': 'ท่าอากาศยานภูเก็ต', 'KIX': 'ท่าอากาศยานคันไซ', 'NRT': 'ท่าอากาศยานนาริตะ', 'HND': 'ท่าอากาศยานฮาเนดะ',
    'ICN': 'ท่าอากาศยานอินชอน', 'SIN': 'ท่าอากาศยานชางงี', 'KUL': 'ท่าอากาศยานกัวลาลัมเปอร์',
    'HKG': 'ท่าอากาศยานฮ่องกง', 'TPE': 'ท่าอากาศยานไต้หวัน', 'PVG': 'ท่าอากาศยานเซี่ยงไฮ้ผู่ตง', 'PEK': 'ท่าอากาศยานปักกิ่ง',
  };
  return airportNames[code.toUpperCase()] || code;
}

function calculateLayoverTime(prevSegment, nextSegment) {
  if (!prevSegment || !nextSegment) return null;
  const prevArrival = prevSegment.arrive_at || prevSegment.depart_at;
  const nextDeparture = nextSegment.depart_at || nextSegment.depart_at;
  if (!prevArrival || !nextDeparture) return null;
  try {
    const diffMs = new Date(nextDeparture).getTime() - new Date(prevArrival).getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    if (diffHours < 0 || diffMinutes < 0) return null;
    return diffHours > 0 ? `${diffHours}ชม ${diffMinutes}นาที` : `${diffMinutes}นาที`;
  } catch (e) { return null; }
}

function getAirlineLogoUrl(carrierCode, attempt = 1) {
  if (!carrierCode) return null;
  const code = carrierCode.toUpperCase();
  const urls = [
    `https://logos.skyscnr.com/images/airlines/favicon/${code}.png`,
    `https://avicon.io/api/airlines/${code}`,
    `https://pics.avs.io/200/200/${code}.png`,
  ];
  return urls[Math.min(attempt - 1, urls.length - 1)] || null;
}

function AirlineLogo({ carrierCode, size = 40 }) {
  const [attempt, setAttempt] = useState(1);
  const [error, setError] = useState(false);
  const url = getAirlineLogoUrl(carrierCode, attempt);
  const handleError = () => {
    if (attempt < 3) setAttempt((a) => a + 1);
    else setError(true);
  };
  if (!carrierCode || error || !url) {
    return (
      <div style={{ width: size, height: size, borderRadius: 6, background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 600, color: '#fff' }}>
        {carrierCode || 'N/A'}
      </div>
    );
  }
  return <img src={url} alt={carrierCode} style={{ width: size, height: size, borderRadius: 6, objectFit: 'contain' }} onError={handleError} />;
}

function getAirlineName(code) {
  if (!code) return 'Unknown';
  const names = { 'TG': 'Thai Airways', 'FD': 'Thai AirAsia', 'SL': 'Thai Lion Air', 'PG': 'Bangkok Airways', 'VZ': 'Thai Vietjet', 'SQ': 'Singapore Airlines', 'JL': 'Japan Airlines', 'NH': 'All Nippon Airways', 'KE': 'Korean Air', 'CX': 'Cathay Pacific', 'VN': 'Vietnam Airlines', 'AK': 'AirAsia', 'D7': 'AirAsia X' };
  return names[code.toUpperCase()] || code;
}

function getAircraftName(code) {
  if (!code) return '';
  const names = { '738': 'Boeing 737-800', '320': 'Airbus A320', '321': 'Airbus A321', '333': 'Airbus A330-300', '77W': 'Boeing 777-300ER', '789': 'Boeing 787-9' };
  return names[code.toUpperCase()] || `เครื่องบิน ${code}`;
}

function getFlightType(segments) {
  if (!segments || segments.length === 0) return 'บินตรง';
  return segments.length > 1 ? 'ต่อเครื่อง' : 'บินตรง';
}

function getArrivalTimeDisplay(arriveAt, arrivePlus) {
  if (!arriveAt) return '';
  let timeStr = typeof arriveAt === 'string' && arriveAt.includes('T') ? arriveAt.split('T')[1]?.slice(0, 5) || '' : (arriveAt || '');
  return arrivePlus ? `${timeStr} ${arrivePlus}` : timeStr;
}

function getFirstSegment(flight) {
  return flight?.segments?.length ? flight.segments[0] : null;
}
function getLastSegment(flight) {
  return flight?.segments?.length ? flight.segments[flight.segments.length - 1] : null;
}
function stopsLabel(flight) {
  const n = flight?.segments?.length || 0;
  return n === 0 ? null : n - 1 === 0 ? 'Non-stop' : `${n - 1} stop`;
}
function carriersLabel(flight) {
  const segs = flight?.segments || [];
  const carriers = [];
  for (const s of segs) { const c = s?.carrier; if (c && !carriers.includes(c)) carriers.push(c); }
  return carriers.length ? carriers.join(', ') : null;
}

export default function PlanChoiceCardFlights({ choice, onSelect }) {
  const [showDetails, setShowDetails] = useState(false);
  const { id, label, tags, recommended, flight, flight_details, currency, total_price, total_price_text, price, price_breakdown, title } = choice || {};
  const displayCurrency = price_breakdown?.currency || currency || flight?.currency || 'THB';
  // ✅ ราคารวม: total_price หรือ price (option) หรือ flight.price_total — ใช้ข้อมูลจริงจาก API
  const resolvedTotal = typeof total_price === 'number' ? total_price : typeof price === 'number' ? price : (typeof flight?.price_total === 'number' ? flight.price_total : null);
  const hasRealPrice = resolvedTotal != null && Number(resolvedTotal) > 0;
  const displayTotalPrice = hasRealPrice
    ? `${displayCurrency} ${Number(resolvedTotal).toLocaleString('th-TH')}`
    : (total_price_text || 'ราคาต้องสอบถาม');

  const firstSeg = getFirstSegment(flight);
  const lastSeg = getLastSegment(flight);
  const flightRoute = firstSeg && lastSeg ? `${firstSeg.from} → ${lastSeg.to}` : null;
  const flightStops = stopsLabel(flight);
  const flightCarriers = carriersLabel(flight);
  const flightPrice = formatMoney(typeof flight?.price_total === 'number' ? flight.price_total : null, flight?.currency || displayCurrency);

  let totalJourneyTime = null;
  if (firstSeg && lastSeg && flight?.segments?.length > 0) {
    try {
      const firstDepart = firstSeg.depart_at || firstSeg.depart_time;
      let lastArrive = lastSeg.arrive_at || lastSeg.arrive_time;
      if (lastArrive && lastSeg.arrive_plus) {
        const d = new Date(lastArrive);
        const m = String(lastSeg.arrive_plus).match(/\+(\d+)/);
        if (m) d.setDate(d.getDate() + parseInt(m[1], 10));
        lastArrive = d.toISOString();
      }
      if (firstDepart && lastArrive) {
        const diffMs = new Date(lastArrive).getTime() - new Date(firstDepart).getTime();
        if (diffMs > 0) {
          const h = Math.floor(diffMs / (1000 * 60 * 60));
          const m = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
          totalJourneyTime = h > 0 ? `${h}ชม ${m}นาที` : `${m}นาที`;
        }
      }
    } catch (e) {}
  }

  if (!flight || !flight.segments || flight.segments.length === 0) {
    return (
      <div className="plan-card">
        <div className="plan-card-header"><span className="plan-card-label">เที่ยวบิน {title || id}</span></div>
        <p className="plan-card-desc">ไม่มีข้อมูลเที่ยวบิน</p>
        <div className="plan-card-footer">
          <button className="plan-card-button" onClick={() => onSelect && onSelect(id)}>เลือกช้อยส์ {id}</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`plan-card ${recommended ? 'plan-card-recommended' : ''}`}>
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">{title || `เที่ยวบิน ${id}${label ? ` — ${label}` : ''}`}</span>
          {recommended && (!tags || !tags.includes('แนะนำ')) && <span className="plan-card-tag">แนะนำ</span>}
          {(choice?.is_non_stop || flightStops === 'Non-stop') && (!tags || !tags.includes('บินตรง')) && (
            <span className="plan-card-tag" style={{ background: 'rgba(227, 242, 253, 0.3)', color: '#1976d2', marginLeft: 6, fontSize: 13, padding: '3px 10px' }}>✈️ บินตรง</span>
          )}
        </div>
        {tags && Array.isArray(tags) && tags.length > 0 && (
          <div className="plan-card-tags">
            {[...new Set(tags)].filter(t => t !== 'แนะนำ' || !recommended).filter(t => t !== 'บินตรง' || flightStops !== 'Non-stop').map((tag, idx) => (
              <span key={idx} className="plan-tag-pill">{tag}</span>
            ))}
          </div>
        )}
      </div>

      <div className="plan-card-section">
        <div className="plan-card-section-title">✈️ รายละเอียดเที่ยวบิน</div>
        <div className="plan-card-section-body">
          {firstSeg && lastSeg && (
            <div style={{ marginBottom: 16, padding: 12, background: 'rgba(255,255,255,0.08)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.15)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <AirlineLogo carrierCode={firstSeg.carrier} size={40} />
                  <div>
                    <div style={{ fontSize: 14, fontWeight: 600 }}>{getAirlineName(firstSeg.carrier)}</div>
                    <div style={{ fontSize: 12, opacity: 0.7 }}>{firstSeg.carrier}{firstSeg.flight_number || ''}</div>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span style={{ fontSize: 16, fontWeight: 600 }}>{firstSeg.depart_time || 'N/A'}</span>
                    <span style={{ opacity: 0.6 }}>–</span>
                    <span style={{ fontSize: 16, fontWeight: 600 }}>{getArrivalTimeDisplay(lastSeg.arrive_at, lastSeg.arrive_plus) || lastSeg.arrive_time || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', fontSize: 13, opacity: 0.8 }}>
                    {totalJourneyTime && <span>⏱️ {totalJourneyTime}</span>}
                    {flightRoute && <><span>•</span><span>📍 {flightRoute}</span></>}
                    {flightStops && <span style={{ padding: '2px 6px', borderRadius: 4, fontSize: 12, fontWeight: 500, background: flightStops === 'Non-stop' ? 'rgba(74,222,128,0.2)' : 'rgba(255,193,7,0.2)', color: flightStops === 'Non-stop' ? '#4ade80' : '#ffc107' }}>{getFlightType(flight.segments) === 'บินตรง' ? '✈️ บินตรง' : '🔀 ต่อเครื่อง'}</span>}
                  </div>
                  {flight.segments.length > 1 && (
                    <div style={{ marginTop: 6, fontSize: 12, opacity: 0.7 }}>
                      {flight.segments.slice(0, -1).map((seg, idx) => {
                        const layover = calculateLayoverTime(seg, flight.segments[idx + 1]);
                        return layover ? <span key={idx} style={{ marginRight: 8 }}>{seg.to ? `รอที่ ${seg.to}` : 'รอต่อเครื่อง'} ({layover})</span> : null;
                      })}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right', minWidth: 100 }}>{flightPrice && <div style={{ fontSize: 18, fontWeight: 700 }}>{flightPrice}</div>}</div>
              </div>
            </div>
          )}

          {flight.segments.map((seg, idx) => {
            const nextSeg = flight.segments[idx + 1];
            const layoverTime = calculateLayoverTime(seg, nextSeg);
            return (
              <div key={idx} style={{ marginBottom: idx < flight.segments.length - 1 ? 12 : 0 }}>
                <div style={{ fontWeight: 600, marginBottom: 6, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span>{seg.direction === 'ขาไป' ? '🛫' : seg.direction === 'ขากลับ' ? '🛬' : '✈️'}</span>
                  <span>{seg.direction || (idx === 0 ? 'ขาไป' : (idx === 1 && flight.segments.length === 2 ? 'ขากลับ' : `เที่ยว ${idx + 1}`))}</span>
                </div>
                <div className="plan-card-small">สายการบิน: {getAirlineName(seg.carrier)} {seg.carrier && seg.flight_number ? ` • ${seg.carrier}${seg.flight_number}` : ''}</div>
                <div className="plan-card-small">เส้นทาง: {seg.from || '-'} → {seg.to || '-'}</div>
                <div className="plan-card-small">ออก: {seg.depart_time || '-'} → ถึง: {seg.arrive_time || '-'}{seg.arrive_plus ? ` ${seg.arrive_plus}` : ''}</div>
                {seg.aircraft_code && <div className="plan-card-small">เครื่อง: {getAircraftName(seg.aircraft_code)}</div>}
                {seg.duration && <div className="plan-card-small">ระยะเวลา: {formatDuration(seg.duration)}</div>}
                {layoverTime && (
                  <div className="plan-card-small" style={{ marginTop: 6, color: 'rgba(255,215,0,0.95)', padding: '4px 8px', background: 'rgba(255,215,0,0.2)', borderRadius: 4 }}>
                    ⏱️ รอคอยต่อเครื่อง: {layoverTime}{seg.to ? ` ที่ ${getAirportName(seg.to)}` : ''}
                  </div>
                )}
              </div>
            );
          })}

          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.25)' }}>
            {(flightStops || flightCarriers) && <div className="plan-card-small" style={{ marginBottom: 8 }}>{flightStops}{flightCarriers ? ` • ${flightCarriers}` : ''}</div>}
            {totalJourneyTime && <div className="plan-card-small" style={{ fontWeight: 600 }}>เวลาเดินทางทั้งหมด: {totalJourneyTime}</div>}
            {flightPrice && <div className="plan-card-small" style={{ marginTop: 6, fontWeight: 600 }}>ราคารวม: {flightPrice}</div>}
          </div>

          {flight_details && (
            <button type="button" onClick={() => setShowDetails(!showDetails)} style={{ marginTop: 8, padding: '6px 12px', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 6, color: '#fff', fontSize: 14, cursor: 'pointer' }}>
            {showDetails ? '▼ ซ่อนรายละเอียด' : '▶ ดูรายละเอียดเพิ่มเติม'}
          </button>
          )}
        </div>
      </div>

      <div className="plan-card-footer">
        {displayTotalPrice && <div className="plan-card-price">{displayTotalPrice}</div>}
        <button className="plan-card-button" onClick={() => onSelect && onSelect(id)}>เลือกช้อยส์ {id}</button>
      </div>
    </div>
  );
}
