/**
 * crypto.subtle shim that delegates to Rust when available.
 * Used in environments without native Web Crypto API.
 */
import type { RustBridge } from "../rust-bridge/types"

interface HashBuilder {
  update(data: string | Uint8Array): HashBuilder
  digest(encoding: string): string
}

export function installCryptoPolyfill(bridge: RustBridge): void {
  const g = globalThis as any

  if (!g.crypto) {
    g.crypto = {}
  }

  const enc = new TextEncoder()

  function concatChunks(chunks: Uint8Array[]): Uint8Array {
    const total = chunks.reduce((s, c) => s + c.length, 0)
    const result = new Uint8Array(total)
    let offset = 0
    for (const c of chunks) { result.set(c, offset); offset += c.length }
    return result
  }

  g.crypto.createHmac = (algorithm: string, secret: string): HashBuilder => {
    const chunks: Uint8Array[] = []
    const builder: HashBuilder = {
      update(data: string | Uint8Array): HashBuilder {
        chunks.push(typeof data === "string" ? enc.encode(data) : data)
        return builder
      },
      digest(encoding: string): string {
        const message = concatChunks(chunks)
        const secretBytes = enc.encode(secret)
        const algo = algorithm.toLowerCase()
        if (algo === "sha256" && encoding === "hex") return bridge.hmacSha256Hex(secretBytes, message)
        if (algo === "sha512" && encoding === "hex") return bridge.hmacSha512Hex(secretBytes, message)
        const accumulated = new TextDecoder().decode(message)
        return bridge.hmac(algorithm, secret, accumulated, encoding)
      },
    }
    return builder
  }

  g.crypto.createHash = (algorithm: string): HashBuilder => {
    let accumulated = ""
    const builder: HashBuilder = {
      update(data: string | Uint8Array): HashBuilder {
        accumulated += typeof data === "string"
          ? data
          : new TextDecoder().decode(data)
        return builder
      },
      digest(encoding: string): string {
        const result = bridge.hash(algorithm, accumulated, encoding)
        accumulated = ""
        return result
      },
    }
    return builder
  }

  if (typeof g.crypto.randomBytes !== "function") {
    g.crypto.randomBytes = (size: number): Uint8Array => {
      return bridge.randomBytes(size)
    }
  }
}
