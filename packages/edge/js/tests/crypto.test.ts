/**
 * Tests for the crypto polyfill (installCryptoPolyfill).
 */
import { describe, test, expect, beforeAll, afterAll } from "@jest/globals"
import { installCryptoPolyfill } from "../src/polyfills/crypto"
import type { RustBridge } from "../src/rust-bridge/types"
import { createHmac, createHash, randomBytes as nodeRandomBytes } from "crypto"

// Create a real bridge backed by Node.js crypto for testing
function createNodeBridge(): RustBridge {
  return {
    hmacSha256(key, message) {
      return new Uint8Array(createHmac("sha256", key).update(message).digest())
    },
    hmacSha256Hex(key, message) {
      return createHmac("sha256", key).update(message).digest("hex")
    },
    hmacSha512(key, message) {
      return new Uint8Array(createHmac("sha512", key).update(message).digest())
    },
    hmacSha512Hex(key, message) {
      return createHmac("sha512", key).update(message).digest("hex")
    },
    hmac(algorithm, secret, data, encoding) {
      return createHmac(algorithm, secret).update(data).digest(encoding as any)
    },
    hash(algorithm, data, encoding) {
      return createHash(algorithm).update(data).digest(encoding as any)
    },
    randomBytesHex(size) {
      return nodeRandomBytes(size).toString("hex")
    },
    randomBytes(size) {
      return new Uint8Array(nodeRandomBytes(size))
    },
    bufferToHex(data) {
      return Buffer.from(data).toString("hex")
    },
    bufferFromHex(hexStr) {
      return new Uint8Array(Buffer.from(hexStr, "hex"))
    },
    bufferToBase64(data) {
      return Buffer.from(data).toString("base64")
    },
    bufferFromBase64(b64) {
      return new Uint8Array(Buffer.from(b64, "base64"))
    },
    bufferByteLength(utf8Str) {
      return Buffer.byteLength(utf8Str, "utf8")
    },
  }
}

describe("installCryptoPolyfill", () => {
  const g = globalThis as any
  let savedCrypto: any

  beforeAll(() => {
    savedCrypto = g.crypto
    // Wipe crypto to test installation from scratch
    g.crypto = undefined
  })

  afterAll(() => {
    g.crypto = savedCrypto
  })

  test("installs crypto.createHmac", () => {
    const bridge = createNodeBridge()
    installCryptoPolyfill(bridge)

    expect(typeof g.crypto.createHmac).toBe("function")
    const result = g.crypto.createHmac("sha256", "secret").update("message").digest("hex")
    expect(typeof result).toBe("string")
    expect(result.length).toBe(64)
  })

  test("installs crypto.createHash", () => {
    const result = g.crypto.createHash("sha256").update("hello world").digest("hex")
    expect(result).toBe("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")
  })

  test("createHmac supports chained updates", () => {
    const polyfill = g.crypto.createHmac("sha256", "key")
      .update("part1")
      .update("part2")
      .digest("hex")

    const native = createHmac("sha256", "key")
      .update("part1part2")
      .digest("hex")

    expect(polyfill).toBe(native)
  })

  test("createHash supports chained updates", () => {
    const polyfill = g.crypto.createHash("sha256")
      .update("a")
      .update("b")
      .digest("hex")

    const native = createHash("sha256")
      .update("ab")
      .digest("hex")

    expect(polyfill).toBe(native)
  })

  test("createHmac handles Uint8Array input", () => {
    const data = new TextEncoder().encode("message")
    const result = g.crypto.createHmac("sha256", "key").update(data).digest("hex")

    const expected = createHmac("sha256", "key").update("message").digest("hex")
    expect(result).toBe(expected)
  })

  test("idempotent - calling twice doesn't break", () => {
    const bridge = createNodeBridge()
    installCryptoPolyfill(bridge)
    installCryptoPolyfill(bridge)

    const result = g.crypto.createHmac("sha256", "s").update("d").digest("hex")
    expect(result.length).toBe(64)
  })
})
