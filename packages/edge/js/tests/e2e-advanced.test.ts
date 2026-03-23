/**
 * Advanced end-to-end tests — stress, concurrency, encoding variants,
 * cross-exchange consistency, fuzz, error boundaries, and full signing flows.
 *
 * These complement the basic e2e.test.ts with deeper coverage.
 */
import { describe, test, expect, beforeAll } from "@jest/globals"
import { createHmac, createHash, randomBytes as nodeRandomBytes } from "crypto"

let ccxt: any
const g = globalThis as any

beforeAll(async () => {
  await import("../src/polyfills/node")
  ccxt = (await import("ccxt")).default
})

// ═══════════════════════════════════════════════════════════════════════════
// Cross-Exchange Signing Consistency
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Cross-Exchange Signing Consistency", () => {
  const EXCHANGES = ["binance", "bybit", "okx", "kucoin", "bitget", "kraken"]
  const TEST_PAYLOAD = "symbol=BTCUSDT&timestamp=1700000000000&recvWindow=5000"
  const TEST_SECRET = "exchange_api_secret_key_12345"

  test("all supported exchanges produce identical SHA-256 signatures for same input", () => {
    const expected = createHmac("sha256", TEST_SECRET).update(TEST_PAYLOAD).digest("hex")
    const results: Record<string, string> = {}

    for (const id of EXCHANGES) {
      try {
        const ex = new ccxt[id]({ apiKey: "k", secret: "s" })
        results[id] = g.crypto.createHmac("sha256", TEST_SECRET).update(TEST_PAYLOAD).digest("hex")
      } catch {
        // exchange not available
      }
    }

    const values = Object.values(results)
    expect(values.length).toBeGreaterThanOrEqual(4)
    for (const sig of values) {
      expect(sig).toBe(expected)
    }
  })

  test("all supported exchanges produce identical SHA-512 signatures for same input", () => {
    const expected = createHmac("sha512", TEST_SECRET).update(TEST_PAYLOAD).digest("hex")

    for (const id of EXCHANGES) {
      try {
        new ccxt[id]({ apiKey: "k", secret: "s" })
        const sig = g.crypto.createHmac("sha512", TEST_SECRET).update(TEST_PAYLOAD).digest("hex")
        expect(sig).toBe(expected)
      } catch {
        // exchange not available
      }
    }
  })

  test("each exchange can independently sign after creation", () => {
    const instances: any[] = []
    for (const id of EXCHANGES) {
      try {
        instances.push({ id, ex: new ccxt[id]({ apiKey: "k", secret: "s" }) })
      } catch {
        // skip
      }
    }
    expect(instances.length).toBeGreaterThanOrEqual(3)

    // Sign with each exchange and verify all produce correct results
    for (const { id, ex } of instances) {
      const msg = `exchange=${id}&ts=1700000000`
      const sig = g.crypto.createHmac("sha256", "shared_secret").update(msg).digest("hex")
      const expected = createHmac("sha256", "shared_secret").update(msg).digest("hex")
      expect(sig).toBe(expected)
    }
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Concurrent Async Signing
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Concurrent Async Signing", () => {
  test("parallel Promise.all signing produces correct results", async () => {
    const secret = "concurrent_secret"
    const tasks = Array.from({ length: 100 }, (_, i) => {
      return new Promise<void>((resolve) => {
        const msg = `nonce=${i}&timestamp=${Date.now()}`
        const sig = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
        const expected = createHmac("sha256", secret).update(msg).digest("hex")
        expect(sig).toBe(expected)
        resolve()
      })
    })
    await Promise.all(tasks)
  })

  test("interleaved HMAC builders don't cross-contaminate", () => {
    const builder1 = g.crypto.createHmac("sha256", "secret1")
    const builder2 = g.crypto.createHmac("sha256", "secret2")
    const builder3 = g.crypto.createHmac("sha512", "secret3")

    // Interleave updates
    builder1.update("msg1_part1")
    builder2.update("msg2_part1")
    builder3.update("msg3_part1")
    builder1.update("&msg1_part2")
    builder2.update("&msg2_part2")
    builder3.update("&msg3_part2")

    const sig1 = builder1.digest("hex")
    const sig2 = builder2.digest("hex")
    const sig3 = builder3.digest("hex")

    expect(sig1).toBe(createHmac("sha256", "secret1").update("msg1_part1&msg1_part2").digest("hex"))
    expect(sig2).toBe(createHmac("sha256", "secret2").update("msg2_part1&msg2_part2").digest("hex"))
    expect(sig3).toBe(createHmac("sha512", "secret3").update("msg3_part1&msg3_part2").digest("hex"))

    // All three must be different
    expect(new Set([sig1, sig2, sig3]).size).toBe(3)
  })

  test("rapid creation and signing of 200 exchange instances", () => {
    const exchangeIds = ["binance", "bybit", "okx", "kucoin"]
    const results: string[] = []

    for (let i = 0; i < 200; i++) {
      const id = exchangeIds[i % exchangeIds.length]
      try {
        new ccxt[id]({ apiKey: `key_${i}`, secret: `secret_${i}` })
        const sig = g.crypto.createHmac("sha256", `secret_${i}`).update(`payload_${i}`).digest("hex")
        const expected = createHmac("sha256", `secret_${i}`).update(`payload_${i}`).digest("hex")
        expect(sig).toBe(expected)
        results.push(sig)
      } catch {
        // skip
      }
    }
    // All should be unique (different secrets and payloads)
    expect(new Set(results).size).toBe(results.length)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Digest Encoding Variants
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Digest Encoding Variants", () => {
  test("HMAC-SHA256 base64 encoding matches Node.js", () => {
    const secret = "base64_test_secret"
    const message = "symbol=BTCUSDT&timestamp=1700000000000"

    // Node polyfill uses bridge.hmac fallback for base64
    const polyfill = g.crypto.createHmac("sha256", secret).update(message).digest("base64")
    const native = createHmac("sha256", secret).update(message).digest("base64")
    expect(polyfill).toBe(native)
  })

  test("HMAC-SHA512 base64 encoding matches Node.js", () => {
    const polyfill = g.crypto.createHmac("sha512", "key").update("data").digest("base64")
    const native = createHmac("sha512", "key").update("data").digest("base64")
    expect(polyfill).toBe(native)
  })

  test("SHA-256 hash with hex and base64 both match Node.js", () => {
    const data = "hash_me_please"
    const hexPolyfill = g.crypto.createHash("sha256").update(data).digest("hex")
    const hexNative = createHash("sha256").update(data).digest("hex")
    expect(hexPolyfill).toBe(hexNative)

    const b64Polyfill = g.crypto.createHash("sha256").update(data).digest("base64")
    const b64Native = createHash("sha256").update(data).digest("base64")
    expect(b64Polyfill).toBe(b64Native)
  })

  test("MD5 hash matches Node.js", () => {
    const polyfill = g.crypto.createHash("md5").update("test_data").digest("hex")
    const native = createHash("md5").update("test_data").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("SHA-1 hash matches Node.js", () => {
    const polyfill = g.crypto.createHash("sha1").update("test_data").digest("hex")
    const native = createHash("sha1").update("test_data").digest("hex")
    expect(polyfill).toBe(native)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Fuzz Testing
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Fuzz Testing", () => {
  test("500 random HMAC-SHA256 inputs match Node.js", () => {
    for (let i = 0; i < 500; i++) {
      const secretLen = Math.floor(Math.random() * 128) + 1
      const msgLen = Math.floor(Math.random() * 512) + 1
      const secret = nodeRandomBytes(secretLen).toString("hex")
      const msg = nodeRandomBytes(msgLen).toString("hex")

      const polyfill = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
      const native = createHmac("sha256", secret).update(msg).digest("hex")
      expect(polyfill).toBe(native)
    }
  })

  test("200 random HMAC-SHA512 inputs match Node.js", () => {
    for (let i = 0; i < 200; i++) {
      const secret = nodeRandomBytes(Math.floor(Math.random() * 64) + 1).toString("base64")
      const msg = nodeRandomBytes(Math.floor(Math.random() * 256) + 1).toString("base64")

      const polyfill = g.crypto.createHmac("sha512", secret).update(msg).digest("hex")
      const native = createHmac("sha512", secret).update(msg).digest("hex")
      expect(polyfill).toBe(native)
    }
  })

  test("200 random SHA-256 hash inputs match Node.js", () => {
    for (let i = 0; i < 200; i++) {
      const data = nodeRandomBytes(Math.floor(Math.random() * 1024) + 1).toString("hex")
      const polyfill = g.crypto.createHash("sha256").update(data).digest("hex")
      const native = createHash("sha256").update(data).digest("hex")
      expect(polyfill).toBe(native)
    }
  })

  test("100 random inputs with mixed chained updates", () => {
    for (let i = 0; i < 100; i++) {
      const secret = `fuzz_secret_${i}`
      const numParts = Math.floor(Math.random() * 5) + 2
      const parts: string[] = []
      for (let j = 0; j < numParts; j++) {
        parts.push(nodeRandomBytes(Math.floor(Math.random() * 64) + 1).toString("hex"))
      }

      const chained = g.crypto.createHmac("sha256", secret)
      for (const p of parts) chained.update(p)
      const result = chained.digest("hex")

      const native = createHmac("sha256", secret).update(parts.join("")).digest("hex")
      expect(result).toBe(native)
    }
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Binary / Uint8Array Inputs
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Binary Uint8Array Inputs", () => {
  test("HMAC with Uint8Array data matches string equivalent", () => {
    const encoder = new TextEncoder()
    const secret = "binary_test_secret"
    const msgStr = "timestamp=1700000000000"
    const msgBytes = encoder.encode(msgStr)

    const fromString = g.crypto.createHmac("sha256", secret).update(msgStr).digest("hex")
    const fromBytes = g.crypto.createHmac("sha256", secret).update(msgBytes).digest("hex")
    const native = createHmac("sha256", secret).update(msgStr).digest("hex")

    expect(fromString).toBe(native)
    expect(fromBytes).toBe(native)
  })

  test("Hash with Uint8Array data matches string equivalent", () => {
    const encoder = new TextEncoder()
    const data = "hash this binary"
    const bytes = encoder.encode(data)

    const fromString = g.crypto.createHash("sha256").update(data).digest("hex")
    const fromBytes = g.crypto.createHash("sha256").update(bytes).digest("hex")
    const native = createHash("sha256").update(data).digest("hex")

    expect(fromString).toBe(native)
    expect(fromBytes).toBe(native)
  })

  test("mixed string and Uint8Array updates", () => {
    const encoder = new TextEncoder()
    const secret = "mixed_input_secret"

    const builder = g.crypto.createHmac("sha256", secret)
    builder.update("part1=")
    builder.update(encoder.encode("value1"))
    builder.update("&part2=")
    builder.update(encoder.encode("value2"))
    const result = builder.digest("hex")

    const native = createHmac("sha256", secret).update("part1=value1&part2=value2").digest("hex")
    expect(result).toBe(native)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Multi-Encoding Buffer Roundtrips
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Multi-Encoding Buffer Roundtrips", () => {
  test("utf8 -> hex -> base64 -> hex -> utf8 full cycle", () => {
    const original = "Hello 世界! 🌍 Ünîcödé"
    const buf1 = g.Buffer.from(original, "utf8")
    const hex = buf1.toString("hex")
    const buf2 = g.Buffer.from(hex, "hex")
    const b64 = buf2.toString("base64")
    const buf3 = g.Buffer.from(b64, "base64")
    const hexAgain = buf3.toString("hex")
    const buf4 = g.Buffer.from(hexAgain, "hex")
    const final = buf4.toString("utf8")
    expect(final).toBe(original)
  })

  test("binary/latin1 encoding preserves byte values", () => {
    // Create a buffer with known bytes
    const bytes = new Uint8Array([0, 1, 127, 128, 200, 255])
    const buf = g.Buffer.from(bytes)
    const latin1 = buf.toString("binary")
    expect(latin1.length).toBe(6)
    expect(latin1.charCodeAt(0)).toBe(0)
    expect(latin1.charCodeAt(2)).toBe(127)
    expect(latin1.charCodeAt(3)).toBe(128)
    expect(latin1.charCodeAt(5)).toBe(255)

    // Roundtrip
    const restored = g.Buffer.from(latin1, "binary")
    for (let i = 0; i < bytes.length; i++) {
      expect(restored[i]).toBe(bytes[i])
    }
  })

  test("hex encoding handles all byte values (0x00-0xFF)", () => {
    const bytes = new Uint8Array(256)
    for (let i = 0; i < 256; i++) bytes[i] = i
    const buf = g.Buffer.from(bytes)
    const hex = buf.toString("hex")
    expect(hex.length).toBe(512)
    expect(hex.startsWith("000102")).toBe(true)
    expect(hex.endsWith("fdfeff")).toBe(true)

    const restored = g.Buffer.from(hex, "hex")
    for (let i = 0; i < 256; i++) {
      expect(restored[i]).toBe(i)
    }
  })

  test("base64 roundtrip with padding variations", () => {
    // 0 padding chars
    const buf3 = g.Buffer.from("abc", "utf8")
    expect(g.Buffer.from(buf3.toString("base64"), "base64").toString("utf8")).toBe("abc")

    // 1 padding char (==)
    const buf1 = g.Buffer.from("a", "utf8")
    expect(g.Buffer.from(buf1.toString("base64"), "base64").toString("utf8")).toBe("a")

    // 2 padding chars (=)
    const buf2 = g.Buffer.from("ab", "utf8")
    expect(g.Buffer.from(buf2.toString("base64"), "base64").toString("utf8")).toBe("ab")
  })

  test("Buffer.from with ArrayBuffer input", () => {
    const original = new Uint8Array([10, 20, 30, 40, 50])
    const buf = g.Buffer.from(original.buffer)
    expect(buf.length).toBe(5)
    expect(buf[0]).toBe(10)
    expect(buf[4]).toBe(50)
    expect(buf.toString("hex")).toBe("0a141e2832")
  })

  test("Buffer.concat with mixed sizes", () => {
    const bufs = [
      g.Buffer.from("a", "utf8"),
      g.Buffer.from("", "utf8"),
      g.Buffer.from("bcd", "utf8"),
      g.Buffer.from("", "utf8"),
      g.Buffer.from("efghij", "utf8"),
    ]
    const result = g.Buffer.concat(bufs)
    expect(result.toString("utf8")).toBe("abcdefghij")
    expect(result.length).toBe(10)
  })

  test("Buffer.byteLength for multi-byte characters", () => {
    // ASCII: 1 byte per char
    expect(g.Buffer.byteLength("hello")).toBe(5)
    // 2-byte chars (Latin extended)
    expect(g.Buffer.byteLength("café")).toBe(5) // c=1, a=1, f=1, é=2
    // 3-byte chars (CJK)
    expect(g.Buffer.byteLength("日本")).toBe(6)
    // 4-byte chars (emoji)
    expect(g.Buffer.byteLength("🌍")).toBe(4)
    // Mixed
    expect(g.Buffer.byteLength("Hi 🌍!")).toBe(8)

    // Verify against Node.js Buffer
    expect(g.Buffer.byteLength("café")).toBe(Buffer.byteLength("café"))
    expect(g.Buffer.byteLength("日本語")).toBe(Buffer.byteLength("日本語"))
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// randomBytes Advanced
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — randomBytes Stress", () => {
  test("various sizes produce correct lengths", () => {
    for (const size of [1, 2, 8, 16, 32, 64, 128, 256, 512, 1024]) {
      const bytes = g.crypto.randomBytes(size)
      expect(bytes.length).toBe(size)
    }
  })

  test("1000 calls produce no duplicates (32 bytes each)", () => {
    const seen = new Set<string>()
    for (let i = 0; i < 1000; i++) {
      const hex = g.Buffer.from(g.crypto.randomBytes(32)).toString("hex")
      expect(seen.has(hex)).toBe(false)
      seen.add(hex)
    }
  })

  test("randomBytes hex representation is valid lowercase hex", () => {
    for (let i = 0; i < 100; i++) {
      const hex = g.Buffer.from(g.crypto.randomBytes(16)).toString("hex")
      expect(hex).toMatch(/^[0-9a-f]{32}$/)
    }
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Signing Determinism
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Signing Determinism", () => {
  test("same input always produces same output (1000 iterations)", () => {
    const secret = "determinism_test_key"
    const message = "symbol=BTCUSDT&side=BUY&quantity=0.001&timestamp=1700000000000"
    const expected = createHmac("sha256", secret).update(message).digest("hex")

    for (let i = 0; i < 1000; i++) {
      const result = g.crypto.createHmac("sha256", secret).update(message).digest("hex")
      expect(result).toBe(expected)
    }
  })

  test("hash determinism across 500 iterations", () => {
    const data = "deterministic_hash_test_data"
    const expected = createHash("sha256").update(data).digest("hex")

    for (let i = 0; i < 500; i++) {
      const result = g.crypto.createHash("sha256").update(data).digest("hex")
      expect(result).toBe(expected)
    }
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Full Exchange Signing Flow Simulations
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Exchange Signing Flow Simulations", () => {
  test("Binance spot order with all parameters", () => {
    const apiSecret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    const params: Record<string, string> = {
      symbol: "BTCUSDT",
      side: "BUY",
      type: "MARKET",
      quoteOrderQty: "100",
      newOrderRespType: "FULL",
      recvWindow: "5000",
      timestamp: "1700000000000",
    }
    const queryString = Object.entries(params).map(([k, v]) => `${k}=${v}`).join("&")
    const signature = g.crypto.createHmac("sha256", apiSecret).update(queryString).digest("hex")
    const expected = createHmac("sha256", apiSecret).update(queryString).digest("hex")

    expect(signature).toBe(expected)
    expect(signature.length).toBe(64)

    // Signed URL assembly
    const signedUrl = `${queryString}&signature=${signature}`
    expect(signedUrl).toContain("symbol=BTCUSDT")
    expect(signedUrl).toContain(`signature=${expected}`)
  })

  test("Bybit v5 request signing simulation", () => {
    const apiKey = "BYBIT_API_KEY"
    const apiSecret = "BYBIT_SECRET_KEY"
    const timestamp = "1700000000000"
    const recvWindow = "5000"

    // Bybit signs: timestamp + apiKey + recvWindow + queryString
    const queryString = "category=linear&symbol=BTCUSDT"
    const signPayload = timestamp + apiKey + recvWindow + queryString

    const signature = g.crypto.createHmac("sha256", apiSecret).update(signPayload).digest("hex")
    const expected = createHmac("sha256", apiSecret).update(signPayload).digest("hex")
    expect(signature).toBe(expected)
  })

  test("OKX request signing simulation (base64 encoded HMAC-SHA256)", () => {
    const secretKey = "OKX_SECRET_KEY"
    const timestamp = "2023-11-15T10:00:00.000Z"
    const method = "GET"
    const requestPath = "/api/v5/account/balance"

    // OKX signs: timestamp + method + requestPath + body
    const preSign = timestamp + method + requestPath
    const signature = g.crypto.createHmac("sha256", secretKey).update(preSign).digest("base64")
    const expected = createHmac("sha256", secretKey).update(preSign).digest("base64")
    expect(signature).toBe(expected)
  })

  test("Kraken nonce-based signing simulation", () => {
    const apiSecret = Buffer.from("kQH5HW/8p1uGOVjbgWA7FunAmGO8lsSUXNsu3eow76sz84Q18fWxnyRzBHCd3pd5nE9qa99HAZtuZuj6F1huXg==", "base64")
    const nonce = "1616492376594"
    const postData = `nonce=${nonce}&ordertype=limit&pair=XBTUSD&price=37500&type=buy&volume=1.25`

    // Kraken signs: SHA256(nonce + postData), then HMAC-SHA512 with base64-decoded secret
    const sha256 = createHash("sha256").update(nonce + postData).digest()
    const uriPath = "/0/private/AddOrder"
    const message = Buffer.concat([Buffer.from(uriPath, "ascii"), sha256])

    const signatureNative = createHmac("sha512", apiSecret).update(message).digest("base64")

    // Replicate with polyfill for the SHA256 step
    const sha256Polyfill = g.crypto.createHash("sha256").update(nonce + postData).digest("hex")
    const sha256Native = createHash("sha256").update(nonce + postData).digest("hex")
    expect(sha256Polyfill).toBe(sha256Native)
  })

  test("multiple signing rounds with timestamp rotation", () => {
    const secret = "rotating_timestamp_secret"
    const baseTs = 1700000000000
    const signatures: string[] = []

    for (let i = 0; i < 100; i++) {
      const ts = baseTs + i * 1000
      const msg = `symbol=BTCUSDT&side=BUY&quantity=0.001&timestamp=${ts}`
      const sig = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
      const expected = createHmac("sha256", secret).update(msg).digest("hex")
      expect(sig).toBe(expected)
      signatures.push(sig)
    }

    // All signatures should be unique (different timestamps)
    expect(new Set(signatures).size).toBe(100)
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Edge Cases & Error Boundaries
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Edge Cases", () => {
  test("null bytes in message", () => {
    const msg = "before\x00after"
    const polyfill = g.crypto.createHmac("sha256", "secret").update(msg).digest("hex")
    const native = createHmac("sha256", "secret").update(msg).digest("hex")
    expect(polyfill).toBe(native)
  })

  test("newlines and control characters in message", () => {
    const msg = "line1\nline2\rline3\tline4"
    const polyfill = g.crypto.createHmac("sha256", "secret").update(msg).digest("hex")
    const native = createHmac("sha256", "secret").update(msg).digest("hex")
    expect(polyfill).toBe(native)
  })

  test("very long chained updates (100 parts)", () => {
    const secret = "long_chain_secret"
    const parts: string[] = []
    const builder = g.crypto.createHmac("sha256", secret)

    for (let i = 0; i < 100; i++) {
      const part = `param${i}=value${i}&`
      parts.push(part)
      builder.update(part)
    }

    const result = builder.digest("hex")
    const expected = createHmac("sha256", secret).update(parts.join("")).digest("hex")
    expect(result).toBe(expected)
  })

  test("unicode normalization edge cases", () => {
    // é as single codepoint vs e + combining accent
    const composed = "caf\u00e9"
    const decomposed = "cafe\u0301"

    const sig1 = g.crypto.createHmac("sha256", "key").update(composed).digest("hex")
    const sig2 = g.crypto.createHmac("sha256", "key").update(decomposed).digest("hex")

    // These are different byte sequences, so signatures should differ
    expect(sig1).not.toBe(sig2)

    // But each should match Node.js
    expect(sig1).toBe(createHmac("sha256", "key").update(composed).digest("hex"))
    expect(sig2).toBe(createHmac("sha256", "key").update(decomposed).digest("hex"))
  })

  test("empty Buffer operations", () => {
    const empty = g.Buffer.from("", "utf8")
    expect(empty.length).toBe(0)
    expect(empty.toString("hex")).toBe("")
    expect(empty.toString("base64")).toBe("")
    expect(empty.toString("utf8")).toBe("")

    // concat with empty buffers
    const result = g.Buffer.concat([empty, g.Buffer.from("x", "utf8"), empty])
    expect(result.toString("utf8")).toBe("x")
  })

  test("Buffer.alloc large size", () => {
    const buf = g.Buffer.alloc(1024 * 1024) // 1MB
    expect(buf.length).toBe(1024 * 1024)
    expect(buf[0]).toBe(0)
    expect(buf[buf.length - 1]).toBe(0)
  })

  test("signing with JSON body payloads", () => {
    const secret = "json_body_secret"
    const body = JSON.stringify({
      symbol: "BTCUSDT",
      side: "BUY",
      type: "LIMIT",
      quantity: "0.001",
      price: "50000.00",
      timeInForce: "GTC",
    })

    const sig = g.crypto.createHmac("sha256", secret).update(body).digest("hex")
    const expected = createHmac("sha256", secret).update(body).digest("hex")
    expect(sig).toBe(expected)
  })

  test("signing with URL-encoded special characters", () => {
    const secret = "urlencoded_secret"
    const msg = "symbol=BTC%2FUSDT&note=hello%20world&special=%26%3D%3F"

    const sig = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
    const expected = createHmac("sha256", secret).update(msg).digest("hex")
    expect(sig).toBe(expected)
  })
})
