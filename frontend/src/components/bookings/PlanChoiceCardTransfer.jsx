/**
 * PlanChoiceCard เฉพาะ Transfer/Transport ทั้งหมด (รถรับส่ง, รถเช่า, รถโดยสาร, รถไฟ ฯลฯ)
 * แยกอิสระจาก PlanChoiceCard เพื่อแก้บั๊กและแสดงผลการเดินทางเท่านั้น
 */
import React from 'react';
import { formatMoney, formatDuration } from './planChoiceCardUtils';
import { formatPriceInThb } from '../../utils/currency';
import './PlanChoiceCard.css';

function transportTypeLabel(transport, car) {
  if (car) return '🚗 รถเช่า';
  if (transport?.type === 'car_rental') return '🚗 รถเช่า';
  if (transport?.type === 'bus') return '🚌 รถโดยสาร';
  if (transport?.type === 'train') return '🚂 รถไฟ';
  if (transport?.type === 'metro') return '🚇 รถไฟฟ้า';
  if (transport?.type === 'ferry') return '⛴️ เรือ';
  if (transport?.type === 'transfer') return '🚗 รถรับส่ง';
  return '🚗 การเดินทาง';
}

function transportTypeName(transport) {
  if (!transport?.type) return '';
  const names = { car_rental: 'รถเช่า', bus: 'รถโดยสาร', train: 'รถไฟ', metro: 'รถไฟฟ้า', ferry: 'เรือ', transfer: 'รถรับส่ง' };
  return names[transport.type] || transport.type;
}

