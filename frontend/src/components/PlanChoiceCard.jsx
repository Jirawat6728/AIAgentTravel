import React from 'react';
import './AITravelChat.css'; // ใช้คลาสจากไฟล์หลักร่วมกันได้

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
    price_breakdown
  } = choice;

  const displayCurrency = currency || 'THB';

  const displayTotalPrice =
    typeof total_price === 'number'
      ? `${displayCurrency} ${total_price.toLocaleString('th-TH')}`
      : (total_price_text || null);

  return (
    <div className={`plan-card ${recommended ? 'plan-card-recommended' : ''}`}>
      {/* Header */}
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">
            ช้อยส์ {id} — {label}
          </span>
          {recommended && <span className="plan-card-tag">แนะนำ</span>}
        </div>
        {tags && tags.length > 0 && (
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

      {/* Flight Section */}
      {flight && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">✈️ ไฟลต์</div>
          <div className="plan-card-section-body">
            <div>
              {flight.airline} {flight.flight_number}
            </div>
            <div className="plan-card-small">
              {flight.origin} → {flight.destination}
              {flight.departure_time && (
                <> • ออกเดินทาง {flight.departure_time}</>
              )}
              {flight.return_time && (
                <> • ขากลับ {flight.return_time}</>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Hotel Section */}
      {hotel && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🏨 ที่พัก</div>
          <div className="plan-card-section-body">
            <div>{hotel.name}</div>
            <div className="plan-card-small">
              {hotel.location}
              {hotel.nights && <> • {hotel.nights} คืน</>}
            </div>
          </div>
        </div>
      )}

      {/* Transport Section */}
      {transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 การเดินทาง</div>
          <div className="plan-card-section-body plan-card-small">
            <div>{transport.mode}</div>
            {transport.note && <div>{transport.note}</div>}
          </div>
        </div>
      )}

      {/* Price Breakdown (ถ้ามี) */}
      {price_breakdown && (
        <div className="plan-card-section plan-card-price-breakdown">
          <div className="plan-card-section-title">💰 รายละเอียดราคา</div>
          <div className="plan-card-section-body plan-card-small">
            {typeof price_breakdown.flight_total === 'number' && (
              <div>✈️ ตั๋วเครื่องบิน: {displayCurrency} {price_breakdown.flight_total.toLocaleString('th-TH')}</div>
            )}
            {typeof price_breakdown.hotel_total === 'number' && (
              <div>🏨 ที่พัก: {displayCurrency} {price_breakdown.hotel_total.toLocaleString('th-TH')}</div>
            )}
            {typeof price_breakdown.transport_total === 'number' && (
              <div>🚗 การเดินทาง: {displayCurrency} {price_breakdown.transport_total.toLocaleString('th-TH')}</div>
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
          onClick={() => onSelect(id)}
        >
          เลือกช้อยส์ {id}
        </button>
      </div>
    </div>
  );
}
