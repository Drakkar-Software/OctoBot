/**
 * Tests for the browser polyfill (installBrowserPolyfills).
 * Uses a mock RustBridge backed by Node.js crypto.
 */
import { describe, test, expect, beforeAll, afterAll } from "@jest/globals"
import { installBrowserPolyfills } from "../src/polyfills/browser"
import type { RustBridge } from "../src/rust-bridge/types"
import { createHmac, createHash, randomBytes as nodeRandomBytes } from "crypto"

// Capture the native Node Buffer BEFORE polyfills overwrite globalThis.Buffer
const NodeBuffer = Buffer

function createNodeBridge(): RustBridge {
  return {
    hmacSha256: (key, message) => new Uint8Array(createHmac("sha256", key).update(message).digest()),
    hmacSha256Hex: (key, message) => createHmac("sha256", key).update(message).digest("hex"),
    hmacSha512: (key, message) => new Uint8Array(createHmac("sha512", key).update(message).digest()),
    hmacSha512Hex: (key, message) => createHmac("sha512", key).update(message).digest("hex"),
    hmac: (algorithm, secret, data, encoding) => createHmac(algorithm, secret).update(data).digest(encoding as any),
    hash: (algorithm, data, encoding) => createHash(algorithm).update(data).digest(encoding as any),
    randomBytesHex: (size) => nodeRandomBytes(size).toString("hex"),
    randomBytes: (size) => new Uint8Array(nodeRandomBytes(size)),
    bufferToHex: (data) => NodeBuffer.from(data).toString("hex"),
    bufferFromHex: (hexStr) => new Uint8Array(NodeBuffer.from(hexStr, "hex")),
    bufferToBase64: (data) => NodeBuffer.from(data).toString("base64"),
    bufferFromBase64: (b64) => new Uint8Array(NodeBuffer.from(b64, "base64")),
    bufferByteLength: (utf8Str) => NodeBuffer.byteLength(utf8Str, "utf8"),
  }
}

describe("installBrowserPolyfills", () => {
  const g = globalThis as any
  let savedCrypto: any
  let savedBuffer: any

  beforeAll(async () => {
    savedCrypto = g.crypto
    savedBuffer = g.Buffer
    // Reset to simulate browser
    g.crypto = { getRandomValues: () => {} }
    delete g.Buffer

    const bridge = createNodeBridge()
    await installBrowserPolyfills(bridge)
  })

  afterAll(() => {
    g.crypto = savedCrypto
    g.Buffer = savedBuffer
  })

  // ── Crypto polyfills ─────────────────────────────────────────────────

  test("installs crypto.createHmac", () => {
    expect(typeof g.crypto.createHmac).toBe("function")
    const result = g.crypto.createHmac("sha256", "secret").update("message").digest("hex")
    expect(result.length).toBe(64)
  })

  test("installs crypto.createHash", () => {
    expect(typeof g.crypto.createHash).toBe("function")
    const result = g.crypto.createHash("sha256").update("hello world").digest("hex")
    expect(result).toBe("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")
  })

  test("installs crypto.randomBytes", () => {
    expect(typeof g.crypto.randomBytes).toBe("function")
    const result = g.crypto.randomBytes(16)
    expect(result).toBeInstanceOf(Uint8Array)
    expect(result.length).toBe(16)
  })

  test("preserves existing getRandomValues", () => {
    // getRandomValues should be preserved from the original crypto
    expect(typeof g.crypto.getRandomValues).toBe("function")
  })

  // ── Buffer polyfill ──────────────────────────────────────────────────

  test("installs globalThis.Buffer", () => {
    expect(typeof g.Buffer).toBe("function")
  })

  test("Buffer.from(string, utf8) roundtrips", () => {
    const buf = g.Buffer.from("hello", "utf8")
    expect(buf.toString()).toBe("hello")
  })

  test("Buffer.from(string, hex) roundtrips", () => {
    const buf = g.Buffer.from("deadbeef", "hex")
    expect(buf.toString("hex")).toBe("deadbeef")
  })

  test("Buffer.from(string, base64) roundtrips", () => {
    const buf = g.Buffer.from("aGVsbG8=", "base64")
    expect(buf.toString("base64")).toBe("aGVsbG8=")
  })

  test("Buffer.alloc creates zero-filled buffer", () => {
    const buf = g.Buffer.alloc(4)
    expect(buf.length).toBe(4)
    expect(Array.from(buf)).toEqual([0, 0, 0, 0])
  })

  test("Buffer.concat joins multiple buffers", () => {
    const a = g.Buffer.from("ab", "utf8")
    const b = g.Buffer.from("cd", "utf8")
    const result = g.Buffer.concat([a, b])
    expect(result.toString()).toBe("abcd")
  })

  test("Buffer.byteLength returns UTF-8 byte length", () => {
    expect(g.Buffer.byteLength("hello")).toBe(5)
  })

  test("Buffer.isBuffer returns true for Buffer instances", () => {
    const buf = g.Buffer.from("x", "utf8")
    expect(g.Buffer.isBuffer(buf)).toBe(true)
    expect(g.Buffer.isBuffer(new Uint8Array(1))).toBe(false)
  })

  // ── Idempotency ──────────────────────────────────────────────────────

  test("calling installBrowserPolyfills twice is safe", async () => {
    const bridge = createNodeBridge()
    await installBrowserPolyfills(bridge)
    // Should still work
    const result = g.crypto.createHash("sha256").update("test").digest("hex")
    expect(result.length).toBe(64)
  })
})
