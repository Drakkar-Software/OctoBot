// Slimmed port of types/rest_exchange.py (~1413 LOC). Keeps every public method
// the Python source defines, but uses the CCXTConnector to do the actual work,
// turning RestExchange into a thin uniformization layer rather than the Python
// god-class. Per the user's scope decision, trader/order-state-machine bits are
// out of scope.

import Decimal from "decimal.js";
import { AbstractExchange, CreateOrderParams, ExchangeManagerLike } from "../abstractExchange.js";
import { CCXTConnector } from "../connectors/ccxt/ccxtConnector.js";
import {
  TraderOrderType,
  TradeOrderSide,
  TradeOrderType,
  OrderStatus,
  ExchangeConstantsOrderColumns as EOC,
} from "../enums.js";
import { ZERO, toDecimal } from "../util/decimalUtil.js";
import { ExchangeMarketStatusFixer } from "../util/exchangeMarketStatusFixer.js";
import { OrderNotFoundOnCancelError, UnsupportedOrderTypeError } from "../errors.js";
import ccxt from "ccxt";

/** Maps OctoBot TraderOrderType to CCXT (type, side) tuples. */
function decomposeOrderType(orderType: TraderOrderType): { type: string; side: TradeOrderSide } {
  switch (orderType) {
    case TraderOrderType.BUY_MARKET: return { type: "market", side: TradeOrderSide.BUY };
    case TraderOrderType.SELL_MARKET: return { type: "market", side: TradeOrderSide.SELL };
    case TraderOrderType.BUY_LIMIT: return { type: "limit", side: TradeOrderSide.BUY };
    case TraderOrderType.SELL_LIMIT: return { type: "limit", side: TradeOrderSide.SELL };
    case TraderOrderType.STOP_LOSS:
    case TraderOrderType.STOP_LOSS_LIMIT:
    case TraderOrderType.TAKE_PROFIT:
    case TraderOrderType.TAKE_PROFIT_LIMIT:
    case TraderOrderType.TRAILING_STOP:
    case TraderOrderType.TRAILING_STOP_LIMIT:
      throw new UnsupportedOrderTypeError(`Order type ${orderType} requires native support; not handled by RestExchange.`);
    default:
      throw new UnsupportedOrderTypeError(`Unknown TraderOrderType: ${orderType}`);
  }
}

export class RestExchange extends AbstractExchange {
  static DUMP_INCOMPLETE_LAST_CANDLE = false;

  connector: CCXTConnector;

  constructor(config: Record<string, unknown>, exchangeManager: ExchangeManagerLike, connector: CCXTConnector) {
    super(config, exchangeManager);
    this.connector = connector;
  }

  async initializeImpl(_opts?: Record<string, unknown>): Promise<void> {
    await this.connector.initializeImpl();
    this.symbols = this.connector.symbols;
    this.timeFrames = this.connector.timeFrames;
  }

  async stop(): Promise<void> {
    await this.connector.stop();
  }

  static getName(): string {
    throw new Error("getName must be overridden by subclass");
  }

  static isSupportingExchange(_name: string): boolean {
    return false;
  }

  getExchangeCurrentTime(): number {
    return this.connector.getExchangeCurrentTime();
  }

  getMarketStatus(symbol: string, priceExample: number | null = null, withFixer = true): Record<string, unknown> {
    const raw = this.connector.getMarketStatus(symbol);
    if (!raw) return {};
    if (withFixer) new ExchangeMarketStatusFixer(raw, priceExample);
    return raw;
  }

  getAllAvailableSymbols(activeOnly = true): Set<string> {
    const result = new Set<string>();
    const markets = this.connector.client.markets ?? {};
    for (const [symbol, m] of Object.entries(markets)) {
      const market = m as Record<string, unknown>;
      if (!activeOnly || market.active !== false) result.add(symbol);
    }
    return result;
  }

  // ---- market data ----

  async getBalance(opts: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return this.connector.getBalance(opts);
  }

