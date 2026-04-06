/**
 * Validation สำหรับ segment เที่ยวบิน — ห้ามซ้ำกัน
 * ใช้ key: from, to, เวลาออก (normalize แล้ว), สายการบิน, เลขเที่ยวบิน
 */

/**
 * แปลงค่าเวลาเป็นรูปแบบเดียวกันเพื่อใช้ใน key (ให้ segment เดียวกันได้ key เดียวแม้ format ต่างกัน)
 * @param {string} dep
 * @returns {string}
 */
function normalizeDepartureKey(dep) {
  if (dep == null || dep === '') return '';
  const s = String(dep).trim();
  if (!s) return '';
  try {
    // รองรับ ISO (2026-03-15T21:00:00) และรูปแบบไทย เช่น 15/3/2569 21:00
    let normalized = s;
    const thaiDateMatch = s.match(/(\d{1,2})\/(\d{1,2})\/(\d{4})\s*(\d{1,2}:\d{2}(?::\d{2})?)?/);
    if (thaiDateMatch) {
      const [, day, month, y, time = '00:00:00'] = thaiDateMatch;
      const year = parseInt(y, 10);
      const budYear = year > 2500 ? year - 543 : year;
      const t = time.length <= 5 ? `${time}:00` : time;
      normalized = `${budYear}-${month.padStart(2, '0')}-${day.padStart(2, '0')}T${t.padEnd(8, '0').slice(0, 8)}`;
    }
    const d = new Date(normalized);
    if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 19);
  } catch (_) {}
  return s.slice(0, 19);
}

/**
 * @param {{ from?: string, to?: string, departure?: string, depart_at?: string, arrival?: string, arrive_at?: string, carrier?: string, number?: string, flight_number?: string }} seg
 * @returns {string}
 */
export function segmentDedupKey(seg) {
  if (!seg || typeof seg !== 'object') return '';
  const from = (seg.from ?? '').toString().trim().toUpperCase();
  const to = (seg.to ?? '').toString().trim().toUpperCase();
  const dep = seg.depart_at ?? seg.departure ?? '';
  const depStr = normalizeDepartureKey(dep != null ? String(dep) : '');
  const carrier = (seg.carrier ?? '').toString().trim().toUpperCase();
  const num = (seg.number ?? seg.flight_number ?? '').toString().trim();
  return `${from}-${to}-${depStr}-${carrier}-${num}`;
}

/**
 * ลบ segment ที่ซ้ำกัน เหลือเฉพาะอันแรกของแต่ละ key (validate: ห้ามซ้ำกัน)
 * @param {Array<object>} segments
 * @returns {Array<object>}
 */
export function dedupeSegments(segments) {
  if (!Array.isArray(segments) || segments.length === 0) return segments;
  const seen = new Set();
  return segments.filter((seg) => {
    const key = segmentDedupKey(seg);
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