export default function PlanChoiceCardTransfer({ choice, onSelect }) {
  const { id, label, tags, recommended, transport, car, ground_transport, currency, total_price, total_price_text, price, price_breakdown, title } = choice || {};
  const displayCurrency = price_breakdown?.currency || currency || transport?.currency || car?.currency || 'THB';
  // ✅ ราคารวม: total_price หรือ price (option) หรือ transport/car price แบบ catalog
  const transportPrice = transport?.price ?? transport?.price_amount ?? transport?.data?.price ?? car?.price ?? car?.price_amount;
  const resolvedTotal = typeof total_price === 'number' ? total_price : typeof price === 'number' ? price : (typeof transportPrice === 'number' ? transportPrice : null);
  const hasRealPrice = resolvedTotal != null && Number(resolvedTotal) > 0;
  const displayTotalPrice = hasRealPrice
    ? formatPriceInThb(resolvedTotal, displayCurrency)
    : (total_price_text || 'ราคาต้องสอบถาม');

  const hasContent = ground_transport || transport || car;
  if (!hasContent) {
    return (
      <div className="plan-card">
        <div className="plan-card-header"><span className="plan-card-label">การเดินทาง {title || id}</span></div>
        <p className="plan-card-desc">ไม่มีข้อมูลการเดินทาง</p>
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
          <span className="plan-card-label">{title || `การเดินทาง ${id}${label ? ` — ${label}` : ''}`}</span>
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

      {ground_transport && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">🚗 รายละเอียดการเดินทาง</div>
          <div className="plan-card-section-body plan-card-small">
            {typeof ground_transport === 'string'
              ? ground_transport.split('\n').map((line, idx) => <div key={idx}>{line}</div>)
              : ground_transport.description && <div style={{ marginBottom: 12, fontSize: 15, lineHeight: 1.6 }}>{ground_transport.description}</div>
            }
          </div>
        </div>
      )}

      {(transport || car) && (
        <div className="plan-card-section">
          <div className="plan-card-section-title">{transportTypeLabel(transport, car)}</div>
          <div className="plan-card-section-body plan-card-small">
            {transport?.type && (
              <div style={{ marginBottom: 8, fontSize: 16, fontWeight: 600 }}>ประเภท: {transportTypeName(transport)}</div>
            )}
            {(transport?.route || transport?.data?.route || car?.route) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>เส้นทาง: </span>{transport?.route || transport?.data?.route || car?.route}</div>
            )}
            {(transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount) && (
              <div style={{ marginBottom: 12, padding: 12, background: 'rgba(74, 222, 128, 0.15)', borderRadius: 8, border: '1px solid rgba(74, 222, 128, 0.3)' }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: '#4ade80', marginBottom: 4 }}>
                  💰 ราคา: {formatMoney(transport?.price || transport?.data?.price || car?.price || transport?.price_amount || car?.price_amount, transport?.currency || transport?.data?.currency || car?.currency || 'THB')}
                </div>
                {(transport?.price_per_day || car?.price_per_day) && (
                  <div style={{ fontSize: 14, opacity: 0.9, marginTop: 4 }}>ราคาต่อวัน: {formatMoney(transport?.price_per_day || car?.price_per_day, transport?.currency || car?.currency || 'THB')}</div>
                )}
              </div>
            )}
            {(transport?.duration || transport?.data?.duration || car?.duration) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>⏱️ ระยะเวลา: </span>{formatDuration(transport?.duration || transport?.data?.duration || car?.duration) || (transport?.duration || transport?.data?.duration || car?.duration)}</div>
            )}
            {(transport?.distance || transport?.data?.distance || car?.distance) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>📏 ระยะทาง: </span>{typeof (transport?.distance || transport?.data?.distance || car?.distance) === 'number' ? `${(transport?.distance || transport?.data?.distance || car?.distance).toLocaleString('th-TH')} กม.` : (transport?.distance || transport?.data?.distance || car?.distance)}</div>
            )}
            {(transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>🏢 บริษัท: </span>{transport?.provider || transport?.data?.provider || car?.provider || transport?.company || car?.company}</div>
            )}
            {(transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>🚙 ประเภทรถ: </span>{transport?.vehicle_type || car?.vehicle_type || transport?.car_type || car?.car_type}</div>
            )}
            {(transport?.seats || car?.seats || transport?.capacity || car?.capacity) && (
              <div style={{ marginBottom: 8, fontSize: 15 }}><span style={{ fontWeight: 600 }}>💺 จำนวนที่นั่ง: </span>{transport?.seats || car?.seats || transport?.capacity || car?.capacity} ที่นั่ง</div>
            )}
            {(transport?.details || transport?.data?.details || car?.details) && (
              <div style={{ marginTop: 12, padding: 10, background: 'rgba(255,255,255,0.1)', borderRadius: 6 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>รายละเอียดเพิ่มเติม:</div>
                {Array.isArray(transport?.details || transport?.data?.details || car?.details) ? (transport?.details || transport?.data?.details || car?.details).map((d, i) => <div key={i} style={{ marginBottom: 4 }}>• {d}</div>) : <div>{transport?.details || transport?.data?.details || car?.details}</div>}
              </div>
            )}
            {(transport?.features || car?.features || transport?.amenities || car?.amenities) && (
              <div style={{ marginTop: 12, padding: 10, background: 'rgba(255,255,255,0.1)', borderRadius: 6 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>คุณสมบัติ:</div>
                {Array.isArray(transport?.features || car?.features || transport?.amenities || car?.amenities) ? (transport?.features || car?.features || transport?.amenities || car?.amenities).map((f, i) => <div key={i} style={{ marginBottom: 4 }}>✓ {f}</div>) : <div>{transport?.features || car?.features || transport?.amenities || car?.amenities}</div>}
              </div>
            )}
            {(transport?.note || transport?.data?.note || car?.note) && (
              <div style={{ marginTop: 12, padding: 10, background: 'rgba(255, 193, 7, 0.15)', borderRadius: 6, fontSize: 14 }}><span style={{ fontWeight: 600 }}>📝 หมายเหตุ: </span>{transport?.note || transport?.data?.note || car?.note}</div>
            )}
          </div>
        </div>
      )}

      <div className="plan-card-footer">
        {displayTotalPrice && <div className="plan-card-price">{displayTotalPrice}</div>}
        <button className="plan-card-button" onClick={() => onSelect && onSelect(id)}>เลือกช้อยส์ {id}</button>
      </div>
    </div>
  );
}
