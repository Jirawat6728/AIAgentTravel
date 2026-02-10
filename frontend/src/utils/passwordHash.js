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
