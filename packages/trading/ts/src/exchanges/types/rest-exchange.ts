// Mirrors octobot_trading/exchanges/types/rest_exchange.py
import { CCXTAdapter } from "../../adapters/ccxt-adapter.js"
import type { TraderOrderTypeValue, TradeOrderSideValue } from "../../enums/index.js"
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
} from "../../types/index.js"
import { AbstractExchange } from "../abstract-exchange.js"
import { CCXTConnector } from "../connectors/ccxt/ccxt-connector.js"

export abstract class RestExchange extends AbstractExchange {
  // ── Capability flags (mirrors Python's 50+ class booleans) ───────────────
  static FIX_MARKET_STATUS = false
  static REMOVE_MARKET_STATUS_PRICE_LIMITS = false
  static ADAPT_MARKET_STATUS_FOR_CONTRACT_SIZE = false
  static ENABLE_SPOT_BUY_MARKET_WITH_COST = false
  static REQUIRE_ORDER_FEES_FROM_TRADES = false
  static REQUIRE_CLOSED_ORDERS_FROM_RECENT_TRADES = false
  static DUMP_INCOMPLETE_LAST_CANDLE = false
  static IS_SKIPPING_EMPTY_CANDLES_IN_OHLCV_FETCH = false
  static CAN_MISS_TICKERS_IN_ALL_TICKERS = true
  static EXPECT_POSSIBLE_ORDER_NOT_FOUND_DURING_ORDER_CREATION = false
  static OPEN_ORDERS_IN_CLOSED_ORDERS = false
  static CANCELLED_ORDERS_IN_CLOSED_ORDERS = false
  static SUPPORTS_FETCHING_CANCELLED_ORDERS = false
  static MARK_PRICE_IN_POSITION = false
  static MARK_PRICE_IN_TICKER = false
  static FUNDING_WITH_MARK_PRICE = false
  static FUNDING_IN_TICKER = false
  static SUPPORTS_SET_MARGIN_TYPE = true
  static ADJUST_FOR_TIME_DIFFERENCE = false
  static CAN_HAVE_DELAYED_OPEN_ORDERS = false
  static CONVERT_ORDER_SIZE_BEFORE_PUSHING_TO_EXCHANGES = false

  // ── Error classification string patterns ─────────────────────────────────
  static EXCHANGE_ORDER_NOT_FOUND_ERRORS: string[][] = []
  static EXCHANGE_PERMISSION_ERRORS: string[][] = []
  static EXCHANGE_COMPLIANCY_ERRORS: string[][] = []
  static EXCHANGE_INTERNAL_SYNC_ERRORS: string[][] = []
  static EXCHANGE_MISSING_FUNDS_ERRORS: string[][] = []
  static EXCHANGE_AUTHENTICATION_ERRORS: string[][] = []
  static EXCHANGE_IP_WHITELIST_ERRORS: string[][] = []

  protected connector: CCXTConnector

  constructor(config: ExchangeConfig) {
    super(config)
    this.connector = this._createConnector(config)
    // Expose exchange flags to the connector for use in adapter
    this.connector.exchange = {
      DUMP_INCOMPLETE_LAST_CANDLE: (this.constructor as typeof RestExchange).DUMP_INCOMPLETE_LAST_CANDLE,
      FIX_MARKET_STATUS: (this.constructor as typeof RestExchange).FIX_MARKET_STATUS,
      REMOVE_MARKET_STATUS_PRICE_LIMITS: (this.constructor as typeof RestExchange).REMOVE_MARKET_STATUS_PRICE_LIMITS,
      isFuture: config.isFuture ?? false,
      getContractSize: (symbol: string) => this.connector.getContractSizeForSymbol(symbol),
    }
  }

  protected _createConnector(config: ExchangeConfig): CCXTConnector {
    return new CCXTConnector(config, this.getAdapterClass())
  }

