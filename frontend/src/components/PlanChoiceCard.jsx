import React from 'react';
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

      {/* Flight Section (Amadeus) */}
      {flight && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ เที่ยวบิน</div>

          <div className="plan-card-section-body">
            {/* Carrier / flight number */}
            {firstSeg ? (
              <div>
                สายการบิน: {firstSeg.carrier}
                {firstSeg.flight_number ? ` • ${firstSeg.flight_number}` : ''}
              </div>
            ) : (
              <div>มีข้อมูลเที่ยวบิน (แต่ไม่พบ segment)</div>
            )}

            {/* Route + time */}
            <div className="plan-card-small">
              {flightRoute ? `เส้นทาง: ${flightRoute}` : 'เส้นทาง: -'}
              {flightTime ? ` • เวลา: ${flightTime}` : ''}
            </div>

            {/* Stops / carriers / cabin / baggage */}
            <div className="plan-card-small">
              {flightStops ? `${flightStops}` : ''}
              {flightCarriers ? ` • ${flightCarriers}` : ''}
              {flight?.cabin ? ` • Cabin: ${flight.cabin}` : ''}
              {flight?.baggage ? ` • Bag: ${flight.baggage}` : ''}
            </div>

            {/* Flight price */}
            {flightPrice && (
              <div className="plan-card-small">
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
            <div>{hotelName || 'Unknown Hotel'}</div>
            <div className="plan-card-small">
              {hotelNights != null ? `${hotelNights} คืน` : ''}
              {hotelBoard ? ` • ${hotelBoard}` : ''}
            </div>
            {hotelPrice && (
              <div className="plan-card-small">
                ราคาโรงแรม: {hotelPrice}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Transport Section (optional legacy) */}
      {transport && (
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
