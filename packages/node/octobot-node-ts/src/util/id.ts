// UUID v4 generator with a React Native-friendly fallback. `crypto.randomUUID`
// is available in Node 18+ and modern browsers; on RN/Hermes it may not be —
// hence the manual fallback using `Math.random` (good enough for execution
// IDs that don't need cryptographic strength).

export function newId(): string {
  const cryptoRef = (globalThis as { crypto?: { randomUUID?: () => string } }).crypto;
  if (cryptoRef && typeof cryptoRef.randomUUID === "function") {
    return cryptoRef.randomUUID();
  }
  // RFC 4122 v4 fallback.
  const bytes = new Array(16);
  for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
