/**
 * PlanChoiceCard เฉพาะที่พักทั้งหมด
 * แยกอิสระจาก PlanChoiceCard เพื่อแก้บั๊กและแสดงผลที่พักเท่านั้น
 */
import React from 'react';
import { formatMoney } from './planChoiceCardUtils';
import './PlanChoiceCard.css';

export default function PlanChoiceCardHotels({ choice, onSelect }) {
  const { id, label, tags, recommended, hotel, currency, total_price, total_price_text, price_breakdown, price, title } = choice || {};
  const displayCurrency = price_breakdown?.currency || currency || hotel?.currency || 'THB';
  // ✅ ราคารวม: choice.total_price / price หรือ hotel แบบ catalog (price_total, booking.pricing.total_amount)
  const resolvedTotal = typeof total_price === 'number' ? total_price
    : typeof price === 'number' ? price
    : (typeof hotel?.price_total === 'number' ? hotel.price_total : null)
    ?? (typeof hotel?.booking?.pricing?.total_amount === 'number' ? hotel.booking.pricing.total_amount : null);
  const displayTotalPrice = resolvedTotal != null
    ? `${displayCurrency} ${Number(resolvedTotal).toLocaleString('th-TH')}`
    : (total_price_text || null);

  const hotelName = hotel?.hotelName || hotel?.name || 'Unknown Hotel';
  const hotelNights = hotel?.nights != null ? hotel.nights : null;
  const hotelBoard = hotel?.boardType || null;
  const hotelPrice = formatMoney(typeof hotel?.price_total === 'number' ? hotel.price_total : null, hotel?.currency || displayCurrency);

  if (!hotel) {
    return (
      <div className="plan-card">
        <div className="plan-card-header"><span className="plan-card-label">ที่พัก {title || id}</span></div>
        <p className="plan-card-desc">ไม่มีข้อมูลที่พัก</p>
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
          <span className="plan-card-label">{title || `ที่พัก ${id}${label ? ` — ${label}` : ''}`}</span>
          {recommended && (!tags || !tags.includes('แนะนำ')) && <span className="plan-card-tag">แนะนำ</span>}
        </div>
        {tags && Array.isArray(tags) && tags.length > 0 && (
          <div className="plan-card-tags">
            {[...new Set(tags)].map((tag, idx) => (
              <span key={idx} className="plan-tag-pill">{tag}</span>
            ))}
          </div>
        )}
      </div>

      <div className="plan-card-section">
        <div className="plan-card-section-title">🏨 ที่พัก: {hotelName}</div>

        {hotel.visuals?.image_urls && hotel.visuals.image_urls.length > 0 && (
          <div style={{ width: '100%', overflowX: 'auto', whiteSpace: 'nowrap', marginBottom: 12, borderRadius: 8 }}>
            {hotel.visuals.image_urls.map((url, idx) => (
              <img key={idx} src={url} alt={`hotel-${idx}`} style={{ width: 120, height: 80, objectFit: 'cover', borderRadius: 6, marginRight: 8, display: 'inline-block' }} />
            ))}
          </div>
        )}

        <div className="plan-card-section-body">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            {hotel.star_rating && (
              <span style={{ color: '#FFD700', fontSize: 14 }}>{'⭐'.repeat(Math.round(hotel.star_rating))} ({hotel.star_rating})</span>
            )}
            {hotel.visuals?.review_score && (
              <span style={{ fontSize: 12, background: '#4CAF50', color: 'white', padding: '2px 6px', borderRadius: 4 }}>
                {hotel.visuals.review_score} / 5 ({hotel.visuals.review_count || 0} รีวิว)
              </span>
            )}
          </div>

          {(hotel.location?.address || hotel?.address) && (
            <div className="plan-card-small" style={{ marginBottom: 8, opacity: 0.9 }}>📍 {hotel.location?.address || hotel.address}</div>
          )}

          {hotel.amenities && (
            <div style={{ display: 'flex', gap: 12, marginBottom: 12, padding: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 18 }}>
              {hotel.amenities.has_wifi && <span title="Free Wi-Fi">📶</span>}
              {hotel.amenities.has_pool && <span title="Swimming Pool">🏊</span>}
              {hotel.amenities.has_fitness && <span title="Fitness Center">🏋️</span>}
              {hotel.amenities.has_parking && <span title="Parking">🅿️</span>}
              {hotel.amenities.has_spa && <span title="Spa">💆</span>}
              {hotel.amenities.has_air_conditioning && <span title="Air Con">❄️</span>}
            </div>
          )}

          <div style={{ marginBottom: 12, paddingLeft: 8, borderLeft: '3px solid rgba(255,255,255,0.3)' }}>
            {hotel.booking?.room?.room_type && <div style={{ fontWeight: 600, fontSize: 15 }}>🛏️ {hotel.booking.room.room_type}</div>}
            {hotel.booking?.room?.bed_type && <div className="plan-card-small">{hotel.booking.room.bed_quantity} x {hotel.booking.room.bed_type}</div>}
            {hotel.booking?.policies?.meal_plan && <div className="plan-card-small">🍽️ {hotel.booking.policies.meal_plan}</div>}
            {hotel.booking?.policies && (
              <span style={{ display: 'inline-block', marginTop: 6, padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600, backgroundColor: hotel.booking.policies.is_refundable ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)', color: hotel.booking.policies.is_refundable ? '#4ade80' : '#f87171' }}>
                {hotel.booking.policies.is_refundable ? '✅ ยกเลิกฟรี' : '❌ ห้ามยกเลิก'}
              </span>
            )}
          </div>

          {hotel.booking?.pricing && (
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, opacity: 0.8 }}>ราคาต่อคืน</span>
                <span style={{ fontWeight: 600 }}>{formatMoney(hotel.booking.pricing.price_per_night, hotel.booking.pricing.currency)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 13, opacity: 0.8 }}>ภาษีและค่าธรรมเนียม</span>
                <span style={{ fontSize: 13 }}>{formatMoney(hotel.booking.pricing.taxes_and_fees, hotel.booking.pricing.currency)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4, fontSize: 16 }}>
                <span style={{ fontWeight: 600 }}>ราคารวม</span>
                <span style={{ fontWeight: 700, color: '#81c784' }}>{formatMoney(hotel.booking.pricing.total_amount, hotel.booking.pricing.currency)}</span>
              </div>
            </div>
          )}

          {!hotel.booking && (
            <>
              <div style={{ fontWeight: 500 }}>{hotelName}</div>
              <div className="plan-card-small">
                {hotelNights != null ? `จำนวนคืน: ${hotelNights}` : ''}
                {hotelBoard ? ` • แพ็กเกจ: ${hotelBoard}` : ''}
              </div>
              {(hotel?.location?.address || hotel?.address) && <div className="plan-card-small">ที่อยู่: {hotel.location?.address || hotel.address}</div>}
              {hotelPrice && <div className="plan-card-small" style={{ marginTop: 4, fontWeight: 500 }}>ราคา: {hotelPrice}</div>}
            </>
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
