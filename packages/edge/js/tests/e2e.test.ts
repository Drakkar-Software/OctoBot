/**
 * End-to-end tests — verify the full polyfill stack works with real ccxt.
 *
 * Simple tests: basic crypto, buffer, polyfill availability.
 * Advanced tests: multi-exchange signing, chained updates, cross-algorithm
 * consistency, binary secrets, concurrent usage, full signing flow.
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
// Simple E2E Tests
// ═══════════════════════════════════════════════════════════════════════════

describe("Simple E2E", () => {
  test("polyfills are installed", () => {
    expect(typeof g.crypto.createHmac).toBe("function")
    expect(typeof g.crypto.createHash).toBe("function")
    expect(typeof g.crypto.randomBytes).toBe("function")
    expect(typeof g.Buffer).toBe("function")
  })

  test("HMAC-SHA256 matches Node.js crypto", () => {
    const polyfill = g.crypto.createHmac("sha256", "secret").update("hello").digest("hex")
    const native = createHmac("sha256", "secret").update("hello").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("HMAC-SHA512 matches Node.js crypto", () => {
    const polyfill = g.crypto.createHmac("sha512", "key").update("data").digest("hex")
    const native = createHmac("sha512", "key").update("data").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("SHA-256 hash matches Node.js crypto", () => {
    const polyfill = g.crypto.createHash("sha256").update("test").digest("hex")
    const native = createHash("sha256").update("test").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("Buffer roundtrip: string -> hex -> base64 -> string", () => {
    const original = "Hello, OctoBot Edge!"
    const buf = g.Buffer.from(original, "utf8")
    const hex = buf.toString("hex")
    const fromHex = g.Buffer.from(hex, "hex")
    const b64 = fromHex.toString("base64")
    const fromB64 = g.Buffer.from(b64, "base64")
    expect(fromB64.toString("utf8")).toBe(original)
  })

  test("randomBytes returns unique values", () => {
    const a = g.crypto.randomBytes(32)
    const b = g.crypto.randomBytes(32)
    expect(a.length).toBe(32)
    expect(b.length).toBe(32)
    // Overwhelmingly likely to be different
    expect(g.Buffer.from(a).toString("hex")).not.toBe(g.Buffer.from(b).toString("hex"))
  })

  test("Binance HMAC test vector", () => {
    const secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    const message =
      "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"
    const result = g.crypto.createHmac("sha256", secret).update(message).digest("hex")
    expect(result).toBe("c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71")
  })
})

// ═══════════════════════════════════════════════════════════════════════════
// Advanced E2E Tests
// ═══════════════════════════════════════════════════════════════════════════

describe("Advanced E2E — Chained Updates", () => {
  test("HMAC with multiple updates matches single update", () => {
    const secret = "multi_update_secret"
    const parts = ["part1=value1", "&part2=value2", "&part3=value3"]

    const chained = g.crypto.createHmac("sha256", secret)
    for (const p of parts) chained.update(p)
    const chainedResult = chained.digest("hex")

    const single = g.crypto.createHmac("sha256", secret)
      .update(parts.join(""))
      .digest("hex")

    const native = createHmac("sha256", secret)
      .update(parts.join(""))
      .digest("hex")

    expect(chainedResult).toBe(single)
    expect(chainedResult).toBe(native)
  })

  test("Hash with incremental updates matches full input", () => {
    const data = "The quick brown fox jumps over the lazy dog"
    const words = data.split(" ")

    const incremental = g.crypto.createHash("sha256")
    words.forEach((w: string, i: number) => {
      incremental.update(i > 0 ? " " + w : w)
    })
    const result = incremental.digest("hex")

    const native = createHash("sha256").update(data).digest("hex")
    expect(result).toBe(native)
  })
})

describe("Advanced E2E — Cross-Algorithm Consistency", () => {
  test("SHA-256 and SHA-512 produce different-length results", () => {
    const sha256 = g.crypto.createHmac("sha256", "s").update("d").digest("hex")
    const sha512 = g.crypto.createHmac("sha512", "s").update("d").digest("hex")
    expect(sha256.length).toBe(64)
    expect(sha512.length).toBe(128)
    expect(sha256).not.toBe(sha512.substring(0, 64))
  })

  test("different secrets produce different signatures", () => {
    const msg = "same_message"
    const sigs = new Set<string>()
    for (let i = 0; i < 50; i++) {
      const sig = g.crypto.createHmac("sha256", `secret_${i}`).update(msg).digest("hex")
      sigs.add(sig)
    }
    expect(sigs.size).toBe(50)
  })

  test("different messages produce different signatures", () => {
    const secret = "same_secret"
    const sigs = new Set<string>()
    for (let i = 0; i < 50; i++) {
      const sig = g.crypto.createHmac("sha256", secret).update(`msg_${i}`).digest("hex")
      sigs.add(sig)
    }
    expect(sigs.size).toBe(50)
  })
})

describe("Advanced E2E — Binary and Edge-Case Secrets", () => {
  test("empty message and secret", () => {
    const polyfill = g.crypto.createHmac("sha256", "").update("").digest("hex")
    const native = createHmac("sha256", "").update("").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("very long secret (4KB)", () => {
    const longSecret = "k".repeat(4096)
    const polyfill = g.crypto.createHmac("sha256", longSecret).update("data").digest("hex")
    const native = createHmac("sha256", longSecret).update("data").digest("hex")
    expect(polyfill).toBe(native)
  })

  test("very long message (1MB)", () => {
    const longMsg = "x".repeat(1024 * 1024)
    const polyfill = g.crypto.createHmac("sha256", "secret").update(longMsg).digest("hex")
    const native = createHmac("sha256", "secret").update(longMsg).digest("hex")
    expect(polyfill).toBe(native)
  })

  test("special characters in secret and message", () => {
    const secret = "key+with/special=chars&%20"
    const message = "data=hello world&price=1000€"
    const polyfill = g.crypto.createHmac("sha256", secret).update(message).digest("hex")
    const native = createHmac("sha256", secret).update(message).digest("hex")
    expect(polyfill).toBe(native)
  })
})

describe("Advanced E2E — CCXT Exchange Integration", () => {
  test("ccxt exchange instances are created with polyfilled crypto", () => {
    const exchange = new ccxt.binance({
      apiKey: "test_key",
      secret: "test_secret",
    })
    expect(exchange).toBeDefined()
    expect(typeof exchange.sign).toBe("function")
    expect(typeof exchange.fetchTicker).toBe("function")
  })

  test("polyfilled crypto.createHmac matches ccxt signing expectations", () => {
    // ccxt 4.x uses noble-hashes internally for exchange.hmac(),
    // but polyfills patch crypto.createHmac which older ccxt or
    // custom signing code uses. Verify both produce the same result.
    const secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
    const message =
      "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"

    const polyfillResult = g.crypto.createHmac("sha256", secret).update(message).digest("hex")
    const nativeResult = createHmac("sha256", secret).update(message).digest("hex")

    expect(polyfillResult).toBe(nativeResult)
    expect(polyfillResult).toBe("c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71")
  })

  test("multiple exchange instances can coexist", () => {
    const exchangeIds = ["binance", "bybit", "okx", "kucoin"]
    const exchanges = exchangeIds.map(
      (id) => new ccxt[id]({ apiKey: "k", secret: "s" }),
    )

    for (const ex of exchanges) {
      expect(ex).toBeDefined()
      expect(typeof ex.sign).toBe("function")
    }

    // Signing via polyfill should be consistent
    const msg = "test_payload"
    const secret = "test_secret"
    const expected = createHmac("sha256", secret).update(msg).digest("hex")
    const polyfillResult = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
    expect(polyfillResult).toBe(expected)
  })

  test("Binance official signature via polyfilled crypto", () => {
    const apiSecret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"

    const params: Record<string, string> = {
      symbol: "LTCBTC",
      side: "BUY",
      type: "LIMIT",
      timeInForce: "GTC",
      quantity: "1",
      price: "0.1",
      recvWindow: "5000",
      timestamp: "1499827319559",
    }
    const queryString = Object.entries(params).map(([k, v]) => `${k}=${v}`).join("&")
    const signature = g.crypto.createHmac("sha256", apiSecret).update(queryString).digest("hex")

    expect(signature).toBe("c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71")
  })

  test("rapid successive signatures via polyfill are correct and unique", () => {
    const secret = "rapid_test_secret"
    let prev = ""
    for (let i = 0; i < 500; i++) {
      const msg = `nonce=${i}`
      const sig = g.crypto.createHmac("sha256", secret).update(msg).digest("hex")
      const expected = createHmac("sha256", secret).update(msg).digest("hex")
      expect(sig).toBe(expected)
      expect(sig).not.toBe(prev)
      prev = sig
    }
  })
})

describe("Advanced E2E — Buffer Integration", () => {
  test("Buffer.concat produces correct result", () => {
    const a = g.Buffer.from("hello", "utf8")
    const b = g.Buffer.from(" ", "utf8")
    const c = g.Buffer.from("world", "utf8")
    const result = g.Buffer.concat([a, b, c])
    expect(result.toString("utf8")).toBe("hello world")
  })

  test("Buffer.alloc creates zeroed buffer", () => {
    const buf = g.Buffer.alloc(16)
    expect(buf.length).toBe(16)
    for (let i = 0; i < 16; i++) {
      expect(buf[i]).toBe(0)
    }
  })

  test("Buffer.isBuffer identifies buffers", () => {
    const buf = g.Buffer.from("test", "utf8")
    expect(g.Buffer.isBuffer(buf)).toBe(true)
    expect(g.Buffer.isBuffer(new Uint8Array(4))).toBe(false)
    expect(g.Buffer.isBuffer("string")).toBe(false)
  })

  test("Buffer.byteLength matches Node.js", () => {
    const str = "Hello, World! 日本語"
    const polyfillLen = g.Buffer.byteLength(str)
    const nodeLen = Buffer.byteLength(str)
    expect(polyfillLen).toBe(nodeLen)
  })
})

describe("Advanced E2E — URLSearchParams", () => {
  test("basic query string parsing", () => {
    const params = new g.URLSearchParams("foo=bar&baz=qux")
    expect(params.get("foo")).toBe("bar")
    expect(params.get("baz")).toBe("qux")
  })

  test("empty value handling", () => {
    const params = new g.URLSearchParams("key=&other=value")
    expect(params.get("key")).toBe("")
    expect(params.get("other")).toBe("value")
  })

  test("key with equals sign in value", () => {
    const params = new g.URLSearchParams("data=a=b=c&other=d")
    expect(params.get("data")).toBe("a=b=c")
    expect(params.get("other")).toBe("d")
  })

  test("toString roundtrip", () => {
    const original = "a=1&b=2&c=3"
    const params = new g.URLSearchParams(original)
    expect(params.toString()).toBe(original)
  })
})
