/**
 * PlanChoiceCard เฉพาะเที่ยวบิน (ไป-กลับ ทุกรูปแบบ)
 * แยกอิสระจาก PlanChoiceCard เพื่อแก้บั๊กและแสดงผลเที่ยวบินเท่านั้น
 */
import React, { useState } from 'react';
import { formatMoney, formatDuration, parseDurationToHours, calculateCO2e } from './planChoiceCardUtils';
import { AIRLINE_NAMES, AIRLINE_DOMAINS } from '../../data/airlineNames';
import { getAirportDisplay } from '../../data/airportNames';
import './PlanChoiceCard.css';

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

// IATA → โดเมน (ใช้ AIRLINE_DOMAINS จาก shared data)
const getDuffelLogoUrl = (code) => {
  const c = String(code || '').toUpperCase();
  if (!c || c.length !== 2) return null;
  return `https://assets.duffel.com/img/airlines/for-light-background/full-color-logo/${c}.svg`;
};
const getKiwiLogoUrl = (code) => `https://images.kiwi.com/airlines/64/${String(code).toUpperCase()}.png`;
const getClearbitLogoUrl = (code) => {
  const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
  return domain ? `https://logo.clearbit.com/${domain}` : null;
};
const getGoogleFaviconUrl = (code) => {
  const domain = AIRLINE_DOMAINS[String(code).toUpperCase()];
  return domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=64` : null;
};

function AirlineLogo({ carrierCode, size = 40 }) {
  const [showFallback, setShowFallback] = useState(false);
  const kiwiUrl = getKiwiLogoUrl(carrierCode);
  const duffelUrl = getDuffelLogoUrl(carrierCode);
  const clearbitUrl = getClearbitLogoUrl(carrierCode);
  const googleFaviconUrl = getGoogleFaviconUrl(carrierCode);
  const initialSrc = duffelUrl || kiwiUrl;

  const handleError = (e) => {
    const img = e.target;
    const src = (img.src || '').toLowerCase();
    const isDuffel = src.includes('assets.duffel.com');
    const isKiwi = src.includes('images.kiwi.com');
    const isClearbit = src.includes('logo.clearbit.com');
    if (isDuffel && kiwiUrl) { img.src = kiwiUrl; return; }
    if (isKiwi && clearbitUrl) { img.src = clearbitUrl; return; }
    if (isClearbit && googleFaviconUrl) { img.src = googleFaviconUrl; return; }
    setShowFallback(true);
    img.style.display = 'none';
  };

  if (!carrierCode || showFallback || !initialSrc) {
    return (
      <div style={{ width: size, height: size, borderRadius: 6, background: 'rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: Math.max(10, size * 0.3), fontWeight: 600, color: '#fff' }}>
        ✈️ {carrierCode || 'N/A'}
      </div>
    );
  }
  return (
    <>
      <img
        src={initialSrc}
        alt={carrierCode}
        style={{ width: size, height: size, borderRadius: 6, objectFit: 'contain', display: showFallback ? 'none' : 'block' }}
        onError={handleError}
      />
    </>
  );
}

function getAirlineName(code) {
  if (!code) return 'Unknown';
  return AIRLINE_NAMES[String(code).toUpperCase()] || code;
}

function getAircraftName(code) {
  if (!code) return '';
  const names = {
    '738': 'Boeing 737-800', '739': 'Boeing 737-900', '73H': 'Boeing 737-800', '73J': 'Boeing 737 MAX 8',
    '320': 'Airbus A320', '321': 'Airbus A321', '333': 'Airbus A330-300', '77W': 'Boeing 777-300ER',
    '788': 'Boeing 787-8', '789': 'Boeing 787-9'
  };
  return names[String(code).toUpperCase()] || `เครื่องบิน ${code}`;
}

function getFlightType(segments) {
  if (!segments || segments.length === 0) return 'บินตรง';
  return segments.length > 1 ? 'ต่อเครื่อง' : 'บินตรง';
}

function getCabinDisplay(cabin) {
  if (!cabin) return null;
  const c = String(cabin).toUpperCase();
  const map = {
    ECONOMY: 'ชั้นประหยัด',
    PREMIUM_ECONOMY: 'ชั้นประหยัดพรีเมียม',
    BUSINESS: 'ชั้นธุรกิจ',
    FIRST: 'ชั้นหนึ่ง',
  };
  return map[c] || cabin;
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
  const flightDirection = choice?.flight_direction ?? (firstSeg?.direction && String(firstSeg.direction).includes('ขากลับ') ? 'inbound' : firstSeg?.direction && String(firstSeg.direction).includes('ขาไป') ? 'outbound' : null);
  const isOutbound = flightDirection === 'outbound';
  const isInbound = flightDirection === 'inbound';
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
          {isOutbound && (
            <span className="plan-card-tag" style={{ background: 'rgba(33, 150, 243, 0.25)', color: '#1976d2', marginLeft: 6, fontSize: 13, padding: '3px 10px' }}>🛫 ขาไป</span>
          )}
          {isInbound && (
            <span className="plan-card-tag" style={{ background: 'rgba(156, 39, 176, 0.25)', color: '#7b1fa2', marginLeft: 6, fontSize: 13, padding: '3px 10px' }}>🛬 ขากลับ</span>
          )}
          {(choice?.is_non_stop || flightStops === 'Non-stop') && (!tags || !tags.includes('บินตรง')) && (
            <span className="plan-card-tag" style={{ background: 'rgba(227, 242, 253, 0.3)', color: '#1976d2', marginLeft: 6, fontSize: 13, padding: '3px 10px' }}>✈️ บินตรง</span>
          )}
        </div>
        {tags && Array.isArray(tags) && tags.length > 0 && (
          <div className="plan-card-tags">
            {[...new Set(tags)]
              .filter(t => !['Amadeus', 'ราคาจริง', 'จองได้ทันที'].includes(t))
              .filter(t => t !== 'แนะนำ' || !recommended)
              .filter(t => t !== 'บินตรง' || flightStops !== 'Non-stop')
              .map((tag, idx) => (
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
                        return layover ? <span key={idx} style={{ marginRight: 8 }}>{seg.to ? `รอที่ ${getAirportDisplay(seg.to)}` : 'รอต่อเครื่อง'} ({layover})</span> : null;
                      })}
                    </div>
                  )}
                </div>
                <div style={{ textAlign: 'right', minWidth: 100 }}>{flightPrice && <div style={{ fontSize: 18, fontWeight: 700 }}>{flightPrice}</div>}</div>
              </div>
            </div>
          )}

          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255,255,255,0.25)' }}>
            {(flightStops || flightCarriers) && <div className="plan-card-small" style={{ marginBottom: 8 }}>{flightStops}{flightCarriers ? ` • ${flightCarriers}` : ''}</div>}
            {totalJourneyTime && <div className="plan-card-small" style={{ fontWeight: 600 }}>เวลาเดินทางทั้งหมด: {totalJourneyTime}</div>}
            {(getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)) && (
              <div className="plan-card-small" style={{ marginTop: 6, fontWeight: 600 }}>ชั้นโดยสาร: {getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)}</div>
            )}
          </div>

          {/* ปุ่มดูรายละเอียดเพิ่มเติม — แสดงเมื่อมี segments */}
          {flight?.segments?.length > 0 && (
            <button type="button" onClick={() => setShowDetails(!showDetails)} style={{ marginTop: 8, padding: '6px 12px', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 6, color: '#fff', fontSize: 14, cursor: 'pointer' }}>
              {showDetails ? '▼ ซ่อนรายละเอียด' : '▶ ดูรายละเอียดเพิ่มเติม'}
            </button>
          )}

          {/* บล็อกรายละเอียดทั้งหมด — ยืดหดตามข้อมูลด้วยแอนิเมชัน */}
          <div className={`plan-card-details-expandable ${showDetails ? 'is-expanded' : ''}`}>
            <div style={{ padding: 14, background: 'rgba(0,0,0,0.2)', borderRadius: 8, border: '1px solid rgba(255,255,255,0.2)' }}>
              <div className="plan-card-section-title" style={{ marginBottom: 10 }}>📋 รายละเอียดเที่ยวบินทั้งหมด</div>
              {/* ส่วนข้อมูลเที่ยวบินแต่ละขา (ขาไป/ขากลับ) — แบบในรูป */}
              {flight.segments.map((seg, idx) => {
                const nextSeg = flight.segments[idx + 1];
                const layoverTime = calculateLayoverTime(seg, nextSeg);
                return (
                  <div key={idx} style={{ marginBottom: idx < flight.segments.length - 1 ? 16 : 12, paddingBottom: idx < flight.segments.length - 1 ? 16 : 0, borderBottom: idx < flight.segments.length - 1 ? '1px solid rgba(255,255,255,0.15)' : 'none' }}>
                    <div style={{ fontWeight: 600, marginBottom: 8, fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span>{seg.direction === 'ขาไป' ? '🛫' : seg.direction === 'ขากลับ' ? '🛬' : '✈️'}</span>
                      <span>{seg.direction || (idx === 0 ? 'ขาไป' : (idx === 1 && flight.segments.length === 2 ? 'ขากลับ' : `เที่ยว ${idx + 1}`))}</span>
                    </div>
                    <div className="plan-card-small" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                      <AirlineLogo carrierCode={seg.carrier} size={28} />
                      <span>สายการบิน: {getAirlineName(seg.carrier)} {seg.carrier && seg.flight_number ? ` • ${seg.carrier}${seg.flight_number}` : ''}</span>
                    </div>
                    <div className="plan-card-small">เส้นทาง: {seg.from || '-'} → {seg.to || '-'}</div>
                    <div className="plan-card-small">ออก: {seg.depart_time || '-'} → ถึง: {getArrivalTimeDisplay(seg.arrive_at, seg.arrive_plus) || seg.arrive_time || '-'}</div>
                    {seg.aircraft_code && <div className="plan-card-small">เครื่อง: {getAircraftName(seg.aircraft_code)}</div>}
                    {seg.duration && <div className="plan-card-small">ระยะเวลา: {formatDuration(seg.duration)}</div>}
                    {layoverTime && (
                      <div className="plan-card-small" style={{ marginTop: 6, color: 'rgba(255,215,0,0.95)', padding: '4px 8px', background: 'rgba(255,215,0,0.2)', borderRadius: 4 }}>
                        ⏱️ รอคอยต่อเครื่อง: {layoverTime}{seg.to ? ` ที่ ${getAirportDisplay(seg.to)}` : ''}
                      </div>
                    )}
                  </div>
                );
              })}
              <div style={{ marginTop: 12, paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                {(flightStops || flightCarriers) && <div className="plan-card-small" style={{ marginBottom: 4 }}>{flightStops}{flightCarriers ? ` • ${flightCarriers}` : ''}</div>}
                {totalJourneyTime && <div className="plan-card-small" style={{ fontWeight: 600, marginBottom: 4 }}>เวลาเดินทางทั้งหมด: {totalJourneyTime}</div>}
                {(getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)) && (
                  <div className="plan-card-small" style={{ fontWeight: 600 }}>ชั้นโดยสาร: {getCabinDisplay(flight?.cabin) || getCabinDisplay(flight_details?.cabin)}</div>
                )}
              </div>
              <div className="plan-card-small" style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
                {flight_details?.price_per_person != null && (
                  <div><span style={{ fontWeight: 600 }}>ราคาต่อคน:</span> {Number(flight_details.price_per_person).toLocaleString('th-TH')} {flight?.currency || displayCurrency}</div>
                )}
                {(flight?.cabin || flight_details?.cabin) && (
                  <div><span style={{ fontWeight: 600 }}>ชั้นโดยสาร:</span> {flight?.cabin || flight_details?.cabin}</div>
                )}

                {/* Baggage Allowance */}
                <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>🧳 Baggage Allowance</div>
                  <div><span style={{ fontWeight: 600 }}>กระเป๋าโหลด (Checked):</span> {flight?.baggage || flight_details?.checked_baggage || 'ไม่รวม'}</div>
                  <div><span style={{ fontWeight: 600 }}>กระเป๋าถือขึ้นเครื่อง (Carry-on):</span> {flight_details?.hand_baggage ?? '1 กระเป๋าถือ (7 kg)'}</div>
                </div>

                {/* Fare Rules */}
                <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>📋 Fare Rules</div>
                  {flight_details?.refundable != null && (
                    <div style={{ marginBottom: 4, padding: '4px 8px', borderRadius: 6, display: 'inline-block', width: 'fit-content', backgroundColor: flight_details.refundable ? 'rgba(74,222,128,0.2)' : 'rgba(248,113,113,0.2)', color: flight_details.refundable ? '#4ade80' : '#f87171' }}>
                      Refundable: {flight_details.refundable ? '✅ คืนเงินได้' : '❌ คืนเงินไม่ได้'}
                    </div>
                  )}
                  {(flight_details?.changeable != null || flight_details?.change_fee) && (
                    <div style={{ marginTop: 4 }}>
                      <span style={{ padding: '4px 8px', borderRadius: 6, display: 'inline-block', backgroundColor: flight_details?.changeable ? 'rgba(96,165,250,0.2)' : 'rgba(248,113,113,0.2)', color: flight_details?.changeable ? '#60a5fa' : '#f87171' }}>
                        Changeable: {flight_details?.changeable ? '✅ เลื่อนวันได้' : '❌ เลื่อนวันไม่ได้'}
                      </span>
                      {flight_details?.changeable && flight_details?.change_fee && (
                        <span style={{ marginLeft: 8, opacity: 0.9 }}>• ค่าธรรมเนียม: {flight_details.change_fee}</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Amenities (Value-Add Data) */}
                <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                  <div style={{ fontWeight: 600, marginBottom: 6 }}>✨ สิ่งอำนวยความสะดวก (Amenities)</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 16px' }}>
                    <span>📶 WiFi: {flight_details?.wifi ?? 'ตรวจสอบบนเครื่อง'}</span>
                    <span>🔌 ปลั๊กไฟ: {flight_details?.power_outlet ?? 'ตรวจสอบบนเครื่อง'}</span>
                    <span>🍽️ อาหาร: {flight_details?.meals ?? 'อาหารว่าง/ซื้อเพิ่ม'}</span>
                    {(flight_details?.seat_width || flight_details?.seat_selection) && (
                      <span>💺 ความกว้างที่นั่ง: {flight_details?.seat_width || flight_details?.seat_selection}</span>
                    )}
                  </div>
                </div>

                {/* CO2 Emissions */}
                {(() => {
                  const totalHours = flight?.segments?.reduce((s, seg) => s + parseDurationToHours(seg.duration), 0) || 0;
                  const estDistKm = totalHours > 0 ? totalHours * 800 : (firstSeg?.from && lastSeg?.to ? 1500 : 0);
                  const co2Kg = flight_details?.co2_emissions_kg ?? (estDistKm > 0 ? calculateCO2e(estDistKm) : null);
                  return co2Kg != null && co2Kg > 0 ? (
                    <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>🌱 CO2 Emissions</div>
                      <div>~{co2Kg} kg CO2e (ประมาณการ)</div>
                    </div>
                  ) : null;
                })()}

                {/* On-time Performance */}
                {flight_details?.on_time_performance != null && flight_details.on_time_performance !== '' && (
                  <div style={{ paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
                    <div style={{ fontWeight: 600, marginBottom: 4 }}>⏱️ On-time Performance</div>
                    <div>{flight_details.on_time_performance}</div>
                  </div>
                )}

                {flight_details?.seat_selection && !flight_details?.seat_width && (
                  <div><span style={{ fontWeight: 600 }}>💺 เลือกที่นั่ง:</span> {flight_details.seat_selection}</div>
                )}
                {flight?.visa_warning && (
                  <div style={{ marginTop: 6, padding: 8, background: 'rgba(255,193,7,0.15)', borderRadius: 6, border: '1px solid rgba(255,193,7,0.4)', color: '#facc15', whiteSpace: 'pre-line' }}>
                    <span style={{ fontWeight: 600 }}>🛂 หมายเหตุ:</span><br />{flight.visa_warning}
                  </div>
                )}
                {flight_details?.promotions && Array.isArray(flight_details.promotions) && flight_details.promotions.length > 0 && (
                  <div style={{ marginTop: 4 }}>
                    <span style={{ fontWeight: 600 }}>🎁 โปรโมชัน:</span>
                    <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                      {flight_details.promotions.map((promo, idx) => (
                        <li key={idx}>{typeof promo === 'string' ? promo : (promo?.text || promo?.name || JSON.stringify(promo))}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="plan-card-footer">
        {displayTotalPrice && <div className="plan-card-price">{displayTotalPrice}</div>}
        <button className="plan-card-button" onClick={() => onSelect && onSelect(id)}>เลือกช้อยส์ {id}</button>
      </div>
    </div>
  );
}
