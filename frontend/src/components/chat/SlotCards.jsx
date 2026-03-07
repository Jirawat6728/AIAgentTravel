import React from 'react';
import { AIRLINE_NAMES } from '../../data/airlineNames';
import '../bookings/TripSummaryUI.css';

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
  return AIRLINE_NAMES[code.toUpperCase()] || code;
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
            {(firstSegment.departure || firstSegment.depart_at) && kv('วัน-เวลาออก', formatThaiDateTime(firstSegment.departure || firstSegment.depart_at))}
            {(lastSegment.arrival || lastSegment.arrive_at) && kv('วัน-เวลาถึง', formatThaiDateTime(lastSegment.arrival || lastSegment.arrive_at))}
            {firstSegment.carrier && kv('สายการบิน', getAirlineName(firstSegment.carrier))}
            {flight.total_duration && kv('ระยะเวลาบิน', flight.total_duration)}
            {flight.is_non_stop !== undefined && kv('บินตรง', flight.is_non_stop ? 'ใช่' : `แวะ ${flight.num_stops || 0} ครั้ง`)}
            {(flight.total_price != null || flight.price_total != null) && kv('ราคา', money(currency, flight.total_price ?? flight.price_total))}
          </>
        )}
        {segments.length > 1 && (
          <div className="slot-card-segments">
            <div className="slot-card-segments-title">เที่ยวบินทั้งหมด ({segments.length} segments):</div>
            {segments.map((seg, idx) => (
              <div key={idx} className="slot-card-segment">
                <div className="segment-number">Segment {idx + 1}</div>
                {seg.from && seg.to && <div>{seg.from} → {seg.to}</div>}
                {(seg.departure || seg.depart_at) && <div>ออก: {formatThaiDateTime(seg.departure || seg.depart_at)}</div>}
                {(seg.arrival || seg.arrive_at) && <div>ถึง: {formatThaiDateTime(seg.arrival || seg.arrive_at)}</div>}
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
            {(hotel.total_price != null || hotel.price_total != null) && kv('ราคา', money(currency, hotel.total_price ?? hotel.price_total))}
          </>
        )}
        <div className="slot-card-edit-hint">
          💡 พิมพ์ในแชทเพื่อแก้ไข เช่น "ขอที่พักถูกลง" หรือ "เปลี่ยนโรงแรม"
        </div>
      </div>
    </div>
  );
}

// Transport Slot Card - Enhanced with full details and price
export function TransportSlotCard({ transport }) {
  if (!transport || (!transport.type && (!transport.segments || transport.segments.length === 0))) {
    return (
      <div className="slot-card">
        <div className="slot-card-header">
          <span className="slot-card-title">🚗 การเดินทาง</span>
          <span className="slot-card-status">ยังไม่ได้เลือก</span>
        </div>
        <div className="slot-card-body">
          <div className="slot-card-empty">พิมพ์ในแชทเพื่อเลือกการเดินทาง เช่น "ขอรถเช่า"</div>
        </div>
      </div>
    );
  }

  const transportSegments = transport.segments || [];
  const currency = transport.currency || transport.data?.currency || 'THB';
  
  // ✅ Extract price from multiple possible locations
  const getPrice = (item) => {
    return item?.price || item?.price_amount || item?.data?.price || item?.data?.price_amount || null;
  };
  
  // ✅ Format duration helper
  const formatDuration = (durationStr) => {
    if (!durationStr) return null;
    if (typeof durationStr === 'string' && durationStr.startsWith('PT')) {
      // Parse ISO 8601 duration (e.g., "PT1H30M")
      let hours = 0, minutes = 0;
      const hourMatch = durationStr.match(/(\d+)H/);
      const minuteMatch = durationStr.match(/(\d+)M/);
      if (hourMatch) hours = parseInt(hourMatch[1]);
      if (minuteMatch) minutes = parseInt(minuteMatch[1]);
      const parts = [];
      if (hours > 0) parts.push(`${hours} ชั่วโมง`);
      if (minutes > 0) parts.push(`${minutes} นาที`);
      return parts.length > 0 ? parts.join(' ') : durationStr;
    }
    return durationStr;
  };

  return (
    <div className="slot-card">
      <div className="slot-card-header">
        <span className="slot-card-title">
          {transport.type === 'car_rental' ? '🚗 รถเช่า' :
           transport.type === 'bus' ? '🚌 รถโดยสาร' :
           transport.type === 'train' ? '🚂 รถไฟ' :
           transport.type === 'metro' ? '🚇 รถไฟฟ้า' :
           transport.type === 'ferry' ? '⛴️ เรือ' :
           transport.type === 'transfer' ? '🚗 รถรับส่ง' :
           '🚗 การเดินทาง'}
        </span>
        <span className="slot-card-status selected">เลือกแล้ว</span>
      </div>
      <div className="slot-card-body">
        {transportSegments.length > 0 ? (
          <>
            {transportSegments.map((seg, idx) => {
              const segmentPrice = getPrice(seg);
              const segmentCurrency = seg.currency || seg.data?.currency || currency;
              
              return (
                <div key={idx} className="slot-card-segment" style={{ 
                  marginBottom: '16px', 
                  padding: '12px', 
                  background: 'rgba(255, 255, 255, 0.05)', 
                  borderRadius: '8px',
                  border: '1px solid rgba(255, 255, 255, 0.1)'
                }}>
                  <div className="segment-number" style={{ fontWeight: '600', marginBottom: '8px', fontSize: '14px' }}>
                    Segment {idx + 1}
                  </div>
                  
                  {/* ✅ Type */}
                  {seg.type && kv('ประเภท', seg.type === 'car_rental' ? 'รถเช่า' :
                                         seg.type === 'bus' ? 'รถโดยสาร' :
                                         seg.type === 'train' ? 'รถไฟ' :
                                         seg.type === 'metro' ? 'รถไฟฟ้า' :
                                         seg.type === 'ferry' ? 'เรือ' :
                                         seg.type === 'transfer' ? 'รถรับส่ง' :
                                         seg.type)}
                  
                  {/* ✅ Route */}
                  {seg.route && kv('เส้นทาง', seg.route)}
                  {(seg.from || seg.origin) && (seg.to || seg.destination) && !seg.route && 
                    kv('เส้นทาง', `${seg.from || seg.origin} → ${seg.to || seg.destination}`)}
                  
                  {/* ✅ Duration */}
                  {(seg.duration || seg.data?.duration) && 
                    kv('ระยะเวลา', formatDuration(seg.duration || seg.data?.duration))}
                  
                  {/* ✅ Distance */}
                  {(seg.distance || seg.data?.distance) && 
                    kv('ระยะทาง', typeof (seg.distance || seg.data?.distance) === 'number' 
                      ? `${(seg.distance || seg.data?.distance).toLocaleString('th-TH')} กม.`
                      : (seg.distance || seg.data?.distance))}
                  
                  {/* ✅ Provider/Company */}
                  {(seg.provider || seg.data?.provider || seg.company || seg.data?.company) && 
                    kv('บริษัท', seg.provider || seg.data?.provider || seg.company || seg.data?.company)}
                  
                  {/* ✅ Vehicle Type (for car rental) */}
                  {(seg.vehicle_type || seg.data?.vehicle_type || seg.car_type || seg.data?.car_type) && 
                    kv('ประเภทรถ', seg.vehicle_type || seg.data?.vehicle_type || seg.car_type || seg.data?.car_type)}
                  
                  {/* ✅ Seats/Capacity */}
                  {(seg.seats || seg.data?.seats || seg.capacity || seg.data?.capacity) && 
                    kv('จำนวนที่นั่ง', `${seg.seats || seg.data?.seats || seg.capacity || seg.data?.capacity} ที่นั่ง`)}
                  
                  {/* ✅ Price - CRITICAL: Always show prominently */}
                  {segmentPrice && (
                    <div style={{ 
                      marginTop: '8px', 
                      padding: '10px', 
                      background: 'rgba(74, 222, 128, 0.15)', 
                      borderRadius: '6px',
                      border: '1px solid rgba(74, 222, 128, 0.3)'
                    }}>
                      <div style={{ fontWeight: '700', fontSize: '16px', color: '#4ade80' }}>
                        💰 ราคา: {money(segmentCurrency, segmentPrice)}
                      </div>
                      {(seg.price_per_day || seg.data?.price_per_day) && (
                        <div style={{ fontSize: '13px', opacity: 0.9, marginTop: '4px' }}>
                          ราคาต่อวัน: {money(segmentCurrency, seg.price_per_day || seg.data?.price_per_day)}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* ✅ Features/Amenities */}
                  {(seg.features || seg.data?.features || seg.amenities || seg.data?.amenities) && (
                    <div style={{ marginTop: '8px', fontSize: '13px' }}>
                      <div style={{ fontWeight: '600', marginBottom: '4px' }}>คุณสมบัติ:</div>
                      {Array.isArray(seg.features || seg.data?.features || seg.amenities || seg.data?.amenities) ? (
                        (seg.features || seg.data?.features || seg.amenities || seg.data?.amenities).map((feature, fIdx) => (
                          <div key={fIdx} style={{ marginLeft: '8px' }}>✓ {feature}</div>
                        ))
                      ) : (
                        <div style={{ marginLeft: '8px' }}>{seg.features || seg.data?.features || seg.amenities || seg.data?.amenities}</div>
                      )}
                    </div>
                  )}
                  
                  {/* ✅ Note/Additional Info */}
                  {(seg.note || seg.data?.note || seg.description || seg.data?.description) && (
                    <div style={{ 
                      marginTop: '8px', 
                      padding: '8px', 
                      background: 'rgba(255, 193, 7, 0.1)', 
                      borderRadius: '6px', 
                      fontSize: '13px' 
                    }}>
                      <span style={{ fontWeight: '600' }}>📝 หมายเหตุ: </span>
                      {seg.note || seg.data?.note || seg.description || seg.data?.description}
                    </div>
                  )}
                </div>
              );
            })}
            
            {/* ✅ Total Price for all segments */}
            {transportSegments.length > 1 && (() => {
              const totalPrice = transportSegments.reduce((sum, seg) => {
                const price = getPrice(seg);
                return sum + (price || 0);
              }, 0);
              if (totalPrice > 0) {
                return (
                  <div style={{ 
                    marginTop: '12px', 
                    padding: '12px', 
                    background: 'rgba(74, 222, 128, 0.2)', 
                    borderRadius: '8px',
                    border: '1px solid rgba(74, 222, 128, 0.4)',
                    textAlign: 'center'
                  }}>
                    <div style={{ fontWeight: '700', fontSize: '18px', color: '#4ade80' }}>
                      💰 ราคารวม: {money(currency, totalPrice)}
                    </div>
                  </div>
                );
              }
              return null;
            })()}
          </>
        ) : (
          <>
            {/* ✅ Type */}
            {transport.type && kv('ประเภท', transport.type === 'car_rental' ? 'รถเช่า' :
                                         transport.type === 'bus' ? 'รถโดยสาร' :
                                         transport.type === 'train' ? 'รถไฟ' :
                                         transport.type === 'metro' ? 'รถไฟฟ้า' :
                                         transport.type === 'ferry' ? 'เรือ' :
                                         transport.type === 'transfer' ? 'รถรับส่ง' :
                                         transport.type)}
            
            {/* ✅ Route */}
            {transport.route && kv('เส้นทาง', transport.route)}
            {(transport.from || transport.origin || transport.data?.from || transport.data?.origin) && 
             (transport.to || transport.destination || transport.data?.to || transport.data?.destination) && 
             !transport.route && 
              kv('เส้นทาง', `${transport.from || transport.origin || transport.data?.from || transport.data?.origin} → ${transport.to || transport.destination || transport.data?.to || transport.data?.destination}`)}
            
            {/* ✅ Duration */}
            {(transport.duration || transport.data?.duration) && 
              kv('ระยะเวลา', formatDuration(transport.duration || transport.data?.duration))}
            
            {/* ✅ Distance */}
            {(transport.distance || transport.data?.distance) && 
              kv('ระยะทาง', typeof (transport.distance || transport.data?.distance) === 'number' 
                ? `${(transport.distance || transport.data?.distance).toLocaleString('th-TH')} กม.`
                : (transport.distance || transport.data?.distance))}
            
            {/* ✅ Provider/Company */}
            {(transport.provider || transport.data?.provider || transport.company || transport.data?.company) && 
              kv('บริษัท', transport.provider || transport.data?.provider || transport.company || transport.data?.company)}
            
            {/* ✅ Vehicle Type (for car rental) */}
            {(transport.vehicle_type || transport.data?.vehicle_type || transport.car_type || transport.data?.car_type) && 
              kv('ประเภทรถ', transport.vehicle_type || transport.data?.vehicle_type || transport.car_type || transport.data?.car_type)}
            
            {/* ✅ Seats/Capacity */}
            {(transport.seats || transport.data?.seats || transport.capacity || transport.data?.capacity) && 
              kv('จำนวนที่นั่ง', `${transport.seats || transport.data?.seats || transport.capacity || transport.data?.capacity} ที่นั่ง`)}
            
            {/* ✅ Price - CRITICAL: Always show prominently */}
            {(() => {
              const transportPrice = getPrice(transport);
              if (transportPrice) {
                return (
                  <div style={{ 
                    marginTop: '12px', 
                    padding: '12px', 
                    background: 'rgba(74, 222, 128, 0.15)', 
                    borderRadius: '8px',
                    border: '1px solid rgba(74, 222, 128, 0.3)'
                  }}>
                    <div style={{ fontWeight: '700', fontSize: '18px', color: '#4ade80', marginBottom: '4px' }}>
                      💰 ราคา: {money(currency, transportPrice)}
                    </div>
                    {(transport.price_per_day || transport.data?.price_per_day) && (
                      <div style={{ fontSize: '14px', opacity: 0.9, marginTop: '4px' }}>
                        ราคาต่อวัน: {money(currency, transport.price_per_day || transport.data?.price_per_day)}
                      </div>
                    )}
                  </div>
                );
              }
              return null;
            })()}
            
            {/* ✅ Features/Amenities */}
            {(transport.features || transport.data?.features || transport.amenities || transport.data?.amenities) && (
              <div style={{ marginTop: '12px', padding: '10px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px' }}>
                <div style={{ fontWeight: '600', marginBottom: '6px', fontSize: '14px' }}>คุณสมบัติ:</div>
                {Array.isArray(transport.features || transport.data?.features || transport.amenities || transport.data?.amenities) ? (
                  (transport.features || transport.data?.features || transport.amenities || transport.data?.amenities).map((feature, idx) => (
                    <div key={idx} style={{ marginLeft: '8px', marginBottom: '4px' }}>✓ {feature}</div>
                  ))
                ) : (
                  <div style={{ marginLeft: '8px' }}>{transport.features || transport.data?.features || transport.amenities || transport.data?.amenities}</div>
                )}
              </div>
            )}
            
            {/* ✅ Note/Additional Info */}
            {(transport.note || transport.data?.note || transport.description || transport.data?.description) && (
              <div style={{ 
                marginTop: '12px', 
                padding: '10px', 
                background: 'rgba(255, 193, 7, 0.15)', 
                borderRadius: '6px', 
                fontSize: '14px' 
              }}>
                <span style={{ fontWeight: '600' }}>📝 หมายเหตุ: </span>
                {transport.note || transport.data?.note || transport.description || transport.data?.description}
              </div>
            )}
          </>
        )}
        <div className="slot-card-edit-hint" style={{ marginTop: '12px' }}>
          💡 พิมพ์ในแชทเพื่อแก้ไข เช่น "ขอรถเช่า" หรือ "เปลี่ยนเป็นรถไฟ"
        </div>
      </div>
    </div>
  );
}
