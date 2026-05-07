// Mirrors additional_tests/exchanges_tests/ public data test patterns
import { afterEach, beforeEach, expect } from "vitest"
import { createExchange } from "../../src/exchanges/exchange-factory.js"
import type { RestExchange } from "../../src/exchanges/types/rest-exchange.js"
import type { ExchangeConfig } from "../../src/types/index.js"

export abstract class AbstractPublicExchangeTester {
  abstract EXCHANGE_NAME: string
  abstract SYMBOL: string
  abstract TIME_FRAME: string

  protected exchange!: RestExchange

  setup(): void {
    const config: ExchangeConfig = {
      exchangeName: this.EXCHANGE_NAME,
      credentials: undefined,
    }
    this.exchange = createExchange(config)
  }

  async initialize(): Promise<void> {
    await this.exchange.initialize()
  }

  async teardown(): Promise<void> {
    await this.exchange.stop()
  }

  // ---------------------------------------------------------------------------
  // Market status
  // ---------------------------------------------------------------------------

  async testGetMarketStatus(): Promise<void> {
    const ms = this.exchange.getMarketStatus(this.SYMBOL)
    expect(ms).not.toBeNull()
    expect(ms.symbol).toBe(this.SYMBOL)
    expect(ms.base).toBeTruthy()
    expect(ms.quote).toBeTruthy()
    expect(typeof ms.precision.price).toBe("number")
    expect(typeof ms.precision.amount).toBe("number")
    expect(ms.limits.amount).toBeDefined()
    expect(ms.limits.price).toBeDefined()
    expect(ms.limits.cost).toBeDefined()
  }

  // ---------------------------------------------------------------------------
  // OHLCV
  // ---------------------------------------------------------------------------

  async testGetSymbolPrices(): Promise<void> {
    const candles = await this.exchange.getSymbolPrices(this.SYMBOL, this.TIME_FRAME, 10)
    expect(candles.length).toBeGreaterThan(5)
    for (const candle of candles) {
      expect(candle).toHaveLength(6)
      const [ts, open, high, low, close, volume] = candle
      // timestamps must be in seconds (< year 2100)
      expect(ts).toBeLessThan(4_000_000_000)
      expect(open).toBeGreaterThan(0)
      expect(high).toBeGreaterThanOrEqual(open)
      expect(low).toBeLessThanOrEqual(open)
      expect(close).toBeGreaterThan(0)
      expect(volume).toBeGreaterThanOrEqual(0)
    }
  }

  async testGetKlinePrice(): Promise<void> {
    const candles = await this.exchange.getKlinePrice(this.SYMBOL, this.TIME_FRAME)
    expect(candles.length).toBeGreaterThanOrEqual(1)
    expect(candles[0]).toHaveLength(6)
  }

  // ---------------------------------------------------------------------------
  // Ticker
  // ---------------------------------------------------------------------------

  async testGetPriceTicker(): Promise<void> {
    const ticker = await this.exchange.getPriceTicker(this.SYMBOL)
    expect(ticker).not.toBeNull()
    expect(ticker.close).toBeGreaterThan(0)
    expect(ticker.last).toBeGreaterThan(0)
    // timestamp in seconds
    expect(ticker.timestamp).toBeLessThan(4_000_000_000)
  }

  async testGetAllCurrenciesPriceTicker(): Promise<void> {
    const tickers = await this.exchange.getAllCurrenciesPriceTicker()
    expect(tickers).not.toBeNull()
    expect(Object.keys(tickers).length).toBeGreaterThan(0)
    // The exchange's symbol should be present (unless CAN_MISS_TICKERS_IN_ALL_TICKERS)
    const ExchangeClass = this.exchange.constructor as { CAN_MISS_TICKERS_IN_ALL_TICKERS?: boolean }
    if (!ExchangeClass.CAN_MISS_TICKERS_IN_ALL_TICKERS) {
      expect(tickers[this.SYMBOL]).toBeDefined()
    }
  }

  // ---------------------------------------------------------------------------
  // Order book
  // ---------------------------------------------------------------------------

  async testGetOrderBook(): Promise<void> {
    const book = await this.exchange.getOrderBook(this.SYMBOL)
    expect(book).not.toBeNull()
    expect(book.bids.length).toBeGreaterThan(0)
    expect(book.asks.length).toBeGreaterThan(0)
    expect(book.bids[0][0]).toBeGreaterThan(0) // price
    expect(book.bids[0][1]).toBeGreaterThan(0) // amount
    expect(book.asks[0][0]).toBeGreaterThan(0)
    // asks should be higher than bids
    expect(book.asks[0][0]).toBeGreaterThan(book.bids[0][0])
  }

  // ---------------------------------------------------------------------------
  // Trades
  // ---------------------------------------------------------------------------

  async testGetRecentTrades(): Promise<void> {
    const trades = await this.exchange.getRecentTrades(this.SYMBOL, 10)
    expect(trades.length).toBeGreaterThan(1)
    for (const trade of trades) {
      expect(trade.symbol).toBe(this.SYMBOL)
      expect(trade.price).toBeGreaterThan(0)
      expect(trade.amount).toBeGreaterThan(0)
    }
  }
}

// ---------------------------------------------------------------------------
// Vitest lifecycle wiring — call in describe blocks:
//   beforeEach(() => tester.setupBeforeEach())
//   afterEach(() => tester.teardownAfterEach())
// ---------------------------------------------------------------------------

export function registerExchangeLifecycle(tester: AbstractPublicExchangeTester): void {
  beforeEach(async () => {
    tester.setup()
    await tester.initialize()
  })
  afterEach(async () => {
    await tester.teardown()
  })
}
