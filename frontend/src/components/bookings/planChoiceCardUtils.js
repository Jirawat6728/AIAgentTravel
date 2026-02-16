/**
 * Shared helpers for PlanChoiceCard components (Flights, Hotels, Transfer).
 * แยกใช้ร่วมกันเพื่อลดบั๊กและให้แก้ทีละประเภทได้อิสระ
 */

export function formatMoney(value, currency = 'THB') {
  if (typeof value !== 'number' || Number.isNaN(value)) return null;
  return `${currency} ${value.toLocaleString('th-TH')}`;
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
