/**
 * ล็อกการทำรายการเมื่อเลยวันเดินทาง/วันสิ้นสุดทริปแล้ว (ยังอ่านประวัติได้)
 * ใช้วันสุดท้ายของทริป = max(วันกลับ, เช็คเอาท์, คืนรถ, end_date) ถ้ามี
 * ถ้าไม่มีวันสิ้น ใช้ max(วันออกเดินทาง, เช็คอิน, รับรถ, start_date)
 */

const DATE_KEYS_START = ['departure_date', 'check_in', 'pickup_date', 'start_date'];
const DATE_KEYS_END = ['return_date', 'check_out', 'dropoff_date', 'end_date'];

function extractYmd(val) {
  if (val == null || val === '') return null;
  const s = String(val).trim().slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null;
  return s;
}

function startOfTodayLocal() {
  const n = new Date();
  return new Date(n.getFullYear(), n.getMonth(), n.getDate());
}

function ymdToLocalDate(ymd) {
  const [y, m, d] = ymd.split('-').map(Number);
  return new Date(y, m - 1, d);
}

const ARRAY_KEYS = ['flights', 'accommodations', 'accommodation', 'ground_transport', 'segments', 'outbound', 'inbound'];
const NEST_KEYS = ['flight', 'hotel', 'accommodation', 'ground_transport', 'transport', 'car', 'travel', 'requirements', 'selected_option', 'raw_data'];

function scanObject(o, starts, ends, visited) {
  if (!o || typeof o !== 'object') return;
  if (visited.has(o)) return;
  visited.add(o);

  for (const k of DATE_KEYS_START) {
    const y = extractYmd(o[k]);
    if (y) starts.push(y);
  }
  for (const k of DATE_KEYS_END) {
    const y = extractYmd(o[k]);
    if (y) ends.push(y);
  }
  for (const k of ARRAY_KEYS) {
    if (Array.isArray(o[k])) {
      o[k].forEach((item) => scanObject(item, starts, ends, visited));
    }
  }
  for (const k of NEST_KEYS) {
    if (o[k] && typeof o[k] === 'object') {
      scanObject(o[k], starts, ends, visited);
    }
  }
}

/**
 * @param {object|null|undefined} slots — travel_slots
 * @param {object|null|undefined} plan — plan
 * @returns {boolean} true = เลยวันแล้ว ห้ามทำรายการ (จอง/ชำระ/แก้ไข)
 */
export function isTripPastTransactionDeadline(slots, plan) {
  const starts = [];
  const ends = [];
  const visited = new WeakSet();
  if (slots && typeof slots === 'object') scanObject(slots, starts, ends, visited);
  if (plan && typeof plan === 'object') scanObject(plan, starts, ends, visited);

  if (!starts.length && !ends.length) return false;

  let deadlineYmd = null;
  if (ends.length) {
    deadlineYmd = ends.reduce((a, b) => (a > b ? a : b));
  } else {
    deadlineYmd = starts.reduce((a, b) => (a > b ? a : b));
  }

  const today = startOfTodayLocal();
  const deadline = ymdToLocalDate(deadlineYmd);
  return today.getTime() > deadline.getTime();
}
