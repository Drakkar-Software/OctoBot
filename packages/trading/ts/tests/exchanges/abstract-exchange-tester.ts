// Mirrors additional_tests/exchanges_tests/abstract_authenticated_exchange_tester.py
import { expect } from "vitest"
import { AuthenticationError } from "../../src/errors/index.js"
import { createExchange } from "../../src/exchanges/exchange-factory.js"
import type { RestExchange } from "../../src/exchanges/types/rest-exchange.js"
import type { OctoBotBalance, OctoBotOrder } from "../../src/types/index.js"
import { AbstractPublicExchangeTester, registerExchangeLifecycle } from "./abstract-public-exchange-tester.js"

export type SpecialOrderType = {
  symbol: string
  typeKey: string
  typeValue: string
  side?: string
}

export abstract class AbstractAuthenticatedExchangeTester extends AbstractPublicExchangeTester {
  // ── Config class variables (mirror Python exactly) ────────────────────────
  EXCHANGE_TYPE = "spot"
  ORDER_CURRENCY = "BTC"
  SETTLEMENT_CURRENCY = "USDT"
  /** Percentage of portfolio to use for test orders */
  ORDER_SIZE = 10
  /** Percentage away from current price for limit/stop orders */
  ORDER_PRICE_DIFF = 20
  /** Known existing order ID for testGetOrder */
  VALID_ORDER_ID = ""
  ALLOW_0_MAKER_FEES = false
  EXPECT_MISSING_FEE_IN_CANCELLED_ORDERS = true
  EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = false
  CONVERTS_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = false
  OPEN_ORDERS_IN_CLOSED_ORDERS = false
  CANCELLED_ORDERS_IN_CLOSED_ORDERS = false
  EXPECT_FETCH_ORDER_TO_BE_AVAILABLE = true
  MIN_PORTFOLIO_SIZE = 1
  EXPECTED_QUOTE_MIN_ORDER_SIZE = 1
  DUPLICATE_TRADES_RATIO = 0
  CHECK_EMPTY_ACCOUNT = false
  MARKET_FILL_TIMEOUT = 15
  OPEN_TIMEOUT = 15
  CANCEL_TIMEOUT = 15
  SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID: Record<string, SpecialOrderType> = {}
  UNCANCELLABLE_ORDER_ID_SYMBOL_TYPE: [string, string, string] | null = null

  // ── Helpers ───────────────────────────────────────────────────────────────

  protected async getCurrentPrice(): Promise<number> {
    const ticker = await this.exchange.getPriceTicker(this.SYMBOL)
    if (!ticker.close || ticker.close <= 0) throw new Error(`Invalid price for ${this.SYMBOL}`)
    return ticker.close
  }

  protected async getPortfolio(): Promise<OctoBotBalance> {
    return this.exchange.getBalance()
  }

  protected computeSafeOrderPrice(currentPrice: number, side: string, priceDiffPercent: number): number {
    const multiplier = priceDiffPercent / 100
    return side === "buy"
      ? currentPrice * (1 - multiplier)
      : currentPrice * (1 + multiplier)
  }

  protected computeOrderSize(
    portfolio: OctoBotBalance,
    currency: string,
    currentPrice: number,
    percent: number,
  ): number {
    const holding = (portfolio[currency] as { free?: number } | undefined)?.free ?? 0
    const quoteHolding =
      (portfolio[this.SETTLEMENT_CURRENCY] as { free?: number } | undefined)?.free ?? 0

    if (currency === this.ORDER_CURRENCY) {
      // For futures/sell orders: use the currency directly
      return (holding * percent) / 100
    }
    // For buy orders: convert quote balance to base amount
    const quoteValue = (quoteHolding * percent) / 100
    return quoteValue / currentPrice
  }

  protected async waitForOrderStatus(
    exchangeOrderId: string,
    symbol: string,
    expectedStatus: string,
    timeoutSeconds: number,
  ): Promise<OctoBotOrder> {
    const start = Date.now()
    while (Date.now() - start < timeoutSeconds * 1000) {
      const order = await this.exchange.getOrder(exchangeOrderId, symbol)
      if (order && order.status === expectedStatus) return order
      await new Promise((resolve) => setTimeout(resolve, 1000))
    }
    throw new Error(
      `Order ${exchangeOrderId} did not reach status "${expectedStatus}" within ${timeoutSeconds}s`,
    )
  }

  // ── Test methods ──────────────────────────────────────────────────────────

