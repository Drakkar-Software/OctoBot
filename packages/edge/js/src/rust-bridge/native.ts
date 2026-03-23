import type { RustBridge } from "./types"

let bridge: RustBridge | null = null

// napi-rs auto-converts snake_case to camelCase, so these match RustBridge.
const REQUIRED_METHODS: (keyof RustBridge)[] = [
  "hmac", "hash", "hmacSha256", "hmacSha256Hex", "hmacSha512", "hmacSha512Hex",
  "randomBytesHex", "randomBytes",
  "bufferToHex", "bufferFromHex", "bufferToBase64", "bufferFromBase64", "bufferByteLength",
]

export async function loadNative(): Promise<RustBridge | null> {
  if (bridge) return bridge
  try {
    // napi-rs generates this via `napi build --js`
    const mod = await import("./native.node")

    // napi-rs converts snake_case Rust names to camelCase JS names.
    // Validate all required methods exist.
    for (const method of REQUIRED_METHODS) {
      if (typeof mod[method] !== "function") {
        // If camelCase not found, the NAPI build may have used different naming.
        // Log which method is missing for debugging.
        console.warn(`[edge] Native bridge missing method: ${method}`)
        return null
      }
    }
    bridge = mod as RustBridge
    return bridge
  } catch {
    // Native module not available (expected in browser/WASM environments)
    return null
  }
}
