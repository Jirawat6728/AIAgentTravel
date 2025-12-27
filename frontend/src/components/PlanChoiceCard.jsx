import React, { useState } from 'react';
import './AITravelChat.css'; // ใช้คลาสจากไฟล์หลักร่วมกันได้

function formatMoney(value, currency = 'THB') {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return `${currency} ${value.toLocaleString('th-TH')}`;
}

function getFirstSegment(flight) {
  return flight?.segments?.length ? flight.segments[0] : null;
}

function getLastSegment(flight) {
  return flight?.segments?.length ? flight.segments[flight.segments.length - 1] : null;
}

function stopsLabel(flight) {
  const n = flight?.segments?.length || 0;
  if (!n) return null;
  const stops = Math.max(0, n - 1);
  return stops === 0 ? 'Non-stop' : `${stops} stop`;
}

function carriersLabel(flight) {
  const segs = flight?.segments || [];
  if (!segs.length) return null;
  const carriers = [];
  for (const s of segs) {
    const c = s?.carrier;
    if (c && !carriers.includes(c)) carriers.push(c);
  }
  return carriers.length ? carriers.join(', ') : null;
}

export default function PlanChoiceCard({ choice, onSelect }) {
  const [showItinerary, setShowItinerary] = useState(false);
  
  const {
    id,
    label,
    description,
    tags,
    recommended,
    flight,
    hotel,
    transport,
    currency,
    total_price,
    total_price_text,
    price_breakdown,
    title, // เผื่อ backend ส่ง title มา (เช่น "🟢 ช้อยส์ 1 (แนะนำ) ...")
    ground_transport, // ✅ ข้อมูลการเดินทาง/ขนส่ง
    itinerary, // ✅ ข้อมูล itinerary
    is_fastest, // ✅ เร็วสุดสะดวกสุด
    is_day_trip, // ✅ 1 วันไปกลับ
  } = choice || {};

  const displayCurrency =
    (price_breakdown && price_breakdown.currency) ||
    currency ||
    flight?.currency ||
    hotel?.currency ||
    'THB';

  const displayTotalPrice =
    typeof total_price === 'number'
      ? `${displayCurrency} ${total_price.toLocaleString('th-TH')}`
      : (total_price_text || null);

  // ===== Flight computed fields (from Amadeus structure) =====
  const firstSeg = getFirstSegment(flight);
  const lastSeg = getLastSegment(flight);

  const flightRoute =
    firstSeg && lastSeg
      ? `${firstSeg.from} → ${lastSeg.to}`
      : null;

  const flightTime =
    firstSeg && lastSeg
      ? `${firstSeg.depart_time || ''} → ${lastSeg.arrive_time || ''}${lastSeg.arrive_plus ? ` ${lastSeg.arrive_plus}` : ''}`.trim()
      : null;

  const flightStops = stopsLabel(flight);
  const flightCarriers = carriersLabel(flight);
  const flightPrice = formatMoney(
    typeof flight?.price_total === 'number' ? flight.price_total : null,
    flight?.currency || displayCurrency
  );

  // ===== Hotel computed fields (from Amadeus structure) =====
  const hotelName = hotel?.hotelName || null;
  const hotelNights = hotel?.nights != null ? hotel.nights : null;
  const hotelBoard = hotel?.boardType || null;
  const hotelPrice = formatMoney(
    typeof hotel?.price_total === 'number' ? hotel.price_total : null,
    hotel?.currency || displayCurrency
  );

  // ===== Transport (your legacy structure) =====
  const transportMode = transport?.mode || null;
  const transportNote = transport?.note || null;

  // ===== Price breakdown =====
  const breakdownFlight =
    typeof price_breakdown?.flight_total === 'number'
      ? formatMoney(price_breakdown.flight_total, displayCurrency)
      : null;

  const breakdownHotel =
    typeof price_breakdown?.hotel_total === 'number'
      ? formatMoney(price_breakdown.hotel_total, displayCurrency)
      : null;

  const breakdownTransport =
    typeof price_breakdown?.transport_total === 'number'
      ? formatMoney(price_breakdown.transport_total, displayCurrency)
      : null;

  return (
    <div className={`plan-card ${recommended ? 'plan-card-recommended' : ''}`}>
      {/* Header */}
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">
            {/* ถ้ามี title จาก backend ให้ใช้ title เลย */}
            {title
              ? title
              : `ช้อยส์ ${id}${label ? ` — ${label}` : ''}`
            }
          </span>
          {recommended && <span className="plan-card-tag">แนะนำ</span>}
          {/* ✅ แสดง tag "บินตรง" ถ้าเป็น non-stop */}
          {choice?.is_non_stop && flightStops === 'Non-stop' && (
            <span className="plan-card-tag" style={{ 
              background: '#e3f2fd', 
              color: '#1976d2',
              marginLeft: '6px'
            }}>
              ✈️ บินตรง
            </span>
          )}
        </div>

        {tags && Array.isArray(tags) && tags.length > 0 && (
          <div className="plan-card-tags">
            {tags.map((tag, idx) => (
              <span key={idx} className="plan-tag-pill">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Description */}
      {description && (
        <p className="plan-card-desc">{description}</p>
      )}

      {/* Flight Section (Amadeus) - แสดงทุก segments */}
      {flight && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>

          <div className="plan-card-section-body">
            {/* แสดงทุก segments */}
            {flight.segments && flight.segments.length > 0 ? (
              flight.segments.map((seg, idx) => (
                <div key={idx} style={{ marginBottom: idx < flight.segments.length - 1 ? '12px' : '0' }}>
                  <div style={{ fontWeight: '500', marginBottom: '4px' }}>
                    Segment {idx + 1}
                  </div>
                  <div>
                    สายการบิน: {seg.carrier || 'Unknown'}
                    {seg.flight_number ? ` • ${seg.flight_number}` : ''}
                  </div>
                  <div className="plan-card-small">
                    เส้นทาง: {seg.from || '-'} → {seg.to || '-'}
                  </div>
                  <div className="plan-card-small">
                    ออก: {seg.depart_time || '-'} → ถึง: {seg.arrive_time || '-'}{seg.arrive_plus ? ` ${seg.arrive_plus}` : ''}
                  </div>
                  {seg.aircraft_code && (
                    <div className="plan-card-small">
                      เครื่อง: {seg.aircraft_code}
                    </div>
                  )}
                  {seg.duration && (
                    <div className="plan-card-small">
                      ระยะเวลา: {seg.duration}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div>มีข้อมูลเที่ยวบิน (แต่ไม่พบ segment)</div>
            )}

            {/* Cabin / baggage / stops */}
            <div className="plan-card-small" style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid rgba(0,0,0,0.1)' }}>
              {flightStops && <span>{flightStops}</span>}
              {flightCarriers && <span> • {flightCarriers}</span>}
              {flight?.cabin && <span> • Cabin: {flight.cabin}</span>}
              {flight?.baggage && <span> • Bag: {flight.baggage}</span>}
            </div>

            {/* Flight price */}
            {flightPrice && (
              <div className="plan-card-small" style={{ marginTop: '4px', fontWeight: '500' }}>
                ราคาไฟลต์: {flightPrice}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Hotel Section (Amadeus) */}
      {hotel && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🏨 ที่พัก</div>
          <div className="plan-card-section-body">
            <div style={{ fontWeight: '500' }}>{hotelName || 'Unknown Hotel'}</div>
            <div className="plan-card-small">
              {hotelNights != null ? `${hotelNights} คืน` : ''}
              {hotelBoard ? ` • ${hotelBoard}` : ''}
            </div>
            {hotel?.address && (
              <div className="plan-card-small">
                ที่อยู่: {hotel.address}
              </div>
            )}
            {hotel?.cityCode && (
              <div className="plan-card-small">
                เมือง: {hotel.cityCode}
              </div>
            )}
            {hotelPrice && (
              <div className="plan-card-small" style={{ marginTop: '4px', fontWeight: '500' }}>
                ราคาโรงแรม: {hotelPrice}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ground Transport Section */}
      {ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚆/🚗 เดินทาง/ขนส่ง</div>
          <div className="plan-card-section-body plan-card-small">
            {ground_transport.split('\n').map((line, idx) => (
              <div key={idx}>{line}</div>
            ))}
          </div>
        </div>
      )}

      {/* Itinerary Section - ซ่อนไว้และมีปุ่มแสดง/ซ่อน */}
      {itinerary && (
        <div className="plan-card-section">
          <div className="plan-card-section-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>📅 Day-by-Day Itinerary</span>
            <button
              onClick={() => setShowItinerary(!showItinerary)}
              style={{
                background: 'transparent',
                border: '1px solid rgba(0,0,0,0.2)',
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                color: '#666',
                transition: 'all 0.2s',
              }}
              onMouseOver={(e) => {
                e.target.style.background = 'rgba(0,0,0,0.05)';
                e.target.style.borderColor = 'rgba(0,0,0,0.3)';
              }}
              onMouseOut={(e) => {
                e.target.style.background = 'transparent';
                e.target.style.borderColor = 'rgba(0,0,0,0.2)';
              }}
            >
              {showItinerary ? '▼ ซ่อน' : '▶ ข้อมูลเพิ่มเติม'}
            </button>
          </div>
          {showItinerary && (
            <div className="plan-card-section-body plan-card-small" style={{ marginTop: '8px' }}>
              {typeof itinerary === 'string' ? (
                // If itinerary is a string (like day trip)
                <div style={{ whiteSpace: 'pre-line' }}>{itinerary}</div>
              ) : Array.isArray(itinerary) ? (
                // If itinerary is an array of days
                itinerary.map((day, idx) => (
                  <div key={idx} style={{ marginBottom: '8px' }}>
                    <div style={{ fontWeight: '500' }}>
                      🗓 Day {day.day || idx + 1} – {day.title || 'Day ' + (idx + 1)}
                    </div>
                    {day.items && Array.isArray(day.items) && (
                      <div style={{ marginLeft: '12px', marginTop: '4px' }}>
                        {day.items.map((item, itemIdx) => (
                          <div key={itemIdx}>- {item}</div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              ) : null}
            </div>
          )}
        </div>
      )}

      {/* Transport Section (optional legacy) */}
      {transport && !ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 การเดินทาง</div>
          <div className="plan-card-section-body plan-card-small">
            {transportMode && <div>{transportMode}</div>}
            {transportNote && <div>{transportNote}</div>}
            {!transportMode && !transportNote && <div>มีข้อมูลการเดินทาง</div>}
          </div>
        </div>
      )}

      {/* Price Breakdown (ถ้ามี) */}
      {price_breakdown && (
        <div className="plan-card-section plan-card-price-breakdown">
          <div className="plan-card-section-title">💰 รายละเอียดราคา</div>
          <div className="plan-card-section-body plan-card-small">
            {breakdownFlight && <div>✈️ ตั๋วเครื่องบิน: {breakdownFlight}</div>}
            {breakdownHotel && <div>🏨 ที่พัก: {breakdownHotel}</div>}
            {breakdownTransport && <div>🚗 การเดินทาง: {breakdownTransport}</div>}
            {!breakdownFlight && !breakdownHotel && !breakdownTransport && (
              <div>ไม่มีรายการแยกราคาเพิ่มเติม</div>
            )}
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="plan-card-footer">
        {displayTotalPrice && (
          <div className="plan-card-price">
            {displayTotalPrice}
          </div>
        )}
        <button
          className="plan-card-button"
          onClick={() => onSelect && onSelect(id)}
        >
          เลือกช้อยส์ {id}
        </button>
      </div>
    </div>
  );
}
