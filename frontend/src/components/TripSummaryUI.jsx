import React from 'react';
import './AITravelChat.css';

function money(currency, n) {
  if (n == null || Number.isNaN(Number(n))) return null;
  const c = currency || 'THB';
  try {
    // if THB -> no decimals
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

export function TripSummaryCard({ plan, travelSlots }) {
  if (!plan) return null;

  const currency =
    plan?.price_breakdown?.currency ||
    plan?.currency ||
    plan?.flight?.currency ||
    plan?.hotel?.currency ||
    'THB';

  const total =
    typeof plan?.total_price === 'number'
      ? plan.total_price
      : typeof plan?.price === 'number'
        ? plan.price
        : plan?.summary?.total_price;

  const totalText = money(currency, total) || safeText(plan?.total_price_text || plan?.summary?.total_price_text);

  const origin = travelSlots?.origin_city || travelSlots?.origin || travelSlots?.origin_iata || '';
  const dest = travelSlots?.destination_city || travelSlots?.destination || travelSlots?.destination_iata || '';
  const dateGo = travelSlots?.departure_date || travelSlots?.start_date || '';
  const dateBack = travelSlots?.return_date || travelSlots?.end_date || '';
  const pax = [
    travelSlots?.adults != null ? `ผู้ใหญ่ ${travelSlots.adults}` : null,
    travelSlots?.children != null ? `เด็ก ${travelSlots.children}` : null,
    travelSlots?.infants != null ? `ทารก ${travelSlots.infants}` : null,
  ].filter(Boolean).join(' • ');

  const badgeLabel = plan?.badge?.label || plan?.label || 'ตัวเลือกที่เลือก';
  const title = plan?.title ? plan.title : `✅ เลือกช้อยส์ ${plan?.id ?? ''} — ${badgeLabel}`;

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">{title}</span>
          <span className="plan-card-tag">สรุปทริป</span>
        </div>
      </div>

      {/* Overview */}
      <div className="plan-card-section">
        <div className="plan-card-section-title">🧾 ภาพรวม</div>
        <div className="plan-card-section-body">
          {kv('ต้นทาง → ปลายทาง', origin && dest ? `${origin} → ${dest}` : '')}
          {kv('วันเดินทาง', dateGo)}
          {kv('วันกลับ', dateBack)}
          {kv('ผู้โดยสาร', pax)}
        </div>
      </div>

      {/* Selected details */}
      <div className="plan-card-section">
        <div className="plan-card-section-title">✅ รายการที่เลือก</div>
        <div className="plan-card-section-body">
          {kv('เที่ยวบิน', plan?.flight?.title || plan?.flight?.summary || plan?.flight_summary)}
          {kv('ที่พัก', plan?.hotel?.hotelName || plan?.hotel?.name || plan?.hotel?.summary || plan?.hotel_summary)}
          {kv('การเดินทาง', plan?.transport?.summary || plan?.transport_summary)}
        </div>
      </div>

      {/* Price */}
      <div className="plan-card-footer">
        <div className="plan-card-price">{totalText || '—'}</div>
        <div className="summary-note">ราคาอ้างอิงจาก Amadeus Search (production)</div>
      </div>
    </div>
  );
}

export function EditSectionCard({ onSelectSection, hints = [] }) {
  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">✍️ แก้ไขเฉพาะส่วน</span>
          <span className="plan-card-tag">Edit</span>
        </div>
      </div>

      <div className="plan-card-desc">
        เลือกส่วนที่อยากแก้ไข แล้วพิมพ์รายละเอียดต่อได้เลย (หรือพิมพ์ “ยืนยัน” เพื่อไปขั้นจอง)
      </div>

      <div className="summary-actions">
        <button className="summary-action" onClick={() => onSelectSection?.('flight')}>✈️ ไฟลต์</button>
        <button className="summary-action" onClick={() => onSelectSection?.('hotel')}>🏨 ที่พัก</button>
        <button className="summary-action" onClick={() => onSelectSection?.('dates')}>🗓️ วัน/คืน</button>
        <button className="summary-action" onClick={() => onSelectSection?.('pax')}>👨‍👩‍👧‍👦 จำนวนคน</button>
        <button className="summary-action" onClick={() => onSelectSection?.('transport')}>🚗 การเดินทาง</button>
      </div>

      {Array.isArray(hints) && hints.length > 0 && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">💡 ตัวอย่างคำสั่ง</div>
          <div className="plan-card-section-body">
            <div className="summary-hints">
              {hints.slice(0, 8).map((h, idx) => (
                <span key={idx} className="plan-tag-pill">{h}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export function UserInfoCard({ userProfile }) {
  if (!userProfile) return null;

  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">👤 ข้อมูลผู้ใช้สำหรับการจอง</span>
          <span className="plan-card-tag">Traveler</span>
        </div>
      </div>

      <div className="plan-card-section">
        <div className="plan-card-section-title">ข้อมูลที่จะใช้ตอนยืนยันจอง</div>
        <div className="plan-card-section-body">
          {kv('ชื่อ', userProfile.first_name)}
          {kv('นามสกุล', userProfile.last_name)}
          {kv('อีเมล', userProfile.email)}
          {kv('เบอร์โทร', userProfile.phone)}
          {kv('วันเกิด', userProfile.dob)}
          {kv('เพศ', userProfile.gender)}
          {kv('พาสปอร์ต', userProfile.passport_no)}
          {kv('หมดอายุพาสปอร์ต', userProfile.passport_expiry)}
          {kv('สัญชาติ', userProfile.nationality)}
        </div>
      </div>
    </div>
  );
}

export function ConfirmBookingCard({ canBook, onConfirm, note }) {
  return (
    <div className="plan-card plan-card-summary">
      <div className="plan-card-header">
        <div className="plan-card-title">
          <span className="plan-card-label">✅ ยืนยันจอง</span>
          <span className="plan-card-tag">Sandbox</span>
        </div>
      </div>

      <div className="plan-card-section">
        <div className="plan-card-section-title">ความปลอดภัย</div>
        <div className="plan-card-section-body plan-card-small">
          <div>🔒 ระบบล็อกให้จองได้เฉพาะ Amadeus Sandbox (test) เท่านั้น</div>
          {note ? <div className="plan-card-small">{note}</div> : null}
        </div>
      </div>

      <div className="plan-card-footer summary-footer">
        <button
          className={`plan-card-button ${!canBook ? 'summary-disabled' : ''}`}
          disabled={!canBook}
          onClick={onConfirm}
        >
          ✅ ยืนยันจองใน Sandbox
        </button>
      </div>
    </div>
  );
}
