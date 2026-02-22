/**
 * Hash password with SHA-256 so the real password is never sent in the request.
 * Payload in DevTools will show only the hash (64 hex chars), not the plain password.
 */
export async function sha256Password(plainPassword) {
  const encoder = new TextEncoder();
  const data = encoder.encode(plainPassword);
  const hashBuffer = await crypto.subtle.digest("SHA-256", data);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
  return hashHex;
}

/**
 * ตรวจสอบความแข็งแกร่งรหัสผ่านให้ตรงกับ backend (security.validate_password_strength)
 * เงื่อนไข: อย่างน้อย 8 ตัว, ตัวพิมพ์ใหญ่ 1 ตัว, ตัวพิมพ์เล็ก 1 ตัว, ตัวเลข 1 ตัว, อักขระพิเศษ 1 ตัว
 * @returns {{ valid: boolean, message: string }}
 */
export function validatePasswordStrength(password) {
  if (!password || typeof password !== "string") {
    return { valid: false, message: "กรุณากรอกรหัสผ่าน" };
  }
  if (password.length < 8) {
    return { valid: false, message: "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร" };
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, message: "รหัสผ่านต้องมีตัวอักษรพิมพ์ใหญ่อย่างน้อย 1 ตัว" };
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, message: "รหัสผ่านต้องมีตัวอักษรพิมพ์เล็กอย่างน้อย 1 ตัว" };
  }
  if (!/\d/.test(password)) {
    return { valid: false, message: "รหัสผ่านต้องมีตัวเลขอย่างน้อย 1 ตัว" };
  }
  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    return { valid: false, message: "รหัสผ่านต้องมีอักขระพิเศษอย่างน้อย 1 ตัว (!@#$%^&*(),.?\":{}|<>) " };
  }
  return { valid: true, message: "" };
}
