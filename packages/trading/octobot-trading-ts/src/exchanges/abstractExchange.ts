// Slimmed port of abstract_exchange.py (888 LOC). Keeps the public method
// signatures the browser-facing wrapper exposes; tentacle-config loading,
// signals dependency, html_util reporting, and decorator-driven authentication
// gating are dropped (server-side concepts per the scope decision).

import Decimal from "decimal.js";
import { AbstractAccount } from "./internal/abstractAccount.js";
import {
  AccountTypes,
  ExchangeTypes,
  TradeOrderSide,
  TraderOrderType,
  OrderStatus,
} from "./enums.js";
import { Logger, getLogger } from "./util/logger.js";
import { ExchangeMarketStatusFixer } from "./util/exchangeMarketStatusFixer.js";

// Forward declaration — circular boundary with ExchangeManager.
export interface ExchangeManagerLike {
  exchangeClassString: string;
  isFuture: boolean;
  isMargin: boolean;
  isSpot: boolean;
  config: Record<string, unknown>;
  tentaclesSetupConfig: unknown;
}

export interface CreateOrderParams {
  reduceOnly?: boolean;
  params?: Record<string, unknown>;
}

export abstract class AbstractExchange extends AbstractAccount {
  static readonly BUY_STR = TradeOrderSide.BUY;
  static readonly SELL_STR = TradeOrderSide.SELL;

  static readonly DEFAULT_EXCHANGE_TIME_LAG = 10; // seconds; mirrors octobot_trading.constants

  // SUPPORTED_ELEMENTS in Python — same shape; subclasses can override.
  static readonly SUPPORTED_ELEMENTS: Record<string, {
    unsupported_orders: TraderOrderType[];
    supported_bundled_orders: Record<string, TraderOrderType[]>;
  }> = {
    [ExchangeTypes.FUTURE]: {
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
    [ExchangeTypes.SPOT]: {
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
  };

  config: Record<string, unknown>;
  exchangeManager: ExchangeManagerLike;
  // Concrete connector type is opaque to AbstractExchange in Python too.
  connector: unknown = null;
  isInitialized = false;
  tentacleConfig: Record<string, unknown> = {};

  symbols: Set<string> = new Set();
  timeFrames: Set<string> = new Set();

  name: string;
  protected logger: Logger;

  allowedTimeLag: number = AbstractExchange.DEFAULT_EXCHANGE_TIME_LAG;
  currentAccount: AccountTypes = AccountTypes.CASH;
  isUnreachable = false;

  protected creatingExchangeOrderDescriptions: Set<string> = new Set();
  protected enableCreateOrderRetrier = true;

  constructor(
    config: Record<string, unknown>,
    exchangeManager: ExchangeManagerLike,
  ) {
    super();
    this.config = config;
    this.exchangeManager = exchangeManager;
    this.name = exchangeManager.exchangeClassString;
    this.logger = getLogger(`${this.constructor.name}[${this.name}]`);
  }

  // ---- lifecycle ----

  async initialize(force = false, opts: Record<string, unknown> = {}): Promise<boolean> {
    if (!this.isInitialized || force) {
      await this.initializeImpl(opts);
      this.isInitialized = true;
      return true;
    }
    return false;
  }

  abstract initializeImpl(opts?: Record<string, unknown>): Promise<void>;
  abstract stop(): Promise<void>;

  // ---- identity ----

  static getName(): string {
    throw new Error("getName is not implemented");
  }

  static isSimulatedExchange(): boolean {
    return false;
  }

  static isDefaultExchange(): boolean {
    return false;
  }

  static isSupportingExchange(_name: string): boolean {
    throw new Error("isSupportingExchange is not implemented");
  }

  static isSupportingSandbox(): boolean {
    return true;
  }

  authenticated(): boolean {
    type AuthCapable = { isAuthenticated?: boolean };
    const c = this.connector as AuthCapable | null;
    return !!c?.isAuthenticated;
  }

  // ---- time / market status ----

  abstract getExchangeCurrentTime(): number;

  getMarketStatus(_symbol: string, _priceExample: number | null = null, _withFixer = true): Record<string, unknown> {
    throw new Error("getMarketStatus is not implemented");
  }

  protected fixMarketStatus(raw: Record<string, unknown>, priceExample: number | null = null): Record<string, unknown> {
    new ExchangeMarketStatusFixer(raw, priceExample);
    return raw;
  }

  // ---- public market data (subclasses override) ----

  abstract getBalance(opts?: Record<string, unknown>): Promise<Record<string, unknown> | null>;
  abstract getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    opts?: Record<string, unknown>,
  ): Promise<unknown[][] | null>;
  abstract getKlinePrice(symbol: string, timeFrame: string, opts?: Record<string, unknown>): Promise<number[] | null>;
  abstract getOrderBook(symbol: string, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown> | null>;
  abstract getRecentTrades(symbol: string, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[] | null>;
  abstract getPriceTicker(symbol: string, opts?: Record<string, unknown>): Promise<Record<string, unknown> | null>;
  abstract getAllCurrenciesPriceTicker(opts?: Record<string, unknown>): Promise<Record<string, Record<string, unknown>> | null>;

  // ---- private/account data ----

  abstract getOrder(exchangeOrderId: string, symbol?: string, opts?: Record<string, unknown>): Promise<Record<string, unknown> | null>;
  abstract getAllOrders(symbol?: string, since?: number, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[]>;
  abstract getOpenOrders(symbol?: string, since?: number, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[]>;
  abstract getClosedOrders(symbol?: string, since?: number, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[]>;
  abstract getCancelledOrders(symbol?: string, since?: number, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[]>;
  abstract getMyRecentTrades(symbol?: string, since?: number, limit?: number, opts?: Record<string, unknown>): Promise<Record<string, unknown>[]>;

  // ---- order operations ----

  abstract cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    orderType: TraderOrderType,
    opts?: Record<string, unknown>,
  ): Promise<OrderStatus>;

  abstract cancelAllOrders(symbol?: string, opts?: Record<string, unknown>): Promise<void>;

  abstract createOrder(
    orderType: TraderOrderType,
    symbol: string,
    quantity: Decimal,
    price?: Decimal,
    stopPrice?: Decimal,
    side?: TradeOrderSide,
    currentPrice?: Decimal,
    params?: CreateOrderParams,
  ): Promise<Record<string, unknown> | null>;

  // ---- helpers ----

  refreshMarkets(): Promise<void> {
    throw new Error("refreshMarkets is not implemented");
  }

  getSupportedElements(elementKey: keyof typeof AbstractExchange.SUPPORTED_ELEMENTS[ExchangeTypes.SPOT]): unknown {
    const exchangeTypeKey = this.exchangeManager.isFuture ? ExchangeTypes.FUTURE : ExchangeTypes.SPOT;
    return AbstractExchange.SUPPORTED_ELEMENTS[exchangeTypeKey][elementKey];
  }
}
