// Mirrors octobot_trading/exchanges/abstract_exchange.py
import type { TraderOrderTypeValue, TradeOrderSideValue } from "../enums/index.js"
import { TraderOrderType } from "../enums/order-status.js"
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
} from "../types/index.js"

export interface SupportedElements {
  unsupported_orders: TraderOrderTypeValue[]
  supported_bundled_orders: Record<string, TraderOrderTypeValue[]>
}

export abstract class AbstractExchange {
  // Default supported elements — mirrors AbstractExchange.SUPPORTED_ELEMENTS
  static SUPPORTED_ELEMENTS: Record<string, SupportedElements> = {
    spot: {
      unsupported_orders: [
        TraderOrderType.STOP_LOSS,
        TraderOrderType.STOP_LOSS_LIMIT,
        TraderOrderType.TAKE_PROFIT,
        TraderOrderType.TAKE_PROFIT_LIMIT,
        TraderOrderType.TRAILING_STOP,
        TraderOrderType.TRAILING_STOP_LIMIT,
      ],
      supported_bundled_orders: {},
    },
    future: {
      unsupported_orders: [
        TraderOrderType.STOP_LOSS,
        TraderOrderType.STOP_LOSS_LIMIT,
        TraderOrderType.TAKE_PROFIT,
        TraderOrderType.TAKE_PROFIT_LIMIT,
        TraderOrderType.TRAILING_STOP,
        TraderOrderType.TRAILING_STOP_LIMIT,
      ],
      supported_bundled_orders: {},
    },
  }

  symbols: Set<string> = new Set()
  timeFrames: Set<string> = new Set()
  isInitialized = false

  constructor(
    protected readonly config: ExchangeConfig,
  ) {}

  static getName(): string {
    throw new Error("getName() not implemented")
  }

  static isSimulatedExchange(): boolean {
    return false
  }

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  abstract initialize(force?: boolean): Promise<boolean>
  abstract stop(): Promise<void>

  // ── Exchange meta ─────────────────────────────────────────────────────────

  abstract getExchangeCurrentTime(): number
  abstract getMarketStatus(
    symbol: string,
    priceExample?: number,
    withFixer?: boolean,
  ): OctoBotMarketStatus
  abstract getAllAvailableSymbols(activeOnly?: boolean): string[]
  abstract refreshMarkets(reload?: boolean): Promise<void>

  // ── Public market data ────────────────────────────────────────────────────

  abstract getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]>

  abstract getKlinePrice(
    symbol: string,
    timeFrame: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOHLCV[]>

  abstract getPriceTicker(
    symbol: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTicker>

  abstract getAllCurrenciesPriceTicker(
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotTicker>>

  abstract getOrderBook(
    symbol: string,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrderBook>

  abstract getRecentTrades(
    symbol: string,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]>

  // ── Account data ──────────────────────────────────────────────────────────

  abstract getBalance(params?: Record<string, unknown>): Promise<OctoBotBalance>

  // ── Orders ────────────────────────────────────────────────────────────────

  abstract getOrder(
    exchangeOrderId: string,
    symbol?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null>

  abstract getOpenOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]>

  abstract getClosedOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]>

  abstract getCancelledOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder[]>

  abstract getMyRecentTrades(
    symbol?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTrade[]>

  abstract createOrder(
    orderType: TraderOrderTypeValue,
    symbol: string,
    quantity: number,
    price?: number,
    stopPrice?: number,
    side?: TradeOrderSideValue,
    currentPrice?: number,
    reduceOnly?: boolean,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder | null>

  abstract cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    orderType: TraderOrderTypeValue,
    params?: Record<string, unknown>,
  ): Promise<string>

  abstract editOrder(
    exchangeOrderId: string,
    orderType: TraderOrderTypeValue,
    symbol: string,
    quantity: number,
    price: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotOrder>

  // ── Futures / positions ───────────────────────────────────────────────────

  abstract getPositions(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<OctoBotPosition[]>

  abstract getLeverageTiers(
    symbols?: string[],
    params?: Record<string, unknown>,
  ): Promise<Record<string, OctoBotLeverageTier[]>>

  abstract getFundingRate(
    symbol: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotFundingRate>

  // ── Transactions ──────────────────────────────────────────────────────────

  abstract getDepositAddress(
    currency: string,
    network?: string,
    params?: Record<string, unknown>,
  ): Promise<OctoBotDepositAddress>

  abstract getTransactions(
    currency?: string,
    since?: number,
    limit?: number,
    params?: Record<string, unknown>,
  ): Promise<OctoBotTransaction[]>
}
