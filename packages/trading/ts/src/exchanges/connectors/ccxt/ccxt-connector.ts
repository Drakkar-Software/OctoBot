// Mirrors octobot_trading/exchanges/connectors/ccxt/ccxt_connector.py
import * as ccxt from "ccxt"

import { CCXTAdapter } from "../../../adapters/ccxt-adapter.js"
import { withCcxtErrorConversion } from "../../../errors/ccxt-converter.js"
import { NotSupported, OrderCancelError } from "../../../errors/index.js"
import type {
  ExchangeConfig,
  OctoBotBalance,
  OctoBotDepositAddress,
  OctoBotFundingRate,
  OctoBotLeverageTier,
  OctoBotMarketStatus,
  OctoBotOHLCV,
  OctoBotOrder,
  OctoBotOrderBook,
  OctoBotPosition,
  OctoBotTicker,
  OctoBotTrade,
  OctoBotTransaction,
} from "../../../types/index.js"
import { ExchangeMarketStatusFixer } from "../../util/market-status-fixer.js"
import {
  createCcxtClient,
  getContractSize,
  mapOrderTypeToCcxt,
} from "./ccxt-client-util.js"

export class CCXTConnector {
  client: ccxt.Exchange
  adapter: CCXTAdapter
  symbols: Set<string> = new Set()
  timeFrames: Set<string> = new Set()
  isAuthenticated: boolean
  allCurrenciesPriceTicker: Record<string, OctoBotTicker> = {}

  // Exchange capability flags — delegated from RestExchange class
  exchange: {
    DUMP_INCOMPLETE_LAST_CANDLE: boolean
    FIX_MARKET_STATUS: boolean
    REMOVE_MARKET_STATUS_PRICE_LIMITS: boolean
    isFuture: boolean
    getContractSize: (symbol: string) => number
  } | null = null

  constructor(
    private readonly config: ExchangeConfig,
    adapterClass: typeof CCXTAdapter = CCXTAdapter,
  ) {
    this.client = createCcxtClient(config)
    this.adapter = new adapterClass(this)
    this.isAuthenticated = !!(config.credentials?.apiKey && config.credentials?.secret)
  }

  async initialize(): Promise<void> {
    await withCcxtErrorConversion(async () => {
      await this.client.loadMarkets()
      this.symbols = new Set(Object.keys(this.client.markets ?? {}))
      this.timeFrames = new Set(Object.keys(this.client.timeframes ?? {}))
    })
  }

  async stop(): Promise<void> {
    // REST clients have no explicit close needed
  }

  getExchangeCurrentTime(): number {
    return Math.floor(Date.now() / 1000)
  }

  getContractSizeForSymbol(symbol: string): number {
    if (this.exchange?.isFuture) {
      return getContractSize(this.client, symbol)
    }
    return 1
  }

  getMarketStatus(
    symbol: string,
    priceExample?: number,
    withFixer = true,
  ): OctoBotMarketStatus {
    const raw = this.client.market(symbol)
    const adapted = this.adapter.adaptMarketStatus(raw)
    if (!adapted) throw new Error(`Failed to adapt market status for ${symbol}`)
    if (withFixer) {
      const shouldRemovePriceLimits = this.exchange?.REMOVE_MARKET_STATUS_PRICE_LIMITS ?? false
      const fixer = new ExchangeMarketStatusFixer(adapted, priceExample)
      if (shouldRemovePriceLimits) {
        fixer.marketStatus.limits.price = { min: null, max: null }
      }
      return fixer.marketStatus
    }
    return adapted
  }

  getAllAvailableSymbols(activeOnly = true): string[] {
    if (!this.client.markets) return []
    return Object.entries(this.client.markets)
      .filter(([, market]) => !activeOnly || ((market as ccxt.Market | undefined)?.active ?? false))
      .map(([symbol]) => symbol)
  }

  async refreshMarkets(reload = true): Promise<void> {
    await withCcxtErrorConversion(() => this.client.loadMarkets(reload))
    this.symbols = new Set(Object.keys(this.client.markets ?? {}))
  }

  // ── Public market data ────────────────────────────────────────────────────

