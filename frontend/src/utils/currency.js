/**
 * แปลงและแสดงราคาเป็นบาท (THB) เท่านั้น
 * อัตราอ้างอิงใช้สำหรับแสดงผลเมื่อ API ส่งสกุลเงินอื่น (JPY, USD ฯลฯ)
 */
const RATE_TO_THB = {
  JPY: 0.25,
  USD: 35,
  EUR: 38,
  GBP: 44,
  SGD: 26,
  KRW: 0.026,
  CNY: 4.9,
  HKD: 4.5,
  THB: 1,
};

/**
 * แปลงจำนวนเงินจากสกุลเงินต้นทางเป็นบาท (ประมาณการ)
 * @param {number} amount - จำนวนเงิน
 * @param {string} sourceCurrency - รหัสสกุลเงิน (THB, JPY, USD ฯลฯ)
 * @returns {number|null} จำนวนบาท (ปัดเศษ) หรือ null ถ้า amount ไม่ถูกต้อง
 */
export function toThb(amount, sourceCurrency = 'THB') {
  if (amount == null || Number.isNaN(Number(amount))) return null;
  const c = String(sourceCurrency || 'THB').toUpperCase();
  if (c === 'THB') return Math.round(Number(amount));
  const rate = RATE_TO_THB[c];
  if (rate == null) return Math.round(Number(amount));
  return Math.round(Number(amount) * rate);
}

/**
 * แสดงราคาเป็นบาทเท่านั้น — ใช้ทุกที่ที่ต้องแสดงเงิน
 * @param {number} amount - จำนวนเงิน
 * @param {string} sourceCurrency - สกุลเงินเดิม (THB, JPY, USD ฯลฯ)
 * @returns {string} เช่น "฿1,234" หรือ "—" ถ้าไม่มีค่า
 */
export function formatPriceInThb(amount, sourceCurrency = 'THB') {
  const thb = toThb(amount, sourceCurrency);
  if (thb == null) return '—';
  try {
    return new Intl.NumberFormat('th-TH', {
      style: 'currency',
      currency: 'THB',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(thb);
  } catch {
    return `฿${thb.toLocaleString('th-TH')}`;
  }
}

export { RATE_TO_THB };
