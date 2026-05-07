import { beforeEach, describe, expect, it, vi } from "vitest"
import { CCXTAdapter } from "../../../src/adapters/ccxt-adapter.js"
import { NotSupported } from "../../../src/errors/index.js"
import { CCXTConnector } from "../../../src/exchanges/connectors/ccxt/ccxt-connector.js"
import type { ExchangeConfig } from "../../../src/types/index.js"

// ---------------------------------------------------------------------------
// Minimal ccxt exchange mock
// ---------------------------------------------------------------------------

function makeMockCcxtExchange(overrides: Record<string, unknown> = {}) {
  return {
    markets: {
      "BTC/USDT": {
        symbol: "BTC/USDT",
        base: "BTC",
        quote: "USDT",
        active: true,
        type: "spot",
        precision: { price: 2, amount: 6 },
        limits: {
          amount: { min: 0.00001, max: 9000 },
          price: { min: 0.01, max: 1000000 },
          cost: { min: 5, max: null },
        },
        taker: 0.001,
        maker: 0.001,
        info: {},
      },
    },
    timeframes: { "1h": 3600, "1d": 86400 },
    has: {
      fetchOrder: true,
      fetchClosedOrders: true,
      fetchCanceledOrders: true,
      fetchPositions: false,
      fetchLeverageTiers: false,
      fetchTransactions: false,
      editOrder: false,
    },
    loadMarkets: vi.fn().mockResolvedValue({}),
    market: vi.fn((symbol: string) => {
      const m = {
        "BTC/USDT": {
          symbol: "BTC/USDT",
          base: "BTC",
          quote: "USDT",
          active: true,
          type: "spot",
          precision: { price: 2, amount: 6 },
          limits: {
            amount: { min: 0.00001, max: 9000 },
            price: { min: 0.01, max: 1000000 },
            cost: { min: 5, max: null },
          },
          taker: 0.001,
          maker: 0.001,
          info: {},
        },
      } as Record<string, unknown>
      return m[symbol]
    }),
    fetchOHLCV: vi.fn().mockResolvedValue([
      [1_700_000_000_000, 30000, 31000, 29000, 30500, 100.5],
      [1_700_003_600_000, 30500, 32000, 30000, 31000, 200.0],
    ]),
    fetchTicker: vi.fn().mockResolvedValue({
      symbol: "BTC/USDT",
      timestamp: 1_700_000_000_000,
      datetime: "2023-11-14T00:00:00.000Z",
      high: 31000,
      low: 29000,
      bid: 30400,
      bidVolume: 10,
      ask: 30500,
      askVolume: 8,
      vwap: 30200,
      open: 29500,
      close: 30500,
      last: 30500,
      previousClose: 29500,
      change: 1000,
      percentage: 3.38,
      average: 30000,
      baseVolume: 500,
      quoteVolume: 15000000,
      info: {},
    }),
    fetchTickers: vi.fn().mockResolvedValue({
      "BTC/USDT": {
        symbol: "BTC/USDT",
        timestamp: 1_700_000_000_000,
        close: 30500,
        last: 30500,
        high: 31000,
        low: 29000,
        bid: 30400,
        ask: 30500,
        baseVolume: 500,
        info: {},
      },
    }),
    fetchOrderBook: vi.fn().mockResolvedValue({
      symbol: "BTC/USDT",
      timestamp: 1_700_000_000_000,
      datetime: "2023-11-14T00:00:00.000Z",
      bids: [[30400, 2.5], [30300, 5.0]],
      asks: [[30500, 1.5], [30600, 3.0]],
    }),
    fetchBalance: vi.fn().mockResolvedValue({
      free: { BTC: 1.5, USDT: 10000 },
      used: { BTC: 0.5, USDT: 0 },
      total: { BTC: 2.0, USDT: 10000 },
      info: {},
      timestamp: 1_700_000_000_000,
      datetime: "2023-11-14T00:00:00.000Z",
      BTC: { free: 1.5, used: 0.5, total: 2.0 },
      USDT: { free: 10000, used: 0, total: 10000 },
    }),
    fetchOrder: vi.fn().mockResolvedValue({
      id: "order-123",
      timestamp: 1_700_000_000_000,
      symbol: "BTC/USDT",
      type: "limit",
      side: "buy",
      price: 30000,
      amount: 0.001,
      filled: 0,
      remaining: 0.001,
      cost: null,
      average: null,
      status: "open",
      fee: null,
      reduceOnly: false,
      stopPrice: null,
      stopLossPrice: null,
      takeProfitPrice: null,
      info: {},
    }),
    fetchOpenOrders: vi.fn().mockResolvedValue([]),
    fetchClosedOrders: vi.fn().mockResolvedValue([]),
    fetchCanceledOrders: vi.fn().mockResolvedValue([]),
    fetchMyTrades: vi.fn().mockResolvedValue([]),
    fetchTrades: vi.fn().mockResolvedValue([]),
    createOrder: vi.fn().mockResolvedValue({
      id: "new-order-456",
      timestamp: 1_700_000_000_000,
      symbol: "BTC/USDT",
      type: "limit",
      side: "buy",
      price: 29000,
      amount: 0.001,
      filled: 0,
      remaining: 0.001,
      cost: null,
      average: null,
      status: "open",
      fee: null,
      reduceOnly: false,
      stopPrice: null,
      stopLossPrice: null,
      takeProfitPrice: null,
      info: {},
    }),
    cancelOrder: vi.fn().mockResolvedValue({ id: "order-123", status: "canceled" }),
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Test helper: build a connector with a mocked ccxt client
// ---------------------------------------------------------------------------

function makeConnector(
  ccxtOverrides: Record<string, unknown> = {},
  configOverrides: Partial<ExchangeConfig> = {},
): CCXTConnector {
  const config: ExchangeConfig = {
    exchangeName: "binance",
    credentials: undefined,
    ...configOverrides,
  }
  const connector = new CCXTConnector(config)
  // replace internal client with mock
  ;(connector as unknown as Record<string, unknown>)["client"] = makeMockCcxtExchange(ccxtOverrides)
  return connector
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("CCXTConnector – initialize", () => {
  it("loads markets and populates symbols/timeFrames", async () => {
    const connector = makeConnector()
    await connector.initialize()
    expect(connector.symbols.has("BTC/USDT")).toBe(true)
    expect(connector.timeFrames.has("1h")).toBe(true)
  })
})

describe("CCXTConnector – getMarketStatus", () => {
  it("returns adapted market status without fixer", () => {
    const connector = makeConnector()
    const ms = connector.getMarketStatus("BTC/USDT", undefined, false)
    expect(ms.symbol).toBe("BTC/USDT")
    expect(ms.base).toBe("BTC")
    expect(ms.limits.amount.min).toBe(0.00001)
  })

  it("applies fixer when withFixer=true", () => {
    const connector = makeConnector()
    const ms = connector.getMarketStatus("BTC/USDT", 30000, true)
    expect(ms.symbol).toBe("BTC/USDT")
    expect(ms.limits.amount.min).toBeDefined()
  })

  it("removes price limits when REMOVE_MARKET_STATUS_PRICE_LIMITS flag is set", () => {
    const connector = makeConnector()
    connector.exchange = {
      DUMP_INCOMPLETE_LAST_CANDLE: false,
      FIX_MARKET_STATUS: true,
      REMOVE_MARKET_STATUS_PRICE_LIMITS: true,
      isFuture: false,
      getContractSize: () => 1,
    }
    const ms = connector.getMarketStatus("BTC/USDT", 30000, true)
    expect(ms.limits.price.min).toBeNull()
    expect(ms.limits.price.max).toBeNull()
  })
})

describe("CCXTConnector – getSymbolPrices", () => {
  it("returns adapted OHLCV array with timestamps in seconds", async () => {
    const connector = makeConnector()
    const ohlcv = await connector.getSymbolPrices("BTC/USDT", "1h", 2)
    expect(ohlcv).toHaveLength(2)
    expect(ohlcv[0][0]).toBeLessThan(2_000_000_000) // seconds
    expect(ohlcv[0][1]).toBe(30000) // open
  })
})

describe("CCXTConnector – getPriceTicker", () => {
  it("returns adapted ticker with timestamp in seconds", async () => {
    const connector = makeConnector()
    const ticker = await connector.getPriceTicker("BTC/USDT")
    expect(ticker.close).toBe(30500)
    expect(ticker.timestamp).toBeCloseTo(1_700_000_000, 0)
  })
})

describe("CCXTConnector – getAllCurrenciesPriceTicker", () => {
  it("returns map keyed by symbol", async () => {
    const connector = makeConnector()
    const tickers = await connector.getAllCurrenciesPriceTicker()
    expect(tickers["BTC/USDT"]).toBeDefined()
    expect(tickers["BTC/USDT"].close).toBe(30500)
  })
})

describe("CCXTConnector – getOrderBook", () => {
  it("returns adapted order book with bids and asks", async () => {
    const connector = makeConnector()
    const book = await connector.getOrderBook("BTC/USDT", 5)
    expect(book.bids.length).toBeGreaterThan(0)
    expect(book.asks.length).toBeGreaterThan(0)
    expect(book.bids[0][0]).toBe(30400)
  })
})

describe("CCXTConnector – getBalance", () => {
  it("returns per-currency balance without aggregate keys", async () => {
    const connector = makeConnector()
    const balance = await connector.getBalance()
    expect(balance["BTC"]).toEqual({ free: 1.5, used: 0.5, total: 2.0 })
    expect(balance["free"]).toBeUndefined()
  })
})

describe("CCXTConnector – getOrder", () => {
  it("returns adapted order with exchange_id", async () => {
    const connector = makeConnector()
    const order = await connector.getOrder("order-123", "BTC/USDT")
    expect(order).not.toBeNull()
    expect(order!.exchange_id).toBe("order-123")
  })

  it("returns null on fetch failure", async () => {
    const connector = makeConnector({
      fetchOrder: vi.fn().mockRejectedValue(new Error("not found")),
    })
    const order = await connector.getOrder("nonexistent", "BTC/USDT")
    expect(order).toBeNull()
  })
})

describe("CCXTConnector – createOrder", () => {
  it("creates an order and returns adapted result", async () => {
    const connector = makeConnector()
    const order = await connector.createOrder(
      "buy_limit",
      "BTC/USDT",
      0.001,
      29000,
      undefined,
      "buy",
    )
    expect(order).not.toBeNull()
    expect(order!.exchange_id).toBe("new-order-456")
  })
})

describe("CCXTConnector – cancelOrder", () => {
  it("calls cancelOrder and returns 'canceled'", async () => {
    const connector = makeConnector()
    const result = await connector.cancelOrder("order-123", "BTC/USDT", "limit")
    expect(result).toBe("canceled")
  })
})

describe("CCXTConnector – getCancelledOrders", () => {
  it("throws NotSupported when fetchCanceledOrders is unsupported", async () => {
    const connector = makeConnector({
      has: { fetchCanceledOrders: false },
    })
    await expect(connector.getCancelledOrders("BTC/USDT")).rejects.toThrow(NotSupported)
  })

  it("returns empty array when fetchCanceledOrders returns empty", async () => {
    const connector = makeConnector()
    const orders = await connector.getCancelledOrders("BTC/USDT")
    expect(orders).toEqual([])
  })
})

describe("CCXTConnector – getPositions", () => {
  it("returns empty array when fetchPositions unsupported", async () => {
    const connector = makeConnector({ has: { fetchPositions: false } })
    const positions = await connector.getPositions()
    expect(positions).toEqual([])
  })
})

describe("CCXTConnector – getAllAvailableSymbols", () => {
  it("returns only active symbols by default", () => {
    const connector = makeConnector()
    const symbols = connector.getAllAvailableSymbols()
    expect(symbols).toContain("BTC/USDT")
  })

  it("returns all symbols when activeOnly=false", () => {
    const connector = makeConnector()
    const symbols = connector.getAllAvailableSymbols(false)
    expect(symbols).toContain("BTC/USDT")
  })
})

describe("CCXTConnector – adapter integration", () => {
  it("uses custom adapter class when provided", () => {
    class CustomAdapter extends CCXTAdapter {}
    const config: ExchangeConfig = { exchangeName: "binance", credentials: undefined }
    const connector = new CCXTConnector(config, CustomAdapter)
    expect(connector.adapter).toBeInstanceOf(CustomAdapter)
  })
})
