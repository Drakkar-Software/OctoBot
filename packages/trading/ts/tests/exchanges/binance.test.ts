// Mirrors additional_tests/exchanges_tests/test_binance.py
import { describe, it } from "vitest"
import {
  AbstractAuthenticatedExchangeTester,
  registerExchangeLifecycle,
} from "./abstract-exchange-tester.js"

const hasCredentials = !!(process.env.BINANCE_API_KEY && process.env.BINANCE_SECRET)

class BinanceTester extends AbstractAuthenticatedExchangeTester {
  EXCHANGE_NAME = "binance"
  SYMBOL = "BTC/USDC"
  TIME_FRAME = "1h"
  ORDER_CURRENCY = "BTC"
  SETTLEMENT_CURRENCY = "USDC"
  VALID_ORDER_ID = "26408108410"
  CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = true
  EXPECTED_QUOTE_MIN_ORDER_SIZE = 5
  DUPLICATE_TRADES_RATIO = 0.1
}

const tester = new BinanceTester()
registerExchangeLifecycle(tester)

describe("Binance – public data", () => {
  it("gets market status", () => tester.testGetMarketStatus())
  it("gets OHLCV prices", () => tester.testGetSymbolPrices())
  it("gets kline price", () => tester.testGetKlinePrice())
  it("gets price ticker", () => tester.testGetPriceTicker())
  it("gets all tickers", () => tester.testGetAllCurrenciesPriceTicker())
  it("gets order book", () => tester.testGetOrderBook())
  it("gets recent trades", () => tester.testGetRecentTrades())
})

describe.skipIf(!hasCredentials)("Binance – authenticated", () => {
  it("gets portfolio", () => tester.testGetPortfolio())
  it("gets open orders", () => tester.testGetOpenOrders())
  it("gets closed orders", () => tester.testGetClosedOrders())
  it("gets cancelled orders", () => tester.testGetCancelledOrders())
  it("gets my recent trades", () => tester.testGetMyRecentTrades())
  it("handles order not found", () => tester.testGetNotFoundOrder())
  it("handles invalid API key", () => tester.testInvalidApiKeyError())
})
