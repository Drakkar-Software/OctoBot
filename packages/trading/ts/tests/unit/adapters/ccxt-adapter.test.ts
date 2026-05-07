import { describe, expect, it } from "vitest"
import { CCXTAdapter } from "../../../src/adapters/ccxt-adapter.js"
import { FeeColumns, OrderColumns } from "../../../src/enums/exchange-constants.js"
import { OrderStatus } from "../../../src/enums/order-status.js"

class TestAdapter extends CCXTAdapter {
  constructor() {
    super(null)
  }
}

const adapter = new TestAdapter()

describe("CCXTAdapter – timestamps", () => {
  it("converts millisecond timestamps to seconds", () => {
    const ms = 1_700_000_000_000 // ms > threshold
    expect(adapter.getUniformizedTimestamp(ms)).toBeCloseTo(1_700_000_000, 0)
  })

  it("keeps second timestamps unchanged", () => {
    const secs = 1_700_000_000 // seconds, below threshold
    expect(adapter.getUniformizedTimestamp(secs)).toBe(secs)
  })

  it("returns null for null input", () => {
    expect(adapter.getUniformizedTimestamp(null)).toBeNull()
    expect(adapter.getUniformizedTimestamp(undefined)).toBeNull()
  })
})

describe("CCXTAdapter – adaptOrder", () => {
  const rawOrder = {
    id: "exchange-order-123",
    timestamp: 1_700_000_000_000, // ms
    symbol: "BTC/USDT",
    type: "limit",
    side: "buy",
    price: 30000.0,
    amount: 0.001,
    filled: 0.0,
    remaining: 0.001,
    cost: null,
    average: null,
    status: "open",
    fee: { type: "taker", currency: "USDT", rate: 0.001, cost: 0.03 },
    reduceOnly: false,
    stopPrice: null,
    stopLossPrice: null,
    takeProfitPrice: null,
    info: {},
  }

  it("renames id to exchange_id", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrder(rawOrder as any)
    expect(adapted).not.toBeNull()
    expect(adapted!.exchange_id).toBe("exchange-order-123")
    expect((adapted as unknown as Record<string, unknown>)["id"]).toBeUndefined()
  })

  it("converts millisecond timestamp to seconds", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrder(rawOrder as any)
    expect(adapted!.timestamp).toBeCloseTo(1_700_000_000, 0)
  })

  it("preserves order fields", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrder(rawOrder as any)
    expect(adapted!.symbol).toBe("BTC/USDT")
    expect(adapted!.type).toBe("limit")
    expect(adapted!.side).toBe("buy")
    expect(adapted!.price).toBe(30000)
    expect(adapted!.amount).toBe(0.001)
    expect(adapted!.status).toBe("open")
  })

  it("parses fee and registers is_from_exchange", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrder(rawOrder as any)
    expect(adapted!.fee).not.toBeNull()
    expect(adapted!.fee!.cost).toBe(0.03)
    expect(adapted!.fee!.is_from_exchange).toBe(true)
    expect(adapted!.fee!.exchange_original_cost).toBe(0.03)
  })

  it("returns null for null input", () => {
    expect(adapter.adaptOrder(null)).toBeNull()
    expect(adapter.adaptOrder(undefined)).toBeNull()
  })
})

describe("CCXTAdapter – adaptOhlcv", () => {
  const rawCandles = [
    [1_700_000_000_000, 30000, 31000, 29000, 30500, 100.5], // ms timestamp
    [1_700_003_600_000, 30500, 32000, 30000, 31000, 200.0],
  ]

  it("converts ms timestamps to seconds and aligns to 1h boundary", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOhlcv(rawCandles as any, { time_frame: "1h" })
    expect(adapted).not.toBeNull()
    expect(adapted!.length).toBe(2)
    // 1700000000 aligned to 3600s boundary = 1700000000 - (1700000000 % 3600)
    const expected0 = 1_700_000_000 - (1_700_000_000 % 3600)
    expect(adapted![0][0]).toBe(expected0)
  })

  it("preserves OHLCV values as numbers", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOhlcv(rawCandles as any, { time_frame: "1h" })
    expect(adapted![0][1]).toBe(30000) // open
    expect(adapted![0][2]).toBe(31000) // high
    expect(adapted![0][3]).toBe(29000) // low
    expect(adapted![0][4]).toBe(30500) // close
    expect(adapted![0][5]).toBe(100.5) // volume
  })

  it("returns null for null input", () => {
    expect(adapter.adaptOhlcv(null)).toBeNull()
  })
})

