// The SDK's own hex<->bytes helpers live in its internal tier and aren't
// part of the public surface (`identity/`'s exports take/return hex strings
// already for everything a consumer needs). This is the same 3-line
// conversion, kept local rather than reaching into the SDK's internals.
export function hexToBytes(hex: string): Uint8Array {
  const clean = hex.startsWith("0x") ? hex.slice(2) : hex
  const bytes = new Uint8Array(clean.length / 2)
  for (let i = 0; i < bytes.length; i++)
    bytes[i] = Number.parseInt(clean.slice(i * 2, i * 2 + 2), 16)
  return bytes
}

export function bytesToHex(bytes: Uint8Array): string {
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
}