  async testGetPortfolio(): Promise<void> {
    const portfolio = await this.getPortfolio()
    expect(portfolio).not.toBeNull()
    const currencies = Object.keys(portfolio)
    expect(currencies.length).toBeGreaterThanOrEqual(this.MIN_PORTFOLIO_SIZE)

    let hasPositiveBalance = false
    for (const currency of currencies) {
      const entry = portfolio[currency] as { free: number; used: number; total: number }
      expect(typeof entry.free).toBe("number")
      expect(typeof entry.used).toBe("number")
      expect(typeof entry.total).toBe("number")
      if (entry.total > 0) hasPositiveBalance = true
    }
    if (!this.CHECK_EMPTY_ACCOUNT) {
      expect(hasPositiveBalance).toBe(true)
    }
    // No duplicates
    expect(new Set(currencies).size).toBe(currencies.length)
  }

  async testGetOrder(): Promise<void> {
    if (!this.VALID_ORDER_ID) {
      console.warn("VALID_ORDER_ID not set — skipping testGetOrder")
      return
    }
    const order = await this.exchange.getOrder(this.VALID_ORDER_ID, this.SYMBOL)
    expect(order).not.toBeNull()
    expect(order!.exchange_id).toBeTruthy()
    expect(order!.symbol).toBe(this.SYMBOL)
    expect(order!.status).toBeTruthy()
  }

  async testGetNotFoundOrder(): Promise<void> {
    const order = await this.exchange.getOrder("__nonexistent_order_id__", this.SYMBOL)
    expect(order).toBeNull()
  }

  async testGetSpecialOrders(): Promise<void> {
    for (const [orderId, spec] of Object.entries(this.SPECIAL_ORDER_TYPES_BY_EXCHANGE_ID)) {
      const order = await this.exchange.getOrder(orderId, spec.symbol)
      expect(order).not.toBeNull()
      if (spec.side) expect(order!.side).toBe(spec.side)
    }
  }

  async testGetOpenOrders(): Promise<void> {
    const orders = await this.exchange.getOpenOrders(this.SYMBOL)
    expect(Array.isArray(orders)).toBe(true)
    for (const order of orders) {
      expect(order.exchange_id).toBeTruthy()
      expect(order.symbol).toBeTruthy()
      expect(order.status).toBeTruthy()
    }
  }

  async testGetClosedOrders(): Promise<void> {
    const orders = await this.exchange.getClosedOrders(this.SYMBOL)
    expect(Array.isArray(orders)).toBe(true)
    for (const order of orders) {
      expect(order.timestamp).toBeLessThan(4_000_000_000) // seconds
      expect(order.status).toBeTruthy()
    }
  }

  async testGetCancelledOrders(): Promise<void> {
    try {
      const orders = await this.exchange.getCancelledOrders(this.SYMBOL)
      expect(Array.isArray(orders)).toBe(true)
    } catch (err) {
      // Some exchanges don't support fetching cancelled orders — acceptable
      const { NotSupported } = await import("../../src/errors/index.js")
      expect(err).toBeInstanceOf(NotSupported)
    }
  }

  async testGetMyRecentTrades(): Promise<void> {
    const trades = await this.exchange.getMyRecentTrades(this.SYMBOL, undefined, 10)
    expect(Array.isArray(trades)).toBe(true)
    for (const trade of trades) {
      expect(trade.symbol).toBe(this.SYMBOL)
      if (trade.fee !== null && trade.fee !== undefined) {
        expect(typeof trade.fee.cost).toBe("number")
      }
    }
  }

  async testCreateAndCancelLimitOrders(): Promise<void> {
    const currentPrice = await this.getCurrentPrice()
    const portfolio = await this.getPortfolio()

    const buyPrice = this.computeSafeOrderPrice(currentPrice, "buy", this.ORDER_PRICE_DIFF)
    const buyAmount = this.computeOrderSize(
      portfolio,
      this.SETTLEMENT_CURRENCY,
      currentPrice,
      this.ORDER_SIZE,
    )

    // Ensure we meet minimum order sizes
    const minAmount = Math.max(
      buyAmount,
      this.EXPECTED_QUOTE_MIN_ORDER_SIZE / buyPrice,
    )

    // Create limit buy order
    const createdOrder = await this.exchange.createOrder(
      "buy_limit",
      this.SYMBOL,
      minAmount,
      buyPrice,
    )
    expect(createdOrder).not.toBeNull()
    expect(createdOrder!.exchange_id).toBeTruthy()

    // Wait for open status
    const openOrder = await this.waitForOrderStatus(
      createdOrder!.exchange_id,
      this.SYMBOL,
      "open",
      this.OPEN_TIMEOUT,
    )
    expect(openOrder.status).toBe("open")

    // Verify it appears in open orders
    const openOrders = await this.exchange.getOpenOrders(this.SYMBOL)
    const found = openOrders.find((o) => o.exchange_id === createdOrder!.exchange_id)
    expect(found).toBeDefined()

    // Cancel the order
    await this.exchange.cancelOrder(createdOrder!.exchange_id, this.SYMBOL, "buy_limit")
    const cancelledOrder = await this.waitForOrderStatus(
      createdOrder!.exchange_id,
      this.SYMBOL,
      "canceled",
      this.CANCEL_TIMEOUT,
    )
    expect(cancelledOrder.status).toBe("canceled")

    // Verify it no longer appears in open orders
    const openOrdersAfter = await this.exchange.getOpenOrders(this.SYMBOL)
    const stillOpen = openOrdersAfter.find((o) => o.exchange_id === createdOrder!.exchange_id)
    expect(stillOpen).toBeUndefined()
  }

