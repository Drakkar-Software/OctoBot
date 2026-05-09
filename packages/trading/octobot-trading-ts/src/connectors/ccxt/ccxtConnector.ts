// Slimmed but functional port of connectors/ccxt/ccxt_connector.py (~1418 LOC).
// Wraps a CCXTExchange with the same uniformized signatures the Python
// connector exposes. Python-only concerns (aiohttp ClientSession lifecycle,
// asynchronous binascii signing, octobot_signals injection) are intentionally
// omitted — ccxt itself handles HTTP transport on both Node and browser.

import ccxt, { Exchange as CCXTExchange } from "ccxt";
import Decimal from "decimal.js";
import type { ExchangeManager } from "../../exchangeManager.js";
import { CCXTAdapter } from "../../adapters/ccxtAdapter.js";
import { getCcxtExchangeClass, setSandboxMode } from "./ccxtClientUtil.js";
import { CCXT_HEADERS, CCXT_OPTIONS } from "./ccxtConstants.js";
import { Logger, getLogger } from "../../util/logger.js";
import { retriedFailedNetworkRequest } from "../util.js";
import {
  AuthenticationError,
  FailedRequest,
  NetworkError,
  NotSupported,
  OctoBotExchangeError,
  RateLimitExceeded,
  UnreachableExchange,
} from "../../errors.js";

export interface CCXTConnectorOptions {
  adapterClass?: new (connector: unknown) => CCXTAdapter;
  additionalConfig?: Record<string, unknown>;
  restName?: string;
  forceAuth?: boolean;
}

export class CCXTConnector {
  client!: CCXTExchange;
  adapter: CCXTAdapter;
  exchangeManager: ExchangeManager;
  config: Record<string, unknown>;

  isAuthenticated = false;
  restName: string;
  forceAuthentication: boolean;
  firstConsecutiveAuthErrorAt: number | null = null;
  protected forceNextMarketReload = false;
  savedData: Record<string, unknown> = {};
  additionalConfig: Record<string, unknown>;
  headers: Record<string, string> = {};
  options: Record<string, unknown> = {};
  symbols: Set<string> = new Set();
  timeFrames: Set<string> = new Set();
  protected logger: Logger;
  isInitialized = false;

  protected exchangeType: typeof CCXTExchange | null = null;

  constructor(
    config: Record<string, unknown>,
    exchangeManager: ExchangeManager,
    opts: CCXTConnectorOptions = {},
  ) {
    this.config = config;
    this.exchangeManager = exchangeManager;
    const AdapterClass = opts.adapterClass ?? CCXTAdapter;
    this.adapter = new AdapterClass(this);
    this.restName = opts.restName ?? exchangeManager.exchangeClassString;
    this.forceAuthentication = opts.forceAuth ?? false;
    this.additionalConfig = opts.additionalConfig ?? {};

    if (this.additionalConfig[CCXT_OPTIONS]) {
      Object.assign(this.options, this.additionalConfig[CCXT_OPTIONS] as Record<string, unknown>);
      delete this.additionalConfig[CCXT_OPTIONS];
    }

    this.logger = getLogger(`CCXTConnector[${this.restName}]`);
    this.createClient();
  }

  protected createClient(): void {
    const ExchangeClass = getCcxtExchangeClass(this.restName);
    const cfg: Record<string, unknown> = {
      enableRateLimit: true,
      ...this.additionalConfig,
    };

    const credentials = this.exchangeManager.credentials;
    if (credentials.apiKey) cfg.apiKey = credentials.apiKey;
    if (credentials.secret) cfg.secret = credentials.secret;
    if (credentials.password) cfg.password = credentials.password;
    if (credentials.uid) cfg.uid = credentials.uid;
    if (credentials.walletAddress) cfg.walletAddress = credentials.walletAddress;
    if (credentials.privateKey) cfg.privateKey = credentials.privateKey;

    if (Object.keys(this.headers).length) cfg[CCXT_HEADERS] = this.headers;
    if (Object.keys(this.options).length) cfg[CCXT_OPTIONS] = this.options;

    if (this.exchangeManager.proxyConfig) {
      const px = this.exchangeManager.proxyConfig;
      if (px.httpProxy) cfg.httpProxy = px.httpProxy;
      if (px.httpsProxy) cfg.httpsProxy = px.httpsProxy;
      if (px.socksProxy) cfg.socksProxy = px.socksProxy;
    }

    this.client = new ExchangeClass(cfg);
    this.isAuthenticated = !!(credentials.apiKey && credentials.secret);
  }