  async getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    opts: Record<string, unknown> = {},
  ): Promise<unknown[][] | null> {
    return this.connector.getSymbolPrices(symbol, timeFrame, limit, opts);
  }

  async getKlinePrice(symbol: string, timeFrame: string, opts: Record<string, unknown> = {}): Promise<number[] | null> {
    return this.connector.getKlinePrice(symbol, timeFrame, opts);
  }

  async getOrderBook(symbol: string, limit = 5, opts: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return this.connector.getOrderBook(symbol, limit, opts);
  }

  async getRecentTrades(symbol: string, limit = 50, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[] | null> {
    return this.connector.getRecentTrades(symbol, limit, opts);
  }

  async getPriceTicker(symbol: string, opts: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return this.connector.getPriceTicker(symbol, opts);
  }

  async getAllCurrenciesPriceTicker(opts: Record<string, unknown> = {}): Promise<Record<string, Record<string, unknown>> | null> {
    return this.connector.getAllCurrenciesPriceTicker(opts);
  }

  async refreshMarkets(): Promise<void> {
    await this.connector.client.loadMarkets(true);
  }

  // ---- account data ----

  async getOrder(exchangeOrderId: string, symbol?: string, opts: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return this.connector.getOrder(exchangeOrderId, symbol, opts);
  }

  async getAllOrders(symbol?: string, since?: number, limit?: number, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    return this.connector.getAllOrders(symbol, since, limit, opts);
  }

  async getOpenOrders(symbol?: string, since?: number, limit?: number, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    return this.connector.getOpenOrders(symbol, since, limit, opts);
  }

  async getClosedOrders(symbol?: string, since?: number, limit?: number, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    return this.connector.getClosedOrders(symbol, since, limit, opts);
  }

  async getCancelledOrders(symbol?: string, since?: number, limit?: number, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    return this.connector.getCancelledOrders(symbol, since, limit, opts);
  }

  async getMyRecentTrades(symbol?: string, since?: number, limit?: number, opts: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    return this.connector.getMyRecentTrades(symbol, since, limit, opts);
  }

  // ---- order operations ----

  async createOrder(
    orderType: TraderOrderType,
    symbol: string,
    quantity: Decimal,
    price?: Decimal,
    _stopPrice?: Decimal,
    _side?: TradeOrderSide,
    _currentPrice?: Decimal,
    params?: CreateOrderParams,
  ): Promise<Record<string, unknown> | null> {
    const { type, side } = decomposeOrderType(orderType);
    const ccxtParams: Record<string, unknown> = { ...(params?.params ?? {}) };
    if (params?.reduceOnly) ccxtParams.reduceOnly = true;
    return this.connector.createOrder(symbol, type, side, quantity, price, ccxtParams);
  }

  async cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    _orderType: TraderOrderType,
    opts: Record<string, unknown> = {},
  ): Promise<OrderStatus> {
    try {
      await this.connector.cancelOrder(exchangeOrderId, symbol, opts);
      return OrderStatus.CANCELED;
    } catch (err) {
      if (err instanceof ccxt.OrderNotFound) {
        throw new OrderNotFoundOnCancelError((err as Error).message);
      }
      throw err;
    }
  }

  async cancelAllOrders(symbol?: string, opts: Record<string, unknown> = {}): Promise<void> {
    await this.connector.cancelAllOrders(symbol, opts);
  }

  // ---- helpers used by personal_data on the Python side; kept for parity ----

  getContractSize(_symbol: string): Decimal {
    return this.connector.getContractSize(_symbol);
  }

  getContractType(_symbol: string): unknown {
    return null;
  }

  /**
   * Compute the price at which a market order would fill, in base currency,
   * using the order book — mirrors RestExchange.calculate_quantity_from_amount_with_orderbook.
   */
  async calculatePriceFromOrderBook(symbol: string, baseAmount: Decimal, side: TradeOrderSide): Promise<Decimal> {
    const ob = await this.getOrderBook(symbol, 25);
    if (!ob) return ZERO;
    const levels = (side === TradeOrderSide.BUY ? ob["asks"] : ob["bids"]) as number[][] | undefined;
    if (!levels || levels.length === 0) return ZERO;
    let remaining = baseAmount;
    let totalCost = ZERO;
    for (const [px, sz] of levels) {
      const take = Decimal.min(remaining, toDecimal(sz));
      totalCost = totalCost.plus(take.mul(toDecimal(px)));
      remaining = remaining.minus(take);
      if (remaining.lte(0)) break;
    }
    if (baseAmount.eq(ZERO)) return ZERO;
    return totalCost.div(baseAmount);
  }

  // Pass-through to keep Python parity for adapter calls.
  get adapter() {
    return this.connector.adapter;
  }
}

// Re-export the constant set used by adapter for convenience (Python parity).
export { EOC };