  async testCreateAndFillMarketOrders(): Promise<void> {
    const currentPrice = await this.getCurrentPrice()
    const portfolio = await this.getPortfolio()

    const buyAmount = this.computeOrderSize(
      portfolio,
      this.SETTLEMENT_CURRENCY,
      currentPrice,
      this.ORDER_SIZE,
    )
    const minAmount = Math.max(buyAmount, this.EXPECTED_QUOTE_MIN_ORDER_SIZE / currentPrice)

    // Create market buy
    const buyOrder = await this.exchange.createOrder("buy_market", this.SYMBOL, minAmount)
    expect(buyOrder).not.toBeNull()

    // Wait for fill
    const filledBuy = await this.waitForOrderStatus(
      buyOrder!.exchange_id,
      this.SYMBOL,
      "closed",
      this.MARKET_FILL_TIMEOUT,
    )
    expect(filledBuy.filled).toBeGreaterThan(0)
    if (!this.ALLOW_0_MAKER_FEES) {
      expect(filledBuy.fee).not.toBeNull()
    }

    // Sell back to close position
    const portfolioAfterBuy = await this.getPortfolio()
    const sellAmount = (portfolioAfterBuy[this.ORDER_CURRENCY] as { free: number } | undefined)?.free ?? minAmount

    const sellOrder = await this.exchange.createOrder("sell_market", this.SYMBOL, sellAmount)
    expect(sellOrder).not.toBeNull()
    await this.waitForOrderStatus(
      sellOrder!.exchange_id,
      this.SYMBOL,
      "closed",
      this.MARKET_FILL_TIMEOUT,
    )
  }

  async testCreateAndCancelStopOrders(): Promise<void> {
    const currentPrice = await this.getCurrentPrice()
    const portfolio = await this.getPortfolio()

    const stopPrice = this.computeSafeOrderPrice(currentPrice, "sell", this.ORDER_PRICE_DIFF)
    const sellAmount = this.computeOrderSize(
      portfolio,
      this.ORDER_CURRENCY,
      currentPrice,
      this.ORDER_SIZE,
    )

    if (sellAmount <= 0) {
      console.warn("Insufficient balance for stop order test — skipping")
      return
    }

    const stopOrder = await this.exchange.createOrder(
      "stop_loss",
      this.SYMBOL,
      sellAmount,
      undefined,
      stopPrice,
      "sell",
    )
    expect(stopOrder).not.toBeNull()
    expect(stopOrder!.exchange_id).toBeTruthy()

    await this.exchange.cancelOrder(stopOrder!.exchange_id, this.SYMBOL, "stop_loss")
    const cancelled = await this.waitForOrderStatus(
      stopOrder!.exchange_id,
      this.SYMBOL,
      "canceled",
      this.CANCEL_TIMEOUT,
    )
    expect(cancelled.status).toBe("canceled")
  }

  async testEditLimitOrder(): Promise<void> {
    const currentPrice = await this.getCurrentPrice()
    const buyPrice = this.computeSafeOrderPrice(currentPrice, "buy", this.ORDER_PRICE_DIFF)
    const minAmount = this.EXPECTED_QUOTE_MIN_ORDER_SIZE / buyPrice

    const created = await this.exchange.createOrder(
      "buy_limit",
      this.SYMBOL,
      minAmount,
      buyPrice,
    )
    expect(created).not.toBeNull()

    const newPrice = this.computeSafeOrderPrice(currentPrice, "buy", this.ORDER_PRICE_DIFF * 1.5)
    const edited = await this.exchange.editOrder(
      created!.exchange_id,
      "buy_limit",
      this.SYMBOL,
      minAmount,
      newPrice,
    )
    expect(edited.exchange_id).toBeTruthy()

    // Clean up
    await this.exchange.cancelOrder(edited.exchange_id, this.SYMBOL, "buy_limit")
  }

  async testInvalidApiKeyError(): Promise<void> {
    const badConfig = {
      exchangeName: this.EXCHANGE_NAME,
      credentials: { apiKey: "bad-key", secret: "bad-secret" },
    }
    const badExchange = createExchange(badConfig)
    await badExchange.initialize()
    await expect(badExchange.getBalance()).rejects.toThrow(AuthenticationError)
    await badExchange.stop()
  }
}

export { registerExchangeLifecycle }
