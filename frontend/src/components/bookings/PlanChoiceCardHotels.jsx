/**
 * PlanChoiceCard เฉพาะที่พักทั้งหมด
 * แสดงข้อมูลครบแบบ PlanChoiceCard: ภาพ, ดาว/รีวิว, รูปแบบห้อง, จำนวนคืน, ส่วนกลาง, เช็คอิน/เอาท์, ราคาแยก/รวม
 */
import React from 'react';
import { formatPriceInThb } from '../../utils/currency';
import './PlanChoiceCard.css';

function formatDate(isoStr) {
  if (!isoStr || typeof isoStr !== 'string') return null;
  try {
    const d = isoStr.split('T')[0].split('-');
    if (d.length >= 3) return `${d[2]}/${d[1]}/${d[0]}`;
    return isoStr;
  } catch (_) {
    return isoStr;
  }
}

function calcNights(checkIn, checkOut) {
  if (!checkIn || !checkOut) return null;
  try {
    const a = new Date(checkIn.split('T')[0]);
    const b = new Date(checkOut.split('T')[0]);
    const diff = (b - a) / (1000 * 60 * 60 * 24);
    return Number.isInteger(diff) && diff > 0 ? diff : null;
  } catch (_) {
    return null;
  }
}

export default function PlanChoiceCardHotels({ choice, onSelect }) {
  const { id, label, tags, recommended, hotel, currency, total_price, total_price_text, price_breakdown, price, title } = choice || {};
  const displayCurrency = price_breakdown?.currency || currency || hotel?.currency || 'THB';
  const resolvedTotal = typeof total_price === 'number' ? total_price
    : typeof price === 'number' ? price
    : (typeof hotel?.price_total === 'number' ? hotel.price_total : null)
    ?? (typeof hotel?.booking?.pricing?.total_amount === 'number' ? hotel.booking.pricing.total_amount : null);
  const displayTotalPrice = resolvedTotal != null
    ? formatPriceInThb(resolvedTotal, displayCurrency)
    : (total_price_text || null);

  const hotelName = hotel?.hotelName || hotel?.name || choice?.title || choice?.raw?.display_name || 'Unknown Hotel';
  const hotelNights = hotel?.nights ?? calcNights(hotel?.booking?.check_in_date, hotel?.booking?.check_out_date);
  const checkInStr = formatDate(hotel?.booking?.check_in_date);
  const checkOutStr = formatDate(hotel?.booking?.check_out_date);

  const pricing = hotel?.booking?.pricing;
  const pricePerNight = pricing?.price_per_night;
  const taxesAndFees = pricing?.taxes_and_fees;
  const totalAmount = pricing?.total_amount ?? hotel?.price_total ?? resolvedTotal;
  const pricingCurrency = pricing?.currency || hotel?.currency || displayCurrency;

  const amenityLabels = [];
  if (hotel?.amenities) {
    const a = hotel.amenities;
    if (a.has_wifi) amenityLabels.push('Wi-Fi');
    if (a.has_pool) amenityLabels.push('สระว่ายน้ำ');
    if (a.has_fitness) amenityLabels.push('ฟิตเนส');
    if (a.has_parking) amenityLabels.push('ที่จอดรถ');
    if (a.has_spa) amenityLabels.push('สปา');
    if (a.has_air_conditioning) amenityLabels.push('แอร์');
  }
  const mealPlan = hotel?.booking?.policies?.meal_plan || '';
  const mealPlanUpper = (mealPlan || '').toUpperCase();
  if (mealPlanUpper.includes('BREAKFAST') || mealPlanUpper.includes('BFST') || mealPlanUpper.includes('HALF') || mealPlanUpper.includes('FULL')) amenityLabels.push('อาหารเช้า');
  if (mealPlanUpper.includes('LUNCH') || (mealPlanUpper.includes('FULL') && mealPlanUpper.includes('BOARD'))) amenityLabels.push('อาหารกลางวัน');
  if (mealPlanUpper.includes('DINNER') || mealPlanUpper.includes('HALF') || mealPlanUpper.includes('FULL')) amenityLabels.push('อาหารเย็น');
  if (mealPlan && !['อาหารเช้า','อาหารกลางวัน','อาหารเย็น'].some(m => amenityLabels.includes(m)) && mealPlan !== 'Room Only') amenityLabels.push(mealPlan);
  const originalList = Array.isArray(hotel?.amenities?.original_list) ? hotel.amenities.original_list : [];
  const hasAnyAmenity = amenityLabels.length > 0 || originalList.length > 0;

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
            {[...new Set(tags)]
              .filter(tag => !['Amadeus', 'ราคาจริง', 'จองได้ทันที'].includes(tag))
              .map((tag, idx) => (
                <span key={idx} className="plan-tag-pill">{tag}</span>
              ))}
          </div>
        )}
      </div>

      <div className="plan-card-section">
        <div className="plan-card-section-title">🏨 รายละเอียดที่พัก</div>

        {/* 1. ภาพที่พัก - แสดงเสมอ */}
        <div style={{ marginBottom: 12 }}>
          <div className="plan-card-small" style={{ marginBottom: 6, opacity: 0.9 }}>ภาพที่พัก</div>
          {hotel.visuals?.image_urls && hotel.visuals.image_urls.length > 0 ? (
            <div style={{ width: '100%', overflowX: 'auto', whiteSpace: 'nowrap', borderRadius: 8, scrollbarWidth: 'none' }}>
              {hotel.visuals.image_urls.map((url, idx) => (
                <img key={idx} src={url} alt="" loading="lazy" onError={(e) => { e.target.style.display = 'none'; }} style={{ width: 140, height: 94, objectFit: 'cover', borderRadius: 8, marginRight: 8, display: 'inline-block' }} />
              ))}
            </div>
          ) : (
            <div style={{ minHeight: 80, background: 'rgba(255,255,255,0.08)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'rgba(255,255,255,0.5)', fontSize: 13 }}>ไม่มีภาพ</div>
          )}
        </div>

        {/* 2. ระดับดาวที่พัก & เรทรีวิวที่พัก - แสดงเสมอ */}
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="plan-card-small" style={{ opacity: 0.9 }}>ระดับดาวที่พัก:</span>
            {hotel.star_rating != null ? (
              <span style={{ color: '#FFD700', fontSize: 15 }}>{'⭐'.repeat(Math.round(hotel.star_rating))} ({hotel.star_rating} ดาว)</span>
            ) : (
              <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>—</span>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="plan-card-small" style={{ opacity: 0.9 }}>เรทรีวิวที่พัก:</span>
            {(hotel.visuals?.review_score != null || hotel.rating != null) ? (
              <span style={{ fontSize: 13, background: '#4CAF50', color: 'white', padding: '3px 8px', borderRadius: 4 }}>
                {(hotel.visuals?.review_score ?? hotel.rating)} / 5 ({(hotel.visuals?.review_count ?? 0) || 0} รีวิว)
              </span>
            ) : (
              <span style={{ fontSize: 13, color: 'rgba(255,255,255,0.5)' }}>—</span>
            )}
          </div>
        </div>

        <div className="plan-card-section-body">

          {/* 3. ที่อยู่ */}
          {(hotel.location?.address || hotel?.address) && (
            <div className="plan-card-small" style={{ marginBottom: 8, opacity: 0.9 }}>📍 {hotel.location?.address || hotel.address}</div>
          )}

          {/* 4. รูปแบบห้อง */}
          {(hotel.booking?.room?.room_type || hotel.booking?.room?.description) && (
            <div style={{ marginBottom: 8, paddingLeft: 8, borderLeft: '3px solid rgba(255,255,255,0.3)' }}>
              <div style={{ fontWeight: 600, fontSize: 15 }}>🛏️ รูปแบบห้อง: {hotel.booking.room.room_type || hotel.booking.room.description || 'Standard'}</div>
              {hotel.booking?.room?.bed_type && (
                <div className="plan-card-small">{hotel.booking.room.bed_quantity ? `${hotel.booking.room.bed_quantity} x ${hotel.booking.room.bed_type}` : hotel.booking.room.bed_type}</div>
              )}
              {hotel.booking?.policies?.meal_plan && (
                <div className="plan-card-small">🍽️ {hotel.booking.policies.meal_plan}</div>
              )}
            </div>
          )}

          {/* 5. จำนวนวันพัก & วันเช็คอิน / เช็คเอาท์ */}
          {(hotelNights != null || checkInStr || checkOutStr) && (
            <div style={{ marginBottom: 8, fontSize: 14 }}>
              {hotelNights != null && <span>📅 จำนวนคืน: {hotelNights} คืน</span>}
              {checkInStr && <div className="plan-card-small">เช็คอิน: {checkInStr}</div>}
              {checkOutStr && <div className="plan-card-small">เช็คเอาท์: {checkOutStr}</div>}
            </div>
          )}

          {/* 6. ส่วนกลาง: Wi-Fi, สระว่ายน้ำ, อาหารเช้า/กลางวัน/เย็น, + original_list fallback */}
          {(hasAnyAmenity || hotel?.amenities) && (
            <div style={{ marginBottom: 12 }}>
              <div className="plan-card-small" style={{ marginBottom: 4, opacity: 0.9 }}>ส่วนกลาง:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, alignItems: 'center', padding: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 6, fontSize: 16 }}>
                {amenityLabels.length > 0 && amenityLabels.map((txt, i) => (
                  <span key={i}>
                    {txt === 'Wi-Fi' && '📶 '}
                    {txt === 'สระว่ายน้ำ' && '🏊 '}
                    {txt === 'อาหารเช้า' && '🍳 '}
                    {txt === 'อาหารกลางวัน' && '☀️ '}
                    {txt === 'อาหารเย็น' && '🌙 '}
                    {txt === 'ฟิตเนส' && '🏋️ '}
                    {txt === 'ที่จอดรถ' && '🅿️ '}
                    {txt === 'สปา' && '💆 '}
                    {txt === 'แอร์' && '❄️ '}
                    {txt}
                  </span>
                ))}
                {amenityLabels.length === 0 && (
                  <>
                    {hotel.amenities?.has_wifi && <span title="Wi-Fi">📶 Wi-Fi</span>}
                    {hotel.amenities?.has_pool && <span title="สระว่ายน้ำ">🏊 สระว่ายน้ำ</span>}
                    {hotel.amenities?.has_fitness && <span title="ฟิตเนส">🏋️ ฟิตเนส</span>}
                    {hotel.amenities?.has_parking && <span title="ที่จอดรถ">🅿️ ที่จอดรถ</span>}
                    {hotel.amenities?.has_spa && <span title="สปา">💆 สปา</span>}
                    {hotel.amenities?.has_air_conditioning && <span title="แอร์">❄️ แอร์</span>}
                  </>
                )}
                {originalList.length > 0 && (
                  originalList.slice(0, 12).map((item, i) => (
                    <span key={`orig-${i}`} style={{ fontSize: 14, opacity: 0.95 }}>{String(item)}</span>
                  ))
                )}
              </div>
            </div>
          )}

          {/* 7. นโยบายยกเลิก */}
          {hotel.booking?.policies && (
            <div style={{ marginBottom: 12 }}>
              <span style={{ display: 'inline-block', padding: '2px 6px', borderRadius: 4, fontSize: 11, fontWeight: 600, backgroundColor: hotel.booking.policies.is_refundable ? 'rgba(74, 222, 128, 0.2)' : 'rgba(248, 113, 113, 0.2)', color: hotel.booking.policies.is_refundable ? '#4ade80' : '#f87171' }}>
                {hotel.booking.policies.is_refundable ? '✅ ยกเลิกฟรี' : '❌ ห้ามยกเลิก'}
              </span>
            </div>
          )}

          {/* 8. ราคาที่พัก / ราคาค่าธรรมเนียม / ราคารวมรวมค่าธรรมเนียมแล้ว */}
          {(pricePerNight != null || taxesAndFees != null || totalAmount != null) && (
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid rgba(255,255,255,0.2)' }}>
              {pricePerNight != null && (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 13, opacity: 0.8 }}>ราคาที่พัก (ต่อคืน)</span>
                  <span style={{ fontWeight: 600 }}>{formatPriceInThb(pricePerNight, pricingCurrency)}</span>
                </div>
              )}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontSize: 13, opacity: 0.8 }}>ราคาค่าธรรมเนียม</span>
                <span style={{ fontSize: 13 }}>{formatPriceInThb(taxesAndFees ?? 0, pricingCurrency)}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 6, fontSize: 16 }}>
                <span style={{ fontWeight: 600 }}>ราคาที่พักรวมค่าธรรมเนียมแล้ว</span>
                <span style={{ fontWeight: 700, color: '#81c784' }}>{formatPriceInThb(totalAmount, pricingCurrency)}</span>
              </div>
            </div>
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