  async getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchOHLCV(symbol, timeFrame, undefined, limit, params)
      return this.adapter.adaptOhlcv(raw, { time_frame: timeFrame }) ?? []
    })
  }

  async getKlinePrice(
    symbol: string,
    timeFrame: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchOHLCV(symbol, timeFrame, undefined, 1, params)
      return this.adapter.adaptKline(raw, { time_frame: timeFrame }) ?? []
    })
  }

  async getPriceTicker(symbol: string, params?: Record<string, unknown>): Promise<OctoBotTicker> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchTicker(symbol, params)
      const adapted = this.adapter.adaptTicker(raw)
      if (!adapted) throw new Error(`Failed to adapt ticker for ${symbol}`)
      return adapted
    })
  }

  async getAllCurrenciesPriceTicker(
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotTicker>> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchTickers(undefined, params)
      const result: Record<string, OctoBotTicker> = {}
      for (const [sym, ticker] of Object.entries(raw)) {
        const adapted = this.adapter.adaptTicker(ticker as ccxt.Ticker)
        if (adapted) result[sym] = adapted
      }
      Object.assign(this.allCurrenciesPriceTicker, result)
      return this.allCurrenciesPriceTicker
    })
  }

  async getOrderBook(
    symbol: string,
    limit = 5,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrderBook> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchOrderBook(symbol, limit, params)
      const adapted = this.adapter.adaptOrderBook(raw)
      if (!adapted) throw new Error(`Failed to adapt order book for ${symbol}`)
      return adapted
    })
  }

  async getRecentTrades(
    symbol: string,
    limit = 50,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchTrades(symbol, undefined, limit, params)
      return this.adapter.adaptPublicRecentTrades(raw) ?? []
    })
  }

  // ── Account data ──────────────────────────────────────────────────────────

  async getBalance(params?: Record<string, unknown>): Promise<OctoBotBalance> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchBalance(params ?? {})
      const adapted = this.adapter.adaptBalance(raw)
      if (!adapted) throw new Error("Failed to adapt balance")
      return adapted
    })
  }

  // ── Orders ────────────────────────────────────────────────────────────────

  async getOrder(
    exchangeOrderId: string,
    symbol?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchOrder"]) {
        const open = await this.getOpenOrders(symbol)
        const closed = await this.getClosedOrders(symbol)
        return [...open, ...closed].find((o) => o.exchange_id === exchangeOrderId) ?? null
      }
      try {
        const raw = await this.client.fetchOrder(exchangeOrderId, symbol, params)
        return raw ? this.adapter.adaptOrder(raw) : null
      } catch {
        return null
      }
    })
  }

  async getOpenOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchOpenOrders(symbol, since, limit, params)
      return this.adapter.adaptOrders(raw) ?? []
    })
  }

  async getClosedOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchClosedOrders"]) return []
      const raw = await this.client.fetchClosedOrders(symbol, since, limit, params)
      return this.adapter.adaptOrders(raw) ?? []
    })
  }

  async getCancelledOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchCanceledOrders"]) {
        throw new NotSupported("fetchCanceledOrders is not supported by this exchange")
      }
      const raw = await this.client.fetchCanceledOrders(symbol, since, limit, params)
      return this.adapter.adaptOrders(raw) ?? []
    })
  }

  async getMyRecentTrades(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchMyTrades(symbol, since, limit, params)
      return this.adapter.adaptTrades(raw ?? []) ?? []
    })
  }

  async createOrder(
    orderType: string,
    symbol: string,
    quantity: number,
    price?: number,
    stopPrice?: number,
    side?: string,
    _currentPrice?: number,
    reduceOnly = false,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null> {
    return withCcxtErrorConversion(async () => {
      const { ccxtType, ccxtSide } = mapOrderTypeToCcxt(orderType, side)
      const orderParams: Record<string, unknown> = { ...(params ?? {}) }
      if (reduceOnly) orderParams["reduceOnly"] = true
      if (stopPrice) {
        orderParams["stopPrice"] = stopPrice
        orderParams["stopLossPrice"] = stopPrice
      }
      const raw = await this.client.createOrder(
        symbol,
        ccxtType,
        ccxtSide,
        quantity,
        price,
        orderParams,
      )
      return raw ? this.adapter.adaptOrder(raw) : null
    })
  }

  async cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    _orderType: string,
    params?: Record<string, unknown>,
  ): Promise<string> {
    return withCcxtErrorConversion(async () => {
      await this.client.cancelOrder(exchangeOrderId, symbol, params)
      return "canceled"
    })
  }

  async editOrder(
    exchangeOrderId: string,
    _orderType: string,
    symbol: string,
    quantity: number,
    price: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["editOrder"]) {
        throw new OrderCancelError("editOrder is not supported by this exchange")
      }
      const raw = await this.client.editOrder(
        exchangeOrderId,
        symbol,
        "limit",
        "buy",
        quantity,
        price,
        params,
      )
      const adapted = this.adapter.adaptOrder(raw)
      if (!adapted) throw new Error("Failed to adapt edited order")
      return adapted
    })
  }

  // ── Futures / positions ───────────────────────────────────────────────────

  async getPositions(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<OctoBotPosition[]> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchPositions"]) return []
      const raw = await this.client.fetchPositions(symbols, params)
      return (raw ?? [])
        .map((p) => this.adapter.adaptPosition(p))
        .filter((p): p is OctoBotPosition => p !== null)
    })
  }

  async getLeverageTiers(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotLeverageTier[]>> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchLeverageTiers"]) return {}
      const raw = await this.client.fetchLeverageTiers(symbols, params)
      return this.adapter.adaptLeverageTiers(raw) ?? {}
    })
  }

  async getFundingRate(symbol: string, params?: Record<string, unknown>): Promise<OctoBotFundingRate> {
    return withCcxtErrorConversion(async () => {
      const raw = await this.client.fetchFundingRate(symbol, params)
      const adapted = this.adapter.adaptFundingRate(raw)
      if (!adapted) throw new Error(`Failed to adapt funding rate for ${symbol}`)
      return adapted
    })
  }

  async getDepositAddress(
    currency: string,
    network?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotDepositAddress> {
    return withCcxtErrorConversion(async () => {
      const p = network ? { ...(params ?? {}), network } : (params ?? {})
      const raw = await this.client.fetchDepositAddress(currency, p)
      const adapted = this.adapter.adaptDepositAddress(raw)
      if (!adapted) throw new Error(`Failed to adapt deposit address for ${currency}`)
      return adapted
    })
  }

  async getTransactions(
    currency?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTransaction[]> {
    return withCcxtErrorConversion(async () => {
      if (!(this.client.has as Record<string, unknown>)["fetchTransactions"]) return []
      const raw = await this.client.fetchTransactions(currency, since, limit, params)
      return (raw ?? [])
        .map((t) => this.adapter.adaptTransaction(t as ccxt.Transaction))
        .filter((t): t is OctoBotTransaction => t !== null)
    })
  }
}
