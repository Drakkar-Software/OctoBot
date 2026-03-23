import type { RustBridge } from "../rust-bridge/types"

/** Minimal exchange interface for patching — avoids ccxt namespace resolution issues. */
interface PatchableExchange {
  hmac: (...args: any[]) => any
}

let enc: TextEncoder | null = null

function getEncoder(): TextEncoder {
  if (!enc) enc = new TextEncoder()
  return enc
}

/** Convert a string or binary value to Uint8Array, preserving byte fidelity. */
function toBytes(value: string | Uint8Array | ArrayBuffer): Uint8Array {
  if (value instanceof Uint8Array) return value
  if (value instanceof ArrayBuffer) return new Uint8Array(value)
  // Use TextEncoder for standard strings. CCXT secrets/requests are typically
  // ASCII, so UTF-8 encoding matches the expected byte representation.
  return getEncoder().encode(value)
}

export function patchExchange(exchange: PatchableExchange, rustBridge: RustBridge | null): void {
  if (!rustBridge) return

  const original = exchange.hmac.bind(exchange)

  exchange.hmac = function (
    request: string | Uint8Array,
    secret: string | Uint8Array,
    hash: string = "sha256",
    digest: string = "hex",
  ): string {
    // Only accelerate hex-encoded HMAC; fall back for other digest formats
    if (digest === "hex") {
      const algo = typeof hash === "string" ? hash.toLowerCase() : ""
      if (algo === "sha256") {
        return rustBridge.hmacSha256Hex(toBytes(secret), toBytes(request))
      }
      if (algo === "sha512") {
        return rustBridge.hmacSha512Hex(toBytes(secret), toBytes(request))
      }
    }
    return original(request, secret, hash, digest)
  }
}
