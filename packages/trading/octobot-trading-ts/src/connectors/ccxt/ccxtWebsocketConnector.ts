// Slimmed port of connectors/ccxt/ccxt_websocket_connector.py — wraps the
// `ccxt.pro` (== `ccxt` since v4) WebSocket layer. Each `watch*` method
// awaits one update batch from CCXT and returns the adapted payload; the
// owning WebSocketExchange runs them in a loop and emits onto the EventBus.

import { Exchange as CCXTExchange } from "ccxt";
import type { ExchangeManager } from "../../exchangeManager.js";
import { CCXTAdapter } from "../../adapters/ccxtAdapter.js";
import { getCcxtExchangeClass, setSandboxMode } from "./ccxtClientUtil.js";
import { CCXT_HEADERS, CCXT_OPTIONS } from "./ccxtConstants.js";
import { Logger, getLogger } from "../../util/logger.js";
import { NotSupported } from "../../errors.js";

export interface CCXTWebsocketConnectorOptions {
  adapterClass?: new (connector: unknown) => CCXTAdapter;
  additionalConfig?: Record<string, unknown>;
}

export class CCXTWebsocketConnector {
  protected client!: CCXTExchange;
  adapter: CCXTAdapter;
  exchangeManager: ExchangeManager;
  config: Record<string, unknown>;
  isAuthenticated = false;
  protected logger: Logger;

  protected headers: Record<string, string> = {};
  protected options: Record<string, unknown> = {};

  constructor(
    config: Record<string, unknown>,
    exchangeManager: ExchangeManager,
    opts: CCXTWebsocketConnectorOptions = {},
  ) {
    this.config = config;
    this.exchangeManager = exchangeManager;
    const AdapterClass = opts.adapterClass ?? CCXTAdapter;
    this.adapter = new AdapterClass(this);
    this.logger = getLogger(`CCXTWebsocketConnector[${exchangeManager.exchangeClassString}]`);

    if (opts.additionalConfig?.[CCXT_OPTIONS]) {
      Object.assign(this.options, opts.additionalConfig[CCXT_OPTIONS] as Record<string, unknown>);
    }

    this.createClient();
  }

  protected createClient(): void {
    const ExchangeClass = getCcxtExchangeClass(this.exchangeManager.exchangeClassString);
    const cfg: Record<string, unknown> = { enableRateLimit: true };

    const credentials = this.exchangeManager.credentials;
    if (credentials.apiKey) cfg.apiKey = credentials.apiKey;
    if (credentials.secret) cfg.secret = credentials.secret;
    if (credentials.password) cfg.password = credentials.password;
    if (credentials.uid) cfg.uid = credentials.uid;

    if (this.exchangeManager.proxyConfig) {
      const px = this.exchangeManager.proxyConfig;
      if (px.wsProxy) cfg.wsProxy = px.wsProxy;
      if (px.wssProxy) cfg.wssProxy = px.wssProxy;
      if (px.wsSocksProxy) cfg.wsSocksProxy = px.wsSocksProxy;
    }

    if (Object.keys(this.headers).length) cfg[CCXT_HEADERS] = this.headers;
    if (Object.keys(this.options).length) cfg[CCXT_OPTIONS] = this.options;

    this.client = new ExchangeClass(cfg);
    this.isAuthenticated = !!(credentials.apiKey && credentials.secret);
  }

  async initialize(): Promise<void> {
    if (this.exchangeManager.isSandboxed) setSandboxMode(this.client, true);
    if (typeof this.client.loadMarkets === "function") await this.client.loadMarkets();
  }

  async stop(): Promise<void> {
    if (typeof this.client.close === "function") {
      try { await this.client.close(); }
      catch (err) { this.logger.exception(err, "Error closing WS client"); }
    }
  }

  getClient(): CCXTExchange {
    return this.client;
  }

  protected ensureWatchSupported(method: keyof CCXTExchange): void {
    if (typeof (this.client as unknown as Record<string, unknown>)[method as string] !== "function") {
      throw new NotSupported(`${this.exchangeManager.exchangeClassString} does not implement ${String(method)}`);
    }
  }

  // ---- public feed loops ----

  async watchTicker(symbol: string, params: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    this.ensureWatchSupported("watchTicker" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchTicker: (s: string, p: Record<string, unknown>) => Promise<Record<string, unknown>> }).watchTicker(symbol, params);
    return this.adapter.adaptTicker(raw);
  }

  async watchOHLCV(symbol: string, timeFrame: string, params: Record<string, unknown> = {}): Promise<unknown[][]> {
    this.ensureWatchSupported("watchOHLCV" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchOHLCV: (s: string, tf: string, since: number | undefined, limit: number | undefined, p: Record<string, unknown>) => Promise<unknown[][]> }).watchOHLCV(symbol, timeFrame, undefined, undefined, params);
    const adapted = this.adapter.adaptOhlcv(raw as unknown as Record<string, unknown>, { timeFrame });
    return adapted as unknown as unknown[][];
  }

  async watchTrades(symbol: string, params: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    this.ensureWatchSupported("watchTrades" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchTrades: (s: string, since: number | undefined, limit: number | undefined, p: Record<string, unknown>) => Promise<Record<string, unknown>[]> }).watchTrades(symbol, undefined, undefined, params);
    return this.adapter.adaptPublicRecentTrades(raw);
  }

  async watchOrderBook(symbol: string, limit?: number, params: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    this.ensureWatchSupported("watchOrderBook" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchOrderBook: (s: string, l: number | undefined, p: Record<string, unknown>) => Promise<Record<string, unknown>> }).watchOrderBook(symbol, limit, params);
    return this.adapter.adaptOrderBook(raw);
  }

  async watchOrders(symbol?: string, params: Record<string, unknown> = {}): Promise<Record<string, unknown>[]> {
    this.ensureWatchSupported("watchOrders" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchOrders: (s: string | undefined, since: number | undefined, limit: number | undefined, p: Record<string, unknown>) => Promise<Record<string, unknown>[]> }).watchOrders(symbol, undefined, undefined, params);
    return this.adapter.adaptOrders(raw, { symbol });
  }

  async watchBalance(params: Record<string, unknown> = {}): Promise<Record<string, unknown> | null> {
    this.ensureWatchSupported("watchBalance" as keyof CCXTExchange);
    const raw = await (this.client as unknown as { watchBalance: (p: Record<string, unknown>) => Promise<Record<string, unknown>> }).watchBalance(params);
    return this.adapter.adaptBalance(raw);
  }
}
