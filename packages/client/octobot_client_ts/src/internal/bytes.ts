// Small hex/byte helpers shared across the package. Previously duplicated
// verbatim across auth/cap-provider.ts, auth/auth-core.ts and other files in
// @drakkar.software/octobot-sdk — consolidated here during the extraction.
// Zero dependencies by design (tier 0): every other tier may import this.

export function toHex(b: Uint8Array): string {
  return Array.from(b, (x) => x.toString(16).padStart(2, '0')).join('')
}

export function hexToBytes(hex: string): Uint8Array {
  const h = hex.startsWith('0x') ? hex.slice(2) : hex
  const out = new Uint8Array(h.length / 2)
  for (let i = 0; i < out.length; i++) out[i] = parseInt(h.slice(i * 2, i * 2 + 2), 16)
  return out
}

export function toBase64(bytes: Uint8Array): string {
  return btoa(Array.from(bytes, (b) => String.fromCharCode(b)).join(''))
}

export function fromBase64(b64: string): Uint8Array<ArrayBuffer> {
  const binary = atob(b64)
  const buf = new ArrayBuffer(binary.length)
  const bytes = new Uint8Array(buf)
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)
  return bytes
}

/** URL-safe base64 (`+/` → `-_`, no `=` padding) of raw bytes. Distinct from
 *  `starfish-protocol`'s `toBase64Url`, which encodes a UTF-8 *string* — not
 *  usable here since not every byte sequence (e.g. random session-id bytes)
 *  round-trips through UTF-8. */
export function toBase64Url(bytes: Uint8Array): string {
  return toBase64(bytes).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function fromBase64Url(b64url: string): Uint8Array<ArrayBuffer> {
  const padded = b64url.replace(/-/g, '+').replace(/_/g, '/')
  const padding = padded.length % 4 === 0 ? '' : '='.repeat(4 - (padded.length % 4))
  return fromBase64(padded + padding)
}