  async initializeImpl(): Promise<void> {
    try {
      if (this.exchangeManager.isSandboxed) {
        setSandboxMode(this.client, true);
      }
      await this.client.loadMarkets();
      const allSymbols = Object.keys(this.client.markets || {});
      for (const s of allSymbols) {
        const m = this.client.markets[s];
        if (m && (m as Record<string, unknown>).active !== false) this.symbols.add(s);
      }
      const tfs = (this.client.timeframes ?? {}) as Record<string, unknown>;
      for (const tf of Object.keys(tfs)) this.timeFrames.add(tf);
      this.isInitialized = true;
    } catch (err) {
      if (err instanceof ccxt.ExchangeNotAvailable || err instanceof ccxt.RequestTimeout) {
        throw new UnreachableExchange((err as Error).message);
      }
      throw this.translateError(err);
    }
  }

  async stop(): Promise<void> {
    if (this.client && typeof this.client.close === "function") {
      try {
        await this.client.close();
      } catch (err) {
        this.logger.exception(err, "Error closing CCXT client");
      }
    }
  }

  // ---- helpers ----

  getExchangeCurrentTime(): number {
    return this.client.milliseconds() / 1000;
  }

  protected translateError(err: unknown): OctoBotExchangeError {
    if (err instanceof ccxt.AuthenticationError) return new AuthenticationError((err as Error).message);
    if (err instanceof ccxt.RateLimitExceeded) return new RateLimitExceeded((err as Error).message);
    if (err instanceof ccxt.NotSupported) return new NotSupported((err as Error).message);
    if (err instanceof ccxt.NetworkError) return new NetworkError((err as Error).message);
    if (err instanceof ccxt.ExchangeError) return new FailedRequest((err as Error).message);
    return new OctoBotExchangeError((err as Error).message);
  }

  // ---- public market data ----

