import React from 'react';
import './AITravelChat.css';

// Helper functions
function money(currency, n) {
  if (n == null || Number.isNaN(Number(n))) return null;
  const c = currency || 'THB';
  try {
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

function formatThaiDateTime(isoDateTime) {
  if (!isoDateTime) return '';
  try {
    const date = new Date(isoDateTime);
    if (isNaN(date.getTime())) return isoDateTime;
    const day = date.getDate();
    const month = date.getMonth() + 1;
    const year = date.getFullYear() + 543;
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${day}/${month}/${year} ${hours}:${minutes}`;
  } catch (e) {
    return isoDateTime;
  }
}

function getAirlineName(code) {
  if (!code) return 'Unknown';
  const airlineNames = {
    'TG': 'Thai Airways', 'FD': 'Thai AirAsia', 'SL': 'Thai Lion Air', 'PG': 'Bangkok Airways',
    'VZ': 'Thai Vietjet Air', 'WE': 'Thai Smile', 'XJ': 'Thai AirAsia X', 'DD': 'Nok Air',
    'SQ': 'Singapore Airlines', 'MH': 'Malaysia Airlines', 'CX': 'Cathay Pacific',
    'JL': 'Japan Airlines', 'NH': 'All Nippon Airways', 'KE': 'Korean Air',
  };
  return airlineNames[code.toUpperCase()] || code;
}

// Flight Slot Card
export function FlightSlotCard({ flight, travelSlots }) {
  if (!flight) {
    return (
      <div className="slot-card">
        <div className="slot-card-header">
          <span className="slot-card-title">✈️ เที่ยวบิน</span>
          <span className="slot-card-status">ยังไม่ได้เลือก</span>
        </div>
        <div className="slot-card-body">
          <div className="slot-card-empty">พิมพ์ในแชทเพื่อเลือกเที่ยวบิน เช่น "ขอไฟลต์เช้ากว่านี้"</div>
        </div>
      </div>
    );
  }

  const segments = flight.segments || [];
  const currency = flight.currency || 'THB';
  const firstSegment = segments[0];
  const lastSegment = segments[segments.length - 1];

  return (
    <div className="slot-card">
      <div className="slot-card-header">
        <span className="slot-card-title">✈️ เที่ยวบิน</span>
        <span className="slot-card-status selected">เลือกแล้ว</span>
      </div>
      <div className="slot-card-body">
        {firstSegment && lastSegment && (
          <>
            {kv('เส้นทาง', `${firstSegment.from || ''} → ${lastSegment.to || ''}`)}
            {firstSegment.departure && kv('วัน-เวลาออก', formatThaiDateTime(firstSegment.departure))}
            {lastSegment.arrival && kv('วัน-เวลาถึง', formatThaiDateTime(lastSegment.arrival))}
            {firstSegment.carrier && kv('สายการบิน', getAirlineName(firstSegment.carrier))}
            {flight.total_duration && kv('ระยะเวลาบิน', flight.total_duration)}
            {flight.is_non_stop !== undefined && kv('บินตรง', flight.is_non_stop ? 'ใช่' : `แวะ ${flight.num_stops || 0} ครั้ง`)}
            {flight.total_price && kv('ราคา', money(currency, flight.total_price))}
          </>
        )}
        {segments.length > 1 && (
          <div className="slot-card-segments">
            <div className="slot-card-segments-title">เที่ยวบินทั้งหมด ({segments.length} segments):</div>
            {segments.map((seg, idx) => (
              <div key={idx} className="slot-card-segment">
                <div className="segment-number">Segment {idx + 1}</div>
                {seg.from && seg.to && <div>{seg.from} → {seg.to}</div>}
                {seg.departure && <div>ออก: {formatThaiDateTime(seg.departure)}</div>}
                {seg.arrival && <div>ถึง: {formatThaiDateTime(seg.arrival)}</div>}
                {seg.carrier && <div>สายการบิน: {getAirlineName(seg.carrier)}</div>}
              </div>
            ))}
          </div>
        )}
        <div className="slot-card-edit-hint">
          💡 พิมพ์ในแชทเพื่อแก้ไข เช่น "ขอไฟลต์เช้ากว่านี้" หรือ "เปลี่ยนสายการบิน"
        </div>
      </div>
    </div>
  );
}

// Hotel Slot Card
export function HotelSlotCard({ hotel, travelSlots }) {
  if (!hotel) {
    return (
      <div className="slot-card">
        <div className="slot-card-header">
          <span className="slot-card-title">🏨 ที่พัก</span>
          <span className="slot-card-status">ยังไม่ได้เลือก</span>
        </div>
        <div className="slot-card-body">
          <div className="slot-card-empty">พิมพ์ในแชทเพื่อเลือกที่พัก เช่น "ขอที่พักถูกลง"</div>
        </div>
      </div>
    );
  }

  const hotelSegments = hotel.segments || [];
  const currency = hotel.currency || 'THB';

  return (
    <div className="slot-card">
      <div className="slot-card-header">
        <span className="slot-card-title">🏨 ที่พัก</span>
        <span className="slot-card-status selected">เลือกแล้ว</span>
      </div>
      <div className="slot-card-body">
        {hotelSegments.length > 0 ? (
          <>
            {hotelSegments.map((seg, idx) => (
              <div key={idx} className="slot-card-segment">
                <div className="segment-number">ที่พัก {idx + 1}</div>
                {seg.city && kv('เมือง', seg.city)}
                {seg.nights && kv('จำนวนคืน', `${seg.nights} คืน`)}
                {seg.hotelName && kv('ชื่อโรงแรม', seg.hotelName)}
                {seg.boardType && kv('ประเภทอาหาร', seg.boardType)}
                {seg.address && kv('ที่อยู่', seg.address)}
                {seg.price && kv('ราคา', money(seg.currency || currency, seg.price))}
              </div>
            ))}
          </>
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
        <div className="slot-card-edit-hint">
          💡 พิมพ์ในแชทเพื่อแก้ไข เช่น "ขอที่พักถูกลง" หรือ "เปลี่ยนโรงแรม"
        </div>
      </div>
    </div>
  );
}

// Transport Slot Card
export function TransportSlotCard({ transport }) {
  if (!transport || (!transport.type && (!transport.segments || transport.segments.length === 0))) {
    return (
      <div className="slot-card">
        <div className="slot-card-header">
          <span className="slot-card-title">🚗 การเดินทาง</span>
          <span className="slot-card-status">ยังไม่ได้เลือก</span>
        </div>
        <div className="slot-card-body">
          <div className="slot-card-empty">พิมพ์ในแชทเพื่อเลือกการเดินทาง เช่น "ขอรถเช่า" หรือ "ขอรถไฟ"</div>
        </div>
      </div>
    );
  }

  const transportSegments = transport.segments || [];
  const currency = transport.currency || 'THB';

  return (
    <div className="slot-card">
      <div className="slot-card-header">
        <span className="slot-card-title">🚗 การเดินทาง</span>
        <span className="slot-card-status selected">เลือกแล้ว</span>
      </div>
      <div className="slot-card-body">
        {transportSegments.length > 0 ? (
          <>
            {transportSegments.map((seg, idx) => (
              <div key={idx} className="slot-card-segment">
                <div className="segment-number">Segment {idx + 1}</div>
                {seg.type && kv('ประเภท', seg.type)}
                {seg.route && kv('เส้นทาง', seg.route)}
                {seg.duration && kv('ระยะเวลา', seg.duration)}
                {seg.price && kv('ราคา', money(seg.currency || currency, seg.price))}
              </div>
            ))}
          </>
        ) : (
          <>
            {transport.type && kv('ประเภท', transport.type)}
            {transport.route && kv('เส้นทาง', transport.route)}
            {transport.duration && kv('ระยะเวลา', transport.duration)}
            {transport.price && kv('ราคา', money(currency, transport.price))}
          </>
        )}
        <div className="slot-card-edit-hint">
          💡 พิมพ์ในแชทเพื่อแก้ไข เช่น "ขอรถเช่า" หรือ "เปลี่ยนเป็นรถไฟ"
        </div>
      </div>
    </div>
  );
}