  getAdapterClass(): typeof CCXTAdapter {
    // Override in exchange-specific subclasses to use a custom adapter
    return CCXTAdapter
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  async initialize(force = false): Promise<boolean> {
    if (this.isInitialized && !force) return true
    await this.connector.initialize()
    this.symbols = this.connector.symbols
    this.timeFrames = this.connector.timeFrames
    this.isInitialized = true
    return true
  }

  async stop(): Promise<void> {
    await this.connector.stop()
    this.isInitialized = false
  }

  // ── Exchange meta ─────────────────────────────────────────────────────────

  getExchangeCurrentTime(): number {
    return this.connector.getExchangeCurrentTime()
  }

  getMarketStatus(symbol: string, priceExample?: number, withFixer = true): OctoBotMarketStatus {
    return this.connector.getMarketStatus(symbol, priceExample, withFixer)
  }

  getAllAvailableSymbols(activeOnly = true): string[] {
    return this.connector.getAllAvailableSymbols(activeOnly)
  }

  async refreshMarkets(reload = true): Promise<void> {
    await this.connector.refreshMarkets(reload)
    this.symbols = this.connector.symbols
  }

  // ── Delegated methods ─────────────────────────────────────────────────────

  getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]> {
    return this.connector.getSymbolPrices(symbol, timeFrame, limit, params)
  }

  getKlinePrice(
    symbol: string,
    timeFrame: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]> {
    return this.connector.getKlinePrice(symbol, timeFrame, params)
  }

  getPriceTicker(symbol: string, params?: Record<string, unknown>): Promise<OctoBotTicker> {
    return this.connector.getPriceTicker(symbol, params)
  }

  getAllCurrenciesPriceTicker(
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotTicker>> {
    return this.connector.getAllCurrenciesPriceTicker(params)
  }

  getOrderBook(
    symbol: string,
    limit = 5,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrderBook> {
    return this.connector.getOrderBook(symbol, limit, params)
  }

  getRecentTrades(
    symbol: string,
    limit = 50,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]> {
    return this.connector.getRecentTrades(symbol, limit, params)
  }

  getBalance(params?: Record<string, unknown>): Promise<OctoBotBalance> {
    return this.connector.getBalance(params)
  }

  getOrder(
    exchangeOrderId: string,
    symbol?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null> {
    return this.connector.getOrder(exchangeOrderId, symbol, params)
  }

  getOpenOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return this.connector.getOpenOrders(symbol, since, limit, params)
  }

  getClosedOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return this.connector.getClosedOrders(symbol, since, limit, params)
  }

  getCancelledOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]> {
    return this.connector.getCancelledOrders(symbol, since, limit, params)
  }

  getMyRecentTrades(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]> {
    return this.connector.getMyRecentTrades(symbol, since, limit, params)
  }

  createOrder(
    orderType: TraderOrderTypeValue,
    symbol: string,
    quantity: number,
    price?: number,
    stopPrice?: number,
    side?: TradeOrderSideValue,
    currentPrice?: number,
    reduceOnly = false,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null> {
    return this.connector.createOrder(
      orderType,
      symbol,
      quantity,
      price,
      stopPrice,
      side,
      currentPrice,
      reduceOnly,
      params,
    )
  }

  cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    orderType: TraderOrderTypeValue,
    params?: Record<string, unknown>,
  ): Promise<string> {
    return this.connector.cancelOrder(exchangeOrderId, symbol, orderType, params)
  }

  editOrder(
    exchangeOrderId: string,
    orderType: TraderOrderTypeValue,
    symbol: string,
    quantity: number,
    price: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder> {
    return this.connector.editOrder(exchangeOrderId, orderType, symbol, quantity, price, params)
  }

  getPositions(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<OctoBotPosition[]> {
    return this.connector.getPositions(symbols, params)
  }

  getLeverageTiers(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotLeverageTier[]>> {
    return this.connector.getLeverageTiers(symbols, params)
  }

  getFundingRate(symbol: string, params?: Record<string, unknown>): Promise<OctoBotFundingRate> {
    return this.connector.getFundingRate(symbol, params)
  }

  getDepositAddress(
    currency: string,
    network?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotDepositAddress> {
    return this.connector.getDepositAddress(currency, network, params)
  }

  getTransactions(
    currency?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTransaction[]> {
    return this.connector.getTransactions(currency, since, limit, params)
  }
}