  async getSymbolPrices(
    symbol: string,
    timeFrame: string,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<unknown[][] | null> {
    return retriedFailedNetworkRequest(async () => {
      const since = (params.since as number | undefined) ?? undefined;
      const raw = await this.client.fetchOHLCV(symbol, timeFrame, since, limit, params);
      const fixed = this.adapter.adaptOhlcv(raw as unknown as Record<string, unknown>, { timeFrame });
      return fixed as unknown as unknown[][];
    })();
  }

  async getKlinePrice(
    symbol: string,
    timeFrame: string,
    params: Record<string, unknown> = {},
  ): Promise<number[] | null> {
    const raw = await this.getSymbolPrices(symbol, timeFrame, 1, params);
    if (!raw || raw.length === 0) return null;
    return raw[raw.length - 1] as number[];
  }

  async getOrderBook(
    symbol: string,
    limit = 5,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown> | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchOrderBook(symbol, limit, params);
      return this.adapter.adaptOrderBook(raw as unknown as Record<string, unknown>);
    })();
  }

  async getRecentTrades(
    symbol: string,
    limit = 50,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[] | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchTrades(symbol, undefined, limit, params);
      return this.adapter.adaptPublicRecentTrades(raw as unknown as Record<string, unknown>[]);
    })();
  }

  async getPriceTicker(
    symbol: string,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown> | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchTicker(symbol, params);
      return this.adapter.adaptTicker(raw as unknown as Record<string, unknown>);
    })();
  }

  async getAllCurrenciesPriceTicker(
    params: Record<string, unknown> = {},
  ): Promise<Record<string, Record<string, unknown>> | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchTickers(undefined, params);
      const out: Record<string, Record<string, unknown>> = {};
      for (const [symbol, ticker] of Object.entries(raw)) {
        const adapted = this.adapter.adaptTicker(ticker as unknown as Record<string, unknown>);
        if (adapted) out[symbol] = adapted;
      }
      return out;
    })();
  }

  // ---- account data ----

  async getBalance(params: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchBalance(params);
      return this.adapter.adaptBalance(raw as unknown as Record<string, unknown>);
    })();
  }

  async getOrder(
    exchangeOrderId: string,
    symbol?: string,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown> | null> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchOrder(exchangeOrderId, symbol, params);
      return this.adapter.adaptOrder(raw as unknown as Record<string, unknown>, { symbol });
    })();
  }

  async getAllOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[]> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchOrders(symbol, since, limit, params);
      return this.adapter.adaptOrders(raw as unknown as Record<string, unknown>[], { symbol });
    })();
  }

  async getOpenOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[]> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchOpenOrders(symbol, since, limit, params);
      return this.adapter.adaptOrders(raw as unknown as Record<string, unknown>[], { symbol });
    })();
  }

  async getClosedOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[]> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchClosedOrders(symbol, since, limit, params);
      return this.adapter.adaptOrders(raw as unknown as Record<string, unknown>[], { symbol });
    })();
  }

  async getCancelledOrders(
    symbol?: string,
    since?: number,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[]> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchCanceledOrders(symbol, since, limit, params);
      return this.adapter.adaptOrders(raw as unknown as Record<string, unknown>[], {
        symbol,
        cancelledOnly: true,
      });
    })();
  }

  async getMyRecentTrades(
    symbol?: string,
    since?: number,
    limit?: number,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>[]> {
    return retriedFailedNetworkRequest(async () => {
      const raw = await this.client.fetchMyTrades(symbol, since, limit, params);
      return this.adapter.adaptTrades(raw as unknown as Record<string, unknown>[], { symbol });
    })();
  }

  // ---- order operations ----

  async createOrder(
    symbol: string,
    type: string,
    side: string,
    amount: Decimal,
    price?: Decimal,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown> | null> {
    const raw = await this.client.createOrder(
      symbol,
      type,
      side,
      amount.toNumber(),
      price ? price.toNumber() : undefined,
      params,
    );
    return this.adapter.adaptOrder(raw as unknown as Record<string, unknown>, { symbol });
  }

  async cancelOrder(
    exchangeOrderId: string,
    symbol: string,
    params: Record<string, unknown> = {},
  ): Promise<Record<string, unknown>> {
    const raw = await this.client.cancelOrder(exchangeOrderId, symbol, params);
    return raw as unknown as Record<string, unknown>;
  }

  async cancelAllOrders(symbol?: string, params: Record<string, unknown> = {}): Promise<void> {
    if (typeof this.client.cancelAllOrders === "function") {
      await this.client.cancelAllOrders(symbol, params);
    } else {
      // Fallback: cancel each open order one by one.
      const open = await this.getOpenOrders(symbol);
      for (const order of open) {
        const id = order["id"] || order["exchange_id"];
        const orderSymbol = (order["symbol"] as string) || symbol;
        if (id && orderSymbol) {
          await this.cancelOrder(String(id), orderSymbol, params);
        }
      }
    }
  }

  // ---- market metadata ----

  getMarket(symbol: string): Record<string, unknown> | null {
    const m = this.client.markets?.[symbol];
    return m ? (m as unknown as Record<string, unknown>) : null;
  }

  getMarketStatus(symbol: string, removePriceLimits = false): Record<string, unknown> | null {
    const m = this.getMarket(symbol);
    if (!m) return null;
    return this.adapter.adaptMarketStatus(m, removePriceLimits);
  }

  getContractSize(_symbol: string): Decimal {
    return new Decimal(1);
  }

  getClientTimeFrames(): Set<string> {
    const tfs = (this.client.timeframes ?? {}) as Record<string, unknown>;
    return new Set(Object.keys(tfs));
  }
}
