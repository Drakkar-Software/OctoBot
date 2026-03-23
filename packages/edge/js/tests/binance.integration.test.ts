/**
 * Binance API integration tests using real ccxt exchange with polyfills.
 *
 * Tests the full polyfill stack: crypto (HMAC, hash), Buffer, and
 * ccxt exchange operations against the live Binance public API.
 *
 * Run with: npm test -- tests/binance.integration.test.ts
 */
import { describe, test, expect, beforeAll } from "@jest/globals"
import { createHmac, createHash } from "crypto"

let ccxt: any
const g = globalThis as any

describe("CCXT Binance Integration", () => {
  beforeAll(async () => {
    // Load Node.js polyfills for testing
    await import("../src/polyfills/node")
    ccxt = (await import("ccxt")).default
  })

  // ── Polyfill availability ──────────────────────────────────────────────

  test("polyfills are loaded", () => {
    expect(typeof g.crypto).toBe("object")
    expect(typeof g.crypto.createHmac).toBe("function")
    expect(typeof g.crypto.createHash).toBe("function")
    expect(typeof g.Buffer).toBe("function")
  })

  test("Buffer encoding/decoding roundtrip", () => {
    const original = "Hello, CCXT!"

    const buf = g.Buffer.from(original, "utf8")
    expect(buf.toString("utf8")).toBe(original)

    const hex = buf.toString("hex")
    expect(g.Buffer.from(hex, "hex").toString("utf8")).toBe(original)

    const b64 = buf.toString("base64")
    expect(g.Buffer.from(b64, "base64").toString("utf8")).toBe(original)
  })

  // ── Crypto functions ───────────────────────────────────────────────────

  describe("Crypto Functions", () => {
    test("HMAC-SHA256 Binance signature vector", () => {
      const secret = "NhqPtmdSJYdKjVHjA7PZj4Mge3R5YNiP1e3UZjInClVN65XAbvqqM6A7H5fATj0j"
      const message =
        "symbol=LTCBTC&side=BUY&type=LIMIT&timeInForce=GTC&quantity=1&price=0.1&recvWindow=5000&timestamp=1499827319559"

      const result = g.crypto.createHmac("sha256", secret).update(message).digest("hex")
      expect(result).toBe("c8db56825ae71d6d79447849e617115f4a920fa2acdcab2b053c4b2838bd6b71")
    })

    test("SHA-256 hash", () => {
      const result = g.crypto.createHash("sha256").update("hello world").digest("hex")
      expect(result).toBe("b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9")
    })

    test("MD5 hash", () => {
      const result = g.crypto.createHash("md5").update("hello world").digest("hex")
      expect(result).toBe("5eb63bbbe01eeed093cb22bb8f5acdc3")
    })

    test("HMAC chained updates produce correct result", () => {
      const polyfill = g.crypto.createHmac("sha256", "secret")
        .update("part1")
        .update("part2")
        .digest("hex")

      const native = createHmac("sha256", "secret")
        .update("part1")
        .update("part2")
        .digest("hex")

      expect(polyfill).toBe(native)
    })

    test("hash chained updates produce correct result", () => {
      const polyfill = g.crypto.createHash("sha256")
        .update("a")
        .update("b")
        .update("c")
        .digest("hex")

      const native = createHash("sha256")
        .update("a")
        .update("b")
        .update("c")
        .digest("hex")

      expect(polyfill).toBe(native)
    })
  })

  // ── Binance Public API ─────────────────────────────────────────────────

  describe("Binance Public API", () => {
    let exchange: any

    beforeAll(() => {
      exchange = new ccxt.binance({
        enableRateLimit: true,
        timeout: 30000,
      })
    })

    test("fetch server time", async () => {
      const time = await exchange.fetchTime()

      expect(typeof time).toBe("number")
      expect(time).toBeGreaterThan(1577836800000) // After 2020-01-01
      expect(time).toBeLessThan(Date.now() + 60000) // Not too far in future
    }, 30000)

    test("fetch BTC/USDT ticker", async () => {
      const ticker = await exchange.fetchTicker("BTC/USDT")

      expect(ticker).toBeDefined()
      expect(ticker.symbol).toBe("BTC/USDT")
      expect(typeof ticker.last).toBe("number")
      expect(ticker.last).toBeGreaterThan(0)
      expect(typeof ticker.bid).toBe("number")
      expect(typeof ticker.ask).toBe("number")
      expect(ticker.ask).toBeGreaterThan(ticker.bid)
    }, 30000)

    test("fetch ETH/USDT ticker", async () => {
      const ticker = await exchange.fetchTicker("ETH/USDT")

      expect(ticker.symbol).toBe("ETH/USDT")
      expect(ticker.last).toBeGreaterThan(0)
    }, 30000)

    test("fetch order book", async () => {
      const orderBook = await exchange.fetchOrderBook("BTC/USDT", 10)

      expect(orderBook).toBeDefined()
      expect(Array.isArray(orderBook.bids)).toBe(true)
      expect(Array.isArray(orderBook.asks)).toBe(true)
      expect(orderBook.bids.length).toBeGreaterThan(0)
      expect(orderBook.asks.length).toBeGreaterThan(0)

      // Bids should be in descending order
      expect(orderBook.bids[0][0]).toBeGreaterThan(orderBook.bids[1][0])
      // Asks should be in ascending order
      expect(orderBook.asks[0][0]).toBeLessThan(orderBook.asks[1][0])
    }, 30000)

    test("fetch recent trades", async () => {
      const trades = await exchange.fetchTrades("BTC/USDT", undefined, 10)

      expect(Array.isArray(trades)).toBe(true)
      expect(trades.length).toBeGreaterThan(0)
      expect(trades.length).toBeLessThanOrEqual(10)

      const trade = trades[0]
      expect(trade.id).toBeDefined()
      expect(typeof trade.timestamp).toBe("number")
      expect(typeof trade.price).toBe("number")
      expect(typeof trade.amount).toBe("number")
      expect(["buy", "sell"]).toContain(trade.side)
    }, 30000)

    test("fetch OHLCV (candlestick data)", async () => {
      const ohlcv = await exchange.fetchOHLCV("BTC/USDT", "1h", undefined, 5)

      expect(Array.isArray(ohlcv)).toBe(true)
      expect(ohlcv.length).toBeGreaterThan(0)
      expect(ohlcv.length).toBeLessThanOrEqual(5)

      const candle = ohlcv[0]
      expect(candle.length).toBe(6) // [timestamp, open, high, low, close, volume]
      for (let i = 0; i < 6; i++) {
        expect(typeof candle[i]).toBe("number")
      }
    }, 30000)

    test("fetch markets", async () => {
      const markets = await exchange.fetchMarkets()

      expect(Array.isArray(markets)).toBe(true)
      expect(markets.length).toBeGreaterThan(100)

      const btcUsdt = markets.find((m: any) => m.symbol === "BTC/USDT")
      expect(btcUsdt).toBeDefined()
      expect(btcUsdt.base).toBe("BTC")
      expect(btcUsdt.quote).toBe("USDT")
      expect(btcUsdt.active).toBe(true)
    }, 30000)
  })

  // ── Multiple Exchanges ─────────────────────────────────────────────────

  describe("Multiple Exchanges", () => {
    test("fetch prices from multiple exchanges", async () => {
      const exchanges = [
        { name: "Binance", instance: new ccxt.binance() },
        { name: "Binance US", instance: new ccxt.binanceus() },
      ]

      const results: { exchange: string; success: boolean }[] = []

      for (const { name, instance } of exchanges) {
        try {
          const ticker = await instance.fetchTicker("BTC/USDT")
          results.push({ exchange: name, success: true })
        } catch {
          results.push({ exchange: name, success: false })
        }
      }

      // At least one should succeed
      expect(results.some((r) => r.success)).toBe(true)
    }, 60000)
  })
})