describe("CCXTAdapter – adaptBalance", () => {
  const rawBalance = {
    free: { BTC: 1.5, USDT: 10000 },
    used: { BTC: 0.5, USDT: 0 },
    total: { BTC: 2.0, USDT: 10000 },
    info: { someExchangeData: true },
    timestamp: 1_700_000_000_000,
    datetime: "2023-11-14T00:00:00.000Z",
    BTC: { free: 1.5, used: 0.5, total: 2.0 },
    USDT: { free: 10000, used: 0, total: 10000 },
  }

  it("strips aggregate keys (free, used, total, info, timestamp, datetime)", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptBalance(rawBalance as any)
    expect(adapted).not.toBeNull()
    expect(adapted!["free"]).toBeUndefined()
    expect(adapted!["used"]).toBeUndefined()
    expect(adapted!["total"]).toBeUndefined()
    expect(adapted!["info"]).toBeUndefined()
    expect(adapted!["timestamp"]).toBeUndefined()
    expect(adapted!["datetime"]).toBeUndefined()
  })

  it("keeps per-currency balance objects with free/used/total", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptBalance(rawBalance as any)
    expect(adapted!["BTC"]).toEqual({ free: 1.5, used: 0.5, total: 2.0 })
    expect(adapted!["USDT"]).toEqual({ free: 10000, used: 0, total: 10000 })
  })
})

describe("CCXTAdapter – adaptTicker", () => {
  const rawTicker = {
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
  }

  it("converts ms timestamp to seconds", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptTicker(rawTicker as any)
    expect(adapted).not.toBeNull()
    expect(adapted!.timestamp).toBeCloseTo(1_700_000_000, 0)
  })

  it("preserves close and last price", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptTicker(rawTicker as any)
    expect(adapted!.close).toBe(30500)
    expect(adapted!.last).toBe(30500)
  })
})

describe("CCXTAdapter – adaptMarketStatus", () => {
  const rawMarket = {
    symbol: "BTC/USDT",
    id: "BTCUSDT",
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
  }

  it("maps base/quote correctly", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptMarketStatus(rawMarket as any)
    expect(adapted).not.toBeNull()
    expect(adapted!.base).toBe("BTC")
    expect(adapted!.quote).toBe("USDT")
  })

  it("maps precision fields", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptMarketStatus(rawMarket as any)
    expect(adapted!.precision.price).toBe(2)
    expect(adapted!.precision.amount).toBe(6)
  })

  it("maps limit fields", () => {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptMarketStatus(rawMarket as any)
    expect(adapted!.limits.amount.min).toBe(0.00001)
    expect(adapted!.limits.cost.min).toBe(5)
    expect(adapted!.limits.cost.max).toBeNull()
  })
})

describe("CCXTAdapter – adaptOrders", () => {
  it("returns null for null input", () => {
    expect(adapter.adaptOrders(null)).toBeNull()
  })

  it("maps array of orders", () => {
    const raw = [
      {
        id: "1",
        timestamp: 1_700_000_000,
        symbol: "ETH/USDT",
        type: "limit",
        side: "sell",
        price: 2000,
        amount: 1,
        filled: 0,
        remaining: 1,
        cost: null,
        average: null,
        status: "open",
        fee: null,
        reduceOnly: false,
        stopPrice: null,
        stopLossPrice: null,
        takeProfitPrice: null,
        info: {},
      },
    ]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrders(raw as any)
    expect(adapted).toHaveLength(1)
    expect(adapted![0].exchange_id).toBe("1")
  })

  it("filters to cancelled only when cancelledOnly=true", () => {
    const raw = [
      { id: "1", status: "open", timestamp: 0, symbol: "BTC/USDT", type: "limit", side: "buy", price: 1, amount: 1, filled: 0, remaining: 1, cost: null, average: null, fee: null, reduceOnly: false, stopPrice: null, stopLossPrice: null, takeProfitPrice: null, info: {} },
      { id: "2", status: "canceled", timestamp: 0, symbol: "BTC/USDT", type: "limit", side: "buy", price: 1, amount: 1, filled: 0, remaining: 1, cost: null, average: null, fee: null, reduceOnly: false, stopPrice: null, stopLossPrice: null, takeProfitPrice: null, info: {} },
    ]
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const adapted = adapter.adaptOrders(raw as any, { cancelledOnly: true })
    expect(adapted).toHaveLength(1)
    expect(adapted![0].status).toBe(OrderStatus.CANCELED)
  })
})
