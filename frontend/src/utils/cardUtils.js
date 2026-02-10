/**
 * Card utilities: format, detect type, validate (Luhn + length)
 * ตามมาตรฐาน Omise: https://www.omise.co/supported-cards
 *
 * เครือข่ายการชำระเงิน | เลขนำหน้า (Prefix) | ความยาวตัวเลขบนบัตร (หลัก)
 * Visa | 4 | 13, 16, 19
 * Mastercard | 51-55 หรือ 2221-2720 | 16
 * American Express | 34, 37 | 15
 * JCB | 3528-3589 | 16-19
 * UnionPay | 62, 81 | 14-19
 * Discover | 6011, 622, 644-649, 65 | 16, 19
 * Diners Club | 300-305, 309, 36, 38, 39 | 14-19
 */

export function formatCardNumber(value) {
  const cleaned = (value || '').replace(/\D/g, '');
  const g = cleaned.match(/.{1,4}/g);
  return (g && g.join(' ')) || cleaned;
}

export function getCardTypeFromIIN(cardNumber) {
  const digits = (cardNumber || '').replace(/\s/g, '');
  if (digits.length < 6 || !/^\d+$/.test(digits)) return null;
  const iin6 = digits.substring(0, 6);
  const iin4 = digits.substring(0, 4);
  const iin3 = digits.substring(0, 3);
  const iin2 = digits.substring(0, 2);
  const n6 = parseInt(iin6, 10);
  const n4 = parseInt(iin4, 10);
  const n2 = parseInt(iin2, 10);

  if (digits.startsWith('4')) return { cardType: 'visa', iin: iin6, label: 'Visa' };
  if (iin2 === '34' || iin2 === '37') return { cardType: 'amex', iin: iin6, label: 'American Express' };
  if (n4 >= 3528 && n4 <= 3589) return { cardType: 'jcb', iin: iin6, label: 'JCB' };
  if ((n4 >= 300 && n4 <= 305) || iin3 === '309' || iin2 === '36' || iin2 === '38' || iin2 === '39') return { cardType: 'diners', iin: iin6, label: 'Diners Club' };
  if (iin4 === '6011') return { cardType: 'discover', iin: iin6, label: 'Discover' };
  if (iin3 === '622' || (n4 >= 644 && n4 <= 649)) return { cardType: 'discover', iin: iin6, label: 'Discover' };
  if (iin2 === '65') return { cardType: 'discover', iin: iin6, label: 'Discover' };
  if (digits.startsWith('62') || digits.startsWith('81')) return { cardType: 'unionpay', iin: iin6, label: 'UnionPay' };
  if (n2 >= 51 && n2 <= 55) return { cardType: 'mastercard', iin: iin6, label: 'Mastercard' };
  if (n4 >= 2221 && n4 <= 2720) return { cardType: 'mastercard', iin: iin6, label: 'Mastercard' };
  return null;
}

export function getCardType(cardNumber) {
  const digits = (cardNumber || '').replace(/\s/g, '');
  if (digits.length < 2) return null;
  const fromIIN = getCardTypeFromIIN(cardNumber);
  if (fromIIN) return fromIIN.cardType;
  if (/^4/.test(digits)) return 'visa';
  if (/^3[47]/.test(digits)) return 'amex';
  if (/^35/.test(digits)) return 'jcb';
  if (/^3[68]/.test(digits) || /^30[0-5]/.test(digits) || /^309/.test(digits)) return 'diners';
  if (/^6011/.test(digits) || /^622/.test(digits) || /^64[4-9]/.test(digits) || /^65/.test(digits)) return 'discover';
  if (/^62/.test(digits) || /^81/.test(digits)) return 'unionpay';
  if (/^5[1-5]/.test(digits) || /^2(22[1-9]|2[3-9]\d|[3-6]\d{2}|7[01]\d|720)/.test(digits)) return 'mastercard';
  return null;
}

/** Luhn algorithm (mod 10) for card number validation */
export function luhnCheck(digits) {
  if (!/^\d+$/.test(digits)) return false;
  let sum = 0;
  let alternate = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let n = parseInt(digits[i], 10);
    if (alternate) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alternate = !alternate;
  }
  return sum % 10 === 0;
}

/** Validate card: length by type + Luhn */
export function validateCardNumber(cardNumber) {
  const digits = (cardNumber || '').replace(/\s/g, '');
  if (!/^\d+$/.test(digits) || digits.length < 13) {
    return { valid: false, cardType: null, label: null, message: 'กรุณากรอกเลขบัตรอย่างน้อย 13 หลัก' };
  }
  const len = digits.length;
  const byIIN = getCardTypeFromIIN(cardNumber);

  const lengthOk = (cardType) => {
    switch (cardType) {
      case 'visa': return len === 13 || len === 16 || len === 19;
      case 'amex': return len === 15;
      case 'jcb': return len >= 16 && len <= 19;
      case 'diners': return len >= 14 && len <= 19;
      case 'discover': return len === 16 || len === 19;
      case 'unionpay': return len >= 14 && len <= 19;
      case 'mastercard': return len === 16;
      default: return false;
    }
  };

  const reqLenByType = { visa: '13, 16 หรือ 19', amex: '15', jcb: '16-19', diners: '14-19', discover: '16 หรือ 19', unionpay: '14-19', mastercard: '16' };

  if (byIIN) {
    const { cardType, label } = byIIN;
    if (!lengthOk(cardType)) {
      const reqLen = reqLenByType[cardType] || '?';
      return { valid: false, cardType, label, message: `บัตร ${label} ต้อง ${reqLen} หลัก` };
    }
    if (!luhnCheck(digits)) {
      return { valid: false, cardType, label, message: 'เลขบัตรไม่ถูกต้อง (เช็ค Luhn ไม่ผ่าน)' };
    }
    return { valid: true, cardType, label, message: `บัตร ${label}` };
  }

  return { valid: false, cardType: null, label: null, message: 'เลขบัตร (IIN) ไม่ตรงกับเครือข่ายบัตรที่รองรับ' };
}
