/**
 * โหลด Omise.js (ใช้ร่วมกับ PaymentPage และ UserProfileEditPage)
 * @param {string} apiBaseUrl - Base URL ของ backend สำหรับ proxy omise.js
 */
export const waitForOmise = (maxMs = 3000, intervalMs = 100) => {
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.Omise) {
      resolve();
      return;
    }
    const start = Date.now();
    const t = setInterval(() => {
      if (typeof window !== 'undefined' && window.Omise) {
        clearInterval(t);
        resolve();
        return;
      }
      if (Date.now() - start >= maxMs) {
        clearInterval(t);
        reject(new Error('Omise.js did not initialize in time'));
      }
    }, intervalMs);
  });
};

const OMISE_CDN_URL = 'https://cdn.omise.co/omise.js';

export const loadOmiseScript = (apiBaseUrl, retryCount = 0) => {
  const maxRetries = 3;
  return new Promise((resolve, reject) => {
    if (typeof window !== 'undefined' && window.Omise) {
      resolve();
      return;
    }
    const existing = document.querySelector('script[data-omise-script]');
    if (existing) existing.remove();

    // ถ้ามี apiBaseUrl ใช้ proxy ของ backend เท่านั้น (ไม่พึ่ง cdn.omise.co เพื่อกัน ERR_NAME_NOT_RESOLVED / เน็ตบล็อก)
    const useProxy = Boolean(apiBaseUrl);
    const scriptUrl = useProxy
      ? `${apiBaseUrl}/api/booking/omise.js?t=${Date.now()}`
      : OMISE_CDN_URL + (retryCount > 0 ? '?t=' + Date.now() : '');

    const script = document.createElement('script');
    script.setAttribute('data-omise-script', '1');
    script.src = scriptUrl;
    script.async = true;
    if (!useProxy) script.crossOrigin = 'anonymous';

    script.onload = () => {
      waitForOmise()
        .then(resolve)
        .catch(() => {
          if (retryCount < maxRetries) {
            loadOmiseScript(apiBaseUrl, retryCount + 1).then(resolve).catch(reject);
          } else {
            reject(new Error('Omise.js โหลดไม่สำเร็จ — กรุณารอสักครู่หรือรีเฟรชหน้า'));
          }
        });
    };
    script.onerror = () => {
      if (retryCount < maxRetries) {
        loadOmiseScript(apiBaseUrl, retryCount + 1).then(resolve).catch(reject);
      } else {
        reject(new Error(
          useProxy
            ? 'โหลด Omise ไม่ได้ — ตรวจสอบว่า Backend (พอร์ต 8000) รันอยู่ และ VITE_API_BASE_URL ถูกต้อง'
            : 'โหลด Omise ไม่ได้ — ตรวจสอบการเชื่อมต่ออินเทอร์เน็ต หรือใช้ผ่าน Backend proxy'
        ));
      }
    };
    document.head.appendChild(script);
  });
};

/**
 * สร้าง Omise token ด้วย callback API (Omise.js ไม่คืน Promise โดยตรง)
 * @param {object} card - { name, number, expiration_month, expiration_year, security_code, ... }
 * @returns {Promise<object>} - response object (มี .id และ .object) หรือ reject เมื่อ error
 */
export const createTokenAsync = (card) => {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.Omise) {
      reject(new Error('Omise.js ยังไม่โหลด'));
      return;
    }
    window.Omise.createToken('card', card, (statusCode, response) => {
      if (statusCode === 200 && response && response.object === 'token') {
        resolve(response);
      } else if (response && response.object === 'error') {
        reject(new Error(response.message || 'ข้อมูลบัตรไม่ถูกต้อง'));
      } else {
        reject(new Error(response?.message || 'การเชื่อมต่อ Omise ล้มเหลว'));
      }
    });
  });
};
