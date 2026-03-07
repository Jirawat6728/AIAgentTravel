/**
 * Shared helpers for PlanChoiceCard components (Flights, Hotels, Transfer).
 * แยกใช้ร่วมกันเพื่อลดบั๊กและให้แก้ทีละประเภทได้อิสระ
 * ราคาแสดงเป็นบาท (THB) เท่านั้น
 */
import { formatPriceInThb } from '../../utils/currency';

export function formatMoney(value, currency = 'THB') {
  return formatPriceInThb(value, currency);
}

/**
 * แปลง ISO 8601 duration (PT1H15M) เป็นข้อความอ่านง่าย
 */
export function formatDuration(durationStr) {
  if (!durationStr || typeof durationStr !== 'string') return '';
  if (durationStr.startsWith('PT')) {
    let hours = 0;
    let minutes = 0;
    try {
      if (durationStr.includes('H')) {
        const hoursPart = durationStr.split('H')[0].replace('PT', '');
        hours = parseInt(hoursPart) || 0;
        const remaining = durationStr.split('H')[1] || '';
        if (remaining.includes('M')) {
          const minutesPart = remaining.split('M')[0];
          minutes = parseInt(minutesPart) || 0;
        }
      } else {
        const remaining = durationStr.replace('PT', '');
        if (remaining.includes('M')) {
          const minutesPart = remaining.split('M')[0];
          minutes = parseInt(minutesPart) || 0;
        }
      }
      const parts = [];
      if (hours > 0) parts.push(`${hours}ชม`);
      if (minutes > 0) parts.push(`${minutes}นาที`);
      return parts.length > 0 ? parts.join(' ') : 'ไม่ระบุ';
    } catch (e) {
      return durationStr;
    }
  }
  return durationStr;
}

/**
 * แปลง ISO 8601 duration เป็นชั่วโมง (สำหรับคำนวณ CO2)
 */
export function parseDurationToHours(durationStr) {
  if (!durationStr || typeof durationStr !== 'string') return 0;
  if (!durationStr.startsWith('PT')) return 0;
  try {
    let hours = 0;
    let minutes = 0;
    if (durationStr.includes('H')) {
      const hoursPart = durationStr.split('H')[0].replace('PT', '');
      hours = parseInt(hoursPart, 10) || 0;
      const remaining = durationStr.split('H')[1] || '';
      if (remaining.includes('M')) minutes = parseInt(remaining.split('M')[0], 10) || 0;
    } else if (durationStr.includes('M')) {
      minutes = parseInt(durationStr.replace(/^PT|M.*$/g, ''), 10) || 0;
    }
    return hours + minutes / 60;
  } catch (e) {
    return 0;
  }
}

/**
 * คำนวณ CO2e จากระยะทาง (km) — ~220 kg ต่อ 1000 km สำหรับ Economy
 */
export function calculateCO2e(distanceKm) {
  if (!distanceKm || distanceKm <= 0) return 0;
  return Math.round(distanceKm * 0.22);
}
