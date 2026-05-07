// Mirrors additional_tests/exchanges_tests/test_bybit.py
import { describe, it } from "vitest"
import {
  AbstractAuthenticatedExchangeTester,
  registerExchangeLifecycle,
} from "./abstract-exchange-tester.js"

const hasCredentials = !!(process.env.BYBIT_API_KEY && process.env.BYBIT_SECRET)

class BybitTester extends AbstractAuthenticatedExchangeTester {
  EXCHANGE_NAME = "bybit"
  SYMBOL = "BTC/USDT"
  TIME_FRAME = "1h"
  ORDER_CURRENCY = "BTC"
  SETTLEMENT_CURRENCY = "USDT"
  EXPECTED_QUOTE_MIN_ORDER_SIZE = 5
}

const tester = new BybitTester()
registerExchangeLifecycle(tester)

describe("Bybit – public data", () => {
  it("gets market status", () => tester.testGetMarketStatus())
  it("gets OHLCV prices", () => tester.testGetSymbolPrices())
  it("gets kline price", () => tester.testGetKlinePrice())
  it("gets price ticker", () => tester.testGetPriceTicker())
  it("gets all tickers", () => tester.testGetAllCurrenciesPriceTicker())
  it("gets order book", () => tester.testGetOrderBook())
  it("gets recent trades", () => tester.testGetRecentTrades())
})

describe.skipIf(!hasCredentials)("Bybit – authenticated", () => {
  it("gets portfolio", () => tester.testGetPortfolio())
  it("gets open orders", () => tester.testGetOpenOrders())
  it("gets closed orders", () => tester.testGetClosedOrders())
  it("gets cancelled orders", () => tester.testGetCancelledOrders())
  it("gets my recent trades", () => tester.testGetMyRecentTrades())
  it("handles order not found", () => tester.testGetNotFoundOrder())
  it("handles invalid API key", () => tester.testInvalidApiKeyError())
})
